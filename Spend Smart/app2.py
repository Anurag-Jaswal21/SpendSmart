from flask import Flask, render_template, redirect, url_for, request, session, flash
from forms import LoginForm, RegistrationForm, ForgotPasswordForm
from config import Config
from db import mysql
from services import check_user, registration
from pymongo import MongoClient
from datetime import datetime, timedelta
from flask_mysqldb import MySQL
from bson.objectid import ObjectId
import re



app = Flask(__name__)
app.config.from_object(Config)

mysql = MySQL(app)

# MongoDB setup
mongo_client = MongoClient('mongodb://localhost:27017/')
mongo_db = mongo_client["wealthyfyme"]
mongo_transactions = mongo_db["transactions"]
mongo_budgets = mongo_db["budgets"]
mongo_challenges=mongo_db["group_challenges"]

CATEGORIES = ["Salary","Food", "Housing", "Transportation", "Entertainment", "Shopping", "Healthcare", "Education","Others"]


@app.route('/')
def home():
    return render_template("index.html")


@app.route('/login', methods=["GET", "POST"])
def login():
    msg = session.get('msg', '')
    form = LoginForm()

    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        res = check_user(email, password)

        if res:
            session['user_email'] = email  # Save user for session scope
            return redirect(url_for('dashboard_home'))
        else:
            session['msg'] = "unsuccessful"
            return redirect(url_for('login'))

    session.pop('msg', None)
    return render_template("login.html", form=form, msg=msg)



def get_user_by_email(email):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM login WHERE email = %s", (email,))
    user = cur.fetchone()
    cur.close()
    return user  # None if not found

def send_password_reset_email(user):
    # 'email' is now accessed by key instead of index
    print(f"Sending password reset email to {user['email']}")

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    form = ForgotPasswordForm()
    msg = None
    if form.validate_on_submit():
        email = form.email.data
        user = get_user_by_email(email)
        if user:
            send_password_reset_email(user)
            msg = 'sent'
        else:
            msg = 'not_found'
    return render_template('forgot_password.html', form=form, msg=msg)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))



@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegistrationForm()

    if request.method == "POST":
        if form.validate_on_submit():
            name = form.name.data
            email = form.email.data
            password = form.password.data
            confirm_password = form.confirm_password.data

            res = registration(name, email, password, confirm_password)
            if res:
                return redirect(url_for('login'))
            else:
                session['msg'] = "Please, Enter a Valid Email !!!"
                return redirect(url_for('register'))
        else:
            # Store errors in session and redirect
            session['form_errors'] = form.errors
            return redirect(url_for('register'))

    # GET request, render form with any stored errors or msg
    msg = session.pop('msg', '')
    form_errors = session.pop('form_errors', {})
    return render_template("registration.html", form=form, msg=msg, form_errors=form_errors)



@app.route('/dashboard_home')
def dashboard_home():
    if 'user_email' not in session:
        return redirect(url_for('login'))

    email = session['user_email']
    current_date = datetime(2025, 5, 1)
    start_date = current_date.replace(day=1)
    end_date = (start_date + timedelta(days=31)).replace(day=1)

    monthly_income = 0
    monthly_expenses = 0
    total_balance = 0
    category_expenses = {}

    transactions = mongo_transactions.find({
        'email': email,
        'date': {'$gte': start_date.strftime('%Y-%m-%d'), '$lt': end_date.strftime('%Y-%m-%d')}
    })

    for txn in transactions:
        txn_type = txn.get('type', '').lower()
        amount = txn.get('amount', 0)
        if txn_type == 'income':
            monthly_income += amount
        elif txn_type == 'expense':
            monthly_expenses += amount
            category = txn.get('category', 'Uncategorized')
            category_expenses[category] = category_expenses.get(category, 0) + amount

    total_balance = monthly_income - monthly_expenses
    sorted_categories = sorted([(cat, abs(amt)) for cat, amt in category_expenses.items()], key=lambda x: x[1], reverse=True)

    monthly_summary = []
    for i in range(6, 0, -1):
        month_start = (current_date - timedelta(days=30 * i)).replace(day=1)
        month_end = (month_start + timedelta(days=31)).replace(day=1)
        month_txns = mongo_transactions.find({
            'email': email,
            'date': {'$gte': month_start.strftime('%Y-%m-%d'), '$lt': month_end.strftime('%Y-%m-%d')}
        })

        month_income, month_expenses = 0, 0
        for txn in month_txns:
            amount = txn.get('amount', 0)
            if txn.get('type', '').lower() == 'income':
                month_income += amount
            else:
                month_expenses += amount

        monthly_summary.append({
            'month': month_start.strftime('%b %Y'),
            'income': month_income,
            'expenses': abs(month_expenses),
            'savings': month_income - abs(month_expenses)
        })

    recent_transactions = mongo_transactions.find({'email': email}).sort('date', -1).limit(5)
    formatted_recent = [{
        'date': datetime.strptime(txn.get('date', ''), '%Y-%m-%d'),
        'category': txn.get('category', ''),
        'description': txn.get('description', ''),
        'amount': txn.get('amount', 0),
        'type': txn.get('type', '')
    } for txn in recent_transactions]

    return render_template("dashboard_home.html",
                           total_balance=total_balance,
                           monthly_income=monthly_income,
                           monthly_expenses=monthly_expenses,
                           recent_transactions=formatted_recent,
                           sorted_categories=sorted_categories,
                           monthly_data={
                               'labels': [m['month'] for m in monthly_summary],
                               'income': [m['income'] for m in monthly_summary],
                               'expenses': [m['expenses'] for m in monthly_summary],
                               'savings': [m['savings'] for m in monthly_summary]
                           },
                           category_data={
                               'labels': [cat[0] for cat in sorted_categories],
                               'data': [cat[1] for cat in sorted_categories]
                           })


