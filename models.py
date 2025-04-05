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
    session_id = db.Column(db.String(100))  # Track active session
    
    # Relationships
    lessons = db.relationship('Lesson', backref='author', lazy=True)
    tests = db.relationship('Test', backref='author', lazy=True)
    grades = db.relationship('Grade', backref='student', lazy=True)

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


class Lesson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    subject = db.Column(db.String(120), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    views = db.Column(db.Integer, default=0)
    completions = db.Column(db.Integer, default=0)
    rating = db.Column(db.Float, default=0.0)
    
    # Relationships
    grades = db.relationship('Grade', backref='lesson', lazy=True)

    def __repr__(self):
        return f"Lesson('{self.title}', '{self.subject}')"


class Test(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    subject = db.Column(db.String(120), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    attempts = db.Column(db.Integer, default=0)
    avg_score = db.Column(db.Float, default=0.0)
    pass_rate = db.Column(db.Float, default=0.0)
    
    # Relationships
    grades = db.relationship('Grade', backref='test', lazy=True)

    def __repr__(self):
        return f"Test('{self.title}', '{self.subject}')"


class Grade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lesson.id'), nullable=True)
    test_id = db.Column(db.Integer, db.ForeignKey('test.id'), nullable=True)
    score = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    time_spent = db.Column(db.Integer, default=0)  # in minutes
    
    @property
    def item_title(self):
        """Return the title of the lesson or test this grade is for"""
        if self.lesson:
            return self.lesson.title
        elif self.test:
            return self.test.title
        return "Unknown"
    
    @property
    def subject(self):
        """Return the subject of the lesson or test this grade is for"""
        if self.lesson:
            return self.lesson.subject
        elif self.test:
            return self.test.subject
        return "Unknown"

    def __repr__(self):
        return f"Grade('{self.student_id}', '{self.score}')"