from app import db, app

if __name__ == "__main__":
    print("Creating database tables...")

    with app.app_context():
        db.create_all()
        print("Database tables created successfully!") 