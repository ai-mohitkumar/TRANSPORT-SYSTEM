import json
import uuid
import os
import requests
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

from models import db, User, Customer, Truck, Trip, Payment, Expense, Location, Document, AuditLog, Rating
from flask_migrate import Migrate

app = Flask(__name__)

@app.template_filter('datetimeformat')
def datetimeformat(value):
    if value:
        return value.strftime('%Y-%m-%d %H:%M:%S')
    return ""

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///kalawati.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'transport_system_secret_key_2024_pro'

db.init_app(app)
migrate = Migrate(app, db)

# Upload folder
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Google Maps API Key (set via environment variable)
GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY', '')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
        user = User.query.get(session['user_id'])
        if not user or user.role != 'admin':
            flash('Admin access required!', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def log_audit(action, entity_type, entity_id, old_values=None, new_values=None):
    audit = AuditLog(
        user_id=session.get('user_id'),
        username=session.get('username'),
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        old_values=json.dumps(old_values) if old_values else None,
        new_values=json.dumps(new_values) if new_values else None
    )
    db.session.add(audit)
    db.session.commit()

def recalculate_fare(trip):
    """Auto-recalculate fare when distance or rate changes"""
    if trip.distance_km and trip.rate_per_km:
        trip.total_fare = (trip.distance_km * trip.rate_per_km) + trip.loading_charges
    return trip

def update_customer_stats():
    customers = Customer.query.all()
    for customer in customers:
        customer.total_trips = Trip.query.filter_by(customer_name=customer.name, status='Delivered').count()
        customer.total_earnings = db.session.query(db.func.sum(Trip.total_fare)).filter_by(
            customer_name=customer.name, status='Delivered').scalar() or 0.0
    db.session.commit()

def update_truck_stats():
    trucks = Truck.query.all()
    for truck in trucks:
        truck.total_trips = Trip.query.filter_by(truck_number=truck.number, status='Delivered').count()
        truck.total_earnings = db.session.query(db.func.sum(Trip.total_fare)).filter_by(
            truck_number=truck.number, status='Delivered').scalar() or 0.0
        active = Trip.query.filter_by(truck_number=truck.number).filter(
            Trip.status.in_(['In Transit', 'Booked'])).first()
        truck.status = 'Busy' if active else 'Available'
    db.session.commit()

# ===== PUBLIC LANDING PAGE =====

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    total_trips = Trip.query.count()
    total_customers = Customer.query.count()
    total_trucks = Truck.query.count()
    completed_trips = Trip.query.filter_by(status='Delivered').count()
    return render_template('index.html',
                         total_trips=total_trips,
                         total_customers=total_customers,
                         total_trucks=total_trucks,
                         completed_trips=completed_trips)

# ===== AUTHENTICATION =====

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and verify_password(password, user.password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            user.last_login = datetime.utcnow()
            db.session.commit()
            flash(f'Welcome back, {user.name}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password!', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        if User.query.filter_by(username=request.form['username']).first():
            flash('Username already exists!', 'error')
            return redirect(url_for('register'))
        user = User(
            username=request.form['username'],
            password=hash_password(request.form['password']),
            name=request.form['name'],
            email=request.form['email'],
            phone=request.form['phone'],
            role=request.form.get('role', 'driver'),
            truck_number=request.form.get('truck_number', '')
        )
        db.session.add(user)
        db.session.commit()
        flash('Account created successfully! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        old = {'name': user.name, 'email': user.email, 'phone': user.phone}
        user.name = request.form['name']
        user.email = request.form['email']
        user.phone = request.form['phone']
        if request.form.get('password'):
            user.password = hash_password(request.form['password'])
        if 'profile_photo' in request.files:
            file = request.files['profile_photo']
            if file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                filename = f"profile_{user.id}_{timestamp}_{filename}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                if user.profile_photo:
                    try:
                        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], user.profile_photo))
                    except:
                        pass
                user.profile_photo = filename
        db.session.commit()
        log_audit('update', 'user', user.id, old, {'name': user.name, 'email': user.email, 'phone': user.phone})
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))
    return render_template('profile.html', user=user)

# ===== DASHBOARD WITH CHART.JS API =====

@app.route('/dashboard')
@login_required
def dashboard():
    trips = Trip.query.all()
    customers = Customer.query.all()
    trucks = Truck.query.all()
    total_trips = len(trips)
    total_customers = len(customers)
    total_trucks = len(trucks)
    total_earnings = db.session.query(db.func.sum(Trip.total_fare)).filter_by(status='Delivered').scalar() or 0.0
    recent_trips = Trip.query.order_by(Trip.timestamp.desc()).limit(5).all()
    pending = []
    total_pending = 0
    for trip in trips:
        paid = db.session.query(db.func.sum(Payment.amount)).filter_by(trip_id=trip.id).scalar() or 0.0
        remaining = trip.total_fare - paid
        if remaining > 0:
            pending.append({'trip': trip, 'remaining': remaining})
            total_pending += remaining
    return render_template('dashboard.html',
                         total_trips=total_trips,
                         total_customers=total_customers,
                         total_trucks=total_trucks,
                         total_earnings=total_earnings,
                         recent_trips=recent_trips,
                         pending_payments=pending,
                         total_pending=total_pending)

