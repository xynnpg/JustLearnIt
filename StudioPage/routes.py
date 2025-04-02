from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db, logger
import os

studio_bp = Blueprint('studio', __name__,
                      template_folder='../Templates',
                      static_folder='../static/studio')

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, '../instance')
LECTII_DIR = os.path.join(INSTANCE_DIR, 'lectii')
TESTE_DIR = os.path.join(INSTANCE_DIR, 'teste')
SUBJECTS = ['Bio', 'Isto', 'Geogra']

# Create directories if they don’t exist
for subject in SUBJECTS:
    os.makedirs(os.path.join(LECTII_DIR, subject, 'profesori'), exist_ok=True)
    os.makedirs(os.path.join(TESTE_DIR, subject, 'profesori'), exist_ok=True)


def professor_required(func):
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or current_user.user_type != 'profesor' or not current_user.is_professor_approved:
            flash('You must be an approved professor to access this page.', 'error')
            return redirect(url_for('landing.index'))
        return func(*args, **kwargs)

    wrapper.__name__ = func.__name__
    return wrapper


@studio_bp.route('/lessons', methods=['GET', 'POST'])
@login_required
@professor_required
def lessons():
    subject = request.args.get('subject', 'Bio')  # Default to Bio
    if subject not in SUBJECTS:
        subject = 'Bio'

    lessons_dir = os.path.join(LECTII_DIR, subject, 'profesori')
    lessons = os.listdir(lessons_dir) if os.path.exists(lessons_dir) else []

    if request.method == 'POST':
        lesson_title = request.form.get('lesson_title')
        lesson_content = request.form.get('lesson_content')
        if lesson_title and lesson_content:
            file_path = os.path.join(lessons_dir, f"{lesson_title}.txt")
            with open(file_path, 'w') as f:
                f.write(lesson_content)
            flash(f'Lesson "{lesson_title}" saved for {subject}.', 'success')
            return redirect(url_for('studio.lessons', subject=subject))
        else:
            flash('Please provide both title and content.', 'error')

    return render_template('studio_lessons.html', subject=subject, subjects=SUBJECTS, lessons=lessons)


@studio_bp.route('/tests', methods=['GET', 'POST'])
@login_required
@professor_required
def tests():
    subject = request.args.get('subject', 'Bio')  # Default to Bio
    if subject not in SUBJECTS:
        subject = 'Bio'

    tests_dir = os.path.join(TESTE_DIR, subject, 'profesori')
    tests = os.listdir(tests_dir) if os.path.exists(tests_dir) else []

    if request.method == 'POST':
        test_title = request.form.get('test_title')
        test_content = request.form.get('test_content')
        if test_title and test_content:
            file_path = os.path.join(tests_dir, f"{test_title}.txt")
            with open(file_path, 'w') as f:
                f.write(test_content)
            flash(f'Test "{test_title}" saved for {subject}.', 'success')
            return redirect(url_for('studio.tests', subject=subject))
        else:
            flash('Please provide both title and content.', 'error')

    return render_template('studio_tests.html', subject=subject, subjects=SUBJECTS, tests=tests)


@studio_bp.route('/edit_lesson/<subject>/<lesson>', methods=['GET', 'POST'])
@login_required
@professor_required
def edit_lesson(subject, lesson):
    if subject not in SUBJECTS:
        flash('Invalid subject.', 'error')
        return redirect(url_for('studio.lessons'))

    file_path = os.path.join(LECTII_DIR, subject, 'profesori', lesson)
    if not os.path.exists(file_path):
        flash('Lesson not found.', 'error')
        return redirect(url_for('studio.lessons', subject=subject))

    if request.method == 'POST':
        new_content = request.form.get('lesson_content')
        if new_content:
            with open(file_path, 'w') as f:
                f.write(new_content)
            flash(f'Lesson "{lesson}" updated.', 'success')
            return redirect(url_for('studio.lessons', subject=subject))
        else:
            flash('Content cannot be empty.', 'error')

    with open(file_path, 'r') as f:
        content = f.read()

    return render_template('edit_lesson.html', subject=subject, lesson=lesson, content=content, subjects=SUBJECTS)