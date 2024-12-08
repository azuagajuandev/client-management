from flask import Flask, render_template, request, redirect, url_for, Response
import sqlite3
import json
import csv
from reportlab.pdfgen import canvas
from io import BytesIO
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Configuración de la clave secreta
app.secret_key = os.urandom(24)  # Genera una clave aleatoria cada vez que se ejecuta la aplicación

# Función para obtener conexión a la base de datos
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row  # Permite acceder a las columnas por nombre
    return conn

# Inicializar la base de datos
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

# Configuración de Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Modelo de Usuario
class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

# Usuario Simulado (para pruebas, reemplazar con base de datos en producción)
USERS = {"admin": {"id": 1, "username": "admin", "password": "password123"}}

@login_manager.user_loader
def load_user(user_id):
    for username, user in USERS.items():
        if user["id"] == int(user_id):
            return User(user["id"], username)
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

        return render_template('login.html', error="Usuario o contraseña incorrectos.")
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

@app.route('/add_client', methods=['GET', 'POST'])
@login_required
def add_client():
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
    return render_template('add_client.html')

@app.route('/client/<int:client_id>')
@login_required
def client_details(client_id):
    conn = get_db_connection()
    client = conn.execute(
        'SELECT * FROM clients WHERE id = ? AND user_id = ?', 
        (client_id, current_user.id)
    ).fetchone()
    if client is None:
        return redirect(url_for('index'))  # Evita el acceso a clientes de otros usuarios
    
    transactions = conn.execute(
        'SELECT * FROM transactions WHERE client_id = ?', 
        (client_id,)
    ).fetchall()
    conn.close()
    return render_template('client_details.html', client=client, transactions=transactions)

@app.route('/client/<int:client_id>/add_transaction', methods=['POST'])
@login_required
def add_transaction(client_id):
    type_ = request.form['type']
    amount = float(request.form['amount'])

    if type_ == 'pago':
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

    # Crear un archivo PDF en memoria
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    p.drawString(100, 800, f"Factura para {client['name']}")
    p.drawString(100, 780, f"Email: {client['email']}")
    p.drawString(100, 760, f"Saldo: {client['balance']}")
    y = 740
    for transaction in transactions:
        p.drawString(100, y, f"{transaction['date']} - {transaction['type']}: {transaction['amount']}")
        y -= 20
    p.save()

    # Mover el puntero al inicio del buffer
    buffer.seek(0)

    # Retornar el PDF como respuesta
    return Response(buffer, mimetype='application/pdf', headers={
        'Content-Disposition': f'inline; filename=invoice_{client_id}.pdf'
    })

@app.route('/monthly_summary')
@login_required
def monthly_summary():
    conn = get_db_connection()
    summary = conn.execute('''
        SELECT strftime('%Y-%m', date) AS month,
               SUM(CASE WHEN type = 'pago' THEN amount ELSE 0 END) AS total_pagos,
               SUM(CASE WHEN type = 'factura' THEN amount ELSE 0 END) AS total_facturas
        FROM transactions
        GROUP BY month
    ''').fetchall()
    conn.close()
    return render_template('monthly_summary.html', summary=summary)

@app.route('/export')
@login_required
def export_clients():
    conn = get_db_connection()
    clients = conn.execute('SELECT * FROM clients').fetchall()
    conn.close()

    def generate():
        data = csv.writer()
        data.writerow(['ID', 'Nombre', 'Email', 'Saldo'])
        for client in clients:
            data.writerow([client['id'], client['name'], client['email'], client['balance']])
        yield data.getvalue()

    response = Response(generate(), mimetype='text/csv')
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
    # Verificar si la transacción pertenece al cliente actual y al usuario autenticado
    conn = get_db_connection()
    transaction = conn.execute(
        'SELECT t.id FROM transactions t JOIN clients c ON t.client_id = c.id WHERE t.id = ? AND c.id = ? AND c.user_id = ?', 
        (transaction_id, client_id, current_user.id)
    ).fetchone()
    
    if transaction:
        conn.execute('DELETE FROM transactions WHERE id = ?', (transaction_id,))
        conn.commit()
    
    conn.close()
    return redirect(url_for('client_details', client_id=client_id))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        try:
            conn = get_db_connection()
            conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return render_template('register.html', error="El nombre de usuario ya está en uso.")
    return render_template('register.html')

login_manager.login_message = "Por favor, inicia sesión para acceder a esta página."
login_manager.login_message_category = "info"

if __name__ == '__main__':
    init_db()
    app.run(debug=True)