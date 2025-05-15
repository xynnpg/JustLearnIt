import os
import shutil
from app import app
from extensions import db
from models import File, Folder, AdminCredentials

def migrate_storage_data():
    with app.app_context():
        # Create tables if they don't exist
        db.create_all()
        
        # Set correct source paths
        storage_api_db = os.path.join(os.path.dirname(__file__), 'storage', 'storage.db')
        storage_api_storage = os.path.join(os.path.dirname(__file__), 'storage')
        main_storage = os.path.join(os.path.dirname(__file__), 'storage')
        
        # Copy storage files (optional, since you already did it)
        # if os.path.exists(storage_api_storage):
        #     for item in os.listdir(storage_api_storage):
        #         if item != 'storage.db':  # Skip the database file
        #             src = os.path.join(storage_api_storage, item)
        #             dst = os.path.join(main_storage, item)
        #             if os.path.isdir(src):
        #                 shutil.copytree(src, dst)
        #             else:
        #                 shutil.copy2(src, dst)
        
        # Migrate database data
        if os.path.exists(storage_api_db):
            import sqlite3
            
            # Connect to source database
            src_conn = sqlite3.connect(storage_api_db)
            src_cursor = src_conn.cursor()
            
            # Migrate folders
            src_cursor.execute('SELECT * FROM folder')
            folders = src_cursor.fetchall()
            for folder in folders:
                new_folder = Folder(
                    id=folder[0],
                    name=folder[1],
                    path=folder[2],
                    created_at=folder[3],
                    parent_id=folder[4]
                )
                db.session.add(new_folder)
            
            # Migrate files
            src_cursor.execute('SELECT * FROM file')
            files = src_cursor.fetchall()
            for file in files:
                new_file = File(
                    id=file[0],
                    filename=file[1],
                    original_filename=file[2],
                    file_path=file[3],
                    file_type=file[4],
                    size=file[5],
                    created_at=file[6],
                    folder_id=file[7]
                )
                db.session.add(new_file)
            
            # Migrate admin credentials
            src_cursor.execute('SELECT * FROM admin_credentials')
            credentials = src_cursor.fetchall()
            for cred in credentials:
                new_cred = AdminCredentials(
                    id=cred[0],
                    username=cred[1],
                    password=cred[2],
                    timestamp=cred[3],
                    created_at=cred[4]
                )
                db.session.add(new_cred)
            
            # Commit changes
            db.session.commit()
            
            # Close connections
            src_conn.close()

if __name__ == '__main__':
    migrate_storage_data() 