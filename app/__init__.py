from flask import Flask, flash, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from config import Config
from flask_mail import Mail
from flask_wtf.csrf import CSRFProtect
import os

db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()
login = LoginManager()
login.login_view = 'auth.login'
login.login_message = 'Please log in to access this page.'

mail = Mail()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)  # Initialize mail
    login.init_app(app)
    
    # Initialize CSRF protection
    csrf.init_app(app)
    
    # Ensure the uploads directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
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

    return app
