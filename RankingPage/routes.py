from flask import render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from models import User
from . import ranking_bp

@ranking_bp.route('/ranking')
@login_required
def ranking():
    # Only students can access the ranking page
    if current_user.user_type != 'elev':
        flash('Only students can access the ranking page.', 'error')
        return redirect(url_for('landing.index'))
        
    # Get all students ordered by XP
    users = User.query.filter_by(user_type='elev').order_by(User.xp.desc()).all()
    
    # Update ranks
    for i, user in enumerate(users, 1):
        user.rank = i
        db.session.commit()
    
    return render_template('ranking/ranking.html', users=users, current_user=current_user)

@ranking_bp.route('/my_ranking')
@login_required
def my_ranking():
    # Only students can access their ranking
    if current_user.user_type != 'elev':
        flash('Only students can access their ranking.', 'error')
        return redirect(url_for('landing.index'))
        
    # Get user's rank
    rank = current_user.get_rank()
    return render_template('ranking/my_ranking.html', user=current_user, rank=rank)