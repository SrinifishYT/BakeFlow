from flask import Flask, render_template, request, redirect, session, flash, jsonify, url_for
import os
import sqlite3
from datetime import datetime, date, timedelta
from functools import wraps

from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


# ==========================================
# Application setup
# ==========================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

app = Flask(__name__)
app.secret_key = os.getenv("BAKEFLOW_SECRET_KEY", "BakeFlowSecretKey2026")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=14)

DATABASE = os.path.join(BASE_DIR, "bakeflow.db")

ORDER_STATUSES = ["Order Placed", "Baking", "Ready", "Completed", "Cancelled"]
DELIVERY_FEE = 12.00
LOW_STOCK_LEVEL = 5

SIZE_PRICES = {
    "6 inch": 65.00,
    "8 inch": 85.00,
    "10 inch": 105.00,
}

FLAVOUR_PRICES = {
    "Vanilla": 0.00,
    "Chocolate": 5.00,
    "Red Velvet": 8.00,
    "Lotus Biscoff": 10.00,
    "Strawberry": 7.00,
}

FILLING_PRICES = {
    "Vanilla Buttercream": 0.00,
    "Chocolate Ganache": 5.00,
    "Biscoff Spread": 8.00,
    "Strawberry Cream": 7.00,
    "Cream Cheese": 6.00,
}

FROSTING_PRICES = {
    "Buttercream": 0.00,
    "Chocolate Ganache": 8.00,
    "Cream Cheese": 6.00,
    "Fondant": 15.00,
}

SHAPE_PRICES = {
    "Round": 0.00,
    "Square": 5.00,
    "Heart": 12.00,
}

DIETARY_PRICES = {
    "Standard": 0.00,
    "Gluten Free": 12.00,
    "Dairy Free": 12.00,
    "Vegan": 15.00,
}

DECORATION_PRICES = {
    "Sprinkles": 4.00,
    "Chocolate Drip": 8.00,
    "Gold Leaf": 10.00,
    "Fresh Flowers": 12.00,
    "Macarons": 12.00,
}

SIZE_SERVINGS = {
    "6 inch": "10–12",
    "8 inch": "18–22",
    "10 inch": "28–32",
}


# ==========================================
# Database helpers
# ==========================================

