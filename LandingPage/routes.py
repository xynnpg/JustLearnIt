from flask import Blueprint, render_template

landing_bp = Blueprint('landing', __name__,
                        template_folder='../Templates',
                        static_folder='../static/landing')

@landing_bp.route('/')
def index():
    return render_template('index.html')