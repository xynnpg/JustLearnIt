#!/usr/bin/env python3
"""
Database Backup and Restoration Utility for JustLearnIt
This script handles database backup, restoration, and data export/import.
"""

import os
import sys
import shutil
import sqlite3
import json
from datetime import datetime
from pathlib import Path

def backup_database():
    """Create a timestamped backup of the database."""
    db_path = Path("storage/storage.db")
    if not db_path.exists():
        print("❌ Database file not found!")
        return None
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = db_path.parent / f"storage.db.backup.{timestamp}"
    
    try:
        shutil.copy2(db_path, backup_path)
        print(f"✅ Database backed up to: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return None

def restore_database(backup_path):
    """Restore database from a backup file."""
    db_path = Path("storage/storage.db")
    backup_path = Path(backup_path)
    
    if not backup_path.exists():
        print(f"❌ Backup file not found: {backup_path}")
        return False
    
    try:
        # Create backup of current database if it exists
        if db_path.exists():
            current_backup = backup_database()
            print(f"Current database backed up to: {current_backup}")
        
        # Restore from backup
        shutil.copy2(backup_path, db_path)
        print(f"✅ Database restored from: {backup_path}")
        return True
    except Exception as e:
        print(f"❌ Restoration failed: {e}")
        return False

def export_data():
    """Export database data to JSON files."""
    db_path = Path("storage/storage.db")
    if not db_path.exists():
        print("❌ Database file not found!")
        return False
    
    export_dir = Path("storage/exports")
    export_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    export_path = export_dir / f"data_export_{timestamp}"
    export_path.mkdir(exist_ok=True)
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        for table in tables:
            # Get table schema
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [row[1] for row in cursor.fetchall()]
            
            # Get table data
            cursor.execute(f"SELECT * FROM {table}")
            rows = cursor.fetchall()
            
            # Convert to list of dictionaries
            data = []
            for row in rows:
                row_dict = {}
                for i, column in enumerate(columns):
                    # Handle datetime objects
                    if isinstance(row[i], str) and 'T' in str(row[i]):
                        try:
                            row_dict[column] = row[i]
                        except:
                            row_dict[column] = str(row[i])
                    else:
                        row_dict[column] = row[i]
                data.append(row_dict)
            
            # Save to JSON file
            table_file = export_path / f"{table}.json"
            with open(table_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            
            print(f"✅ Exported {len(data)} rows from table '{table}'")
        
        conn.close()
        
        # Create export info file
        info_file = export_path / "export_info.json"
        info = {
            "export_date": datetime.now().isoformat(),
            "tables": tables,
            "database_path": str(db_path),
            "total_tables": len(tables)
        }
        
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(info, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Data export completed: {export_path}")
        return True
        
    except Exception as e:
        print(f"❌ Export failed: {e}")
        return False

def import_data(export_path):
    """Import data from JSON export files."""
    export_path = Path(export_path)
    if not export_path.exists():
        print(f"❌ Export directory not found: {export_path}")
        return False
    
    db_path = Path("storage/storage.db")
    if not db_path.exists():
        print("❌ Database file not found! Please run init_db.py first.")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Read export info
        info_file = export_path / "export_info.json"
        if info_file.exists():
            with open(info_file, 'r', encoding='utf-8') as f:
                info = json.load(f)
            print(f"Importing data from export dated: {info.get('export_date', 'Unknown')}")
        
        # Import each table
        json_files = list(export_path.glob("*.json"))
        json_files = [f for f in json_files if f.name != "export_info.json"]
        
        for json_file in json_files:
            table_name = json_file.stem
            
            # Check if table exists
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
            if not cursor.fetchone():
                print(f"⚠️  Table '{table_name}' does not exist, skipping...")
                continue
            
            # Read data from JSON
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not data:
                print(f"⚠️  No data in {json_file.name}")
                continue
            
            # Get table columns
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [row[1] for row in cursor.fetchall()]
            
            # Clear existing data
            cursor.execute(f"DELETE FROM {table_name}")
            
            # Insert data
            for row in data:
                values = []
                placeholders = []
                
                for column in columns:
                    if column in row:
                        values.append(row[column])
                        placeholders.append('?')
                    else:
                        values.append(None)
                        placeholders.append('?')
                
                query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
                cursor.execute(query, values)
            
            print(f"✅ Imported {len(data)} rows into table '{table_name}'")
        
        conn.commit()
        conn.close()
        
        print("✅ Data import completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def list_backups():
    """List all available database backups."""
    storage_dir = Path("storage")
    if not storage_dir.exists():
        print("❌ Storage directory not found!")
        return
    
    backup_files = list(storage_dir.glob("storage.db.backup.*"))
    
    if not backup_files:
        print("No backup files found.")
        return
    
    print("Available backups:")
    print("=" * 50)
    
    for backup_file in sorted(backup_files, reverse=True):
        stat = backup_file.stat()
        size = stat.st_size
        modified = datetime.fromtimestamp(stat.st_mtime)
        
        print(f"📁 {backup_file.name}")
        print(f"   Size: {size:,} bytes ({size/1024/1024:.2f} MB)")
        print(f"   Modified: {modified}")
        print()

def list_exports():
    """List all available data exports."""
    export_dir = Path("storage/exports")
    if not export_dir.exists():
        print("❌ Exports directory not found!")
        return
    
    export_dirs = [d for d in export_dir.iterdir() if d.is_dir()]
    
    if not export_dirs:
        print("No export directories found.")
        return
    
    print("Available exports:")
    print("=" * 50)
    
    for export_dir in sorted(export_dirs, reverse=True):
        stat = export_dir.stat()
        modified = datetime.fromtimestamp(stat.st_mtime)
        
        # Count JSON files
        json_files = list(export_dir.glob("*.json"))
        table_count = len([f for f in json_files if f.name != "export_info.json"])
        
        print(f"📁 {export_dir.name}")
        print(f"   Tables: {table_count}")
        print(f"   Modified: {modified}")
        print()

def main():
    """Main function to handle command line arguments."""
    if len(sys.argv) < 2:
        print("Database Backup and Restoration Utility")
        print("=" * 40)
        print("Available commands:")
        print("  backup          - Create a database backup")
        print("  restore <file>  - Restore database from backup")
        print("  export          - Export data to JSON files")
        print("  import <dir>    - Import data from JSON export")
        print("  list-backups    - List available backups")
        print("  list-exports    - List available exports")
        return
    
    command = sys.argv[1].lower()
    
    if command == 'backup':
        backup_database()
    elif command == 'restore':
        if len(sys.argv) < 3:
            print("❌ Please specify backup file path")
            return
        restore_database(sys.argv[2])
    elif command == 'export':
        export_data()
    elif command == 'import':
        if len(sys.argv) < 3:
            print("❌ Please specify export directory path")
            return
        import_data(sys.argv[2])
    elif command == 'list-backups':
        list_backups()
    elif command == 'list-exports':
        list_exports()
    else:
        print(f"❌ Unknown command: {command}")

if __name__ == "__main__":
    main() 