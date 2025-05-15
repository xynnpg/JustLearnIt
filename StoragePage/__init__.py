from flask import Blueprint

storage_bp = Blueprint('storage', __name__)

from . import routes 