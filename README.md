
# **Client Management System**

## 📽️ **Video Demo**
[Insert Video URL Here]

---

## 📋 **Description**
The **Client Management System** is a web-based application that enables users to manage their clients, track payments, and generate invoices. The system provides an intuitive and user-friendly interface to facilitate client management, allowing users to view client details, track balances, and generate financial reports.

---

## 🚀 **Features**
- **User Authentication**: Secure user login and registration system.
- **Client Management**: Add, view, update, and delete client information.
- **Transaction Management**: Record payments and invoices for clients.
- **Invoices**: Generate and download client invoices in PDF format.
- **Reports**: View monthly summaries of payments and invoices.
- **Data Export**: Export client data to a CSV file.

---

## 🛠️ **Technologies Used**
- **Backend**: Python (Flask)
- **Frontend**: HTML, CSS, Bootstrap
- **Database**: SQLite
- **Others**: 
  - **Chart.js**: For data visualization.
  - **ReportLab**: For generating PDF invoices.

---

## 📁 **Folder Structure**
```
.
├── README.md
├── app.py                 # Main application file
├── database.db            # SQLite database file
├── node_modules/          # Node.js dependencies
├── package-lock.json      # Lock file for npm packages
├── package.json           # NPM configuration file
├── static/
│   └── styles.css         # Custom CSS styles
├── templates/             # HTML templates
│   ├── add_client.html
│   ├── client_details.html
│   ├── index.html
│   ├── layout.html
│   ├── login.html
│   ├── monthly_summary.html
│   └── register.html
└── .gitignore             # Git ignore file (excludes venv, cache, etc.)
```

---

## 📦 **Installation Instructions**
Follow these steps to set up the **Client Management System** on your local machine.

### **Prerequisites**
- **Python 3.9 or higher**
- **pip** (Python package installer)
- **Git** (to clone the repository)

---

### **Steps to Install**

1️⃣ **Clone the Repository**
```bash
git clone https://github.com/azuagajuandev/client-management.git
cd client-management
```

2️⃣ **Create and Activate Virtual Environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3️⃣ **Install Required Packages**
```bash
pip install -r requirements.txt
```

4️⃣ **Initialize the Database**
```bash
python -c "from app import init_db; init_db()"
```

5️⃣ **Run the Application**
```bash
flask run
```

6️⃣ **Access the Application**
Open your web browser and go to: 
```
http://127.0.0.1:5000/
```

---

## 📘 **Usage Instructions**
1. **Register**: Create an account to log in.
2. **Login**: Log in to access the dashboard.
3. **Dashboard**: View client information, client balance charts, and client actions.
4. **Add Client**: Add a new client to the system.
5. **View Client Details**: View individual client details, transactions, and invoices.
6. **Manage Transactions**: Add payments and generate invoices.
7. **Export Data**: Export client data to a CSV file.
8. **Generate Reports**: View monthly payment and invoice summaries.

---

## 🌐 **Routes and Endpoints**

| **Route**                      | **Method** | **Description**                     |
|---------------------------------|------------|-------------------------------------|
| `/`                             | `GET`      | Dashboard showing clients and balances |
| `/login`                        | `GET/POST` | Login page for users                 |
| `/register`                     | `GET/POST` | Registration page for new users      |
| `/logout`                       | `GET`      | Log out the current user             |
| `/add_client`                   | `GET/POST` | Add a new client to the system       |
| `/client/<int:client_id>`       | `GET`      | View details of a specific client    |
| `/client/<int:client_id>/add_transaction` | `POST` | Add a new transaction for a client  |
| `/client/<int:client_id>/invoice` | `GET`    | Generate a PDF invoice for a client  |
| `/client/<int:client_id>/delete` | `POST`    | Delete a client and their transactions |
| `/client/<int:client_id>/transaction/<int:transaction_id>/delete` | `POST` | Delete a specific transaction |
| `/export`                       | `GET`      | Export all client data to a CSV file |
| `/monthly_summary`              | `GET`      | View monthly payment and invoice summaries |

---

## 🛠️ **Known Issues and Limitations**
- **Limited User Roles**: Only basic user accounts are supported. Admin roles are not available.
- **Single-user Data Isolation**: Each user's data is isolated, but there is no multi-user role support.
- **Database Storage**: Uses SQLite, which is suitable for small-scale applications. For larger deployments, consider using PostgreSQL or MySQL.

---

## 🌱 **Future Enhancements**
- Add user roles (Admin, Manager, User).
- Implement email notifications for invoices.
- Improve UI/UX design with animations and better responsiveness.
- Add support for additional financial reports.
- Integrate third-party payment gateways for real-time payments.

---

## 👨‍💻 **Author**
- **Juan Azuaga Lombardo**

---

## 📜 **License**
This project is licensed under the MIT License. See the `LICENSE` file for details.

---

If you have any questions or feedback, please contact azuagajuan@gmail.com.
