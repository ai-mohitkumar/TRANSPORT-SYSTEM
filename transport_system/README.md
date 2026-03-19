# KALAWATI TRANSPORT - Payment & Tracking System

## Setup
1. cd transport_system
2. pip install -r requirements.txt

## Run Options

### 🌐 Web Interface (Recommended)
```bash
python main.py web
```
Then open your browser and go to: **http://localhost:5000**

### 💻 Command Line Interface
```bash
python main.py
```

## Features Implemented
- **STEP 1-11: Complete Transport Workflow** - Full trip lifecycle management
- **Customer Management** - Add/view customers with trip history and earnings
- **Truck Management** - Add/view trucks with capacity and status tracking
- **Expense Tracking** - Record fuel, tolls, maintenance costs per trip
- **Advanced Reports** - Daily/weekly/monthly earnings, pending payments, profit/loss
- **Search & Filter** - Find trips by customer, truck, status, or date range
- **Trip Editing** - Modify trip details and status
- **Real-time Statistics** - Automatic calculation of earnings, expenses, and profits
- **Beautiful Web UI** - Modern Bootstrap interface with responsive design

## Web Interface Menu
### 📝 TRIP MANAGEMENT
- **Create New Trip** - Book new transport jobs
- **All Trips** - View and manage all trips
- **Search Trips** - Find trips by various criteria

### 👥 CUSTOMER MANAGEMENT
- **Add Customer** - Register new customers
- **View Customers** - Customer database with statistics

### 🚛 TRUCK MANAGEMENT
- **Add Truck** - Register new vehicles
- **View Trucks** - Fleet management dashboard

### 📊 REPORTS
- **Generate Reports** - Financial and operational analytics

## Data Storage
- `trips.json` - Complete trip records with payments and expenses
- `customers.json` - Customer database with performance metrics
- `trucks.json` - Fleet management with utilization tracking

## Reports Available
- **Daily Earnings** - Today's revenue
- **Monthly Earnings** - Current month performance
- **Pending Payments** - Outstanding customer payments
- **Profit & Loss** - Complete financial analysis

## Future Enhancements
- Google Maps API for automatic distance calculation
- GPS tracking integration with real-time location updates
- SMS/WhatsApp notifications system
- Invoice generation and PDF export
- Fuel efficiency tracking and optimization
- Driver management system
- Maintenance scheduling
- Multi-user support with authentication
- Mobile app companion