@app.route('/api/dashboard_stats')
@login_required
def dashboard_stats():
    """API endpoint for Chart.js dashboard charts"""
    months = []
    earnings = []
    for i in range(5, -1, -1):
        d = datetime.now() - timedelta(days=i*30)
        month_start = d.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_label = d.strftime('%b %Y') if i == 0 else month_start.strftime('%b %Y')
        month_earnings = db.session.query(db.func.sum(Trip.total_fare)).filter(
            Trip.status == 'Delivered',
            Trip.timestamp >= month_start,
            Trip.timestamp < (month_start + timedelta(days=32)).replace(day=1)
        ).scalar() or 0.0
        months.append(month_label)
        earnings.append(float(month_earnings))
    
    status_counts = {
        'Booked': Trip.query.filter_by(status='Booked').count(),
        'In Transit': Trip.query.filter_by(status='In Transit').count(),
        'Delivered': Trip.query.filter_by(status='Delivered').count()
    }
    
    top_customers = []
    for customer in Customer.query.order_by(Customer.total_earnings.desc()).limit(5).all():
        top_customers.append({'name': customer.name, 'earnings': float(customer.total_earnings or 0)})
    
    return jsonify({
        'monthly_labels': months,
        'monthly_earnings': earnings,
        'status_labels': list(status_counts.keys()),
        'status_data': list(status_counts.values()),
        'top_customers': top_customers
    })

# ===== GOOGLE MAPS AUTO-DISTANCE API =====

@app.route('/api/calculate_distance', methods=['POST'])
@login_required
def calculate_distance_api():
    data = request.get_json()
    pickup = data.get('pickup', '')
    destination = data.get('destination', '')
    
    if not GOOGLE_MAPS_API_KEY:
        return jsonify({
            'distance_km': None,
            'message': 'Google Maps API key not configured. Set GOOGLE_MAPS_API_KEY environment variable.',
            'fallback': True
        })
    
    try:
        url = 'https://maps.googleapis.com/maps/api/distancematrix/json'
        params = {'origins': pickup, 'destinations': destination, 'mode': 'driving', 'key': GOOGLE_MAPS_API_KEY}
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        if data.get('rows') and data['rows'][0].get('elements'):
            element = data['rows'][0]['elements'][0]
            if element.get('status') == 'OK':
                distance_km = round(element['distance']['value'] / 1000, 1)
                return jsonify({'distance_km': distance_km, 'duration': element['duration']['text'], 'fallback': False})
        return jsonify({'distance_km': None, 'message': 'Could not calculate distance', 'fallback': True})
    except Exception as e:
        return jsonify({'distance_km': None, 'message': str(e), 'fallback': True})

# ===== TRIP MANAGEMENT =====

@app.route('/create_trip', methods=['GET', 'POST'])
@login_required
def create_trip():
    if request.method == 'POST':
        customer_name = request.form['customer'].strip()
        truck_number = request.form['truck_number'].strip().upper()
        customer = Customer.query.filter_by(name=customer_name).first()
        if not customer:
            customer = Customer(name=customer_name)
            db.session.add(customer)
            db.session.flush()
        truck = Truck.query.filter_by(number=truck_number).first()
        if not truck:
            truck = Truck(number=truck_number)
            db.session.add(truck)
            db.session.flush()
        distance = request.form.get('distance_km')
        loading = float(request.form.get('loading_charges', 0))
        rate = float(request.form['rate_per_km'])
        trip = Trip(
            customer_id=customer.id,
            customer_name=customer_name,
            pickup=request.form['pickup'].strip(),
            destination=request.form['destination'].strip(),
            truck_number=truck_number,
            load_type=request.form['load_type'].strip(),
            weight=float(request.form['weight']),
            rate_per_km=rate,
            distance_km=float(distance) if distance else None,
            loading_charges=loading
        )
        trip = recalculate_fare(trip)
        db.session.add(trip)
        db.session.commit()
        log_audit('create', 'trip', trip.id, None, {'customer': customer_name, 'pickup': trip.pickup})
        update_truck_stats()
        flash('Trip created successfully!', 'success')
        return redirect(url_for('trips'))
    return render_template('create_trip.html', google_maps_key=GOOGLE_MAPS_API_KEY)

@app.route('/trips')
@login_required
def trips():
    return render_template('trips.html', trips=Trip.query.order_by(Trip.timestamp.desc()).all())

