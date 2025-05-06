import os
from flask import Flask, url_for, make_response, session, request, jsonify
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
import shutil
from api_dialect import APIDialect
from api_pool import APIPool
from api_events import setup_api_events
from api_session import APISession
from api_mapper import APIMapper
from api_base import APIDeclarativeBase
from api_engine import APIEngine
from sqlalchemy.dialects import registry
from sqlalchemy.orm import sessionmaker
from sqlalchemy import event
from api_query import APIQuery
from api_result import APIResultProxy
from api_transaction import APITransaction
from api_connection import APIConnection
from api_cursor import APICursor
from api_compiler import APICompiler
from api_type_compiler import APITypeCompiler
from api_ddl_compiler import APIDDLCompiler
from api_schema_compiler import APISchemaGenerator, APISchemaDropper
from api_inspector import APIInspector
from api_url import APIURL
from sqlalchemy.pool import Pool

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

STORAGE_API_URL = os.getenv('STORAGE_API_URL', 'http://localhost:5002/api')

# Create custom URL
api_url = APIURL.create(f"api://{STORAGE_API_URL}")

# Initialize the API engine
api_engine = APIEngine(api_url=api_url.api_url)

# Register the custom dialect before creating SQLAlchemy instance
registry.register("api", "api_dialect", "APIDialect")

# Create a minimal pool class
class CustomAPIPool(Pool):
    def __init__(self, creator, api_url=None, **kw):
        logger.debug("Initializing CustomAPIPool")
        self.api_url = api_url
        # Pass only the creator to the parent class
        super().__init__(creator)
        logger.debug("CustomAPIPool initialized")

    def connect(self):
        return self._creator()

    def recreate(self):
        return CustomAPIPool(self._creator, api_url=self.api_url)

    def dispose(self):
        pass

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = f"api://localhost:5002/api"

# Configure engine options - minimal configuration
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'api_url': api_url.api_url,
    'echo': True  # Enable SQL logging for debugging
}

# Initialize extensions
db = SQLAlchemy(app, query_class=APIQuery)
migrate = Migrate(app, db)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login.login'
mail = Mail(app)

def init_app(app):
    """Initialize the application with the given Flask app."""
    with app.app_context():
        # Create and configure the engine
        engine = db.engine

        # Create and configure the dialect
        dialect = APIDialect()
        dialect.result_proxy_class = APIResultProxy
        dialect.transaction_class = APITransaction
        dialect.connection_class = APIConnection
        dialect.cursor_class = APICursor
        dialect.compiler_class = APICompiler
        dialect.type_compiler_class = APITypeCompiler
        dialect.ddl_compiler_class = APIDDLCompiler
        dialect.schema_generator_class = APISchemaGenerator
        dialect.schema_dropper_class = APISchemaDropper
        dialect.inspector_class = APIInspector
        dialect.url_class = APIURL

        # Set the dialect on the engine
        engine.dialect = dialect

        # Now setup API events after engine and dialect are configured
        setup_api_events(engine, api_url.api_url)

        # Create a custom session factory
        Session = sessionmaker(
            bind=engine,
            class_=APISession,
            query_cls=APIQuery,
            api_url=api_url.api_url
        )

        # Override the default session
        db.session = Session()

        # Create a custom mapper factory
        def create_mapper(*args, **kwargs):
            kwargs['api_url'] = api_url.api_url
            return APIMapper(*args, **kwargs)

        # Set the mapper factory on the Model class
        db.Model._mapper_factory = create_mapper

# Initialize the application
init_app(app)

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
from RankingPage import ranking_bp

app.register_blueprint(landing_bp)
app.register_blueprint(login_bp)
app.register_blueprint(choose_bp)
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(account_bp)
app.register_blueprint(studio_bp, url_prefix='/studio')
app.register_blueprint(learn_bp)
app.register_blueprint(about_bp)
app.register_blueprint(ranking_bp)

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
        
        # Add XP for correct answers - only for students
        if request.endpoint == 'learn.submit_answer' and response.status_code == 200 and current_user.user_type == 'elev':
            try:
                current_user.add_xp(5)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                print(f"Error adding XP: {e}")
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

def verify_database():
    try:
        response = requests.get(f"{STORAGE_API_URL}/database")
        if response.status_code == 200:
            print("Cloud database is accessible")
            return True
        else:
            print(f"Failed to access cloud database. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"Error verifying cloud database: {e}")
        return False

# Verify database access
if not verify_database():
    raise Exception("Could not access cloud database")

# Cleanup on application shutdown
@atexit.register
def cleanup():
    pass

# Remove sync function since we're using the database directly
@app.after_request
def after_request(response):
    return response

# Create custom declarative base
Base = APIDeclarativeBase(api_url=api_url.api_url)

# Import models after Base is created
from models import *

# Create tables
Base.metadata.create_all(api_engine)

# Import routes after models are created
from routes import *

if __name__ == '__main__':
    app.run(debug=True)