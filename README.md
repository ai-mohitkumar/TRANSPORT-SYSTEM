# 🚛 Kalawati Transport ERP & Logistics Intelligence Platform

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.3.3-green.svg)](https://flask.palletsprojects.com/)
[![SQLite](https://img.shields.io/badge/Database-SQLite-yellow.svg)](https://www.sqlite.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Deployment](https://img.shields.io/badge/Deployment-Render-orange.svg)](https://kalawati-transport.onrender.com)

> A production-grade Transport ERP system built with Python and Flask to manage trips, customers, trucks, payments, expenses, live GPS tracking, analytics, and automated PDF reporting.

---

## 🌐 Live Demo

- **Application:** https://kalawati-transport.onrender.com
- **Repository:** https://github.com/ai-mohitkumar/TRANSPORT-SYSTEM

---

## ✨ Key Features

### 🚚 Transport Operations
- Complete trip lifecycle management
- Customer and truck management
- Driver dashboard and role-based access control
- Smart search and filtering

### 💳 Finance & Payments
- Payment and expense tracking
- Pending dues and profit calculation
- PDF invoices and reports
- Razorpay online payment integration (UPI, Cards, Net Banking)

### 🗺️ Real-Time Tracking
- Google Maps distance calculation
- Fare estimation
- Live GPS tracking with location history

### 📊 Analytics & Reporting
- Revenue dashboards
- Trip status charts
- Top customers and truck utilization
- Exportable PDF reports

### 📎 Compliance & Documents
- Vehicle and driver document uploads
- Expiry tracking and reminders
- Audit logs

### 🎨 Professional UI
- Responsive Bootstrap 5 dashboard
- Modern admin interface
- Charts powered by Chart.js

---

## 🛠️ Tech Stack

| Category | Technologies |
|--------|--------|
| Backend | Python, Flask, SQLAlchemy, Flask-Migrate |
| Frontend | HTML5, CSS3, JavaScript, Bootstrap 5, Chart.js |
| Database | SQLite (development), PostgreSQL-ready |
| APIs | Google Maps Platform, Razorpay |
| Reports | ReportLab |
| Deployment | Gunicorn, Render |
| Tools | Git, GitHub, VS Code |

---

## 🏗️ Project Architecture

- MVC-inspired application structure
- SQLAlchemy ORM with relational models
- REST-style endpoints
- Environment-based configuration
- JSON-to-SQLite migration pipeline

---

## 📁 Project Structure

```text
TRANSPORT-SYSTEM/
├── transport_system/
│   ├── main.py
│   ├── models.py
│   ├── api/
│   ├── scripts/
│   ├── templates/
│   ├── static/
│   ├── uploads/
│   └── vercel.json
├── requirements.txt
├── README.md
├── LICENSE
└── vercel.json
🚀 Local Setup
1. Clone Repository
git clone https://github.com/ai-mohitkumar/TRANSPORT-SYSTEM.git
cd TRANSPORT-SYSTEM
2. Create Virtual Environment
python -m venv venv
3. Activate Virtual Environment

Windows PowerShell

.\venv\Scripts\Activate.ps1

macOS/Linux

source venv/bin/activate
4. Install Dependencies
pip install -r requirements.txt
pip install requests reportlab pandas numpy openpyxl razorpay
5. Optional Environment Variables
GOOGLE_MAPS_API_KEY=your_google_maps_api_key
RAZORPAY_KEY_ID=your_razorpay_key_id
RAZORPAY_KEY_SECRET=your_razorpay_key_secret
SECRET_KEY=your_secret_key
6. Run the Application
python .\transport_system\main.py
7. Open in Browser
http://127.0.0.1:5000
🔐 First Login
Open the application.
Register a new Admin account.
Log in to access the dashboard.
🌐 Deployment
Render
Build Command:
pip install -r requirements.txt
Start Command:
gunicorn transport_system.main:app
📈 Resume Highlights
Built and deployed a full-stack Transport ERP system.
Integrated Google Maps and live GPS tracking.
Implemented financial analytics and PDF reporting.
Added online payment processing using Razorpay.
Designed a scalable Flask + SQLAlchemy architecture.
🏆 Key Business Modules
Dashboard Analytics
Trip Management
Customer Management
Fleet Management
Driver Portal
Financial Management
Online Payments
Document Compliance
Audit Logs
Reporting
🔮 Future Enhancements
Progressive Web App (PWA)
Email and WhatsApp notifications
AI-based revenue forecasting
PostgreSQL production migration
Multi-tenant SaaS support
👨‍💻 Author

Mohit Kumar

LinkedIn: https://linkedin.com/in/mohitkumar1979
GitHub: https://github.com/ai-mohitkumar
Email: mkitman58@gmail.com
📄 License

This project is licensed under the MIT License.