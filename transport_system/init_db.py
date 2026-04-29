"""Production database initialization script"""
from main import app, db, migrate_json_to_sqlite
import os

with app.app_context():
    db.create_all()
    migrate_json_to_sqlite()
    print("✅ Database initialized and JSON data migrated to kalawati.db")

