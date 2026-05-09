




\## 🚛 Comprehensive Transport Management System



\*\*KALAWATI TRANSPORT\*\* is a full-featured web application for managing transport operations. Handle trips, customers, trucks, payments, live GPS tracking, PDF reports, and more - all in one place


\## ✨ Features



\- \*\*📊 Interactive Dashboard\*\* - Chart.js charts: Monthly earnings, trip status pie, top customers bar

\- \*\*🗺️ Google Maps Integration\*\* - Auto-distance calculation + real-time live tracking

\- \*\*🔄 Complete Trip Lifecycle\*\* - Book → Calculate Distance/Fare → Add Payments/Expenses → Track → Deliver → Rate

\- \*\*👥 Customer Management\*\* - Add/edit customers, view stats, ratings, trip history

\- \*\*🚚 Truck Fleet Management\*\* - Track availability, earnings, ratings, document uploads

\- \*\*💰 Financial Tracking\*\* - Payments, expenses, pending dues, profit calculations

\- \*\*📄 PDF Reports\*\* - Summary, trips, customers, trucks (downloadable)

\- \*\*🔐 Role-Based Auth\*\* - Admin panel + Driver dashboard

\- \*\*📱 Live GPS Tracking\*\* - Real-time location updates with history

\- \*\*📎 Document Management\*\* - Upload truck/driver docs with expiry tracking

\- \*\*🔍 Smart Search\*\* - Filter trips by customer, truck, status

\- \*\*⭐ Ratings System\*\* - Rate customers and trucks post-delivery

\- \*\*📈 Audit Logs\*\* - Track all create/update/delete actions

\- \*\*⚡ JSON to SQLite Migration\*\* - Seamless data import from legacy JSON files



\## 🛠️ Tech Stack



| Category | Technologies |

|----------|--------------|

| Backend | Python 3.8+, Flask 2.3.3, SQLAlchemy, Flask-Migrate |

| Database | SQLite (kalawati.db), legacy JSON support |

| Frontend | HTML5, Bootstrap 5, Chart.js, Google Maps JavaScript API |

| Reports | ReportLab (PDF generation) |

| Other | Werkzeug, Gunicorn (production), Ngrok (tunneling) |



\## 🚀 Local Setup



\### 1. Prerequisites

\- Python 3.8+

\- Git



\### 2. Clone \& Setup

```bash

git clone <your-repo> transport\_system

cd transport\_system

```



\### 3. Virtual Environment (Recommended)

```bash

\# Windows

python -m venv venv\_local

venv\_local\\Scripts\\activate



\# macOS/Linux

python3 -m venv venv\_local

source venv\_local/bin/activate

```



\### 4. Install Dependencies

```bash

pip install -r requirements.txt

```



\### 5. Database Setup

Database auto-migrates from JSON files (`users.json`, `customers.json`, etc.) to `kalawati.db` on first run.



\### 6. Google Maps (Optional)

```bash

\# Windows

set GOOGLE\_MAPS\_API\_KEY=your\_api\_key\_here



\# Or in .env file

echo GOOGLE\_MAPS\_API\_KEY=your\_api\_key\_here > .env

```



\### 7. Run the App

```bash

python main.py

```

\*\*Open:\*\* http://localhost:5000



\### 8. First Login

1\. Click \*\*Register\*\* → Create admin account

2\. Login → Access full dashboard



\## 🌐 Deployment



\### Render.com (Free Tier)

1\. Push to GitHub

2\. Connect repo in Render

3\. Build: `pip install -r requirements.txt`

4\. Start: `gunicorn transport_system.main:app`

5\. Env:
   - `GOOGLE\_MAPS\_API\_KEY=your\_key` (optional)
   - `SECRET\_KEY=your\_secret` (recommended)



\### Vercel (via vercel.json)


```bash

npm i -g vercel

vercel --prod

```



\### Heroku

```bash

git push heroku main

heroku config:set GOOGLE\_MAPS\_API\_KEY=your\_key

```



\## 🗃️ Database \& Data Migration



\- \*\*Legacy:\*\* JSON files (`users.json`, `trips.json`, etc.)

\- \*\*Production:\*\* SQLite (`kalawati.db`)

\- \*\*Migration:\*\* Auto-runs `migrate\_json\_to\_sqlite()` on first launch

\- \*\*Models:\*\* See `models.py` (User, Trip, Customer, Truck, Payment, Expense, Location, Document)



\## 🔌 Key API Endpoints



| Endpoint | Description | Auth |

|----------|-------------|------|

| `/api/dashboard\_stats` | Chart.js data | ✅ |

| `/api/calculate\_distance` | Google Maps distance | ✅ |

| `/get\_locations/:truck` | GPS location history | ✅ |

| `/update\_location` | POST driver GPS | ✅ |

| `/download_report/:report_type` | PDF reports | ✅ |



\## 📁 Project Structure

```

transport\_system/

├── transport_system/main.py  # Flask app + all routes

├── transport_system/models.py  # SQLAlchemy ORM models


├── requirements.txt     # Dependencies

├── kalawati.db          # SQLite database

├── templates/           # HTML Jinja2 templates

├── static/              # CSS/JS/images

├── uploads/             # Documents

├── \*.json               # Legacy data (auto-migrated)

├── Procfile             # Heroku deployment

├── runtime.txt          # Python version

└── vercel.json          # Vercel config

```



\## 📸 Screenshots



1\. \*\*Dashboard\*\*: Earnings charts, recent trips, pending payments

2\. \*\*Trip Creation\*\*: Auto-distance via Google Maps

3\. \*\*Live Tracking\*\*: Real-time GPS on Google Maps

4\. \*\*PDF Reports\*\*: Professional financial summaries

5\. \*\*Driver Dashboard\*\*: Assigned trips + GPS update



\*(Add actual screenshots to `/static/screenshots/` and link here)\*



\## 🤝 Contributing



1\. Fork the repo

2\. Create feature branch (`git checkout -b feature/AmazingFeature`)

3\. Commit changes (`git commit -m 'Add some AmazingFeature'`)

4\. Push to branch (`git push origin feature/AmazingFeature`)

5\. Open Pull Request



See \[CONTRIBUTING.md](CONTRIBUTING.md) for details.



\## 📋 TODOs

\- See \[TODO.md](TODO.md)

\- \[TODO\_launch.md](TODO\_launch.md)

\- \[TODO\_single\_main.md](TODO\_single\_main.md)



\## 📄 License

This project is MIT licensed. See \[LICENSE](LICENSE) for details.



\## 🙏 Acknowledgments

\- Flask \& SQLAlchemy teams

\- Chart.js, Bootstrap, Google Maps

\- ReportLab for PDF generation



\---



⭐ \*\*Star this repo if useful!\*\* 🚀





