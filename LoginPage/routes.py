from flask import Blueprint, render_template, request, flash, redirect, url_for, session, make_response
from flask_login import login_user, logout_user, login_required, current_user
from app import db, bcrypt, mail
from models import User
from flask_mail import Message
import requests
import uuid
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

STORAGE_API_URL = os.getenv('STORAGE_API_URL', 'http://localhost:5000/api')

login_bp = Blueprint('login', __name__,
                     template_folder='../Templates',
                     static_folder='../static/login')

ABSTRACT_API_KEY = os.getenv('ABSTRACT_API_KEY')

def verify_email_address(email):
    try:
        url = f"https://emailvalidation.abstractapi.com/v1/?api_key={ABSTRACT_API_KEY}&email={email}"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        is_valid_format = data.get('is_valid_format', {}).get('value', False)
        is_smtp_valid = data.get('is_smtp_valid', {}).get('value', False)
        return is_valid_format and is_smtp_valid
    except requests.RequestException as e:
        print(f"Eroare la verificarea e-mailului: {e}")
        return True

@login_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('account.account'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user and bcrypt.check_password_hash(user.password, password):
            # Generate new session ID
            session_id = str(uuid.uuid4())
            user.session_id = session_id
            db.session.commit()
            
            login_user(user)
            session['user_id'] = user.id
            session['session_id'] = session_id
            session.permanent = True  # Make the session permanent
            
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            # Set a secure cookie to track login state
            response = make_response(redirect(url_for('account.account')))
            response.set_cookie('user_session', session_id, 
                              max_age=30*24*60*60,  # 30 days
                              httponly=True,
                              secure=True,
                              samesite='Lax')
            return response
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('login.html')

@login_bp.route('/signup', methods=['POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')

        if not verify_email_address(email):
            flash('Adresa de e-mail nu este validă sau nu există.', 'error')
            return redirect(url_for('login.login'))

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('E-mailul este deja înregistrat.', 'error')
            return redirect(url_for('login.login'))

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(name=name, email=email, password=hashed_password)
        new_user.generate_verification_token()
        db.session.add(new_user)
        db.session.commit()

        # Create user directory in storage API
        try:
            response = requests.post(f"{STORAGE_API_URL}/folders/users/{email}")
            if response.status_code != 201:
                print(f"Error creating user directory: {response.text}")
        except Exception as e:
            print(f"Error creating user directory: {e}")

        send_verification_email(new_user)

        flash('Cont creat cu succes! Verifică-ți e-mailul pentru a confirma adresa.', 'success')
        return redirect(url_for('login.login'))

@login_bp.route('/verify/<token>')
def verify_email(token):
    user = User.query.filter_by(verification_token=token).first()
    if user:
        user.is_verified = True
        user.verification_token = None
        db.session.commit()
        session['user_id'] = user.id
        session['email'] = user.email
        session.permanent = True
        login_user(user)
        flash('E-mail verificat cu succes! Alege o opțiune.', 'success')
        return redirect(url_for('choose.index'))
    else:
        flash('Link de verificare invalid sau expirat.', 'error')
        return redirect(url_for('login.login'))

@login_bp.route('/logout')
@login_required
def logout():
    # Clear session ID from user record
    current_user.session_id = None
    db.session.commit()
    
    # Clear session data
    session.clear()
    
    # Logout user
    logout_user()
    
    # Create response and clear cookies
    response = make_response(redirect(url_for('login.login')))
    response.delete_cookie('user_session')
    
    return response

def send_verification_email(user):
    token = user.verification_token
    verify_url = url_for('login.verify_email', token=token, _external=True)
    msg = Message('Verifică-ți adresa de e-mail',
                  recipients=[user.email])
    msg.html = f"""
    <h2>Bună {user.name or "Utilizator"},</h2>
    <p>Te rugăm să verifici adresa ta de e-mail făcând clic pe butonul de mai jos:</p>
    <a href="{verify_url}" style="padding: 10px 20px; background: #74ebd5; color: #fff; text-decoration: none; border-radius: 5px;">Verifică E-mail</a>
    <p>Dacă nu ai creat acest cont, ignoră acest mesaj.</p>
    <p>Echipa JustLearnIt</p>
    """
    mail.send(msg)