from app import app, db
from models import User

with app.app_context():
    users = User.query.all()
    print(f"Found {len(users)} total users:")
    for user in users:
        print(f"- {user.name} ({user.email}) - Type: {user.user_type}") 