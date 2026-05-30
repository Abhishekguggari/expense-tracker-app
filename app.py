from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, Response
import sqlite3
import os
import csv
import io
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "expense_tracker_secret_key_2026"

DATABASE = os.path.join(os.path.dirname(__file__), "expenses.db")

CATEGORIES = [
    "Food & Dining",
    "Transport",
    "Shopping",
    "Entertainment",
    "Health",
    "Education",
    "Utilities",
    "Rent",
    "Other"
]

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access this page.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            note TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    # Migration: Automatically add user_id column if the database already existed before the auth update
    cursor = conn.execute("PRAGMA table_info(expenses)")
    columns = [col["name"] for col in cursor.fetchall()]
    if "user_id" not in columns:
        conn.execute("ALTER TABLE expenses ADD COLUMN user_id INTEGER DEFAULT 1")
        
    # Migration: Add monthly_budget
    cursor = conn.execute("PRAGMA table_info(users)")
    user_columns = [col["name"] for col in cursor.fetchall()]
    if "monthly_budget" not in user_columns:
        conn.execute("ALTER TABLE users ADD COLUMN monthly_budget REAL DEFAULT 0.0")

    conn.commit()
    conn.close()

# Initialize the database when the application starts
init_db()

@app.route("/")
@login_required
def index():
    category_filter = request.args.get("category", "")
    search_query = request.args.get("q", "").strip()
    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()
    user_id = session["user_id"]
    conn = get_db()
    
    query_base = " FROM expenses WHERE user_id = ?"
    params = [user_id]
    
    if category_filter:
        query_base += " AND category = ?"
        params.append(category_filter)
    if search_query:
        query_base += " AND (title LIKE ? OR note LIKE ?)"
        params.extend([f"%{search_query}%", f"%{search_query}%"])
    if start_date:
        query_base += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query_base += " AND date <= ?"
        params.append(end_date)
        
    expenses = conn.execute("SELECT *" + query_base + " ORDER BY date DESC", params).fetchall()

    total = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) as total FROM expenses WHERE user_id = ?",
        (user_id,)
    ).fetchone()["total"]

    # Calculate Current and Last Month boundaries
    today = datetime.today()
    first_day_current = today.replace(day=1)
    last_day_last_month = first_day_current - timedelta(days=1)
    first_day_last_month = last_day_last_month.replace(day=1)

    current_month_total = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) as total FROM expenses WHERE user_id = ? AND date >= ?",
        (user_id, first_day_current.strftime("%Y-%m-%d"))
    ).fetchone()["total"]

    last_month_total = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) as total FROM expenses WHERE user_id = ? AND date >= ? AND date <= ?",
        (user_id, first_day_last_month.strftime("%Y-%m-%d"), last_day_last_month.strftime("%Y-%m-%d"))
    ).fetchone()["total"]

    filtered_total = sum(e["amount"] for e in expenses)

    category_totals = conn.execute(
        "SELECT category, SUM(amount) as total" + query_base + " GROUP BY category ORDER BY total DESC",
        params
    ).fetchall()

    user = conn.execute("SELECT monthly_budget FROM users WHERE id = ?", (user_id,)).fetchone()
    budget = user["monthly_budget"] if user else 0.0

    conn.close()
    return render_template(
        "index.html",
        expenses=expenses,
        total=total,
        filtered_total=filtered_total,
        categories=CATEGORIES,
        category_filter=category_filter,
        category_totals=category_totals,
        budget=budget,
        search_query=search_query,
        start_date=start_date,
        end_date=end_date,
        current_month_total=current_month_total,
        last_month_total=last_month_total
    )

