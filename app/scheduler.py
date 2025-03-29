from flask_apscheduler import APScheduler
from app.tasks.match_tasks import check_upcoming_matches

scheduler = APScheduler()

def init_scheduler(app):
    """
    Initialize and configure the APScheduler instance with the provided Flask app.
    
    Args:
        app: Flask application instance
    """
    # Configure the scheduler with Flask app
    scheduler.init_app(app)
    
    # Add scheduled jobs
    if not scheduler.get_job('check_upcoming_matches'):
        scheduler.add_job(
            id='check_upcoming_matches',
            func=check_upcoming_matches,
            trigger='interval',
            hours=1,  # Run every hour
            replace_existing=True
        )
    
    # Start the scheduler
    scheduler.start()
    
    app.logger.info("APScheduler initialized and started")
