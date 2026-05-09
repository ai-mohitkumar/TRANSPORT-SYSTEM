import sys, os
# Ensure transport_system directory is on path
sys.path.insert(0, os.path.dirname(__file__))
from main import app, db, hash_password
from models import User

with app.app_context():
    if not User.query.filter_by(username='admin').first():
        u = User(username='admin', password=hash_password('admin123'), name='Admin', role='admin')
        db.session.add(u)
        db.session.commit()
        print('Created admin: admin / admin123')
    else:
        print('Admin already exists')
