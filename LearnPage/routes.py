from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from models import User
import os

learn_bp = Blueprint('learn', __name__,
                     template_folder='../Templates',
                     static_folder='../static')

SUBJECTS = ['bio', 'isto', 'geogra']
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, '../instance')
LECTII_DIR = os.path.join(INSTANCE_DIR, 'lectii')
TESTE_DIR = os.path.join(INSTANCE_DIR, 'teste')


def get_lessons_for_subject(subject):
    lessons = []
    subject_dir = os.path.join(LECTII_DIR, subject)
    if os.path.exists(subject_dir):
        for prof_dir in os.listdir(subject_dir):
            prof_path = os.path.join(subject_dir, prof_dir)
            if os.path.isdir(prof_path):
                for lesson_file in os.listdir(prof_path):
                    if lesson_file.endswith('.html'):
                        lessons.append({
                            'professor': prof_dir.replace('profesori/', ''),
                            'title': lesson_file.replace('.html', ''),
                            'path': os.path.join(prof_path, lesson_file)
                        })
    return lessons


def get_tests_for_lesson(lesson_title, subject):
    tests = []
    subject_dir = os.path.join(TESTE_DIR, subject)
    if os.path.exists(subject_dir):
        for prof_dir in os.listdir(subject_dir):
            prof_path = os.path.join(subject_dir, prof_dir)
            if os.path.isdir(prof_path):
                for test_file in os.listdir(prof_path):
                    if test_file.endswith('.json'):
                        with open(os.path.join(prof_path, test_file), 'r') as f:
                            test_data = json.load(f)
                            if test_data.get('lesson') == lesson_title:
                                tests.append({
                                    'title': test_file.replace('.json', ''),
                                    'professor': prof_dir.replace('profesori/', ''),
                                    'question_count': len(test_data.get('questions', []))
                                })
    return tests


@learn_bp.route('/learn/<subject>')
@login_required
def subject_page(subject):
    if subject not in SUBJECTS:
        flash('Invalid subject selected', 'error')
        return redirect(url_for('choose.index'))

    if current_user.user_type != 'elev':
        flash('Only students can access this page', 'error')
        return redirect(url_for('account.account'))

    # Get all professors for this subject
    professors = User.query.filter_by(
        user_type='profesor',
        is_professor_approved=True,
        subject=subject
    ).all()

    lessons = get_lessons_for_subject(subject)

    return render_template('learn_subject.html', subject=subject)



@learn_bp.route('/learn/<subject>/<professor_email>')
@login_required
def professor_lessons(subject, professor_email):
    if subject not in SUBJECTS:
        flash('Invalid subject selected', 'error')
        return redirect(url_for('choose.index'))

    professor = User.query.filter_by(email=professor_email).first()
    if not professor or not professor.is_professor_approved:
        flash('Professor not found', 'error')
        return redirect(url_for('learn.subject_page', subject=subject))

    lessons = []
    prof_dir = os.path.join(LECTII_DIR, subject, 'profesori', professor_email)
    if os.path.exists(prof_dir):
        for lesson_file in os.listdir(prof_dir):
            if lesson_file.endswith('.html'):
                lessons.append({
                    'title': lesson_file.replace('.html', ''),
                    'path': os.path.join(prof_dir, lesson_file)
                })

    return render_template('professor_lessons.html',
                           subject=subject.capitalize(),
                           professor=professor,
                           lessons=lessons)


@learn_bp.route('/learn/<subject>/<professor_email>/<lesson>')
@login_required
def view_lesson(subject, professor_email, lesson):
    lesson_path = os.path.join(LECTII_DIR, subject, 'profesori', professor_email, f"{lesson}.html")
    if not os.path.exists(lesson_path):
        flash('Lesson not found', 'error')
        return redirect(url_for('learn.professor_lessons', subject=subject, professor_email=professor_email))

    with open(lesson_path, 'r') as f:
        content = f.read()

    # Get associated test
    test = None
    tests_dir = os.path.join(TESTE_DIR, subject, 'profesori', professor_email)
    if os.path.exists(tests_dir):
        for test_file in os.listdir(tests_dir):
            if test_file.endswith('.json'):
                with open(os.path.join(tests_dir, test_file), 'r') as f:
                    test_data = json.load(f)
                    if test_data.get('lesson') == lesson:
                        test = {
                            'title': test_file.replace('.json', ''),
                            'questions': test_data.get('questions', [])
                        }
                        break

    return render_template('view_lesson.html',
                           subject=subject.capitalize(),
                           professor_email=professor_email,
                           lesson_title=lesson,
                           content=content,
                           test=test)