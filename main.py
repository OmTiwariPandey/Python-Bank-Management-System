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


class Loan:
    def __init__(
        self,
        account: str,
        principal: float,
        interest_rate: float,
        term_months: int,
        start_date: datetime.date | None = None
    ):
        self.account = account
        self.principal = principal
        self.interest_rate = interest_rate
        self.term_months = term_months
        self.start_date = start_date or datetime.date.today()
        self.balance = principal
        self.monthly_payment = self.calculate_monthly_payment()

    def calculate_monthly_payment(self) -> float:
        r = self.interest_rate / 12 / 100
        n = self.term_months
        if r == 0:
            return self.principal / n
        return (self.principal * r * (1 + r)**n) / ((1 + r)**n - 1)

    def make_payment(self, amount: float) -> None:
        if amount <= 0:
            raise ValueError("Payment amount must be positive.")
        if amount > self.balance:
            amount = self.balance
        self.balance -= amount
        Bank.append_loan_payment(self, amount)
        log_audit('LOAN_PAYMENT', self.account, f"Amount={amount}")

    def to_dict(self) -> dict:
        return {
            'account': self.account,
            'principal': f"{self.principal:.2f}",
            'interest_rate': f"{self.interest_rate:.2f}",
            'term_months': str(self.term_months),
            'start_date': self.start_date.strftime('%Y-%m-%d'),
            'balance': f"{self.balance:.2f}"
        }


# Sending emails
class NotificationManager:
    @staticmethod
    def send_email(to_email: str, subject: str, body: str) -> None:
        # TODO
        log_audit('NOTIFICATION', details=f"To={to_email},Subject={subject}")


# BackupManager for Automated Data Backups lol 
class BackupManager:
    @staticmethod
    def backup_file(src: str, dest_dir: str) -> None:
        if not os.path.exists(src):
            return
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = os.path.basename(src)
        dest = os.path.join(dest_dir, f"{timestamp}_{filename}")
        with open(src, 'r') as fsrc, open(dest, 'w') as fdest:
            fdest.write(fsrc.read())
        log_audit('BACKUP', details=f"{src} -> {dest}")

    @staticmethod
    def perform_backup():
        BackupManager.backup_file(ACCOUNTS_FILE, BACKUP_DIR)
        BackupManager.backup_file(TRANSACTIONS_FILE, BACKUP_DIR)
        BackupManager.backup_file(LOANS_FILE, BACKUP_DIR)

    @staticmethod
    def schedule_backups(interval_minutes: int):
        schedule.every(interval_minutes).minutes.do(BackupManager.perform_backup)
        def run_scheduler():
            while True:
                schedule.run_pending()
                time.sleep(1)
        t = threading.Thread(target=run_scheduler, daemon=True)
        t.start()


