from flask import Flask, render_template, request, redirect, url_for, Response
import sqlite3
import json
import csv
from reportlab.pdfgen import canvas
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import os
from werkzeug.security import generate_password_hash, check_password_hash
import io
from io import BytesIO

app = Flask(__name__)

# Secret key configuration
app.secret_key = os.urandom(24)

# Function to get a connection to the database
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# Initialize the database
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            balance REAL NOT NULL,
            user_id INTEGER NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            type TEXT NOT NULL,
            date TEXT NOT NULL,
            FOREIGN KEY(client_id) REFERENCES clients(id)
        )
    ''')
    conn.commit()
    conn.close()

# Flask-Login configuration
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User model
class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

# Simulated user (for testing purposes, replace with database in production)
USERS = {"admin": {"id": 1, "username": "admin", "password": "password123"}}

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    if user:
        return User(user['id'], user['username'])
    return None

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            login_user(User(user['id'], user['username']))
            return redirect(url_for('index'))

        return render_template('login.html', error="Incorrect username or password.")
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    query = request.args.get('query')
    page = int(request.args.get('page', 1))
    per_page = 10
    offset = (page - 1) * per_page

    conn = get_db_connection()
    if query:
        clients = conn.execute(
            'SELECT * FROM clients WHERE name LIKE ? AND user_id = ? LIMIT ? OFFSET ?',
            (f'%{query}%', current_user.id, per_page, offset)
        ).fetchall()
    else:
        clients = conn.execute(
            'SELECT * FROM clients WHERE user_id = ? LIMIT ? OFFSET ?', 
            (current_user.id, per_page, offset)
        ).fetchall()
    
    total_clients = conn.execute(
        'SELECT COUNT(*) FROM clients WHERE user_id = ?', 
        (current_user.id,)
    ).fetchone()[0]
    
    total_pages = (total_clients + per_page - 1) // per_page

    negative_clients = conn.execute(
        'SELECT * FROM clients WHERE balance < 0 AND user_id = ?', 
        (current_user.id,)
    ).fetchall()
    
    chart_data = {
        "labels": [client["name"] for client in clients],
        "values": [client["balance"] for client in clients]
    }

    conn.close()
    return render_template(
        'index.html',
        clients=clients,
        page=page,
        total_pages=total_pages,
        chart_data=json.dumps(chart_data),
        negative_clients=negative_clients
    )

@app.route('/create_client', methods=['GET', 'POST'])
@login_required
def create_client():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        balance = float(request.form['balance'])

        conn = get_db_connection()
        conn.execute('INSERT INTO clients (name, email, balance, user_id) VALUES (?, ?, ?, ?)', 
                     (name, email, balance, current_user.id))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    return render_template('create_client.html')

@app.route('/client/<int:client_id>')
@login_required
def client_details(client_id):
    conn = get_db_connection()
    client = conn.execute(
        'SELECT * FROM clients WHERE id = ? AND user_id = ?', 
        (client_id, current_user.id)
    ).fetchone()
    if client is None:
        return redirect(url_for('index'))
    
    transactions = conn.execute(
        'SELECT * FROM transactions WHERE client_id = ?', 
        (client_id,)
    ).fetchall()
    conn.close()
    return render_template('client_details.html', client=client, transactions=transactions)

@app.route('/client/<int:client_id>/create_transaction', methods=['POST'])
@login_required
def create_transaction(client_id):
    type_ = request.form['type']
    amount = float(request.form['amount'])

    if type_ == 'payment':
        amount = -amount

    conn = get_db_connection()
    conn.execute('INSERT INTO transactions (client_id, amount, type, date) VALUES (?, ?, ?, DATE("now"))',
                 (client_id, amount, type_))
    conn.execute('UPDATE clients SET balance = balance + ? WHERE id = ?', (amount, client_id))
    conn.commit()
    conn.close()
    return redirect(url_for('client_details', client_id=client_id))

@app.route('/client/<int:client_id>/invoice')
@login_required
def generate_invoice(client_id):
    conn = get_db_connection()
    client = conn.execute('SELECT * FROM clients WHERE id = ?', (client_id,)).fetchone()
    transactions = conn.execute('SELECT * FROM transactions WHERE client_id = ?', (client_id,)).fetchall()
    conn.close()

    # Create a PDF file in memory
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    p.drawString(100, 800, f"Client Invoice for {client['name']}")
    p.drawString(100, 780, f"Email: {client['email']}")
    p.drawString(100, 760, f"Outstanding Balance: ${client['balance']:.2f}")
    y = 740
    for transaction in transactions:
        p.drawString(100, y, f"{transaction['date']} - {transaction['type']}: {transaction['amount']}")
        y -= 20
    p.save()

    buffer.seek(0)

    # Return the PDF as a response
    return Response(buffer, mimetype='application/pdf', headers={
        'Content-Disposition': f'inline; filename=invoice_{client_id}.pdf'
    })

@app.route('/monthly_summary')
@login_required
def monthly_summary():
    try:
        conn = get_db_connection()
        summary = conn.execute('''
            SELECT strftime('%Y-%m', date) AS month,
                   SUM(CASE WHEN type = 'payment' THEN amount ELSE 0 END) AS total_payments,
                   SUM(CASE WHEN type = 'invoice' THEN amount ELSE 0 END) AS total_invoices
            FROM transactions
            WHERE client_id IN (
                SELECT id FROM clients WHERE user_id = ?
            )
            GROUP BY month
            ORDER BY month DESC
        ''', (current_user.id,)).fetchall()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        summary = []
    finally:
        conn.close()

    return render_template('monthly_summary.html', summary=summary)

@app.route('/export')
@login_required
def export_clients():
    conn = get_db_connection()
    clients = conn.execute('SELECT * FROM clients WHERE user_id = ?', (current_user.id,)).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Client ID', 'Name', 'Email', 'Outstanding Balance'])

    for client in clients:
        writer.writerow([client['id'], client['name'], client['email'], client['balance']])

    output.seek(0)

    response = Response(output, mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=clients.csv'
    return response

@app.route('/client/<int:client_id>/delete', methods=['POST'])
@login_required
def delete_client(client_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM clients WHERE id = ?', (client_id,))
    conn.execute('DELETE FROM transactions WHERE client_id = ?', (client_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/client/<int:client_id>/transaction/<int:transaction_id>/delete', methods=['POST'])
@login_required
def delete_transaction(client_id, transaction_id):
    # Step 1: Retrieve the transaction to get its amount and type before deleting it
    conn = get_db_connection()
    transaction = conn.execute(
        '''
        SELECT t.amount, t.type 
        FROM transactions t 
        WHERE t.id = ? 
        AND t.client_id = ? 
        AND EXISTS (
            SELECT NULL 
            FROM clients c 
            WHERE c.id = t.client_id 
                AND c.user_id = ? 
            LIMIT 1
        )
        ''', 
        (transaction_id, client_id, current_user.id)
    ).fetchone()
    
    if transaction:
        amount = transaction['amount']  # Get the transaction amount
        type_ = transaction['type']  # Get the transaction type ('payment' or 'invoice')
        
        # Step 2: Adjust the client's balance to revert the impact of the deleted transaction
        if type_ == 'payment':
            # If it was a payment, it was subtracted from the balance, so we need to add it back
            conn.execute('UPDATE clients SET balance = balance + ? WHERE id = ?', (-amount, client_id))
        else:
            # If it was an invoice, it was added to the balance, so we need to subtract it
            conn.execute('UPDATE clients SET balance = balance - ? WHERE id = ?', (amount, client_id))

        # Step 3: Delete the transaction from the database
        conn.execute('DELETE FROM transactions WHERE id = ?', (transaction_id,))
        conn.commit()  # Save the changes to the database
    
    conn.close()  # Close the database connection
    return redirect(url_for('client_details', client_id=client_id))  # Redirect to the client's details page

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['password_confirmation']

        if password != confirm_password:
            return render_template('register.html', error="Passwords do not match.")
        
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        try:
            conn = get_db_connection()
            conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return render_template('register.html', error="The username is already in use.")
    return render_template('register.html')

login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "info"

if __name__ == '__main__':
    init_db()
    app.run(debug=True)