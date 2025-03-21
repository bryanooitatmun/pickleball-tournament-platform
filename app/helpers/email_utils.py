from flask import render_template, current_app
from flask_mail import Message
from threading import Thread
from datetime import datetime
from app import mail

def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)

def send_email(subject, recipients, html_body, text_body=None, sender=None, attachments=None):
    """
    Send an email asynchronously.
    
    Args:
        subject (str): The email subject line
        recipients (list): List of email addresses to send to
        html_body (str): HTML content of the email
        text_body (str, optional): Plain text version of the email
        sender (str, optional): Email sender address (defaults to app config)
        attachments (list, optional): List of (filename, mime_type, file_data) tuples
    """
    app = current_app._get_current_object()
    
    # If sender not specified, use the default from config
    if sender is None:
        sender = current_app.config['MAIL_DEFAULT_SENDER']
    
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.html = html_body
    
    if text_body:
        msg.body = text_body
    
    if attachments:
        for attachment in attachments:
            filename, mime_type, file_data = attachment
            msg.attach(filename=filename, content_type=mime_type, data=file_data)
    
    # Send email asynchronously
    Thread(target=send_async_email, args=(app, msg)).start()

def send_registration_confirmation_email(registration):
    """Send a registration confirmation email to the player"""
    player = registration.player
    tournament = registration.category.tournament
    category = registration.category
    
    # Generate payment URL
    payment_url = f"{current_app.config['SITE_URL']}/player/payment/{registration.id}"
    tournament_url = f"{current_app.config['SITE_URL']}/tournament/{tournament.id}"
    
    # Context data for the email template
    context = {
        'player': player,
        'tournament': tournament,
        'category': category,
        'registration': registration,
        'payment_url': payment_url,
        'tournament_url': tournament_url,
        'current_year': datetime.now().year
    }
    
    subject = f"Registration Confirmation - {tournament.name}"
    html_body = render_template('emails/registration_confirmation.html', **context)
    
    # Send the email
    send_email(
        subject=subject,
        recipients=[player.user.email],
        html_body=html_body
    )

def send_payment_verified_email(registration):
    """Send a payment verified confirmation email to the player"""
    player = registration.player
    tournament = registration.category.tournament
    category = registration.category
    
    # Generate tournament URL
    tournament_url = f"{current_app.config['SITE_URL']}/tournament/{tournament.id}"
    
    # Context data for the email template
    context = {
        'player': player,
        'tournament': tournament,
        'category': category,
        'registration': registration,
        'tournament_url': tournament_url,
        'current_year': datetime.now().year
    }
    
    subject = f"Payment Confirmed - {tournament.name}"
    html_body = render_template('emails/payment_verified.html', **context)
    
    # Send the email
    send_email(
        subject=subject,
        recipients=[player.user.email],
        html_body=html_body
    )

def send_payment_rejected_email(registration):
    """Send a payment rejected email to the player"""
    player = registration.player
    tournament = registration.category.tournament
    category = registration.category
    
    # Generate payment URL
    payment_url = f"{current_app.config['SITE_URL']}/player/payment/{registration.id}"
    
    # Context data for the email template
    context = {
        'player': player,
        'tournament': tournament,
        'category': category,
        'registration': registration,
        'payment_url': payment_url,
        'current_year': datetime.now().year
    }
    
    subject = f"Payment Rejected - {tournament.name}"
    html_body = render_template('emails/payment_rejected.html', **context)
    
    # Send the email
    send_email(
        subject=subject,
        recipients=[player.user.email],
        html_body=html_body
    )