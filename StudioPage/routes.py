from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime
import os
import json
from functools import wraps
from . import studio_bp
from flask_login import current_user
from flask_sqlalchemy import SQLAlchemy

# Constants
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

# Create base directories if they don't exist
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
        
    # Create the full path: base_dir/subject/profesori/professor_email
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
            data = request.get_json()
            title = data.get('title')
            content = data.get('content')
            subject = data.get('subject', 'Bio')

            if not title or not content:
                return jsonify({'success': False, 'message': 'Title and content are required'}), 400

            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            lessons_dir = get_professor_dir(LECTII_DIR, subject)  # ✅ professor-specific directory
            os.makedirs(lessons_dir, exist_ok=True)

            file_path = os.path.join(lessons_dir, f"{safe_title}.html")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>{safe_title}</title>
        <link href="https://cdn.quilljs.com/1.3.6/quill.snow.css" rel="stylesheet">
        <style>
            body {{ padding: 20px; font-family: Arial, sans-serif; }}
            .ql-editor {{ border: none; padding: 0; }}
        </style>
    </head>
    <body>
        <div class="ql-editor">{content}</div>
    </body>
    </html>
    """)

            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    return render_template('studio_lessons.html',
                         user=current_user,
                         subject=SUBJECTS[subject],
                         subjects=SUBJECTS,
                         lessons=lessons)

@studio_bp.route('/lesson/<subject>/<lesson>', methods=['GET', 'POST'])
@login_required
@require_professor
def view_lesson(subject, lesson):
    if subject not in SUBJECTS:
        flash('Invalid subject', 'error')
        return redirect(url_for('studio.lessons'))

    file_path = os.path.join(get_professor_dir(LECTII_DIR, subject), f"{lesson}.html")
    if not os.path.exists(file_path):
        flash('Lesson not found', 'error')
        return redirect(url_for('studio.lessons'))

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    start_marker = '<div class="ql-editor">'
    end_marker = '</div>'
    start_idx = content.find(start_marker) + len(start_marker)
    end_idx = content.find(end_marker, start_idx)
    lesson_content = content[start_idx:end_idx] if start_idx != -1 and end_idx != -1 else content

    if request.method == 'POST':
        try:
            data = request.get_json()
            new_content = data.get('content')
            action = data.get('action')  # 'save' or 'publish'
            if not new_content:
                return jsonify({'success': False, 'message': 'Content is required'}), 400

            html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{lesson}</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; max-width: 800px; margin: 20px auto; padding: 20px; color: #333; }}
        h1, h2, h3 {{ color: #5f06a8; }}
        img {{ max-width: 100%; height: auto; }}
    </style>
</head>
<body>
    <h1>{lesson}</h1>
    <div class="ql-editor">{new_content}</div>
    <div class="metadata" style="font-size: 0.8em; color: #666; margin-top: 30px;">
        Updated by: {current_user.email} | {datetime.now().strftime('%Y-%m-%d')} | Status: {'Published' if action == 'publish' else 'Draft'}
    </div>
</body>
</html>"""

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    return render_template('view_lesson.html',
                           user=current_user,
                           subject=subject,
                           lesson_title=lesson,
                           content=lesson_content)

