# Bank Management System by Om

A menu-driven Python application for managing bank accounts, transactions, loans, and administrative tasks. It supports user authentication, audit logging, automated backups, and more.

---

## Features

- **User operations**: Register, login/logout, check balance, deposit, withdraw, transfer funds, view statements, update details, close account.
- **Loan management**: Apply for loans, view existing loans, make loan payments.
- **Administrative operations**: Admin login/logout, freeze/unfreeze accounts, view audit logs.
- **Audit logging**: All critical actions are logged to `audit.log` with timestamps.
- **Automated backups**: Periodic backups of CSV data files to `backups/` directory.
- **Data persistence**: Account, transaction, and loan data stored in CSV files.

---

## Requirements

- Python 3.8 or higher
- [`schedule`](https://pypi.org/project/schedule/) (for automated backups)

---

## Setup

1. **Clone or download** this repository into your local machine.
2. **Create a virtual environment** (recommended):

   ```bash
   python3 -m venv venv
   source venv/bin/activate      # On Windows: venv\Scripts\activate
   ```
3. **Install dependencies**:

   ```bash
   pip install schedule
   ```
4. **Prepare data files**:

   - Ensure the following files exist in the project root (they will be created automatically on first run if missing):
     - `accounts.csv`
     - `transactions.csv`
     - `loans.csv`
     - `admins.json`
     - `audit.log`

   You can also initialize `admins.json` with an empty JSON object:

   ```json
   {}
   ```
5. **(Optional) Create an admin user**:

   Edit `admins.json` and add an entry with a username and a SHA256-hashed password. Example:

   ```json
   {
     "superadmin": "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd..."
   }
   ```

   To generate a SHA256 hash for your desired password in Python:

   ```python
   import hashlib
   print(hashlib.sha256(b"your_password_here").hexdigest())
   ```

---

## Running the Application

With your virtual environment activated, simply run:

```bash
python bank_management_full.py
```

You will see a menu with options for both user and admin operations.

---

## File Structure

```
├── main.py   		     # Main application script
├── accounts.csv             # Stores account details
├── transactions.csv         # Stores transaction logs
├── loans.csv                # Stores loan records
├── admins.json              # Admin credentials (username: password_hash)
├── audit.log                # Audit log of all actions
└── backups/                 # Directory where automated backups are saved
```

---

## Notes

- **Data security**: Passwords are stored as SHA256 hashes. For production use, consider using a stronger hashing algorithm like bcrypt.
- **Backup interval**: The default backup interval is every 60 minutes. Modify `BACKUP_INTERVAL_MINUTES` in `bank_management_full.py` as needed.
- **Extensibility**: You can replace CSV storage with a database, integrate email/SMS notifications, or build a web API on top of this core logic.
