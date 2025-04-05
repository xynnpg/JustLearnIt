# File: /AdminPage/routes.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import current_user
from app import db, logger, bcrypt, regenerate_credentials, load_credentials, send_login_notification
from models import User, Lesson, Test, Grade
from datetime import datetime, timedelta
import os
import json
import requests
from sqlalchemy import func, desc
from datetime import datetime, timedelta

admin_bp = Blueprint('admin', __name__,
                     template_folder='../Templates',
                     static_folder='../static/admin')

ADMIN_SESSION_KEY = 'admin_logged_in'


def is_admin_logged_in():
    return session.get(ADMIN_SESSION_KEY, False)


def get_user_activity_stats():
    """Get user activity statistics"""
    # Get active users count per day
    active_users = db.session.query(
        func.date(User.last_login).label('date'),
        func.count(User.id).label('count')
    ).filter(
        User.last_login > (datetime.utcnow() - timedelta(days=7))
    ).group_by(
        func.date(User.last_login)
    ).all()

    # Convert to dictionary format
    active_users_dict = {str(date): count for date, count in active_users}

    # Get user types count
    user_types = db.session.query(
        User.user_type,
        func.count(User.id)
    ).group_by(
        User.user_type
    ).all()

    # Convert to dictionary format
    user_types_dict = dict(user_types)

    return {
        'active_users': active_users_dict,
        'user_types': user_types_dict
    }


def get_country_from_ip(ip):
    try:
        response = requests.get(f"http://ip-api.com/json/{ip}?fields=country")
        if response.status_code == 200:
            return response.json().get('country', 'Unknown')
    except:
        pass
    return 'Unknown'


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
                session.permanent = True
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

    # Get all users with additional info
    professors = User.query.filter_by(user_type='profesor').all()
    students = User.query.filter_by(user_type='elev').all()
    unapproved = User.query.filter(User.user_type == 'profesor', User.is_professor_approved == False).all()

    # Get lessons with author information
    lessons = db.session.query(Lesson).join(User, Lesson.author_id == User.id).order_by(desc(Lesson.created_at)).all()
    
    # Get tests with author information
    tests = db.session.query(Test).join(User, Test.author_id == User.id).order_by(desc(Test.created_at)).all()
    
    # Get grades with student and item information
    grades = db.session.query(Grade).join(User, Grade.student_id == User.id).order_by(desc(Grade.date)).all()

    # Get statistics
    stats = {
        'total_users': User.query.count(),
        'total_professors': len(professors),
        'total_students': len(students),
        'unapproved_professors': len(unapproved),
        'activity': get_user_activity_stats(),
    }

    # Get IP country information (simplified example)
    ip_countries = {}
    for user in User.query.filter(User.last_login.isnot(None)).all():
        # In a real app, you'd store the IP when users log in
        ip_countries[user.id] = get_country_from_ip(request.remote_addr)

    return render_template('admin.html',
                           professors=professors,
                           students=students,
                           unapproved=unapproved,
                           lessons=lessons,
                           tests=tests,
                           grades=grades,
                           stats=stats,
                           ip_countries=ip_countries,
                           datetime=datetime)


@admin_bp.route('/logout')
def admin_logout():
    session.pop(ADMIN_SESSION_KEY, None)
    logger.info("Admin logged out")
    flash('You have been logged out.', 'success')
    return redirect(url_for('admin.admin_login'))