import csv
import os
import random
import datetime
import getpass
import hashlib
import json
import threading
import time
import schedule
import logging

# Constants
ACCOUNTS_FILE = 'accounts.csv'
TRANSACTIONS_FILE = 'transactions.csv'
LOANS_FILE = 'loans.csv'
AUDIT_LOG_FILE = 'audit.log'
BACKUP_DIR = 'backups'
ADMIN_CREDENTIALS_FILE = 'admins.json'
BACKUP_INTERVAL_MINUTES = 60 

# Logging
logging.basicConfig(
    filename=AUDIT_LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Utility
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def hash_password(password: str) -> str:
    # SHA256 hash password
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    
    return hash_password(password) == hashed


def generate_account_number() -> str:
    return str(random.randint(100000, 999999))


def log_audit(action: str, account: str | None = None, details: str = ""):
    msg = f"ACTION={action}"
    if account:
        msg += f" ACCOUNT={account}"
    if details:
        msg += f" DETAILS={details}"
    logging.info(msg)



class Transaction:
    def __init__(self, account: str, tx_type: str, amount: float, balance: float, timestamp: datetime.datetime | None = None):
        self.account = account
        self.type = tx_type  # 'DEPOSIT', 'WITHDRAW', 'TRANSFER', etc.
        self.amount = amount
        self.balance = balance
        self.timestamp = timestamp or datetime.datetime.now()

    def to_dict(self) -> dict:
        return {
            'account': self.account,
            'datetime': self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'type': self.type,
            'amount': f"{self.amount:.2f}",
            'balance': f"{self.balance:.2f}"
        }


class Account:
    # Represents a single bank account
    def __init__(
        self,
        number: str,
        name: str,
        email: str,
        phone: str,
        password_hash: str,
        balance: float = 0.0,
        is_frozen: bool = False
    ):
        self.number = number
        self.name = name
        self.email = email
        self.phone = phone
        self.password_hash = password_hash
        self.balance = balance
        self.is_frozen = is_frozen
        self.transactions: list[Transaction] = []

    def deposit(self, amount: float) -> None:
        if self.is_frozen:
            raise PermissionError("Account is frozen.")
        if amount <= 0:
            raise ValueError("Deposit amount must be positive.")
        self.balance += amount
        tx = Transaction(self.number, 'DEPOSIT', amount, self.balance)
        self.transactions.append(tx)
        Bank.append_transaction(tx)
        log_audit('DEPOSIT', self.number, f"Amount={amount}")

    def withdraw(self, amount: float) -> None:
        if self.is_frozen:
            raise PermissionError("Account is frozen.")
        if amount <= 0:
            raise ValueError("Withdrawal amount must be positive.")
        if amount > self.balance:
            raise ValueError("Insufficient balance.")
        self.balance -= amount
        tx = Transaction(self.number, 'WITHDRAW', amount, self.balance)
        self.transactions.append(tx)
        Bank.append_transaction(tx)
        log_audit('WITHDRAW', self.number, f"Amount={amount}")

    def transfer_to(self, target: 'Account', amount: float) -> None:
        if self.is_frozen or target.is_frozen:
            raise PermissionError("One of the accounts is frozen.")
        if amount <= 0:
            raise ValueError("Transfer amount must be positive.")
        if amount > self.balance:
            raise ValueError("Insufficient balance.")
        self.balance -= amount
        target.balance += amount
        tx_out = Transaction(self.number, 'TRANSFER_OUT', amount, self.balance)
        tx_in = Transaction(target.number, 'TRANSFER_IN', amount, target.balance)
        self.transactions.append(tx_out)
        target.transactions.append(tx_in)
        Bank.append_transaction(tx_out)
        Bank.append_transaction(tx_in)
        log_audit('TRANSFER', self.number, f"To={target.number},Amount={amount}")

    def add_transaction(self, tx: Transaction) -> None:
        self.transactions.append(tx)

    def load_transactions(self) -> None:
        self.transactions = []
        if os.path.exists(TRANSACTIONS_FILE):
            with open(TRANSACTIONS_FILE, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['account'] == self.number:
                        ts = datetime.datetime.strptime(row['datetime'], '%Y-%m-%d %H:%M:%S')
                        tx = Transaction(
                            account=row['account'],
                            tx_type=row['type'],
                            amount=float(row['amount']),
                            balance=float(row['balance']),
                            timestamp=ts
                        )
                        self.transactions.append(tx)

    def statement_str(self) -> str:
        self.load_transactions()
        lines = []
        header = f"Bank Statement for {self.name} (A/C {self.number})"
        lines.append(header)
        lines.append('-' * len(header))
        lines.append(f"{'Date Time':<20} | {'Type':<12} | {'Amount':<10} | {'Balance':<10}")
        lines.append('-' * 62)
        for tx in sorted(self.transactions, key=lambda t: t.timestamp):
            dt = tx.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            lines.append(f"{dt:<20} | {tx.type:<12} | {tx.amount:<10.2f} | {tx.balance:<10.2f}")
        lines.append('-' * 62)
        lines.append(f"Current Balance: {self.balance:.2f}")
        return '\n'.join(lines)


def main():
    a = 'y'
    while a=='y':
        
        print('-'*50)
        
        print("\nMain Menu:")
        print('-'*50)
        print("1. Add account")
        print("2. Check balance")
        print("3. Deposit")
        print("4. Withdraw")
        print("5. Display all accounts")
        print("6. Print bank statement")
        print("7. Quit\n")

        
        choice = input("\nEnter your choice: ")

        
        if choice == '1':
          balance = float(input("Enter initial balance: "))
          generate_account_number()

        elif choice == '2':
          account_num = input("Enter account number: ")
          check_balance(account_num)

        
        elif choice == '3':
          account_num = input("Enter account number: ")
          amount = float(input("Enter amount to deposit: "))
          deposit(account_num, amount)

        
        elif choice == '4':
          account_num = input("Enter account number: ")
          amount = float(input("Enter amount to withdraw: "))
          withdraw(account_num, amount)

        
        elif choice == '5':
          display_all()

        
        elif choice == '6':
          account_num = input("Enter account number: ")
          print_bank_statement(account_num)

      
        elif choice == '7':
          
          save_data()
          break

        else:
          print("Error: Invalid choice\n")
          
          
        
try:
    load_data()
    main()


except:
    main()
    
    
