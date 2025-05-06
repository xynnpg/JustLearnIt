import os
from flask import Flask, url_for, make_response, session, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, current_user
from flask_mail import Mail, Message
from flask_migrate import Migrate
import logging
import time
from datetime import datetime, timedelta
from threading import Thread
import atexit
from dotenv import load_dotenv
import requests
import shutil
from utils import load_credentials, regenerate_credentials

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev')
app.config['PERMANENT_SESSION_LIFETIME'] = 1800
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_REFRESH_EACH_REQUEST'] = True

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'  # Use SQLite database
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login.login'
mail = Mail(app)

# Register blueprints
from LandingPage.routes import landing_bp
from LoginPage.routes import login_bp
from ChoosePage.routes import choose_bp
from AdminPage.routes import admin_bp
from AccountPage.routes import account_bp
from StudioPage.routes import studio_bp
from LearnPage.routes import learn_bp
from AboutPage.routes import about_bp
from RankingPage.routes import ranking_bp

app.register_blueprint(landing_bp)
app.register_blueprint(login_bp)
app.register_blueprint(choose_bp)
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(account_bp)
app.register_blueprint(studio_bp, url_prefix='/studio')
app.register_blueprint(learn_bp)
app.register_blueprint(about_bp)
app.register_blueprint(ranking_bp)

ADMIN_EMAIL = os.getenv('ADMIN_EMAIL')

# Check if admin credentials exist, if not create them
response = requests.head(f"{os.getenv('STORAGE_API_URL', 'http://localhost:5002/api')}/admin/credentials")
if response.status_code == 404:
    with app.app_context():
        regenerate_credentials(db, mail)

def check_and_regenerate():
    while True:
        _, _, last_timestamp = load_credentials()
        if last_timestamp and time.time() - last_timestamp >= 7*86400:
            logger.debug("Regenerating admin credentials (7 days passed)")
            with app.app_context():
                regenerate_credentials(db, mail)
        time.sleep(3600)

thread = Thread(target=check_and_regenerate, daemon=True)
thread.start()
atexit.register(lambda: logger.info("Shutting down credential regeneration thread"))

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

@app.after_request
def add_header(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

@app.route('/test-email')
def test_email():
    if not current_user.is_authenticated or not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        msg = Message("Test Email",
                    recipients=[ADMIN_EMAIL])
        msg.body = "This is a test email from the application."
        mail.send(msg)
        return jsonify({'message': 'Test email sent successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/force-password-change')
def force_password_change():
    if not current_user.is_authenticated or not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 401
    from utils import clear_all_sessions
    clear_all_sessions(db)
    return jsonify({'message': 'All users will be required to change their password on next login'})

@app.route('/force-logout-all')
def force_logout_all():
    if not current_user.is_authenticated or not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 401
    from utils import clear_all_sessions
    clear_all_sessions(db)
    return jsonify({'message': 'All users have been logged out'})

def verify_database():
    try:
        with app.app_context():
            db.engine.connect()
            logger.info("Database connection successful")
            return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False

@atexit.register
def cleanup():
    logger.info("Cleaning up resources")
    try:
        db.session.close()
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response