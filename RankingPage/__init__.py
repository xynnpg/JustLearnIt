from flask import Blueprint

ranking_bp = Blueprint('ranking', __name__)

from . import routes