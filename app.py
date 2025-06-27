from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from datetime import datetime
from models import User, get_db, init_db
import sqlite3


app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Database Configuration
DATABASE = 'finance.db'

def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    with app.app_context():
        db = get_db()
        # Create users table
        db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        # Create transactions table
        db.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                description TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                type TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        # Create budgets table
        db.execute('''
            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                amount REAL NOT NULL,
                month TEXT NOT NULL,
                UNIQUE(user_id, category, month),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        db.commit()
        db.close()

class User:
    @staticmethod
    def create(username, password):
        db = get_db()
        db.execute('INSERT INTO users (username, password) VALUES (?, ?)', 
                  (username, password))
        db.commit()
        db.close()

    @staticmethod
    def verify_user(username, password):
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ? AND password = ?',
                         (username, password)).fetchone()
        db.close()
        return dict(user) if user else None

    @staticmethod
    def delete_budget(user_id, category, month):
        db = get_db()
        db.execute('''
            DELETE FROM budgets 
            WHERE user_id = ? AND category = ? AND month = ?
        ''', (user_id, category, month))
        db.commit()
        db.close()

# Initialize database
init_db()

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    return response

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.verify_user(username, password)
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('dashboard'))
        flash('Invalid username or password', 'error')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Username and password are required', 'error')
            return redirect(url_for('signup'))
        
        try:
            User.create(username, password)
            flash('Account created successfully! Please login.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists', 'error')
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', now=datetime.now().strftime('%Y-%m-%d'))

@app.route('/transactions')
def get_transactions():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        conn = get_db()
        transactions = conn.execute('''
            SELECT * FROM transactions 
            WHERE user_id = ?
            ORDER BY date DESC
        ''', (session['user_id'],)).fetchall()
        
        result = []
        for row in transactions:
            result.append({
                'id': row['id'],
                'date': row['date'],
                'description': row['description'],
                'amount': row['amount'],
                'category': row['category'],
                'type': row['type']
            })
        conn.close()
        return jsonify(result)
    except Exception as e:
        print("TRANSACTIONS ERROR:", str(e))
        return jsonify({"error": str(e)}), 500

@app.route('/add', methods=['POST'])
def add_transaction():
    if 'user_id' not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    try:
        data = request.get_json()
        if not data or not data.get('description') or not data.get('amount'):
            return jsonify({"success": False, "error": "Description and amount are required"}), 400
        
        conn = get_db()
        conn.execute('''
            INSERT INTO transactions (user_id, date, description, amount, category, type)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            session['user_id'],
            data.get('date', datetime.now().strftime('%Y-%m-%d')),
            data['description'],
            float(data['amount']),
            data.get('category', 'Other'),
            data.get('type', 'Expense')
        ))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        print("ADD ERROR:", str(e))
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/delete/<int:id>', methods=['DELETE'])
def delete_transaction(id):
    if 'user_id' not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    try:
        conn = get_db()
        conn.execute('''
            DELETE FROM transactions 
            WHERE id = ? AND user_id = ?
        ''', (id, session['user_id']))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        print("DELETE ERROR:", str(e))
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/stats')
def get_stats():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        conn = get_db()
        current_month = datetime.now().strftime('%Y-%m')
        
        income = conn.execute('''
            SELECT COALESCE(SUM(amount), 0) 
            FROM transactions 
            WHERE user_id = ? AND type = 'Income' AND strftime('%Y-%m', date) = ?
        ''', (session['user_id'], current_month)).fetchone()[0]
        
        expense = conn.execute('''
            SELECT COALESCE(SUM(amount), 0) 
            FROM transactions 
            WHERE user_id = ? AND type = 'Expense' AND strftime('%Y-%m', date) = ?
        ''', (session['user_id'], current_month)).fetchone()[0]
        
        net_savings = income - expense
        savings_rate = (net_savings / income * 100) if income > 0 else 0
        
        categories = conn.execute('''
            SELECT category, COALESCE(SUM(amount), 0) as total 
            FROM transactions 
            WHERE user_id = ? AND type = 'Expense' AND strftime('%Y-%m', date) = ?
            GROUP BY category
        ''', (session['user_id'], current_month)).fetchall()
        
        budgets = conn.execute('''
            SELECT category, amount 
            FROM budgets 
            WHERE user_id = ? AND month = ?
        ''', (session['user_id'], current_month)).fetchall()
        
        conn.close()
        
        return jsonify({
            "income": float(income),
            "expense": float(expense),
            "net_savings": float(net_savings),
            "savings_rate": float(savings_rate),
            "categories": [{'category': row[0], 'total': float(row[1])} for row in categories],
            "budgets": [{'category': row[0], 'amount': float(row[1])} for row in budgets]
        })
    except Exception as e:
        print("STATS ERROR:", str(e))
        return jsonify({"error": str(e)}), 500

@app.route('/budget', methods=['POST'])
def set_budget():
    if 'user_id' not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    try:
        data = request.get_json()
        if not data or not data.get('category') or not data.get('amount'):
            return jsonify({"success": False, "error": "Category and amount are required"}), 400
        
        current_month = datetime.now().strftime('%Y-%m')
        
        conn = get_db()
        conn.execute('''
            INSERT OR REPLACE INTO budgets (user_id, category, amount, month)
            VALUES (?, ?, ?, ?)
        ''', (
            session['user_id'],
            data['category'],
            float(data['amount']),
            current_month
        ))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        print("BUDGET ERROR:", str(e))
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/budget/<category>', methods=['DELETE'])
def delete_budget(category):
    if 'user_id' not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    try:
        current_month = datetime.now().strftime('%Y-%m')
        User.delete_budget(session['user_id'], category, current_month)
        return jsonify({"success": True})
    except Exception as e:
        print("BUDGET DELETE ERROR:", str(e))
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)