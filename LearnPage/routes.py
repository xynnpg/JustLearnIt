from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from models import User
import os
import json
from datetime import datetime

learn_bp = Blueprint('learn', __name__,
                     template_folder='../Templates',
                     static_folder='../static/learn')

# Configuration
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, '../instance')
LECTII_DIR = os.path.join(INSTANCE_DIR, 'lectii')
TESTE_DIR = os.path.join(INSTANCE_DIR, 'teste')

# Subject mapping
SUBJECTS = {
    'Bio': {
        'name': 'Biologie',
        'color': '#4CAF50',
        'icon': 'fas fa-leaf'
    },
    'Isto': {
        'name': 'Istorie',
        'color': '#FF5722',
        'icon': 'fas fa-landmark'
    },
    'Geogra': {
        'name': 'Geografie',
        'color': '#2196F3',
        'icon': 'fas fa-globe-europe'
    }
}


def get_professors_for_subject(subject_key):
    """Get approved professors for a subject"""
    subject_name = SUBJECTS.get(subject_key, {}).get('name', '')
    if not subject_name:
        return []

    # Get all professors and filter by subject (case-insensitive)
    professors = User.query.filter_by(
        user_type='profesor',
        is_professor_approved=True
    ).all()
    
    # Filter professors by subject (case-insensitive)
    return [p for p in professors if p.subject and p.subject.lower() == subject_name.lower()]


def get_lessons_for_subject(subject_key):
    """Get all lessons for a subject"""
    lessons = []
    
    # Convert subject key to proper case for directory lookup
    subject_dir_name = None
    for key, data in SUBJECTS.items():
        if key.lower() == subject_key.lower():
            subject_dir_name = key
            break
    
    if not subject_dir_name:
        return lessons
        
    subject_dir = os.path.join(LECTII_DIR, subject_dir_name)

    if not os.path.exists(subject_dir):
        return lessons

    # Get all professor directories
    professors_dir = os.path.join(subject_dir, 'profesori')
    if not os.path.exists(professors_dir):
        return lessons

    for professor_dir in os.listdir(professors_dir):
        prof_path = os.path.join(professors_dir, professor_dir)
        if os.path.isdir(prof_path):
            for lesson_file in os.listdir(prof_path):
                if lesson_file.endswith('.html'):
                    # Get professor name from database
                    professor = User.query.filter_by(email=professor_dir).first()
                    professor_name = professor.name if professor else professor_dir
                    
                    lessons.append({
                        'professor': professor_name,
                        'professor_email': professor_dir,
                        'title': lesson_file.replace('.html', ''),
                        'path': os.path.join(prof_path, lesson_file)
                    })
    return lessons


def get_lesson_content(subject_key, professor_email, lesson_title):
    """Get content of a specific lesson"""
    lesson_path = os.path.join(
        LECTII_DIR,
        subject_key,
        'profesori',
        professor_email,
        f"{lesson_title}.html"
    )

    if not os.path.exists(lesson_path):
        return None

    with open(lesson_path, 'r', encoding='utf-8') as f:
        return f.read()


