from flask import Blueprint

learn_bp = Blueprint('learn', __name__,
                     template_folder='../Templates',
                     static_folder='../static/learn')

from . import routes