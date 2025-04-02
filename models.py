from app import db
from datetime import datetime
import uuid
from flask_login import UserMixin

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    name = db.Column(db.String(120), nullable=True)
    is_admin = db.Column(db.Boolean, default=False)
    user_type = db.Column(db.String(50), nullable=True)
    subject = db.Column(db.String(120), nullable=True)
    is_professor_approved = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(36), nullable=True)
    is_verified = db.Column(db.Boolean, default=False)
    last_login = db.Column(db.DateTime, nullable=True)

    def generate_verification_token(self):
        """Generate a verification token for the user."""
        self.verification_token = str(uuid.uuid4())
        db.session.commit()

    @property
    def is_active(self):
        """Return True if the user is active (verified)."""
        return self.is_verified

    @property
    def is_authenticated(self):
        """Return True if the user is authenticated."""
        return True

    @property
    def is_anonymous(self):
        """Return False as this is not an anonymous user."""
        return False

    def get_id(self):
        """Return the user ID as a string (required by Flask-Login)."""
        return str(self.id)

    def __repr__(self):
        return f"User('{self.email}', '{self.user_type}', '{self.is_admin}')"