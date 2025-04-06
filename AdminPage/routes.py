from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import current_user, login_required
from app import db, logger, bcrypt, regenerate_credentials, load_credentials, send_login_notification
from models import User, Lesson, Test, Grade, AdminWhitelist
from datetime import datetime, timedelta
import os
import json
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from StudioPage.routes import SUBJECTS, get_professor_dir, LECTII_DIR, TESTE_DIR, INSTANCE_DIR
from functools import wraps

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
                    db.session.delete(user)
                    db.session.commit()
                    flash(f'User {user.name} has been deleted.', 'success')
                elif action == 'decline':
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
        subject_dir = os.path.join(LECTII_DIR, subject_key, 'profesori')
        if os.path.exists(subject_dir):
            for professor_dir in os.listdir(subject_dir):
                prof_path = os.path.join(subject_dir, professor_dir)
                if os.path.isdir(prof_path):
                    for lesson_file in os.listdir(prof_path):
                        if lesson_file.endswith('.html'):
                            professor = User.query.filter_by(email=professor_dir).first()
                            professor_name = professor.name if professor else professor_dir
                            lessons.append({
                                'title': lesson_file.replace('.html', ''),
                                'subject': SUBJECTS[subject_key]['name'],
                                'subject_key': subject_key,
                                'professor': professor_name,
                                'professor_email': professor_dir
                            })

    # Get all tests
    tests = []
    for subject_key in SUBJECTS:
        subject_dir = os.path.join(TESTE_DIR, subject_key, 'profesori')
        if os.path.exists(subject_dir):
            for professor_dir in os.listdir(subject_dir):
                prof_path = os.path.join(subject_dir, professor_dir)
                if os.path.isdir(prof_path):
                    for test_file in os.listdir(prof_path):
                        if test_file.endswith('.json'):
                            with open(os.path.join(prof_path, test_file), 'r', encoding='utf-8') as f:
                                test_data = json.load(f)
                                professor = User.query.filter_by(email=professor_dir).first()
                                tests.append({
                                    'title': test_data.get('title', test_file.replace('.json', '')),
                                    'subject_key': subject_key,
                                    'subject': SUBJECTS[subject_key]['name'],
                                    'author': professor,
                                    'questions': len(test_data.get('questions', [])),
                                    'created_at': test_data.get('created_at', 'Unknown')
                                })

    # Get all grades from both locations
    grades = []
    
    # Check test results in each subject directory
    for subject_key in SUBJECTS:
        subject_dir = os.path.join(TESTE_DIR, subject_key, 'profesori')
        if os.path.exists(subject_dir):
            for professor_dir in os.listdir(subject_dir):
                results_dir = os.path.join(subject_dir, professor_dir, 'results')
                if os.path.exists(results_dir):
                    for result_file in os.listdir(results_dir):
                        if result_file.endswith('.json'):
                            with open(os.path.join(results_dir, result_file), 'r', encoding='utf-8') as f:
                                result_data = json.load(f)
                                student = User.query.filter_by(email=result_data['student_email']).first()
                                professor = User.query.filter_by(email=professor_dir).first()
                                if student and professor:
                                    grades.append({
                                        'student': student,
                                        'professor': professor,
                                        'subject': subject_key,
                                        'test_title': result_data['lesson_title'],
                                        'score': result_data['score'],
                                        'date': datetime.fromisoformat(result_data['timestamp'])
                                    })

    # Check grades directory
    grades_dir = os.path.join(INSTANCE_DIR, 'grades')
    if os.path.exists(grades_dir):
        for student_email in os.listdir(grades_dir):
            student_dir = os.path.join(grades_dir, student_email)
            if os.path.isdir(student_dir):
                for grade_file in os.listdir(student_dir):
                    if grade_file.endswith('.json'):
                        with open(os.path.join(student_dir, grade_file), 'r', encoding='utf-8') as f:
                            grade_data = json.load(f)
                            student = User.query.filter_by(email=student_email).first()
                            professor = User.query.filter_by(email=grade_data.get('professor_email')).first()
                            if student and professor:
                                grades.append({
                                    'student': student,
                                    'professor': professor,
                                    'subject': grade_data['subject'],
                                    'test_title': grade_data['test_title'],
                                    'score': grade_data['score'],
                                    'date': datetime.fromisoformat(grade_data['date'])
                                })

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
        'activity': {
            'active_users': active_users,
            'user_types': {
                'students': len(students),
                'professors': len(professors),
                'admins': User.query.filter_by(user_type='admin').count()
            }
        }
    }

    return render_template('admin.html',
                         user=current_user,
                         professors=professors,
                         students=students,
                         lessons=lessons,
                         tests=tests,
                         grades=grades,
                         subjects=SUBJECTS,
                         stats=stats)


@admin_bp.route('/logout')
def admin_logout():
    session.pop(ADMIN_SESSION_KEY, None)
    logger.info("Admin logged out")
    flash('You have been logged out.', 'success')
    return redirect(url_for('admin.admin_login'))


