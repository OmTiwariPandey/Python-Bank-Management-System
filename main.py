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

print('-'*50)

print('*'*50)

print('\tBank Management Software -by Om')

print('Hello Bahini')

print('*'*50)

print('-'*50)

accounts = {}


def rand():

    num = random.randint(100000, 999999)
    return num


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


def check_balance(account_num):

  if account_num not in accounts:
    print("Error: Account does not exist")

  else:
    balance = accounts[account_num][0]
    print(f"Balance: {balance}")

  print('Operation Done Successfully.\n')


def deposit(account_num, amount):

  if account_num not in accounts:
    print("Error: Account does not exist")

  else:
    balance = accounts[account_num][0]
    transaction_history = accounts[account_num][1]
    accounts[account_num] = (balance + amount, transaction_history)
    transaction_history.append(f"Deposited Rs{amount}")
    balance = accounts[account_num][0]
    print(f'Current Balance: {balance}')

  print('Operation Done Successfully.\n')

def withdraw(account_num, amount):

  if account_num not in accounts:
    print("Error: Account does not exist")

  else:
    balance = accounts[account_num][0]
    transaction_history = accounts[account_num][1]

    if balance < amount:
      print("Error: Insufficient balance")
      balance = accounts[account_num][0]
      print(f'Current Balance: {balance}')

    else:
      accounts[account_num] = (balance - amount, transaction_history)
      transaction_history.append(f"Withdrew Rs{amount}")
      balance = accounts[account_num][0]
      print(f'Current Balance: {balance}')

  print('Operation Done Successfully.\n')

def display_all():
  bal=0

  print('Account| Balance')
  for account_num, (balance, _) in accounts.items():
    bal=bal+balance
    print(f"{account_num} | {balance}")
  print(f'Total Amount in Bank= {bal}')
  print('Operation Done Successfully.\n')
  


def print_bank_statement(account_num):

  if account_num not in accounts:
    print("Error: Account does not exist")
    
  else:
      
    balance = accounts[account_num][0]
    transaction_history = accounts[account_num][1]
    print(f"Bank statement for account {account_num}:")
    print(f"Balance: {balance}")
    print("Transaction history:")
    
    print('-'*60)
    
    
    balance = accounts[account_num][0]
    print(f'Current Balance: {balance}')

    for transaction in transaction_history:
      print(transaction)
  print('Operation Done Successfully.\n')


def load_data():

  global accounts
  with open('bank_data1.csv', 'r') as file:
    reader = csv.reader(file)
    accounts = {row[0]: (float(row[1]), row[2:]) for row in reader}
  print('\nLoading Data...')
  print('Operation Done Successfully.\n')
    
  
def save_data():
   with open('bank_data1.csv', 'w', newline='') as file:
       writer = csv.writer(file)
       for account_num, (balance, transaction_history) in accounts.items():
           transaction_history_str = ','.join(transaction_history)
           writer.writerow([account_num, balance, transaction_history_str])
   print('Data Saved Successfully.\n')


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
    
    
