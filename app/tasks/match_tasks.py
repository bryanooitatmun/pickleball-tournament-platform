from flask import current_app
from app.models import Match
from datetime import datetime, timedelta
from .email_tasks import send_match_reminder_email

def check_upcoming_matches():
    """
    Check for matches scheduled to start soon and send reminders.
    This function is intended to be scheduled to run regularly (e.g., every hour).
    """
    with current_app.app_context():
        # Find matches scheduled to start between 1 and 2 hours from now
        now = datetime.now()
        reminder_window_start = now + timedelta(hours=1)
        reminder_window_end = now + timedelta(hours=2)
        
        upcoming_matches = Match.query.filter(
            Match.completed == False,
            Match.scheduled_time.isnot(None),
            Match.scheduled_time >= reminder_window_start,
            Match.scheduled_time <= reminder_window_end
        ).all()
        
        current_app.logger.info(f"Found {len(upcoming_matches)} matches scheduled in the next 1-2 hours")
        
        # Send reminder emails for each match
        for match in upcoming_matches:
            send_match_reminder_email(match.id)
            
        # Also find matches starting in 24 hours for day-before reminders
        day_reminder_start = now + timedelta(hours=23)
        day_reminder_end = now + timedelta(hours=25)
        
        day_ahead_matches = Match.query.filter(
            Match.completed == False,
            Match.scheduled_time.isnot(None),
            Match.scheduled_time >= day_reminder_start,
            Match.scheduled_time <= day_reminder_end
        ).all()
        
        current_app.logger.info(f"Found {len(day_ahead_matches)} matches scheduled in ~24 hours")
        
        # Send 24-hour reminder emails
        for match in day_ahead_matches:
            send_match_reminder_email(match.id, is_day_before=True)
