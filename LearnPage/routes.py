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

    professors_dir = os.path.join(subject_dir, 'profesori')
    if not os.path.exists(professors_dir):
        return lessons

    for professor_dir in os.listdir(professors_dir):
        prof_path = os.path.join(professors_dir, professor_dir)
        if os.path.isdir(prof_path):
            for lesson_file in os.listdir(prof_path):
                if lesson_file.endswith('.html'):

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
    subject_data = None
    for key, data in SUBJECTS.items():
        if key.lower() == subject_key.lower():
            subject_data = data
            subject_key = key
            break

    if not subject_data:
        flash('Invalid subject', 'error')
        return redirect(url_for('account.account'))

    lesson_dir = os.path.join(LECTII_DIR, subject_key, 'profesori', professor_email)
    lesson_file = os.path.join(lesson_dir, f"{lesson_title}.html")

    if not os.path.exists(lesson_file):
        flash('Lesson not found', 'error')
        return redirect(url_for('learn.professor_lessons', subject_key=subject_key, professor_email=professor_email))

    with open(lesson_file, 'r', encoding='utf-8') as f:
        content = f.read()

    test = None
    test_dir = os.path.join(TESTE_DIR, subject_key, 'profesori', professor_email)

    test_file = os.path.join(test_dir, f"{lesson_title}.json")
    if os.path.exists(test_file):
        with open(test_file, 'r', encoding='utf-8') as f:
            test = json.load(f)
    else:
        if os.path.exists(test_dir):
            for file in os.listdir(test_dir):
                if file.endswith('.json'):
                    with open(os.path.join(test_dir, file), 'r', encoding='utf-8') as f:
                        test_data = json.load(f)
                        if test_data.get('lesson') == lesson_title:
                            test = test_data
                            break

        if not test:
            test_file = os.path.join(test_dir, f"{lesson_title}_test.json")
            if os.path.exists(test_file):
                with open(test_file, 'r', encoding='utf-8') as f:
                    test = json.load(f)

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

    subject_data = None
    for key, data in SUBJECTS.items():
        if key.lower() == subject_key.lower():
            subject_data = data
            subject_key = key
            break

    if not subject_data:
        flash('Invalid subject', 'error')
        return redirect(url_for('account.account'))

    test_dir = os.path.join(TESTE_DIR, subject_key, 'profesori', professor_email)

    test_file = os.path.join(test_dir, f"{lesson_title}.json")
    if os.path.exists(test_file):
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

    if os.path.exists(test_dir):
        for file in os.listdir(test_dir):
            if file.endswith('.json'):
                with open(os.path.join(test_dir, file), 'r', encoding='utf-8') as f:
                    test_data = json.load(f)
                    if test_data.get('lesson') == lesson_title:
                        test_file = os.path.join(test_dir, file)
                        return render_template('take_test.html',
                                             subject=subject_data['name'],
                                             subject_key=subject_key,
                                             subject_color=subject_data['color'],
                                             subject_icon=subject_data['icon'],
                                             lesson_title=lesson_title,
                                             professor_email=professor_email,
                                             test=test_data)

    test_file = os.path.join(test_dir, f"{lesson_title}_test.json")
    if os.path.exists(test_file):
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

    flash('Test not found', 'error')
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

    test_dir = os.path.join(TESTE_DIR, subject_key, 'profesori', professor_email)

    test_file = os.path.join(test_dir, f"{lesson_title}.json")
    if os.path.exists(test_file):
        with open(test_file, 'r', encoding='utf-8') as f:
            test = json.load(f)
    else:

        test = None
        if os.path.exists(test_dir):
            for file in os.listdir(test_dir):
                if file.endswith('.json'):
                    with open(os.path.join(test_dir, file), 'r', encoding='utf-8') as f:
                        test_data = json.load(f)
                        if test_data.get('lesson') == lesson_title:
                            test_file = os.path.join(test_dir, file)
                            test = test_data
                            break

        if not test:
            test_file = os.path.join(test_dir, f"{lesson_title}_test.json")
            if os.path.exists(test_file):
                with open(test_file, 'r', encoding='utf-8') as f:
                    test = json.load(f)

    if not test:
        flash('Test not found', 'error')
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

    results_dir = os.path.join(test_dir, 'results')
    os.makedirs(results_dir, exist_ok=True)

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

    result_file = os.path.join(results_dir, f"{lesson_title}_{current_user.email}.json")
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)

    # Also save in grades directory
    grades_dir = os.path.join(INSTANCE_DIR, 'grades', current_user.email)
    os.makedirs(grades_dir, exist_ok=True)

    grade_data = {
        'subject': subject_key,
        'test_title': lesson_title,
        'professor_email': professor_email,
        'score': round(score_10_scale, 1),
        'date': datetime.now().isoformat(),
        'type': 'test'
    }

    grade_file = os.path.join(grades_dir, f"test_{subject_key}_{lesson_title}.json")
    with open(grade_file, 'w', encoding='utf-8') as f:
        json.dump(grade_data, f, indent=2)

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

    test_dir = os.path.join(TESTE_DIR, subject_key, 'profesori', professor_email)
    results = []

    if os.path.exists(test_dir):
        results_dir = os.path.join(test_dir, 'results')
        if os.path.exists(results_dir):
            for result_file in os.listdir(results_dir):
                if result_file.endswith('.json'):
                    with open(os.path.join(results_dir, result_file), 'r', encoding='utf-8') as f:
                        result_data = json.load(f)

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

    test_dir = os.path.join(TESTE_DIR, subject_key, 'profesori', professor_email)
    results_dir = os.path.join(test_dir, 'results')
    result_file = os.path.join(results_dir, f"{lesson_title}_{student_email}.json")

    if not os.path.exists(result_file):
        flash('Test result not found', 'error')
        return redirect(url_for('learn.view_test_results',
                              subject_key=subject_key,
                              professor_email=professor_email))

    with open(result_file, 'r', encoding='utf-8') as f:
        result = json.load(f)

    test_file = os.path.join(test_dir, f"{lesson_title}.json")
    if not os.path.exists(test_file):

        test = None
        if os.path.exists(test_dir):
            for file in os.listdir(test_dir):
                if file.endswith('.json'):
                    with open(os.path.join(test_dir, file), 'r', encoding='utf-8') as f:
                        test_data = json.load(f)
                        if test_data.get('lesson') == lesson_title:
                            test = test_data
                            break

        if not test:
            test_file = os.path.join(test_dir, f"{lesson_title}_test.json")
            if os.path.exists(test_file):
                with open(test_file, 'r', encoding='utf-8') as f:
                    test = json.load(f)
    else:
        with open(test_file, 'r', encoding='utf-8') as f:
            test = json.load(f)

    if not test:
        flash('Original test not found', 'error')
        return redirect(url_for('learn.view_test_results',
                              subject_key=subject_key,
                              professor_email=professor_email))

    student = User.query.filter_by(email=student_email).first()
    student_name = student.name if student else student_email

    return render_template('test_result_detail.html',
                         subject=subject_data['name'],
                         subject_key=subject_key,
                         subject_color=subject_data['color'],
                         subject_icon=subject_data['icon'],
                         professor_email=professor_email,
                         lesson_title=lesson_title,
                         student_name=student_name,
                         student_email=student_email,
                         test=test,
                         result=result)