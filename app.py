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
import requests

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_REFRESH_EACH_REQUEST'] = True

STORAGE_API_URL = os.getenv('STORAGE_API_URL', 'http://localhost:5000/api')

# Configure SQLAlchemy to use storage.db database
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:////home/xympg/Desktop/Github/storage_api_website/storage/storage.db')
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

ADMIN_EMAIL = os.getenv('ADMIN_EMAIL')

def generate_random_credentials():
    letters = string.ascii_letters + string.digits
    username = ''.join(random.choice(letters) for _ in range(12))
    password = ''.join(random.choice(letters) for _ in range(16))
    return username, password

def save_credentials(username, password, timestamp):
    try:
        response = requests.post(
            f"{STORAGE_API_URL}/admin/credentials",
            json={
                'username': username,
                'password': password,
                'timestamp': timestamp
            }
        )
        if response.status_code != 201:
            logger.error(f"Failed to save admin credentials: {response.text}")
            return False
        return True
    except Exception as e:
        logger.error(f"Error saving admin credentials: {e}")
        return False

def load_credentials():
    try:
        response = requests.get(f"{STORAGE_API_URL}/admin/credentials")
        if response.status_code == 200:
            data = response.json()
            return data['username'], data['password'], float(data['timestamp'])
        else:
            logger.error(f"Failed to load admin credentials: {response.text}")
    except Exception as e:
        logger.error(f"Error loading admin credentials: {e}")
    return None, None, 0

def send_credentials_email(username, password):
    try:
        with app.app_context():
            msg = Message("New Admin Credentials",
                        recipients=[ADMIN_EMAIL])
            msg.body = f"Your new admin credentials:\nUsername: {username}\nPassword: {password}\nValid until: {datetime.fromtimestamp(time.time() + 7*86400).strftime('%Y-%m-%d %H:%M:%S')}"
            mail.send(msg)
            logger.info(f"Admin credentials sent to {ADMIN_EMAIL}: {username}/{password}")
    except Exception as e:
        logger.error(f"Failed to send admin credentials email: {str(e)}")

def send_login_notification(username, ip_address):
    try:
        with app.app_context():
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
    if save_credentials(username, password, timestamp):
        send_credentials_email(username, password)
        clear_all_sessions()
        return username, password, timestamp
    return None, None, 0

# Check if admin credentials exist, if not create them
response = requests.head(f"{STORAGE_API_URL}/admin/credentials")
if response.status_code == 404:
    with app.app_context():
        regenerate_credentials()

def check_and_regenerate():
    while True:
        _, _, last_timestamp = load_credentials()
        if last_timestamp and time.time() - last_timestamp >= 7*86400:
            logger.debug("Regenerating admin credentials (7 days passed)")
            with app.app_context():
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
    if username and password:
        return f"Password changed successfully! New credentials sent to {ADMIN_EMAIL}. Username: {username}, Password: {password}"
    return "Failed to change password. Check logs for details."

@app.route('/force-logout-all')
def force_logout_all():
    """Force logout all users"""
    clear_all_sessions()
    return "All users have been logged out successfully"