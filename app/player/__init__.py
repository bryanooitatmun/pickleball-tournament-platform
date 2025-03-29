from flask import Blueprint

bp = Blueprint('player', __name__, template_folder='templates') # Define template folder if specific

# Import the new route modules to register the routes with the blueprint
from app.player import profile_routes
from app.player import registration_routes
from app.player import dashboard_routes

# The old 'from app.player import routes' is no longer needed
# If feedback routes are added later, import them here too:
# from app.player import feedback_routes
