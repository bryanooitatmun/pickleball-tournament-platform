from flask import Blueprint

bp = Blueprint('organizer', __name__, template_folder='templates') # Define template folder if specific

# Import the new route modules to register the routes with the blueprint
from app.organizer import registration_routes
from app.organizer import tournament_routes
from app.organizer import category_routes
from app.organizer import prize_routes
from app.organizer import venue_routes
from app.organizer import sponsor_routes
from app.organizer import match_routes

# The old 'from app.organizer import routes' is no longer needed
