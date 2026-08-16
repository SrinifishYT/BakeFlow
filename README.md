# BakeFlow

BakeFlow is a Flask + SQLite ordering system for Sweet Souls Bakery.

## Included features

- Customer registration and secure password hashing
- Login/logout and customer sessions
- Product catalogue with search, category filters, price filters and sorting
- Product details and stock availability
- Shopping cart with quantity controls
- Custom Cake Builder with live preview and automatic price estimate
- Saved custom cake designs
- Checkout with pickup or delivery
- Order creation, order history and order detail pages
- Order status tracking
- SmartBake AI assistant using the OpenAI Responses API
- Contact form stored in the database
- Administrator dashboard for order statuses, stock and customer messages
- Shared `base.html` navigation so navbar links only need to be changed in one file

## Project structure

```text
BakeFlow-main/
├── app.py
├── bakeflow.db
├── requirements.txt
├── .env.example
├── static/
│   ├── css/
│   ├── images/
│   └── js/
└── templates/
```

## 1. Install Python packages

Open a terminal inside the project folder and run:

```bash
python -m pip install -r requirements.txt
```

## 2. Set up SmartBake AI

Create a file called `.env` in the same folder as `app.py`.

Copy the contents of `.env.example` into it and replace the example OpenAI key with your own key:

```text
BAKEFLOW_SECRET_KEY=choose-a-long-random-secret
OPENAI_API_KEY=your-real-key-here
OPENAI_MODEL=gpt-5-mini
```

Do not put a real API key directly inside `app.py`, JavaScript, HTML or GitHub.

If no API key is configured, the rest of BakeFlow still works and the SmartBake page explains that API setup is required.

## 3. Run BakeFlow

```bash
python app.py
```

Then open the local Flask address shown in the terminal, normally:

```text
http://127.0.0.1:5000
```

## Administrator account

A default administrator account is created if one does not already exist:

```text
Email: admin@sweetsouls.com
Password: Admin123
```

Change the password before using this outside a school prototype.

## Database

`create_database()` runs when BakeFlow starts. It creates missing tables and adds missing columns to older BakeFlow databases, so the existing database can be upgraded without deleting customer accounts.

## Payment note

This school prototype does not collect or store card numbers. Checkout records the order and allows payment to be arranged with Sweet Souls Bakery.