@studio_bp.route('/tests', methods=['GET', 'POST'])
@login_required
@require_professor
def tests():
    subject = request.args.get('subject', 'Bio')
    if subject not in SUBJECTS:
        subject = 'Bio'
        flash('Invalid subject selected. Defaulting to Biology.', 'warning')

    # Get professor's test directory
    tests_dir = get_professor_dir(TESTE_DIR, subject)
    
    try:
        tests = []
        if os.path.exists(tests_dir):
            for f in os.listdir(tests_dir):
                if f.endswith('.json'):
                    with open(os.path.join(tests_dir, f), 'r', encoding='utf-8') as test_file:
                        test_data = json.load(test_file)
                        tests.append({
                            'title': f.replace('.json', ''),
                            'question_count': len(test_data.get('questions', [])),
                            'created_at': test_data.get('created_at', 'Unknown')
                        })
    except Exception as e:
        flash('Error accessing tests. Please try again.', 'error')
        tests = []

    if request.method == 'POST':
        try:
            data = request.get_json()
            title = data.get('title')
            questions = data.get('questions')
            subject = data.get('subject', 'Bio')

            if not title or not questions:
                return jsonify({'success': False, 'message': 'Title and questions are required'}), 400

            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            
            # Get professor's test directory
            tests_dir = get_professor_dir(TESTE_DIR, subject)

            # Create test data structure
            test_data = {
                'title': title,
                'subject': subject,
                'questions': questions,
                'created_by': current_user.email,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat(),
                'status': 'Draft'
            }

            # Save test file
            file_path = os.path.join(tests_dir, f"{safe_title}.json")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(test_data, f, indent=2)

            return jsonify({'success': True})
        except Exception as e:
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

    # Get professor's test directory
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
            action = data.get('action')  # 'save' or 'publish'

            if not questions:
                return jsonify({'success': False, 'message': 'Questions are required'}), 400

            # Update test data
            test_data['questions'] = questions
            test_data['updated_at'] = datetime.utcnow().isoformat()
            test_data['status'] = 'Published' if action == 'publish' else 'Draft'

            # Save updated test data
            with open(test_file, 'w', encoding='utf-8') as f:
                json.dump(test_data, f, indent=2)

            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    return render_template('view_test.html',
                         user=current_user,
                         subject=subject,
                         test=test_data)

@studio_bp.route('/test-results/<subject>')
@login_required
@require_professor
def view_test_results(subject):
    # Check if subject exists
    subject_key = subject
    if subject_key not in SUBJECTS:
        flash('Invalid subject.', 'error')
        return redirect(url_for('studio.dashboard'))
    
    # Get test results from the directory
    results_dir = os.path.join(TESTE_DIR, subject_key, 'profesori', current_user.email, 'results')
    if not os.path.exists(results_dir):
        flash('No test results found.', 'info')
        return redirect(url_for('studio.dashboard'))
    
    # Get all result files
    results = []
    for filename in os.listdir(results_dir):
        if filename.endswith('.json'):
            with open(os.path.join(results_dir, filename), 'r') as f:
                result = json.load(f)
                # Get student name from email
                student = User.query.filter_by(email=result['student_email']).first()
                result['student_name'] = student.name if student else result['student_email']
                results.append(result)
    
    # Sort results by timestamp
    results.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return render_template('studio_test_results.html', 
                         subject=SUBJECTS[subject_key],
                         results=results)

@studio_bp.route('/test-result/<subject>/<lesson_title>/<student_email>')
@login_required
@require_professor
def view_test_result(subject, lesson_title, student_email):
    # Check if subject exists
    subject_key = subject
    if subject_key not in SUBJECTS:
        flash('Invalid subject.', 'error')
        return redirect(url_for('studio.dashboard'))
    
    # Get test result
    result_path = os.path.join(TESTE_DIR, subject_key, 'profesori', current_user.email, 'results', f'{lesson_title}_{student_email}.json')
    if not os.path.exists(result_path):
        flash('Test result not found.', 'error')
        return redirect(url_for('studio.view_test_results', subject=subject_key))
    
    # Load test result
    with open(result_path, 'r') as f:
        result = json.load(f)
    
    # Get original test
    test_path = os.path.join(TESTE_DIR, subject_key, 'profesori', current_user.email, f'{lesson_title}.json')
    if not os.path.exists(test_path):
        flash('Original test not found.', 'error')
        return redirect(url_for('studio.view_test_results', subject=subject_key))
    
    # Load original test
    with open(test_path, 'r') as f:
        test = json.load(f)
    
    # Get student name
    student = User.query.filter_by(email=student_email).first()
    student_name = student.name if student else student_email
    
    return render_template('studio_test_result_detail.html',
                         subject=SUBJECTS[subject_key],
                         test=test,
                         result=result,
                         student_name=student_name)