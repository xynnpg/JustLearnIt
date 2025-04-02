from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db, bcrypt
from models import User

account_bp = Blueprint('account', __name__,
                       template_folder='../Templates',
                       static_folder='../static/account')


@account_bp.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    user = User.query.get(current_user.id)
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        user_type = request.form.get('value-radio')  # From radio buttons

        if email != user.email:
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                flash('This email is already in use. Please choose a different one.', 'error')
                return redirect(url_for('account.account'))

        user.name = name
        user.email = email
        if password:
            user.password = bcrypt.generate_password_hash(password).decode('utf-8')

        if user_type in ['elev', 'profesor']:
            user.user_type = user_type
            if user_type == 'profesor' and not user.is_professor_approved:
                user.is_professor_approved = False  # Reset approval if changing to professor
            elif user_type == 'elev':
                user.is_professor_approved = True  # No approval needed for students

        db.session.commit()
        flash('Account updated successfully!', 'success')
        return redirect(url_for('account.account'))

    return render_template('account.html', user=user)