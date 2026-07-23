from flask import Flask, render_template, request, redirect, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "BakeFlowSecretKey2026"

DATABASE = "bakeflow.db"


# -------------------------------
# Database Connection
# -------------------------------

def get_db_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


# -------------------------------
# Create Database
# -------------------------------

def create_database():

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        first_name TEXT NOT NULL,

        last_name TEXT NOT NULL,

        email TEXT UNIQUE NOT NULL,

        password TEXT NOT NULL,

        role TEXT NOT NULL

    )
    """)

    connection.commit()

    # Create default admin account if it doesn't already exist
    cursor.execute(
        "SELECT * FROM users WHERE email=?",
        ("admin@sweetsouls.com",)
    )

    admin = cursor.fetchone()

    if admin is None:

        hashed_password = generate_password_hash("Admin123")

        cursor.execute("""
        INSERT INTO users
        (first_name, last_name, email, password, role)

        VALUES (?, ?, ?, ?, ?)
        """,
        (
            "Sweet",
            "Souls",
            "admin@sweetsouls.com",
            hashed_password,
            "Admin"
        ))

        connection.commit()

    connection.close()


# -------------------------------
# Routes
# -------------------------------

@app.route("/")
def index():

    if "user" in session:
        return redirect("/home")

    return redirect("/login")


# -------------------------------
# Login Page
# -------------------------------

@app.route("/login")
def login():

    return render_template("login.html")


# -------------------------------
# Login Authentication
# -------------------------------

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

    if user:

        if check_password_hash(user["password"], password):

            session["user"] = user["first_name"]
            session["role"] = user["role"]

            return redirect("/home")

    flash("Incorrect email or password.")
    return redirect("/login")


# -------------------------------
# Home Page
# -------------------------------

@app.route("/home")
def home():

    if "user" not in session:
        return redirect("/login")

    return render_template(
        "home.html",
        username=session["user"]
    )


# -------------------------------
# Logout
# -------------------------------

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


# -------------------------------
# Future Register Page
# -------------------------------

@app.route("/register")
def register():

    return "<h1>Registration Coming Soon</h1>"


# -------------------------------
# Run Application
# -------------------------------

if __name__ == "__main__":

    create_database()

    app.run(debug=True)