def get_test_for_lesson(subject_key, professor_email, lesson_title):
    """Get test for a specific lesson"""
    # Convert subject key to proper case for directory lookup
    subject_dir_name = None
    for key, data in SUBJECTS.items():
        if key.lower() == subject_key.lower():
            subject_dir_name = key
            break
    
    if not subject_dir_name:
        return None

    test_dir = os.path.join(TESTE_DIR, subject_dir_name, 'profesori', professor_email)
    if not os.path.exists(test_dir):
        return None

    test_file = os.path.join(test_dir, f"{lesson_title}_test.json")
    if os.path.exists(test_file):
        with open(test_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


@learn_bp.route('/learn/<subject_key>')
@login_required
def subject_page(subject_key):
    """Main subject page showing professors and lessons"""
    # Find the correct subject key (case-insensitive)
    subject_data = None
    for key, data in SUBJECTS.items():
        if key.lower() == subject_key.lower():
            subject_data = data
            subject_key = key  # Use the correct case
            break
            
    if not subject_data:
        flash('Invalid subject selected', 'error')
        return redirect(url_for('choose.index'))

    professors = get_professors_for_subject(subject_key)
    lessons = get_lessons_for_subject(subject_key)
    
    # Get tests for the subject
    tests = []
    test_dir = os.path.join(TESTE_DIR, subject_key, 'profesori')
    if os.path.exists(test_dir):
        for professor_dir in os.listdir(test_dir):
            prof_path = os.path.join(test_dir, professor_dir)
            if os.path.isdir(prof_path):
                for test_file in os.listdir(prof_path):
                    if test_file.endswith('.json'):
                        with open(os.path.join(prof_path, test_file), 'r', encoding='utf-8') as f:
                            test_data = json.load(f)
                            # Get professor name from database
                            professor = User.query.filter_by(email=professor_dir).first()
                            professor_name = professor.name if professor else professor_dir
                            
                            # Extract lesson title from test title if possible
                            lesson_title = test_data.get('lesson', test_file.replace('.json', ''))
                            
                            tests.append({
                                'title': test_data.get('title', test_file.replace('.json', '')),
                                'professor': professor_name,
                                'professor_email': professor_dir,
                                'lesson_title': lesson_title,
                                'question_count': len(test_data.get('questions', [])),
                                'created_at': test_data.get('created_at', 'Unknown')
                            })

    return render_template('learn_subject.html',
                           subject=subject_data['name'],
                           subject_key=subject_key,
                           subject_color=subject_data['color'],
                           subject_icon=subject_data['icon'],
                           professors=professors,
                           lessons=lessons,
                           tests=tests)


@learn_bp.route('/learn/<subject_key>/<professor_email>')
@login_required
def professor_lessons(subject_key, professor_email):
    """Show all lessons from a specific professor"""
    # Find the correct subject key (case-insensitive)
    subject_data = None
    for key, data in SUBJECTS.items():
        if key.lower() == subject_key.lower():
            subject_data = data
            subject_key = key  # Use the correct case
            break
            
    if not subject_data:
        flash('Invalid subject selected', 'error')
        return redirect(url_for('choose.index'))

    professor = User.query.filter_by(email=professor_email).first()
    if not professor or not professor.is_professor_approved:
        flash('Professor not found', 'error')
        return redirect(url_for('learn.subject_page', subject_key=subject_key))

    lessons = []
    prof_dir = os.path.join(LECTII_DIR, subject_key, 'profesori', professor_email)
    if os.path.exists(prof_dir):
        for lesson_file in os.listdir(prof_dir):
            if lesson_file.endswith('.html'):
                lessons.append({
                    'title': lesson_file.replace('.html', ''),
                    'path': os.path.join(prof_dir, lesson_file)
                })

    return render_template('professor_lessons.html',
                           subject=subject_data['name'],
                           subject_key=subject_key,
                           subject_color=subject_data['color'],
                           subject_icon=subject_data['icon'],
                           professor=professor,
                           lessons=lessons)


@learn_bp.route('/subject/<subject_key>/professor/<professor_email>/lesson/<lesson_title>')
@login_required
def view_lesson(subject_key, professor_email, lesson_title):
    """View a specific lesson"""
    # Find the correct subject key (case-insensitive)
    subject_data = None
    for key, data in SUBJECTS.items():
        if key.lower() == subject_key.lower():
            subject_data = data
            subject_key = key  # Use the correct case
            break
            
    if not subject_data:
        flash('Invalid subject', 'error')
        return redirect(url_for('account.account'))

    # Get the lesson content
    lesson_dir = os.path.join(LECTII_DIR, subject_key, 'profesori', professor_email)
    lesson_file = os.path.join(lesson_dir, f"{lesson_title}.html")
    
    if not os.path.exists(lesson_file):
        flash('Lesson not found', 'error')
        return redirect(url_for('learn.professor_lessons', subject_key=subject_key, professor_email=professor_email))

    with open(lesson_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check if there's an associated test
    test = None
    test_dir = os.path.join(TESTE_DIR, subject_key, 'profesori', professor_email)
    
    # First try to find a test with the lesson title
    test_file = None
    if os.path.exists(test_dir):
        # Look for a test file that matches the lesson title
        for file in os.listdir(test_dir):
            if file.endswith('.json'):
                with open(os.path.join(test_dir, file), 'r', encoding='utf-8') as f:
                    test_data = json.load(f)
                    if test_data.get('lesson') == lesson_title:
                        test_file = os.path.join(test_dir, file)
                        test = test_data
                        break
    
    # If no test found with lesson title, try the old naming pattern
    if not test_file:
        test_file = os.path.join(test_dir, f"{lesson_title}_test.json")
        if os.path.exists(test_file):
            with open(test_file, 'r', encoding='utf-8') as f:
                test = json.load(f)

    # Check if current user is the professor
    is_professor = current_user.email == professor_email

    return render_template('view_lessons.html',
                         subject=subject_data['name'],
                         subject_key=subject_key,
                         subject_color=subject_data['color'],
                         subject_icon=subject_data['icon'],
                         lesson_title=lesson_title,
                         professor_email=professor_email,
                         content=content,
                         test=test,
                         is_professor=is_professor)


@learn_bp.route('/subject/<subject_key>/professor/<professor_email>/lesson/<lesson_title>/test')
@login_required
def take_test(subject_key, professor_email, lesson_title):
    """Take a test for a specific lesson"""
    # Find the correct subject key (case-insensitive)
    subject_data = None
    for key, data in SUBJECTS.items():
        if key.lower() == subject_key.lower():
            subject_data = data
            subject_key = key  # Use the correct case
            break
            
    if not subject_data:
        flash('Invalid subject', 'error')
        return redirect(url_for('account.account'))

    # Get the test content
    test_dir = os.path.join(TESTE_DIR, subject_key, 'profesori', professor_email)
    
    # First try to find a test with the lesson title
    test_file = None
    if os.path.exists(test_dir):
        # Look for a test file that matches the lesson title
        for file in os.listdir(test_dir):
            if file.endswith('.json'):
                with open(os.path.join(test_dir, file), 'r', encoding='utf-8') as f:
                    test_data = json.load(f)
                    if test_data.get('lesson') == lesson_title:
                        test_file = os.path.join(test_dir, file)
                        break
    
    # If no test found with lesson title, try the old naming pattern
    if not test_file:
        test_file = os.path.join(test_dir, f"{lesson_title}_test.json")
    
    if not os.path.exists(test_file):
        flash('Test not found', 'error')
        return redirect(url_for('learn.view_lesson', 
                              subject_key=subject_key, 
                              professor_email=professor_email, 
                              lesson_title=lesson_title))

    with open(test_file, 'r', encoding='utf-8') as f:
        test = json.load(f)

    return render_template('take_test.html',
                         subject=subject_data['name'],
                         subject_key=subject_key,
                         subject_color=subject_data['color'],
                         subject_icon=subject_data['icon'],
                         lesson_title=lesson_title,
                         professor_email=professor_email,
                         test=test)


@learn_bp.route('/subject/<subject_key>/professor/<professor_email>/lesson/<lesson_title>/test/submit', methods=['POST'])
@login_required
def submit_test(subject_key, professor_email, lesson_title):
    """Submit test answers"""
    # Find the correct subject key (case-insensitive)
    subject_data = None
    for key, data in SUBJECTS.items():
        if key.lower() == subject_key.lower():
            subject_data = data
            subject_key = key  # Use the correct case
            break
            
    if not subject_data:
        flash('Invalid subject', 'error')
        return redirect(url_for('account.account'))

    # Get the test content
    test_dir = os.path.join(TESTE_DIR, subject_key, 'profesori', professor_email)
    
    # First try to find a test with the lesson title
    test_file = None
    if os.path.exists(test_dir):
        # Look for a test file that matches the lesson title
        for file in os.listdir(test_dir):
            if file.endswith('.json'):
                with open(os.path.join(test_dir, file), 'r', encoding='utf-8') as f:
                    test_data = json.load(f)
                    if test_data.get('lesson') == lesson_title:
                        test_file = os.path.join(test_dir, file)
                        break
    
    # If no test found with lesson title, try the old naming pattern
    if not test_file:
        test_file = os.path.join(test_dir, f"{lesson_title}_test.json")
    
    if not os.path.exists(test_file):
        flash('Test not found', 'error')
        return redirect(url_for('learn.view_lesson', 
                              subject_key=subject_key, 
                              professor_email=professor_email, 
                              lesson_title=lesson_title))

    with open(test_file, 'r', encoding='utf-8') as f:
        test = json.load(f)

    # Get answers from form
    answers = {}
    for i, question in enumerate(test['questions']):
        if question['type'] == 'multiple_choice':
            answers[str(i)] = request.form.get(f'question_{i}')
        elif question['type'] in ['short_answer', 'essay']:
            answers[str(i)] = request.form.get(f'question_{i}')

    # Calculate score
    score = 0
    total = len(test['questions'])
    for i, question in enumerate(test['questions']):
        if question['type'] == 'multiple_choice':
            if str(answers.get(str(i))) == str(question['correctIndex']):
                score += 1

    # Save test results
    results_dir = os.path.join(test_dir, 'results')
    os.makedirs(results_dir, exist_ok=True)
    
    result = {
        'student_email': current_user.email,
        'lesson_title': lesson_title,
        'score': score,
        'total': total,
        'answers': answers,
        'timestamp': datetime.now().isoformat()
    }
    
    result_file = os.path.join(results_dir, f"{lesson_title}_{current_user.email}.json")
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)

    flash(f'Test submitted! Your score: {score}/{total}', 'success')
    return redirect(url_for('learn.view_lesson', 
                          subject_key=subject_key, 
                          professor_email=professor_email, 
                          lesson_title=lesson_title))