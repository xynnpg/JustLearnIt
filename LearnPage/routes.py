from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify
from flask_login import login_required, current_user
from app import db
from models import User, Lesson, Test
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from io import BytesIO
from functools import wraps

# Load environment variables
load_dotenv()

learn_bp = Blueprint('learn', __name__,
                     template_folder='../Templates',
                     static_folder='../static/learn')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_DIR = os.path.join(BASE_DIR, '../storage')
LECTII_DIR = os.path.join(STORAGE_DIR, 'lectii')
TESTE_DIR = os.path.join(STORAGE_DIR, 'teste')

def require_professor(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.user_type != 'profesor' or not current_user.is_professor_approved:
            flash('You must be an approved professor to access this page.', 'error')
            return redirect(url_for('landing.index'))
        return f(*args, **kwargs)
    return decorated_function

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

def get_professors_for_subject(subject):
    return User.query.filter_by(user_type='profesor', is_professor_approved=True).all()

def get_lessons_for_subject(subject):
    lessons = []
    professors = get_professors_for_subject(subject)
    for professor in professors:
        lessons_path = os.path.join(LECTII_DIR, subject, 'profesori', professor.email)
        if os.path.exists(lessons_path):
            for file in os.listdir(lessons_path):
                if file.endswith('.html'):
                    lesson_title = file.replace('.html', '')
                    # Check for test
                    test_path = os.path.join(TESTE_DIR, subject, 'profesori', professor.email, f'{lesson_title}.json')
                    has_test = os.path.exists(test_path)
                    test_data = None
                    if has_test:
                        with open(test_path, 'r') as tf:
                            test_data = json.load(tf)
                    lessons.append({
                        'title': lesson_title,
                        'professor': professor.name,
                        'professor_email': professor.email,
                        'has_test': has_test,
                        'test_data': test_data
                    })
    return lessons

def get_lesson_content(subject_key, professor_email, lesson_title):
    lesson_path = os.path.join(LECTII_DIR, subject_key, 'profesori', professor_email, f'{lesson_title}.html')
    if os.path.exists(lesson_path):
        with open(lesson_path, 'r') as f:
            return f.read()
    return None

def get_test_for_lesson(subject_key, professor_email, lesson_title):
    test_path = os.path.join(TESTE_DIR, subject_key, 'profesori', professor_email, f'{lesson_title}.json')
    if os.path.exists(test_path):
        with open(test_path, 'r') as f:
            return json.load(f)
    return None

def get_professor_path(subject, content_type='lectii'):
    return f"{content_type}/{subject}/profesori/{current_user.email}"

def get_test_path(subject, professor_email, test_name):
    return f"teste/{subject}/profesori/{professor_email}/{test_name}"

def get_test_result_path(subject, professor_email, test_name, student_email):
    return f"teste/{subject}/profesori/{professor_email}/results/{test_name}_{student_email}.json"

@learn_bp.route('/learn')
@login_required
def learn():
    all_results = {}
    for subject_key in SUBJECTS:
        results = []
        professors = get_professors_for_subject(subject_key)
        for professor in professors:
            results_path = os.path.join(TESTE_DIR, subject_key, 'profesori', professor.email, 'results')
            if os.path.exists(results_path):
                for file in os.listdir(results_path):
                    if file.endswith('.json') and current_user.email in file:
                        with open(os.path.join(results_path, file), 'r') as rf:
                            result_data = json.load(rf)
                            results.append(result_data)
        all_results[subject_key] = results
    return render_template('learn.html', 
                         user=current_user,
                         subjects=SUBJECTS,
                         results=all_results)

@learn_bp.route('/api/lessons', methods=['GET'])
@login_required
def get_lessons():
    try:
        # Get lessons from storage API
        response = requests.get(f"{STORAGE_API_URL}/lessons/{current_user.email}")
        if response.status_code == 200:
            lessons = response.json()
            return jsonify(lessons)
        else:
            return jsonify([])
    except Exception as e:
        print(f"Error getting lessons: {e}")
        return jsonify([])

@learn_bp.route('/api/lessons', methods=['POST'])
@login_required
def create_lesson():
    try:
        title = request.form.get('title')
        content = request.form.get('content')
        
        # Create lesson in storage API
        response = requests.post(
            f"{STORAGE_API_URL}/lessons/{current_user.email}",
            json={
                'title': title,
                'content': content
            }
        )
        
        if response.status_code == 201:
            return jsonify({'message': 'Lesson created successfully'})
        else:
            return jsonify({'error': 'Failed to create lesson'}), 400
    except Exception as e:
        print(f"Error creating lesson: {e}")
        return jsonify({'error': str(e)}), 500

@learn_bp.route('/api/lessons/<lesson_id>', methods=['PUT'])
@login_required
def update_lesson(lesson_id):
    try:
        title = request.form.get('title')
        content = request.form.get('content')
        
        # Update lesson in storage API
        response = requests.put(
            f"{STORAGE_API_URL}/lessons/{current_user.email}/{lesson_id}",
            json={
                'title': title,
                'content': content
            }
        )
        
        if response.status_code == 200:
            return jsonify({'message': 'Lesson updated successfully'})
        else:
            return jsonify({'error': 'Failed to update lesson'}), 400
    except Exception as e:
        print(f"Error updating lesson: {e}")
        return jsonify({'error': str(e)}), 500

@learn_bp.route('/api/lessons/<lesson_id>', methods=['DELETE'])
@login_required
def delete_lesson(lesson_id):
    try:
        # Delete lesson from storage API
        response = requests.delete(f"{STORAGE_API_URL}/lessons/{current_user.email}/{lesson_id}")
        
        if response.status_code == 200:
            return jsonify({'message': 'Lesson deleted successfully'})
        else:
            return jsonify({'error': 'Failed to delete lesson'}), 400
    except Exception as e:
        print(f"Error deleting lesson: {e}")
        return jsonify({'error': str(e)}), 500

@learn_bp.route('/api/tests', methods=['GET'])
@login_required
def get_tests():
    try:
        # Get tests from storage API
        response = requests.get(f"{STORAGE_API_URL}/tests/{current_user.email}")
        if response.status_code == 200:
            tests = response.json()
            return jsonify(tests)
        else:
            return jsonify([])
    except Exception as e:
        print(f"Error getting tests: {e}")
        return jsonify([])

@learn_bp.route('/api/tests', methods=['POST'])
@login_required
def create_test():
    try:
        title = request.form.get('title')
        content = request.form.get('content')
        
        # Create test in storage API
        response = requests.post(
            f"{STORAGE_API_URL}/tests/{current_user.email}",
            json={
                'title': title,
                'content': content
            }
        )
        
        if response.status_code == 201:
            return jsonify({'message': 'Test created successfully'})
        else:
            return jsonify({'error': 'Failed to create test'}), 400
    except Exception as e:
        print(f"Error creating test: {e}")
        return jsonify({'error': str(e)}), 500

@learn_bp.route('/api/tests/<test_id>', methods=['PUT'])
@login_required
def update_test(test_id):
    try:
        title = request.form.get('title')
        content = request.form.get('content')
        
        # Update test in storage API
        response = requests.put(
            f"{STORAGE_API_URL}/tests/{current_user.email}/{test_id}",
            json={
                'title': title,
                'content': content
            }
        )
        
        if response.status_code == 200:
            return jsonify({'message': 'Test updated successfully'})
        else:
            return jsonify({'error': 'Failed to update test'}), 400
    except Exception as e:
        print(f"Error updating test: {e}")
        return jsonify({'error': str(e)}), 500

@learn_bp.route('/api/tests/<test_id>', methods=['DELETE'])
@login_required
def delete_test(test_id):
    try:
        # Delete test from storage API
        response = requests.delete(f"{STORAGE_API_URL}/tests/{current_user.email}/{test_id}")
        
        if response.status_code == 200:
            return jsonify({'message': 'Test deleted successfully'})
        else:
            return jsonify({'error': 'Failed to delete test'}), 400
    except Exception as e:
        print(f"Error deleting test: {e}")
        return jsonify({'error': str(e)}), 500

@learn_bp.route('/learn/<subject_key>')
@login_required
def subject_page(subject_key):
    if subject_key not in SUBJECTS:
        flash('Invalid subject', 'error')
        return redirect(url_for('learn.learn'))
    professors = get_professors_for_subject(subject_key)
    lessons = []
    tests = []
    for professor in professors:
        lessons_path = os.path.join(LECTII_DIR, subject_key, 'profesori', professor.email)
        if os.path.exists(lessons_path):
            for file in os.listdir(lessons_path):
                if file.endswith('.html'):
                    lesson_title = file.replace('.html', '')
                    lessons.append({
                        'title': lesson_title,
                        'professor': professor.name,
                        'professor_email': professor.email
                    })
        tests_path = os.path.join(TESTE_DIR, subject_key, 'profesori', professor.email)
        if os.path.exists(tests_path):
            for file in os.listdir(tests_path):
                if file.endswith('.json'):
                    test_name = file.replace('.json', '')
                    with open(os.path.join(tests_path, file), 'r') as tf:
                        test_data = json.load(tf)
                    tests.append({
                        'title': test_name,
                        'professor': professor.name,
                        'professor_email': professor.email,
                        'test_data': test_data
                    })
    return render_template('learn_subject.html',
                        user=current_user,
                        subject_key=subject_key,
                        subject_data=SUBJECTS[subject_key],
                        professors=professors,
                        lessons=lessons,
                        tests=tests)

@learn_bp.route('/learn/<subject_key>/<professor_email>')
@login_required
def professor_lessons(subject_key, professor_email):
    if subject_key not in SUBJECTS:
        flash('Invalid subject', 'error')
        return redirect(url_for('learn.index'))
    professor = User.query.filter_by(email=professor_email).first()
    if not professor:
        flash('Professor not found', 'error')
        return redirect(url_for('learn.subject_page', subject_key=subject_key))
    lessons = []
    lessons_path = os.path.join(LECTII_DIR, subject_key, 'profesori', professor_email)
    if os.path.exists(lessons_path):
        for file in os.listdir(lessons_path):
            if file.endswith('.html'):
                lesson_title = file.replace('.html', '')
                test_path = os.path.join(TESTE_DIR, subject_key, 'profesori', professor_email, f'{lesson_title}.json')
                has_test = os.path.exists(test_path)
                test_data = None
                if has_test:
                    with open(test_path, 'r') as tf:
                        test_data = json.load(tf)
                lessons.append({
                    'title': lesson_title,
                    'has_test': has_test,
                    'test_data': test_data
                })
    return render_template('professor_lessons.html',
                        user=current_user,
                        subject_key=subject_key,
                        subject_data=SUBJECTS[subject_key],
                        professor=professor,
                        professor_email=professor_email,
                        lessons=lessons)

@learn_bp.route('/subject/<subject_key>/professor/<professor_email>/lesson/<lesson_title>')
@login_required
def view_lesson(subject_key, professor_email, lesson_title):
    if subject_key not in SUBJECTS:
        flash('Invalid subject', 'error')
        return redirect(url_for('learn.learn'))
    professor = User.query.filter_by(email=professor_email).first()
    if not professor:
        flash('Professor not found', 'error')
        return redirect(url_for('learn.subject_page', subject_key=subject_key))
    lesson_content = get_lesson_content(subject_key, professor_email, lesson_title)
    if lesson_content is None:
        flash('Lesson not found', 'error')
        return redirect(url_for('learn.subject_page', subject_key=subject_key))
    test = get_test_for_lesson(subject_key, professor_email, lesson_title)
    return render_template('view_lesson.html',
                       user=current_user,
                       subject=SUBJECTS[subject_key]['name'],
                       subject_key=subject_key,
                       subject_color=SUBJECTS[subject_key]['color'],
                       subject_icon=SUBJECTS[subject_key]['icon'],
                       professor=professor,
                       professor_email=professor_email,
                       lesson_title=lesson_title,
                       content=lesson_content,
                       test=test,
                       is_professor=current_user.email == professor_email)

@learn_bp.route('/test/<subject_key>/<professor_email>/<lesson_title>', methods=['GET'])
@login_required
def take_test(subject_key, professor_email, lesson_title):
    if subject_key not in SUBJECTS:
        flash('Invalid subject', 'error')
        return redirect(url_for('learn.index'))

    # Try the new format first
    test_path = os.path.join(TESTE_DIR, subject_key, 'profesori', professor_email, f"{lesson_title}.json")
    if not os.path.exists(test_path):
        # Try the old format
        test_path = os.path.join(TESTE_DIR, subject_key, 'profesori', professor_email, f"{lesson_title}_test.json")
    if os.path.exists(test_path):
        with open(test_path, 'r') as f:
            test_data = json.load(f)
        return render_template('take_test.html',
                              user=current_user,
                              subject=subject_key,
                              test=test_data,
                              professor_email=professor_email,
                              lesson_title=lesson_title)
    else:
        flash('Test not found', 'error')
        return redirect(url_for('learn.subject_page', subject_key=subject_key))

@learn_bp.route('/test/<subject_key>/<professor_email>/<lesson_title>/submit', methods=['POST'])
@login_required
def submit_test(subject_key, professor_email, lesson_title):
    if subject_key not in SUBJECTS:
        flash('Invalid subject', 'error')
        return redirect(url_for('learn.learn'))

    try:
        # Get test data
        test_path = os.path.join(TESTE_DIR, subject_key, 'profesori', professor_email, f"{lesson_title}.json")
        if not os.path.exists(test_path):
            flash('Test not found', 'error')
            return redirect(url_for('learn.learn'))

        with open(test_path, 'r') as f:
            test_data = json.load(f)
        answers = request.form

        # Calculate score
        total_questions = len(test_data['questions'])
        correct_answers = 0
        for i, question in enumerate(test_data['questions']):
            answer_key = f'answer_{i}'
            if answer_key in answers and answers[answer_key] == str(question.get('correctIndex', '')):
                correct_answers += 1

        score = (correct_answers / total_questions) * 100 if total_questions > 0 else 0

        # Save result
        result = {
            'student_email': current_user.email,
            'professor_email': professor_email,
            'subject': subject_key,
            'lesson_title': lesson_title,
            'score': score,
            'total_questions': total_questions,
            'correct_answers': correct_answers,
            'submission_date': datetime.now().isoformat()
        }

        # Create results folder if it doesn't exist
        results_dir = os.path.join(TESTE_DIR, subject_key, 'profesori', professor_email, 'results')
        os.makedirs(results_dir, exist_ok=True)

        # Save result file
        result_path = os.path.join(results_dir, f"{lesson_title}_{current_user.email}.json")
        with open(result_path, 'w') as rf:
            json.dump(result, rf, indent=2)

        # Award XP to student after submitting test
        student = User.query.filter_by(email=current_user.email).first()
        if student:
            student.add_xp(10)  # You can adjust the XP amount here

        flash(f'Test submitted successfully. Your score: {score:.1f}%', 'success')
        return redirect(url_for('learn.view_results', subject_key=subject_key))

    except Exception as e:
        print(f"Error submitting test: {str(e)}")
        flash('Error submitting test', 'error')
        return redirect(url_for('learn.learn'))

@learn_bp.route('/results/<subject_key>', methods=['GET'])
@login_required
def view_results(subject_key):
    if subject_key not in SUBJECTS:
        flash('Invalid subject', 'error')
        return redirect(url_for('landing.index'))

    results = []
    try:
        professors = get_professors_for_subject(subject_key)
        for professor in professors:
            results_path = os.path.join(TESTE_DIR, subject_key, 'profesori', professor.email, 'results')
            if os.path.exists(results_path):
                for file in os.listdir(results_path):
                    if file.endswith('.json') and current_user.email in file:
                        with open(os.path.join(results_path, file), 'r') as rf:
                            result_data = json.load(rf)
                            results.append(result_data)
        return render_template('view_results.html',
                            user=current_user,
                            subject=subject_key,
                            results=results)
    except Exception as e:
        print(f"Error viewing results: {str(e)}")
        flash('Error viewing results', 'error')
        return redirect(url_for('landing.index'))

@learn_bp.route('/results/<subject_key>/<professor_email>/<lesson_title>/<student_email>', methods=['GET'])
@login_required
@require_professor
def view_student_result(subject_key, professor_email, lesson_title, student_email):
    if subject_key not in SUBJECTS:
        flash('Invalid subject', 'error')
        return redirect(url_for('studio.index'))
        
    try:
        # Get test data
        test_path = get_test_path(subject_key, professor_email, f"{lesson_title}.json")
        test_response = requests.get(f"{STORAGE_API_URL}/files/{test_path}")
        if test_response.status_code != 200:
            flash('Test not found', 'error')
            return redirect(url_for('studio.index'))
            
        # Get result data
        result_path = get_test_result_path(subject_key, professor_email, lesson_title, student_email)
        result_response = requests.get(f"{STORAGE_API_URL}/files/{result_path}")
        if result_response.status_code != 200:
            flash('Result not found', 'error')
            return redirect(url_for('studio.index'))
            
        test_data = test_response.json()
        result_data = result_response.json()
        
        return render_template('view_student_result.html',
                            user=current_user,
                            subject=subject_key,
                            test=test_data,
                            result=result_data)
                            
    except Exception as e:
        print(f"Error viewing student result: {str(e)}")
        flash('Error viewing student result', 'error')
        return redirect(url_for('studio.index')) 