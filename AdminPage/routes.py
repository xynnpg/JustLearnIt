from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import current_user, login_required
from app import db, logger, bcrypt, regenerate_credentials, load_credentials, send_login_notification
from models import User, Lesson, Test, Grade, AdminWhitelist
from datetime import datetime, timedelta
import os
import json
import requests
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from StudioPage.routes import SUBJECTS
from functools import wraps
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

STORAGE_API_URL = os.getenv('STORAGE_API_URL', 'http://localhost:5000/api')

admin_bp = Blueprint('admin', __name__,
                     template_folder='../Templates',
                     static_folder='../static/admin')

ADMIN_SESSION_KEY = 'admin_logged_in'


def require_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_admin_logged_in():
            return redirect(url_for('landing.index'))
        return f(*args, **kwargs)
    return decorated_function


def is_admin_logged_in():
    # Check if IP is whitelisted
    whitelisted = AdminWhitelist.query.filter_by(ip_address=request.remote_addr).first()
    if whitelisted:
        return True
    return session.get(ADMIN_SESSION_KEY, False)


def get_user_activity_stats():
    """Get user activity statistics"""
    active_users = db.session.query(
        func.date(User.last_login).label('date'),
        func.count(User.id).label('count')
    ).filter(
        User.last_login > (datetime.utcnow() - timedelta(days=7))
    ).group_by(
        func.date(User.last_login)
    ).all()

    active_users_dict = {str(date): count for date, count in active_users}

    user_types = db.session.query(
        User.user_type,
        func.count(User.id)
    ).group_by(
        User.user_type
    ).all()

    user_types_dict = dict(user_types)

    return {
        'active_users': active_users_dict,
        'user_types': user_types_dict
    }


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
                
                # Send login notification
                send_login_notification(input_username, request.remote_addr)
                
                # Add IP to whitelist if not already there
                whitelisted = AdminWhitelist.query.filter_by(ip_address=request.remote_addr).first()
                if not whitelisted:
                    whitelist = AdminWhitelist(
                        ip_address=request.remote_addr,
                        created_by=input_username
                    )
                    db.session.add(whitelist)
                    db.session.commit()
                    logger.info(f"Added IP {request.remote_addr} to admin whitelist")
                
                flash('Admin access granted.', 'info')
                return redirect(url_for('admin.admin_panel'))
            else:
                logger.debug(f"Admin login failed: Invalid credentials for {input_username}")
                flash('Invalid username or password.', 'error')
        else:
            logger.error("No admin credentials found")
            flash('Admin credentials not initialized.', 'error')

    return render_template('admin_login.html')


