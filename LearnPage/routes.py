from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from models import User
import os
import json

learn_bp = Blueprint('learn', __name__,
                     template_folder='../Templates',
                     static_folder='../static/learn')

# Configuration
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, '../instance')
LECTII_DIR = os.path.join(INSTANCE_DIR, 'lectii')
TESTE_DIR = os.path.join(INSTANCE_DIR, 'teste')

# Subject mapping
SUBJECTS = {
    'bio': {
        'name': 'Biologie',
        'color': '#4CAF50',
        'icon': 'fas fa-leaf'
    },
    'isto': {
        'name': 'Istorie',
        'color': '#FF5722',
        'icon': 'fas fa-landmark'
    },
    'geogra': {
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

    return User.query.filter_by(
        user_type='profesor',
        is_professor_approved=True,
        subject=subject_name
    ).all()


def get_lessons_for_subject(subject_key):
    """Get all lessons for a subject"""
    lessons = []
    subject_dir = os.path.join(LECTII_DIR, subject_key)

    if not os.path.exists(subject_dir):
        return lessons

    for professor_dir in os.listdir(os.path.join(subject_dir, 'profesori')):
        prof_path = os.path.join(subject_dir, 'profesori', professor_dir)
        if os.path.isdir(prof_path):
            for lesson_file in os.listdir(prof_path):
                if lesson_file.endswith('.html'):
                    lessons.append({
                        'professor': professor_dir,
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
    test_dir = os.path.join(TESTE_DIR, subject_key, 'profesori', professor_email)
    if not os.path.exists(test_dir):
        return None

    for test_file in os.listdir(test_dir):
        if test_file.endswith('.json'):
            with open(os.path.join(test_dir, test_file), 'r') as f:
                test_data = json.load(f)
                if test_data.get('lesson') == lesson_title:
                    return test_data
    return None


@learn_bp.route('/learn/<subject_key>')
@login_required
def subject_page(subject_key):
    """Main subject page showing professors and lessons"""
    if subject_key not in SUBJECTS:
        flash('Invalid subject selected', 'error')
        return redirect(url_for('choose.index'))

    subject_data = SUBJECTS[subject_key]
    professors = get_professors_for_subject(subject_key)
    lessons = get_lessons_for_subject(subject_key)

    return render_template('learn_subject.html',
                           subject=subject_data['name'],
                           subject_key=subject_key,
                           subject_color=subject_data['color'],
                           subject_icon=subject_data['icon'],
                           professors=professors,
                           lessons=lessons)


@learn_bp.route('/learn/<subject_key>/<professor_email>')
@login_required
def professor_lessons(subject_key, professor_email):
    """Show all lessons from a specific professor"""
    if subject_key not in SUBJECTS:
        flash('Invalid subject selected', 'error')
        return redirect(url_for('choose.index'))

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
                           subject=SUBJECTS[subject_key]['name'],
                           subject_key=subject_key,
                           professor=professor,
                           lessons=lessons)


@learn_bp.route('/learn/<subject_key>/<professor_email>/<lesson_title>')
@login_required
def view_lesson(subject_key, professor_email, lesson_title):
    """View a specific lesson"""
    if subject_key not in SUBJECTS:
        flash('Invalid subject selected', 'error')
        return redirect(url_for('choose.index'))

    content = get_lesson_content(subject_key, professor_email, lesson_title)
    if not content:
        flash('Lesson not found', 'error')
        return redirect(url_for('learn.professor_lessons',
                                subject_key=subject_key,
                                professor_email=professor_email))

    test = get_test_for_lesson(subject_key, professor_email, lesson_title)

    return render_template('view_lesson.html',
                           subject=SUBJECTS[subject_key]['name'],
                           subject_key=subject_key,
                           professor_email=professor_email,
                           lesson_title=lesson_title,
                           content=content,
                           test=test)