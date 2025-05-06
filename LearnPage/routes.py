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

def get_lessons_for_subject(subject):
    """Get all lessons for a subject"""
    try:
        lessons = []
        professors = get_professors_for_subject(subject)
        print(f"Found {len(professors)} professors for subject {subject}")
        
        for professor in professors:
            print(f"\nProcessing professor: {professor.email}")
            # Get lessons for this professor
            response = requests.get(f"{STORAGE_API_URL}/folders/lectii/{subject}/profesori/{professor.email}")
            if response.status_code == 200:
                files = response.json()
                print(f"Found {len(files)} files for professor {professor.email}")
                for file in files:
                    if file['type'] == 'file' and file['name'].endswith('.html'):
                        lesson_title = file['name'].replace('.html', '')
                        print(f"\nProcessing lesson: {lesson_title}")
                        
                        # Get all test files for this professor
                        test_folder_response = requests.get(f"{STORAGE_API_URL}/folders/teste/{subject}/profesori/{professor.email}")
                        has_test = False
                        test_data = None
                        
                        if test_folder_response.status_code == 200:
                            test_files = test_folder_response.json()
                            print(f"Found {len(test_files)} test files for professor {professor.email}")
                            
                            # Check each test file
                            for test_file in test_files:
                                if test_file['type'] == 'file' and test_file['name'].endswith('.json'):
                                    test_name = test_file['name'].replace('.json', '')
                                    print(f"Checking test file: {test_name} against lesson: {lesson_title}")
                                    
                                    # Try to get test data
                                    test_path = f"teste/{subject}/profesori/{professor.email}/{test_file['name']}"
                                    print(f"Requesting test data from: {STORAGE_API_URL}/files/{test_path}")
                                    test_data_response = requests.get(f"{STORAGE_API_URL}/files/{test_path}")
                                    print(f"Test data response status: {test_data_response.status_code}")
                                    
                                    if test_data_response.status_code == 200:
                                        test_data = test_data_response.json()
                                        has_test = True
                                        print(f"Found test data for lesson {lesson_title}")
                                        break
                                    else:
                                        print(f"Failed to get test data: {test_data_response.text}")
                        else:
                            print(f"Failed to get test folder: {test_folder_response.text}")
                        
                        lessons.append({
                            'title': lesson_title,
                            'professor': professor.name,
                            'professor_email': professor.email,
                            'has_test': has_test,
                            'test_data': test_data
                        })

        print(f"\nReturning {len(lessons)} lessons")
        return lessons
    except Exception as e:
        print(f"Error getting lessons: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

def get_lesson_content(subject_key, professor_email, lesson_title):
    """Get content of a specific lesson"""
    try:
        url = f"{STORAGE_API_URL}/folders/lectii/{subject_key}/profesori/{professor_email}/{lesson_title}.html"
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
    try:
        test_path = f"teste/{subject_key}/profesori/{professor_email}/{lesson_title}.json"
        response = requests.get(f"{STORAGE_API_URL}/files/{test_path}")
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"Error getting test: {str(e)}")
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
    # Get test results for all subjects
    all_results = {}
    for subject_key in SUBJECTS:
        results = []
        try:
            # Get all professors
            response = requests.get(f"{STORAGE_API_URL}/folders/teste/{subject_key}/profesori")
            if response.status_code == 200:
                professors = [item for item in response.json() if item['type'] == 'folder']
                
                for professor in professors:
                    professor_email = professor['name']
                    results_response = requests.get(f"{STORAGE_API_URL}/folders/teste/{subject_key}/profesori/{professor_email}/results")
                    if results_response.status_code == 200:
                        result_files = [item for item in results_response.json() if item['type'] == 'file']
                        
                        for result_file in result_files:
                            if current_user.email in result_file['name']:
                                result_response = requests.get(f"{STORAGE_API_URL}/files/teste/{subject_key}/profesori/{professor_email}/results/{result_file['name']}")
                                if result_response.status_code == 200:
                                    result_data = result_response.json()
                                    results.append(result_data)
        except Exception as e:
            print(f"Error getting results for {subject_key}: {str(e)}")
            continue
            
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
        
    try:
        # Get professors for this subject
        professors = get_professors_for_subject(subject_key)
        print(f"Found {len(professors)} professors for subject {subject_key}")
        
        # Get lessons and tests for this subject
        lessons = []
        tests = []
        
        for professor in professors:
            print(f"\nProcessing professor: {professor.email}")
            
            # Get lessons for this professor
            response = requests.get(f"{STORAGE_API_URL}/folders/lectii/{subject_key}/profesori/{professor.email}")
            if response.status_code == 200:
                files = response.json()
                print(f"Found {len(files)} lesson files for professor {professor.email}")
                for file in files:
                    if file['type'] == 'file' and file['name'].endswith('.html'):
                        lesson_title = file['name'].replace('.html', '')
                        print(f"\nProcessing lesson: {lesson_title}")
                        lessons.append({
                            'title': lesson_title,
                            'professor': professor.name,
                            'professor_email': professor.email
                        })
            
            # Get tests for this professor
            test_folder_response = requests.get(f"{STORAGE_API_URL}/folders/teste/{subject_key}/profesori/{professor.email}")
            if test_folder_response.status_code == 200:
                test_files = test_folder_response.json()
                print(f"Found {len(test_files)} test files for professor {professor.email}")
                for test_file in test_files:
                    if test_file['type'] == 'file' and test_file['name'].endswith('.json'):
                        test_name = test_file['name'].replace('.json', '')
                        print(f"Processing test: {test_name}")
                        
                        # Get test data
                        test_path = f"teste/{subject_key}/profesori/{professor.email}/{test_file['name']}"
                        test_response = requests.get(f"{STORAGE_API_URL}/files/{test_path}")
                        
                        if test_response.status_code == 200:
                            test_data = test_response.json()
                            tests.append({
                                'title': test_name,
                                'professor': professor.name,
                                'professor_email': professor.email,
                                'test_data': test_data
                            })
        
        print(f"\nReturning {len(lessons)} lessons and {len(tests)} tests")
        return render_template('learn_subject.html',
                            user=current_user,
                            subject_key=subject_key,
                            subject_data=SUBJECTS[subject_key],
                            professors=professors,
                            lessons=lessons,
                            tests=tests)
    except Exception as e:
        print(f"Error loading subject page: {str(e)}")
        import traceback
        traceback.print_exc()
        flash('Error loading subject page', 'error')
        return redirect(url_for('learn.learn'))

