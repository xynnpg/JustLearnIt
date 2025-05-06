from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import current_user, login_required
from app import db, logger, bcrypt, mail
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
from utils import load_credentials, regenerate_credentials, send_login_notification

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
                send_login_notification(input_username, request.remote_addr, mail)
                
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
                                        student = User.query.filter_by(email=result_data.get('student_email')).first()
                                        professor = User.query.filter_by(email=professor_email).first()
                                        grades.append({
                                            'student': student if student else type('FakeUser', (), {'name': result_data.get('student_email', 'Unknown'), 'email': result_data.get('student_email', 'Unknown')}),
                                            'professor': professor if professor else type('FakeUser', (), {'name': professor_email, 'email': professor_email}),
                                            'subject': subject_key,
                                            'test_title': result_data.get('lesson_title', 'Unknown'),
                                            'score': result_data.get('score', 0),
                                            'date': datetime.fromisoformat(result_data.get('timestamp')) if result_data.get('timestamp') else datetime.now()
                                        })
        except Exception as e:
            logger.error(f"Error getting grades for {subject_key}: {str(e)}")

    # Remove duplicates and sort by date
    unique_grades = {}
    for grade in grades:
        key = (grade['student'].email, grade['professor'].email, grade['subject'], grade['test_title'])
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

    # Prepare chart data for the admin panel
    subject_labels = [s['name'] for s in SUBJECTS.values()]
    subject_data = [len([t for t in tests if t['subject_key'] == k]) for k in SUBJECTS.keys()]
    subject_colors = [s['color'] for s in SUBJECTS.values()]

    # User activity (last 7 days)
    activity_labels = list(stats['active_users'].keys())[::-1]
    activity_data = list(stats['active_users'].values())[::-1]

    # User types
    user_types_data = [stats['total_students'], stats['total_professors'], 1]

    # Results distribution (score buckets)
    results_distribution = [0]*10
    for grade in grades:
        try:
            score = float(grade['score'])
            idx = int(score // 10)
            if 0 <= idx < 10:
                results_distribution[idx] += 1
        except Exception:
            continue

    return render_template('admin_panel.html',
                         professors=professors,
                         students=students,
                         lessons=lessons,
                         tests=tests,
                         grades=grades,
                         stats=stats,
                         SUBJECTS=SUBJECTS,
                         subject_labels=subject_labels,
                         subject_data=subject_data,
                         subject_colors=subject_colors,
                         activity_labels=activity_labels,
                         activity_data=activity_data,
                         user_types_data=user_types_data,
                         results_distribution=results_distribution
    )


@admin_bp.route('/whitelist', methods=['GET', 'POST'])
@require_admin
def whitelist():
    if request.method == 'POST':
        ip_address = request.form.get('ip_address')
        description = request.form.get('description')
        
        if ip_address:
            whitelist = AdminWhitelist(
                ip_address=ip_address,
                description=description,
                created_by=current_user.email
            )
            db.session.add(whitelist)
            db.session.commit()
            flash('IP address added to whitelist.', 'success')
            return redirect(url_for('admin.whitelist'))
    
    whitelisted_ips = AdminWhitelist.query.all()
    return render_template('admin_whitelist.html', whitelisted_ips=whitelisted_ips)


@admin_bp.route('/credentials', methods=['GET', 'POST'])
@require_admin
def credentials():
    if request.method == 'POST':
        username, password, timestamp = regenerate_credentials(db, mail)
        if username and password:
            flash('Admin credentials regenerated successfully.', 'success')
        else:
            flash('Failed to regenerate admin credentials.', 'error')
        return redirect(url_for('admin.credentials'))
    
    stored_username, stored_password, timestamp = load_credentials()
    return render_template('admin_credentials.html',
                         username=stored_username,
                         password=stored_password,
                         timestamp=timestamp)


@admin_bp.route('/logout')
def admin_logout():
    session.pop(ADMIN_SESSION_KEY, None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('landing.index'))


def get_professor_path(subject, content_type='lectii'):
    return f"{STORAGE_API_URL}/folders/{content_type}/{subject}/profesori"


def get_test_path(subject, professor_email, test_name):
    return f"{STORAGE_API_URL}/files/teste/{subject}/profesori/{professor_email}/{test_name}.json"


def get_test_result_path(subject, professor_email, test_name, student_email):
    return f"{STORAGE_API_URL}/files/teste/{subject}/profesori/{professor_email}/results/{student_email}_{test_name}.json"


@admin_bp.route('/tests/<subject>/<test_name>/<email>')
@login_required
@require_admin
def view_tests(subject, test_name, email):
    try:
        # Get test content
        test_path = get_test_path(subject, email, test_name)
        test_response = requests.get(test_path)
        if test_response.status_code != 200:
            flash('Test not found.', 'error')
            return redirect(url_for('admin.admin_panel'))
        
        test_data = test_response.json()
        
        # Get test results
        results = []
        results_path = f"{STORAGE_API_URL}/folders/teste/{subject}/profesori/{email}/results"
        results_response = requests.get(results_path)
        if results_response.status_code == 200:
            results_contents = results_response.json()
            for result in results_contents:
                if result['type'] == 'file' and result['name'].endswith('.json'):
                    result_response = requests.get(f"{STORAGE_API_URL}/files/teste/{subject}/profesori/{email}/results/{result['name']}")
                    if result_response.status_code == 200:
                        result_data = result_response.json()
                        if result_data.get('lesson_title') == test_name:
                            student = User.query.filter_by(email=result_data.get('student_email')).first()
                            if student:
                                results.append({
                                    'student': student,
                                    'score': result_data.get('score', 0),
                                    'max_score': result_data.get('max_score', 0),
                                    'date': datetime.fromisoformat(result_data.get('timestamp')) if result_data.get('timestamp') else datetime.now()
                                })
        
        # Sort results by date
        results.sort(key=lambda x: x['date'], reverse=True)
        
        return render_template('admin_test_view.html',
                             test=test_data,
                             results=results,
                             subject=subject,
                             test_name=test_name,
                             professor_email=email)
    except Exception as e:
        logger.error(f"Error viewing test: {str(e)}")
        flash('Error viewing test.', 'error')
        return redirect(url_for('admin.admin_panel'))


@admin_bp.route('/results/<subject_key>', methods=['GET'])
@login_required
@require_admin
def view_results(subject_key):
    try:
        # Get all test results for the subject
        results = []
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
                                    student = User.query.filter_by(email=result_data.get('student_email')).first()
                                    professor = User.query.filter_by(email=professor_email).first()
                                    if student and professor:
                                        results.append({
                                            'student': student,
                                            'professor': professor,
                                            'test_title': result_data.get('lesson_title', 'Unknown'),
                                            'score': result_data.get('score', 0),
                                            'max_score': result_data.get('max_score', 0),
                                            'date': datetime.fromisoformat(result_data.get('timestamp')) if result_data.get('timestamp') else datetime.now()
                                        })
        
        # Sort results by date
        results.sort(key=lambda x: x['date'], reverse=True)
        
        return render_template('admin_results.html',
                             results=results,
                             subject_key=subject_key,
                             subject_name=SUBJECTS[subject_key]['name'])
    except Exception as e:
        logger.error(f"Error viewing results: {str(e)}")
        flash('Error viewing results.', 'error')
        return redirect(url_for('admin.admin_panel'))


@admin_bp.route('/delete_item', methods=['POST'])
@login_required
@require_admin
def delete_item():
    try:
        data = request.get_json()
        item_type = data.get('type')
        subject = data.get('subject')
        name = data.get('name')
        email = data.get('email')
        
        if not all([item_type, subject, name, email]):
            return jsonify({'error': 'Missing required parameters'}), 400
        
        if item_type == 'lesson':
            # Delete lesson file
            lesson_path = f"{STORAGE_API_URL}/files/lectii/{subject}/profesori/{email}/{name}.html"
            response = requests.delete(lesson_path)
            if response.status_code != 200:
                return jsonify({'error': 'Failed to delete lesson'}), 500
            
            flash('Lesson deleted successfully.', 'success')
        elif item_type == 'test':
            # Delete test file and its results
            test_path = f"{STORAGE_API_URL}/files/teste/{subject}/profesori/{email}/{name}.json"
            response = requests.delete(test_path)
            if response.status_code != 200:
                return jsonify({'error': 'Failed to delete test'}), 500
            
            # Delete test results
            results_path = f"{STORAGE_API_URL}/folders/teste/{subject}/profesori/{email}/results"
            results_response = requests.get(results_path)
            if results_response.status_code == 200:
                results_contents = results_response.json()
                for result in results_contents:
                    if result['type'] == 'file' and result['name'].endswith('.json'):
                        result_response = requests.get(f"{STORAGE_API_URL}/files/teste/{subject}/profesori/{email}/results/{result['name']}")
                        if result_response.status_code == 200:
                            result_data = result_response.json()
                            if result_data.get('lesson_title') == name:
                                delete_response = requests.delete(f"{STORAGE_API_URL}/files/teste/{subject}/profesori/{email}/results/{result['name']}")
                                if delete_response.status_code != 200:
                                    logger.error(f"Failed to delete test result: {result['name']}")
            
            flash('Test and its results deleted successfully.', 'success')
        
        return jsonify({'message': 'Item deleted successfully'})
    except Exception as e:
        logger.error(f"Error deleting item: {str(e)}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/lessons/<subject>/<lesson_name>/<email>/edit', methods=['GET', 'POST'])
@login_required
@require_admin
def edit_lesson(subject, lesson_name, email):
    try:
        lesson_path = f"{STORAGE_API_URL}/files/lectii/{subject}/profesori/{email}/{lesson_name}.html"
        
        if request.method == 'POST':
            content = request.form.get('content')
            if content:
                response = requests.put(lesson_path, data=content)
                if response.status_code == 200:
                    flash('Lesson updated successfully.', 'success')
                    return redirect(url_for('admin.admin_panel'))
                else:
                    flash('Failed to update lesson.', 'error')
            else:
                flash('No content provided.', 'error')
        
        # Get current lesson content
        response = requests.get(lesson_path)
        if response.status_code == 200:
            content = response.text
            return render_template('admin_edit_lesson.html',
                                 content=content,
                                 subject=subject,
                                 lesson_name=lesson_name,
                                 email=email)
        else:
            flash('Lesson not found.', 'error')
            return redirect(url_for('admin.admin_panel'))
    except Exception as e:
        logger.error(f"Error editing lesson: {str(e)}")
        flash('Error editing lesson.', 'error')
        return redirect(url_for('admin.admin_panel'))


@admin_bp.route('/lessons/<subject>/<lesson_name>/<email>/delete', methods=['POST'])
@login_required
@require_admin
def delete_lesson(subject, lesson_name, email):
    try:
        lesson_path = f"{STORAGE_API_URL}/files/lectii/{subject}/profesori/{email}/{lesson_name}.html"
        response = requests.delete(lesson_path)
        if response.status_code == 200:
            flash('Lesson deleted successfully.', 'success')
        else:
            flash('Failed to delete lesson.', 'error')
        return redirect(url_for('admin.admin_panel'))
    except Exception as e:
        logger.error(f"Error deleting lesson: {str(e)}")
        flash('Error deleting lesson.', 'error')
        return redirect(url_for('admin.admin_panel'))