@app.route('/trip/<trip_id>')
@login_required
def trip_details(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    total_paid = db.session.query(db.func.sum(Payment.amount)).filter_by(trip_id=trip.id).scalar() or 0.0
    total_expenses = db.session.query(db.func.sum(Expense.amount)).filter_by(trip_id=trip.id).scalar() or 0.0
    net_profit = trip.total_fare - total_expenses
    return render_template('trip_details.html',
                         trip=trip,
                         total_paid=total_paid,
                         total_expenses=total_expenses,
                         net_profit=net_profit)

@app.route('/update_distance/<trip_id>', methods=['GET', 'POST'])
@login_required
def update_distance(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    if request.method == 'POST':
        old_distance = trip.distance_km
        trip.distance_km = float(request.form['distance'])
        trip = recalculate_fare(trip)
        db.session.commit()
        log_audit('update_distance', 'trip', trip.id, {'distance': old_distance}, {'distance': trip.distance_km})
        flash('Distance updated and fare auto-recalculated!', 'success')
        return redirect(url_for('trip_details', trip_id=trip_id))
    return render_template('update_distance.html', trip=trip)

@app.route('/calculate_fare/<trip_id>', methods=['GET', 'POST'])
@login_required
def calculate_fare(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    if request.method == 'POST':
        old = {'loading_charges': trip.loading_charges, 'total_fare': trip.total_fare}
        trip.loading_charges = float(request.form['loading_charges'])
        trip = recalculate_fare(trip)
        db.session.commit()
        log_audit('calculate_fare', 'trip', trip.id, old, {'loading_charges': trip.loading_charges, 'total_fare': trip.total_fare})
        flash('Fare calculated successfully!', 'success')
        return redirect(url_for('trip_details', trip_id=trip_id))
    return render_template('calculate_fare.html', trip=trip)

@app.route('/add_payment/<trip_id>', methods=['GET', 'POST'])
@login_required
def add_payment(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    if request.method == 'POST':
        payment = Payment(
            trip_id=trip_id,
            type=request.form['payment_type'],
            amount=float(request.form['amount'])
        )
        db.session.add(payment)
        db.session.commit()
        log_audit('add_payment', 'trip', trip_id, None, {'amount': payment.amount, 'type': payment.type})
        flash(f'Payment of ₹{payment.amount} recorded successfully!', 'success')
        return redirect(url_for('trip_details', trip_id=trip_id))
    return render_template('add_payment.html', trip=trip)

@app.route('/add_expense/<trip_id>', methods=['GET', 'POST'])
@login_required
def add_expense(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    if request.method == 'POST':
        expense = Expense(
            trip_id=trip_id,
            type=request.form['expense_type'],
            amount=float(request.form['amount']),
            description=request.form['description'].strip()
        )
        db.session.add(expense)
        db.session.commit()
        log_audit('add_expense', 'trip', trip_id, None, {'amount': expense.amount, 'type': expense.type})
        flash(f'Expense of ₹{expense.amount} recorded successfully!', 'success')
        return redirect(url_for('trip_details', trip_id=trip_id))
    return render_template('add_expense.html', trip=trip)

@app.route('/start_trip/<trip_id>', methods=['POST'])
@login_required
def start_trip(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    trip.status = 'In Transit'
    trip.started_at = datetime.utcnow()
    db.session.commit()
    update_truck_stats()
    flash('Trip started successfully!', 'success')
    return redirect(url_for('trip_details', trip_id=trip_id))

@app.route('/deliver_trip/<trip_id>', methods=['POST'])
@login_required
def deliver_trip(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    trip.status = 'Delivered'
    trip.delivered_at = datetime.utcnow()
    db.session.commit()
    update_customer_stats()
    update_truck_stats()
    flash('Trip marked as delivered!', 'success')
    return redirect(url_for('trip_details', trip_id=trip_id))

@app.route('/rate_customer/<trip_id>', methods=['GET', 'POST'])
@login_required
def rate_customer(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    if trip.status != 'Delivered':
        flash('Can only rate completed trips!', 'error')
        return redirect(url_for('trip_details', trip_id=trip_id))
    if request.method == 'POST':
        rating = Rating(
            trip_id=trip_id,
            entity_type='customer',
            entity_id=trip.customer_id,
            rating=int(request.form['rating']),
            review=request.form['review'].strip(),
            rated_by=session['username']
        )
        db.session.add(rating)
        # Update customer average
        customer = Customer.query.get(trip.customer_id)
        if customer:
            ratings = Rating.query.filter_by(entity_type='customer', entity_id=customer.id).all()
            if ratings:
                customer.average_rating = round(sum(r.rating for r in ratings) / len(ratings), 1)
                customer.total_ratings = len(ratings)
        db.session.commit()
        flash('Customer rated successfully!', 'success')
        return redirect(url_for('trip_details', trip_id=trip_id))
    return render_template('rate_customer.html', trip=trip)

@app.route('/rate_truck/<trip_id>', methods=['GET', 'POST'])
@login_required
def rate_truck(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    if trip.status != 'Delivered':
        flash('Can only rate completed trips!', 'error')
        return redirect(url_for('trip_details', trip_id=trip_id))
    if request.method == 'POST':
        truck = Truck.query.filter_by(number=trip.truck_number).first()
        rating = Rating(
            trip_id=trip_id,
            entity_type='truck',
            entity_id=truck.id if truck else None,
            rating=int(request.form['rating']),
            review=request.form['review'].strip(),
            rated_by=session['username']
        )
        db.session.add(rating)
        if truck:
            ratings = Rating.query.filter_by(entity_type='truck', entity_id=truck.id).all()
            if ratings:
                truck.average_rating = round(sum(r.rating for r in ratings) / len(ratings), 1)
                truck.total_ratings = len(ratings)
        db.session.commit()
        flash('Truck rated successfully!', 'success')
        return redirect(url_for('trip_details', trip_id=trip_id))
    return render_template('rate_truck.html', trip=trip)

@app.route('/edit_trip/<trip_id>', methods=['GET', 'POST'])
@login_required
def edit_trip(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    if request.method == 'POST':
        old = {
            'customer': trip.customer_name, 'pickup': trip.pickup,
            'destination': trip.destination, 'truck': trip.truck_number
        }
        customer_name = request.form['customer'].strip()
        truck_number = request.form['truck_number'].strip().upper()
        
        customer = Customer.query.filter_by(name=customer_name).first()
        if not customer:
            customer = Customer(name=customer_name)
            db.session.add(customer)
            db.session.flush()
        
        truck = Truck.query.filter_by(number=truck_number).first()
        if not truck:
            truck = Truck(number=truck_number)
            db.session.add(truck)
            db.session.flush()
        
        trip.customer_id = customer.id
        trip.customer_name = customer_name
        trip.pickup = request.form['pickup'].strip()
        trip.destination = request.form['destination'].strip()
        trip.truck_number = truck_number
        trip.load_type = request.form['load_type'].strip()
        trip.weight = float(request.form['weight'])
        trip.rate_per_km = float(request.form['rate_per_km'])
        trip = recalculate_fare(trip)
        db.session.commit()
        log_audit('edit', 'trip', trip.id, old, {
            'customer': customer_name, 'pickup': trip.pickup,
            'destination': trip.destination, 'truck': truck_number
        })
        update_truck_stats()
        flash('Trip updated successfully!', 'success')
        return redirect(url_for('trip_details', trip_id=trip_id))
    return render_template('edit_trip.html', trip=trip)

@app.route('/delete_trip/<trip_id>', methods=['POST'])
@login_required
def delete_trip(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    if Payment.query.filter_by(trip_id=trip_id).first():
        flash('Cannot delete trip with payment records!', 'error')
        return redirect(url_for('trip_details', trip_id=trip_id))
    db.session.delete(trip)
    db.session.commit()
    update_customer_stats()
    update_truck_stats()
    flash('Trip deleted successfully!', 'success')
    return redirect(url_for('trips'))

# ===== CUSTOMER MANAGEMENT =====

@app.route('/add_customer', methods=['GET', 'POST'])
@login_required
def add_customer():
    if request.method == 'POST':
        name = request.form['name'].strip()
        if Customer.query.filter_by(name=name).first():
            flash('Customer already exists!', 'error')
            return redirect(url_for('add_customer'))
        customer = Customer(
            name=name,
            phone=request.form['phone'].strip(),
            email=request.form['email'].strip(),
            address=request.form['address'].strip()
        )
        db.session.add(customer)
        db.session.commit()
        log_audit('create', 'customer', customer.id, None, {'name': name})
        flash('Customer added successfully!', 'success')
        return redirect(url_for('customers'))
    return render_template('add_customer.html')

@app.route('/customers')
@login_required
def customers():
    customers_data = Customer.query.all()
    return render_template('customers.html', customers=customers_data)

@app.route('/customer/<customer_id>')
@login_required
def customer_details(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    customer_trips = Trip.query.filter_by(customer_name=customer.name).all()
    return render_template('customer_details.html', customer=customer, trips=customer_trips)

@app.route('/edit_customer/<customer_id>', methods=['GET', 'POST'])
@login_required
def edit_customer(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    if request.method == 'POST':
        old_name = customer.name
        customer.name = request.form['name'].strip()
        customer.phone = request.form['phone'].strip()
        customer.email = request.form['email'].strip()
        customer.address = request.form['address'].strip()
        db.session.commit()
        log_audit('edit', 'customer', customer.id, {'name': old_name}, {'name': customer.name})
        flash('Customer updated successfully!', 'success')
        return redirect(url_for('customer_details', customer_id=customer_id))
    return render_template('edit_customer.html', customer=customer)

@app.route('/delete_customer/<customer_id>', methods=['POST'])
@login_required
def delete_customer(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    active = Trip.query.filter_by(customer_name=customer.name).filter(
        Trip.status.in_(['In Transit', 'Booked'])).first()
    if active:
        flash('Cannot delete customer with active trips!', 'error')
        return redirect(url_for('customer_details', customer_id=customer_id))
    db.session.delete(customer)
    db.session.commit()
    flash('Customer deleted successfully!', 'success')
    return redirect(url_for('customers'))

# ===== TRUCK MANAGEMENT =====

@app.route('/add_truck', methods=['GET', 'POST'])
@login_required
def add_truck():
    if request.method == 'POST':
        number = request.form['number'].strip().upper()
        if Truck.query.filter_by(number=number).first():
            flash('Truck already exists!', 'error')
            return redirect(url_for('add_truck'))
        truck = Truck(
            number=number,
            model=request.form['model'].strip(),
            capacity=float(request.form['capacity'])
        )
        db.session.add(truck)
        db.session.commit()
        log_audit('create', 'truck', truck.id, None, {'number': number})
        flash('Truck added successfully!', 'success')
        return redirect(url_for('trucks'))
    return render_template('add_truck.html')

@app.route('/trucks')
@login_required
def trucks():
    trucks_data = Truck.query.all()
    return render_template('trucks.html', trucks=trucks_data)

# ===== SEARCH =====

@app.route('/search_trips', methods=['GET', 'POST'])
@login_required
def search_trips():
    results = []
    if request.method == 'POST':
        search_type = request.form['search_type']
        query = request.form['query'].strip()
        if search_type == 'customer':
            results = Trip.query.filter(Trip.customer_name.ilike(f'%{query}%')).all()
        elif search_type == 'truck':
            results = Trip.query.filter(Trip.truck_number.ilike(f'%{query}%')).all()
        elif search_type == 'status':
            results = Trip.query.filter_by(status=query).all()
    return render_template('search_trips.html', results=results)

# ===== REPORTS =====

@app.route('/reports')
@login_required
def reports():
    today = datetime.now().date()
    daily_earnings = db.session.query(db.func.sum(Trip.total_fare)).filter(
        Trip.status == 'Delivered',
        db.func.date(Trip.timestamp) == today
    ).scalar() or 0.0
    
    current_month = datetime.now().month
    current_year = datetime.now().year
    monthly_earnings = db.session.query(db.func.sum(Trip.total_fare)).filter(
        Trip.status == 'Delivered',
        db.func.extract('month', Trip.timestamp) == current_month,
        db.func.extract('year', Trip.timestamp) == current_year
    ).scalar() or 0.0
    
    total_revenue = db.session.query(db.func.sum(Trip.total_fare)).filter_by(status='Delivered').scalar() or 0.0
    total_expenses = db.session.query(db.func.sum(Expense.amount)).join(Trip).filter(
        Trip.status == 'Delivered'
    ).scalar() or 0.0
    net_profit = total_revenue - total_expenses
    
    booked_count = Trip.query.filter_by(status='Booked').count()
    transit_count = Trip.query.filter_by(status='In Transit').count()
    delivered_count = Trip.query.filter_by(status='Delivered').count()
    available_trucks = Truck.query.filter_by(status='Available').count()
    busy_trucks = Truck.query.filter_by(status='Busy').count()
    
    pending = []
    total_pending = 0
    for trip in Trip.query.all():
        paid = db.session.query(db.func.sum(Payment.amount)).filter_by(trip_id=trip.id).scalar() or 0.0
        remaining = trip.total_fare - paid
        if remaining > 0:
            pending.append({'trip': trip, 'remaining': remaining})
            total_pending += remaining
    
    return render_template('reports.html',
                         daily_earnings=daily_earnings,
                         monthly_earnings=monthly_earnings,
                         pending_payments=pending,
                         total_pending=total_pending,
                         total_revenue=total_revenue,
                         total_expenses=total_expenses,
                         net_profit=net_profit,
                         booked_count=booked_count,
                         transit_count=transit_count,
                         delivered_count=delivered_count,
                         available_trucks=available_trucks,
                         busy_trucks=busy_trucks)

# ===== LOCATION TRACKING =====

@app.route('/update_location', methods=['POST'])
@login_required
def update_location():
    data = request.get_json()
    user = User.query.get(session['user_id'])
    if not user or not user.truck_number:
        return jsonify({'error': 'No truck assigned'}), 400
    
    location = Location(
        truck_number=user.truck_number,
        driver_id=user.id,
        driver_name=user.name,
        latitude=data['latitude'],
        longitude=data['longitude'],
        speed=data.get('speed', 0),
        heading=data.get('heading', 0),
        accuracy=data.get('accuracy', 0)
    )
    db.session.add(location)
    user.last_location_lat = data['latitude']
    user.last_location_lon = data['longitude']
    user.last_location_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'success': True, 'location_id': location.id})

@app.route('/get_locations/<truck_number>')
@login_required
def get_locations(truck_number):
    yesterday = datetime.now() - timedelta(days=1)
    locations = Location.query.filter(
        Location.truck_number == truck_number,
        Location.timestamp > yesterday
    ).order_by(Location.timestamp).all()
    return jsonify([{
        'latitude': l.latitude,
        'longitude': l.longitude,
        'timestamp': l.timestamp.isoformat(),
        'speed': l.speed,
        'heading': l.heading
    } for l in locations])

@app.route('/live_tracking')
@login_required
def live_tracking():
    trucks = Truck.query.all()
    users = User.query.filter_by(role='driver', is_active=True).all()
    active_drivers = []
    for user in users:
        if user.truck_number:
            truck = Truck.query.filter_by(number=user.truck_number).first()
            if truck:
                active_drivers.append({
                    'user': user,
                    'truck': truck,
                    'last_location': {
                        'latitude': user.last_location_lat,
                        'longitude': user.last_location_lon,
                        'timestamp': user.last_location_at.isoformat() if user.last_location_at else None
                    } if user.last_location_lat else None
                })
    return render_template('live_tracking_google.html', active_drivers=active_drivers, google_maps_key=GOOGLE_MAPS_API_KEY)

@app.route('/location_history/<truck_number>')
@login_required
def location_history(truck_number):
    locations = Location.query.filter_by(truck_number=truck_number).order_by(Location.timestamp.desc()).all()
    history_by_date = {}
    for loc in locations:
        date = loc.timestamp.strftime('%Y-%m-%d')
        if date not in history_by_date:
            history_by_date[date] = []
        history_by_date[date].append(loc)
    return render_template('location_history.html', truck_number=truck_number, history_by_date=history_by_date)

@app.route('/driver_dashboard')
@login_required
def driver_dashboard():
    user = User.query.get(session['user_id'])
    if not user or user.role != 'driver':
        flash('Access denied!', 'error')
        return redirect(url_for('dashboard'))
    assigned_trips = Trip.query.filter_by(truck_number=user.truck_number).filter(
        Trip.status.in_(['In Transit', 'Booked'])).all()
    recent_locations = Location.query.filter_by(truck_number=user.truck_number).order_by(
        Location.timestamp.desc()).limit(10).all()
    return render_template('driver_dashboard.html',
                         user=user,
                         assigned_trips=assigned_trips,
                         recent_locations=recent_locations)

# ===== USER MANAGEMENT =====

@app.route('/manage_users')
@admin_required
def manage_users():
    users = User.query.all()
    return render_template('manage_users.html', users=users)

@app.route('/create_user', methods=['GET', 'POST'])
@admin_required
def create_user():
    if request.method == 'POST':
        if User.query.filter_by(username=request.form['username']).first():
            flash('Username already exists!', 'error')
            return redirect(url_for('create_user'))
        user = User(
            username=request.form['username'],
            password=hash_password(request.form['password']),
            name=request.form['name'],
            email=request.form['email'],
            phone=request.form['phone'],
            role=request.form['role'],
            truck_number=request.form.get('truck_number', '')
        )
        db.session.add(user)
        db.session.commit()
        flash('User created successfully!', 'success')
        return redirect(url_for('manage_users'))
    trucks = Truck.query.all()
    return render_template('create_user.html', trucks=trucks)

@app.route('/edit_user/<user_id>', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    if request.method == 'POST':
        user.name = request.form['name']
        user.email = request.form['email']
        user.phone = request.form['phone']
        user.role = request.form['role']
        user.truck_number = request.form.get('truck_number', '')
        user.is_active = 'is_active' in request.form
        if request.form.get('password'):
            user.password = hash_password(request.form['password'])
        db.session.commit()
        flash('User updated successfully!', 'success')
        return redirect(url_for('manage_users'))
    trucks = Truck.query.all()
    return render_template('edit_user.html', user=user, trucks=trucks)

@app.route('/delete_user/<user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('User deleted successfully!', 'success')
    return redirect(url_for('manage_users'))

# ===== DOCUMENTS =====

@app.route('/documents')
@login_required
def documents():
    docs = Document.query.all()
    trucks = Truck.query.all()
    users = User.query.all()
    documents_by_entity = {}
    for doc in docs:
        key = f"{doc.entity_type}_{doc.entity_id}"
        if key not in documents_by_entity:
            documents_by_entity[key] = []
        documents_by_entity[key].append(doc)
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
            return redirect(url_for('upload_document'))
        file = request.files['file']
        if file.filename == '':
            flash('No file selected!', 'error')
            return redirect(url_for('upload_document'))
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
            filename = f"doc_{timestamp}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            doc = Document(
                filename=filename,
                original_filename=file.filename,
                entity_type=request.form['entity_type'],
                entity_id=request.form['entity_id'],
                document_type=request.form['document_type'],
                description=request.form.get('description', ''),
                expiry_date=datetime.strptime(request.form['expiry_date'], '%Y-%m-%d').date() if request.form.get('expiry_date') else None,
                uploaded_by=session.get('username'),
                file_path=file_path
            )
            db.session.add(doc)
            db.session.commit()
            log_audit('upload', 'document', doc.id, None, {'filename': file.filename, 'type': doc.document_type})
            flash('Document uploaded successfully!', 'success')
            return redirect(url_for('documents'))
        else:
            flash('Invalid file type!', 'error')
            return redirect(url_for('upload_document'))
    trucks = Truck.query.all()
    users = User.query.all()
    return render_template('upload_document.html', trucks=trucks, users=users)

@app.route('/download_document/<document_id>')
@login_required
def download_document(document_id):
    doc = Document.query.get_or_404(document_id)
    return send_from_directory(app.config['UPLOAD_FOLDER'], doc.filename, as_attachment=True, download_name=doc.original_filename)

@app.route('/delete_document/<document_id>', methods=['POST'])
@login_required
def delete_document(document_id):
    doc = Document.query.get_or_404(document_id)
    try:
        if doc.file_path and os.path.exists(doc.file_path):
            os.remove(doc.file_path)
    except Exception:
        pass
    db.session.delete(doc)
    db.session.commit()
    log_audit('delete', 'document', document_id, {'filename': doc.original_filename}, None)
    flash('Document deleted successfully!', 'success')
    return redirect(url_for('documents'))

# ===== PDF REPORTS =====

@app.route('/download_report/<report_type>')
@login_required
def download_report(report_type):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=72, leftMargin=72,
                            topMargin=72, bottomMargin=18)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=1,
        textColor=colors.HexColor('#1a5276')
    )

    story.append(Paragraph("KALAWATI TRANSPORT", title_style))
    story.append(Paragraph(f"Report Generated: {datetime.now().strftime('%d-%b-%Y %H:%M')}", styles['Normal']))
    story.append(Spacer(1, 20))

    if report_type == 'summary':
        story.append(Paragraph("Financial Summary Report", styles['Heading2']))
        story.append(Spacer(1, 12))

        total_revenue = db.session.query(db.func.sum(Trip.total_fare)).filter_by(status='Delivered').scalar() or 0.0
        total_expenses = db.session.query(db.func.sum(Expense.amount)).join(Trip).filter(Trip.status == 'Delivered').scalar() or 0.0
        net_profit = total_revenue - total_expenses
        total_trips = Trip.query.filter_by(status='Delivered').count()
        total_customers = Customer.query.count()
        total_trucks = Truck.query.count()

        data = [
            ['Metric', 'Value'],
            ['Total Revenue', f'₹{total_revenue:,.2f}'],
            ['Total Expenses', f'₹{total_expenses:,.2f}'],
            ['Net Profit', f'₹{net_profit:,.2f}'],
            ['Completed Trips', str(total_trips)],
            ['Total Customers', str(total_customers)],
            ['Total Trucks', str(total_trucks)],
        ]
        t = Table(data, colWidths=[3*inch, 3*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5276')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 12),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        story.append(t)

    elif report_type == 'trips':
        story.append(Paragraph("Trip Details Report", styles['Heading2']))
        story.append(Spacer(1, 12))

        trips = Trip.query.order_by(Trip.timestamp.desc()).all()
        data = [['ID', 'Customer', 'Pickup', 'Destination', 'Truck', 'Status', 'Fare']]
        for trip in trips:
            data.append([
                trip.id[:8],
                trip.customer_name,
                trip.pickup[:20],
                trip.destination[:20],
                trip.truck_number,
                trip.status,
                f'₹{trip.total_fare:,.2f}'
            ])
        t = Table(data, colWidths=[0.8*inch, 1.2*inch, 1.3*inch, 1.3*inch, 0.9*inch, 0.8*inch, 0.9*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5276')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        story.append(t)

    elif report_type == 'customers':
        story.append(Paragraph("Customer Report", styles['Heading2']))
        story.append(Spacer(1, 12))

        customers = Customer.query.order_by(Customer.total_earnings.desc()).all()
        data = [['Name', 'Phone', 'Email', 'Trips', 'Earnings', 'Rating']]
        for customer in customers:
            data.append([
                customer.name,
                customer.phone or '-',
                customer.email or '-',
                str(customer.total_trips),
                f'₹{customer.total_earnings:,.2f}',
                f'{customer.average_rating or 0}/5'
            ])
        t = Table(data, colWidths=[1.5*inch, 1.2*inch, 1.5*inch, 0.7*inch, 1.1*inch, 0.7*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5276')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        story.append(t)

    elif report_type == 'trucks':
        story.append(Paragraph("Truck Fleet Report", styles['Heading2']))
        story.append(Spacer(1, 12))

        trucks = Truck.query.order_by(Truck.total_earnings.desc()).all()
        data = [['Number', 'Model', 'Capacity', 'Status', 'Trips', 'Earnings', 'Rating']]
        for truck in trucks:
            data.append([
                truck.number,
                truck.model or '-',
                f'{truck.capacity}T',
                truck.status,
                str(truck.total_trips),
                f'₹{truck.total_earnings:,.2f}',
                f'{truck.average_rating or 0}/5'
            ])
        t = Table(data, colWidths=[0.9*inch, 1.1*inch, 0.7*inch, 0.8*inch, 0.6*inch, 1.0*inch, 0.6*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5276')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        story.append(t)

    else:
        flash('Invalid report type!', 'error')
        return redirect(url_for('reports'))

    doc.build(story)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True,
                     download_name=f'kalawati_report_{report_type}_{datetime.now().strftime("%Y%m%d")}.pdf',
                     mimetype='application/pdf')

# ===== APP ENTRY POINT WITH JSON MIGRATION =====

def migrate_json_to_sqlite():
    """One-time migration from JSON files to SQLite database"""
    import json

    json_dir = os.path.dirname(os.path.abspath(__file__))

    # Migrate Users
    users_file = os.path.join(json_dir, 'users.json')
    if os.path.exists(users_file):
        with open(users_file, 'r', encoding='utf-8') as f:
            users_data = json.load(f)
        for u in users_data:
            if not User.query.filter_by(username=u['username']).first():
                user = User(
                    id=u.get('id', str(uuid.uuid4())),
                    username=u['username'],
                    password=u['password'],
                    name=u.get('name', ''),
                    email=u.get('email', ''),
                    phone=u.get('phone', ''),
                    role=u.get('role', 'driver'),
                    truck_number=u.get('truck_number', ''),
                    is_active=u.get('is_active', True),
                    profile_photo=u.get('profile_photo', None)
                )
                try:
                    user.created_at = datetime.fromisoformat(u['created_at']) if 'created_at' in u else datetime.utcnow()
                except:
                    user.created_at = datetime.utcnow()
                if u.get('last_login'):
                    try:
                        user.last_login = datetime.fromisoformat(u['last_login'])
                    except:
                        pass
                db.session.add(user)
        db.session.commit()
        print(f"Migrated {len(users_data)} users")

    # Migrate Customers
    customers_file = os.path.join(json_dir, 'customers.json')
    if os.path.exists(customers_file):
        with open(customers_file, 'r', encoding='utf-8') as f:
            customers_data = json.load(f)
        for c in customers_data:
            if not Customer.query.filter_by(id=c.get('id')).first():
                customer = Customer(
                    id=c.get('id', str(uuid.uuid4())),
                    name=c['name'],
                    phone=c.get('phone', ''),
                    email=c.get('email', ''),
                    address=c.get('address', ''),
                    total_trips=c.get('total_trips', 0),
                    total_earnings=c.get('total_earnings', 0.0),
                    average_rating=c.get('average_rating', None),
                    total_ratings=c.get('total_ratings', 0)
                )
                try:
                    customer.created_at = datetime.fromisoformat(c['created_at']) if 'created_at' in c else datetime.utcnow()
                except:
                    customer.created_at = datetime.utcnow()
                db.session.add(customer)
                for r in c.get('ratings', []):
                    rating = Rating(
                        trip_id=r.get('trip_id'),
                        entity_type='customer',
                        entity_id=customer.id,
                        rating=r['rating'],
                        review=r.get('review', ''),
                        rated_by=r.get('rated_by', 'system'),
                        rated_at=datetime.fromisoformat(r['rated_at']) if r.get('rated_at') else datetime.utcnow()
                    )
                    db.session.add(rating)
        db.session.commit()
        print(f"Migrated {len(customers_data)} customers")

    # Migrate Trucks
    trucks_file = os.path.join(json_dir, 'trucks.json')
    if os.path.exists(trucks_file):
        with open(trucks_file, 'r', encoding='utf-8') as f:
            trucks_data = json.load(f)
        for t in trucks_data:
            if not Truck.query.filter_by(id=t.get('id')).first():
                truck = Truck(
                    id=t.get('id', str(uuid.uuid4())),
                    number=t['number'].upper(),
                    model=t.get('model', ''),
                    capacity=t.get('capacity', 0.0),
                    status=t.get('status', 'Available'),
                    total_trips=t.get('total_trips', 0),
                    total_earnings=t.get('total_earnings', 0.0),
                    average_rating=t.get('average_rating', None),
                    total_ratings=t.get('total_ratings', 0)
                )
                try:
                    truck.added_at = datetime.fromisoformat(t['added_at']) if 'added_at' in t else datetime.utcnow()
                except:
                    truck.added_at = datetime.utcnow()
                db.session.add(truck)
                for r in t.get('ratings', []):
                    rating = Rating(
                        trip_id=r.get('trip_id'),
                        entity_type='truck',
                        entity_id=truck.id,
                        rating=r['rating'],
                        review=r.get('review', ''),
                        rated_by=r.get('rated_by', 'system'),
                        rated_at=datetime.fromisoformat(r['rated_at']) if r.get('rated_at') else datetime.utcnow()
                    )
                    db.session.add(rating)
        db.session.commit()
        print(f"Migrated {len(trucks_data)} trucks")

    # Migrate Trips
    trips_file = os.path.join(json_dir, 'trips.json')
    if os.path.exists(trips_file):
        with open(trips_file, 'r', encoding='utf-8') as f:
            trips_data = json.load(f)
        for t in trips_data:
            if not Trip.query.filter_by(id=t.get('id')).first():
                customer = Customer.query.filter_by(name=t['customer']).first()
                if not customer:
                    customer = Customer(name=t['customer'])
                    db.session.add(customer)
                    db.session.flush()

                trip = Trip(
                    id=t.get('id', str(uuid.uuid4())),
                    customer_id=customer.id,
                    customer_name=t['customer'],
                    pickup=t.get('pickup', ''),
                    destination=t.get('destination', ''),
                    truck_number=t.get('truck_number', '').upper(),
                    load_type=t.get('load_type', ''),
                    weight=t.get('weight', 0.0),
                    rate_per_km=t.get('rate_per_km', 0.0),
                    distance_km=t.get('distance_km'),
                    loading_charges=t.get('loading_charges', 0.0),
                    total_fare=t.get('total_fare', 0.0),
                    advance_paid=t.get('advance_paid', 0.0),
                    status=t.get('status', 'Booked')
                )
                try:
                    trip.timestamp = datetime.fromisoformat(t['timestamp']) if 'timestamp' in t else datetime.utcnow()
                except:
                    trip.timestamp = datetime.utcnow()
                db.session.add(trip)
                db.session.flush()

                for p in t.get('payments', []):
                    payment = Payment(
                        trip_id=trip.id,
                        type=p.get('type', 'payment'),
                        amount=p.get('amount', 0.0),
                        timestamp=datetime.fromisoformat(p['timestamp']) if p.get('timestamp') else datetime.utcnow()
                    )
                    db.session.add(payment)

                for e in t.get('expenses', []):
                    expense = Expense(
                        trip_id=trip.id,
                        type=e.get('type', 'other'),
                        amount=e.get('amount', 0.0),
                        description=e.get('description', ''),
                        timestamp=datetime.fromisoformat(e['timestamp']) if e.get('timestamp') else datetime.utcnow()
                    )
                    db.session.add(expense)

                if t.get('customer_rating'):
                    cr = t['customer_rating']
                    rating = Rating(
                        trip_id=trip.id,
                        entity_type='customer',
                        entity_id=customer.id,
                        rating=cr['rating'],
                        review=cr.get('review', ''),
                        rated_by=cr.get('rated_by', 'system'),
                        rated_at=datetime.fromisoformat(cr['rated_at']) if cr.get('rated_at') else datetime.utcnow()
                    )
                    db.session.add(rating)

                if t.get('truck_rating'):
                    tr = t['truck_rating']
                    truck = Truck.query.filter_by(number=trip.truck_number).first()
                    rating = Rating(
                        trip_id=trip.id,
                        entity_type='truck',
                        entity_id=truck.id if truck else None,
                        rating=tr['rating'],
                        review=tr.get('review', ''),
                        rated_by=tr.get('rated_by', 'system'),
                        rated_at=datetime.fromisoformat(tr['rated_at']) if tr.get('rated_at') else datetime.utcnow()
                    )
                    db.session.add(rating)

        db.session.commit()
        print(f"Migrated {len(trips_data)} trips")

    update_customer_stats()
    update_truck_stats()
    print("Migration complete! JSON data imported into SQLite.")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not User.query.first():
            print("Running JSON to SQLite migration...")
            migrate_json_to_sqlite()
    app.run(debug=True, host='0.0.0.0', port=5000)

# 👇 ADD THIS OUTSIDE (NO INDENT)
handler = app