from flask import Flask, render_template, request, redirect, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash


# ==========================================
# Create Flask application
# ==========================================

app = Flask(__name__)

# Used to protect session information and flash messages
app.secret_key = "BakeFlowSecretKey2026"

# SQLite database file
DATABASE = "bakeflow.db"


# ==========================================
# Database connection
# ==========================================

def get_db_connection():

    connection = sqlite3.connect(DATABASE)

    # Allows database columns to be accessed using their names
    connection.row_factory = sqlite3.Row

    return connection


# ==========================================
# Create database
# ==========================================

def create_database():

    connection = get_db_connection()
    cursor = connection.cursor()


    # ==========================================
    # Users Table
    # ==========================================

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


    # ==========================================
    # Products Table
    # ==========================================

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


    # ==========================================
    # Cart Table
    # ==========================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cart (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_email TEXT NOT NULL,

            product_id INTEGER NOT NULL,

            quantity INTEGER NOT NULL,

            FOREIGN KEY (user_email)
                REFERENCES users(email),

            FOREIGN KEY (product_id)
                REFERENCES products(id)
        )
    """)


    # ==========================================
    # Orders Table
    # ==========================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_email TEXT NOT NULL,

            order_date TEXT NOT NULL,

            status TEXT NOT NULL,

            order_type TEXT NOT NULL,

            delivery_method TEXT NOT NULL,

            total REAL NOT NULL,

            FOREIGN KEY (user_email)
                REFERENCES users(email)
        )
    """)


    # ==========================================
    # Order Items Table
    # ==========================================

    # Stores the individual cakes belonging to each order

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS order_items (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            order_id INTEGER NOT NULL,

            product_id INTEGER NOT NULL,

            quantity INTEGER NOT NULL,

            price REAL NOT NULL,

            FOREIGN KEY (order_id)
                REFERENCES orders(id),

            FOREIGN KEY (product_id)
                REFERENCES products(id)
        )
    """)


    # ==========================================
    # Custom Cake Table
    # ==========================================

    # This table is ready for the custom cake builder page later

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS custom_cakes (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_email TEXT NOT NULL,

            size TEXT,

            flavour TEXT,

            filling TEXT,

            frosting TEXT,

            colour TEXT,

            decorations TEXT,

            cake_message TEXT,

            notes TEXT,

            estimated_price REAL,

            FOREIGN KEY (user_email)
                REFERENCES users(email)
        )
    """)


    # ==========================================
    # Create default administrator account
    # ==========================================

    cursor.execute(
        "SELECT * FROM users WHERE email = ?",
        ("admin@sweetsouls.com",)
    )

    admin = cursor.fetchone()

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


    # ==========================================
    # Add starter products
    # ==========================================

    cursor.execute("SELECT COUNT(*) FROM products")

    product_count = cursor.fetchone()[0]

    # Only add products if the table is empty

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
# Main Route
# ==========================================

@app.route("/")
def index():

    if "user" in session:

        return redirect("/home")

    return redirect("/login")


# ==========================================
# Login Page
# ==========================================

@app.route("/login")
def login():

    return render_template("login.html")


# ==========================================
# Login Authentication
# ==========================================

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

    # Check the user exists and the password is correct

    if user and check_password_hash(
        user["password"],
        password
    ):

        session["user"] = user["first_name"]

        session["email"] = user["email"]

        session["role"] = user["role"]

        return redirect("/home")

    flash("Incorrect email or password.")

    return redirect("/login")


# ==========================================
# Logout
# ==========================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


# ==========================================
# Registration Page
# ==========================================

@app.route("/register")
def register():

    return render_template("register.html")


# ==========================================
# Register New Customer
# ==========================================

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


    # Check that both passwords match

    if password != confirm_password:

        flash("Passwords do not match.")

        return redirect("/register")


    # Password must contain at least 8 characters

    if len(password) < 8:

        flash("Password must contain at least 8 characters.")

        return redirect("/register")


    connection = get_db_connection()

    cursor = connection.cursor()


    # Check whether email already exists

    cursor.execute(
        "SELECT * FROM users WHERE email = ?",
        (email,)
    )

    existing_user = cursor.fetchone()

    if existing_user:

        connection.close()

        flash("Email already registered.")

        return redirect("/register")


    # Securely hash the password

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
# Home Page
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
# Products Page
# ==========================================

@app.route("/products")
def products():

    if "user" not in session:

        return redirect("/login")


    connection = get_db_connection()

    cursor = connection.cursor()


    cursor.execute(
        "SELECT * FROM products"
    )


    product_records = cursor.fetchall()


    connection.close()


    return render_template(

        "products.html",

        username=session["user"],

        products=product_records
    )


