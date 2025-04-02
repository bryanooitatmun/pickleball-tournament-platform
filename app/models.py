# This file is kept for backward compatibility.
# New code should import directly from the specific model files
# within the app.models package (e.g., from app.models.user_models import User)
# or from the package itself (e.g., from app.models import User).

from app.models.enums import *
from app.models.user_models import *
from app.models.tournament_models import *
from app.models.match_models import *
from app.models.registration_models import *
from app.models.venue_sponsor_models import *
from app.models.support_models import *
from app.models.feedback_models import *  # Import the new Feedback model
from app.models.prize_models import *
from app.models.misc_models import *

# Note: The load_user function is defined in user_models.py and is automatically
# registered with Flask-Login via the @login.user_loader decorator.
# No need to re-import or re-define it here.

# It's recommended to eventually update all imports throughout the project
# to point to the specific modules (e.g., app.models.user_models)
# or the package init (app.models) and then potentially remove this file.