@app.route("/add", methods=["GET", "POST"])
@login_required
def add_expense():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        amount = request.form.get("amount", "").strip()
        category = request.form.get("category", "").strip()
        date = request.form.get("date", "").strip()
        note = request.form.get("note", "").strip()

        errors = []
        if not title:
            errors.append("Title is required.")
        if not amount:
            errors.append("Amount is required.")
        else:
            try:
                amount = float(amount)
                if amount <= 0:
                    errors.append("Amount must be a positive number.")
            except ValueError:
                errors.append("Amount must be a valid number.")
        if not category:
            errors.append("Category is required.")
        elif category not in CATEGORIES:
            errors.append("Invalid category selected.")
        if not date:
            errors.append("Date is required.")

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("add.html", categories=CATEGORIES, form_data=request.form)

        conn = get_db()
        conn.execute(
            "INSERT INTO expenses (user_id, title, amount, category, date, note) VALUES (?, ?, ?, ?, ?, ?)",
            (session["user_id"], title, amount, category, date, note)
        )
        conn.commit()
        conn.close()

        flash("Expense added successfully!", "success")
        return redirect(url_for("index"))

    return render_template("add.html", categories=CATEGORIES, form_data={})

@app.route("/edit/<int:expense_id>", methods=["GET", "POST"])
@login_required
def edit_expense(expense_id):
    conn = get_db()
    expense = conn.execute("SELECT * FROM expenses WHERE id = ? AND user_id = ?", (expense_id, session["user_id"])).fetchone()
    conn.close()

    if not expense:
        flash("Expense not found.", "error")
        return redirect(url_for("index"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        amount = request.form.get("amount", "").strip()
        category = request.form.get("category", "").strip()
        date = request.form.get("date", "").strip()
        note = request.form.get("note", "").strip()

        errors = []
        if not title:
            errors.append("Title is required.")
        if not amount:
            errors.append("Amount is required.")
        else:
            try:
                amount = float(amount)
                if amount <= 0:
                    errors.append("Amount must be a positive number.")
            except ValueError:
                errors.append("Amount must be a valid number.")
        if not category:
            errors.append("Category is required.")
        elif category not in CATEGORIES:
            errors.append("Invalid category selected.")
        if not date:
            errors.append("Date is required.")

        if errors:
            for error in errors:
                flash(error, "error")
            
            # Preserve user input so form fields don't reset to DB values on error
            expense_data = {
                "id": expense_id,
                "title": title,
                "amount": request.form.get("amount", ""),
                "category": category,
                "date": date,
                "note": note
            }
            return render_template("edit.html", expense=expense_data, categories=CATEGORIES)

        conn = get_db()
        conn.execute(
            "UPDATE expenses SET title=?, amount=?, category=?, date=?, note=? WHERE id=? AND user_id=?",
            (title, amount, category, date, note, expense_id, session["user_id"])
        )
        conn.commit()
        conn.close()

        flash("Expense updated successfully!", "success")
        return redirect(url_for("index"))

    return render_template("edit.html", expense=expense, categories=CATEGORIES)

@app.route("/delete/<int:expense_id>", methods=["POST"])
@login_required
def delete_expense(expense_id):
    conn = get_db()
    conn.execute("DELETE FROM expenses WHERE id = ? AND user_id = ?", (expense_id, session["user_id"]))
    conn.commit()
    conn.close()
    flash("Expense deleted.", "success")
    return redirect(url_for("index"))

@app.route("/api/category-data")
@login_required
def category_data():
    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()
    category_filter = request.args.get("category", "").strip()
    search_query = request.args.get("q", "").strip()
    
    query_base = " FROM expenses WHERE user_id = ?"
    params = [session["user_id"]]
    
    if category_filter:
        query_base += " AND category = ?"
        params.append(category_filter)
    if search_query:
        query_base += " AND (title LIKE ? OR note LIKE ?)"
        params.extend([f"%{search_query}%", f"%{search_query}%"])
    if start_date:
        query_base += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query_base += " AND date <= ?"
        params.append(end_date)

    conn = get_db()
    rows = conn.execute(
        "SELECT category, SUM(amount) as total" + query_base + " GROUP BY category ORDER BY total DESC",
        params
    ).fetchall()
    conn.close()
    return jsonify([{"category": r["category"], "total": round(r["total"], 2)} for r in rows])

@app.route("/api/current-month-category-data")
@login_required
def current_month_category_data():
    today = datetime.today()
    first_day = today.replace(day=1)
    start_date = first_day.strftime("%Y-%m-%d")

    conn = get_db()
    rows = conn.execute(
        "SELECT category, SUM(amount) as total FROM expenses WHERE user_id = ? AND date >= ? GROUP BY category ORDER BY total DESC",
        (session["user_id"], start_date)
    ).fetchall()
    conn.close()
    return jsonify([{"category": r["category"], "total": round(r["total"], 2)} for r in rows])

@app.route("/api/last-month-category-data")
@login_required
def last_month_category_data():
    today = datetime.today()
    first_day_current = today.replace(day=1)
    last_day_last_month = first_day_current - timedelta(days=1)
    first_day_last_month = last_day_last_month.replace(day=1)

    start_date = first_day_last_month.strftime("%Y-%m-%d")
    end_date = last_day_last_month.strftime("%Y-%m-%d")

    conn = get_db()
    rows = conn.execute(
        "SELECT category, SUM(amount) as total FROM expenses WHERE user_id = ? AND date >= ? AND date <= ? GROUP BY category ORDER BY total DESC",
        (session["user_id"], start_date, end_date)
    ).fetchall()
    conn.close()
    return jsonify([{"category": r["category"], "total": round(r["total"], 2)} for r in rows])

@app.route("/export")
@login_required
def export_csv():
    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()
    category_filter = request.args.get("category", "").strip()
    search_query = request.args.get("q", "").strip()
    
    query_base = " FROM expenses WHERE user_id = ?"
    params = [session["user_id"]]
    
    # Apply exactly the same filters from the UI
    if category_filter: query_base += " AND category = ?"; params.append(category_filter)
    if search_query: query_base += " AND (title LIKE ? OR note LIKE ?)"; params.extend([f"%{search_query}%", f"%{search_query}%"])
    if start_date: query_base += " AND date >= ?"; params.append(start_date)
    if end_date: query_base += " AND date <= ?"; params.append(end_date)
    
    conn = get_db()
    expenses = conn.execute("SELECT title, amount, category, date, note" + query_base + " ORDER BY date DESC", params).fetchall()
    conn.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Title", "Amount", "Category", "Date", "Note"])
    for e in expenses:
        writer.writerow([e["title"], e["amount"], e["category"], e["date"], e["note"]])
        
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=expenses.csv"}
    )

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    conn = get_db()
    if request.method == "POST":
        budget = request.form.get("budget", "").strip()
        password = request.form.get("password", "")
        
        try:
            budget_val = float(budget) if budget else 0.0
            if budget_val < 0:
                flash("Budget cannot be negative.", "error")
                return redirect(url_for("profile"))
                
            conn.execute("UPDATE users SET monthly_budget = ? WHERE id = ?", (budget_val, session["user_id"]))
            
            if password:
                hashed_pw = generate_password_hash(password)
                conn.execute("UPDATE users SET password = ? WHERE id = ?", (hashed_pw, session["user_id"]))
                
            conn.commit()
            flash("Account settings updated successfully!", "success")
        except ValueError:
            flash("Invalid budget amount.", "error")
            
    user = conn.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    conn.close()
    return render_template("profile.html", user=user)

@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("index"))
        
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Username and password are required.", "error")
            return render_template("register.html")

        conn = get_db()
        if conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone():
            flash("Username already exists.", "error")
            conn.close()
            return render_template("register.html")

        hashed_pw = generate_password_hash(password)
        conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_pw))
        conn.commit()
        conn.close()

        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("index"))
        
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash(f"Welcome back, {username}!", "success")
            return redirect(url_for("index"))
        
        flash("Invalid username or password.", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
