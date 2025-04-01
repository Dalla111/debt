from flask import Flask, render_template, request, redirect, url_for
from collections import defaultdict

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Needed for session management

# Data structure to store all transactions and member balances
transactions = []
members = defaultdict(lambda: {'owed_to': {}, 'owed_by': {}, 'net_balance': 0})

# Initialize with sample members or load from database
initial_members = ['Monil', 'Mayank', 'danveer', 'shlok','het','atul','naman','tanish pacheshwar','tansih','devesh','yash','pushkin','nishant']
for member in initial_members:
    members[member]  # Initialize all members

@app.route('/')
def home():
    # Calculate net balances for all members
    for member in members.values():
        member['net_balance'] = sum(member['owed_to'].values()) - sum(member['owed_by'].values())
    return render_template('home.html', members=members)

@app.route('/add_transaction/<lender>', methods=['GET', 'POST'])
def add_transaction(lender):
    if request.method == 'POST':
        amount = float(request.form['amount'])
        borrowers = request.form.getlist('borrowers')
        description = request.form.get('description', '')
        
        if not borrowers:
            return redirect(url_for('add_transaction', lender=lender))
        
        split_amount = amount / len(borrowers)
        
        # Record transaction
        transactions.append({
            'lender': lender,
            'amount': amount,
            'borrowers': borrowers,
            'description': description,
            'split_amount': split_amount
        })
        
        # Update member balances
        for borrower in borrowers:
            if borrower != lender:
                members[lender]['owed_to'][borrower] = members[lender]['owed_to'].get(borrower, 0) + split_amount
                members[borrower]['owed_by'][lender] = members[borrower]['owed_by'].get(lender, 0) + split_amount
        
        return redirect(url_for('home'))
    
    return render_template('add_transaction.html', 
                         lender=lender, 
                         all_members=initial_members)

@app.route('/settle')
def settle_debts():
    # Debt settlement logic (as previous)
    balances = {}
    for member in members:
        balances[member] = members[member]['net_balance']
    
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
        settlements.append(f"{dr} should pay ₹{settle:.2f} to {cr}")
        
        cr_amt -= settle
        dr_amt -= settle
        
        if cr_amt == 0:
            i += 1
        if dr_amt == 0:
            j += 1
    
    return render_template('settlements.html', settlements=settlements)
@app.route('/report/<member_name>')
def member_report(member_name):
    member_data = members[member_name]
    
    # Get all related transactions
    related_transactions = [
        t for t in transactions
        if t['lender'] == member_name or member_name in t['borrowers']
    ]
    
    return render_template('report.html',
                         member_name=member_name,
                         member_data=member_data,
                         transactions=related_transactions)

if __name__ == '__main__':
    app.run(debug=True)