@app.route('/transactions', methods=["GET", "POST"])
def transactions():
    if 'user_email' not in session:
        return redirect(url_for('login'))

    email = session['user_email']

    if request.method == "POST":
        txn = {
            "amount": float(request.form["amount"]),
            "category": request.form["category"],
            "description": request.form["description"],
            "date": request.form["date"],
            "type": request.form.get("type", "expense"),
            "email": email
        }
        mongo_transactions.insert_one(txn)
        return redirect(url_for('transactions'))

    transactions = mongo_transactions.find({'email': email}).sort("date", -1)
    formatted_txns = [{
        "date": datetime.strptime(txn.get("date", ""), "%Y-%m-%d").date(),
        "category": txn.get("category", "No Category"),
        "description": txn.get("description", "No description"),
        "amount": txn.get("amount", 0.0),
        "type": txn.get("type", "expense")
    } for txn in transactions]

    return render_template("transactions.html", transactions=formatted_txns,CATEGORIES=CATEGORIES)


@app.route('/budgets')
def budgets():
    if 'user_email' not in session:
        return redirect(url_for('login'))

    email = session['user_email']
    budgets_data = list(mongo_budgets.find({'email': email}))

    pipeline = [
        {"$match": {"email": email, "type": "expense"}},
        {"$group": {"_id": "$category", "total_spent": {"$sum": "$amount"}}}
    ]
    expense_sums = list(mongo_transactions.aggregate(pipeline))
    spent_map = {e['_id']: e['total_spent'] for e in expense_sums}

    for b in budgets_data:
        cat = b['category']
        limit = b.get('limit', 0)
        spent = spent_map.get(cat, 0)
        b['spent'] = spent
        b['progress'] = round((spent / limit) * 100, 2) if limit > 0 else 0

    return render_template('budgets.html', budgets=budgets_data)


@app.route('/add-budget', methods=['POST'])
def add_budget():
    if 'user_email' not in session:
        return redirect(url_for('login'))

    email = session['user_email']
    category = request.form.get('category')
    limit = float(request.form.get('limit'))

    if not category or limit <= 0:
        flash("Invalid budget input!", "danger")
        return redirect(url_for('budgets'))

    existing = mongo_budgets.find_one({"email": email, "category": category})
    if existing:
        flash(f"Budget for '{category}' already exists.", "warning")
        return redirect(url_for('budgets'))

    mongo_budgets.insert_one({
        "category": category,
        "limit": limit,
        "email": email
    })

    flash(f"Budget for '{category}' added!", "success")
    return redirect(url_for('budgets'))


@app.route('/edit-budget/<budget_id>', methods=['POST'])
def edit_budget(budget_id):
    category = request.form.get('category')
    limit = float(request.form.get('limit'))
    mongo_budgets.update_one(
        {"_id": ObjectId(budget_id)},
        {"$set": {"category": category, "limit": limit}}
    )
    flash("Budget updated.", "success")
    return redirect(url_for('budgets'))


@app.route('/delete-budget/<budget_id>', methods=['POST'])
def delete_budget(budget_id):
    mongo_budgets.delete_one({"_id": ObjectId(budget_id)})
    flash("Budget deleted.", "info")
    return redirect(url_for('budgets'))

