"""
Database migration initialization script
Run this once after installing Flask-Migrate
"""

import os
import sys
from flask import Flask
from flask_migrate import Migrate
from models import db
from config import get_config

def init_migrations(app):
    """Initialize Alembic migration environment"""
    migrate = Migrate(app, db)
    print("✅ Migrations initialized!")
    print("\nUsage:")
    print("  flask db init          - Initialize migrations folder")
    print("  flask db migrate       - Create migration from model changes")
    print("  flask db upgrade       - Apply migrations to database")
    print("  flask db downgrade     - Revert last migration")
    print("\nExample workflow:")
    print("  1. Make changes to models.py")
    print("  2. Run: flask db migrate -m 'Add new field'")
    print("  3. Review migrations/versions/<timestamp>_add_new_field.py")
    print("  4. Run: flask db upgrade")

if __name__ == '__main__':
    # Create Flask app context
    app = Flask(__name__)
    app.config.from_object(get_config())
    
    # Initialize database
    db.init_app(app)
    init_migrations(app)
    
    # Create tables
    with app.app_context():
        print("\n📦 Creating initial tables...")
        db.create_all()
        print("✅ Tables created!")
