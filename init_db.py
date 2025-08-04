#!/usr/bin/env python3
"""
Simple Database Initialization for JustLearnIt
Deletes current database and creates a fresh one with the same structure.
"""

import os
import sqlite3
from pathlib import Path

def create_database_schema():
    """Create database schema directly using SQL."""
    db_path = Path("storage/storage.db")
    
    # Create storage directory if it doesn't exist
    db_path.parent.mkdir(exist_ok=True)
    
    # Connect to database (this will create it if it doesn't exist)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create tables based on the models
    tables = [
        """
        CREATE TABLE user (
            id INTEGER NOT NULL,
            email VARCHAR(120) NOT NULL,
            password VARCHAR(120) NOT NULL,
            name VARCHAR(120),
            is_admin BOOLEAN,
            user_type VARCHAR(50),
            subject VARCHAR(120),
            is_professor_approved BOOLEAN,
            verification_token VARCHAR(36),
            is_verified BOOLEAN,
            last_login DATETIME,
            session_id VARCHAR(100),
            created_at DATETIME,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            rank INTEGER DEFAULT 0,
            PRIMARY KEY (id),
            UNIQUE (email)
        )
        """,
        
        """
        CREATE TABLE admin_credentials (
            id INTEGER NOT NULL,
            username VARCHAR(255) NOT NULL,
            password VARCHAR(255) NOT NULL,
            timestamp FLOAT NOT NULL,
            created_at DATETIME,
            PRIMARY KEY (id)
        )
        """,
        
        """
        CREATE TABLE admin_whitelist (
            id INTEGER NOT NULL,
            ip_address VARCHAR(45) NOT NULL,
            description VARCHAR(200),
            created_at DATETIME,
            created_by VARCHAR(120) NOT NULL,
            PRIMARY KEY (id),
            UNIQUE (ip_address)
        )
        """,
        
        """
        CREATE TABLE lesson (
            id INTEGER NOT NULL,
            title VARCHAR(200) NOT NULL,
            content TEXT NOT NULL,
            subject VARCHAR(120) NOT NULL,
            author_id INTEGER NOT NULL,
            created_at DATETIME,
            updated_at DATETIME,
            views INTEGER,
            completions INTEGER,
            rating FLOAT,
            PRIMARY KEY (id),
            FOREIGN KEY (author_id) REFERENCES user (id)
        )
        """,
        
        """
        CREATE TABLE test (
            id INTEGER NOT NULL,
            title VARCHAR(200) NOT NULL,
            subject VARCHAR(120) NOT NULL,
            author_id INTEGER NOT NULL,
            created_at DATETIME,
            updated_at DATETIME,
            attempts INTEGER,
            avg_score FLOAT,
            pass_rate FLOAT,
            PRIMARY KEY (id),
            FOREIGN KEY (author_id) REFERENCES user (id)
        )
        """,
        
        """
        CREATE TABLE grade (
            id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            lesson_id INTEGER,
            test_id INTEGER,
            score FLOAT NOT NULL,
            date DATETIME,
            time_spent INTEGER,
            PRIMARY KEY (id),
            FOREIGN KEY (student_id) REFERENCES user (id),
            FOREIGN KEY (lesson_id) REFERENCES lesson (id),
            FOREIGN KEY (test_id) REFERENCES test (id)
        )
        """,
        
        """
        CREATE TABLE folder (
            id INTEGER NOT NULL,
            name VARCHAR(255) NOT NULL,
            path VARCHAR(512) NOT NULL,
            created_at DATETIME,
            parent_id INTEGER,
            PRIMARY KEY (id),
            FOREIGN KEY (parent_id) REFERENCES folder (id)
        )
        """,
        
        """
        CREATE TABLE file (
            id INTEGER NOT NULL,
            filename VARCHAR(255) NOT NULL,
            original_filename VARCHAR(255) NOT NULL,
            file_path VARCHAR(512) NOT NULL,
            file_type VARCHAR(50),
            size INTEGER,
            created_at DATETIME,
            folder_id INTEGER,
            PRIMARY KEY (id),
            FOREIGN KEY (folder_id) REFERENCES folder (id)
        )
        """
    ]
    
    # Execute each table creation
    for table_sql in tables:
        cursor.execute(table_sql)
    
    # Commit changes
    conn.commit()
    conn.close()
    
    return True

def seed_initial_data():
    """Add initial admin credentials and whitelist."""
    import random
    import string
    from datetime import datetime
    
    db_path = Path("storage/storage.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Generate random admin credentials
    letters = string.ascii_letters + string.digits
    username = ''.join(random.choice(letters) for _ in range(12))
    password = ''.join(random.choice(letters) for _ in range(16))
    timestamp = datetime.now().timestamp()
    
    # Insert admin credentials
    cursor.execute("""
        INSERT INTO admin_credentials (username, password, timestamp, created_at)
        VALUES (?, ?, ?, ?)
    """, (username, password, timestamp, datetime.utcnow()))
    
    # Insert admin whitelist for localhost
    cursor.execute("""
        INSERT INTO admin_whitelist (ip_address, description, created_at, created_by)
        VALUES (?, ?, ?, ?)
    """, ('127.0.0.1', 'Localhost for development', datetime.utcnow(), 'system'))
    
    conn.commit()
    conn.close()
    
    print(f"Admin credentials created - Username: {username}, Password: {password}")

def main():
    """Main function."""
    db_path = Path("storage/storage.db")
    
    # Remove existing database if it exists
    if db_path.exists():
        db_path.unlink()
        print("Existing database removed.")
    
    # Create new database schema
    if create_database_schema():
        print("Database schema created.")
        
        # Seed initial data
        seed_initial_data()
        
        print("Database initialized successfully.")
    else:
        print("Failed to initialize database.")
        exit(1)

if __name__ == "__main__":
    main() 