from flask_login import current_user
from app.models.enums import UserRole

def check_user_permission(permission_type=None):
    """
    Check if the current user has permission for a specific functionality
    
    Args:
        permission_type: The type of permission to check
        
    Returns:
        bool: True if the user has permission, False otherwise
    """
    # Admin has access to everything
    if current_user.is_admin():
        return True
        
    # Organizer has access to everything except admin-specific functions
    if current_user.is_organizer() and permission_type != 'admin_only':
        return True
        
    # Referee permissions
    if current_user.is_referee():
        # Referees can edit match scores
        if permission_type in ['edit_match_scores', 'view_tournament', 'view_category', 'view_matches']:
            return True
    
    # Default: no permission
    return False
