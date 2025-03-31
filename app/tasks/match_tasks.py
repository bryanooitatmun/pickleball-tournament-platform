from flask import current_app
from app.models import Match
from datetime import datetime, timedelta
from .email_tasks import send_match_reminder_email, send_schedule_change_email

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

def schedule_match_reminders(match_id):
    """
    Schedule reminders for a match.
    
    Args:
        match_id: The ID of the match to schedule reminders for
    """
    with current_app.app_context():
        match = Match.query.get(match_id)
        if not match or not match.scheduled_time:
            current_app.logger.error(f"Cannot schedule reminders for match {match_id}: Match not found or no scheduled time")
            return
        
        # Don't schedule reminders for completed matches or matches in the past
        if match.completed or match.scheduled_time < datetime.now():
            return
            
        scheduler = current_app.scheduler
        
        # Schedule 24-hour reminder
        day_before = match.scheduled_time - timedelta(hours=24)
        if day_before > datetime.now():
            scheduler.add_job(
                send_match_reminder_email,
                'date',
                run_date=day_before,
                args=[match_id, True],
                id=f'match_{match_id}_24h_reminder',
                replace_existing=True
            )
            
        # Schedule 1-hour reminder
        hour_before = match.scheduled_time - timedelta(hours=1)
        if hour_before > datetime.now():
            scheduler.add_job(
                send_match_reminder_email,
                'date',
                run_date=hour_before,
                args=[match_id, False],
                id=f'match_{match_id}_1h_reminder',
                replace_existing=True
            )
            
        current_app.logger.info(f"Scheduled reminders for match {match_id}")

def check_schedule_changes(match_id, original_court, original_time):
    """
    Check if a match's schedule or court has changed and send notification if needed.
    
    Args:
        match_id: The ID of the match
        original_court: The previous court assignment
        original_time: The previous scheduled time
    """
    with current_app.app_context():
        match = Match.query.get(match_id)
        if not match:
            current_app.logger.error(f"Cannot check schedule changes for match {match_id}: Match not found")
            return
            
        changes = {}
    
        # Check for court change
        if match.court != original_court:
            changes['court'] = match.court
            
        # Check for time change
        if match.scheduled_time and original_time and match.scheduled_time != original_time:
            changes['scheduled_time'] = match.scheduled_time
            
        # If there are changes, send notification
        if changes:
            send_schedule_change_email(match_id, changes)
            
            current_app.logger.info(f"Sent schedule change notification for match {match_id}")
