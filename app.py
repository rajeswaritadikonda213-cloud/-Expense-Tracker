from flask import Flask, render_template, request, redirect, url_for, send_file, flash
import json
from datetime import datetime
import os
from io import BytesIO
import csv

app = Flask(__name__)
app.secret_key = "replace-with-a-secure-random-key"  # for flash messages

FILENAME = "expenses.json"

def load_expenses():
    if not os.path.exists(FILENAME):
        return []
    with open(FILENAME, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_expenses(expenses):
    with open(FILENAME, "w") as f:
        json.dump(expenses, f, indent=4)

def get_totals(expenses):
    total = sum(e["amount"] for e in expenses)
    by_cat = {}
    for e in expenses:
        by_cat[e["category"]] = by_cat.get(e["category"], 0) + e["amount"]
    return total, by_cat

@app.route("/")
def index():
    expenses = load_expenses()
    total, by_cat = get_totals(expenses)
    # Show recent 10
    recent = sorted(expenses, key=lambda x: x["date"], reverse=True)[:10]
    return render_template("index.html", expenses=recent, total=total, by_cat=by_cat)

@app.route("/all")
def all_expenses():
    expenses = load_expenses()
    # sort by date descending
    expenses_sorted = sorted(expenses, key=lambda x: x["date"], reverse=True)
    return render_template("all.html", expenses=expenses_sorted)

@app.route("/add", methods=["GET", "POST"])
def add_expense():
    if request.method == "POST":
        try:
            amount = float(request.form["amount"])
            category = request.form.get("category", "").strip().capitalize() or "Other"
            date = request.form.get("date")
            if not date:
                date = datetime.now().strftime("%Y-%m-%d")
            note = request.form.get("note", "").strip()

            expenses = load_expenses()
            expenses.append({
                "id": int(datetime.now().timestamp() * 1000),  # simple unique id
                "amount": amount,
                "category": category,
                "date": date,
                "note": note
            })
            save_expenses(expenses)
            flash("Expense added successfully.", "success")
            return redirect(url_for("index"))
        except ValueError:
            flash("Invalid amount. Please enter a number.", "danger")
            return redirect(url_for("add_expense"))
    return render_template("add.html")

@app.route("/edit/<int:expense_id>", methods=["GET", "POST"])
def edit_expense(expense_id):
    expenses = load_expenses()
    exp = next((e for e in expenses if e.get("id") == expense_id), None)
    if not exp:
        flash("Expense not found.", "danger")
        return redirect(url_for("all_expenses"))

    if request.method == "POST":
        try:
            amount = float(request.form["amount"])
            category = request.form.get("category", "").strip().capitalize() or "Other"
            date = request.form.get("date") or exp["date"]
            note = request.form.get("note", "").strip()

            exp["amount"] = amount
            exp["category"] = category
            exp["date"] = date
            exp["note"] = note
            save_expenses(expenses)
            flash("Expense updated.", "success")
            return redirect(url_for("all_expenses"))
        except ValueError:
            flash("Invalid amount. Please enter a number.", "danger")
            return redirect(url_for("edit_expense", expense_id=expense_id))

    return render_template("edit.html", expense=exp)

@app.route("/delete/<int:expense_id>", methods=["POST"])
def delete_expense(expense_id):
    expenses = load_expenses()
    new = [e for e in expenses if e.get("id") != expense_id]
    if len(new) == len(expenses):
        flash("Expense not found.", "danger")
    else:
        save_expenses(new)
        flash("Expense deleted.", "success")
    return redirect(url_for("all_expenses"))

@app.route("/summary")
def summary():
    expenses = load_expenses()
    total, by_cat = get_totals(expenses)
    # prepare monthly totals
    monthly = {}
    for e in expenses:
        # ensure date string and get month
        month = e.get("date", "")[:7]  # YYYY-MM
        monthly[month] = monthly.get(month, 0) + e["amount"]
    monthly_list = sorted(monthly.items(), reverse=True)
    return render_template("summary.html", total=total, by_cat=by_cat, monthly=monthly_list)

@app.route("/download/json")
def download_json():
    if not os.path.exists(FILENAME):
        flash("No expense file to download.", "danger")
        return redirect(url_for("index"))
    return send_file(FILENAME, as_attachment=True)

@app.route("/download/csv")
def download_csv():
    expenses = load_expenses()
    if not expenses:
        flash("No expenses to export.", "danger")
        return redirect(url_for("index"))
    mem = BytesIO()
    writer = csv.writer(mem)
    writer.writerow(["id", "date", "category", "amount", "note"])
    for e in expenses:
        writer.writerow([e.get("id"), e.get("date"), e.get("category"), e.get("amount"), e.get("note", "")])
    mem.seek(0)
    return send_file(mem, mimetype="text/csv", download_name="expenses.csv", as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