class Bank:
    def __init__(self):
        self.accounts: dict[str, Account] = {}
        self.loans: dict[str, list[Loan]] = {}
        self.admins: dict[str, str] = {}  # username: password_hash
        self.logged_in_user: Account | None = None
        self.logged_in_admin: str | None = None
        self.load_admins()
        self.load_accounts()
        self.load_loans()
        BackupManager.schedule_backups(BACKUP_INTERVAL_MINUTES)
        log_audit('BANK_INIT')

    def load_admins(self) -> None:
        if os.path.exists(ADMIN_CREDENTIALS_FILE):
            with open(ADMIN_CREDENTIALS_FILE, 'r') as f:
                data = json.load(f)
                self.admins = data

    def save_admins(self) -> None:
        with open(ADMIN_CREDENTIALS_FILE, 'w') as f:
            json.dump(self.admins, f)

    def load_accounts(self) -> None:
        self.accounts.clear()
        if os.path.exists(ACCOUNTS_FILE):
            with open(ACCOUNTS_FILE, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    acc = Account(
                        number=row['number'],
                        name=row['name'],
                        email=row['email'],
                        phone=row['phone'],
                        password_hash=row['password'],
                        balance=float(row['balance']),
                        is_frozen=(row.get('frozen', 'False') == 'True')
                    )
                    acc.load_transactions()
                    self.accounts[acc.number] = acc

    def save_accounts(self) -> None:
        with open(ACCOUNTS_FILE, 'w', newline='') as f:
            fieldnames = ['number', 'name', 'email', 'phone', 'password', 'balance', 'frozen']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for acc in self.accounts.values():
                writer.writerow({
                    'number': acc.number,
                    'name': acc.name,
                    'email': acc.email,
                    'phone': acc.phone,
                    'password': acc.password_hash,
                    'balance': f"{acc.balance:.2f}",
                    'frozen': str(acc.is_frozen)
                })

    @staticmethod
    def append_transaction(tx: Transaction) -> None:
        file_exists = os.path.exists(TRANSACTIONS_FILE)
        with open(TRANSACTIONS_FILE, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['account', 'datetime', 'type', 'amount', 'balance'])
            if not file_exists:
                writer.writeheader()
            writer.writerow(tx.to_dict())

    def load_loans(self) -> None:
        self.loans.clear()
        if os.path.exists(LOANS_FILE):
            with open(LOANS_FILE, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    loan = Loan(
                        account=row['account'],
                        principal=float(row['principal']),
                        interest_rate=float(row['interest_rate']),
                        term_months=int(row['term_months']),
                        start_date=datetime.datetime.strptime(row['start_date'], '%Y-%m-%d').date()
                    )
                    loan.balance = float(row['balance'])
                    self.loans.setdefault(loan.account, []).append(loan)

    def save_loans(self) -> None:
        with open(LOANS_FILE, 'w', newline='') as f:
            fieldnames = ['account', 'principal', 'interest_rate', 'term_months', 'start_date', 'balance']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for loan_list in self.loans.values():
                for loan in loan_list:
                    writer.writerow(loan.to_dict())

    @staticmethod
    def append_loan_payment(loan: Loan, amount: float) -> None:
        tx = Transaction(loan.account, 'LOAN_PAYMENT', amount, loan.balance)
        Bank.append_transaction(tx)

    # Account Management
    def register_account(self) -> None:
        name = input("Enter your full name: ").strip()
        email = input("Enter your email address: ").strip()
        phone = input("Enter your phone number: ").strip()
        while True:
            pwd = getpass.getpass("Set a secure password: ")
            pwd2 = getpass.getpass("Confirm password: ")
            if pwd != pwd2:
                print("Passwords do not match. Try again.")
            else:
                break
        acc_num = generate_account_number()
        while acc_num in self.accounts:
            acc_num = generate_account_number()
        pwd_hash = hash_password(pwd)
        initial_deposit = float(input("Enter initial deposit amount: "))
        acc = Account(acc_num, name, email, phone, pwd_hash, balance=0.0)
        self.accounts[acc_num] = acc
        acc.deposit(initial_deposit)
        self.save_accounts()
        log_audit('REGISTER', acc_num)
        print(f"Account created successfully. Your account number is {acc_num}.")

    def login(self) -> None:
        acc_num = input("Account number: ").strip()
        pwd = getpass.getpass("Password: ")
        acc = self.accounts.get(acc_num)
        if acc and verify_password(pwd, acc.password_hash):
            self.logged_in_user = acc
            log_audit('LOGIN', acc_num)
            print(f"Login successful. Welcome {acc.name}.")
        else:
            print("Invalid credentials.")

    def logout(self) -> None:
        if self.logged_in_user:
            log_audit('LOGOUT', self.logged_in_user.number)
            self.logged_in_user = None
            print("Logged out successfully.")
        else:
            print("No user is currently logged in.")

    def require_user_login(self) -> bool:
        if not self.logged_in_user:
            print("You must be logged in first.")
            return False
        return True

    def check_balance(self) -> None:
        if not self.require_user_login(): return
        assert self.logged_in_user is not None
        print(f"Your current balance is: {self.logged_in_user.balance:.2f}")
        log_audit('CHECK_BALANCE', self.logged_in_user.number)

    def deposit_money(self) -> None:
        if not self.require_user_login(): return
        assert self.logged_in_user is not None
        amt = float(input("Enter deposit amount: "))
        try:
            self.logged_in_user.deposit(amt)
            self.save_accounts()
            print(f"Deposited {amt:.2f}. New balance: {self.logged_in_user.balance:.2f}")
        except Exception as e:
            print(f"Error: {e}")

    def withdraw_money(self) -> None:
        if not self.require_user_login(): return
        assert self.logged_in_user is not None
        amt = float(input("Enter withdrawal amount: "))
        try:
            self.logged_in_user.withdraw(amt)
            self.save_accounts()
            print(f"Withdrew {amt:.2f}. New balance: {self.logged_in_user.balance:.2f}")
        except Exception as e:
            print(f"Error: {e}")

    def transfer_funds(self) -> None:
        if not self.require_user_login(): return
        assert self.logged_in_user is not None
        target_num = input("Enter recipient account number: ").strip()
        amt = float(input("Enter amount to transfer: "))
        target = self.accounts.get(target_num)
        if not target:
            print("Recipient account not found.")
            return
        try:
            self.logged_in_user.transfer_to(target, amt)
            self.save_accounts()
            print(f"Transferred {amt:.2f} to account {target_num}.")
        except Exception as e:
            print(f"Error: {e}")

    def view_statement(self) -> None:
        if not self.require_user_login(): return
        assert self.logged_in_user is not None
        print(self.logged_in_user.statement_str())

    def update_account_details(self) -> None:
        if not self.require_user_login(): return
        assert self.logged_in_user is not None
        acc = self.logged_in_user
        assert acc is not None
        print("Update Options:\n1. Name\n2. Email\n3. Phone\n4. Password")
        choice = input("Your choice: ").strip()
        if choice == '1':
            acc.name = input("Enter new name: ").strip()
        elif choice == '2':
            acc.email = input("Enter new email: ").strip()
        elif choice == '3':
            acc.phone = input("Enter new phone: ").strip()
        elif choice == '4':
            while True:
                p1 = getpass.getpass("New password: ")
                p2 = getpass.getpass("Confirm new password: ")
                if p1 != p2:
                    print("Passwords do not match.")
                else:
                    acc.password_hash = hash_password(p1)
                    break
        else:
            print("Invalid choice.")
            return
        self.save_accounts()
        log_audit('UPDATE_ACCOUNT', acc.number)
        print("Details updated.")

    def close_account(self) -> None:
        if not self.require_user_login(): return
        assert self.logged_in_user is not None
        acc_num = self.logged_in_user.number
        confirm = input("Are you sure you want to close your account? (y/n): ").strip().lower()
        if confirm == 'y':
            del self.accounts[acc_num]
            self.save_accounts()
            log_audit('CLOSE_ACCOUNT', acc_num)
            self.logged_in_user = None
            print("Account closed successfully.")
        else:
            print("Cancellation confirmed. Account not closed.")

    def list_accounts(self) -> None:
        print(f"{'AccNo':<8} {'Name':<20} {'Email':<25} {'Phone':<12} {'Bal':>10}")
        print('-'*75)
        for acc in self.accounts.values():
            print(f"{acc.number:<8} {acc.name:<20} {acc.email:<25} {acc.phone:<12} {acc.balance:>10.2f}")
        log_audit('LIST_ACCOUNTS')

    def search_accounts(self) -> None:
        query = input("Enter name, email, or account number: ").strip().lower()
        found = False
        for acc in self.accounts.values():
            if query in acc.number or query in acc.name.lower() or query in acc.email.lower():
                print(f"Found: {acc.number} | {acc.name} | {acc.email} | Balance: {acc.balance:.2f}")
                found = True
        if not found:
            print("No matching accounts.")
        log_audit('SEARCH_ACCOUNTS', details=f"Query={query}")

    def analytics(self) -> None:
        total_acc = len(self.accounts)
        total_balance = sum(acc.balance for acc in self.accounts.values())
        richest = max(self.accounts.values(), key=lambda x: x.balance, default=None)
        print(f"Total Accounts: {total_acc}\nTotal Bank Balance: {total_balance:.2f}")
        if richest:
            print(f"Richest Account: {richest.number} ({richest.name}), Balance: {richest.balance:.2f}")
        log_audit('ANALYTICS')

    def export_statement(self) -> None:
        if not self.require_user_login(): return
        assert self.logged_in_user is not None
        filename = f"statement_{self.logged_in_user.number}.txt"
        with open(filename, 'w') as f:
            f.write(self.logged_in_user.statement_str())
        print(f"Statement exported to {filename}.")
        log_audit('EXPORT_STATEMENT', self.logged_in_user.number)

    # Loan Management
    def apply_loan(self) -> None:
        if not self.require_user_login(): return
        assert self.logged_in_user is not None
        principal = float(input("Enter loan amount: "))
        rate = float(input("Enter annual interest rate (%): "))
        term = int(input("Enter term (months): "))
        loan = Loan(self.logged_in_user.number, principal, rate, term)
        self.loans.setdefault(self.logged_in_user.number, []).append(loan)
        self.save_loans()
        self.logged_in_user.balance += principal
        tx = Transaction(self.logged_in_user.number, 'LOAN_DISBURSAL', principal, self.logged_in_user.balance)
        Bank.append_transaction(tx)
        print(f"Loan approved. Disbursed {principal:.2f} to your account.")
        log_audit('LOAN_APPLY', self.logged_in_user.number, f"Amt={principal}")

    def view_loans(self) -> None:
        if not self.require_user_login(): return
        assert self.logged_in_user is not None
        my_loans = self.loans.get(self.logged_in_user.number, [])
        if not my_loans:
            print("No loans found.")
            return
        for i, loan in enumerate(my_loans, 1):
            print(f"Loan {i}: Principal={loan.principal:.2f}, Rate={loan.interest_rate:.2f}%, Term={loan.term_months}m, Balance={loan.balance:.2f}")
        log_audit('VIEW_LOANS', self.logged_in_user.number)

    def make_loan_payment(self) -> None:
        if not self.require_user_login(): return
        assert self.logged_in_user is not None
        my_loans = self.loans.get(self.logged_in_user.number, [])
        if not my_loans:
            print("No loans to pay.")
            return
        self.view_loans()
        idx = int(input("Select loan number to pay: ")) - 1
        if idx < 0 or idx >= len(my_loans):
            print("Invalid selection.")
            return
        amt = float(input("Enter payment amount: "))
        loan = my_loans[idx]
        try:
            loan.make_payment(amt)
            self.save_loans()
            print(f"Paid {amt:.2f}. Remaining balance: {loan.balance:.2f}")
        except Exception as e:
            print(f"Error: {e}")
    # Admin stuff
    def admin_login(self) -> None:
        user = input("Admin username: ").strip()
        pwd = getpass.getpass("Password: ")
        hashed = self.admins.get(user)
        if hashed and verify_password(pwd, hashed):
            self.logged_in_admin = user
            print(f"Admin {user} logged in.")
            log_audit('ADMIN_LOGIN', details=f"Admin={user}")
        else:
            print("Invalid admin credentials.")

    def admin_logout(self) -> None:
        if self.logged_in_admin:
            log_audit('ADMIN_LOGOUT', details=f"Admin={self.logged_in_admin}")
            print(f"Admin {self.logged_in_admin} logged out.")
            self.logged_in_admin = None
        else:
            print("No admin is currently logged in.")

    def require_admin_login(self) -> bool:
        if not self.logged_in_admin:
            print("Admin privileges required.")
            return False
        return True

    def freeze_account_admin(self) -> None:
        if not self.require_admin_login(): return
        acc_num = input("Enter account number to freeze: ").strip()
        acc = self.accounts.get(acc_num)
        if not acc:
            print("Account not found.")
            return
        acc.is_frozen = True
        self.save_accounts()
        print(f"Account {acc_num} frozen.")
        log_audit('ADMIN_FREEZE', acc_num)

    def unfreeze_account_admin(self) -> None:
        if not self.require_admin_login(): return
        acc_num = input("Enter account number to unfreeze: ").strip()
        acc = self.accounts.get(acc_num)
        if not acc:
            print("Account not found.")
            return
        acc.is_frozen = False
        self.save_accounts()
        print(f"Account {acc_num} unfrozen.")
        log_audit('ADMIN_UNFREEZE', acc_num)

    def view_audit_logs(self) -> None:
        if not self.require_admin_login(): return
        if os.path.exists(AUDIT_LOG_FILE):
            with open(AUDIT_LOG_FILE, 'r') as f:
                print(f.read())
        else:
            print("No audit logs found.")

    def run(self) -> None:
        while True:
            clear_screen()
            print("Welcome to OmniBank Management System")
            print("--------------------------------------")
            print("1. Register  2. Login  3. Logout  4. Check Balance")
            print("5. Deposit   6. Withdraw 7. Transfer  8. Statement")
            print("9. Apply Loan 10. View Loans 11. Pay Loan")
            print("12. Update Details")
            print("13. Close Account 14. Export Statement")
            print("15. Analytics")
            print("16. Search Accounts 17. List Accounts")
            print("18. Admin Login 19. Admin Logout")
            print("20. Freeze Account 21. Unfreeze Account")
            print("22. View Audit Logs")
            print("23. Save & Exit")
            print("--------------------------------------")
            if self.logged_in_user:
                print(f"User: {self.logged_in_user.name} (A/C {self.logged_in_user.number})")
            if self.logged_in_admin:
                print(f"Admin: {self.logged_in_admin}")
            choice = input("Choose an option: ").strip()
            try:
                if choice == '1': self.register_account()
                elif choice == '2': self.login()
                elif choice == '3': self.logout()
                elif choice == '4': self.check_balance()
                elif choice == '5': self.deposit_money()
                elif choice == '6': self.withdraw_money()
                elif choice == '7': self.transfer_funds()
                elif choice == '8': self.view_statement()
                elif choice == '9': self.apply_loan()
                elif choice == '10': self.view_loans()
                elif choice == '11': self.make_loan_payment()
                elif choice == '12': self.update_account_details()
                elif choice == '13': self.close_account()
                elif choice == '14': self.export_statement()
                elif choice == '15': self.analytics()
                elif choice == '16': self.search_accounts()
                elif choice == '17': self.list_accounts()
                elif choice == '18': self.admin_login()
                elif choice == '19': self.admin_logout()
                elif choice == '20': self.freeze_account_admin()
                elif choice == '21': self.unfreeze_account_admin()
                elif choice == '22': self.view_audit_logs()
                elif choice == '23':
                    self.save_accounts()
                    self.save_loans()
                    print("Goodbye.")
                    break
                else:
                    print("Invalid choice.")
            except Exception as e:
                print(f"Error: {e}")
            input("\nPress Enter to continue...")

if __name__ == '__main__':
    bank = Bank()
    bank.run()
