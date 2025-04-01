from flask import Flask, render_template, request, redirect, url_for, flash
from collections import defaultdict
import os
import json
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY') or 'dev-secret-key'

# Initialize data storage
DATA_FILE = 'data.json'

# Sample initial members
initial_members = [
    'Monil', 'Mayank', 'danveer', 'shlok', 'het', 'atul', 'naman',
    'tanish pacheshwar', 'tanish', 'devesh', 'yash', 'pushkin', 'nishant'
]

def load_data():
    """Load data from JSON file or initialize if doesn't exist"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {
        'transactions': [],
        'members': {m: {'owed_to': {}, 'owed_by': {}, 'net_balance': 0} for m in initial_members}
    }

def save_data(data):
    """Save data to JSON file"""
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

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
    for member in members.values():
        member['net_balance'] = (
            sum(member['owed_to'].values()) - sum(member['owed_by'].values()
        ))
    
    return render_template('home.html', 
                         members=members,
                         total_transactions=len(data['transactions']))

@app.route('/add_transaction/<lender>', methods=['GET', 'POST'])
def add_transaction(lender):
    """Add new transaction"""
    data = app.config['data']
    members = data['members']
    
    if request.method == 'POST':
        try:
            amount = float(request.form['amount'])
            borrowers = request.form.getlist('borrowers')
            description = request.form.get('description', '').strip()
            
            if not borrowers:
                flash('Please select at least one borrower', 'error')
                return redirect(url_for('add_transaction', lender=lender))
            
            if amount <= 0:
                flash('Amount must be positive', 'error')
                return redirect(url_for('add_transaction', lender=lender))
            
            split_amount = amount / len(borrowers)
            
            # Record transaction
            transaction = {
                'lender': lender,
                'amount': amount,
                'borrowers': borrowers,
                'description': description,
                'split_amount': split_amount,
                'date': datetime.now().strftime('%Y-%m-%d %H:%M')
            }
            data['transactions'].append(transaction)
            
            # Update member balances
            for borrower in borrowers:
                if borrower != lender:
                    members[lender]['owed_to'][borrower] = (
                        members[lender]['owed_to'].get(borrower, 0) + split_amount
                    )
                    members[borrower]['owed_by'][lender] = (
                        members[borrower]['owed_by'].get(lender, 0) + split_amount
                    )
            
            flash('Transaction added successfully!', 'success')
            return redirect(url_for('home'))
        
        except ValueError:
            flash('Invalid amount entered', 'error')
            return redirect(url_for('add_transaction', lender=lender))
    
    return render_template('add_transaction.html', 
                         lender=lender, 
                         all_members=[m for m in members.keys() if m != lender])

@app.route('/settle')
def settle_debts():
    """Calculate optimal settlement plan"""
    data = app.config['data']
    members = data['members']
    
    # Calculate net balances
    balances = {}
    for name, member in members.items():
        balances[name] = sum(member['owed_to'].values()) - sum(member['owed_by'].values())
    
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
        
        if cr_amt == 0:
            i += 1
        if dr_amt == 0:
            j += 1
    
    return render_template('settlements.html', 
                         settlements=settlements,
                         total=sum(s['amount'] for s in settlements))

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
    """Reset all data (for testing)"""
    if request.form.get('confirm') == 'RESET':
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