@admin_bp.route('/whitelist', methods=['GET', 'POST'])
def manage_whitelist():
    if not is_admin_logged_in():
        return redirect(url_for('admin.admin_login'))

    if request.method == 'POST':
        action = request.form.get('action')
        ip_address = request.form.get('ip_address')
        description = request.form.get('description')

        if action == 'add':
            if not ip_address:
                flash('IP address is required', 'error')
            else:
                # Check if IP is already whitelisted
                existing = AdminWhitelist.query.filter_by(ip_address=ip_address).first()
                if existing:
                    flash('IP address is already whitelisted', 'error')
                else:
                    whitelist = AdminWhitelist(
                        ip_address=ip_address,
                        description=description,
                        created_by=current_user.email if current_user.is_authenticated else 'System'
                    )
                    db.session.add(whitelist)
                    db.session.commit()
                    flash('IP address added to whitelist', 'success')
        elif action == 'remove':
            ip_id = request.form.get('ip_id')
            if ip_id:
                whitelist = AdminWhitelist.query.get(ip_id)
                if whitelist:
                    db.session.delete(whitelist)
                    db.session.commit()
                    flash('IP address removed from whitelist', 'success')

    # Get all whitelisted IPs
    whitelisted_ips = AdminWhitelist.query.order_by(AdminWhitelist.created_at.desc()).all()

    return render_template('admin_whitelist.html',
                         user=current_user,
                         whitelisted_ips=whitelisted_ips)


@admin_bp.route('/test/<subject>/<test>/<professor_email>')
def view_test(subject, test, professor_email):
    if not is_admin_logged_in():
        return redirect(url_for('admin.admin_login'))

    if subject not in SUBJECTS:
        flash('Invalid subject', 'error')
        return redirect(url_for('admin.admin_panel'))

    test_dir = os.path.join(TESTE_DIR, subject, 'profesori', professor_email)
    test_file = os.path.join(test_dir, f"{test}.json")

    if not os.path.exists(test_file):
        flash('Test not found', 'error')
        return redirect(url_for('admin.admin_panel'))

    with open(test_file, 'r', encoding='utf-8') as f:
        test_data = json.load(f)

    return render_template('view_test.html',
                         user=current_user,
                         subject=subject,
                         test=test_data,
                         subjects=SUBJECTS,
                         is_admin=True)


@admin_bp.route('/lesson/<subject>/<title>/<professor_email>')
def view_lesson(subject, title, professor_email):
    if not is_admin_logged_in():
        return redirect(url_for('admin.admin_login'))

    if subject not in SUBJECTS:
        flash('Invalid subject', 'error')
        return redirect(url_for('admin.admin_panel'))

    lesson_dir = os.path.join(LECTII_DIR, subject, 'profesori', professor_email)
    lesson_file = os.path.join(lesson_dir, f"{title}.html")

    if not os.path.exists(lesson_file):
        flash('Lesson not found', 'error')
        return redirect(url_for('admin.admin_panel'))

    with open(lesson_file, 'r', encoding='utf-8') as f:
        lesson_content = f.read()

    return render_template('view_lesson.html',
                         user=current_user,
                         subject=subject,
                         lesson_title=title,
                         lesson_content=lesson_content,
                         subjects=SUBJECTS,
                         is_admin=True)


@admin_bp.route('/student/<student_id>')
def view_student(student_id):
    if not is_admin_logged_in():
        return redirect(url_for('admin.admin_login'))

    student = User.query.get(student_id)
    if not student or student.user_type != 'elev':
        flash('Student not found', 'error')
        return redirect(url_for('admin.admin_panel'))

    # Get student's grades
    grades = []
    grades_dir = os.path.join(INSTANCE_DIR, 'grades', student.email)
    if os.path.exists(grades_dir):
        for grade_file in os.listdir(grades_dir):
            if grade_file.endswith('.json'):
                with open(os.path.join(grades_dir, grade_file), 'r', encoding='utf-8') as f:
                    grade_data = json.load(f)
                    professor = User.query.filter_by(email=grade_data.get('professor_email')).first()
                    if professor:
                        grades.append({
                            'subject': grade_data['subject'],
                            'test_title': grade_data['test_title'],
                            'score': grade_data['score'],
                            'professor': professor,
                            'date': datetime.fromisoformat(grade_data['date'])
                        })

    grades.sort(key=lambda x: x['date'], reverse=True)

    return render_template('view_student.html',
                         user=current_user,
                         student=student,
                         grades=grades,
                         subjects=SUBJECTS,
                         is_admin=True)


@admin_bp.route('/delete', methods=['POST'])
@require_admin
def delete_item():
    action = request.form.get('action')
    
    if action == 'delete_lesson':
        lesson_title = request.form.get('lesson_title')
        subject = request.form.get('subject')
        professor_email = request.form.get('professor_email')
        
        if lesson_title and subject and professor_email:
            lesson_dir = os.path.join(LECTII_DIR, subject, 'profesori', professor_email)
            lesson_file = os.path.join(lesson_dir, f"{lesson_title}.html")
            
            if os.path.exists(lesson_file):
                try:
                    os.remove(lesson_file)
                    flash('Lesson deleted successfully', 'success')
                except Exception as e:
                    flash(f'Error deleting lesson: {str(e)}', 'error')
            else:
                flash('Lesson not found', 'error')
    
    elif action == 'delete_test':
        test_title = request.form.get('test_title')
        subject = request.form.get('subject')
        professor_email = request.form.get('professor_email')
        
        if test_title and subject and professor_email:
            test_dir = os.path.join(TESTE_DIR, subject, 'profesori', professor_email)
            test_file = os.path.join(test_dir, f"{test_title}.json")
            
            if os.path.exists(test_file):
                try:
                    os.remove(test_file)
                    flash('Test deleted successfully', 'success')
                except Exception as e:
                    flash(f'Error deleting test: {str(e)}', 'error')
            else:
                flash('Test not found', 'error')
    
    return redirect(url_for('admin.admin_panel'))