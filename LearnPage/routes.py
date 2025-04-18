from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify
from flask_login import login_required, current_user
from app import db
from models import User, Lesson, Test
import os
import json
from datetime import datetime
import requests
from dotenv import load_dotenv
from io import BytesIO
from functools import wraps

# Load environment variables
load_dotenv()

STORAGE_API_URL = os.getenv('STORAGE_API_URL', 'http://localhost:5000/api')

learn_bp = Blueprint('learn', __name__,
                     template_folder='../Templates',
                     static_folder='../static/learn')

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, '../instance')
LECTII_DIR = os.path.join(INSTANCE_DIR, 'lectii')
TESTE_DIR = os.path.join(INSTANCE_DIR, 'teste')

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

def get_professors_for_subject(subject_key):
    """Get approved professors for a subject"""
    subject_name = SUBJECTS.get(subject_key, {}).get('name', '')
    if not subject_name:
        return []

    professors = User.query.filter_by(
        user_type='profesor',
        is_professor_approved=True
    ).all()

    return [p for p in professors if p.subject and p.subject.lower() == subject_name.lower()]

def get_lessons_for_subject(subject_key):
    """Get all lessons for a subject"""
    lessons = []
    print(f"Getting lessons for subject: {subject_key}")

    subject_dir_name = None
    for key, data in SUBJECTS.items():
        if key.lower() == subject_key.lower():
            subject_dir_name = key
            break

    if not subject_dir_name:
        print(f"Subject not found: {subject_key}")
        return lessons

    try:
        # Get all professors for this subject
        professors_url = f"{STORAGE_API_URL}/folders/lectii/{subject_dir_name}/profesori"
        print(f"Fetching professors from: {professors_url}")
        response = requests.get(professors_url)
        print(f"Professors response: {response.status_code}")
        print(f"Professors response content: {response.text}")
        
        if response.status_code == 404:
            print("Professors directory does not exist yet")
            return lessons
        elif response.status_code == 200:
            professors = response.json()
            print(f"Found {len(professors)} professors")
            
            for professor in professors:
                if professor['type'] == 'folder':
                    professor_email = professor['name']
                    print(f"Getting lessons for professor: {professor_email}")
                    
                    # Get lessons for this professor
                    lessons_url = f"{STORAGE_API_URL}/folders/lectii/{subject_dir_name}/profesori/{professor_email}"
                    print(f"Fetching lessons from: {lessons_url}")
                    prof_response = requests.get(lessons_url)
                    print(f"Lessons response: {prof_response.status_code}")
                    print(f"Lessons response content: {prof_response.text}")
                    
                    if prof_response.status_code == 404:
                        print(f"No lessons directory for professor {professor_email}")
                        continue
                    elif prof_response.status_code == 200:
                        prof_lessons = prof_response.json()
                        print(f"Found {len(prof_lessons)} lessons")
                        
                        for lesson in prof_lessons:
                            if lesson['type'] == 'file' and lesson['name'].endswith('.html'):
                                professor_user = User.query.filter_by(email=professor_email).first()
                                professor_name = professor_user.name if professor_user else professor_email
                                lessons.append({
                                    'professor': professor_name,
                                    'professor_email': professor_email,
                                    'title': lesson['name'].replace('.html', ''),
                                    'path': lesson['path']
                                })
                                print(f"Added lesson: {lesson['name']}")
                    else:
                        print(f"Error getting lessons for professor {professor_email}: {prof_response.text}")
        else:
            print(f"Error getting professors: {response.text}")
    except Exception as e:
        print(f"Error getting lessons for subject {subject_key}: {str(e)}")
        import traceback
        traceback.print_exc()
        return lessons

    print(f"Returning {len(lessons)} lessons")
    return lessons