def get_db_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def add_column_if_missing(connection, table, column, definition):
    columns = [row[1] for row in connection.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in columns:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def create_database():
    connection = get_db_connection()
    cursor = connection.cursor()

    # Customer and administrator accounts
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
            marketing INTEGER DEFAULT 0,
            role TEXT NOT NULL DEFAULT 'Customer'
        )
    """)

    # Products and inventory
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            price REAL NOT NULL,
            image TEXT NOT NULL,
            stock INTEGER NOT NULL DEFAULT 15,
            is_active INTEGER NOT NULL DEFAULT 1
        )
    """)
    add_column_if_missing(connection, "products", "stock", "INTEGER NOT NULL DEFAULT 15")
    add_column_if_missing(connection, "products", "is_active", "INTEGER NOT NULL DEFAULT 1")

    # Standard product cart
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cart (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (user_email) REFERENCES users(email),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)

    # Custom cake designs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS custom_cakes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            size TEXT NOT NULL,
            flavour TEXT NOT NULL,
            filling TEXT NOT NULL,
            frosting TEXT NOT NULL,
            colour TEXT NOT NULL,
            decorations TEXT,
            cake_message TEXT,
            notes TEXT,
            estimated_price REAL NOT NULL,
            shape TEXT DEFAULT 'Round',
            dietary TEXT DEFAULT 'Standard',
            event_date TEXT,
            servings TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_email) REFERENCES users(email)
        )
    """)
    add_column_if_missing(connection, "custom_cakes", "shape", "TEXT DEFAULT 'Round'")
    add_column_if_missing(connection, "custom_cakes", "dietary", "TEXT DEFAULT 'Standard'")
    add_column_if_missing(connection, "custom_cakes", "event_date", "TEXT")
    add_column_if_missing(connection, "custom_cakes", "servings", "TEXT")
    add_column_if_missing(connection, "custom_cakes", "created_at", "TEXT")

    # Custom cake cart
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS custom_cart (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            custom_cake_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (user_email) REFERENCES users(email),
            FOREIGN KEY (custom_cake_id) REFERENCES custom_cakes(id)
        )
    """)

    # Customer orders
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            order_date TEXT NOT NULL,
            status TEXT NOT NULL,
            order_type TEXT NOT NULL,
            delivery_method TEXT NOT NULL,
            total REAL NOT NULL,
            customer_name TEXT,
            phone TEXT,
            street TEXT,
            suburb TEXT,
            state TEXT,
            postcode TEXT,
            requested_date TEXT,
            notes TEXT,
            delivery_fee REAL DEFAULT 0,
            payment_method TEXT DEFAULT 'Pay on pickup/delivery',
            FOREIGN KEY (user_email) REFERENCES users(email)
        )
    """)
    add_column_if_missing(connection, "orders", "customer_name", "TEXT")
    add_column_if_missing(connection, "orders", "phone", "TEXT")
    add_column_if_missing(connection, "orders", "street", "TEXT")
    add_column_if_missing(connection, "orders", "suburb", "TEXT")
    add_column_if_missing(connection, "orders", "state", "TEXT")
    add_column_if_missing(connection, "orders", "postcode", "TEXT")
    add_column_if_missing(connection, "orders", "requested_date", "TEXT")
    add_column_if_missing(connection, "orders", "notes", "TEXT")
    add_column_if_missing(connection, "orders", "delivery_fee", "REAL DEFAULT 0")
    add_column_if_missing(connection, "orders", "payment_method", "TEXT DEFAULT 'Pay on pickup/delivery'")

    # Standard products attached to an order
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            product_name TEXT,
            image TEXT,
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)
    add_column_if_missing(connection, "order_items", "product_name", "TEXT")
    add_column_if_missing(connection, "order_items", "image", "TEXT")

    # Custom cakes attached to an order
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS custom_order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            custom_cake_id INTEGER,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            size TEXT,
            flavour TEXT,
            filling TEXT,
            frosting TEXT,
            colour TEXT,
            decorations TEXT,
            cake_message TEXT,
            notes TEXT,
            shape TEXT,
            dietary TEXT,
            event_date TEXT,
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (custom_cake_id) REFERENCES custom_cakes(id)
        )
    """)

    # Contact form messages
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS contact_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            subject TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            is_read INTEGER NOT NULL DEFAULT 0
        )
    """)

    # SmartBake conversation history
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS smartbake_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Default administrator
    cursor.execute("SELECT id FROM users WHERE email = ?", ("admin@sweetsouls.com",))
    if cursor.fetchone() is None:
        cursor.execute("""
            INSERT INTO users (
                first_name, last_name, email, phone, password, street,
                suburb, state, postcode, favourite_cake, dietary, marketing, role
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "Sweet", "Souls", "admin@sweetsouls.com", "0400000000",
            generate_password_hash("Admin123"), "Bakery Street", "Melbourne",
            "Victoria", "3000", "", "", 0, "Admin"
        ))

    # Starter products
    cursor.execute("SELECT COUNT(*) FROM products")
    if cursor.fetchone()[0] == 0:
        products = [
            ("Chocolate Dream Cake", "Chocolate", "Rich chocolate sponge with silky ganache.", 79.95, "chocolate-cake.jpg", 15, 1),
            ("Vanilla Celebration", "Vanilla", "Classic vanilla cake with buttercream frosting.", 69.95, "vanilla-cake.jpg", 15, 1),
            ("Lotus Biscoff Cake", "Specialty", "Layers of Lotus Biscoff sponge and cream.", 89.95, "lotus-cake.jpg", 12, 1),
            ("Red Velvet Cake", "Red Velvet", "Traditional red velvet with cream cheese icing.", 84.95, "red-velvet.jpg", 10, 1),
            ("Strawberry Delight", "Fruit", "Fresh strawberries with whipped cream.", 74.95, "strawberry-cake.jpg", 12, 1),
            ("Cookies & Cream", "Specialty", "Loaded with Oreo pieces and cream.", 79.95, "oreo-cake.jpg", 15, 1),
        ]
        cursor.executemany("""
            INSERT INTO products (name, category, description, price, image, stock, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, products)

    # Fix the older Red Velvet image filename if it is already in the database
    cursor.execute("UPDATE products SET image = 'red-velvet.jpg' WHERE image = 'redvelvet-cake.jpg'")

    connection.commit()
    connection.close()


# ==========================================
# Login helpers
# ==========================================

def login_required(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        if "user" not in session or "email" not in session:
            flash("Please log in to continue.")
            return redirect(url_for("login"))
        return function(*args, **kwargs)
    return wrapped


def admin_required(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        if session.get("role") != "Admin":
            flash("Administrator access is required.")
            return redirect(url_for("home"))
        return function(*args, **kwargs)
    return wrapped


# ==========================================
# Shared helpers
# ==========================================

def calculate_custom_cake_price(size, flavour, filling, frosting, shape, dietary, decorations):
    if size not in SIZE_PRICES:
        raise ValueError("Invalid cake size")
    if flavour not in FLAVOUR_PRICES:
        raise ValueError("Invalid cake flavour")
    if filling not in FILLING_PRICES:
        raise ValueError("Invalid cake filling")
    if frosting not in FROSTING_PRICES:
        raise ValueError("Invalid frosting")
    if shape not in SHAPE_PRICES:
        raise ValueError("Invalid cake shape")
    if dietary not in DIETARY_PRICES:
        raise ValueError("Invalid dietary option")

    total = SIZE_PRICES[size]
    total += FLAVOUR_PRICES[flavour]
    total += FILLING_PRICES[filling]
    total += FROSTING_PRICES[frosting]
    total += SHAPE_PRICES[shape]
    total += DIETARY_PRICES[dietary]

    for decoration in decorations:
        total += DECORATION_PRICES.get(decoration, 0)

    return round(total, 2)


def get_cart_data(user_email):
    connection = get_db_connection()
    cursor = connection.cursor()

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
            products.stock,
            products.price * cart.quantity AS item_total
        FROM cart
        INNER JOIN products ON cart.product_id = products.id
        WHERE cart.user_email = ?
        ORDER BY cart.id DESC
    """, (user_email,))
    product_items = cursor.fetchall()

    cursor.execute("""
        SELECT
            custom_cart.id AS cart_id,
            custom_cart.quantity,
            custom_cakes.*,
            custom_cakes.estimated_price * custom_cart.quantity AS item_total
        FROM custom_cart
        INNER JOIN custom_cakes ON custom_cart.custom_cake_id = custom_cakes.id
        WHERE custom_cart.user_email = ?
        ORDER BY custom_cart.id DESC
    """, (user_email,))
    custom_items = cursor.fetchall()

    connection.close()

    subtotal = sum(item["item_total"] for item in product_items)
    subtotal += sum(item["item_total"] for item in custom_items)

    return product_items, custom_items, round(subtotal, 2)


