from app import db, app
import os

if __name__ == "__main__":
    print("Creating database tables...")

    # Ensure the instance directory exists and has correct permissions
    instance_dir = os.path.join(os.path.dirname(__file__), 'instance')
    os.makedirs(instance_dir, exist_ok=True)
    os.chmod(instance_dir, 0o777)

    # Create the database file with correct permissions
    db_path = os.path.join(instance_dir, 'site.db')
    if not os.path.exists(db_path):
        open(db_path, 'a').close()
    os.chmod(db_path, 0o666)

    with app.app_context():
        db.create_all()
        print("Database tables created successfully!") 