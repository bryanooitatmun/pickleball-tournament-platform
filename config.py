import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard-to-guess-string'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    FLASK_ENV=os.environ.get('FLASK_ENV', 'development')
    
    # Upload configurations
    UPLOAD_FOLDER = os.path.join(basedir, 'app', 'static', 'uploads')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB max upload
    
    # Email configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.example.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@sportssync.asia')

    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)
    
    # Admin email
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL') or 'admin@example.com'
    
    # Socket.IO configuration
    SOCKETIO_CORS_ALLOWED_ORIGINS = os.environ.get('SOCKETIO_CORS_ALLOWED_ORIGINS', '*')
    SOCKETIO_ASYNC_MODE = os.environ.get('SOCKETIO_ASYNC_MODE', 'eventlet')
    
    # APScheduler configuration
    SCHEDULER_API_ENABLED = False  # Disable the API for security
    SCHEDULER_TIMEZONE = "UTC"
    SCHEDULER_JOB_DEFAULTS = {
        'coalesce': False,
        'max_instances': 3
    }
    
    # Tournament configuration
    TOURNAMENT_TIERS = [
        {'name': 'SLATE', 'points': 2000, 'color': 'blue'},
        {'name': 'CUP', 'points': 3200, 'color': 'gray'},
        {'name': 'OPEN', 'points': 1400, 'color': 'indigo'},
        {'name': 'CHALLENGE', 'points': 925, 'color': 'red'}
    ]
    
    TOURNAMENT_FORMATS = [
        'Single Elimination',
        'Double Elimination',
        'Round Robin',
        'Group Stage + Knockout'
    ]
    
    TOURNAMENT_CATEGORIES = [
        {'id': 'mens_singles', 'name': "Men's Singles"},
        {'id': 'womens_singles', 'name': "Women's Singles"},
        {'id': 'mens_doubles', 'name': "Men's Doubles"},
        {'id': 'womens_doubles', 'name': "Women's Doubles"},
        {'id': 'mixed_doubles', 'name': "Mixed Doubles"}
    ]
    
    # Points distribution by placement (% of total points)
    POINTS_DISTRIBUTION = {
        1: 100,    # Winner gets 100% of available points
        2: 70,     # Runner-up gets 70% of available points
        3: 50,     # Semi-finalist gets 50%
        4: 40,     # Semi-finalist gets 40%
        5: 25,     # Quarter-finalist gets 25%
        6: 25,     # Quarter-finalist gets 25%
        7: 25,     # Quarter-finalist gets 25%
        8: 25,     # Quarter-finalist gets 25%
        9: 15,     # Round of 16 gets 15%
        # ... and so on
    }
