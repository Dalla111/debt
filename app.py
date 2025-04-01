from flask import Flask, render_template, request, redirect, url_for, flash
from collections import defaultdict
import os
import json
from datetime import datetime
from pathlib import Path

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY') or 'dev-secret-key'

# Configuration
DATA_DIR = Path('/var/lib/render/data/') if os.environ.get('RENDER') else Path.cwd()
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATA_FILE = DATA_DIR / 'data.json'
SETTLEMENT_PASSWORD = "c17jwala"  # Password for sensitive operations

# Consistent member names
initial_members = [
    'Monil', 'Mayank', 'danveer', 'shlok', 'het', 'atul', 'naman',
    'tanish pacheshwar', 'tanish', 'devesh', 'yash', 'pushkin', 'nishant'
]

def load_data():
    """Load data from JSON file or initialize if doesn't exist"""
    try:
        if DATA_FILE.exists():
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
                # Ensure all initial members exist
                for member in initial_members:
                    if member not in data['members']:
                        data['members'][member] = {'owed_to': {}, 'owed_by': {}, 'net_balance': 0}
                return data
    except (json.JSONDecodeError, FileNotFoundError):
        pass
    
    return {
        'transactions': [],
        'members': {m: {'owed_to': {}, 'owed_by': {}, 'net_balance': 0} for m in initial_members}
    }

def save_data(data):
    """Save data to JSON file with atomic write"""
    temp_file = DATA_FILE.with_suffix('.tmp')
    with open(temp_file, 'w') as f:
        json.dump(data, f, indent=2)
    temp_file.replace(DATA_FILE)

@app.before_request
def before_request():
    """Load data before each request"""
    app.config['data'] = load_data()

@app.teardown_request
def teardown_request(exception=None):
    """Save data after each request"""
    if hasattr(app, 'config') and 'data' in app.config:
        save_data(app.config['data'])

@app.route('/')
def home():
    """Home page showing all members and balances"""
    data = app.config['data']
    members = data['members']
    
    # Calculate net balances
    for name, member in members.items():
        member['net_balance'] = round(
            sum(member['owed_to'].values()) - sum(member['owed_by'].values()),
            2
        )
    
    return render_template('home.html', 
                         members=members,
                         total_transactions=len(data['transactions']))

@app.route('/add_transaction/<lender>', methods=['GET', 'POST'])
def add_transaction(lender):
    """Add new transaction with self-inclusion option"""
    data = app.config['data']
    members = data['members']
    
    if request.method == 'POST':
        # Check if this is password verification step
        if 'verify_password' in request.form:
            if request.form.get('password', '').strip() != SETTLEMENT_PASSWORD:
                flash('Incorrect password', 'error')
                return redirect(url_for('add_transaction', lender=lender))
            # Password verified - show transaction form
            return render_template('add_transaction_form.html',
                                lender=lender,
                                all_members=[m for m in members.keys() if m != lender])
        
        # Process the actual transaction
        try:
            amount = float(request.form['amount'])
            borrowers = request.form.getlist('borrowers')
            include_self = request.form.get('include_self') == 'on'
            description = request.form.get('description', '').strip()
            
            if not borrowers:
                flash('Please select at least one borrower', 'error')
                return redirect(url_for('add_transaction', lender=lender))
            
            if amount <= 0:
                flash('Amount must be positive', 'error')
                return redirect(url_for('add_transaction', lender=lender))
            
            # Handle self-inclusion
            if include_self and lender not in borrowers:
                borrowers.append(lender)
            
            split_amount = amount / len(borrowers)
            
            # Record transaction
            transaction = {
                'lender': lender,
                'amount': amount,
                'borrowers': borrowers,
                'description': description,
                'split_amount': split_amount,
                'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'include_self': include_self
            }
            data['transactions'].append(transaction)
            
            # Update member balances
            for borrower in borrowers:
                if borrower != lender:
                    members[lender]['owed_to'][borrower] = round(
                        members[lender]['owed_to'].get(borrower, 0) + split_amount,
                        2
                    )
                    members[borrower]['owed_by'][lender] = round(
                        members[borrower]['owed_by'].get(lender, 0) + split_amount,
                        2
                    )
            
            flash('Transaction added successfully!', 'success')
            return redirect(url_for('home'))
        
        except ValueError:
            flash('Invalid amount entered', 'error')
            return redirect(url_for('add_transaction', lender=lender))
    
    # GET request - show password verification
    return render_template('add_transaction_verify.html', lender=lender)

@app.route('/settle', methods=['GET', 'POST'])
def settle_debts():
    """Password-protected settlement plan"""
    if request.method == 'POST':
        if request.form.get('password', '').strip() != SETTLEMENT_PASSWORD:
            flash('Incorrect password', 'error')
            return redirect(url_for('settle_debts'))
        
        # Password verified - calculate settlements
        data = app.config['data']
        members = data['members']
        
        # Calculate net balances
        balances = {}
        for name, member in members.items():
            balances[name] = round(
                sum(member['owed_to'].values()) - sum(member['owed_by'].values()),
                2
            )
        
        creditors = {k: v for k, v in balances.items() if v > 0}
        debtors = {k: -v for k, v in balances.items() if v < 0}
        
        creditors = sorted(creditors.items(), key=lambda x: -x[1])
        debtors = sorted(debtors.items(), key=lambda x: -x[1])
        
        settlements = []
        i = j = 0
        while i < len(creditors) and j < len(debtors):
            cr, cr_amt = creditors[i]
            dr, dr_amt = debtors[j]
            
            settle = min(cr_amt, dr_amt)
            settlements.append({
                'from': dr,
                'to': cr,
                'amount': round(settle, 2)
            })
            
            cr_amt -= settle
            dr_amt -= settle
            
            creditors[i] = (cr, cr_amt)
            debtors[j] = (dr, dr_amt)
            
            if cr_amt <= 0.01:
                i += 1
            if dr_amt <= 0.01:
                j += 1
        
        return render_template('settlements.html', 
                            settlements=settlements,
                            total=round(sum(s['amount'] for s in settlements), 2))
    
    # GET request - show password form
    return render_template('settle_password.html')

@app.route('/report/<member_name>')
def member_report(member_name):
    """Generate detailed report for a member"""
    data = app.config['data']
    
    if member_name not in data['members']:
        flash('Member not found', 'error')
        return redirect(url_for('home'))
    
    member_data = data['members'][member_name]
    transactions = []
    
    for t in data['transactions']:
        if t['lender'] == member_name or member_name in t['borrowers']:
            transactions.append(t)
    
    # Calculate totals
    total_lent = sum(t['amount'] for t in transactions if t['lender'] == member_name)
    total_borrowed = sum(
        t['split_amount'] for t in transactions 
        if member_name in t['borrowers'] and t['lender'] != member_name
    )
    
    return render_template('report.html',
                         member_name=member_name,
                         member_data=member_data,
                         transactions=transactions,
                         total_lent=total_lent,
                         total_borrowed=total_borrowed)

@app.route('/reset', methods=['POST'])
def reset_data():
    """Password-protected data reset"""
    if request.form.get('password', '').strip() != SETTLEMENT_PASSWORD:
        flash('Incorrect password', 'error')
        return redirect(url_for('home'))
    
    data = {
        'transactions': [],
        'members': {m: {'owed_to': {}, 'owed_by': {}, 'net_balance': 0} 
                  for m in initial_members}
    }
    app.config['data'] = data
    save_data(data)
    flash('All data has been reset', 'success')
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)