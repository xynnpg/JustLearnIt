import os
from flask import Flask, url_for, make_response, session, request
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, current_user
from flask_mail import Mail, Message
from flask_migrate import Migrate
import logging
import random
import string
import time
from datetime import datetime, timedelta
from threading import Thread
import atexit
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['PERMANENT_SESSION_LIFETIME'] = 3600

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, 'instance')
os.makedirs(INSTANCE_DIR, exist_ok=True)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(INSTANCE_DIR, "site.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')
app.config['MAIL_DEBUG'] = True
app.config['MAIL_SUPPRESS_SEND'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login.login'
mail = Mail(app)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

CREDENTIALS_FILE = os.path.join(INSTANCE_DIR, 'admin_credentials.txt')
ADMIN_EMAIL = os.getenv('ADMIN_EMAIL')

def generate_random_credentials():
    letters = string.ascii_letters + string.digits
    username = ''.join(random.choice(letters) for _ in range(12))
    password = ''.join(random.choice(letters) for _ in range(16))
    return username, password

def save_credentials(username, password, timestamp):
    with open(CREDENTIALS_FILE, 'w') as f:
        f.write(f"{username}:{password}:{timestamp}")

def load_credentials():
    try:
        with open(CREDENTIALS_FILE, 'r') as f:
            data = f.read().strip().split(':')
            if len(data) == 3:
                return data[0], data[1], float(data[2])
    except FileNotFoundError:
        pass
    return None, None, 0

def send_credentials_email(username, password):
    try:
        msg = Message("New Admin Credentials",
                     recipients=[ADMIN_EMAIL])
        msg.body = f"Your new admin credentials:\nUsername: {username}\nPassword: {password}\nValid until: {datetime.fromtimestamp(time.time() + 7*86400).strftime('%Y-%m-%d %H:%M:%S')}"
        mail.send(msg)
        logger.info(f"Admin credentials sent to {ADMIN_EMAIL}: {username}/{password}")
    except Exception as e:
        logger.error(f"Failed to send admin credentials email: {str(e)}")

def send_login_notification(username, ip_address):
    try:
        msg = Message("Admin Login Notification",
                     recipients=[ADMIN_EMAIL])
        msg.body = f"Admin login detected:\nUsername: {username}\nIP Address: {ip_address}\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        mail.send(msg)
        logger.info(f"Admin login notification sent to {ADMIN_EMAIL}")
    except Exception as e:
        logger.error(f"Failed to send admin login notification: {str(e)}")

def clear_all_sessions():
    try:
        from models import User
        users = User.query.all()
        for user in users:
            user.session_id = None
        db.session.commit()
        logger.info("All user sessions cleared successfully")
    except Exception as e:
        logger.error(f"Failed to clear user sessions: {str(e)}")

def regenerate_credentials():
    username, password = generate_random_credentials()
    timestamp = time.time()
    save_credentials(username, password, timestamp)
    send_credentials_email(username, password)
    clear_all_sessions()
    return username, password, timestamp

if not os.path.exists(CREDENTIALS_FILE):
    regenerate_credentials()

def check_and_regenerate():
    while True:
        _, _, last_timestamp = load_credentials()

        if time.time() - last_timestamp >= 7*86400:
            logger.debug("Regenerating admin credentials (7 days passed)")
            regenerate_credentials()
        time.sleep(3600)

thread = Thread(target=check_and_regenerate, daemon=True)
thread.start()
atexit.register(lambda: logger.info("Shutting down credential regeneration thread"))

from LandingPage.routes import landing_bp
from LoginPage.routes import login_bp
from ChoosePage.routes import choose_bp
from AdminPage.routes import admin_bp
from AccountPage.routes import account_bp
from StudioPage import studio_bp
from LearnPage.routes import learn_bp
from AboutPage.routes import about_bp

app.register_blueprint(landing_bp)
app.register_blueprint(login_bp)
app.register_blueprint(choose_bp)
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(account_bp)
app.register_blueprint(studio_bp, url_prefix='/studio')
app.register_blueprint(learn_bp)
app.register_blueprint(about_bp)

from models import User

@login_manager.user_loader
def load_user(user_id):
    user = User.query.get(int(user_id))
    if user and 'user_id' in session:
        user.last_login = datetime.utcnow()
        db.session.commit()
    return user

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    
    # Check if this is a response from the email verification endpoint
    if request.endpoint == 'login.verify_email':
        response.set_cookie('logged_in', 'false', max_age=3600, httponly=True)
    elif 'user_id' in session:
        response.set_cookie('logged_in', 'true', max_age=3600, httponly=True)
    else:
        response.set_cookie('logged_in', 'false', max_age=3600, httponly=True)
    return response

@app.route('/test-email')
def test_email():
    try:
        msg = Message("Test Email from JustLearnIt",
                     recipients=[ADMIN_EMAIL])
        msg.body = "This is a test email to verify SMTP settings."
        mail.send(msg)
        logger.info(f"Test email sent successfully to {ADMIN_EMAIL}")
        return f"Test email sent! Check {ADMIN_EMAIL}."
    except Exception as e:
        logger.error(f"Failed to send test email: {str(e)}")
        return f"Error sending test email: {str(e)}"

@app.route('/force-password-change')
def force_password_change():
    """Force a password change and send the new credentials via email"""
    username, password, timestamp = regenerate_credentials()
    return f"Password changed successfully! New credentials sent to {ADMIN_EMAIL}. Username: {username}, Password: {password}"

@app.route('/force-logout-all')
def force_logout_all():
    """Force logout all users"""
    clear_all_sessions()
    return "All users have been logged out successfully"