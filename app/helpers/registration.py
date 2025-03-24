from datetime import datetime, date
import random
import string
from werkzeug.utils import secure_filename
import os

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

def calculate_age(birth_date):
    """Calculate age from birth date"""
    today = date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

def save_picture(picture, subfolder='tournament_pics'):
    # Generate a secure filename
    filename = secure_filename(picture.filename)
    
    # Generate a unique filename with timestamp
    unique_filename = f"{subfolder}_{int(datetime.utcnow().timestamp())}_{filename}"
    
    # Create full path
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], subfolder, unique_filename)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Save the file
    picture.save(file_path)
    
    # Return the relative path for the database
    return os.path.join('uploads', subfolder, unique_filename)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def generate_payment_reference(tournament):
    """Generate a unique payment reference"""
    prefix = tournament.payment_reference_prefix or "REF"
    random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"{prefix}{random_suffix}"
    
