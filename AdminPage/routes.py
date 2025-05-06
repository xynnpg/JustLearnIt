from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
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


def get_professor_path(subject, content_type='lectii'):
    return f"{content_type}/{subject}/profesori/{current_user.email}"

def get_test_path(subject, professor_email, test_name):
    return f"teste/{subject}/profesori/{professor_email}/{test_name}"

def get_test_result_path(subject, professor_email, test_name, student_email):
    return f"teste/{subject}/profesori/{professor_email}/results/{test_name}_{student_email}.json"

@admin_bp.route('/tests/<subject>/<test_name>/<email>')
@login_required
@require_admin
def view_tests(subject, test_name, email):
    try:
        # Get test data
        url = f"{STORAGE_API_URL}/files/teste/{subject}/profesori/{email}/{test_name}.json"
        print(f"Fetching test from: {url}")
        test_data = requests.get(url)
        print(f"Test response status: {test_data.status_code}")
        
        if test_data.status_code != 200:
            print(f"Failed to fetch test. Status: {test_data.status_code}, Response: {test_data.text}")
            flash('Test not found', 'error')
            return redirect(url_for('admin.admin_panel'))

        # Get results
        results_url = f"{STORAGE_API_URL}/folders/teste/{subject}/profesori/{email}/results"
        print(f"Fetching results from: {results_url}")
        results = requests.get(results_url)
        print(f"Results response status: {results.status_code}")

        if results.status_code != 200:
            print(f"Failed to fetch results. Status: {results.status_code}, Response: {results.text}")
            flash('Error getting results', 'error')
            return redirect(url_for('admin.admin_panel'))

        test_results = []
        for result in results.json():
            if result['name'].endswith('.json'):
                result_url = f"{STORAGE_API_URL}/files/teste/{subject}/profesori/{email}/results/{result['name']}"
                print(f"Fetching result from: {result_url}")
                result_data = requests.get(result_url)
                if result_data.status_code == 200:
                    test_results.append(result_data.json())

        # Get all professors and students for stats
        professors = User.query.filter_by(user_type='profesor').all()
        students = User.query.filter_by(user_type='elev').all()

        # Get stats for the template
        stats = {
            'total_users': len(professors) + len(students),
            'total_professors': len(professors),
            'total_students': len(students),
            'total_lessons': 0,
            'total_tests': 0,
            'total_grades': len(test_results)
        }

        # Get user activity stats for the last 7 days
        active_users = {}
        for i in range(7):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            active_users[date] = User.query.filter(
                User.last_login >= datetime.strptime(date, '%Y-%m-%d'),
                User.last_login < datetime.strptime(date, '%Y-%m-%d') + timedelta(days=1)
            ).count()

        # Prepare chart data
        activity_labels = list(active_users.keys())[::-1]
        activity_data = list(active_users.values())[::-1]
        user_types_data = [len(students), len(professors), 1]  # [students, professors, admins]

        # Get subject data
        subject_labels = [s['name'] for s in SUBJECTS.values()]
        subject_data = [1 if s == subject else 0 for s in SUBJECTS.keys()]
        subject_colors = [s['color'] for s in SUBJECTS.values()]

        # Get results distribution
        results_distribution = [0] * 10
        for result in test_results:
            try:
                score = float(result.get('score', 0))
                idx = int(score // 10)
                if 0 <= idx < 10:
                    results_distribution[idx] += 1
            except Exception:
                continue

        return render_template('admin_tests.html',
                            subject=subject,
                            test_name=test_name,
                            test_data=test_data.json(),
                            test_results=test_results,
                            email=email,
                            stats=stats,
                            activity_labels=activity_labels,
                            activity_data=activity_data,
                            user_types_data=user_types_data,
                            subject_labels=subject_labels,
                            subject_data=subject_data,
                            subject_colors=subject_colors,
                            SUBJECTS=SUBJECTS,
                            results_distribution=results_distribution,
                            professors=professors,
                            students=students,
                            lessons=[],
                            tests=[],
                            grades=[])
    except Exception as e:
        print(f"Error viewing test: {str(e)}")
        flash('Error viewing test', 'error')
        return redirect(url_for('admin.admin_panel'))

@admin_bp.route('/results/<subject_key>', methods=['GET'])
@login_required
@require_admin
def view_results(subject_key):
    if subject_key not in SUBJECTS:
        flash('Invalid subject', 'error')
        return redirect(url_for('admin.index'))
        
    try:
        results_by_professor = {}
        # Get all professors
        response = requests.get(f"{STORAGE_API_URL}/folders/teste/{subject_key}/profesori")
        if response.status_code == 200:
            # The API returns a list directly, not a dictionary with 'folders' key
            professors = [item for item in response.json() if item['type'] == 'folder']
            
            for professor in professors:
                professor_email = professor['name']
                # Get results for each professor
                results_response = requests.get(f"{STORAGE_API_URL}/folders/teste/{subject_key}/profesori/{professor_email}/results")
                if results_response.status_code == 200:
                    # The API returns a list directly, not a dictionary with 'files' key
                    result_files = [item for item in results_response.json() if item['type'] == 'file']
                    
                    if result_files:
                        results = []
                        for result_file in result_files:
                            result_response = requests.get(f"{STORAGE_API_URL}/files/teste/{subject_key}/profesori/{professor_email}/results/{result_file['name']}")
                            if result_response.status_code == 200:
                                result_data = result_response.json()
                                results.append(result_data)
                        
                        if results:
                            results_by_professor[professor_email] = results
                            
        return render_template('admin_results.html',
                            user=current_user,
                            subject=subject_key,
                            results=results_by_professor)
                            
    except Exception as e:
        print(f"Error viewing results: {str(e)}")
        flash('Error viewing results', 'error')
        return redirect(url_for('admin.index'))

@admin_bp.route('/delete_item', methods=['POST'])
@login_required
@require_admin
def delete_item():
    action = request.form.get('action')
    
    if action == 'delete_lesson':
        lesson_title = request.form.get('lesson_title')
        subject = request.form.get('subject')
        professor_email = request.form.get('professor_email')
        
        if lesson_title and subject and professor_email:
            try:
                # Delete the lesson file
                lesson_path = f"lectii/{subject}/profesori/{professor_email}/{lesson_title}.html"
                response = requests.delete(f"{STORAGE_API_URL}/files/{lesson_path}")
                
                if response.status_code == 200:
                    flash(f'Lesson {lesson_title} has been deleted.', 'success')
                else:
                    flash(f'Error deleting lesson {lesson_title}.', 'error')
                    
            except Exception as e:
                print(f"Error deleting lesson: {str(e)}")
                flash('Error deleting lesson', 'error')
    
    elif action == 'delete_test':
        test_title = request.form.get('test_title')
        subject = request.form.get('subject')
        professor_email = request.form.get('professor_email')
        
        if test_title and subject and professor_email:
            try:
                # Delete the test file
                test_path = f"teste/{subject}/profesori/{professor_email}/{test_title}.json"
                response = requests.delete(f"{STORAGE_API_URL}/files/{test_path}")
                
                if response.status_code == 200:
                    flash(f'Test {test_title} has been deleted.', 'success')
                else:
                    flash(f'Error deleting test {test_title}.', 'error')
                    
            except Exception as e:
                print(f"Error deleting test: {str(e)}")
                flash('Error deleting test', 'error')
                
    return redirect(url_for('admin.admin_panel'))

@admin_bp.route('/lessons/<subject>/<lesson_name>/<email>/edit', methods=['GET', 'POST'])
@login_required
@require_admin
def edit_lesson(subject, lesson_name, email):
    if request.method == 'GET':
        try:
            # Get the lesson data from storage
            url = f"{STORAGE_API_URL}/files/lectii/{subject}/profesori/{email}/{lesson_name}.html"
            print(f"Fetching lesson from: {url}")
            response = requests.get(url)
            print(f"Response status: {response.status_code}")
            print(f"Response content: {response.text[:200]}...")  # Print first 200 chars
            
            if response.status_code == 200:
                lesson_data = {
                    'title': lesson_name,
                    'subject': subject,
                    'content': response.text,
                    'professor_email': email
                }
                return render_template('edit_lesson.html', lesson=lesson_data)
            else:
                print(f"Failed to fetch lesson. Status: {response.status_code}, Response: {response.text}")
                flash('Failed to fetch lesson data', 'error')
                return redirect(url_for('admin.admin_panel'))
        except Exception as e:
            print(f"Error fetching lesson: {str(e)}")
            flash('Error fetching lesson data', 'error')
            return redirect(url_for('admin.admin_panel'))
    
    elif request.method == 'POST':
        try:
            # Get the updated lesson data from the form
            updated_lesson = {
                'title': request.form.get('title'),
                'subject': request.form.get('subject'),
                'content': request.form.get('content'),
                'professor_email': email
            }
            
            # Send PUT request to storage API
            url = f"{STORAGE_API_URL}/files/lectii/{subject}/profesori/{email}/{lesson_name}.html"
            print(f"Updating lesson at: {url}")
            response = requests.put(
                url,
                data=updated_lesson['content'].encode('utf-8'),
                headers={'Content-Type': 'text/html'}
            )
            print(f"Update response status: {response.status_code}")
            print(f"Update response: {response.text}")
            
            if response.status_code == 200:
                flash('Lesson updated successfully', 'success')
            else:
                flash('Failed to update lesson', 'error')
            
            return redirect(url_for('admin.admin_panel'))
        except Exception as e:
            print(f"Error updating lesson: {str(e)}")
            flash('Error updating lesson', 'error')
            return redirect(url_for('admin.admin_panel'))

@admin_bp.route('/lessons/<subject>/<lesson_name>/<email>/delete', methods=['POST'])
@login_required
@require_admin
def delete_lesson(subject, lesson_name, email):
    try:
        # Send DELETE request to storage API
        response = requests.delete(f"{STORAGE_API_URL}/files/lectii/{subject}/profesori/{email}/{lesson_name}.html")
        
        if response.status_code == 200:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to delete lesson'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})