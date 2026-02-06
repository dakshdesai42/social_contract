"""One-time database initialization for production.
Run with: python init_db.py
Called by Procfile before gunicorn starts.
"""
from app import app
from models import db, seed_achievements

with app.app_context():
    db.create_all()
    seed_achievements()
    print("Database tables created and achievements seeded.")
