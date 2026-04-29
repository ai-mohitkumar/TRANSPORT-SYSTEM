from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

db = SQLAlchemy()

def generate_uuid():
    return str(uuid.uuid4())

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    name = db.Column(db.String(120))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    role = db.Column(db.String(20), default='driver')
    truck_number = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    profile_photo = db.Column(db.String(255))
    last_location_lat = db.Column(db.Float)
    last_location_lon = db.Column(db.Float)
    last_location_at = db.Column(db.DateTime)

class Customer(db.Model):
    __tablename__ = 'customers'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    address = db.Column(db.Text)
    total_trips = db.Column(db.Integer, default=0)
    total_earnings = db.Column(db.Float, default=0.0)
    average_rating = db.Column(db.Float)
    total_ratings = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Truck(db.Model):
    __tablename__ = 'trucks'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    number = db.Column(db.String(20), unique=True, nullable=False)
    model = db.Column(db.String(120))
    capacity = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='Available')
    total_trips = db.Column(db.Integer, default=0)
    total_earnings = db.Column(db.Float, default=0.0)
    average_rating = db.Column(db.Float)
    total_ratings = db.Column(db.Integer, default=0)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

class Trip(db.Model):
    __tablename__ = 'trips'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    customer_id = db.Column(db.String(36), db.ForeignKey('customers.id'))
    customer_name = db.Column(db.String(120))
    pickup = db.Column(db.String(255))
    destination = db.Column(db.String(255))
    truck_number = db.Column(db.String(20))
    load_type = db.Column(db.String(50))
    weight = db.Column(db.Float, default=0.0)
    rate_per_km = db.Column(db.Float, default=0.0)
    distance_km = db.Column(db.Float)
    loading_charges = db.Column(db.Float, default=0.0)
    total_fare = db.Column(db.Float, default=0.0)
    advance_paid = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='Booked')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime)
    delivered_at = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    gst_applicable = db.Column(db.Boolean, default=False)
    gst_amount = db.Column(db.Float, default=0.0)
    eway_bill = db.Column(db.String(50))

class Payment(db.Model):
    __tablename__ = 'payments'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    trip_id = db.Column(db.String(36), db.ForeignKey('trips.id'))
    type = db.Column(db.String(20))
    amount = db.Column(db.Float, default=0.0)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    method = db.Column(db.String(20), default='cash')

class Expense(db.Model):
    __tablename__ = 'expenses'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    trip_id = db.Column(db.String(36), db.ForeignKey('trips.id'))
    type = db.Column(db.String(20))
    amount = db.Column(db.Float, default=0.0)
    description = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Location(db.Model):
    __tablename__ = 'locations'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    truck_number = db.Column(db.String(20))
    driver_id = db.Column(db.String(36), db.ForeignKey('users.id'))
    driver_name = db.Column(db.String(120))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    speed = db.Column(db.Float, default=0.0)
    heading = db.Column(db.Float, default=0.0)
    accuracy = db.Column(db.Float, default=0.0)

class Document(db.Model):
    __tablename__ = 'documents'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    filename = db.Column(db.String(255))
    original_filename = db.Column(db.String(255))
    entity_type = db.Column(db.String(20))
    entity_id = db.Column(db.String(36))
    document_type = db.Column(db.String(50))
    description = db.Column(db.Text)
    expiry_date = db.Column(db.Date)
    uploaded_by = db.Column(db.String(80))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    file_path = db.Column(db.String(255))

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(36))
    username = db.Column(db.String(80))
    action = db.Column(db.String(50))
    entity_type = db.Column(db.String(20))
    entity_id = db.Column(db.String(36))
    old_values = db.Column(db.Text)
    new_values = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Rating(db.Model):
    __tablename__ = 'ratings'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    trip_id = db.Column(db.String(36), db.ForeignKey('trips.id'))
    entity_type = db.Column(db.String(20))
    entity_id = db.Column(db.String(36))
    rating = db.Column(db.Integer)
    review = db.Column(db.Text)
    rated_by = db.Column(db.String(80))
    rated_at = db.Column(db.DateTime, default=datetime.utcnow)
