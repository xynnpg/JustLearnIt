from flask import Blueprint

studio_bp = Blueprint('studio', __name__,
                     template_folder='../Templates',
                     static_folder='../static/studio')

from . import routes