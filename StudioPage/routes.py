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
from sync_service import sync_service

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, '../instance')
LECTII_DIR = os.path.join(INSTANCE_DIR, 'lectii')
TESTE_DIR = os.path.join(INSTANCE_DIR, 'teste')
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

os.makedirs(LECTII_DIR, exist_ok=True)
os.makedirs(TESTE_DIR, exist_ok=True)

def require_professor(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.user_type != 'profesor' or not current_user.is_professor_approved:
            flash('You must be an approved professor to access this page.', 'error')
            return redirect(url_for('landing.index'))
        return f(*args, **kwargs)
    return decorated_function

def get_professor_dir(base_dir, subject):
    """Get professor-specific directory for a subject"""
    if not current_user.is_authenticated:
        return None

    professor_dir = os.path.join(base_dir, subject, 'profesori', current_user.email)
    os.makedirs(professor_dir, exist_ok=True)
    return professor_dir

@studio_bp.route('/')
@login_required
@require_professor
def studio():
    lesson_count = 0
    test_count = 0
    student_count = 0
    try:
        for subject_key in SUBJECTS:
            lesson_dir = get_professor_dir(LECTII_DIR, subject_key)
            test_dir = get_professor_dir(TESTE_DIR, subject_key)
            if os.path.exists(lesson_dir):
                lesson_count += len([f for f in os.listdir(lesson_dir) if f.endswith('.html')])
            if os.path.exists(test_dir):
                test_count += len([f for f in os.listdir(test_dir) if f.endswith('.json')])
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
        
        # Create videos directory if it doesn't exist
        videos_dir = os.path.join(INSTANCE_DIR, 'videos')
        os.makedirs(videos_dir, exist_ok=True)
        print(f"Videos directory: {videos_dir}")
        
        # Save the video
        video_path = os.path.join(videos_dir, filename)
        video.save(video_path)
        print(f"Video saved to: {video_path}")
        
        # Sync with Google Drive
        sync_service.sync_videos()
        
        # Return the URL for the video
        video_url = url_for('studio.serve_video', filename=filename, _external=True)
        print(f"Generated video URL: {video_url}")
        return jsonify({'success': True, 'url': video_url})
    
    except Exception as e:
        print(f"Error uploading video: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@studio_bp.route('/videos/<filename>')
@login_required
def serve_video(filename):
    videos_dir = os.path.join(INSTANCE_DIR, 'videos')
    try:
        return send_from_directory(videos_dir, filename, as_attachment=False)
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

    lessons_dir = get_professor_dir(LECTII_DIR, subject)

    try:
        lessons = []
        if os.path.exists(lessons_dir):
            for f in os.listdir(lessons_dir):
                if f.endswith('.html'):
                    lessons.append({
                        'title': f.replace('.html', ''),
                        'path': os.path.join(lessons_dir, f)
                    })
    except Exception as e:
        flash('Error accessing lessons. Please try again.', 'error')
        lessons = []

    if request.method == 'POST':
        try:
            print("Received POST request")
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
                return jsonify({'success': False, 'message': 'Title is required'}), 400
            if not content:
                return jsonify({'success': False, 'message': 'Content is required'}), 400

            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            lessons_dir = get_professor_dir(LECTII_DIR, subject)
            os.makedirs(lessons_dir, exist_ok=True)

            file_path = os.path.join(lessons_dir, f"{safe_title}.html")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            # Sync with Google Drive
            sync_service.sync_lessons()
            
            return jsonify({'success': True, 'message': 'Lesson saved successfully'})
            
        except Exception as e:
            print(f"Error saving lesson: {str(e)}")
            return jsonify({'success': False, 'message': str(e)}), 500

    return render_template('studio_lessons.html',
                         user=current_user,
                         subject=subject,
                         subjects=SUBJECTS,
                         lessons=lessons)

@studio_bp.route('/lesson/<subject>/<title>')
@login_required
@require_professor
def view_lesson(subject, title):
    if subject not in SUBJECTS:
        flash('Invalid subject', 'error')
        return redirect(url_for('studio.lessons'))

    lesson_dir = get_professor_dir(LECTII_DIR, subject)
    lesson_file = os.path.join(lesson_dir, f"{title}.html")
    
    if not os.path.exists(lesson_file):
        flash('Lesson not found', 'error')
        return redirect(url_for('studio.lessons', subject=subject))
    
    with open(lesson_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    return render_template('view_lesson.html',
                         lesson={'title': title, 'content': content, 'subject': subject},
                         subjects=SUBJECTS,
                         user=current_user)

@studio_bp.route('/tests', methods=['GET', 'POST'])
@login_required
@require_professor
def tests():
    subject = request.args.get('subject', 'Bio')
    if subject not in SUBJECTS:
        subject = 'Bio'
        flash('Invalid subject selected. Defaulting to Biology.', 'warning')

    tests_dir = get_professor_dir(TESTE_DIR, subject)

    try:
        tests = []
        if os.path.exists(tests_dir):
            for f in os.listdir(tests_dir):
                if f.endswith('.json'):
                    tests.append({
                        'title': f.replace('.json', ''),
                        'path': os.path.join(tests_dir, f)
                    })
    except Exception as e:
        flash('Error accessing tests. Please try again.', 'error')
        tests = []

    if request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'No data received'}), 400

            title = data.get('title')
            questions = data.get('questions', [])
            
            if not title:
                return jsonify({'success': False, 'message': 'Title is required'}), 400
            if not questions:
                return jsonify({'success': False, 'message': 'At least one question is required'}), 400

            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            tests_dir = get_professor_dir(TESTE_DIR, subject)
            os.makedirs(tests_dir, exist_ok=True)

            file_path = os.path.join(tests_dir, f"{safe_title}.json")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'title': title,
                    'questions': questions,
                    'created_at': datetime.now().isoformat(),
                    'created_by': current_user.email
                }, f, ensure_ascii=False, indent=4)

            # Sync with Google Drive
            sync_service.sync_tests()
            
            return jsonify({'success': True, 'message': 'Test saved successfully'})
            
        except Exception as e:
            print(f"Error saving test: {str(e)}")
            return jsonify({'success': False, 'message': str(e)}), 500

    return render_template('studio_tests.html',
                         user=current_user,
                         subject=subject,
                         subjects=SUBJECTS,
                         tests=tests)

@studio_bp.route('/test/<subject>/<test>', methods=['GET', 'POST'])
@login_required
@require_professor
def view_test(subject, test):
    if subject not in SUBJECTS:
        flash('Invalid subject', 'error')
        return redirect(url_for('studio.tests'))

    test_dir = get_professor_dir(TESTE_DIR, subject)

    test_file = os.path.join(test_dir, f"{test}.json")
    if os.path.exists(test_file):
        with open(test_file, 'r', encoding='utf-8') as f:
            test_data = json.load(f)
    else:
        test_data = {
            'title': test,
            'subject': subject,
            'questions': [],
            'created_by': current_user.email,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'status': 'Draft'
        }

    if request.method == 'POST':
        try:
            data = request.get_json()
            questions = data.get('questions')
            action = data.get('action')

            if not questions:
                return jsonify({'success': False, 'message': 'Questions are required'}), 400

            test_data['questions'] = questions
            test_data['updated_at'] = datetime.utcnow().isoformat()
            test_data['status'] = 'Published' if action == 'publish' else 'Draft'

            with open(test_file, 'w', encoding='utf-8') as f:
                json.dump(test_data, f, indent=2)

            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    return render_template('view_test.html',
                         user=current_user,
                         subject=subject,
                         test=test_data,
                         subjects=SUBJECTS)

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