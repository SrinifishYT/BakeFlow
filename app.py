from flask import Flask, render_template, request, redirect, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash


# Creates the Flask application
app = Flask(__name__)

# Used by Flask to protect session information and flash messages
app.secret_key = "BakeFlowSecretKey2026"

# Name of the SQLite database file
DATABASE = "bakeflow.db"


# ==========================================
# Database connection
# ==========================================

def get_db_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


# ==========================================
# Create database tables and starter data
# ==========================================

def create_database():
    connection = get_db_connection()
    cursor = connection.cursor()

    # Stores customer and administrator accounts
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT NOT NULL,
            password TEXT NOT NULL,
            street TEXT NOT NULL,
            suburb TEXT NOT NULL,
            state TEXT NOT NULL,
            postcode TEXT NOT NULL,
            favourite_cake TEXT,
            dietary TEXT,
            marketing INTEGER,
            role TEXT NOT NULL
        )
    """)

    # Stores cakes displayed on the products page
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            price REAL NOT NULL,
            image TEXT NOT NULL
        )
    """)

    # Stores products placed in each customer's cart
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cart (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            FOREIGN KEY (user_email) REFERENCES users(email),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)

    # Check whether the default administrator exists
    cursor.execute(
        "SELECT * FROM users WHERE email = ?",
        ("admin@sweetsouls.com",)
    )

    admin = cursor.fetchone()

    # Create the administrator account once
    if admin is None:
        hashed_password = generate_password_hash("Admin123")

        cursor.execute("""
            INSERT INTO users (
                first_name,
                last_name,
                email,
                phone,
                password,
                street,
                suburb,
                state,
                postcode,
                favourite_cake,
                dietary,
                marketing,
                role
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "Sweet",
            "Souls",
            "admin@sweetsouls.com",
            "0400000000",
            hashed_password,
            "Bakery Street",
            "Melbourne",
            "Victoria",
            "3000",
            "",
            "",
            0,
            "Admin"
        ))

    # Add sample products only if the products table is empty
    cursor.execute("SELECT COUNT(*) FROM products")
    product_count = cursor.fetchone()[0]

    if product_count == 0:
        sample_products = [
            (
                "Chocolate Dream Cake",
                "Chocolate",
                "Rich chocolate sponge with silky ganache.",
                79.95,
                "chocolate-cake.jpg"
            ),
            (
                "Vanilla Celebration",
                "Vanilla",
                "Classic vanilla cake with buttercream frosting.",
                69.95,
                "vanilla-cake.jpg"
            ),
            (
                "Lotus Biscoff Cake",
                "Specialty",
                "Layers of Lotus Biscoff sponge and cream.",
                89.95,
                "lotus-cake.jpg"
            ),
            (
                "Red Velvet Cake",
                "Red Velvet",
                "Traditional red velvet with cream cheese icing.",
                84.95,
                "redvelvet-cake.jpg"
            ),
            (
                "Strawberry Delight",
                "Fruit",
                "Fresh strawberries with whipped cream.",
                74.95,
                "strawberry-cake.jpg"
            ),
            (
                "Cookies & Cream",
                "Specialty",
                "Loaded with Oreo pieces and cream.",
                79.95,
                "oreo-cake.jpg"
            )
        ]

        cursor.executemany("""
            INSERT INTO products (
                name,
                category,
                description,
                price,
                image
            )
            VALUES (?, ?, ?, ?, ?)
        """, sample_products)

    connection.commit()
    connection.close()


# ==========================================
# Main route
# ==========================================

@app.route("/")
def index():
    if "user" in session:
        return redirect("/home")

    return redirect("/login")


# ==========================================
# Login routes
# ==========================================

@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login_user():
    email = request.form["email"].strip().lower()
    password = request.form["password"]

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(
        "SELECT * FROM users WHERE email = ?",
        (email,)
    )

    user = cursor.fetchone()
    connection.close()

    if user and check_password_hash(user["password"], password):
        session["user"] = user["first_name"]
        session["email"] = user["email"]
        session["role"] = user["role"]

        return redirect("/home")

    flash("Incorrect email or password.")
    return redirect("/login")


# ==========================================
# Logout route
# ==========================================

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ==========================================
# Registration routes
# ==========================================

@app.route("/register")
def register():
    return render_template("register.html")


@app.route("/register", methods=["POST"])
def register_user():
    first_name = request.form["first_name"].strip()
    last_name = request.form["last_name"].strip()
    email = request.form["email"].strip().lower()
    phone = request.form["phone"].strip()

    street = request.form["street"].strip()
    suburb = request.form["suburb"].strip()
    state = request.form["state"]
    postcode = request.form["postcode"].strip()

    favourite_cake = request.form["favourite_cake"]
    dietary = request.form["dietary"]

    password = request.form["password"]
    confirm_password = request.form["confirm_password"]

    marketing = 1 if "marketing" in request.form else 0

    # Make sure both passwords match
    if password != confirm_password:
        flash("Passwords do not match.")
        return redirect("/register")

    # Basic password length check
    if len(password) < 8:
        flash("Password must contain at least 8 characters.")
        return redirect("/register")

    connection = get_db_connection()
    cursor = connection.cursor()

    # Check whether the email is already registered
    cursor.execute(
        "SELECT * FROM users WHERE email = ?",
        (email,)
    )

    existing_user = cursor.fetchone()

    if existing_user:
        connection.close()
        flash("Email already registered.")
        return redirect("/register")

    hashed_password = generate_password_hash(password)

    cursor.execute("""
        INSERT INTO users (
            first_name,
            last_name,
            email,
            phone,
            password,
            street,
            suburb,
            state,
            postcode,
            favourite_cake,
            dietary,
            marketing,
            role
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        first_name,
        last_name,
        email,
        phone,
        hashed_password,
        street,
        suburb,
        state,
        postcode,
        favourite_cake,
        dietary,
        marketing,
        "Customer"
    ))

    connection.commit()
    connection.close()

    flash("Account created successfully. Please login.")
    return redirect("/login")


