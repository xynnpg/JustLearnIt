from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify
from flask_login import login_required, current_user
from app import db
from models import User, Lesson, Test
import os
import json
from datetime import datetime
import requests
from dotenv import load_dotenv

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

@learn_bp.route('/subject/<subject_key>/professor/<professor_email>/lesson/<lesson_title>/test')
@login_required
def take_test(subject_key, professor_email, lesson_title):
    """Take a test for a specific lesson"""
    subject_data = None
    for key, data in SUBJECTS.items():
        if key.lower() == subject_key.lower():
            subject_data = data
            subject_key = key
            break

    if not subject_data:
        flash('Invalid subject', 'error')
        return redirect(url_for('account.account'))

    try:
        # Get test from storage API
        response = requests.get(f"{STORAGE_API_URL}/files/teste/{subject_key}/profesori/{professor_email}/{lesson_title}_test.json")
        if response.status_code == 200:
            test = response.json()
            return render_template('take_test.html',
                                 subject=subject_data['name'],
                                 subject_key=subject_key,
                                 subject_color=subject_data['color'],
                                 subject_icon=subject_data['icon'],
                                 lesson_title=lesson_title,
                                 professor_email=professor_email,
                                 test=test)
        else:
            flash('Test not found', 'error')
            return redirect(url_for('learn.view_lesson',
                                  subject_key=subject_key,
                                  professor_email=professor_email,
                                  lesson_title=lesson_title))
    except Exception as e:
        print(f"Error getting test: {e}")
        flash('Error loading test', 'error')
        return redirect(url_for('learn.view_lesson',
                              subject_key=subject_key,
                              professor_email=professor_email,
                              lesson_title=lesson_title))

@learn_bp.route('/subject/<subject_key>/professor/<professor_email>/lesson/<lesson_title>/test/submit', methods=['POST'])
@login_required
def submit_test(subject_key, professor_email, lesson_title):
    """Submit test answers"""
    subject_data = None
    for key, data in SUBJECTS.items():
        if key.lower() == subject_key.lower():
            subject_data = data
            subject_key = key
            break

    if not subject_data:
        flash('Invalid subject', 'error')
        return redirect(url_for('account.account'))

    try:
        # Get test from storage API
        response = requests.get(f"{STORAGE_API_URL}/files/teste/{subject_key}/profesori/{professor_email}/{lesson_title}_test.json")
        if response.status_code == 200:
            test = response.json()
        else:
            flash('Test not found', 'error')
            return redirect(url_for('learn.professor_lessons',
                                  subject_key=subject_key,
                                  professor_email=professor_email))
    except Exception as e:
        print(f"Error getting test: {e}")
        flash('Error loading test', 'error')
        return redirect(url_for('learn.professor_lessons',
                              subject_key=subject_key,
                              professor_email=professor_email))

    answers = {}
    for i, question in enumerate(test['questions']):
        if question['type'] == 'multiple_choice':
            answer = request.form.get(f'question_{i}')
            if answer is not None:
                answers[str(i)] = str(answer)
        elif question['type'] in ['short_answer', 'essay']:
            answers[str(i)] = request.form.get(f'question_{i}')

    score = 0
    total = len(test['questions'])
    graded_questions = 0
    for i, question in enumerate(test['questions']):
        if question['type'] == 'multiple_choice':
            if str(answers.get(str(i))) == str(question.get('correctIndex')):
                score += 1
            graded_questions += 1

    # Convert score to 1-10 scale
    if total > 0:
        score_10_scale = 1 + (score / total) * 9  # This ensures score is between 1 and 10
    else:
        score_10_scale = 1

    # Save test result
    result = {
        'student_email': current_user.email,
        'lesson_title': lesson_title,
        'score': round(score_10_scale, 1),  # Round to 1 decimal place
        'total': 10,  # Always show out of 10
        'raw_score': score,
        'raw_total': total,
        'graded_questions': graded_questions,
        'answers': answers,
        'timestamp': datetime.now().isoformat(),
        'status': 'pending' if graded_questions < total else 'graded'
    }

    try:
        # Save result in storage API
        response = requests.post(
            f"{STORAGE_API_URL}/files/teste/{subject_key}/profesori/{professor_email}/results/{lesson_title}_{current_user.email}.json",
            json=result
        )
        if response.status_code != 201:
            print(f"Error saving test result: {response.text}")
            flash('Error saving test result', 'error')
    except Exception as e:
        print(f"Error saving test result: {e}")
        flash('Error saving test result', 'error')

    try:
        # Save grade in storage API
        grade_data = {
            'subject': subject_key,
            'test_title': lesson_title,
            'professor_email': professor_email,
            'score': round(score_10_scale, 1),
            'date': datetime.now().isoformat(),
            'type': 'test'
        }
        response = requests.post(
            f"{STORAGE_API_URL}/files/grades/{current_user.email}/test_{subject_key}_{lesson_title}.json",
            json=grade_data
        )
        if response.status_code != 201:
            print(f"Error saving grade: {response.text}")
            flash('Error saving grade', 'error')
    except Exception as e:
        print(f"Error saving grade: {e}")
        flash('Error saving grade', 'error')

    # Instead of redirecting to professor lessons, show the test results
    return render_template('learn_test_results.html',
                         subject=subject_data['name'],
                         subject_key=subject_key,
                         subject_color=subject_data['color'],
                         subject_icon=subject_data['icon'],
                         test_title=lesson_title,
                         professor_email=professor_email,
                         lesson_title=lesson_title,
                         score=result['score'],
                         raw_score=result['raw_score'],
                         raw_total=result['raw_total'],
                         completed_at=datetime.now().strftime('%Y-%m-%d %H:%M'))

