from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from flask_login import login_user, logout_user, login_required, current_user
from app import db, bcrypt, mail
from models import User
from flask_mail import Message
import requests

login_bp = Blueprint('login', __name__,
                     template_folder='../Templates',
                     static_folder='../static/login')

ABSTRACT_API_KEY = 'your-abstract-api-key'

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
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()

        if user and bcrypt.check_password_hash(user.password, password):
            if user.is_verified:
                login_user(user)
                session['user_id'] = user.id
                session['email'] = email
                session.permanent = True
                flash('Autentificare reușită!', 'success')
                return redirect(url_for('choose.index'))
            else:
                flash('Te rugăm să verifici adresa de e-mail mai întâi.', 'error')
        else:
            flash('Autentificare eșuată. Verifică e-mailul și parola.', 'error')

    return render_template('login.html', template='base_login.html')

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
    logout_user()
    session.pop('user_id', None)
    session.pop('email', None)
    flash('Ai fost deconectat.', 'success')
    return redirect(url_for('login.login'))

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