import json
import uuid
import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file, send_from_directory
from functools import wraps
import hashlib
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.units import inch
from io import BytesIO
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'transport_system_secret_key_2024'

# Data files
DATA_FILE = 'trips.json'
CUSTOMERS_FILE = 'customers.json'
TRUCKS_FILE = 'trucks.json'
USERS_FILE = 'users.json'
LOCATIONS_FILE = 'locations.json'
DOCUMENTS_FILE = 'documents.json'

# Upload folder
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create upload folder if it doesn't exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def load_data(filename):
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_data(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

def load_trips():
    return load_data(DATA_FILE)

def save_trips(trips):
    save_data(DATA_FILE, trips)

def load_customers():
    return load_data(CUSTOMERS_FILE)

def save_customers(customers):
    save_data(CUSTOMERS_FILE, customers)

def load_users():
    return load_data(USERS_FILE)

def save_users(users):
    save_data(USERS_FILE, users)

def load_locations():
    return load_data(LOCATIONS_FILE)

def save_locations(locations):
    save_data(LOCATIONS_FILE, locations)

def load_documents():
    return load_data(DOCUMENTS_FILE)

def save_documents(documents):
    save_data(DOCUMENTS_FILE, documents)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def load_locations():
    return load_data(LOCATIONS_FILE)

def save_locations(locations):
    save_data(LOCATIONS_FILE, locations)

def load_trucks():
    return load_data(TRUCKS_FILE)

def save_trucks(trucks):
    save_data(TRUCKS_FILE, trucks)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    return hash_password(password) == hashed

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        users = load_users()
        user = next((u for u in users if u['id'] == session['user_id']), None)
        if not user or user['role'] != 'admin':
            flash('Admin access required!', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def get_float_input(prompt):
    while True:
        try:
            return float(input(prompt))
        except ValueError:
            print("Please enter a valid number.")

def get_trip_by_id(trips, trip_id):
    for trip in trips:
        if trip['id'] == trip_id:
            return trip
    return None

def get_customer_by_name(customers, name):
    for customer in customers:
        if customer['name'].lower() == name.lower():
            return customer
    return None

def get_truck_by_number(trucks, number):
    for truck in trucks:
        if truck['number'].lower() == number.lower():
            return truck
    return None

def create_trip():
    print("\n🚛 STEP 1: Customer Booking / Load Entry")
    customers = load_customers()
    trucks = load_trucks()
    
    customer_name = input("Customer name: ").strip()
    # Auto-create customer if doesn't exist
    if not get_customer_by_name(customers, customer_name):
        print(f"New customer '{customer_name}' will be added.")
        customer = {
            'id': str(uuid.uuid4()),
            'name': customer_name,
            'phone': '',
            'email': '',
            'address': '',
            'total_trips': 0,
            'total_earnings': 0.0,
            'created_at': datetime.now().isoformat()
        }
        customers.append(customer)
        save_customers(customers)
    
    truck_number = input("Truck number: ").strip().upper()
    # Auto-create truck if doesn't exist
    if not get_truck_by_number(trucks, truck_number):
        print(f"New truck '{truck_number}' will be added.")
        truck = {
            'id': str(uuid.uuid4()),
            'number': truck_number,
            'model': '',
            'capacity': 0.0,
            'status': 'Available',
            'total_trips': 0,
            'total_earnings': 0.0,
            'added_at': datetime.now().isoformat()
        }
        trucks.append(truck)
        save_trucks(trucks)
    
    trip = {
        'id': str(uuid.uuid4()),
        'customer': customer_name,
        'pickup': input("Pickup location: ").strip(),
        'destination': input("Destination: ").strip(),
        'truck_number': truck_number,
        'load_type': input("Load type: ").strip(),
        'weight': get_float_input("Load weight (kg): "),
        'rate_per_km': get_float_input("Rate per km (₹): "),
        'distance_km': None,
        'loading_charges': 0.0,
        'total_fare': 0.0,
        'advance_paid': 0.0,
        'payments': [],  # list of payment records
        'expenses': [],  # list of expense records
        'status': 'Booked',
        'timestamp': datetime.now().isoformat()
    }
    
    trips = load_trips()
    trips.append(trip)
    save_trips(trips)
    
    # Update truck status
    update_truck_stats()
    
    print(f"\n✅ Trip created! ID: {trip['id']}")
    print("Details:")
    for k, v in trip.items():
        if k not in ['payments', 'expenses']:
            print(f"  {k}: {v}")

def update_distance():
    print("\n📏 STEP 2: Distance Calculation")
    trips = load_trips()
    if not trips:
        print("No trips found. Create a trip first.")
        return
    
    print("Available trips:")
    for trip in trips:
        if trip['distance_km'] is None:
            print(f"ID: {trip['id']} - {trip['customer']} ({trip['pickup']} → {trip['destination']})")
    
    trip_id = input("Enter trip ID to update distance: ").strip()
    trip = get_trip_by_id(trips, trip_id)
    if not trip:
        print("Trip not found.")
        return
    
    # For now, manual entry. Future: Google Maps API
    distance = get_float_input("Enter distance (km): ")
    trip['distance_km'] = distance
    save_trips(trips)
    print(f"✅ Distance updated: {distance} km")

def calculate_fare():
    print("\n💰 STEP 3: Fare Calculation")
    trips = load_trips()
    trip_id = input("Enter trip ID to calculate fare: ").strip()
    trip = get_trip_by_id(trips, trip_id)
    if not trip:
        print("Trip not found.")
        return
    
    if trip['distance_km'] is None:
        print("Distance not set. Update distance first.")
        return
    
    loading_charges = get_float_input("Loading charges (₹): ")
    trip['loading_charges'] = loading_charges
    trip['total_fare'] = (trip['distance_km'] * trip['rate_per_km']) + loading_charges
    save_trips(trips)
    print(f"✅ Fare calculated: ₹{trip['total_fare']}")
    print(f"   Distance: {trip['distance_km']} km × ₹{trip['rate_per_km']} = ₹{trip['distance_km'] * trip['rate_per_km']}")
    print(f"   Loading: ₹{loading_charges}")
    print(f"   Total: ₹{trip['total_fare']}")

def enter_advance_payment():
    print("\n💳 STEP 4: Advance Payment Entry")
    trips = load_trips()
    trip_id = input("Enter trip ID: ").strip()
    trip = get_trip_by_id(trips, trip_id)
    if not trip:
        print("Trip not found.")
        return
    
    if trip['total_fare'] == 0:
        print("Calculate fare first.")
        return
    
    amount = get_float_input("Advance payment amount (₹): ")
    trip['advance_paid'] = amount
    trip['payments'].append({
        'type': 'advance',
        'amount': amount,
        'timestamp': datetime.now().isoformat()
    })
    save_trips(trips)
    remaining = trip['total_fare'] - amount
    print(f"✅ Advance payment recorded: ₹{amount}")
    print(f"   Remaining: ₹{remaining}")

def start_trip():
    print("\n🚚 STEP 5: Trip Start")
    trips = load_trips()
    trip_id = input("Enter trip ID to start: ").strip()
    trip = get_trip_by_id(trips, trip_id)
    if not trip:
        print("Trip not found.")
        return
    
    trip['status'] = 'In Transit'
    save_trips(trips)
    print("✅ Trip started! Status: In Transit")
    print("📩 Notification: Trip started")

def update_payment():
    print("\n💰 STEP 7: Payment Updates")
    trips = load_trips()
    trip_id = input("Enter trip ID: ").strip()
    trip = get_trip_by_id(trips, trip_id)
    if not trip:
        print("Trip not found.")
        return
    
    amount = get_float_input("Payment amount received (₹): ")
    trip['payments'].append({
        'type': 'payment',
        'amount': amount,
        'timestamp': datetime.now().isoformat()
    })
    total_paid = sum(p['amount'] for p in trip['payments'])
    remaining = trip['total_fare'] - total_paid
    save_trips(trips)
    print(f"✅ Payment recorded: ₹{amount}")
    print(f"   Total paid: ₹{total_paid}")
    print(f"   Remaining: ₹{remaining}")
    print(f"📩 Notification: ₹{amount} received")

def mark_delivered():
    print("\n📦 STEP 9: Delivery Completion")
    trips = load_trips()
    trip_id = input("Enter trip ID: ").strip()
    trip = get_trip_by_id(trips, trip_id)
    if not trip:
        print("Trip not found.")
        return
    
    trip['status'] = 'Delivered'
    save_trips(trips)
    print("✅ Trip delivered!")
    print("📩 Notification: Reached destination")

def view_trip_details():
    print("\n📋 View Trip Details")
    trips = load_trips()
    trip_id = input("Enter trip ID: ").strip()
    trip = get_trip_by_id(trips, trip_id)
    if not trip:
        print("Trip not found.")
        return
    
    print(f"\nTrip ID: {trip['id']}")
    print(f"Customer: {trip['customer']}")
    print(f"Route: {trip['pickup']} → {trip['destination']}")
    print(f"Truck: {trip['truck_number']}")
    print(f"Load: {trip['load_type']} ({trip['weight']} kg)")
    print(f"Rate: ₹{trip['rate_per_km']}/km")
    print(f"Distance: {trip['distance_km']} km" if trip['distance_km'] else "Distance: Not set")
    print(f"Loading Charges: ₹{trip['loading_charges']}")
    print(f"Total Fare: ₹{trip['total_fare']}")
    
    total_paid = sum(p['amount'] for p in trip['payments'])
    total_expenses = sum(e['amount'] for e in trip.get('expenses', []))
    net_profit = trip['total_fare'] - total_expenses
    
    print(f"Total Paid: ₹{total_paid}")
    print(f"Remaining: ₹{trip['total_fare'] - total_paid}")
    print(f"Total Expenses: ₹{total_expenses}")
    print(f"Net Profit: ₹{net_profit}")
    print(f"Status: {trip['status']}")
    
    print("\nPayments:")
    if trip['payments']:
        for p in trip['payments']:
            print(f"  {p['type'].title()}: ₹{p['amount']} ({p['timestamp']})")
    else:
        print("  No payments recorded")
    
    print("\nExpenses:")
    if trip.get('expenses'):
        for e in trip['expenses']:
            print(f"  {e['type']}: ₹{e['amount']} - {e['description']} ({e['timestamp']})")
    else:
        print("  No expenses recorded")

def view_all_trips():
    print("\n📊 All Trips")
    trips = load_trips()
    if not trips:
        print("No trips found.")
        return
    
    for trip in trips:
        total_paid = sum(p['amount'] for p in trip['payments'])
        remaining = trip['total_fare'] - total_paid
        print(f"ID: {trip['id']} | {trip['customer']} | {trip['pickup']}→{trip['destination']} | Status: {trip['status']} | Paid: ₹{total_paid} | Remaining: ₹{remaining}")

# ===== CUSTOMER MANAGEMENT =====
def add_customer():
    print("\n👤 Add New Customer")
    customers = load_customers()
    
    name = input("Customer name: ").strip()
    if get_customer_by_name(customers, name):
        print("Customer already exists!")
        return
    
    customer = {
        'id': str(uuid.uuid4()),
        'name': name,
        'phone': input("Phone number: ").strip(),
        'email': input("Email: ").strip(),
        'address': input("Address: ").strip(),
        'total_trips': 0,
        'total_earnings': 0.0,
        'created_at': datetime.now().isoformat()
    }
    
    customers.append(customer)
    save_customers(customers)
    print(f"✅ Customer '{name}' added successfully!")

def view_customers():
    print("\n👥 All Customers")
    customers = load_customers()
    if not customers:
        print("No customers found.")
        return
    
    for customer in customers:
        print(f"Name: {customer['name']} | Phone: {customer['phone']} | Trips: {customer['total_trips']} | Earnings: ₹{customer['total_earnings']}")

def update_customer_stats():
    customers = load_customers()
    trips = load_trips()
    
    # Reset stats
    for customer in customers:
        customer['total_trips'] = 0
        customer['total_earnings'] = 0.0
    
    # Calculate from trips
    for trip in trips:
        if trip['status'] == 'Delivered':
            customer = get_customer_by_name(customers, trip['customer'])
            if customer:
                customer['total_trips'] += 1
                customer['total_earnings'] += trip['total_fare']
    
    save_customers(customers)

# ===== TRUCK MANAGEMENT =====
def add_truck():
    print("\n🚛 Add New Truck")
    trucks = load_trucks()
    
    number = input("Truck number: ").strip().upper()
    if get_truck_by_number(trucks, number):
        print("Truck already exists!")
        return
    
    truck = {
        'id': str(uuid.uuid4()),
        'number': number,
        'model': input("Model: ").strip(),
        'capacity': get_float_input("Capacity (tons): "),
        'status': 'Available',
        'total_trips': 0,
        'total_earnings': 0.0,
        'added_at': datetime.now().isoformat()
    }
    
    trucks.append(truck)
    save_trucks(trucks)
    print(f"✅ Truck '{number}' added successfully!")

def view_trucks():
    print("\n🚛 All Trucks")
    trucks = load_trucks()
    if not trucks:
        print("No trucks found.")
        return
    
    for truck in trucks:
        print(f"Number: {truck['number']} | Model: {truck['model']} | Capacity: {truck['capacity']}T | Status: {truck['status']} | Trips: {truck['total_trips']}")

def update_truck_stats():
    trucks = load_trucks()
    trips = load_trips()
    
    # Reset stats
    for truck in trucks:
        truck['total_trips'] = 0
        truck['total_earnings'] = 0.0
        truck['status'] = 'Available'
    
    # Calculate from trips
    for trip in trips:
        truck = get_truck_by_number(trucks, trip['truck_number'])
        if truck:
            if trip['status'] in ['In Transit', 'Booked']:
                truck['status'] = 'Busy'
            elif trip['status'] == 'Delivered':
                truck['total_trips'] += 1
                truck['total_earnings'] += trip['total_fare']
    
    save_trucks(trucks)

# ===== EXPENSE TRACKING =====
def add_expense():
    print("\n💸 Add Trip Expense")
    trips = load_trips()
    
    trip_id = input("Enter trip ID: ").strip()
    trip = get_trip_by_id(trips, trip_id)
    if not trip:
        print("Trip not found.")
        return
    
    if 'expenses' not in trip:
        trip['expenses'] = []
    
    expense = {
        'id': str(uuid.uuid4()),
        'type': input("Expense type (fuel/toll/maintenance/other): ").strip(),
        'amount': get_float_input("Amount (₹): "),
        'description': input("Description: ").strip(),
        'timestamp': datetime.now().isoformat()
    }
    
    trip['expenses'].append(expense)
    save_trips(trips)
    print(f"✅ Expense added: ₹{expense['amount']} for {expense['type']}")

# ===== REPORTS =====
def generate_reports():
    print("\n📈 Reports Menu")
    print("1. Daily Earnings Report")
    print("2. Weekly Earnings Report") 
    print("3. Monthly Earnings Report")
    print("4. Pending Payments Report")
    print("5. Profit/Loss Report")
    print("0. Back")
    
    choice = input("Choose report: ").strip()
    
    if choice == '1':
        daily_report()
    elif choice == '2':
        weekly_report()
    elif choice == '3':
        monthly_report()
    elif choice == '4':
        pending_payments_report()
    elif choice == '5':
        profit_loss_report()
    elif choice == '0':
        return
    else:
        print("Invalid choice.")

def daily_report():
    print("\n📅 Daily Earnings Report")
    today = datetime.now().date()
    trips = load_trips()
    
    total_earnings = 0.0
    completed_trips = 0
    
    for trip in trips:
        trip_date = datetime.fromisoformat(trip['timestamp']).date()
        if trip_date == today and trip['status'] == 'Delivered':
            total_earnings += trip['total_fare']
            completed_trips += 1
    
    print(f"Date: {today}")
    print(f"Completed Trips: {completed_trips}")
    print(f"Total Earnings: ₹{total_earnings}")

def weekly_report():
    print("\n📊 Weekly Earnings Report")
    today = datetime.now().date()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    
    trips = load_trips()
    total_earnings = 0.0
    completed_trips = 0
    
    for trip in trips:
        trip_date = datetime.fromisoformat(trip['timestamp']).date()
        if week_start <= trip_date <= week_end and trip['status'] == 'Delivered':
            total_earnings += trip['total_fare']
            completed_trips += 1
    
    print(f"Week: {week_start} to {week_end}")
    print(f"Completed Trips: {completed_trips}")
    print(f"Total Earnings: ₹{total_earnings}")

def monthly_report():
    print("\n📈 Monthly Earnings Report")
    now = datetime.now()
    current_month = now.month
    current_year = now.year
    
    trips = load_trips()
    total_earnings = 0.0
    completed_trips = 0
    
    for trip in trips:
        trip_date = datetime.fromisoformat(trip['timestamp'])
        if trip_date.month == current_month and trip_date.year == current_year and trip['status'] == 'Delivered':
            total_earnings += trip['total_fare']
            completed_trips += 1
    
    print(f"Month: {now.strftime('%B %Y')}")
    print(f"Completed Trips: {completed_trips}")
    print(f"Total Earnings: ₹{total_earnings}")

def pending_payments_report():
    print("\n⏳ Pending Payments Report")
    trips = load_trips()
    pending_trips = []
    
    for trip in trips:
        total_paid = sum(p['amount'] for p in trip['payments'])
        remaining = trip['total_fare'] - total_paid
        if remaining > 0:
            pending_trips.append({
                'trip': trip,
                'remaining': remaining
            })
    
    if not pending_trips:
        print("No pending payments!")
        return
    
    total_pending = sum(p['remaining'] for p in pending_trips)
    print(f"Total Pending Amount: ₹{total_pending}")
    print(f"Trips with Pending Payments: {len(pending_trips)}")
    
    for item in pending_trips:
        trip = item['trip']
        print(f"  {trip['id']}: {trip['customer']} - ₹{item['remaining']} pending")

def profit_loss_report():
    print("\n💰 Profit/Loss Report")
    trips = load_trips()
    
    total_revenue = 0.0
    total_expenses = 0.0
    completed_trips = 0
    
    for trip in trips:
        if trip['status'] == 'Delivered':
            total_revenue += trip['total_fare']
            completed_trips += 1
            
            if 'expenses' in trip:
                for expense in trip['expenses']:
                    total_expenses += expense['amount']
    
    profit = total_revenue - total_expenses
    
    print(f"Completed Trips: {completed_trips}")
    print(f"Total Revenue: ₹{total_revenue}")
    print(f"Total Expenses: ₹{total_expenses}")
    print(f"Net Profit/Loss: ₹{profit}")
    
    if profit > 0:
        print("✅ Profitable period!")
    elif profit < 0:
        print("⚠️ Loss making period!")
    else:
        print("😐 Break-even period!")

# ===== SEARCH & FILTER =====
def search_trips():
    print("\n🔍 Search Trips")
    print("Search by:")
    print("1. Customer name")
    print("2. Truck number")
    print("3. Status")
    print("4. Date range")
    
    choice = input("Choose search type: ").strip()
    trips = load_trips()
    
    if choice == '1':
        customer = input("Customer name: ").strip().lower()
        results = [t for t in trips if customer in t['customer'].lower()]
    elif choice == '2':
        truck = input("Truck number: ").strip().lower()
        results = [t for t in trips if truck in t['truck_number'].lower()]
    elif choice == '3':
        status = input("Status (Booked/In Transit/Delivered): ").strip()
        results = [t for t in trips if t['status'] == status]
    elif choice == '4':
        start_date = input("Start date (YYYY-MM-DD): ").strip()
        end_date = input("End date (YYYY-MM-DD): ").strip()
        try:
            start = datetime.fromisoformat(start_date).date()
            end = datetime.fromisoformat(end_date).date()
            results = []
            for t in trips:
                trip_date = datetime.fromisoformat(t['timestamp']).date()
                if start <= trip_date <= end:
                    results.append(t)
        except:
            print("Invalid date format!")
            return
    else:
        print("Invalid choice!")
        return
    
    if not results:
        print("No trips found.")
        return
    
    print(f"\nFound {len(results)} trips:")
    for trip in results:
        total_paid = sum(p['amount'] for p in trip['payments'])
        remaining = trip['total_fare'] - total_paid
        print(f"ID: {trip['id']} | {trip['customer']} | {trip['status']} | Paid: ₹{total_paid} | Remaining: ₹{remaining}")

# ===== TRIP EDITING =====
def edit_trip():
    print("\n✏️ Edit Trip")
    trips = load_trips()
    trip_id = input("Enter trip ID to edit: ").strip()
    trip = get_trip_by_id(trips, trip_id)
    
    if not trip:
        print("Trip not found.")
        return
    
    print("Current details:")
    print(f"Customer: {trip['customer']}")
    print(f"Pickup: {trip['pickup']}")
    print(f"Destination: {trip['destination']}")
    print(f"Status: {trip['status']}")
    
    print("\nWhat to edit?")
    print("1. Customer name")
    print("2. Pickup location")
    print("3. Destination")
    print("4. Status")
    
    choice = input("Choose: ").strip()
    
    if choice == '1':
        trip['customer'] = input("New customer name: ").strip()
    elif choice == '2':
        trip['pickup'] = input("New pickup location: ").strip()
    elif choice == '3':
        trip['destination'] = input("New destination: ").strip()
    elif choice == '4':
        print("Available statuses: Booked, In Transit, Delivered")
        trip['status'] = input("New status: ").strip()
    else:
        print("Invalid choice!")
        return
    
    save_trips(trips)
    print("✅ Trip updated successfully!")
    
    # Update stats
    update_customer_stats()
    update_truck_stats()

# ===== PDF REPORT GENERATION =====

def generate_pdf_report(report_type='summary'):
    """Generate PDF report with transport system data"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=1  # Center alignment
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=20,
    )
    
    normal_style = styles['Normal']
    
    story = []
    
    # Title
    story.append(Paragraph("KALAWATI TRANSPORT", title_style))
    story.append(Paragraph("Business Report", subtitle_style))
    story.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", normal_style))
    story.append(Spacer(1, 20))
    
    # Load data
    trips = load_trips()
    customers = load_customers()
    trucks = load_trucks()
    
    if report_type == 'summary':
        # Summary Statistics
        story.append(Paragraph("Summary Statistics", subtitle_style))
        
        # Calculate statistics
        today = datetime.now().date()
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        daily_earnings = sum(t['total_fare'] for t in trips
                            if datetime.fromisoformat(t['timestamp']).date() == today
                            and t['status'] == 'Delivered')
        
        monthly_earnings = sum(t['total_fare'] for t in trips
                              if datetime.fromisoformat(t['timestamp']).month == current_month
                              and datetime.fromisoformat(t['timestamp']).year == current_year
                              and t['status'] == 'Delivered')
        
        total_revenue = sum(t['total_fare'] for t in trips if t['status'] == 'Delivered')
        total_expenses = 0
        for trip in trips:
            if trip['status'] == 'Delivered':
                total_expenses += sum(e['amount'] for e in trip.get('expenses', []))
        
        net_profit = total_revenue - total_expenses
        
        # Pending payments
        pending_payments = []
        total_pending = 0
        for trip in trips:
            total_paid = sum(p['amount'] for p in trip['payments'])
            remaining = trip['total_fare'] - total_paid
            if remaining > 0:
                pending_payments.append({'trip': trip, 'remaining': remaining})
                total_pending += remaining
        
        # Summary table
        summary_data = [
            ['Metric', 'Value'],
            ['Total Trips', str(len(trips))],
            ['Completed Trips', str(len([t for t in trips if t['status'] == 'Delivered']))],
            ['Total Customers', str(len(customers))],
            ['Total Trucks', str(len(trucks))],
            ['Today\'s Earnings', f'₹{daily_earnings:.2f}'],
            ['Monthly Earnings', f'₹{monthly_earnings:.2f}'],
            ['Total Revenue', f'₹{total_revenue:.2f}'],
            ['Total Expenses', f'₹{total_expenses:.2f}'],
            ['Net Profit', f'₹{net_profit:.2f}'],
            ['Pending Payments', f'₹{total_pending:.2f}']
        ]
        
        summary_table = Table(summary_data)
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(summary_table)
        story.append(Spacer(1, 20))
        
        # Recent Trips
        story.append(Paragraph("Recent Trips", subtitle_style))
        recent_trips = sorted(trips, key=lambda x: x['timestamp'], reverse=True)[:10]
        
        if recent_trips:
            trip_data = [['ID', 'Customer', 'Route', 'Status', 'Fare', 'Date']]
            for trip in recent_trips:
                trip_date = datetime.fromisoformat(trip['timestamp']).strftime('%Y-%m-%d')
                trip_data.append([
                    trip['id'][:8] + '...',
                    trip['customer'][:20],
                    f"{trip['pickup']} → {trip['destination']}"[:30],
                    trip['status'],
                    f'₹{trip["total_fare"]:.2f}',
                    trip_date
                ])
            
            trip_table = Table(trip_data)
            trip_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
            ]))
            
            story.append(trip_table)
        
    elif report_type == 'trips':
        # Detailed trips report
        story.append(Paragraph("All Trips Report", subtitle_style))
        
        if trips:
            trip_data = [['ID', 'Customer', 'Route', 'Truck', 'Status', 'Fare', 'Paid', 'Remaining', 'Date']]
            for trip in trips:
                total_paid = sum(p['amount'] for p in trip['payments'])
                remaining = trip['total_fare'] - total_paid
                trip_date = datetime.fromisoformat(trip['timestamp']).strftime('%Y-%m-%d')
                
                trip_data.append([
                    trip['id'][:8] + '...',
                    trip['customer'][:15],
                    f"{trip['pickup']} → {trip['destination']}"[:25],
                    trip['truck_number'],
                    trip['status'],
                    f'₹{trip["total_fare"]:.2f}',
                    f'₹{total_paid:.2f}',
                    f'₹{remaining:.2f}',
                    trip_date
                ])
            
            trip_table = Table(trip_data)
            trip_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
            ]))
            
            story.append(trip_table)
    
    elif report_type == 'customers':
        # Customers report
        story.append(Paragraph("Customers Report", subtitle_style))
        
        if customers:
            customer_data = [['Name', 'Phone', 'Email', 'Total Trips', 'Total Earnings']]
            for customer in customers:
                customer_data.append([
                    customer['name'][:20],
                    customer.get('phone', '')[:15],
                    customer.get('email', '')[:20],
                    str(customer['total_trips']),
                    f'₹{customer["total_earnings"]:.2f}'
                ])
            
            customer_table = Table(customer_data)
            customer_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
            ]))
            
            story.append(customer_table)
    
    elif report_type == 'trucks':
        # Trucks report
        story.append(Paragraph("Trucks Report", subtitle_style))
        
        if trucks:
            truck_data = [['Number', 'Model', 'Capacity', 'Status', 'Total Trips', 'Total Earnings']]
            for truck in trucks:
                truck_data.append([
                    truck['number'],
                    truck.get('model', '')[:15],
                    f"{truck.get('capacity', 0)}T",
                    truck['status'],
                    str(truck['total_trips']),
                    f'₹{truck["total_earnings"]:.2f}'
                ])
            
            truck_table = Table(truck_data)
            truck_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
            ]))
            
            story.append(truck_table)
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer

# ===== AUTHENTICATION ROUTES =====

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        users = load_users()
        user = next((u for u in users if u['username'] == username), None)
        
        if user and verify_password(password, user['password']):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            flash(f'Welcome back, {user["name"]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password!', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        users = load_users()
        
        # Check if username exists
        if any(u['username'] == request.form['username'] for u in users):
            flash('Username already exists!', 'error')
            return redirect(url_for('register'))
        
        user = {
            'id': str(uuid.uuid4()),
            'username': request.form['username'],
            'password': hash_password(request.form['password']),
            'name': request.form['name'],
            'email': request.form['email'],
            'phone': request.form['phone'],
            'role': request.form.get('role', 'driver'),  # driver or admin
            'truck_number': request.form.get('truck_number', ''),
            'created_at': datetime.now().isoformat(),
            'last_login': None,
            'is_active': True
        }
        
        users.append(user)
        save_users(users)
        
        flash('Account created successfully! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    users = load_users()
    user = next((u for u in users if u['id'] == session['user_id']), None)
    
    if request.method == 'POST':
        user['name'] = request.form['name']
        user['email'] = request.form['email']
        user['phone'] = request.form['phone']
        if request.form.get('password'):
            user['password'] = hash_password(request.form['password'])
        
        # Handle profile photo upload
        if 'profile_photo' in request.files:
            file = request.files['profile_photo']
            if file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Add user ID and timestamp to avoid conflicts
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                filename = f"profile_{user['id']}_{timestamp}_{filename}"
                
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                
                # Remove old profile photo if exists
                if user.get('profile_photo'):
                    try:
                        old_path = os.path.join(app.config['UPLOAD_FOLDER'], user['profile_photo'])
                        os.remove(old_path)
                    except FileNotFoundError:
                        pass
                
                user['profile_photo'] = filename
        
        save_users(users)
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))
    
    return render_template('profile.html', user=user)

# ===== LOCATION TRACKING ROUTES =====

@app.route('/update_location', methods=['POST'])
@login_required
def update_location():
    data = request.get_json()
    
    users = load_users()
    user = next((u for u in users if u['id'] == session['user_id']), None)
    
    if not user or not user['truck_number']:
        return jsonify({'error': 'No truck assigned'}), 400
    
    locations = load_locations()
    
    location = {
        'id': str(uuid.uuid4()),
        'truck_number': user['truck_number'],
        'driver_id': user['id'],
        'driver_name': user['name'],
        'latitude': data['latitude'],
        'longitude': data['longitude'],
        'timestamp': datetime.now().isoformat(),
        'speed': data.get('speed', 0),
        'heading': data.get('heading', 0),
        'accuracy': data.get('accuracy', 0)
    }
    
    locations.append(location)
    save_locations(locations)
    
    # Update user's last location
    user['last_location'] = {
        'latitude': data['latitude'],
        'longitude': data['longitude'],
        'timestamp': location['timestamp']
    }
    save_users(users)
    
    return jsonify({'success': True, 'location_id': location['id']})

@app.route('/get_locations/<truck_number>')
@login_required
def get_locations(truck_number):
    locations = load_locations()
    
    # Get locations for this truck (last 24 hours)
    yesterday = datetime.now() - timedelta(days=1)
    truck_locations = [
        loc for loc in locations 
        if loc['truck_number'] == truck_number 
        and datetime.fromisoformat(loc['timestamp']) > yesterday
    ]
    
    # Sort by timestamp
    truck_locations.sort(key=lambda x: x['timestamp'])
    
    return jsonify(truck_locations)

@app.route('/live_tracking')
@login_required
def live_tracking():
    trucks = load_trucks()
    users = load_users()
    
    # Get active drivers with trucks
    active_drivers = []
    for user in users:
        if user['role'] == 'driver' and user['truck_number'] and user.get('is_active', True):
            truck = next((t for t in trucks if t['number'] == user['truck_number']), None)
            if truck:
                active_drivers.append({
                    'user': user,
                    'truck': truck,
                    'last_location': user.get('last_location')
                })
    
    return render_template('live_tracking.html', active_drivers=active_drivers)

@app.route('/location_history/<truck_number>')
@login_required
def location_history(truck_number):
    locations = load_locations()
    
    # Get all locations for this truck
    truck_locations = [
        loc for loc in locations 
        if loc['truck_number'] == truck_number
    ]
    
    # Sort by timestamp (newest first)
    truck_locations.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # Group by date
    history_by_date = {}
    for loc in truck_locations:
        date = loc['timestamp'][:10]
        if date not in history_by_date:
            history_by_date[date] = []
        history_by_date[date].append(loc)
    
    return render_template('location_history.html', 
                         truck_number=truck_number, 
                         history_by_date=history_by_date)

@app.route('/driver_dashboard')
@login_required
def driver_dashboard():
    users = load_users()
    user = next((u for u in users if u['id'] == session['user_id']), None)
    
    if not user or user['role'] != 'driver':
        flash('Access denied!', 'error')
        return redirect(url_for('dashboard'))
    
    # Get assigned trips
    trips = load_trips()
    assigned_trips = [
        trip for trip in trips 
        if trip['truck_number'] == user.get('truck_number', '') 
        and trip['status'] in ['In Transit', 'Booked']
    ]
    
    # Get recent locations
    locations = load_locations()
    recent_locations = [
        loc for loc in locations 
        if loc['truck_number'] == user.get('truck_number', '')
    ][-10:]  # Last 10 locations
    
    return render_template('driver_dashboard.html', 
                         user=user, 
                         assigned_trips=assigned_trips,
                         recent_locations=recent_locations)

# ===== ACCOUNT MANAGEMENT ROUTES =====

@app.route('/manage_users')
@admin_required
def manage_users():
    users = load_users()
    return render_template('manage_users.html', users=users)

@app.route('/create_user', methods=['GET', 'POST'])
@admin_required
def create_user():
    if request.method == 'POST':
        users = load_users()
        
        # Check if username exists
        if any(u['username'] == request.form['username'] for u in users):
            flash('Username already exists!', 'error')
            return redirect(url_for('create_user'))
        
        user = {
            'id': str(uuid.uuid4()),
            'username': request.form['username'],
            'password': hash_password(request.form['password']),
            'name': request.form['name'],
            'email': request.form['email'],
            'phone': request.form['phone'],
            'role': request.form['role'],
            'truck_number': request.form.get('truck_number', ''),
            'created_at': datetime.now().isoformat(),
            'last_login': None,
            'is_active': True
        }
        
        users.append(user)
        save_users(users)
        
        flash('User created successfully!', 'success')
        return redirect(url_for('manage_users'))
    
    trucks = load_trucks()
    return render_template('create_user.html', trucks=trucks)

@app.route('/edit_user/<user_id>', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    users = load_users()
    user = next((u for u in users if u['id'] == user_id), None)
    
    if not user:
        flash('User not found!', 'error')
        return redirect(url_for('manage_users'))
    
    if request.method == 'POST':
        user['name'] = request.form['name']
        user['email'] = request.form['email']
        user['phone'] = request.form['phone']
        user['role'] = request.form['role']
        user['truck_number'] = request.form.get('truck_number', '')
        user['is_active'] = 'is_active' in request.form
        
        if request.form.get('password'):
            user['password'] = hash_password(request.form['password'])
        
        save_users(users)
        flash('User updated successfully!', 'success')
        return redirect(url_for('manage_users'))
    
    trucks = load_trucks()
    return render_template('edit_user.html', user=user, trucks=trucks)

@app.route('/delete_user/<user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    users = load_users()
    users = [u for u in users if u['id'] != user_id]
    save_users(users)
    
    flash('User deleted successfully!', 'success')
    return redirect(url_for('manage_users'))

# ===== DOCUMENT MANAGEMENT ROUTES =====

@app.route('/documents')
@login_required
def documents():
    documents_data = load_documents()
    trucks = load_trucks()
    users = load_users()
    
    # Group documents by entity
    documents_by_entity = {}
    for doc in documents_data:
        entity_key = f"{doc['entity_type']}_{doc['entity_id']}"
        if entity_key not in documents_by_entity:
            documents_by_entity[entity_key] = []
        documents_by_entity[entity_key].append(doc)
    
    return render_template('documents.html', 
                         documents_by_entity=documents_by_entity,
                         trucks=trucks,
                         users=users)

@app.route('/upload_document', methods=['GET', 'POST'])
@login_required
def upload_document():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected!', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected!', 'error')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Add timestamp to avoid conflicts
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
            filename = timestamp + filename
            
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # Save document metadata
            documents = load_documents()
            document = {
                'id': str(uuid.uuid4()),
                'filename': filename,
                'original_filename': file.filename,
                'entity_type': request.form['entity_type'],
                'entity_id': request.form['entity_id'],
                'document_type': request.form['document_type'],
                'description': request.form.get('description', ''),
                'expiry_date': request.form.get('expiry_date', ''),
                'uploaded_by': session['username'],
                'uploaded_at': datetime.now().isoformat(),
                'file_path': file_path
            }
            
            documents.append(document)
            save_documents(documents)
            
            flash('Document uploaded successfully!', 'success')
            return redirect(url_for('documents'))
        else:
            flash('Invalid file type! Allowed: PDF, JPG, PNG, DOC, DOCX', 'error')
    
    trucks = load_trucks()
    users = load_users()
    return render_template('upload_document.html', trucks=trucks, users=users)

@app.route('/download_document/<document_id>')
@login_required
def download_document(document_id):
    documents = load_documents()
    document = next((d for d in documents if d['id'] == document_id), None)
    
    if not document:
        flash('Document not found!', 'error')
        return redirect(url_for('documents'))
    
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], 
                                 document['filename'], 
                                 as_attachment=True,
                                 download_name=document['original_filename'])
    except FileNotFoundError:
        flash('File not found on server!', 'error')
        return redirect(url_for('documents'))

@app.route('/delete_document/<document_id>', methods=['POST'])
@login_required
def delete_document(document_id):
    documents = load_documents()
    document = next((d for d in documents if d['id'] == document_id), None)
    
    if not document:
        flash('Document not found!', 'error')
        return redirect(url_for('documents'))
    
    # Remove file from filesystem
    try:
        os.remove(document['file_path'])
    except FileNotFoundError:
        pass  # File already deleted
    
    # Remove from database
    documents = [d for d in documents if d['id'] != document_id]
    save_documents(documents)
    
    flash('Document deleted successfully!', 'success')
    return redirect(url_for('documents'))

# ===== EXISTING ROUTES (with login_required decorator) =====

@app.route('/')
@login_required
def dashboard():
    trips = load_trips()
    customers = load_customers()
    trucks = load_trucks()

    # Calculate statistics
    total_trips = len(trips)
    total_customers = len(customers)
    total_trucks = len(trucks)
    total_earnings = sum(trip['total_fare'] for trip in trips if trip['status'] == 'Delivered')

    # Recent trips (last 5)
    recent_trips = sorted(trips, key=lambda x: x['timestamp'], reverse=True)[:5]

    # Pending payments
    pending_payments = []
    total_pending = 0
    for trip in trips:
        total_paid = sum(p['amount'] for p in trip['payments'])
        remaining = trip['total_fare'] - total_paid
        if remaining > 0:
            pending_payments.append({'trip': trip, 'remaining': remaining})
            total_pending += remaining

    return render_template('dashboard.html',
                         total_trips=total_trips,
                         total_customers=total_customers,
                         total_trucks=total_trucks,
                         total_earnings=total_earnings,
                         recent_trips=recent_trips,
                         pending_payments=pending_payments,
                         total_pending=total_pending)

@app.route('/create_trip', methods=['GET', 'POST'])
@login_required
def create_trip():
    if request.method == 'POST':
        customers = load_customers()
        trucks = load_trucks()

        customer_name = request.form['customer'].strip()
        truck_number = request.form['truck_number'].strip().upper()

        # Auto-create customer if doesn't exist
        if not get_customer_by_name(customers, customer_name):
            customer = {
                'id': str(uuid.uuid4()),
                'name': customer_name,
                'phone': '',
                'email': '',
                'address': '',
                'total_trips': 0,
                'total_earnings': 0.0,
                'created_at': datetime.now().isoformat()
            }
            customers.append(customer)
            save_customers(customers)

        # Auto-create truck if doesn't exist
        if not get_truck_by_number(trucks, truck_number):
            truck = {
                'id': str(uuid.uuid4()),
                'number': truck_number,
                'model': '',
                'capacity': 0.0,
                'status': 'Available',
                'total_trips': 0,
                'total_earnings': 0.0,
                'added_at': datetime.now().isoformat()
            }
            trucks.append(truck)
            save_trucks(trucks)

        trip = {
            'id': str(uuid.uuid4()),
            'customer': customer_name,
            'pickup': request.form['pickup'].strip(),
            'destination': request.form['destination'].strip(),
            'truck_number': truck_number,
            'load_type': request.form['load_type'].strip(),
            'weight': float(request.form['weight']),
            'rate_per_km': float(request.form['rate_per_km']),
            'distance_km': None,
            'loading_charges': 0.0,
            'total_fare': 0.0,
            'advance_paid': 0.0,
            'payments': [],
            'expenses': [],
            'status': 'Booked',
            'timestamp': datetime.now().isoformat()
        }

        trips = load_trips()
        trips.append(trip)
        save_trips(trips)

        update_truck_stats()

        flash('Trip created successfully!', 'success')
        return redirect(url_for('trips'))

    return render_template('create_trip.html')

@app.route('/trips')
@login_required
def trips():
    trips_data = load_trips()
    # Sort by timestamp (newest first)
    trips_data.sort(key=lambda x: x['timestamp'], reverse=True)
    return render_template('trips.html', trips=trips_data)

@app.route('/trip/<trip_id>')
@login_required
def trip_details(trip_id):
    trips = load_trips()
    trip = get_trip_by_id(trips, trip_id)
    if not trip:
        flash('Trip not found!', 'error')
        return redirect(url_for('trips'))

    total_paid = sum(p['amount'] for p in trip['payments'])
    total_expenses = sum(e['amount'] for e in trip.get('expenses', []))
    net_profit = trip['total_fare'] - total_expenses

    return render_template('trip_details.html',
                         trip=trip,
                         total_paid=total_paid,
                         total_expenses=total_expenses,
                         net_profit=net_profit)

@app.route('/update_distance/<trip_id>', methods=['GET', 'POST'])
@login_required
def update_distance(trip_id):
    trips = load_trips()
    trip = get_trip_by_id(trips, trip_id)

    if not trip:
        flash('Trip not found!', 'error')
        return redirect(url_for('trips'))

    if request.method == 'POST':
        distance = float(request.form['distance'])
        trip['distance_km'] = distance
        save_trips(trips)
        flash('Distance updated successfully!', 'success')
        return redirect(url_for('trip_details', trip_id=trip_id))

    return render_template('update_distance.html', trip=trip)

@app.route('/calculate_fare/<trip_id>', methods=['GET', 'POST'])
@login_required
def calculate_fare(trip_id):
    trips = load_trips()
    trip = get_trip_by_id(trips, trip_id)

    if not trip:
        flash('Trip not found!', 'error')
        return redirect(url_for('trips'))

    if request.method == 'POST':
        loading_charges = float(request.form['loading_charges'])
        trip['loading_charges'] = loading_charges
        trip['total_fare'] = (trip['distance_km'] * trip['rate_per_km']) + loading_charges
        save_trips(trips)
        flash('Fare calculated successfully!', 'success')
        return redirect(url_for('trip_details', trip_id=trip_id))

    return render_template('calculate_fare.html', trip=trip)

@app.route('/add_payment/<trip_id>', methods=['GET', 'POST'])
@login_required
def add_payment(trip_id):
    trips = load_trips()
    trip = get_trip_by_id(trips, trip_id)

    if not trip:
        flash('Trip not found!', 'error')
        return redirect(url_for('trips'))

    if request.method == 'POST':
        amount = float(request.form['amount'])
        payment_type = request.form['payment_type']

        trip['payments'].append({
            'type': payment_type,
            'amount': amount,
            'timestamp': datetime.now().isoformat()
        })

        save_trips(trips)
        flash(f'Payment of ₹{amount} recorded successfully!', 'success')
        return redirect(url_for('trip_details', trip_id=trip_id))

    return render_template('add_payment.html', trip=trip)

@app.route('/add_expense/<trip_id>', methods=['GET', 'POST'])
@login_required
def add_expense(trip_id):
    trips = load_trips()
    trip = get_trip_by_id(trips, trip_id)

    if not trip:
        flash('Trip not found!', 'error')
        return redirect(url_for('trips'))

    if request.method == 'POST':
        expense_type = request.form['expense_type']
        amount = float(request.form['amount'])
        description = request.form['description'].strip()

        if 'expenses' not in trip:
            trip['expenses'] = []

        trip['expenses'].append({
            'id': str(uuid.uuid4()),
            'type': expense_type,
            'amount': amount,
            'description': description,
            'timestamp': datetime.now().isoformat()
        })

        save_trips(trips)
        flash(f'Expense of ₹{amount} recorded successfully!', 'success')
        return redirect(url_for('trip_details', trip_id=trip_id))

    return render_template('add_expense.html', trip=trip)

@app.route('/start_trip/<trip_id>', methods=['POST'])
@login_required
def start_trip(trip_id):
    trips = load_trips()
    trip = get_trip_by_id(trips, trip_id)

    if not trip:
        flash('Trip not found!', 'error')
        return redirect(url_for('trips'))

    trip['status'] = 'In Transit'
    save_trips(trips)
    update_truck_stats()

    flash('Trip started successfully!', 'success')
    return redirect(url_for('trip_details', trip_id=trip_id))

@app.route('/deliver_trip/<trip_id>', methods=['POST'])
@login_required
def deliver_trip(trip_id):
    trips = load_trips()
    trip = get_trip_by_id(trips, trip_id)

    if not trip:
        flash('Trip not found!', 'error')
        return redirect(url_for('trips'))

    trip['status'] = 'Delivered'
    save_trips(trips)
    update_customer_stats()
    update_truck_stats()

    flash('Trip marked as delivered!', 'success')
    return redirect(url_for('trip_details', trip_id=trip_id))

@app.route('/rate_customer/<trip_id>', methods=['GET', 'POST'])
@login_required
def rate_customer(trip_id):
    trips = load_trips()
    trip = get_trip_by_id(trips, trip_id)
    
    if not trip:
        flash('Trip not found!', 'error')
        return redirect(url_for('trips'))
    
    if trip['status'] != 'Delivered':
        flash('Can only rate completed trips!', 'error')
        return redirect(url_for('trip_details', trip_id=trip_id))
    
    if request.method == 'POST':
        rating = int(request.form['rating'])
        review = request.form['review'].strip()
        
        # Add rating to trip
        if 'customer_rating' not in trip:
            trip['customer_rating'] = {}
        trip['customer_rating'] = {
            'rating': rating,
            'review': review,
            'rated_by': session['username'],
            'rated_at': datetime.now().isoformat()
        }
        
        # Update customer's average rating
        customers = load_customers()
        customer = get_customer_by_name(customers, trip['customer'])
        if customer:
            if 'ratings' not in customer:
                customer['ratings'] = []
            customer['ratings'].append({
                'rating': rating,
                'review': review,
                'trip_id': trip_id,
                'rated_at': datetime.now().isoformat()
            })
            
            # Calculate average rating
            total_ratings = len(customer['ratings'])
            avg_rating = sum(r['rating'] for r in customer['ratings']) / total_ratings
            customer['average_rating'] = round(avg_rating, 1)
            customer['total_ratings'] = total_ratings
            
            save_customers(customers)
        
        save_trips(trips)
        flash('Customer rated successfully!', 'success')
        return redirect(url_for('trip_details', trip_id=trip_id))
    
    return render_template('rate_customer.html', trip=trip)

@app.route('/rate_truck/<trip_id>', methods=['GET', 'POST'])
@login_required
def rate_truck(trip_id):
    trips = load_trips()
    trip = get_trip_by_id(trips, trip_id)
    
    if not trip:
        flash('Trip not found!', 'error')
        return redirect(url_for('trips'))
    
    if trip['status'] != 'Delivered':
        flash('Can only rate completed trips!', 'error')
        return redirect(url_for('trip_details', trip_id=trip_id))
    
    if request.method == 'POST':
        rating = int(request.form['rating'])
        review = request.form['review'].strip()
        
        # Add rating to trip
        if 'truck_rating' not in trip:
            trip['truck_rating'] = {}
        trip['truck_rating'] = {
            'rating': rating,
            'review': review,
            'rated_by': session['username'],
            'rated_at': datetime.now().isoformat()
        }
        
        # Update truck's average rating
        trucks = load_trucks()
        truck = get_truck_by_number(trucks, trip['truck_number'])
        if truck:
            if 'ratings' not in truck:
                truck['ratings'] = []
            truck['ratings'].append({
                'rating': rating,
                'review': review,
                'trip_id': trip_id,
                'rated_at': datetime.now().isoformat()
            })
            
            # Calculate average rating
            total_ratings = len(truck['ratings'])
            avg_rating = sum(r['rating'] for r in truck['ratings']) / total_ratings
            truck['average_rating'] = round(avg_rating, 1)
            truck['total_ratings'] = total_ratings
            
            save_trucks(trucks)
        
        save_trips(trips)
        flash('Truck rated successfully!', 'success')
        return redirect(url_for('trip_details', trip_id=trip_id))
    
    return render_template('rate_truck.html', trip=trip)

@app.route('/edit_trip/<trip_id>', methods=['GET', 'POST'])
@login_required
def edit_trip(trip_id):
    trips = load_trips()
    trip = get_trip_by_id(trips, trip_id)
    
    if not trip:
        flash('Trip not found!', 'error')
        return redirect(url_for('trips'))
    
    if request.method == 'POST':
        customers = load_customers()
        trucks = load_trucks()
        
        customer_name = request.form['customer'].strip()
        truck_number = request.form['truck_number'].strip().upper()
        
        # Validate customer exists or auto-create
        if not get_customer_by_name(customers, customer_name):
            customer = {
                'id': str(uuid.uuid4()),
                'name': customer_name,
                'phone': '',
                'email': '',
                'address': '',
                'total_trips': 0,
                'total_earnings': 0.0,
                'created_at': datetime.now().isoformat()
            }
            customers.append(customer)
            save_customers(customers)
        
        # Validate truck exists or auto-create
        if not get_truck_by_number(trucks, truck_number):
            truck = {
                'id': str(uuid.uuid4()),
                'number': truck_number,
                'model': '',
                'capacity': 0.0,
                'status': 'Available',
                'total_trips': 0,
                'total_earnings': 0.0,
                'added_at': datetime.now().isoformat()
            }
            trucks.append(truck)
            save_trucks(trucks)
        
        # Update trip details
        trip['customer'] = customer_name
        trip['pickup'] = request.form['pickup'].strip()
        trip['destination'] = request.form['destination'].strip()
        trip['truck_number'] = truck_number
        trip['load_type'] = request.form['load_type'].strip()
        trip['weight'] = float(request.form['weight'])
        trip['rate_per_km'] = float(request.form['rate_per_km'])
        
        # Recalculate fare if distance is set
        if trip.get('distance_km'):
            trip['total_fare'] = (trip['distance_km'] * trip['rate_per_km']) + trip.get('loading_charges', 0)
        
        save_trips(trips)
        update_truck_stats()
        
        flash('Trip updated successfully!', 'success')
        return redirect(url_for('trip_details', trip_id=trip_id))
    
    return render_template('edit_trip.html', trip=trip)

@app.route('/delete_trip/<trip_id>', methods=['POST'])
@login_required
def delete_trip(trip_id):
    trips = load_trips()
    trip = get_trip_by_id(trips, trip_id)
    
    if not trip:
        flash('Trip not found!', 'error')
        return redirect(url_for('trips'))
    
    # Don't allow deletion of trips with payments
    if trip.get('payments') and len(trip['payments']) > 0:
        flash('Cannot delete trip with payment records!', 'error')
        return redirect(url_for('trip_details', trip_id=trip_id))
    
    # Remove trip
    trips = [t for t in trips if t['id'] != trip_id]
    save_trips(trips)
    
    # Update stats
    update_customer_stats()
    update_truck_stats()
    
    flash('Trip deleted successfully!', 'success')
    return redirect(url_for('trips'))

@app.route('/add_customer', methods=['GET', 'POST'])
@login_required
def add_customer():
    if request.method == 'POST':
        customers = load_customers()

        name = request.form['name'].strip()
        if get_customer_by_name(customers, name):
            flash('Customer already exists!', 'error')
            return redirect(url_for('add_customer'))

        customer = {
            'id': str(uuid.uuid4()),
            'name': name,
            'phone': request.form['phone'].strip(),
            'email': request.form['email'].strip(),
            'address': request.form['address'].strip(),
            'total_trips': 0,
            'total_earnings': 0.0,
            'created_at': datetime.now().isoformat()
        }

        customers.append(customer)
        save_customers(customers)
        flash('Customer added successfully!', 'success')
        return redirect(url_for('customers'))

    return render_template('add_customer.html')

@app.route('/customers')
@login_required
def customers():
    customers_data = load_customers()
    return render_template('customers.html', customers=customers_data)

@app.route('/customer/<customer_id>')
@login_required
def customer_details(customer_id):
    customers = load_customers()
    customer = next((c for c in customers if c['id'] == customer_id), None)
    
    if not customer:
        flash('Customer not found!', 'error')
        return redirect(url_for('customers'))
    
    # Get customer's trips
    trips = load_trips()
    customer_trips = [t for t in trips if t['customer'] == customer['name']]
    
    return render_template('customer_details.html', customer=customer, trips=customer_trips)

@app.route('/edit_customer/<customer_id>', methods=['GET', 'POST'])
@login_required
def edit_customer(customer_id):
    customers = load_customers()
    customer = next((c for c in customers if c['id'] == customer_id), None)
    
    if not customer:
        flash('Customer not found!', 'error')
        return redirect(url_for('customers'))
    
    if request.method == 'POST':
        # Check if new name conflicts with existing customers
        new_name = request.form['name'].strip()
        if new_name != customer['name'] and get_customer_by_name(customers, new_name):
            flash('Customer name already exists!', 'error')
            return redirect(url_for('edit_customer', customer_id=customer_id))
        
        customer['name'] = new_name
        customer['phone'] = request.form['phone'].strip()
        customer['email'] = request.form['email'].strip()
        customer['address'] = request.form['address'].strip()
        
        save_customers(customers)
        flash('Customer updated successfully!', 'success')
        return redirect(url_for('customer_details', customer_id=customer_id))
    
    return render_template('edit_customer.html', customer=customer)

@app.route('/delete_customer/<customer_id>', methods=['POST'])
@login_required
def delete_customer(customer_id):
    customers = load_customers()
    customer = next((c for c in customers if c['id'] == customer_id), None)
    
    if not customer:
        flash('Customer not found!', 'error')
        return redirect(url_for('customers'))
    
    # Check if customer has active trips
    trips = load_trips()
    active_trips = [t for t in trips if t['customer'] == customer['name'] and t['status'] != 'Delivered']
    
    if active_trips:
        flash('Cannot delete customer with active trips!', 'error')
        return redirect(url_for('customer_details', customer_id=customer_id))
    
    # Remove customer
    customers = [c for c in customers if c['id'] != customer_id]
    save_customers(customers)
    
    flash('Customer deleted successfully!', 'success')
    return redirect(url_for('customers'))

@app.route('/add_truck', methods=['GET', 'POST'])
@login_required
def add_truck():
    if request.method == 'POST':
        trucks = load_trucks()

        number = request.form['number'].strip().upper()
        if get_truck_by_number(trucks, number):
            flash('Truck already exists!', 'error')
            return redirect(url_for('add_truck'))

        truck = {
            'id': str(uuid.uuid4()),
            'number': number,
            'model': request.form['model'].strip(),
            'capacity': float(request.form['capacity']),
            'status': 'Available',
            'total_trips': 0,
            'total_earnings': 0.0,
            'added_at': datetime.now().isoformat()
        }

        trucks.append(truck)
        save_trucks(trucks)
        flash('Truck added successfully!', 'success')
        return redirect(url_for('trucks'))

    return render_template('add_truck.html')

@app.route('/trucks')
@login_required
def trucks():
    trucks_data = load_trucks()
    return render_template('trucks.html', trucks=trucks_data)

@app.route('/search_trips', methods=['GET', 'POST'])
@login_required
def search_trips():
    results = []
    if request.method == 'POST':
        search_type = request.form['search_type']
        query = request.form['query'].strip()

        trips = load_trips()

        if search_type == 'customer':
            results = [t for t in trips if query.lower() in t['customer'].lower()]
        elif search_type == 'truck':
            results = [t for t in trips if query.lower() in t['truck_number'].lower()]
        elif search_type == 'status':
            results = [t for t in trips if t['status'] == query]

    return render_template('search_trips.html', results=results)

@app.route('/reports')
@login_required
def reports():
    # Calculate report data
    trips = load_trips()
    today = datetime.now().date()

    # Daily earnings
    daily_earnings = sum(t['total_fare'] for t in trips
                        if datetime.fromisoformat(t['timestamp']).date() == today
                        and t['status'] == 'Delivered')

    # Monthly earnings
    current_month = datetime.now().month
    current_year = datetime.now().year
    monthly_earnings = sum(t['total_fare'] for t in trips
                          if datetime.fromisoformat(t['timestamp']).month == current_month
                          and datetime.fromisoformat(t['timestamp']).year == current_year
                          and t['status'] == 'Delivered')

    # Pending payments
    pending_payments = []
    total_pending = 0
    for trip in trips:
        total_paid = sum(p['amount'] for p in trip['payments'])
        remaining = trip['total_fare'] - total_paid
        if remaining > 0:
            pending_payments.append({'trip': trip, 'remaining': remaining})
            total_pending += remaining

    # Profit/Loss
    total_revenue = sum(t['total_fare'] for t in trips if t['status'] == 'Delivered')
    total_expenses = 0
    for trip in trips:
        if trip['status'] == 'Delivered':
            total_expenses += sum(e['amount'] for e in trip.get('expenses', []))
    net_profit = total_revenue - total_expenses

    return render_template('reports.html',
                         daily_earnings=daily_earnings,
                         monthly_earnings=monthly_earnings,
                         pending_payments=pending_payments,
                         total_pending=total_pending,
                         total_revenue=total_revenue,
                         total_expenses=total_expenses,
                         net_profit=net_profit)

@app.route('/download_report/<report_type>')
@login_required
def download_report(report_type):
    """Download PDF report"""
    try:
        # Validate report type
        valid_types = ['summary', 'trips', 'customers', 'trucks']
        if report_type not in valid_types:
            report_type = 'summary'
        
        # Generate PDF
        pdf_buffer = generate_pdf_report(report_type)
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"kalawati_transport_{report_type}_report_{timestamp}.pdf"
        
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
    except Exception as e:
        flash(f'Error generating PDF report: {str(e)}', 'error')
        return redirect(url_for('reports'))

# ===== CLI FUNCTIONS (for backward compatibility) =====

def main_menu():
    # Update stats on startup
    update_customer_stats()
    update_truck_stats()
    
    while True:
        print("\n" + "="*60)
        print("🚛 KALAWATI TRANSPORT - Payment & Tracking System")
        print("="*60)
        print("📝 TRIP MANAGEMENT")
        print("1. Create New Trip (STEP 1)")
        print("2. Update Distance (STEP 2)")
        print("3. Calculate Fare (STEP 3)")
        print("4. Enter Advance Payment (STEP 4)")
        print("5. Start Trip (STEP 5)")
        print("6. Update Payment (STEP 7)")
        print("7. Mark as Delivered (STEP 9)")
        print("8. View Trip Details")
        print("9. View All Trips")
        print("10. Edit Trip")
        print("11. Add Trip Expense")
        print()
        print("👥 CUSTOMER MANAGEMENT")
        print("12. Add Customer")
        print("13. View Customers")
        print()
        print("🚛 TRUCK MANAGEMENT")
        print("14. Add Truck")
        print("15. View Trucks")
        print()
        print("📊 REPORTS & SEARCH")
        print("16. Generate Reports")
        print("17. Search Trips")
        print()
        print("0. Exit")
        print("="*60)
        
        choice = input("Choose option: ").strip()
        
        if choice == '1':
            create_trip()
        elif choice == '2':
            update_distance()
        elif choice == '3':
            calculate_fare()
        elif choice == '4':
            enter_advance_payment()
        elif choice == '5':
            start_trip()
        elif choice == '6':
            update_payment()
        elif choice == '7':
            mark_delivered()
        elif choice == '8':
            view_trip_details()
        elif choice == '9':
            view_all_trips()
        elif choice == '10':
            edit_trip()
        elif choice == '11':
            add_expense()
        elif choice == '12':
            add_customer()
        elif choice == '13':
            view_customers()
        elif choice == '14':
            add_truck()
        elif choice == '15':
            view_trucks()
        elif choice == '16':
            generate_reports()
        elif choice == '17':
            search_trips()
        elif choice == '0':
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Try again.")

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