@app.route('/peer_comparison')
def peer_comparison():
    # Get distinct user emails from transactions
    user_emails = mongo_transactions.distinct("email")

    user_savings = []

    for email in user_emails:
        # Get income total
        income_result = mongo_transactions.aggregate([
            {"$match": {"email": email, "type": "income"}},
            {"$group": {"_id": None, "total_income": {"$sum": "$amount"}}}
        ])
        income = next(income_result, {}).get("total_income", 0)

        # Get expense total
        expense_result = mongo_transactions.aggregate([
            {"$match": {"email": email, "type": "expense"}},
            {"$group": {"_id": None, "total_expense": {"$sum": "$amount"}}}
        ])
        expense = next(expense_result, {}).get("total_expense", 0)

        saved_amount = income - expense

        # Optionally fetch user's name from users collection
        user_info = mongo_db["users"].find_one({"email": email})
       
        raw_name = user_info.get("name") if user_info else email.split("@")[0]
        name = re.sub(r'\d+', '', raw_name)

        user_savings.append({
            "name": name,
            "email": email,
            "saved_amount": saved_amount
        })

    # Sort users by savings descending
    sorted_users = sorted(user_savings, key=lambda x: x["saved_amount"], reverse=True)

    top3 = sorted_users[:3]
    next5 = sorted_users[3:8]

    return render_template("peer_comparison.html", top3=top3, next5=next5)



@app.route('/alerts')
def alerts():
    if 'user_email' not in session:
        return redirect(url_for('login'))

    email = session['user_email']
    budgets_data = list(mongo_budgets.find({'email': email}))

    pipeline = [
        {"$match": {"email": email, "type": "expense"}},
        {"$group": {"_id": "$category", "total_spent": {"$sum": "$amount"}}}
    ]
    expense_sums = list(mongo_transactions.aggregate(pipeline))
    spent_map = {e['_id']: e['total_spent'] for e in expense_sums}

    alerts = []
    for b in budgets_data:
        cat = b['category']
        limit = b.get('limit', 0)
        spent = spent_map.get(cat, 0)
        percentage = (spent / limit) * 100 if limit > 0 else 0

        if percentage >= 90:
            alerts.append({
                'category': cat,
                'limit': limit,
                'spent': spent,
                'percentage': round(percentage, 2)
            })

    # Store alert count in session for use in sidebar
    session['alert_count'] = len(alerts)

    return render_template('alerts.html', alerts=alerts)

@app.route('/group_challenges')
def group_challenges():
    if 'user_email' not in session:
        return redirect(url_for('login'))

    email = session['user_email']
    today = datetime.now()
    challenges = list(mongo_challenges.find({'participants': email}).sort('end_date', 1))

    active_challenges = []
    past_challenges = []

    for challenge in challenges:
        participants = challenge['participants']
        challenge['user_progress'] = get_user_progress(email, challenge)
        leaderboard = []

        for participant in participants:
            progress = get_user_progress(participant, challenge)
            leaderboard.append({'email': participant, 'progress': progress})

        leaderboard.sort(
            key=lambda x: x['progress'],
            reverse=(challenge['type'] == 'savings')  # savings = more is better, spending = less is better
        )
        challenge['leaderboard'] = leaderboard
        challenge['leader'] = leaderboard[0]['email'] if leaderboard else None

        if challenge['end_date'] >= today.strftime('%Y-%m-%d'):
            active_challenges.append(challenge)
        else:
            challenge['user_result'] = 'won' if leaderboard and leaderboard[0]['email'] == email else 'lost'
            past_challenges.append(challenge)

    return render_template("group_challenges.html",
                           active_challenges=active_challenges,
                           past_challenges=past_challenges,
                           today=today)


def get_user_progress(email, challenge):
    transactions = mongo_transactions.find({
        'user_email': email,
        'date': {'$gte': challenge['start_date'], '$lte': challenge['end_date']}
    })
    total = sum(txn['amount'] for txn in transactions if txn['type'] in ['income', 'expense'])

    if challenge['type'] == 'savings':
        return sum(txn['amount'] for txn in transactions if txn['type'] == 'income') - \
               sum(txn['amount'] for txn in transactions if txn['type'] == 'expense')
    elif challenge['type'] == 'spending':
        return sum(txn['amount'] for txn in transactions if txn['type'] == 'expense')
    return 0



@app.route('/create_challenge', methods=['GET', 'POST'])
def create_challenge():
    if request.method == 'POST':
        # Get form data
        name = request.form['name']
        type_ = request.form['type']
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        participants = request.form.getlist('participants')  # list of emails

        mongo_challenges.insert_one({
            'name': name,
            'type': type_,
            'start_date': start_date,
            'end_date': end_date,
            'participants': participants,
        })

        return redirect(url_for('group_challenges'))

    return render_template('create_challenge.html')  # if showing the form page






if __name__ == '__main__':
    app.run(debug=True)