def get_lesson_content(subject_key, professor_email, lesson_title):
    """Get content of a specific lesson"""
    try:
        url = f"{STORAGE_API_URL}/files/lectii/{subject_key}/profesori/{professor_email}/{lesson_title}.html"
        print(f"Fetching lesson content from: {url}")
        response = requests.get(url)
        print(f"Lesson content response: {response.status_code}")
        
        if response.status_code == 404:
            print("Lesson file does not exist")
            return None
        elif response.status_code == 200:
            print("Successfully retrieved lesson content")
            return response.text
        else:
            print(f"Error getting lesson content: {response.text}")
            return None
    except Exception as e:
        print(f"Error getting lesson content: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def get_test_for_lesson(subject_key, professor_email, lesson_title):
    """Get test for a specific lesson"""

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

def get_professor_path(subject, content_type='lectii'):
    return f"{content_type}/{subject}/profesori/{current_user.email}"

def get_test_path(subject, professor_email, test_name):
    return f"teste/{subject}/profesori/{professor_email}/{test_name}"

def get_test_result_path(subject, professor_email, test_name, student_email):
    return f"teste/{subject}/profesori/{professor_email}/results/{test_name}_{student_email}.json"

@learn_bp.route('/learn')
@login_required
def learn():
    return render_template('learn.html')

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
        questions = request.form.get('questions')
        
        # Create test in storage API
        response = requests.post(
            f"{STORAGE_API_URL}/tests/{current_user.email}",
            json={
                'title': title,
                'questions': questions
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
        questions = request.form.get('questions')
        
        # Update test in storage API
        response = requests.put(
            f"{STORAGE_API_URL}/tests/{current_user.email}/{test_id}",
            json={
                'title': title,
                'questions': questions
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
    """Main subject page showing professors and lessons"""

    subject_data = None
    for key, data in SUBJECTS.items():
        if key.lower() == subject_key.lower():
            subject_data = data
            subject_key = key
            break

    if not subject_data:
        flash('Invalid subject selected', 'error')
        return redirect(url_for('account.account'))

    professors = get_professors_for_subject(subject_key)
    lessons = get_lessons_for_subject(subject_key)

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

                            professor = User.query.filter_by(email=professor_dir).first()
                            professor_name = professor.name if professor else professor_dir

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
    subject_data = None
    for key, data in SUBJECTS.items():
        if key.lower() == subject_key.lower():
            subject_data = data
            subject_key = key
            break

    if not subject_data:
        flash('Invalid subject selected', 'error')
        return redirect(url_for('account.account'))

    professor = User.query.filter_by(email=professor_email).first()
    if not professor or not professor.is_professor_approved:
        flash('Professor not found', 'error')
        return redirect(url_for('learn.subject_page', subject_key=subject_key))

    lessons = []
    try:
        # Get lessons from storage API
        response = requests.get(f"{STORAGE_API_URL}/folders/lectii/{subject_key}/profesori/{professor_email}")
        if response.status_code == 200:
            files = response.json()
            for file in files:
                if file['type'] == 'file' and file['name'].endswith('.html'):
                    lessons.append({
                        'title': file['name'].replace('.html', ''),
                        'path': file['path']
                    })
    except Exception as e:
        print(f"Error getting lessons for professor {professor_email}: {e}")

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
    subject_data = None
    for key, data in SUBJECTS.items():
        if key.lower() == subject_key.lower():
            subject_data = data
            subject_key = key
            break

    if not subject_data:
        flash('Invalid subject', 'error')
        return redirect(url_for('account.account'))

    professor = User.query.filter_by(email=professor_email).first()
    if not professor or not professor.is_professor_approved:
        flash('Professor not found', 'error')
        return redirect(url_for('learn.subject_page', subject_key=subject_key))

    try:
        # Get lesson content from storage API
        response = requests.get(f"{STORAGE_API_URL}/files/lectii/{subject_key}/profesori/{professor_email}/{lesson_title}.html")
        if response.status_code == 200:
            lesson_content = response.text
        else:
            flash('Lesson not found', 'error')
            return redirect(url_for('learn.professor_lessons', subject_key=subject_key, professor_email=professor_email))
    except Exception as e:
        print(f"Error getting lesson content: {e}")
        flash('Error loading lesson', 'error')
        return redirect(url_for('learn.professor_lessons', subject_key=subject_key, professor_email=professor_email))

    return render_template('view_lesson.html',
                           subject=subject_data['name'],
                           subject_key=subject_key,
                           subject_color=subject_data['color'],
                           subject_icon=subject_data['icon'],
                           professor=professor,
                           lesson_title=lesson_title,
                           lesson_content=lesson_content)

@learn_bp.route('/test/<subject_key>/<professor_email>/<lesson_title>', methods=['GET'])
@login_required
def take_test(subject_key, professor_email, lesson_title):
    if subject_key not in SUBJECTS:
        flash('Invalid subject', 'error')
        return redirect(url_for('learn.index'))

    try:
        test_path = get_test_path(subject_key, professor_email, f"{lesson_title}_test.json")
        response = requests.get(f"{STORAGE_API_URL}/files/{test_path}")
        if response.status_code == 200:
            test_data = response.json()
            return render_template('take_test.html',
                                user=current_user,
                                subject=subject_key,
                                test=test_data,
                                professor_email=professor_email,
                                lesson_title=lesson_title)
        else:
            flash('Test not found', 'error')
            return redirect(url_for('learn.index'))
            
    except Exception as e:
        print(f"Error loading test: {str(e)}")
        flash('Error loading test', 'error')
        return redirect(url_for('learn.index'))

@learn_bp.route('/test/<subject_key>/<professor_email>/<lesson_title>/submit', methods=['POST'])
@login_required
def submit_test(subject_key, professor_email, lesson_title):
    if subject_key not in SUBJECTS:
        flash('Invalid subject', 'error')
        return redirect(url_for('learn.index'))

    try:
        # Get test data
        test_path = get_test_path(subject_key, professor_email, f"{lesson_title}_test.json")
        response = requests.get(f"{STORAGE_API_URL}/files/{test_path}")
        if response.status_code != 200:
            flash('Test not found', 'error')
            return redirect(url_for('learn.index'))
            
        test_data = response.json()
        answers = request.form
        
        # Calculate score
        total_questions = len(test_data['questions'])
        correct_answers = 0
        for i, question in enumerate(test_data['questions']):
            answer_key = f'answer_{i}'
            if answer_key in answers and answers[answer_key] == question['correct_answer']:
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
        response = requests.post(f"{STORAGE_API_URL}/folders", 
                               json={'name': 'results', 
                                     'parent_path': f"teste/{subject_key}/profesori/{professor_email}"})
        
        # Save result file
        result_path = get_test_result_path(subject_key, professor_email, lesson_title, current_user.email)
        file_content = BytesIO(json.dumps(result, indent=2).encode('utf-8'))
        file_content.name = f"{lesson_title}_{current_user.email}.json"
        files = {'file': (file_content.name, file_content, 'application/json')}
        data = {'folder_path': f"teste/{subject_key}/profesori/{professor_email}/results"}
        response = requests.post(f"{STORAGE_API_URL}/files", files=files, data=data)
        
        if response.status_code == 201:
            flash(f'Test submitted successfully. Your score: {score:.1f}%', 'success')
        else:
            flash('Error saving test result', 'error')
            
        return redirect(url_for('learn.view_results', subject_key=subject_key))
        
    except Exception as e:
        print(f"Error submitting test: {str(e)}")
        flash('Error submitting test', 'error')
        return redirect(url_for('learn.index'))

@learn_bp.route('/results/<subject_key>', methods=['GET'])
@login_required
def view_results(subject_key):
    if subject_key not in SUBJECTS:
        flash('Invalid subject', 'error')
        return redirect(url_for('learn.index'))
        
    try:
        results = []
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
                    
                    # Filter results for current user
                    for result_file in result_files:
                        if current_user.email in result_file['name']:
                            result_response = requests.get(f"{STORAGE_API_URL}/files/teste/{subject_key}/profesori/{professor_email}/results/{result_file['name']}")
                            if result_response.status_code == 200:
                                result_data = result_response.json()
                                results.append(result_data)
                                
        return render_template('view_results.html',
                            user=current_user,
                            subject=subject_key,
                            results=results)
                            
    except Exception as e:
        print(f"Error viewing results: {str(e)}")
        flash('Error viewing results', 'error')
        return redirect(url_for('learn.index'))

@learn_bp.route('/results/<subject_key>/<professor_email>/<lesson_title>/<student_email>', methods=['GET'])
@login_required
@require_professor
def view_student_result(subject_key, professor_email, lesson_title, student_email):
    if subject_key not in SUBJECTS:
        flash('Invalid subject', 'error')
        return redirect(url_for('studio.index'))
        
    try:
        # Get test data
        test_path = get_test_path(subject_key, professor_email, f"{lesson_title}_test.json")
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