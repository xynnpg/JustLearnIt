from flask import render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from flask_login import login_required, current_user
from datetime import datetime
import os
import json
from functools import wraps
from . import studio_bp
from flask_login import current_user
from flask_sqlalchemy import SQLAlchemy
from models import User, Lesson
import uuid
import requests
from dotenv import load_dotenv
from io import BytesIO

# Load environment variables
load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, '../instance')
STORAGE_API_URL = os.getenv('STORAGE_API_URL', 'http://localhost:5000/api')

SUBJECTS = {
    'Bio': {
        'name': 'Biology',
        'key': 'Bio',
        'color': '#28a745',
        'icon': 'fas fa-dna'
    },
    'Isto': {
        'name': 'History',
        'key': 'Isto',
        'color': '#dc3545',
        'icon': 'fas fa-landmark'
    },
    'Geogra': {
        'name': 'Geography',
        'key': 'Geogra',
        'color': '#17a2b8',
        'icon': 'fas fa-globe-americas'
    }
}

def require_professor(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.user_type != 'profesor' or not current_user.is_professor_approved:
            flash('You must be an approved professor to access this page.', 'error')
            return redirect(url_for('landing.index'))
        return f(*args, **kwargs)
    return decorated_function

def get_professor_path(subject, content_type='lectii'):
    """Get professor-specific path for a subject"""
    if not current_user.is_authenticated:
        return None
    return f"{content_type}/{subject}/profesori/{current_user.email}"

@studio_bp.route('/')
@login_required
@require_professor
def studio():
    lesson_count = 0
    test_count = 0
    student_count = 0
    try:
        for subject_key in SUBJECTS:
            lectii_path = get_professor_path(subject_key)
            teste_path = get_professor_path(subject_key, 'teste')
            
            # Get lessons count
            response = requests.get(f"{STORAGE_API_URL}/folders/{lectii_path}")
            if response.status_code == 200:
                contents = response.json()
                lesson_count += len([f for f in contents if f['type'] == 'file' and f['name'].endswith('.html')])
            
            # Get tests count
            response = requests.get(f"{STORAGE_API_URL}/folders/{teste_path}")
            if response.status_code == 200:
                contents = response.json()
                test_count += len([f for f in contents if f['type'] == 'file' and f['name'].endswith('.json')])
    except Exception as e:
        flash('Error counting lessons and tests', 'error')

    return render_template('studio_dashboard.html',
                         user=current_user,
                         subjects=SUBJECTS,
                         total_lessons=lesson_count,
                         total_tests=test_count,
                         total_students=student_count)

@studio_bp.route('/upload-video', methods=['POST'])
@login_required
@require_professor
def upload_video():
    print("Upload video request received")
    if 'video' not in request.files:
        print("No video file in request")
        return jsonify({'success': False, 'message': 'No video file provided'}), 400
    
    video = request.files['video']
    if video.filename == '':
        print("Empty filename")
        return jsonify({'success': False, 'message': 'No video file selected'}), 400
    
    if not video.filename.lower().endswith(('.mp4', '.webm', '.ogg')):
        print(f"Invalid file format: {video.filename}")
        return jsonify({'success': False, 'message': 'Invalid video format. Supported formats: MP4, WebM, OGG'}), 400
    
    try:
        # Create a unique filename
        filename = f"{uuid.uuid4()}_{video.filename}"
        print(f"Generated filename: {filename}")
        
        # Create videos folder in storage API
        response = requests.post(f"{STORAGE_API_URL}/folders", json={'name': 'videos', 'parent_path': ''})
        if response.status_code != 201:
            print(f"Error creating videos folder: {response.text}")
            return jsonify({'success': False, 'message': 'Error creating videos folder'}), 500
        
        # Upload the video to storage API
        files = {'file': (filename, video)}
        data = {'folder_path': 'videos'}
        response = requests.post(f"{STORAGE_API_URL}/files", files=files, data=data)
        
        if response.status_code != 201:
            print(f"Error uploading video: {response.text}")
            return jsonify({'success': False, 'message': 'Error uploading video'}), 500
        
        # Return the URL for the video
        video_url = f"{STORAGE_API_URL}/files/videos/{filename}"
        print(f"Generated video URL: {video_url}")
        return jsonify({'success': True, 'url': video_url})
    
    except Exception as e:
        print(f"Error uploading video: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@studio_bp.route('/videos/<filename>')
@login_required
def serve_video(filename):
    try:
        response = requests.get(f"{STORAGE_API_URL}/files/videos/{filename}")
        if response.status_code == 200:
            return response.content, 200, {'Content-Type': 'video/mp4'}
        return jsonify({'success': False, 'message': 'Video not found'}), 404
    except Exception as e:
        print(f"Error serving video {filename}: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 404

@studio_bp.route('/lessons', methods=['GET', 'POST'])
@login_required
@require_professor
def lessons():
    subject = request.args.get('subject', 'Bio')
    if subject not in SUBJECTS:
        subject = 'Bio'
        flash('Invalid subject selected. Defaulting to Biology.', 'warning')

    lessons_path = get_professor_path(subject)

    try:
        lessons = []
        response = requests.get(f"{STORAGE_API_URL}/folders/{lessons_path}")
        if response.status_code == 200:
            contents = response.json()
            for item in contents:
                if item['type'] == 'file' and item['name'].endswith('.html'):
                    lessons.append({
                        'title': item['name'].replace('.html', ''),
                        'path': item['path']
                    })
    except Exception as e:
        flash('Error accessing lessons. Please try again.', 'error')
        lessons = []

    if request.method == 'POST':
        try:
            print("Received POST request for saving lesson")
            print("Content-Type:", request.headers.get('Content-Type'))
            print("Request data:", request.get_data())
            
            data = request.get_json()
            print("Parsed JSON data:", data)
            
            if not data:
                print("No data received")
                return jsonify({'success': False, 'message': 'No data received'}), 400

            title = data.get('title')
            content = data.get('content')
            
            print("Title:", title)
            print("Content length:", len(content) if content else 0)
            
            if not title:
                print("No title provided")
                return jsonify({'success': False, 'message': 'Title is required'}), 400
            if not content:
                print("No content provided")
                return jsonify({'success': False, 'message': 'Content is required'}), 400

            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            print("Safe title:", safe_title)
            
            # Create folder structure in storage API
            print("Creating lectii folder")
            response = requests.post(f"{STORAGE_API_URL}/folders", json={'name': 'lectii', 'parent_path': ''})
            print("Lectii folder response:", response.status_code, response.text)
            if response.status_code not in [200, 201]:  # 200 means folder exists, 201 means folder created
                print("Error creating lectii folder")
                return jsonify({'success': False, 'message': 'Error creating lectii folder'}), 500
                
            print("Creating subject folder:", subject)
            response = requests.post(f"{STORAGE_API_URL}/folders", json={'name': subject, 'parent_path': 'lectii'})
            print("Subject folder response:", response.status_code, response.text)
            if response.status_code not in [200, 201]:  # 200 means folder exists, 201 means folder created
                print("Error creating subject folder")
                return jsonify({'success': False, 'message': 'Error creating subject folder'}), 500
                
            print("Creating professors folder")
            response = requests.post(f"{STORAGE_API_URL}/folders", json={'name': 'profesori', 'parent_path': f"lectii/{subject}"})
            print("Professors folder response:", response.status_code, response.text)
            if response.status_code not in [200, 201]:  # 200 means folder exists, 201 means folder created
                print("Error creating professors folder")
                return jsonify({'success': False, 'message': 'Error creating professors folder'}), 500
                
            print("Creating professor folder:", current_user.email)
            response = requests.post(f"{STORAGE_API_URL}/folders", json={'name': current_user.email, 'parent_path': f"lectii/{subject}/profesori"})
            print("Professor folder response:", response.status_code, response.text)
            if response.status_code not in [200, 201]:  # 200 means folder exists, 201 means folder created
                print("Error creating professor folder")
                return jsonify({'success': False, 'message': 'Error creating professor folder'}), 500

            # Upload the lesson file
            print("Uploading lesson file")
            file_content = BytesIO(content.encode('utf-8'))
            file_content.name = f"{safe_title}.html"
            files = {'file': (f"{safe_title}.html", file_content, 'text/html')}
            data = {'folder_path': f"lectii/{subject}/profesori/{current_user.email}"}
            response = requests.post(f"{STORAGE_API_URL}/files", files=files, data=data)
            print("File upload response:", response.status_code, response.text)
            
            if response.status_code != 201:
                print("Error saving lesson")
                return jsonify({'success': False, 'message': 'Error saving lesson'}), 500
            
            print("Lesson saved successfully")
            return jsonify({'success': True, 'message': 'Lesson saved successfully'})
            
        except Exception as e:
            print(f"Error saving lesson: {str(e)}")
            return jsonify({'success': False, 'message': str(e)}), 500

    return render_template('studio_lessons.html',
                         user=current_user,
                         subject=subject,
                         subjects=SUBJECTS,
                         lessons=lessons)

@studio_bp.route('/tests', defaults={'subject': None}, methods=['GET', 'POST'])
@studio_bp.route('/tests/<subject>', methods=['GET', 'POST'])
@login_required
@require_professor
def tests(subject):
    if subject and subject not in SUBJECTS:
        flash('Invalid subject', 'error')
        return redirect(url_for('studio.tests'))

    tests_by_subject = {}

    if request.method == 'POST':
        subject = request.form.get('subject')
        test_name = request.form.get('test_name')
        
        if not subject or not test_name:
            flash('Subject and test name are required', 'error')
            return redirect(url_for('studio.tests'))
            
        if subject not in SUBJECTS:
            flash('Invalid subject', 'error')
            return redirect(url_for('studio.tests'))
            
        try:
            # Create professor folder if it doesn't exist
            response = requests.post(f"{STORAGE_API_URL}/folders", json={'name': current_user.email, 'parent_path': f"teste/{subject}/profesori"})
            
            # Create test file
            test_content = {
                'title': test_name,
                'questions': []
            }
            file_content = BytesIO(json.dumps(test_content, indent=2).encode('utf-8'))
            file_content.name = f"{test_name}.json"
            files = {'file': (f"{test_name}.json", file_content, 'application/json')}
            data = {'folder_path': get_professor_path(subject, 'teste')}
            response = requests.post(f"{STORAGE_API_URL}/files", files=files, data=data)
            
            if response.status_code == 201:
                flash('Test created successfully', 'success')
                return redirect(url_for('studio.view_test', subject=subject, test=test_name))
            else:
                flash('Error creating test', 'error')
                return redirect(url_for('studio.tests', subject=subject))
        except Exception as e:
            print(f"Error creating test: {str(e)}")
            flash('Error creating test', 'error')
            return redirect(url_for('studio.tests', subject=subject))
    
    # GET request handling
    try:
        if subject:
            # Get tests for specific subject
            test_path = get_professor_path(subject, 'teste')
            response = requests.get(f"{STORAGE_API_URL}/folders/{test_path}")
            if response.status_code == 200:
                files = response.json()
                tests_by_subject[subject] = [
                    {'name': file['name'].replace('.json', '')}
                    for file in files
                    if file['type'] == 'file' and file['name'].endswith('.json')
                ]
        else:
            # Get tests for all subjects
            for subj in SUBJECTS:
                test_path = get_professor_path(subj, 'teste')
                response = requests.get(f"{STORAGE_API_URL}/folders/{test_path}")
                if response.status_code == 200:
                    files = response.json()
                    tests_by_subject[subj] = [
                        {'name': file['name'].replace('.json', '')}
                        for file in files
                        if file['type'] == 'file' and file['name'].endswith('.json')
                    ]
    except Exception as e:
        print(f"Error fetching tests: {str(e)}")
        flash('Error fetching tests', 'error')
        return redirect(url_for('studio.studio'))

    return render_template('studio_tests.html',
                       user=current_user,
                       subjects=SUBJECTS,
                       tests=tests_by_subject,
                       selected_subject=subject)

@studio_bp.route('/test/<subject>/<test>', methods=['GET', 'POST'])
@login_required
@require_professor
def view_test(subject, test):
    if subject not in SUBJECTS:
        flash('Invalid subject', 'error')
        return redirect(url_for('studio.tests'))

    test_path = f"{get_professor_path(subject, 'teste')}/{test}.json"
    try:
        response = requests.get(f"{STORAGE_API_URL}/files/{test_path}")
        if response.status_code == 200:
            test_data = response.json()
            return render_template('view_test.html',
                                user=current_user,
                                subject=subject,
                                test=test_data,
                                subjects=SUBJECTS)
        else:
            flash('Test not found', 'error')
            return redirect(url_for('studio.tests', subject=subject))
    except Exception as e:
        print(f"Error viewing test: {str(e)}")
        flash('Error viewing test', 'error')
        return redirect(url_for('studio.tests', subject=subject))

@studio_bp.route('/edit-test/<subject>/<test>', methods=['GET', 'POST'])
@login_required
@require_professor
def edit_test(subject, test):
    if subject not in SUBJECTS:
        flash('Invalid subject selected', 'error')
        return redirect(url_for('studio.tests'))
        
    try:
        test_path = f"{get_professor_path(subject, 'teste')}/{test}.json"
        
        if request.method == 'POST':
            content = request.form.get('test_content')
            if not content:
                flash('Test content cannot be empty', 'error')
                return redirect(url_for('studio.edit_test', subject=subject, test=test))
            
            try:
                # Validate JSON content
                test_data = json.loads(content)
                # Ensure required fields are present
                if 'title' not in test_data or 'questions' not in test_data:
                    flash('Invalid test format: missing required fields', 'error')
                    return redirect(url_for('studio.edit_test', subject=subject, test=test))
                
                # Validate questions format
                if not isinstance(test_data['questions'], list):
                    flash('Invalid test format: questions must be a list', 'error')
                    return redirect(url_for('studio.edit_test', subject=subject, test=test))
                
                for question in test_data['questions']:
                    if not isinstance(question, dict):
                        flash('Invalid question format', 'error')
                        return redirect(url_for('studio.edit_test', subject=subject, test=test))
                    
                    if 'content' not in question:
                        flash('Invalid question format: missing content', 'error')
                        return redirect(url_for('studio.edit_test', subject=subject, test=test))
                
            except json.JSONDecodeError as e:
                flash(f'Invalid JSON content: {str(e)}', 'error')
                return redirect(url_for('studio.edit_test', subject=subject, test=test))
            
            # Create test file
            file_content = BytesIO(content.encode('utf-8'))
            file_content.name = f"{test}.json"
            files = {'file': (f"{test}.json", file_content, 'application/json')}
            data = {'folder_path': get_professor_path(subject, 'teste')}
            
            # Create professor folder if it doesn't exist
            response = requests.post(f"{STORAGE_API_URL}/folders", json={'name': current_user.email, 'parent_path': f"teste/{subject}/profesori"})
            
            # Upload test file
            response = requests.post(f"{STORAGE_API_URL}/files", files=files, data=data)
            
            if response.status_code == 201:
                flash('Test updated successfully', 'success')
                return redirect(url_for('studio.view_test', subject=subject, test=test))
            else:
                flash('Error updating test', 'error')
                return redirect(url_for('studio.edit_test', subject=subject, test=test))
        
        # GET request - fetch test content
        response = requests.get(f"{STORAGE_API_URL}/files/{test_path}")
        if response.status_code == 200:
            content = json.dumps(response.json(), indent=2)
            return render_template('edit_test.html',
                                subject=subject,
                                test=test,
                                content=content,
                                user=current_user,
                                subjects=SUBJECTS,
                                subject_data=SUBJECTS[subject])
        else:
            flash('Test not found', 'error')
            return redirect(url_for('studio.tests', subject=subject))
            
    except Exception as e:
        print(f"Error editing test: {str(e)}")
        flash('Error editing test', 'error')
        return redirect(url_for('studio.tests', subject=subject))

@studio_bp.route('/test-results/<subject>')
@login_required
@require_professor
def view_test_results(subject):
    if subject not in SUBJECTS:
        flash('Invalid subject', 'error')
        return redirect(url_for('studio.dashboard'))

    # Get all tests for this subject
    tests = []
    test_dir = os.path.join(TESTE_DIR, subject, 'profesori', current_user.email)
    if os.path.exists(test_dir):
        for filename in os.listdir(test_dir):
            if filename.endswith('.json'):
                test_file = os.path.join(test_dir, filename)
                with open(test_file, 'r', encoding='utf-8') as f:
                    test_data = json.load(f)
                    tests.append({
                        'title': test_data['title'],
                        'created_at': datetime.fromisoformat(test_data['created_at']),
                        'questions': len(test_data['questions']),
                        'status': test_data.get('status', 'draft')
                    })

    # Get all grades for this subject from both locations
    grades = []
    
    # Check test results directory
    results_dir = os.path.join(test_dir, 'results')
    if os.path.exists(results_dir):
        for filename in os.listdir(results_dir):
            if filename.endswith('.json'):
                result_file = os.path.join(results_dir, filename)
                with open(result_file, 'r', encoding='utf-8') as f:
                    result_data = json.load(f)
                    student = User.query.filter_by(email=result_data['student_email']).first()
                    if student:
                        grades.append({
                            'student': student,
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
                for filename in os.listdir(student_dir):
                    if filename.endswith('.json'):
                        grade_file = os.path.join(student_dir, filename)
                        with open(grade_file, 'r', encoding='utf-8') as f:
                            grade_data = json.load(f)
                            if (grade_data.get('subject') == subject and 
                                grade_data.get('professor_email') == current_user.email):
                                student = User.query.filter_by(email=student_email).first()
                                if student:
                                    grades.append({
                                        'student': student,
                                        'test_title': grade_data['test_title'],
                                        'score': grade_data['score'],
                                        'date': datetime.fromisoformat(grade_data['date'])
                                    })

    # Remove duplicates and sort by date
    unique_grades = {}
    for grade in grades:
        key = f"{grade['student'].email}_{grade['test_title']}"
        if key not in unique_grades or grade['date'] > unique_grades[key]['date']:
            unique_grades[key] = grade

    grades = list(unique_grades.values())
    grades.sort(key=lambda x: x['date'], reverse=True)

    return render_template('studio_test_results.html',
                         user=current_user,
                         subject=subject,
                         tests=tests,
                         grades=grades,
                         subjects=SUBJECTS)

@studio_bp.route('/test-result/<subject>/<lesson_title>/<student_email>')
@login_required
@require_professor
def view_test_result(subject, lesson_title, student_email):

    subject_key = subject
    if subject_key not in SUBJECTS:
        flash('Invalid subject.', 'error')
        return redirect(url_for('studio.dashboard'))

    result_path = os.path.join(TESTE_DIR, subject_key, 'profesori', current_user.email, 'results', f'{lesson_title}_{student_email}.json')
    if not os.path.exists(result_path):
        flash('Test result not found.', 'error')
        return redirect(url_for('studio.view_test_results', subject=subject_key))

    with open(result_path, 'r') as f:
        result = json.load(f)

    print(f"Test result data: {result}")

    test_path = os.path.join(TESTE_DIR, subject_key, 'profesori', current_user.email, f'{lesson_title}.json')
    if not os.path.exists(test_path):
        flash('Original test not found.', 'error')
        return redirect(url_for('studio.view_test_results', subject=subject_key))

    with open(test_path, 'r') as f:
        test = json.load(f)

    print(f"Test data: {test}")

    student = User.query.filter_by(email=student_email).first()
    student_name = student.name if student else student_email

    total_score = result.get('score', 0)
    if 'grades' in result:
        graded_score = sum(result['grades'].values())
        total_score += graded_score

    result['total_score'] = total_score

    print(f"Final result data: {result}")

    return render_template('studio_test_result_detail.html',
                         subject=SUBJECTS[subject_key],
                         test=test,
                         result=result,
                         student_name=student_name)

@studio_bp.route('/grade-question/<subject>/<test>/<student_email>', methods=['POST'])
@login_required
@require_professor
def grade_question(subject, test, student_email):
    try:
        data = request.get_json()
        question_index = int(data.get('question_index'))
        grade = float(data.get('grade'))

        if grade < 0 or grade > 10:
            return jsonify({'success': False, 'message': 'Grade must be between 0 and 10'})

        result_path = os.path.join(TESTE_DIR, subject, 'profesori', current_user.email, 'results', f'{test}_{student_email}.json')

        if not os.path.exists(result_path):
            return jsonify({'success': False, 'message': 'Test result not found'})

        with open(result_path, 'r') as f:
            result = json.load(f)

        if 'grades' not in result:
            result['grades'] = {}

        result['grades'][str(question_index)] = grade

        test_path = os.path.join(TESTE_DIR, subject, 'profesori', current_user.email, f'{test}.json')
        with open(test_path, 'r') as f:
            test_data = json.load(f)

        total_questions = len(test_data['questions'])
        graded_questions = len(result['grades']) + result.get('graded_questions', 0)

        total_score = result.get('score', 0)
        graded_score = sum(result['grades'].values())
        result['total_score'] = total_score + graded_score

        if graded_questions == total_questions:
            result['status'] = 'graded'

        with open(result_path, 'w') as f:
            json.dump(result, f, indent=2)

        return jsonify({
            'success': True,
            'all_graded': graded_questions == total_questions,
            'total_score': result['total_score']
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@studio_bp.route('/view-lesson/<subject>/<title>')
@login_required
@require_professor
def view_lesson(subject, title):
    try:
        lesson_path = f"lectii/{subject}/profesori/{current_user.email}/{title}.html"
        response = requests.get(f"{STORAGE_API_URL}/files/{lesson_path}")
        if response.status_code == 200:
            content = response.text
            return render_template('view_lesson.html',
                                subject=subject,
                                title=title,
                                content=content,
                                professor=current_user,
                                subject_key=subject,
                                subject_data=SUBJECTS[subject])
        else:
            flash('Lesson not found', 'error')
            return redirect(url_for('studio.lessons', subject=subject))
    except Exception as e:
        print(f"Error viewing lesson: {str(e)}")
        flash('Error viewing lesson', 'error')
        return redirect(url_for('studio.lessons', subject=subject))

@studio_bp.route('/edit-lesson/<subject>/<title>', methods=['GET', 'POST'])
@login_required
@require_professor
def edit_lesson(subject, title):
    if subject not in SUBJECTS:
        flash('Invalid subject selected', 'error')
        return redirect(url_for('studio.lessons'))
        
    try:
        lesson_path = f"lectii/{subject}/profesori/{current_user.email}/{title}.html"
        
        if request.method == 'POST':
            content = request.form.get('lesson_content')
            if not content:
                flash('Lesson content cannot be empty', 'error')
                return redirect(url_for('studio.edit_lesson', subject=subject, title=title))
            
            # Update lesson in storage API using POST
            file_content = BytesIO(content.encode('utf-8'))
            file_content.name = f"{title}.html"
            files = {'file': (f"{title}.html", file_content, 'text/html')}
            data = {'folder_path': f"lectii/{subject}/profesori/{current_user.email}"}
            response = requests.post(f"{STORAGE_API_URL}/files", files=files, data=data)
            
            if response.status_code == 201:
                flash('Lesson updated successfully', 'success')
                return redirect(url_for('studio.view_lesson', subject=subject, title=title))
            else:
                flash('Error updating lesson', 'error')
                return redirect(url_for('studio.edit_lesson', subject=subject, title=title))
        
        # GET request - fetch lesson content
        response = requests.get(f"{STORAGE_API_URL}/files/{lesson_path}")
        if response.status_code == 200:
            content = response.text
            return render_template('edit_lesson.html',
                                subject=subject,
                                title=title,
                                lesson=title,
                                content=content,
                                user=current_user,
                                subjects=SUBJECTS,
                                subject_data=SUBJECTS[subject])
        else:
            flash('Lesson not found', 'error')
            return redirect(url_for('studio.lessons', subject=subject))
            
    except Exception as e:
        print(f"Error editing lesson: {str(e)}")
        flash('Error editing lesson', 'error')
        return redirect(url_for('studio.lessons', subject=subject))

@studio_bp.route('/delete-lesson/<subject>/<title>', methods=['POST'])
@login_required
@require_professor
def delete_lesson(subject, title):
    if subject not in SUBJECTS:
        flash('Invalid subject selected', 'error')
        return redirect(url_for('studio.lessons'))
        
    try:
        lesson_path = f"lectii/{subject}/profesori/{current_user.email}/{title}.html"
        
        # Delete the lesson file from storage API
        response = requests.delete(f"{STORAGE_API_URL}/files/{lesson_path}")
        
        if response.status_code == 200:
            flash('Lesson deleted successfully', 'success')
        else:
            flash('Error deleting lesson', 'error')
            
        return redirect(url_for('studio.lessons', subject=subject))
            
    except Exception as e:
        print(f"Error deleting lesson: {str(e)}")
        flash('Error deleting lesson', 'error')
        return redirect(url_for('studio.lessons', subject=subject))

@studio_bp.route('/delete-test/<subject>/<title>', methods=['POST'])
@login_required
@require_professor
def delete_test(subject, title):
    if subject not in SUBJECTS:
        flash('Invalid subject selected', 'error')
        return redirect(url_for('studio.tests'))
        
    try:
        test_path = f"teste/{subject}/profesori/{current_user.email}/{title}.json"
        
        # Delete the test file from storage API
        response = requests.delete(f"{STORAGE_API_URL}/files/{test_path}")
        
        if response.status_code == 200:
            flash('Test deleted successfully', 'success')
        else:
            flash('Error deleting test', 'error')
            
        return redirect(url_for('studio.tests', subject=subject))
            
    except Exception as e:
        print(f"Error deleting test: {str(e)}")
        flash('Error deleting test', 'error')
        return redirect(url_for('studio.tests', subject=subject))