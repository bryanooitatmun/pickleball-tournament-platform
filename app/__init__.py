from flask import Flask, flash, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from config import Config
from flask_mail import Mail
from flask_wtf.csrf import CSRFProtect
from flask_socketio import SocketIO  # Added for real-time features
import os

db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()
login = LoginManager()
login.login_view = 'auth.login'
login.login_message = 'Please log in to access this page.'
mail = Mail()
socketio = SocketIO()  # Initialize SocketIO

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    login.init_app(app)
    csrf.init_app(app)
    
    # Initialize SocketIO with the app and enable CORS
    socketio.init_app(app, 
                     cors_allowed_origins=app.config['SOCKETIO_CORS_ALLOWED_ORIGINS'],
                     async_mode=app.config['SOCKETIO_ASYNC_MODE'])
    
    # Initialize APScheduler for task scheduling
    from app.scheduler import init_scheduler
    init_scheduler(app)
    
    # Ensure the uploads directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Add environment and enums to template context
    @app.context_processor
    def inject_global_vars():
        from app.models.enums import TournamentStatus, UserRole
        return dict(
            ENV=app.config.get('FLASK_ENV', 'production'),
            TournamentStatus=TournamentStatus,
            UserRole=UserRole
        )
    
    # Register blueprints
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)
    
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    from app.player import bp as player_bp
    app.register_blueprint(player_bp, url_prefix='/player')
    
    from app.tournament import bp as tournament_bp
    app.register_blueprint(tournament_bp, url_prefix='/tournament')
    
    from app.organizer import bp as organizer_bp
    app.register_blueprint(organizer_bp, url_prefix='/organizer')
    
    from app.admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    from app.support import bp as support_bp
    app.register_blueprint(support_bp, url_prefix='/support')
    
    # Register error handlers
    from app.errors import register_error_handlers
    register_error_handlers(app)
    
    # Add the nl2br filter
    @app.template_filter('nl2br')
    def nl2br_filter(text):
        if not text:
            return ""
        return text.replace('\n', '<br>')
    
    @app.errorhandler(413)
    def request_entity_too_large(error):
        flash("File too large! Please upload an image smaller than 5MB.", "danger")
        return redirect(request.referrer)

    # Import and register Socket.IO event handlers
    with app.app_context():
        from app.socket import register_socketio_handlers
        register_socketio_handlers(socketio)

    return app
