from app import app, db
from models import User, Lesson, Test, Grade

def init_db():
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        print("Database tables created successfully!")

if __name__ == "__main__":
    init_db() 