@learn_bp.route('/learn/<subject_key>/<professor_email>')
@login_required
def professor_lessons(subject_key, professor_email):
    if subject_key not in SUBJECTS:
        flash('Invalid subject', 'error')
        return redirect(url_for('learn.index'))
        
    try:
        # Get professor info
        professor = User.query.filter_by(email=professor_email).first()
        if not professor:
            flash('Professor not found', 'error')
            return redirect(url_for('learn.subject_page', subject_key=subject_key))
            
        # Get lessons for this professor
        lessons_url = f"{STORAGE_API_URL}/folders/lectii/{subject_key}/profesori/{professor_email}"
        response = requests.get(lessons_url)
        
        lessons = []
        if response.status_code == 200:
            files = response.json()
            for file in files:
                if file['type'] == 'file' and file['name'].endswith('.html'):
                    lesson_title = file['name'].replace('.html', '')
                    
                    # Check if there's a test for this lesson
                    test_path = f"teste/{subject_key}/profesori/{professor_email}/{lesson_title}.json"
                    test_response = requests.get(f"{STORAGE_API_URL}/files/{test_path}")
                    has_test = test_response.status_code == 200
                    
                    # Also check old format
                    if not has_test:
                        old_test_path = f"teste/{subject_key}/profesori/{professor_email}/{lesson_title}_test.json"
                        old_test_response = requests.get(f"{STORAGE_API_URL}/files/{old_test_path}")
                        has_test = old_test_response.status_code == 200
                    
                    # Get test data if it exists
                    test_data = None
                    if has_test:
                        if test_response.status_code == 200:
                            test_data = test_response.json()
                        else:
                            test_data = old_test_response.json()
                    
                    lessons.append({
                        'title': lesson_title,
                        'path': file['path'],
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
    except Exception as e:
        print(f"Error loading professor lessons: {str(e)}")
        flash('Error loading professor lessons', 'error')
        return redirect(url_for('learn.subject_page', subject_key=subject_key))

@learn_bp.route('/subject/<subject_key>/professor/<professor_email>/lesson/<lesson_title>')
@login_required
def view_lesson(subject_key, professor_email, lesson_title):
    if subject_key not in SUBJECTS:
        flash('Invalid subject', 'error')
        return redirect(url_for('learn.learn'))
        
    try:
        # Get professor info
        professor = User.query.filter_by(email=professor_email).first()
        if not professor:
            flash('Professor not found', 'error')
            return redirect(url_for('learn.subject_page', subject_key=subject_key))
            
        # Get lesson content
        lesson_path = f"lectii/{subject_key}/profesori/{professor_email}/{lesson_title}.html"
        response = requests.get(f"{STORAGE_API_URL}/files/{lesson_path}")
        
        if response.status_code != 200:
            flash('Lesson not found', 'error')
            return redirect(url_for('learn.subject_page', subject_key=subject_key))
            
        lesson_content = response.text
            
        # Check if there's a test for this lesson
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

    except Exception as e:
        print(f"Error viewing lesson: {str(e)}")
        flash('Error viewing lesson', 'error')
        return redirect(url_for('learn.subject_page', subject_key=subject_key))

@learn_bp.route('/test/<subject_key>/<professor_email>/<lesson_title>', methods=['GET'])
@login_required
def take_test(subject_key, professor_email, lesson_title):
    if subject_key not in SUBJECTS:
        flash('Invalid subject', 'error')
        return redirect(url_for('learn.index'))

    try:
        # Try the new format first
        test_path = f"teste/{subject_key}/profesori/{professor_email}/{lesson_title}.json"
        response = requests.get(f"{STORAGE_API_URL}/files/{test_path}")
        
        # If not found, try the old format
        if response.status_code != 200:
            test_path = f"teste/{subject_key}/profesori/{professor_email}/{lesson_title}_test.json"
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
            return redirect(url_for('learn.subject_page', subject_key=subject_key))
            
    except Exception as e:
        print(f"Error loading test: {str(e)}")
        flash('Error loading test', 'error')
        return redirect(url_for('learn.subject_page', subject_key=subject_key))

@learn_bp.route('/test/<subject_key>/<professor_email>/<lesson_title>/submit', methods=['POST'])
@login_required
def submit_test(subject_key, professor_email, lesson_title):
    if subject_key not in SUBJECTS:
        flash('Invalid subject', 'error')
        return redirect(url_for('learn.index'))

    try:
        # Get test data
        test_path = get_test_path(subject_key, professor_email, f"{lesson_title}.json")
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
            if answer_key in answers and answers[answer_key] == str(question['correctIndex']):
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
        return redirect(url_for('landing.index'))

    results = []
    try:
        # Get all professors
        response = requests.get(f"{STORAGE_API_URL}/folders/teste/{subject_key}/profesori")
        if response.status_code == 200:
            professors = [item for item in response.json() if item['type'] == 'folder']
            
            for professor in professors:
                professor_email = professor['name']
                results_response = requests.get(f"{STORAGE_API_URL}/folders/teste/{subject_key}/profesori/{professor_email}/results")
                if results_response.status_code == 200:
                    result_files = [item for item in results_response.json() if item['type'] == 'file']
                    
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