# ==========================================
# Home page
# ==========================================

@app.route("/home")
def home():
    if "user" not in session:
        return redirect("/login")

    return render_template(
        "home.html",
        username=session["user"]
    )


# ==========================================
# Products page
# ==========================================

@app.route("/products")
def products():
    if "user" not in session:
        return redirect("/login")

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM products")
    product_records = cursor.fetchall()

    connection.close()

    return render_template(
        "products.html",
        username=session["user"],
        products=product_records
    )


# ==========================================
# Add a product to the shopping cart
# ==========================================

@app.route("/add-to-cart/<int:product_id>")
def add_to_cart(product_id):
    if "user" not in session:
        return redirect("/login")

    user_email = session.get("email")

    if not user_email:
        session.clear()
        flash("Please log in again.")
        return redirect("/login")

    connection = get_db_connection()
    cursor = connection.cursor()

    # Check that the selected product exists
    cursor.execute(
        "SELECT id FROM products WHERE id = ?",
        (product_id,)
    )

    product = cursor.fetchone()

    if product is None:
        connection.close()
        flash("That product could not be found.")
        return redirect("/products")

    # Check whether this product is already in the cart
    cursor.execute("""
        SELECT *
        FROM cart
        WHERE user_email = ? AND product_id = ?
    """, (
        user_email,
        product_id
    ))

    existing_item = cursor.fetchone()

    # Increase the quantity if it is already in the cart
    if existing_item:
        cursor.execute("""
            UPDATE cart
            SET quantity = quantity + 1
            WHERE id = ?
        """, (
            existing_item["id"],
        ))

    # Otherwise add it as a new cart item
    else:
        cursor.execute("""
            INSERT INTO cart (
                user_email,
                product_id,
                quantity
            )
            VALUES (?, ?, ?)
        """, (
            user_email,
            product_id,
            1
        ))

    connection.commit()
    connection.close()

    flash("Cake added to cart!")
    return redirect("/products")


# ==========================================
# Display the shopping cart
# ==========================================

@app.route("/cart")
def cart():
    if "user" not in session:
        return redirect("/login")

    user_email = session.get("email")

    if not user_email:
        session.clear()
        flash("Please log in again.")
        return redirect("/login")

    connection = get_db_connection()
    cursor = connection.cursor()

    # Join the cart and products tables to retrieve
    # the product details for each cart record
    cursor.execute("""
        SELECT
            cart.id AS cart_id,
            cart.quantity,
            products.id AS product_id,
            products.name,
            products.category,
            products.description,
            products.price,
            products.image,
            products.price * cart.quantity AS item_total
        FROM cart
        INNER JOIN products
            ON cart.product_id = products.id
        WHERE cart.user_email = ?
        ORDER BY cart.id DESC
    """, (
        user_email,
    ))

    cart_items = cursor.fetchall()
    connection.close()

    total = sum(item["item_total"] for item in cart_items)

    return render_template(
        "cart.html",
        username=session["user"],
        cart_items=cart_items,
        total=total
    )


# ==========================================
# Remove a product from the shopping cart
# ==========================================

@app.route("/remove-from-cart/<int:cart_id>")
def remove_from_cart(cart_id):
    if "user" not in session:
        return redirect("/login")

    user_email = session.get("email")

    if not user_email:
        session.clear()
        flash("Please log in again.")
        return redirect("/login")

    connection = get_db_connection()
    cursor = connection.cursor()

    # The email check stops a user from removing
    # an item belonging to another customer's cart
    cursor.execute("""
        DELETE FROM cart
        WHERE id = ? AND user_email = ?
    """, (
        cart_id,
        user_email
    ))

    connection.commit()
    connection.close()

    flash("Cake removed from cart.")
    return redirect("/cart")


# ==========================================
# Placeholder pages for future development
# ==========================================

@app.route("/custom-cakes")
def custom_cakes():
    if "user" not in session:
        return redirect("/login")

    return "<h1>Custom Cake Builder Coming Soon</h1>"


@app.route("/smartbake")
def smartbake():
    if "user" not in session:
        return redirect("/login")

    return "<h1>SmartBake AI Coming Soon</h1>"


@app.route("/orders")
def orders():
    if "user" not in session:
        return redirect("/login")

    return "<h1>Orders Page Coming Soon</h1>"


@app.route("/contact")
def contact():
    if "user" not in session:
        return redirect("/login")

    return "<h1>Contact Page Coming Soon</h1>"


# ==========================================
# Run the application
# ==========================================

if __name__ == "__main__":
    create_database()
    app.run(debug=True)