@learn_bp.route('/subject/<subject_key>/professor/<professor_email>/test-results')
@login_required
def view_test_results(subject_key, professor_email):
    """View test results for professors and admins"""
    subject_data = None
    for key, data in SUBJECTS.items():
        if key.lower() == subject_key.lower():
            subject_data = data
            subject_key = key
            break

    if not subject_data:
        flash('Invalid subject', 'error')
        return redirect(url_for('account.account'))

    if not current_user.is_admin and current_user.email != professor_email:
        flash('You do not have permission to view these results', 'error')
        return redirect(url_for('learn.subject_page', subject_key=subject_key))

    results = []
    try:
        # Get test results from storage API
        response = requests.get(f"{STORAGE_API_URL}/folders/teste/{subject_key}/profesori/{professor_email}/results")
        if response.status_code == 200:
            result_files = response.json()
            for result_file in result_files:
                if result_file['type'] == 'file' and result_file['name'].endswith('.json'):
                    # Get individual result file
                    result_response = requests.get(f"{STORAGE_API_URL}/files/teste/{subject_key}/profesori/{professor_email}/results/{result_file['name']}")
                    if result_response.status_code == 200:
                        result_data = result_response.json()

                        student = User.query.filter_by(email=result_data['student_email']).first()
                        student_name = student.name if student else result_data['student_email']

                        results.append({
                            'student_name': student_name,
                            'student_email': result_data['student_email'],
                            'lesson_title': result_data['lesson_title'],
                            'score': result_data['score'],
                            'total': result_data['total'],
                            'timestamp': result_data['timestamp']
                        })
    except Exception as e:
        print(f"Error getting test results: {e}")
        flash('Error loading test results', 'error')

    results.sort(key=lambda x: x['timestamp'], reverse=True)

    return render_template('test_results.html',
                         subject=subject_data['name'],
                         subject_key=subject_key,
                         subject_color=subject_data['color'],
                         subject_icon=subject_data['icon'],
                         professor_email=professor_email,
                         results=results)

@learn_bp.route('/subject/<subject_key>/professor/<professor_email>/lesson/<lesson_title>/student/<student_email>/result')
@login_required
def view_test_result(subject_key, professor_email, lesson_title, student_email):
    """View detailed test result for a specific student"""
    subject_data = None
    for key, data in SUBJECTS.items():
        if key.lower() == subject_key.lower():
            subject_data = data
            subject_key = key
            break

    if not subject_data:
        flash('Invalid subject', 'error')
        return redirect(url_for('account.account'))

    if not current_user.is_admin and current_user.email != professor_email:
        flash('You do not have permission to view these results', 'error')
        return redirect(url_for('learn.subject_page', subject_key=subject_key))

    try:
        # Get test result from storage API
        result_response = requests.get(f"{STORAGE_API_URL}/files/teste/{subject_key}/profesori/{professor_email}/results/{lesson_title}_{student_email}.json")
        if result_response.status_code != 200:
            flash('Test result not found', 'error')
            return redirect(url_for('learn.view_test_results',
                                  subject_key=subject_key,
                                  professor_email=professor_email))
        result = result_response.json()

        # Get original test from storage API
        test_response = requests.get(f"{STORAGE_API_URL}/files/teste/{subject_key}/profesori/{professor_email}/{lesson_title}_test.json")
        if test_response.status_code != 200:
            flash('Original test not found', 'error')
            return redirect(url_for('learn.view_test_results',
                                  subject_key=subject_key,
                                  professor_email=professor_email))
        test = test_response.json()

        student = User.query.filter_by(email=student_email).first()
        student_name = student.name if student else student_email

        return render_template('view_test_result.html',
                             subject=subject_data['name'],
                             subject_key=subject_key,
                             subject_color=subject_data['color'],
                             subject_icon=subject_data['icon'],
                             professor_email=professor_email,
                             lesson_title=lesson_title,
                             student_name=student_name,
                             student_email=student_email,
                             result=result,
                             test=test)
    except Exception as e:
        print(f"Error getting test result: {e}")
        flash('Error loading test result', 'error')
        return redirect(url_for('learn.view_test_results',
                              subject_key=subject_key,
                              professor_email=professor_email))