from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime
import os
import json
from functools import wraps
from . import studio_bp  # Import the blueprint from the package

# Constants
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, '../instance')
LECTII_DIR = os.path.join(INSTANCE_DIR, 'lectii')
TESTE_DIR = os.path.join(INSTANCE_DIR, 'teste')
SUBJECTS = ['Bio', 'Isto', 'Geogra']

# Create directories if they don't exist
for subject in SUBJECTS:
    os.makedirs(os.path.join(LECTII_DIR, subject, 'profesori'), exist_ok=True)
    os.makedirs(os.path.join(TESTE_DIR, subject, 'profesori'), exist_ok=True)

def require_professor(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.user_type != 'profesor' or not current_user.is_professor_approved:
            flash('You must be an approved professor to access this page.', 'error')
            return redirect(url_for('landing.index'))
        return f(*args, **kwargs)
    return decorated_function

@studio_bp.route('/')
@login_required
@require_professor
def studio():
    # Count lessons and tests for the dashboard
    lesson_count = 0
    test_count = 0
    try:
        for subject in SUBJECTS:
            lesson_dir = os.path.join(LECTII_DIR, subject, 'profesori')
            test_dir = os.path.join(TESTE_DIR, subject, 'profesori')
            if os.path.exists(lesson_dir):
                lesson_count += len([f for f in os.listdir(lesson_dir) if f.endswith('.html')])
            if os.path.exists(test_dir):
                test_count += len([f for f in os.listdir(test_dir) if f.endswith('.json')])
    except Exception as e:
        flash('Error counting lessons and tests', 'error')

    return render_template('studio.html', 
                         user=current_user,
                         lesson_count=lesson_count,
                         test_count=test_count)

# [Rest of your routes remain the same as in the previous implementation]