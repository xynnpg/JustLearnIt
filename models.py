from extensions import db
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
    session_id = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    xp = db.Column(db.Integer, default=0)
    level = db.Column(db.Integer, default=1)
    rank = db.Column(db.Integer, default=0)

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

    def xp_for_current_level(self):
        """Return the total XP required to reach the current level (not the next level)."""
        if self.user_type == 'elev':
            xp = 0
            for lvl in range(1, self.level):
                xp += int(50 * lvl * 0.5)
            return xp
        return 0

    def get_current_level_xp(self):
        """Return the XP earned in the current level."""
        if self.user_type == 'elev':
            total_xp_for_current_level = self.xp_for_current_level()
            xp_in_current_level = self.xp - total_xp_for_current_level
            return xp_in_current_level
        return 0

    def get_progress_percentage(self):
        """Calculate the progress percentage between current level and next level."""
        if self.user_type == 'elev':
            xp_needed = self.xp_needed_for_next_level()
            current_level_xp = self.get_current_level_xp()
            if xp_needed <= 0:
                return 100
            progress = (current_level_xp / xp_needed) * 100
            return min(max(progress, 0), 100)  # Ensure progress is between 0 and 100
        return 0

    def get_rank(self):
        """Get user's rank based on XP - only for students"""
        if self.user_type == 'elev':
            users = User.query.filter_by(user_type='elev').order_by(User.xp.desc()).all()
            for i, user in enumerate(users, 1):
                if user.id == self.id:
                    return i
        return 0

    @property
    def lessons_completed(self):
        """Return the number of lessons completed by the student (based on grades with lesson_id)."""
        if self.user_type == 'elev':
            return len([g for g in self.grades if g.lesson_id is not None])
        return 0

    @property
    def tests_taken(self):
        """Return the number of tests taken by the student (based on grades with test_id)."""
        if self.user_type == 'elev':
            return len([g for g in self.grades if g.test_id is not None])
        return 0

    @property
    def lessons_created(self):
        """Return the number of lessons created by the professor."""
        if self.user_type == 'profesor':
            return len(self.lessons)
        return 0

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
    time_spent = db.Column(db.Integer, default=0)

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

class AdminWhitelist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(45), unique=True, nullable=False)  # IPv6 addresses can be up to 45 chars
    description = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(120), nullable=False)  # Email of admin who added it

    def __repr__(self):
        return f"AdminWhitelist('{self.ip_address}', '{self.description}')"

# Storage Models
class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(512), nullable=False)
    file_type = db.Column(db.String(50))
    size = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    folder_id = db.Column(db.Integer, db.ForeignKey('folder.id'), nullable=True)

class Folder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    path = db.Column(db.String(512), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    parent_id = db.Column(db.Integer, db.ForeignKey('folder.id'), nullable=True)
    files = db.relationship('File', backref='folder', lazy=True)

class AdminCredentials(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)