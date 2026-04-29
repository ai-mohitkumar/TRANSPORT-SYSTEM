# KALAWATI TRANSPORT - Transport Management System 🚛

## 🎯 Quick Start

**Run the app:**
```cmd
cd transport_system
..\venv_local\Scripts\python.exe main.py
```

**Open in browser:** http://localhost:5000

## ✨ Features
- **Chart.js Dashboard** — Monthly earnings trend, trip status pie chart, top customers bar chart
- **Google Maps Integration** — Auto-distance calculation when creating trips
- **Google Maps Live Tracking** — Real-time truck location tracking on Google Maps
- **Full Trip Lifecycle** — Booking → Distance → Fare → Payment → Delivery
- **Customer & Truck Management** — With statistics and ratings
- **PDF Reports** — Financial summary, trip details, customer & truck reports
- **Admin/Driver Login** — Role-based access control
- **Document Upload** — Truck & driver document management with expiry tracking

## 🗺️ Google Maps Setup (Optional)
To enable Google Maps features, set your API key:
```cmd
set GOOGLE_MAPS_API_KEY=your_api_key_here
```
Then restart the app.

## 📁 Project Structure
- `main.py` — Flask backend with all routes
- `models.py` — SQLAlchemy database models
- `templates/` — HTML templates
- `static/` — Logo and assets
- `uploads/` — Uploaded documents

## 🔗 First Time Use
1. Run the app
2. Go to http://localhost:5000
3. Click **Register** to create an account
4. Login and access the dashboard