def get_logged_in_user():
    if "email" not in session:
        return None
    connection = get_db_connection()
    user = connection.execute("SELECT * FROM users WHERE email = ?", (session["email"],)).fetchone()
    connection.close()
    return user


@app.context_processor
def shared_template_values():
    cart_count = 0
    if session.get("email"):
        connection = get_db_connection()
        product_count = connection.execute(
            "SELECT COALESCE(SUM(quantity), 0) FROM cart WHERE user_email = ?",
            (session["email"],)
        ).fetchone()[0]
        custom_count = connection.execute(
            "SELECT COALESCE(SUM(quantity), 0) FROM custom_cart WHERE user_email = ?",
            (session["email"],)
        ).fetchone()[0]
        connection.close()
        cart_count = product_count + custom_count

    return {
        "cart_count": cart_count,
        "current_role": session.get("role"),
    }


# ==========================================
# Authentication
# ==========================================

@app.route("/")
def index():
    return redirect(url_for("home")) if "user" in session else redirect(url_for("login"))


@app.route("/login")
def login():
    if "user" in session:
        return redirect(url_for("home"))
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login_user():
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    connection = get_db_connection()
    user = connection.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    connection.close()

    if user and check_password_hash(user["password"], password):
        session["user"] = user["first_name"]
        session["email"] = user["email"]
        session["role"] = user["role"]
        session.permanent = "remember" in request.form
        return redirect(url_for("home"))

    flash("Incorrect email or password.")
    return redirect(url_for("login"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/register")
def register():
    if "user" in session:
        return redirect(url_for("home"))
    return render_template("register.html")


@app.route("/register", methods=["POST"])
def register_user():
    first_name = request.form.get("first_name", "").strip()
    last_name = request.form.get("last_name", "").strip()
    email = request.form.get("email", "").strip().lower()
    phone = request.form.get("phone", "").strip()
    street = request.form.get("street", "").strip()
    suburb = request.form.get("suburb", "").strip()
    state = request.form.get("state", "").strip()
    postcode = request.form.get("postcode", "").strip()
    favourite_cake = request.form.get("favourite_cake", "")
    dietary = request.form.get("dietary", "None")
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")
    marketing = 1 if "marketing" in request.form else 0

    if not all([first_name, last_name, email, phone, street, suburb, state, postcode, password]):
        flash("Please complete all required fields.")
        return redirect(url_for("register"))

    if password != confirm_password:
        flash("Passwords do not match.")
        return redirect(url_for("register"))

    if len(password) < 8:
        flash("Password must contain at least 8 characters.")
        return redirect(url_for("register"))

    connection = get_db_connection()
    if connection.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone():
        connection.close()
        flash("Email already registered.")
        return redirect(url_for("register"))

    connection.execute("""
        INSERT INTO users (
            first_name, last_name, email, phone, password, street, suburb,
            state, postcode, favourite_cake, dietary, marketing, role
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Customer')
    """, (
        first_name, last_name, email, phone, generate_password_hash(password),
        street, suburb, state, postcode, favourite_cake, dietary, marketing
    ))
    connection.commit()
    connection.close()

    flash("Account created successfully. Please log in.")
    return redirect(url_for("login"))


# ==========================================
# Home and products
# ==========================================

@app.route("/home")
@login_required
def home():
    connection = get_db_connection()
    featured_products = connection.execute("""
        SELECT * FROM products
        WHERE is_active = 1
        ORDER BY id ASC
        LIMIT 3
    """).fetchall()
    connection.close()
    return render_template("home.html", username=session["user"], featured_products=featured_products)


@app.route("/products")
@login_required
def products():
    search = request.args.get("search", "").strip()
    category = request.args.get("category", "All").strip()
    price_range = request.args.get("price", "All").strip()
    sort = request.args.get("sort", "name").strip()

    sql = "SELECT * FROM products WHERE is_active = 1"
    values = []

    if search:
        sql += " AND (name LIKE ? OR description LIKE ? OR category LIKE ?)"
        term = f"%{search}%"
        values.extend([term, term, term])

    if category and category != "All":
        sql += " AND category = ?"
        values.append(category)

    if price_range == "under-75":
        sql += " AND price < 75"
    elif price_range == "75-85":
        sql += " AND price >= 75 AND price <= 85"
    elif price_range == "over-85":
        sql += " AND price > 85"

    sort_options = {
        "name": "name ASC",
        "price-low": "price ASC",
        "price-high": "price DESC",
        "stock": "stock DESC",
    }
    sql += " ORDER BY " + sort_options.get(sort, "name ASC")

    connection = get_db_connection()
    product_records = connection.execute(sql, values).fetchall()
    categories = connection.execute("""
        SELECT DISTINCT category FROM products
        WHERE is_active = 1
        ORDER BY category
    """).fetchall()
    connection.close()

    return render_template(
        "products.html",
        username=session["user"],
        products=product_records,
        categories=categories,
        search=search,
        selected_category=category,
        selected_price=price_range,
        selected_sort=sort,
    )


@app.route("/product/<int:product_id>")
@login_required
def product_details(product_id):
    connection = get_db_connection()
    product = connection.execute(
        "SELECT * FROM products WHERE id = ? AND is_active = 1",
        (product_id,)
    ).fetchone()

    if product:
        related = connection.execute("""
            SELECT * FROM products
            WHERE category = ? AND id != ? AND is_active = 1
            LIMIT 3
        """, (product["category"], product_id)).fetchall()
    else:
        related = []

    connection.close()

    if product is None:
        flash("Product could not be found.")
        return redirect(url_for("products"))

    return render_template(
        "product_details.html",
        username=session["user"],
        product=product,
        related=related,
    )


# ==========================================
# Shopping cart
# ==========================================

@app.route("/add-to-cart/<int:product_id>", methods=["GET", "POST"])
@login_required
def add_to_cart(product_id):
    quantity = request.form.get("quantity", 1, type=int) if request.method == "POST" else 1
    quantity = max(1, min(quantity or 1, 20))
    next_url = request.form.get("next", "") if request.method == "POST" else ""
    if not (next_url.startswith("/") and not next_url.startswith("//")):
        next_url = url_for("products")

    connection = get_db_connection()
    product = connection.execute(
        "SELECT id, name, stock FROM products WHERE id = ? AND is_active = 1",
        (product_id,)
    ).fetchone()

    if product is None:
        connection.close()
        flash("That product could not be found.")
        return redirect(url_for("products"))

    existing = connection.execute("""
        SELECT * FROM cart WHERE user_email = ? AND product_id = ?
    """, (session["email"], product_id)).fetchone()

    existing_quantity = existing["quantity"] if existing else 0
    new_quantity = existing_quantity + quantity

    if product["stock"] <= 0:
        connection.close()
        flash("This cake is currently sold out.")
        return redirect(request.referrer or url_for("products"))

    adjusted = False
    if new_quantity > product["stock"]:
        new_quantity = product["stock"]
        adjusted = True
        flash(f"Only {product['stock']} are currently available, so your cart was adjusted.")

    if existing:
        connection.execute("UPDATE cart SET quantity = ? WHERE id = ?", (new_quantity, existing["id"]))
    else:
        connection.execute("""
            INSERT INTO cart (user_email, product_id, quantity) VALUES (?, ?, ?)
        """, (session["email"], product_id, new_quantity))

    connection.commit()
    connection.close()

    if not adjusted:
        flash(f"{product['name']} added to your cart.")
    return redirect(next_url)


@app.route("/cart")
@login_required
def cart():
    product_items, custom_items, subtotal = get_cart_data(session["email"])
    return render_template(
        "cart.html",
        username=session["user"],
        cart_items=product_items,
        custom_items=custom_items,
        total=subtotal,
    )


@app.route("/cart/update/<int:cart_id>", methods=["POST"])
@login_required
def update_cart(cart_id):
    action = request.form.get("action", "")
    connection = get_db_connection()
    item = connection.execute("""
        SELECT cart.*, products.stock
        FROM cart
        JOIN products ON cart.product_id = products.id
        WHERE cart.id = ? AND cart.user_email = ?
    """, (cart_id, session["email"])).fetchone()

    if item:
        if action == "increase":
            new_quantity = min(item["quantity"] + 1, item["stock"])
            connection.execute("UPDATE cart SET quantity = ? WHERE id = ?", (new_quantity, cart_id))
        elif action == "decrease":
            if item["quantity"] <= 1:
                connection.execute("DELETE FROM cart WHERE id = ?", (cart_id,))
            else:
                connection.execute("UPDATE cart SET quantity = quantity - 1 WHERE id = ?", (cart_id,))

    connection.commit()
    connection.close()
    return redirect(url_for("cart"))


@app.route("/remove-from-cart/<int:cart_id>", methods=["POST", "GET"])
@login_required
def remove_from_cart(cart_id):
    connection = get_db_connection()
    connection.execute(
        "DELETE FROM cart WHERE id = ? AND user_email = ?",
        (cart_id, session["email"])
    )
    connection.commit()
    connection.close()
    flash("Cake removed from cart.")
    return redirect(url_for("cart"))


@app.route("/custom-cart/update/<int:cart_id>", methods=["POST"])
@login_required
def update_custom_cart(cart_id):
    action = request.form.get("action", "")
    connection = get_db_connection()
    item = connection.execute(
        "SELECT * FROM custom_cart WHERE id = ? AND user_email = ?",
        (cart_id, session["email"])
    ).fetchone()

    if item:
        if action == "increase":
            connection.execute("UPDATE custom_cart SET quantity = quantity + 1 WHERE id = ?", (cart_id,))
        elif action == "decrease":
            if item["quantity"] <= 1:
                connection.execute("DELETE FROM custom_cart WHERE id = ?", (cart_id,))
            else:
                connection.execute("UPDATE custom_cart SET quantity = quantity - 1 WHERE id = ?", (cart_id,))

    connection.commit()
    connection.close()
    return redirect(url_for("cart"))


@app.route("/remove-custom-from-cart/<int:cart_id>", methods=["POST", "GET"])
@login_required
def remove_custom_from_cart(cart_id):
    connection = get_db_connection()
    connection.execute(
        "DELETE FROM custom_cart WHERE id = ? AND user_email = ?",
        (cart_id, session["email"])
    )
    connection.commit()
    connection.close()
    flash("Custom cake removed from cart.")
    return redirect(url_for("cart"))


# ==========================================
# Custom cake builder
# ==========================================

@app.route("/custom-cakes", methods=["GET", "POST"])
@login_required
def custom_cakes():
    if request.method == "POST":
        size = request.form.get("size", "")
        flavour = request.form.get("flavour", "")
        filling = request.form.get("filling", "")
        frosting = request.form.get("frosting", "")
        shape = request.form.get("shape", "Round")
        dietary = request.form.get("dietary", "Standard")
        colour = request.form.get("colour", "#D7A98C")
        decorations = request.form.getlist("decorations")
        cake_message = request.form.get("cake_message", "").strip()[:80]
        notes = request.form.get("notes", "").strip()[:800]
        event_date = request.form.get("event_date", "")
        action = request.form.get("action", "add")

        try:
            price = calculate_custom_cake_price(
                size, flavour, filling, frosting, shape, dietary, decorations
            )
        except ValueError:
            flash("Please choose valid options for your custom cake.")
            return redirect(url_for("custom_cakes"))

        if event_date:
            try:
                selected_date = date.fromisoformat(event_date)
                if selected_date < date.today():
                    flash("The event date cannot be in the past.")
                    return redirect(url_for("custom_cakes"))
            except ValueError:
                flash("Please choose a valid event date.")
                return redirect(url_for("custom_cakes"))

        servings = SIZE_SERVINGS.get(size, "")
        decorations_text = ", ".join(decorations) if decorations else "None"

        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("""
            INSERT INTO custom_cakes (
                user_email, size, flavour, filling, frosting, colour,
                decorations, cake_message, notes, estimated_price,
                shape, dietary, event_date, servings, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session["email"], size, flavour, filling, frosting, colour,
            decorations_text, cake_message, notes, price, shape, dietary,
            event_date, servings, datetime.now().isoformat(timespec="seconds")
        ))
        custom_cake_id = cursor.lastrowid

        if action == "add":
            cursor.execute("""
                INSERT INTO custom_cart (user_email, custom_cake_id, quantity)
                VALUES (?, ?, 1)
            """, (session["email"], custom_cake_id))

        connection.commit()
        connection.close()

        if action == "add":
            flash("Your custom cake was created and added to the cart.")
            return redirect(url_for("cart"))

        flash("Your custom cake design was saved.")
        return redirect(url_for("custom_cakes"))

    connection = get_db_connection()
    saved_designs = connection.execute("""
        SELECT * FROM custom_cakes
        WHERE user_email = ?
        ORDER BY id DESC
        LIMIT 6
    """, (session["email"],)).fetchall()
    connection.close()

    pricing = {
        "sizes": SIZE_PRICES,
        "flavours": FLAVOUR_PRICES,
        "fillings": FILLING_PRICES,
        "frostings": FROSTING_PRICES,
        "shapes": SHAPE_PRICES,
        "dietary": DIETARY_PRICES,
        "decorations": DECORATION_PRICES,
    }

    return render_template(
        "custom_cakes.html",
        username=session["user"],
        saved_designs=saved_designs,
        pricing=pricing,
        today=date.today().isoformat(),
    )


@app.route("/custom-cakes/<int:custom_cake_id>/add", methods=["POST"])
@login_required
def add_saved_custom_cake(custom_cake_id):
    connection = get_db_connection()
    design = connection.execute("""
        SELECT id FROM custom_cakes WHERE id = ? AND user_email = ?
    """, (custom_cake_id, session["email"])).fetchone()

    if design:
        connection.execute("""
            INSERT INTO custom_cart (user_email, custom_cake_id, quantity)
            VALUES (?, ?, 1)
        """, (session["email"], custom_cake_id))
        connection.commit()
        flash("Saved custom cake added to your cart.")
    else:
        flash("That saved design could not be found.")

    connection.close()
    return redirect(url_for("cart"))


# ==========================================
# Checkout and orders
# ==========================================

@app.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    user = get_logged_in_user()
    product_items, custom_items, subtotal = get_cart_data(session["email"])

    if not product_items and not custom_items:
        flash("Your cart is empty.")
        return redirect(url_for("cart"))

    if request.method == "POST":
        delivery_method = request.form.get("delivery_method", "Pickup")
        customer_name = request.form.get("customer_name", "").strip()
        phone = request.form.get("phone", "").strip()
        street = request.form.get("street", "").strip()
        suburb = request.form.get("suburb", "").strip()
        state = request.form.get("state", "").strip()
        postcode = request.form.get("postcode", "").strip()
        requested_date = request.form.get("requested_date", "")
        notes = request.form.get("notes", "").strip()[:800]
        payment_method = request.form.get("payment_method", "Pay on pickup/delivery")

        if delivery_method not in ["Pickup", "Delivery"]:
            flash("Please choose pickup or delivery.")
            return redirect(url_for("checkout"))

        if not customer_name or not phone:
            flash("Please enter your name and phone number.")
            return redirect(url_for("checkout"))

        if delivery_method == "Delivery" and not all([street, suburb, state, postcode]):
            flash("Please complete the delivery address.")
            return redirect(url_for("checkout"))

        if requested_date:
            try:
                if date.fromisoformat(requested_date) < date.today():
                    flash("The requested date cannot be in the past.")
                    return redirect(url_for("checkout"))
            except ValueError:
                flash("Please enter a valid requested date.")
                return redirect(url_for("checkout"))

        # Check stock again immediately before creating the order
        for item in product_items:
            if item["quantity"] > item["stock"]:
                flash(f"There is not enough stock available for {item['name']}. Please update your cart.")
                return redirect(url_for("cart"))

        delivery_fee = DELIVERY_FEE if delivery_method == "Delivery" else 0
        total = round(subtotal + delivery_fee, 2)

        if product_items and custom_items:
            order_type = "Standard + Custom"
        elif custom_items:
            order_type = "Custom Cake"
        else:
            order_type = "Standard Order"

        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            cursor.execute("BEGIN")
            cursor.execute("""
                INSERT INTO orders (
                    user_email, order_date, status, order_type, delivery_method,
                    total, customer_name, phone, street, suburb, state, postcode,
                    requested_date, notes, delivery_fee, payment_method
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session["email"], datetime.now().isoformat(timespec="seconds"),
                "Order Placed", order_type, delivery_method, total, customer_name,
                phone, street, suburb, state, postcode, requested_date, notes,
                delivery_fee, payment_method
            ))
            order_id = cursor.lastrowid

            for item in product_items:
                cursor.execute("""
                    INSERT INTO order_items (
                        order_id, product_id, quantity, price, product_name, image
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    order_id, item["product_id"], item["quantity"], item["price"],
                    item["name"], item["image"]
                ))
                cursor.execute("""
                    UPDATE products SET stock = stock - ? WHERE id = ?
                """, (item["quantity"], item["product_id"]))

            for item in custom_items:
                cursor.execute("""
                    INSERT INTO custom_order_items (
                        order_id, custom_cake_id, quantity, price, size, flavour,
                        filling, frosting, colour, decorations, cake_message,
                        notes, shape, dietary, event_date
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    order_id, item["id"], item["quantity"], item["estimated_price"],
                    item["size"], item["flavour"], item["filling"], item["frosting"],
                    item["colour"], item["decorations"], item["cake_message"],
                    item["notes"], item["shape"], item["dietary"], item["event_date"]
                ))

            cursor.execute("DELETE FROM cart WHERE user_email = ?", (session["email"],))
            cursor.execute("DELETE FROM custom_cart WHERE user_email = ?", (session["email"],))
            connection.commit()
        except Exception:
            connection.rollback()
            connection.close()
            flash("The order could not be placed. Please try again.")
            return redirect(url_for("checkout"))

        connection.close()
        flash(f"Order #{order_id} has been placed successfully.")
        return redirect(url_for("order_details", order_id=order_id))

    return render_template(
        "checkout.html",
        username=session["user"],
        user=user,
        cart_items=product_items,
        custom_items=custom_items,
        subtotal=subtotal,
        delivery_fee=DELIVERY_FEE,
        today=date.today().isoformat(),
    )


@app.route("/orders")
@login_required
def orders():
    connection = get_db_connection()
    order_records = connection.execute("""
        SELECT * FROM orders
        WHERE user_email = ?
        ORDER BY id DESC
    """, (session["email"],)).fetchall()

    active_orders = connection.execute("""
        SELECT COUNT(*) FROM orders
        WHERE user_email = ? AND status NOT IN ('Completed', 'Cancelled')
    """, (session["email"],)).fetchone()[0]

    completed_orders = connection.execute("""
        SELECT COUNT(*) FROM orders
        WHERE user_email = ? AND status = 'Completed'
    """, (session["email"],)).fetchone()[0]
    connection.close()

    return render_template(
        "orders.html",
        username=session["user"],
        orders=order_records,
        active_orders=active_orders,
        completed_orders=completed_orders,
    )


@app.route("/orders/<int:order_id>")
@login_required
def order_details(order_id):
    connection = get_db_connection()
    if session.get("role") == "Admin":
        order = connection.execute(
            "SELECT * FROM orders WHERE id = ?",
            (order_id,)
        ).fetchone()
    else:
        order = connection.execute("""
            SELECT * FROM orders WHERE id = ? AND user_email = ?
        """, (order_id, session["email"])).fetchone()

    if order is None:
        connection.close()
        flash("That order could not be found.")
        return redirect(url_for("orders"))

    product_items = connection.execute("""
        SELECT * FROM order_items WHERE order_id = ? ORDER BY id
    """, (order_id,)).fetchall()

    custom_items = connection.execute("""
        SELECT * FROM custom_order_items WHERE order_id = ? ORDER BY id
    """, (order_id,)).fetchall()
    connection.close()

    return render_template(
        "order_details.html",
        username=session["user"],
        order=order,
        product_items=product_items,
        custom_items=custom_items,
    )


# ==========================================
# SmartBake AI
# ==========================================

@app.route("/smartbake")
@login_required
def smartbake():
    connection = get_db_connection()
    history = connection.execute("""
        SELECT role, content FROM smartbake_messages
        WHERE user_email = ?
        ORDER BY id DESC
        LIMIT 12
    """, (session["email"],)).fetchall()
    connection.close()

    history = list(reversed(history))
    ai_configured = bool(os.getenv("OPENAI_API_KEY")) and OpenAI is not None

    return render_template(
        "smartbake.html",
        username=session["user"],
        history=history,
        ai_configured=ai_configured,
    )


@app.route("/api/smartbake", methods=["POST"])
@login_required
def smartbake_api():
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()

    if not message:
        return jsonify({"error": "Please enter a message."}), 400

    if len(message) > 1200:
        return jsonify({"error": "Please keep your message under 1200 characters."}), 400

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or OpenAI is None:
        return jsonify({
            "error": "SmartBake AI is not configured yet. Add OPENAI_API_KEY to your .env file and restart BakeFlow."
        }), 503

    connection = get_db_connection()
    user = connection.execute("SELECT * FROM users WHERE email = ?", (session["email"],)).fetchone()
    products = connection.execute("""
        SELECT name, category, description, price, stock
        FROM products WHERE is_active = 1
        ORDER BY name
    """).fetchall()
    history = connection.execute("""
        SELECT role, content FROM smartbake_messages
        WHERE user_email = ?
        ORDER BY id DESC
        LIMIT 10
    """, (session["email"],)).fetchall()

    product_text = "\n".join(
        f"- {item['name']} ({item['category']}): ${item['price']:.2f}, stock {item['stock']}. {item['description']}"
        for item in products
    )

    history_text = "\n".join(
        f"{row['role'].title()}: {row['content']}" for row in reversed(history)
    )

    dietary = user["dietary"] or "None"
    favourite = user["favourite_cake"] or "Not provided"

    instructions = f"""
You are SmartBake, the helpful cake recommendation assistant for Sweet Souls Bakery inside the BakeFlow website.
Keep answers friendly, practical and fairly concise.
Recommend items from the current product list when they match the customer's request, and include prices when useful.
You may also suggest a custom cake using the builder options: Vanilla, Chocolate, Red Velvet, Lotus Biscoff or Strawberry flavours; 6, 8 or 10 inch sizes; Round, Square or Heart shapes.
The customer's saved favourite cake is: {favourite}.
The customer's saved dietary requirement is: {dietary}.
Never claim that a cake is definitely safe for an allergy or free from cross-contamination. If allergies are mentioned, tell the customer to confirm ingredients and cross-contamination risks directly with Sweet Souls Bakery.
Do not invent products, prices or stock levels that are not in the supplied catalogue.

Current catalogue:
{product_text}
""".strip()

    conversation_input = history_text
    if conversation_input:
        conversation_input += "\n"
    conversation_input += f"Customer: {message}\nSmartBake:"

    try:
        client = OpenAI(api_key=api_key)
        response = client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
            instructions=instructions,
            input=conversation_input,
        )
        reply = (response.output_text or "").strip()
    except Exception:
        connection.close()
        return jsonify({"error": "SmartBake could not reach the AI service. Please try again shortly."}), 502

    if not reply:
        connection.close()
        return jsonify({"error": "SmartBake did not return a response. Please try again."}), 502

    connection.execute("""
        INSERT INTO smartbake_messages (user_email, role, content)
        VALUES (?, 'user', ?)
    """, (session["email"], message))
    connection.execute("""
        INSERT INTO smartbake_messages (user_email, role, content)
        VALUES (?, 'assistant', ?)
    """, (session["email"], reply))
    connection.commit()
    connection.close()

    return jsonify({"reply": reply})


@app.route("/smartbake/clear", methods=["POST"])
@login_required
def clear_smartbake():
    connection = get_db_connection()
    connection.execute("DELETE FROM smartbake_messages WHERE user_email = ?", (session["email"],))
    connection.commit()
    connection.close()
    flash("SmartBake conversation cleared.")
    return redirect(url_for("smartbake"))


# ==========================================
# Contact page
# ==========================================

@app.route("/contact", methods=["GET", "POST"])
@login_required
def contact():
    user = get_logged_in_user()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        subject = request.form.get("subject", "").strip()
        message = request.form.get("message", "").strip()

        if not all([name, email, subject, message]):
            flash("Please complete every contact form field.")
            return redirect(url_for("contact"))

        connection = get_db_connection()
        connection.execute("""
            INSERT INTO contact_messages (user_email, name, email, subject, message)
            VALUES (?, ?, ?, ?, ?)
        """, (session["email"], name, email, subject[:120], message[:1500]))
        connection.commit()
        connection.close()

        flash("Your message has been sent to Sweet Souls Bakery.")
        return redirect(url_for("contact"))

    return render_template("contact.html", username=session["user"], user=user)


# ==========================================
# Administrator dashboard
# ==========================================

@app.route("/admin")
@admin_required
def admin_dashboard():
    connection = get_db_connection()

    metrics = {
        "total_orders": connection.execute("SELECT COUNT(*) FROM orders").fetchone()[0],
        "active_orders": connection.execute(
            "SELECT COUNT(*) FROM orders WHERE status NOT IN ('Completed', 'Cancelled')"
        ).fetchone()[0],
        "revenue": connection.execute(
            "SELECT COALESCE(SUM(total), 0) FROM orders WHERE status != 'Cancelled'"
        ).fetchone()[0],
        "low_stock": connection.execute(
            "SELECT COUNT(*) FROM products WHERE stock <= ? AND is_active = 1",
            (LOW_STOCK_LEVEL,)
        ).fetchone()[0],
        "unread_messages": connection.execute(
            "SELECT COUNT(*) FROM contact_messages WHERE is_read = 0"
        ).fetchone()[0],
    }

    recent_orders = connection.execute("""
        SELECT * FROM orders ORDER BY id DESC LIMIT 12
    """).fetchall()

    inventory = connection.execute("""
        SELECT * FROM products ORDER BY stock ASC, name ASC
    """).fetchall()

    messages = connection.execute("""
        SELECT * FROM contact_messages ORDER BY id DESC LIMIT 10
    """).fetchall()

    connection.close()

    return render_template(
        "admin.html",
        username=session["user"],
        metrics=metrics,
        recent_orders=recent_orders,
        inventory=inventory,
        messages=messages,
        statuses=ORDER_STATUSES,
        low_stock_level=LOW_STOCK_LEVEL,
    )


@app.route("/admin/order/<int:order_id>/status", methods=["POST"])
@admin_required
def admin_update_order_status(order_id):
    status = request.form.get("status", "")
    if status not in ORDER_STATUSES:
        flash("Invalid order status.")
        return redirect(url_for("admin_dashboard"))

    connection = get_db_connection()
    current_order = connection.execute(
        "SELECT status FROM orders WHERE id = ?",
        (order_id,)
    ).fetchone()

    if current_order is None:
        connection.close()
        flash("Order could not be found.")
        return redirect(url_for("admin_dashboard"))

    old_status = current_order["status"]

    # Return standard product stock when an order is cancelled.
    if status == "Cancelled" and old_status != "Cancelled":
        order_items = connection.execute(
            "SELECT product_id, quantity FROM order_items WHERE order_id = ?",
            (order_id,)
        ).fetchall()
        for item in order_items:
            if item["product_id"] is not None:
                connection.execute(
                    "UPDATE products SET stock = stock + ? WHERE id = ?",
                    (item["quantity"], item["product_id"])
                )

    # If a cancelled order is reopened, make sure stock is still available.
    if old_status == "Cancelled" and status != "Cancelled":
        order_items = connection.execute(
            "SELECT product_id, quantity FROM order_items WHERE order_id = ?",
            (order_id,)
        ).fetchall()

        for item in order_items:
            if item["product_id"] is None:
                continue
            product = connection.execute(
                "SELECT stock, name FROM products WHERE id = ?",
                (item["product_id"],)
            ).fetchone()
            if product is None or product["stock"] < item["quantity"]:
                connection.close()
                flash("This cancelled order cannot be reopened because there is not enough product stock.")
                return redirect(url_for("admin_dashboard"))

        for item in order_items:
            if item["product_id"] is not None:
                connection.execute(
                    "UPDATE products SET stock = stock - ? WHERE id = ?",
                    (item["quantity"], item["product_id"])
                )

    connection.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
    connection.commit()
    connection.close()
    flash(f"Order #{order_id} updated to {status}.")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/product/<int:product_id>/stock", methods=["POST"])
@admin_required
def admin_update_stock(product_id):
    stock = request.form.get("stock", type=int)
    if stock is None or stock < 0 or stock > 999:
        flash("Stock must be between 0 and 999.")
        return redirect(url_for("admin_dashboard"))

    connection = get_db_connection()
    connection.execute("UPDATE products SET stock = ? WHERE id = ?", (stock, product_id))
    connection.commit()
    connection.close()
    flash("Inventory updated.")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/message/<int:message_id>/read", methods=["POST"])
@admin_required
def admin_mark_message_read(message_id):
    connection = get_db_connection()
    connection.execute("UPDATE contact_messages SET is_read = 1 WHERE id = ?", (message_id,))
    connection.commit()
    connection.close()
    return redirect(url_for("admin_dashboard"))


# ==========================================
# Run application
# ==========================================

create_database()

if __name__ == "__main__":
    app.run(debug=True)
 