from flask import Blueprint

bp = Blueprint('player', __name__)

from app.player import routes
