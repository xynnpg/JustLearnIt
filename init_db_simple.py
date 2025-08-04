#!/usr/bin/env python3
"""
Simple Database Initialization Script for JustLearnIt
This script handles basic database operations without requiring Flask.
"""

import os
import sys
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

def get_db_path():
    """Get the database file path."""
    return Path("storage/storage.db")

def backup_database():
    """Create a backup of the existing database if it exists."""
    db_path = get_db_path()
    if db_path.exists():
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = db_path.parent / f"storage.db.backup.{timestamp}"
        shutil.copy2(db_path, backup_path)
        print(f"Database backed up to: {backup_path}")
        return backup_path
    return None

def create_database_structure():
    """Create all database tables using SQLAlchemy models."""
    print("Creating database tables...")
    
    try:
        # Import Flask app components
        from app import db, app
        
        with app.app_context():
            db.create_all()
            print("Database structure created successfully!")
            return True
    except ImportError as e:
        print(f"❌ Flask not available: {e}")
        print("Please install Flask dependencies first:")
        print("pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"❌ Error creating database: {e}")
        return False

def seed_initial_data():
    """Seed the database with initial data."""
    print("Seeding initial data...")
    
    try:
        from app import db, app
        from models import AdminCredentials, AdminWhitelist
        from app import generate_random_credentials, save_credentials
        
        with app.app_context():
            # Check if admin credentials already exist
            existing_admin = AdminCredentials.query.first()
            if not existing_admin:
                # Create initial admin credentials
                username, password = generate_random_credentials()
                timestamp = datetime.now().timestamp()
                
                if save_credentials(username, password, timestamp):
                    print(f"Initial admin credentials created:")
                    print(f"Username: {username}")
                    print(f"Password: {password}")
                    print("These credentials will be sent to the admin email if configured.")
                else:
                    print("Failed to create initial admin credentials.")
            
            # Check if admin whitelist exists
            existing_whitelist = AdminWhitelist.query.first()
            if not existing_whitelist:
                # Add localhost to admin whitelist for development
                localhost_whitelist = AdminWhitelist(
                    ip_address='127.0.0.1',
                    description='Localhost for development',
                    created_by='system',
                    created_at=datetime.utcnow()
                )
                db.session.add(localhost_whitelist)
                db.session.commit()
                print("Added localhost (127.0.0.1) to admin whitelist for development.")
            
            print("Initial data seeding completed!")
            return True
            
    except ImportError as e:
        print(f"❌ Flask not available: {e}")
        print("Please install Flask dependencies first:")
        print("pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"❌ Error seeding data: {e}")
        return False

def recreate_database():
    """Completely recreate the database from scratch."""
    print("Recreating database from scratch...")
    
    db_path = get_db_path()
    
    # Backup existing database
    backup_path = backup_database()
    
    # Remove existing database
    if db_path.exists():
        db_path.unlink()
        print("Existing database removed.")
    
    # Create new database structure
    if create_database_structure():
        # Seed with initial data
        seed_initial_data()
        print("Database recreation completed!")
        if backup_path:
            print(f"Previous database backed up to: {backup_path}")
        return True
    else:
        print("❌ Database recreation failed!")
        return False

def verify_database():
    """Verify that the database is properly initialized."""
    print("Verifying database...")
    
    db_path = get_db_path()
    if not db_path.exists():
        print("❌ Database file does not exist!")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if all tables exist
        expected_tables = ['user', 'admin_credentials', 'admin_whitelist', 'lesson', 'test', 'grade', 'folder', 'file']
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        missing_tables = [table for table in expected_tables if table not in existing_tables]
        if missing_tables:
            print(f"❌ Missing tables: {missing_tables}")
            conn.close()
            return False
        
        # Check if admin credentials exist
        cursor.execute("SELECT COUNT(*) FROM admin_credentials")
        admin_count = cursor.fetchone()[0]
        if admin_count == 0:
            print("❌ No admin credentials found!")
            conn.close()
            return False
        
        # Check if admin whitelist exists
        cursor.execute("SELECT COUNT(*) FROM admin_whitelist")
        whitelist_count = cursor.fetchone()[0]
        if whitelist_count == 0:
            print("❌ No admin whitelist entries found!")
            conn.close()
            return False
        
        conn.close()
        print("✅ Database verification completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Database verification failed: {e}")
        return False

def show_database_info():
    """Show information about the current database."""
    print("Database Information:")
    print("=" * 50)
    
    db_path = get_db_path()
    
    if db_path.exists():
        size = db_path.stat().st_size
        modified_time = datetime.fromtimestamp(db_path.stat().st_mtime)
        print(f"Database file: {db_path}")
        print(f"Database size: {size:,} bytes ({size/1024/1024:.2f} MB)")
        print(f"Last modified: {modified_time}")
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Get table counts
            tables = ['user', 'lesson', 'test', 'grade']
            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    print(f"{table.capitalize()}: {count}")
                except sqlite3.OperationalError:
                    print(f"{table.capitalize()}: table not found")
            
            conn.close()
            
        except Exception as e:
            print(f"Error reading database info: {e}")
    else:
        print("Database file does not exist.")

def main():
    """Main function to handle command line arguments."""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'recreate':
            recreate_database()
        elif command == 'seed':
            seed_initial_data()
        elif command == 'verify':
            verify_database()
        elif command == 'info':
            show_database_info()
        elif command == 'backup':
            backup_path = backup_database()
            if backup_path:
                print(f"Backup created: {backup_path}")
            else:
                print("No database to backup.")
        else:
            print("Unknown command. Available commands:")
            print("  recreate - Completely recreate the database")
            print("  seed     - Seed initial data only")
            print("  verify   - Verify database integrity")
            print("  info     - Show database information")
            print("  backup   - Create a backup of the database")
    else:
        # Default behavior: create structure and seed data
        print("JustLearnIt Database Initialization")
        print("=" * 40)
        
        # Check if database exists
        db_path = get_db_path()
        if db_path.exists():
            print("Database already exists.")
            response = input("Do you want to recreate it? (y/N): ").lower()
            if response == 'y':
                recreate_database()
            else:
                print("Using existing database.")
                seed_initial_data()
        else:
            print("Creating new database...")
            if create_database_structure():
                seed_initial_data()
        
        # Verify the database
        verify_database()

if __name__ == "__main__":
    main() 