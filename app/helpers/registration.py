from datetime import datetime, date
from flask import current_app
import random
import string
from werkzeug.utils import secure_filename
from PIL import Image
import io
import os

def resize_image(image_data, max_size=1024, quality=85, subfolder=None):
    """
    Resize an image to a maximum width or height while maintaining aspect ratio
    
    Args:
        image_data: The binary image data
        max_size: Maximum width or height in pixels
        quality: JPEG quality (1-100)
        subfolder: Type of image (profile_pics, banner_pics, etc.) to apply specific handling
        
    Returns:
        Binary data of the resized image
    """
    try:
        # Create image from binary data
        img = Image.open(io.BytesIO(image_data))
        
        # Convert to RGB if it's in RGBA mode (for PNG with transparency)
        if img.mode == 'RGBA':
            img = img.convert('RGB')
        
        # Set desired aspect ratios and handling based on image type
        if subfolder == 'profile_pics':
            # For profile pictures, crop to square if needed
            if img.width != img.height:
                # Take the smaller dimension
                min_dimension = min(img.width, img.height)
                # Calculate crop box to create a centered square
                left = (img.width - min_dimension) // 2
                top = (img.height - min_dimension) // 2
                right = left + min_dimension
                bottom = top + min_dimension
                # Crop the image to a square
                img = img.crop((left, top, right, bottom))
        elif subfolder == 'banner_pics':
            # For banners, ensure wide format (3:1 ratio)
            # If it's not wide enough, add padding
            target_ratio = 3.0  # 3:1 aspect ratio
            current_ratio = img.width / img.height
            
            if current_ratio < target_ratio:
                # Image is not wide enough, add horizontal padding
                new_width = int(img.height * target_ratio)
                new_img = Image.new('RGB', (new_width, img.height), (255, 255, 255))  # White background
                paste_x = (new_width - img.width) // 2  # Center horizontally
                new_img.paste(img, (paste_x, 0))
                img = new_img
        
        # Check if resize is needed
        if img.width > max_size or img.height > max_size:
            # Calculate new dimensions maintaining aspect ratio
            if img.width > img.height:
                new_width = max_size
                new_height = int(img.height * (max_size / img.width))
            else:
                new_width = int(img.width * (max_size / img.height))
                new_height = max_size
                
            # Resize image
            img = img.resize((new_width, new_height), Image.LANCZOS)
        
        # Save to memory buffer
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=quality)
        buffer.seek(0)
        
        return buffer.getvalue()
    except Exception as e:
        current_app.logger.error(f"Error resizing image: {e}")
        raise ValueError(f"Error processing image: {str(e)}")


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

def save_payment_proof(proof_file, registration_id):
    return save_picture(proof_file, subfolder='payment_proofs', additional_text=registration_id)


def save_picture(picture, subfolder='tournament_pics', additional_text=''):
    """
    Save and resize image with specific handling based on image type
    
    Args:
        picture: The uploaded file (from form)
        subfolder: The subfolder to save to (e.g. profile_pics, tournament_logos)
        additional_text: Additional text to prepend to filename (e.g. user_id)
        
    Returns:
        The relative path to the saved file for database storage
    """
    try:
        if isinstance(picture, str):
            return picture

        # Read file data
        file_data = picture.read()
        
        # Check file size - limit to 5MB (5 * 1024 * 1024 bytes)
        max_file_size = 5 * 1024 * 1024  # 5MB in bytes
        if len(file_data) > max_file_size:
            raise ValueError(f"File size exceeds the 5MB limit")
            
        # Verify file is an image
        try:
            Image.open(io.BytesIO(file_data))
        except Exception:
            raise ValueError("Uploaded file is not a valid image")
        
        # Set max size based on image type
        max_size = 1024  # Default max size
        if subfolder in ['tournament_logos', 'profile_pics', 'sponsor_logos']:
            max_size = 800  # Square images for logos/profiles
        elif subfolder in ['tournament_banners', 'banner_pics']:
            max_size = 1500  # Larger for banners
        elif subfolder in ['venue_images']:
            max_size = 1200  # Medium for venue images
        
        # Resize image with appropriate handling based on subfolder
        resized_data = resize_image(file_data, max_size=max_size, subfolder=subfolder)
        
        # Create secure filename
        original_filename = secure_filename(picture.filename)
        filename = f"{additional_text}_{int(datetime.utcnow().timestamp())}_{original_filename}"
        
        # Create directory if it doesn't exist
        upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], subfolder)
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save file
        file_path = os.path.join(upload_dir, filename)
        with open(file_path, 'wb') as f:
            f.write(resized_data)
            
        # Return relative path for database
        return os.path.join('uploads', subfolder, filename)
    except Exception as e:
        current_app.logger.error(f"Error saving image: {e}")
        raise ValueError(str(e))


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def generate_payment_reference(tournament):
    """Generate a unique payment reference"""
    prefix = tournament.payment_reference_prefix or "REF"
    random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"{prefix}{random_suffix}"
    
