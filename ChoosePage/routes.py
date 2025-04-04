from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from models import User

choose_bp = Blueprint('choose', __name__,
                      template_folder='../Templates',
                      static_folder='../static/choose')

# Subject mapping (aligned with LearnPage/routes.py)
SUBJECTS = {
    'biologie': 'bio',
    'istorie': 'isto',
    'geografie': 'geogra'
}

FULL_SUBJECTS = {
    'biologie': 'Biologie',
    'istorie': 'Istorie',
    'geografie': 'Geografie'
}

@choose_bp.route('/choose', methods=['GET', 'POST'])
@login_required
def index():
    user = User.query.get(current_user.id)
    if user.user_type == 'profesor' and not user.is_professor_approved:
        return render_template('pending.html')

    if request.method == 'POST':
        user_type = request.form.get('user_type')
        subject_form = request.form.get('subject')  # e.g., 'biologie', 'istorie', 'geografie'

        if not user_type:
            flash('Please select if you are a student or teacher first!', 'error')
            return redirect(url_for('choose.index'))

        if not subject_form or subject_form not in SUBJECTS:
            flash('Please select a valid subject!', 'error')
            return redirect(url_for('choose.index'))

        # Map the form subject to the full name and short key
        user.user_type = user_type
        user.subject = FULL_SUBJECTS[subject_form]  # Store full name (e.g., "Biologie")
        subject_key = SUBJECTS[subject_form]  # Get short key (e.g., "bio")

        if user_type == 'profesor':
            user.is_professor_approved = False
        db.session.commit()

        if user_type == 'profesor':
            flash('Your professor account is pending admin approval.', 'info')
            return render_template('pending.html')
        else:
            flash('Selections saved successfully!', 'success')
            return redirect(url_for('learn.subject_page', subject_key=subject_key))  # Use short key

    return render_template('choose.html', template='choose_base.html')