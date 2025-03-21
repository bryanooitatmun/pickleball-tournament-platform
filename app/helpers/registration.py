from datetime import datetime
import random
import string

def generate_payment_reference(tournament):
    """Generate a unique payment reference for a tournament registration"""
    prefix = tournament.payment_reference_prefix or "PCKL"
    timestamp = datetime.now().strftime('%y%m%d%H%M')
    random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    
    return f"{prefix}-{timestamp}-{random_chars}"

def generate_temp_password(length=10):
    """Generate a random temporary password"""
    # Include at least one of each: uppercase, lowercase, digit, special char
    uppercase = random.choice(string.ascii_uppercase)
    lowercase = random.choice(string.ascii_lowercase)
    digit = random.choice(string.digits)
    special = random.choice('!@#$%^&*')
    
    # Generate remaining characters
    remaining_length = length - 4
    all_chars = string.ascii_letters + string.digits + '!@#$%^&*'
    remaining = ''.join(random.choices(all_chars, k=remaining_length))
    
    # Combine all and shuffle
    password = uppercase + lowercase + digit + special + remaining
    password_list = list(password)
    random.shuffle(password_list)
    
    return ''.join(password_list)