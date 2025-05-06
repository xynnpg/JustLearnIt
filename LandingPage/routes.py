from flask import Blueprint, render_template, redirect, url_for
from flask_login import current_user

landing_bp = Blueprint('landing', __name__,
                        template_folder='../Templates',
                        static_folder='../static/landing')

@landing_bp.route('/')
def index():
    return render_template('index.html')

@landing_bp.route('/inscrie-te')
def inscrie_te():
    if not current_user.is_authenticated:
        return redirect(url_for('login.login'))
    
    if current_user.user_type == 'elev':
        return redirect(url_for('learn.subject_page', subject_key=current_user.subject.lower()[:4]))
    elif current_user.user_type == 'profesor':
        if current_user.is_professor_approved:
            return redirect(url_for('studio.lessons'))
        else:
            return redirect(url_for('account.account'))
    else:
        return redirect(url_for('choose.index'))