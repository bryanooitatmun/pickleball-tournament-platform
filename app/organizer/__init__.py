from flask import Blueprint

bp = Blueprint('organizer', __name__)

from app.organizer import routes
