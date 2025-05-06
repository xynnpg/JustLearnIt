from app import db
from datetime import datetime
import uuid
from flask_login import UserMixin
from api_base import Base
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Float
from sqlalchemy.orm import relationship

class User(Base, UserMixin):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    name = Column(String(120), nullable=True)
    is_admin = Column(Boolean, default=False)
    user_type = Column(String(50), nullable=True)
    subject = Column(String(120), nullable=True)
    is_professor_approved = Column(Boolean, default=False)
    verification_token = Column(String(36), nullable=True)
    is_verified = Column(Boolean, default=False)
    last_login = Column(DateTime, nullable=True)
    session_id = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    xp = Column(Integer, default=0)
    level = Column(Integer, default=1)
    rank = Column(Integer, default=0)

    # Relationships
    lessons = relationship('Lesson', backref='author', lazy=True)
    tests = relationship('Test', backref='author', lazy=True)
    grades = relationship('Grade', backref='student', lazy=True)

    def __init__(self, username, email, password_hash):
        self.username = username
        self.email = email
        self.password_hash = password_hash

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'name': self.name,
            'is_admin': self.is_admin,
            'user_type': self.user_type,
            'subject': self.subject,
            'is_professor_approved': self.is_professor_approved,
            'is_verified': self.is_verified,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'xp': self.xp,
            'level': self.level,
            'rank': self.rank
        }

    def generate_verification_token(self):
        """Generate a verification token for the user."""
        self.verification_token = str(uuid.uuid4())
        return self.verification_token

    def verify(self):
        """Mark the user as verified."""
        self.is_verified = True
        self.verification_token = None

    def update_last_login(self):
        """Update the user's last login timestamp."""
        self.last_login = datetime.utcnow()

    def add_xp(self, amount):
        """Add XP to the user and update level if necessary."""
        self.xp += amount
        self.level = (self.xp // 100) + 1  # Level up every 100 XP

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

    def add_xp(self, amount=5):
        """Add XP to the user and check for level up - only for students"""
        if self.user_type == 'elev':
            self.xp += amount
            self.check_level_up()
            db.session.commit()

    def check_level_up(self):
        """Check if user has enough XP to level up"""
        if self.user_type == 'elev':
            while self.xp >= self.xp_needed_for_next_level():
                self.xp -= self.xp_needed_for_next_level()
                self.level += 1

    def xp_needed_for_next_level(self):
        """Calculate XP needed for next level using the formula: 50 * level * 0.5"""
        if self.user_type == 'elev':
            return int(50 * self.level * 0.5)
        return 0

    def get_rank(self):
        """Get user's rank based on XP - only for students"""
        if self.user_type == 'elev':
            users = User.query.filter_by(user_type='elev').order_by(User.xp.desc()).all()
            for i, user in enumerate(users, 1):
                if user.id == self.id:
                    return i
        return 0

class Lesson(Base):
    __tablename__ = 'lessons'

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    author_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    subject = Column(String(120), nullable=False)
    difficulty = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_published = Column(Boolean, default=False)
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)

    # Relationships
    tests = relationship('Test', backref='lesson', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'author_id': self.author_id,
            'subject': self.subject,
            'difficulty': self.difficulty,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_published': self.is_published,
            'views': self.views,
            'likes': self.likes
        }

class Test(Base):
    __tablename__ = 'tests'

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    lesson_id = Column(Integer, ForeignKey('lessons.id'), nullable=False)
    author_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_published = Column(Boolean, default=False)
    time_limit = Column(Integer, nullable=True)  # Time limit in minutes
    passing_score = Column(Float, nullable=False)

    # Relationships
    grades = relationship('Grade', backref='test', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'lesson_id': self.lesson_id,
            'author_id': self.author_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_published': self.is_published,
            'time_limit': self.time_limit,
            'passing_score': self.passing_score
        }

class Grade(Base):
    __tablename__ = 'grades'

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    test_id = Column(Integer, ForeignKey('tests.id'), nullable=False)
    score = Column(Float, nullable=False)
    max_score = Column(Float, nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    is_passed = Column(Boolean, default=False)

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'test_id': self.test_id,
            'score': self.score,
            'max_score': self.max_score,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'is_passed': self.is_passed
        }

class AdminWhitelist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(45), unique=True, nullable=False)  # IPv6 addresses can be up to 45 chars
    description = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(120), nullable=False)  # Email of admin who added it

    def __repr__(self):
        return f"AdminWhitelist('{self.ip_address}', '{self.description}')"