# ==========================================
# Individual Product Page
# ==========================================

@app.route("/product/<int:product_id>")
def product_details(product_id):

    if "user" not in session:

        return redirect("/login")


    connection = get_db_connection()

    cursor = connection.cursor()


    cursor.execute(
        "SELECT * FROM products WHERE id = ?",
        (product_id,)
    )


    product = cursor.fetchone()


    connection.close()


    if product is None:

        flash("Product could not be found.")

        return redirect("/products")


    return render_template(

        "product_details.html",

        username=session["user"],

        product=product
    )


# ==========================================
# Add Product To Cart
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


    # Check product exists

    cursor.execute(
        "SELECT id FROM products WHERE id = ?",
        (product_id,)
    )


    product = cursor.fetchone()


    if product is None:

        connection.close()

        flash("That product could not be found.")

        return redirect("/products")


    # Check whether product already exists in cart

    cursor.execute("""
        SELECT *

        FROM cart

        WHERE user_email = ?

        AND product_id = ?

    """, (

        user_email,

        product_id
    ))


    existing_item = cursor.fetchone()


    if existing_item:

        # Increase existing quantity

        cursor.execute("""
            UPDATE cart

            SET quantity = quantity + 1

            WHERE id = ?

        """, (

            existing_item["id"],
        ))


    else:

        # Add a new cart record

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
# Shopping Cart Page
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


    # Join cart and product data

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


    # Calculate total price

    total = sum(
        item["item_total"]
        for item in cart_items
    )


    return render_template(

        "cart.html",

        username=session["user"],

        cart_items=cart_items,

        total=total
    )


# ==========================================
# Remove Product From Cart
# ==========================================

@app.route("/remove-from-cart/<int:cart_id>")
def remove_from_cart(cart_id):

    if "user" not in session:

        return redirect("/login")


    user_email = session.get("email")


    if not user_email:

        session.clear()

        return redirect("/login")


    connection = get_db_connection()

    cursor = connection.cursor()


    cursor.execute("""
        DELETE FROM cart

        WHERE id = ?

        AND user_email = ?

    """, (

        cart_id,

        user_email
    ))


    connection.commit()

    connection.close()


    flash("Cake removed from cart.")

    return redirect("/cart")


# ==========================================
# Checkout Page
# ==========================================

@app.route("/checkout")
def checkout():

    if "user" not in session:

        return redirect("/login")


    return render_template(

        "checkout.html",

        username=session["user"]
    )


# ==========================================
# Orders Page
# ==========================================

@app.route("/orders")
def orders():

    if "user" not in session:

        return redirect("/login")


    user_email = session.get("email")


    connection = get_db_connection()

    cursor = connection.cursor()


    cursor.execute("""
        SELECT *

        FROM orders

        WHERE user_email = ?

        ORDER BY id DESC

    """, (

        user_email,
    ))


    order_records = cursor.fetchall()


    # Count active orders

    cursor.execute("""
        SELECT COUNT(*)

        FROM orders

        WHERE user_email = ?

        AND status != 'Completed'

    """, (

        user_email,
    ))


    active_orders = cursor.fetchone()[0]


    # Count completed orders

    cursor.execute("""
        SELECT COUNT(*)

        FROM orders

        WHERE user_email = ?

        AND status = 'Completed'

    """, (

        user_email,
    ))


    completed_orders = cursor.fetchone()[0]


    connection.close()


    return render_template(

        "orders.html",

        username=session["user"],

        orders=order_records,

        active_orders=active_orders,

        completed_orders=completed_orders
    )


# ==========================================
# Custom Cake Builder Page
# ==========================================

@app.route("/custom-cakes")
def custom_cakes():

    if "user" not in session:

        return redirect("/login")


    return render_template(

        "custom_cakes.html",

        username=session["user"]
    )


# ==========================================
# SmartBake AI Page
# ==========================================

@app.route("/smartbake")
def smartbake():

    if "user" not in session:

        return redirect("/login")


    return render_template(

        "smartbake.html",

        username=session["user"]
    )


# ==========================================
# Contact Page
# ==========================================

@app.route("/contact")
def contact():

    if "user" not in session:

        return redirect("/login")


    return render_template(

        "contact.html",

        username=session["user"]
    )


# ==========================================
# Run Application
# ==========================================

if __name__ == "__main__":

    create_database()

    app.run(debug=True)