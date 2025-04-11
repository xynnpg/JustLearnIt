from flask import render_template, Blueprint

about_bp = Blueprint('about', __name__)

@about_bp.route('/about')
def about():
    return render_template('about.html') 