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
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('landing.index'))

    if request.method == 'POST':
        try:
            name = request.form.get('name')
            email = request.form.get('email')
            password = request.form.get('password')
            user_type = request.form.get('value-radio')

            if email != user.email:
                existing_user = User.query.filter_by(email=email).first()
                if existing_user:
                    flash('This email is already in use. Please choose a different one.', 'error')
                    return redirect(url_for('account.account'))

            user.name = name
            user.email = email

            if password:
                if len(password) < 8:
                    flash('Password must be at least 8 characters long.', 'error')
                    return redirect(url_for('account.account'))
                user.password = bcrypt.generate_password_hash(password).decode('utf-8')

            if user_type in ['elev', 'profesor']:
                user.user_type = user_type
                if user_type == 'profesor' and not user.is_professor_approved:
                    user.is_professor_approved = False
                    flash('Your professor status is pending admin approval.', 'info')
                elif user_type == 'elev':
                    user.is_professor_approved = True

            db.session.commit()
            flash('Account updated successfully!', 'success')
            return redirect(url_for('account.account'))

        except Exception as e:
            db.session.rollback()
            flash('An error occurred while updating your account. Please try again.', 'error')
            return redirect(url_for('account.account'))

    return render_template('account.html', user=user)