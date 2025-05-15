import os
import random
import string
import time
from datetime import datetime
import requests
import logging
from flask import current_app
from flask_mail import Message

logger = logging.getLogger(__name__)

def generate_random_credentials():
    letters = string.ascii_letters + string.digits
    username = ''.join(random.choice(letters) for _ in range(12))
    password = ''.join(random.choice(letters) for _ in range(16))
    return username, password

def save_credentials(username, password, timestamp):
    try:
        response = requests.post(
            f"{os.getenv('STORAGE_API_URL', 'http://localhost:5002/api')}/admin/credentials",
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
        response = requests.get(f"{os.getenv('STORAGE_API_URL', 'http://localhost:5002/api')}/admin/credentials")
        if response.status_code == 200:
            data = response.json()
            return data['username'], data['password'], float(data['timestamp'])
        else:
            logger.error(f"Failed to load admin credentials: {response.text}")
    except Exception as e:
        logger.error(f"Error loading admin credentials: {e}")
    return None, None, 0

def send_credentials_email(username, password, mail):
    try:
        msg = Message("New Admin Credentials",
                    recipients=[os.getenv('ADMIN_EMAIL')])
        msg.body = f"Your new admin credentials:\nUsername: {username}\nPassword: {password}\nValid until: {datetime.fromtimestamp(time.time() + 7*86400).strftime('%Y-%m-%d %H:%M:%S')}"
        mail.send(msg)
        logger.info(f"Admin credentials sent to {os.getenv('ADMIN_EMAIL')}: {username}/{password}")
    except Exception as e:
        logger.error(f"Failed to send admin credentials email: {str(e)}")

def send_login_notification(username, ip_address, mail):
    try:
        msg = Message("Admin Login Notification",
                    recipients=[os.getenv('ADMIN_EMAIL')])
        msg.body = f"Admin login detected:\nUsername: {username}\nIP Address: {ip_address}\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        mail.send(msg)
        logger.info(f"Admin login notification sent to {os.getenv('ADMIN_EMAIL')}")
    except Exception as e:
        logger.error(f"Failed to send admin login notification: {str(e)}")

def clear_all_sessions(db):
    try:
        from models import User
        users = User.query.all()
        for user in users:
            user.session_id = None
        db.session.commit()
        logger.info("All user sessions cleared successfully")
    except Exception as e:
        logger.error(f"Failed to clear user sessions: {str(e)}")

def regenerate_credentials(db, mail):
    username, password = generate_random_credentials()
    timestamp = time.time()
    if save_credentials(username, password, timestamp):
        send_credentials_email(username, password, mail)
        clear_all_sessions(db)
        return username, password, timestamp
    return None, None, 0 