@admin_bp.route('/', methods=['GET', 'POST'])
@require_admin
def admin_panel():
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        action = request.form.get('action')
        
        if user_id and action:
            user = User.query.get(user_id)
            if user:
                if action == 'approve':
                    user.is_professor_approved = True
                    db.session.commit()
                    flash(f'Professor {user.name} has been approved.', 'success')
                elif action == 'revoke':
                    user.is_professor_approved = False
                    db.session.commit()
                    flash(f'Professor {user.name} has been revoked.', 'warning')
                elif action == 'delete':
                    # Delete user's data from storage API
                    try:
                        requests.delete(f"{STORAGE_API_URL}/folders/users/{user.email}")
                    except Exception as e:
                        logger.error(f"Error deleting user data from storage API: {e}")
                    
                    db.session.delete(user)
                    db.session.commit()
                    flash(f'User {user.name} has been deleted.', 'success')
                elif action == 'decline':
                    # Delete user's data from storage API
                    try:
                        requests.delete(f"{STORAGE_API_URL}/folders/users/{user.email}")
                    except Exception as e:
                        logger.error(f"Error deleting user data from storage API: {e}")
                    
                    db.session.delete(user)
                    db.session.commit()
                    flash(f'Professor application for {user.name} has been declined.', 'warning')
        
    # Get all professors
    professors = User.query.filter_by(user_type='profesor').all()
    
    # Get all students
    students = User.query.filter_by(user_type='elev').all()
    
    # Get all lessons
    lessons = []
    for subject_key in SUBJECTS:
        try:
            response = requests.get(f"{STORAGE_API_URL}/folders/lectii/{subject_key}/profesori")
            if response.status_code == 200:
                contents = response.json()
                for item in contents:
                    if item['type'] == 'folder':
                        professor_email = item['name']
                        prof_response = requests.get(f"{STORAGE_API_URL}/folders/lectii/{subject_key}/profesori/{professor_email}")
                        if prof_response.status_code == 200:
                            prof_contents = prof_response.json()
                            for lesson in prof_contents:
                                if lesson['type'] == 'file' and lesson['name'].endswith('.html'):
                                    professor = User.query.filter_by(email=professor_email).first()
                                    professor_name = professor.name if professor else professor_email
                                    lessons.append({
                                        'title': lesson['name'].replace('.html', ''),
                                        'subject': SUBJECTS[subject_key]['name'],
                                        'subject_key': subject_key,
                                        'professor': professor_name,
                                        'professor_email': professor_email
                                    })
        except Exception as e:
            logger.error(f"Error getting lessons for {subject_key}: {str(e)}")

    # Get all tests
    tests = []
    for subject_key in SUBJECTS:
        try:
            response = requests.get(f"{STORAGE_API_URL}/folders/teste/{subject_key}/profesori")
            if response.status_code == 200:
                contents = response.json()
                for item in contents:
                    if item['type'] == 'folder':
                        professor_email = item['name']
                        prof_response = requests.get(f"{STORAGE_API_URL}/folders/teste/{subject_key}/profesori/{professor_email}")
                        if prof_response.status_code == 200:
                            prof_contents = prof_response.json()
                            for test in prof_contents:
                                if test['type'] == 'file' and test['name'].endswith('.json'):
                                    professor = User.query.filter_by(email=professor_email).first()
                                    professor_name = professor.name if professor else professor_email
                                    tests.append({
                                        'title': test['name'].replace('.json', ''),
                                        'subject': SUBJECTS[subject_key]['name'],
                                        'subject_key': subject_key,
                                        'professor': professor_name,
                                        'professor_email': professor_email
                                    })
        except Exception as e:
            logger.error(f"Error getting tests for {subject_key}: {str(e)}")

    # Get all grades
    grades = []
    for subject_key in SUBJECTS:
        try:
            response = requests.get(f"{STORAGE_API_URL}/folders/teste/{subject_key}/profesori")
            if response.status_code == 200:
                contents = response.json()
                for item in contents:
                    if item['type'] == 'folder':
                        professor_email = item['name']
                        results_response = requests.get(f"{STORAGE_API_URL}/folders/teste/{subject_key}/profesori/{professor_email}/results")
                        if results_response.status_code == 200:
                            results_contents = results_response.json()
                            for result in results_contents:
                                if result['type'] == 'file' and result['name'].endswith('.json'):
                                    result_response = requests.get(f"{STORAGE_API_URL}/files/teste/{subject_key}/profesori/{professor_email}/results/{result['name']}")
                                    if result_response.status_code == 200:
                                        result_data = result_response.json()
                                        student = User.query.filter_by(email=result_data['student_email']).first()
                                        professor = User.query.filter_by(email=professor_email).first()
                                        if student and professor:
                                            grades.append({
                                                'student': student,
                                                'professor': professor,
                                                'subject': subject_key,
                                                'test_title': result_data['lesson_title'],
                                                'score': result_data['score'],
                                                'date': datetime.fromisoformat(result_data['timestamp'])
                                            })
        except Exception as e:
            logger.error(f"Error getting grades for {subject_key}: {str(e)}")

    # Remove duplicates and sort by date
    unique_grades = {}
    for grade in grades:
        key = f"{grade['student'].email}_{grade['test_title']}_{grade['subject']}"
        if key not in unique_grades or grade['date'] > unique_grades[key]['date']:
            unique_grades[key] = grade

    grades = list(unique_grades.values())
    grades.sort(key=lambda x: x['date'], reverse=True)

    # Get user activity stats for the last 7 days
    active_users = {}
    for i in range(7):
        date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        active_users[date] = User.query.filter(
            User.last_login >= datetime.strptime(date, '%Y-%m-%d'),
            User.last_login < datetime.strptime(date, '%Y-%m-%d') + timedelta(days=1)
        ).count()

    # Get user activity stats
    stats = {
        'total_users': len(professors) + len(students),
        'total_professors': len(professors),
        'total_students': len(students),
        'unapproved_professors': User.query.filter(User.user_type == 'profesor', User.is_professor_approved == False).count(),
        'active_users': active_users,
        'total_lessons': len(lessons),
        'total_tests': len(tests),
        'total_grades': len(grades)
    }

    return render_template('admin_panel.html',
                         professors=professors,
                         students=students,
                         lessons=lessons,
                         tests=tests,
                         grades=grades,
                         stats=stats)


@admin_bp.route('/whitelist', methods=['GET', 'POST'])
@require_admin
def whitelist():
    if request.method == 'POST':
        ip_address = request.form.get('ip_address')
        if ip_address:
            whitelisted = AdminWhitelist.query.filter_by(ip_address=ip_address).first()
            if whitelisted:
                db.session.delete(whitelisted)
                db.session.commit()
                flash(f'IP {ip_address} has been removed from whitelist.', 'success')
            else:
                # Get the current admin username
                username, _, _ = load_credentials()
                new_whitelist = AdminWhitelist(
                    ip_address=ip_address,
                    created_by=username
                )
                db.session.add(new_whitelist)
                db.session.commit()
                flash(f'IP {ip_address} has been added to whitelist.', 'success')
    
    whitelisted_ips = AdminWhitelist.query.all()
    return render_template('whitelist.html', whitelisted_ips=whitelisted_ips)


@admin_bp.route('/credentials', methods=['GET', 'POST'])
@require_admin
def credentials():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'regenerate':
            regenerate_credentials()
            flash('Admin credentials have been regenerated.', 'success')
        elif action == 'view':
            username, password, timestamp = load_credentials()
            if username and password:
                flash(f'Current credentials - Username: {username}, Password: {password}', 'info')
            else:
                flash('No admin credentials found.', 'error')
    return render_template('credentials.html')


@admin_bp.route('/logout')
def admin_logout():
    session.pop(ADMIN_SESSION_KEY, None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('landing.index'))