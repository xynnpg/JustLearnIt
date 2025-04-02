from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app import db, logger, bcrypt, regenerate_credentials, load_credentials
from models import User
from datetime import datetime

admin_bp = Blueprint('admin', __name__,
                     template_folder='../Templates',
                     static_folder='../static/admin')

ADMIN_SESSION_KEY = 'admin_logged_in'


def is_admin_logged_in():
    return session.get(ADMIN_SESSION_KEY, False)


@admin_bp.route('/login', methods=['GET', 'POST'])
def admin_login():
    if is_admin_logged_in():
        logger.debug("Already logged in, redirecting to admin panel")
        return redirect(url_for('admin.admin_panel'))

    logger.debug("Entering admin_login route")

    if request.method == 'POST':
        input_username = request.form.get('username')
        input_password = request.form.get('password')

        logger.debug(f"Admin login attempt with username: {input_username}")

        stored_username, stored_password, timestamp = load_credentials()
        if stored_username and stored_password:
            if input_username == stored_username and input_password == stored_password:
                logger.info(f"Admin login successful for {input_username}")
                session[ADMIN_SESSION_KEY] = True
                flash('Admin access granted.', 'info')
                return redirect(url_for('admin.admin_panel'))
            else:
                logger.debug(f"Admin login failed: Invalid credentials for {input_username}")
                flash('Invalid username or password.', 'error')
        else:
            logger.error("No admin credentials found in file")
            flash('Admin credentials not initialized.', 'error')

    return render_template('admin_login.html')


@admin_bp.route('/', methods=['GET', 'POST'])
def admin_panel():
    if not is_admin_logged_in():
        logger.debug("Not logged in, redirecting to admin login")
        return redirect(url_for('admin.admin_login'))

    if request.method == 'POST':
        user_id = request.form.get('user_id')
        action = request.form.get('action')
        user = User.query.get(user_id)

        if user and user.user_type == 'profesor':
            if action == 'approve':
                user.is_professor_approved = True
                db.session.commit()
                logger.info(f"Approved professor: {user.email}")
                flash(f"Professor {user.email} approved.", 'success')
            elif action == 'decline':
                user.user_type = None
                user.subject = None
                user.is_professor_approved = False
                db.session.commit()
                logger.info(f"Declined professor: {user.email}")
                flash(f"Professor {user.email} declined.", 'success')
            else:
                flash('Invalid action.', 'error')
        else:
            flash('User not found or not a professor.', 'error')

    professors = User.query.filter_by(user_type='profesor').all()
    students = User.query.filter_by(user_type='elev').all()
    return render_template('admin.html', professors=professors, students=students)


@admin_bp.route('/logout')
def admin_logout():
    session.pop(ADMIN_SESSION_KEY, None)
    logger.info("Admin logged out")
    flash('You have been logged out.', 'success')
    return redirect(url_for('admin.admin_login'))