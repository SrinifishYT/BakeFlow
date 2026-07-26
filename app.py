from flask import Flask, render_template, request, redirect, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

# Creates the Flask application
app = Flask(__name__)

# Secret key used to store session data securely
app.secret_key = "BakeFlowSecretKey2026"

# Name of the SQLite database file
DATABASE = "bakeflow.db"


# ==========================================
# Connect to the database
# ==========================================

# This function connects to the SQLite database
# and allows the data to be accessed by column names.

# ==========================================
# Create Database
# ==========================================

# ==========================================
# Connect to the database
# ==========================================

# This function connects to the SQLite database
# and allows the data to be accessed by column names.

def get_db_connection():

    connection = sqlite3.connect(DATABASE)

    connection.row_factory = sqlite3.Row

    return connection

def create_database():

    connection = get_db_connection()
    cursor = connection.cursor()

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

    connection.commit()

    # Check whether the admin account already exists

    cursor.execute(
        "SELECT * FROM users WHERE email=?",
        ("admin@sweetsouls.com",)
    )

    admin = cursor.fetchone()

    # Create the admin account the first time
    if admin is None:

        hashed_password = generate_password_hash("Admin123")

        cursor.execute("""

        INSERT INTO users(

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

        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)

        """,(

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

        connection.commit()

    connection.close()


# ==========================================
# Home Route
# ==========================================

# Opens the application.
# If the user is already logged in they are
# taken to the homepage, otherwise they are
# redirected to the login page.
@app.route("/")
def index():

    if "user" in session:
        return redirect("/home")

    return redirect("/login")


# ==========================================
# Login Page
# ==========================================

# Displays the login page.
@app.route("/login")
def login():

    return render_template("login.html")


# ==========================================
# Login Authentication
# ==========================================

# Receives the login details entered by the user.
# It checks if the email exists and if the password
# matches the one stored in the database.
@app.route("/login", methods=["POST"])
def login_user():

    email = request.form["email"]
    password = request.form["password"]

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(
        "SELECT * FROM users WHERE email=?",
        (email,)
    )

    user = cursor.fetchone()

    connection.close()

    # If the account exists and the password is correct,
    # save the user's information into the session.
    if user:

        if check_password_hash(user["password"], password):

            session["user"] = user["first_name"]
            session["role"] = user["role"]

            return redirect("/home")

    # If the login fails, display an error message.
    flash("Incorrect email or password.")

    return redirect("/login")


# ==========================================
# Home Page
# ==========================================

# Displays the home page.
# Users must be logged in before they can
# access this page.
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

# Displays the products page.
# Users must be logged in before they can
# access this page.
@app.route("/products")
def products():

    # Redirect to the login page if the user
    # is not currently logged in.
    if "user" not in session:
        return redirect("/login")

    # Open the products page and pass the
    # username into the HTML template.
    return render_template(
        "products.html",
        username=session["user"]
    )


# ==========================================
# Custom Cakes
# ==========================================

@app.route("/custom-cakes")
def custom_cakes():

    return "<h1>Custom Cake Builder Coming Soon</h1>"


# ==========================================
# SmartBake AI
# ==========================================

@app.route("/smartbake")
def smartbake():

    return "<h1>SmartBake AI Coming Soon</h1>"


# ==========================================
# Orders
# ==========================================

@app.route("/orders")
def orders():

    return "<h1>Orders Page Coming Soon</h1>"


# ==========================================
# Contact
# ==========================================

@app.route("/contact")
def contact():

    return "<h1>Contact Page Coming Soon</h1>"

# ==========================================
# Logout
# ==========================================

# Logs the user out by clearing the session
# before returning them to the login page.
@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


# ==========================================
# Register Page
# ==========================================

@app.route("/register")
def register():

    return render_template("register.html")

# ==========================================
# Register User
# ==========================================

@app.route("/register", methods=["POST"])
def register_user():

    first_name = request.form["first_name"]
    last_name = request.form["last_name"]
    email = request.form["email"]
    phone = request.form["phone"]

    street = request.form["street"]
    suburb = request.form["suburb"]
    state = request.form["state"]
    postcode = request.form["postcode"]

    favourite_cake = request.form["favourite_cake"]
    dietary = request.form["dietary"]

    password = request.form["password"]
    confirm_password = request.form["confirm_password"]

    marketing = 1 if "marketing" in request.form else 0

    # Check passwords match

    if password != confirm_password:

        flash("Passwords do not match.")

        return redirect("/register")

    connection = get_db_connection()
    cursor = connection.cursor()

    # Check email doesn't already exist

    cursor.execute(

        "SELECT * FROM users WHERE email=?",

        (email,)

    )

    existing_user = cursor.fetchone()

    if existing_user:

        connection.close()

        flash("Email already registered.")

        return redirect("/register")

    hashed_password = generate_password_hash(password)

    cursor.execute("""

    INSERT INTO users(

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

    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)

    """,(

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
# Run the Application
# ==========================================

# Creates the database before starting
# the Flask development server.
if __name__ == "__main__":

    create_database()

    app.run(debug=True)