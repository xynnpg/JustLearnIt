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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_DIR = os.path.join(BASE_DIR, '../storage')
LECTII_DIR = os.path.join(STORAGE_DIR, 'lectii')
TESTE_DIR = os.path.join(STORAGE_DIR, 'teste')

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
    test_results_count = 0
    test_results = {}
    
    try:
        for subject_key in SUBJECTS:
            lectii_path = os.path.join(LECTII_DIR, subject_key, 'profesori', current_user.email)
            teste_path = os.path.join(TESTE_DIR, subject_key, 'profesori', current_user.email)
            
            # Get lessons count
            if os.path.exists(lectii_path):
                files = os.listdir(lectii_path)
                lesson_count += len([f for f in files if f.endswith('.html')])
            
            # Get tests count and results
            if os.path.exists(teste_path):
                files = os.listdir(teste_path)
                test_count += len([f for f in files if f.endswith('.json')])
                
                # Get test results
                results_path = os.path.join(teste_path, 'results')
                if os.path.exists(results_path):
                    result_files = [f for f in os.listdir(results_path) if f.endswith('.json')]
                    test_results_count += len(result_files)
                    results = []
                    
                    for result_file in result_files:
                        with open(os.path.join(results_path, result_file), 'r') as f:
                            result_data = json.load(f)
                            results.append(result_data)
                            
                    test_results[subject_key] = results
    except Exception as e:
        flash('Error counting lessons and tests', 'error')

    return render_template('studio_dashboard.html',
                         user=current_user,
                         subjects=SUBJECTS,
                         total_lessons=lesson_count,
                         total_tests=test_count,
                         total_students=test_results_count,
                         test_results=test_results)

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

    lessons_path = os.path.join(LECTII_DIR, subject, 'profesori', current_user.email)
    lessons = []
    try:
        if os.path.exists(lessons_path):
            files = os.listdir(lessons_path)
            for file in files:
                if file.endswith('.html'):
                    lessons.append({
                        'title': file.replace('.html', ''),
                        'path': os.path.join(lessons_path, file)
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
            
            # Create folder structure
            os.makedirs(lessons_path, exist_ok=True)
            
            # Save the lesson file
            lesson_file = os.path.join(lessons_path, f"{safe_title}.html")
            with open(lesson_file, 'w') as f:
                f.write(content)
            
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
    if not subject:
        subject = request.args.get('subject', 'Bio')
    if subject not in SUBJECTS:
        subject = 'Bio'
        flash('Invalid subject selected. Defaulting to Biology.', 'warning')

    tests_by_subject = {subject: []}
    try:
        tests_path = os.path.join(TESTE_DIR, subject, 'profesori', current_user.email)
        if os.path.exists(tests_path):
            files = os.listdir(tests_path)
            for file in files:
                if file.endswith('.json'):
                    tests_by_subject[subject].append({
                        'name': file.replace('.json', ''),
                        'path': os.path.join(tests_path, file)
                    })
    except Exception as e:
        flash('Error accessing tests. Please try again.', 'error')
        tests_by_subject = {subject: []}

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
            # Get test content from form data
            test_content = request.form.get('test_content')
            if not test_content:
                flash('Test content cannot be empty', 'error')
                return redirect(url_for('studio.tests', subject=subject))
            
            try:
                # Validate JSON content
                test_data = json.loads(test_content)
                # Ensure required fields are present
                if 'title' not in test_data or 'questions' not in test_data:
                    flash('Invalid test format: missing required fields', 'error')
                    return redirect(url_for('studio.tests', subject=subject))
                
                # Validate questions format
                if not isinstance(test_data['questions'], list):
                    flash('Invalid test format: questions must be a list', 'error')
                    return redirect(url_for('studio.tests', subject=subject))
                
                for question in test_data['questions']:
                    if not isinstance(question, dict):
                        flash('Invalid question format', 'error')
                        return redirect(url_for('studio.tests', subject=subject))
                    
                    if 'content' not in question:
                        flash('Invalid question format: missing content', 'error')
                        return redirect(url_for('studio.tests', subject=subject))
                
            except json.JSONDecodeError as e:
                flash(f'Invalid JSON content: {str(e)}', 'error')
                return redirect(url_for('studio.tests', subject=subject))
            
            # Create test file
            os.makedirs(os.path.join(TESTE_DIR, subject, 'profesori', current_user.email), exist_ok=True)
            test_file = os.path.join(TESTE_DIR, subject, 'profesori', current_user.email, f"{test_name}.json")
            with open(test_file, 'w') as f:
                f.write(test_content)
            
            flash('Test created successfully', 'success')
            return redirect(url_for('studio.view_test', subject=subject, test=test_name))
            
        except Exception as e:
            print(f"Error creating test: {str(e)}")
            flash('Error creating test', 'error')
            return redirect(url_for('studio.tests', subject=subject))
    
    return render_template('studio_tests.html',
                          user=current_user,
                          selected_subject=subject,
                          subjects=SUBJECTS,
                          tests=tests_by_subject)

@studio_bp.route('/test/<subject>/<test>', methods=['GET', 'POST'])
@login_required
def view_test(subject, test):
    if subject not in SUBJECTS:
        flash('Invalid subject', 'error')
        return redirect(url_for('studio.tests'))

    test_path = os.path.join(TESTE_DIR, subject, 'profesori', current_user.email, f"{test}.json")
    try:
        if os.path.exists(test_path):
            with open(test_path, 'r') as f:
                test_data = json.load(f)
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
        flash('Invalid subject', 'error')
        return redirect(url_for('studio.tests'))

    test_path = os.path.join(TESTE_DIR, subject, 'profesori', current_user.email, f"{test}.json")
    
    try:
        if request.method == 'POST':
            test_content = request.form.get('test_content')
            if not test_content:
                flash('No test content provided', 'error')
                return redirect(url_for('studio.edit_test', subject=subject, test=test))
            
            try:
                test_data = json.loads(test_content)
                
                # Validate test data
                if not isinstance(test_data, dict):
                    raise ValueError('Invalid test data format')
                
                if 'title' not in test_data or 'questions' not in test_data:
                    raise ValueError('Missing required fields')
                
                if not isinstance(test_data['questions'], list):
                    raise ValueError('Questions must be a list')
                
                # Write content to file
                with open(test_path, 'w') as f:
                    json.dump(test_data, f, indent=4)
                
                flash('Test updated successfully', 'success')
                return redirect(url_for('studio.view_test', subject=subject, test=test))
                
            except json.JSONDecodeError:
                flash('Invalid JSON format', 'error')
                return redirect(url_for('studio.edit_test', subject=subject, test=test))
        
        # GET request - fetch test content
        if os.path.exists(test_path):
            with open(test_path, 'r') as f:
                test_data = json.load(f)
            return render_template('edit_test.html',
                                subject=subject,
                                test=test,
                                content=test_data,
                                user=current_user,
                                subjects=SUBJECTS)
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
        return redirect(url_for('studio.studio'))

    try:
        results = []
        results_path = os.path.join(TESTE_DIR, subject, 'profesori', current_user.email, 'results')
        print(f"Checking results path: {results_path}")
        
        if os.path.exists(results_path):
            result_files = [f for f in os.listdir(results_path) if f.endswith('.json')]
            print(f"Found result files: {result_files}")
            
            for result_file in result_files:
                try:
                    file_path = os.path.join(results_path, result_file)
                    print(f"Processing file: {file_path}")
                    
                    with open(file_path, 'r') as f:
                        result_data = json.load(f)
                        print(f"Result data: {result_data}")
                        
                        # Extract test name and student email from filename
                        file_name = result_file.replace('.json', '')
                        test_name = file_name.rsplit('_', 1)[0]  # Get everything before the last underscore
                        student_email = file_name.rsplit('_', 1)[1]  # Get everything after the last underscore
                        
                        # Add required fields to result data
                        result_data['lesson_title'] = test_name
                        result_data['student_email'] = student_email
                        
                        # Get student name if available
                        student = User.query.filter_by(email=student_email).first()
                        result_data['student_name'] = student.name if student else student_email
                        
                        # Calculate total score
                        total_score = float(result_data.get('score', 0))
                        if 'grades' in result_data:
                            graded_score = sum(float(grade) for grade in result_data['grades'].values())
                            total_score += graded_score
                        result_data['score'] = total_score
                        
                        # Format submission date if available
                        if 'submission_date' not in result_data:
                            result_data['submission_date'] = 'N/A'
                            
                        results.append(result_data)
                        print(f"Processed result: {result_data}")
                except Exception as e:
                    print(f"Error processing result file {result_file}: {str(e)}")
                    continue
            
            # Sort results by submission date
            results.sort(key=lambda x: x.get('submission_date', ''), reverse=True)
        
        print(f"Final results list: {results}")
        return render_template('studio_test_results.html',
                             user=current_user,
                             subject=subject,
                             results=results,
                             subjects=SUBJECTS)
    except Exception as e:
        print(f"Error viewing test results: {str(e)}")
        flash('Error viewing test results', 'error')
        return redirect(url_for('studio.studio'))

@studio_bp.route('/test-result/<subject>/<lesson_title>/<student_email>')
@login_required
@require_professor
def view_test_result(subject, lesson_title, student_email):
    if subject not in SUBJECTS:
        flash('Invalid subject.', 'error')
        return redirect(url_for('studio.studio'))

    try:
        # Get the test result
        result_path = os.path.join(TESTE_DIR, subject, 'profesori', current_user.email, 'results', f"{lesson_title}_{student_email}.json")
        print(f"Looking for result at path: {result_path}")
        
        if not os.path.exists(result_path):
            print(f"Test result not found at path: {result_path}")
            flash('Test result not found.', 'error')
            return redirect(url_for('studio.view_test_results', subject=subject))
        
        with open(result_path, 'r') as f:
            result = json.load(f)
        print(f"Found result: {result}")
        
        # Get the original test
        test_path = os.path.join(TESTE_DIR, subject, 'profesori', current_user.email, f"{lesson_title}.json")
        print(f"Looking for test at path: {test_path}")
        
        if not os.path.exists(test_path):
            print(f"Original test not found at path: {test_path}")
            flash('Original test not found.', 'error')
            return redirect(url_for('studio.view_test_results', subject=subject))
        
        with open(test_path, 'r') as f:
            test = json.load(f)
        print(f"Found test: {test}")
        
        # Get student info
        student = User.query.filter_by(email=student_email).first()
        student_name = student.name if student else student_email
        
        # Calculate total score
        total_score = float(result.get('score', 0))
        if 'grades' in result:
            graded_score = sum(float(grade) for grade in result['grades'].values())
            total_score += graded_score
        result['total_score'] = total_score
        
        # Debug print all data being passed to template
        print("\nData being passed to template:")
        print(f"subject: {SUBJECTS[subject]}")
        print(f"test: {test}")
        print(f"result: {result}")
        print(f"student_name: {student_name}")
        print(f"subjects: {SUBJECTS}")
        
        return render_template('studio_test_result_detail.html',
                            subject=SUBJECTS[subject],
                            test=test,
                            result=result,
                            student_name=student_name,
                            subjects=SUBJECTS)
    except Exception as e:
        print(f"Error viewing test result: {str(e)}")
        print(f"Full error details: ", e.__class__.__name__, str(e))
        flash('Error viewing test result', 'error')
        return redirect(url_for('studio.view_test_results', subject=subject))

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
        lesson_path = os.path.join(LECTII_DIR, subject, 'profesori', current_user.email, f"{title}.html")
        if os.path.exists(lesson_path):
            with open(lesson_path, 'r') as f:
                content = f.read()
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
        lesson_path = os.path.join(LECTII_DIR, subject, 'profesori', current_user.email, f"{title}.html")
        
        if request.method == 'POST':
            content = request.form.get('lesson_content')
            if not content:
                flash('Lesson content cannot be empty', 'error')
                return redirect(url_for('studio.edit_lesson', subject=subject, title=title))
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(lesson_path), exist_ok=True)
            
            # Write content to file
            with open(lesson_path, 'w') as f:
                f.write(content)
            
            flash('Lesson updated successfully', 'success')
            return redirect(url_for('studio.view_lesson', subject=subject, title=title))
        
        # GET request - fetch lesson content
        if os.path.exists(lesson_path):
            with open(lesson_path, 'r') as f:
                content = f.read()
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
        lesson_path = os.path.join(LECTII_DIR, subject, 'profesori', current_user.email, f"{title}.html")
        if os.path.exists(lesson_path):
            os.remove(lesson_path)
            flash('Lesson deleted successfully', 'success')
        else:
            flash('Lesson not found', 'error')
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
        test_path = os.path.join(TESTE_DIR, subject, 'profesori', current_user.email, f"{title}.json")
        if os.path.exists(test_path):
            os.remove(test_path)
            flash('Test deleted successfully', 'success')
        else:
            flash('Test not found', 'error')
        return redirect(url_for('studio.tests', subject=subject))
    except Exception as e:
        print(f"Error deleting test: {str(e)}")
        flash('Error deleting test', 'error')
        return redirect(url_for('studio.tests', subject=subject))