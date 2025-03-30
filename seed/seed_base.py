"""
Base seeding utilities for the Pickleball Tournament Platform.
Contains common functions, database initialization, and app context handling.
"""

from app import db, create_app
import sys
import random
import string
from datetime import datetime, timedelta, date

# Create Flask app and push context
app = create_app()
app.app_context().push()

def reset_db():
    """Reset the database - drops and recreates all tables"""
    print("Dropping all tables...")
    db.drop_all()
    print("Creating all tables...")
    db.create_all()

def generate_reference(prefix="REF", length=8):
    """Generate a random alphanumeric reference code"""
    random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
    return f"{prefix}{random_suffix}"

def commit_changes(message="Changes committed successfully"):
    """Helper to commit changes and provide confirmation message"""
    try:
        db.session.commit()
        print(message)
        return True
    except Exception as e:
        db.session.rollback()
        print(f"Error: {e}")
        return False

def date_in_range(start_date, end_date=None):
    """Generate a random date between start_date and end_date (or today)"""
    if not end_date:
        end_date = datetime.now().date()
    
    time_between_dates = end_date - start_date
    days_between_dates = time_between_dates.days
    random_number_of_days = random.randrange(days_between_dates)
    
    return start_date + timedelta(days=random_number_of_days)

def random_phone():
    """Generate a random Malaysian phone number"""
    prefixes = ['011', '012', '013', '014', '016', '017', '018', '019']
    prefix = random.choice(prefixes)
    
    if prefix == '011':
        # 011 numbers have 8 digits
        number = ''.join(random.choices(string.digits, k=8))
    else:
        # Other numbers have 7-8 digits
        number = ''.join(random.choices(string.digits, k=random.choice([7, 8])))
    
    return f"+60{prefix}{number}"

def main():
    """Base initialization when this module is run directly"""
    if len(sys.argv) > 1 and sys.argv[1] == '--reset':
        reset_db()

if __name__ == "__main__":
    with app.app_context():
        main()
