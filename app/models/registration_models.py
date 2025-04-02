from datetime import datetime
from flask import current_app
from sqlalchemy import Column, Integer, ForeignKey, String, Boolean, DateTime, Text, Float, Date
from sqlalchemy.orm import relationship
from app import db
from app.helpers.registration import calculate_age # Keep helper import if used directly

# Import necessary models using strings initially if needed, or adjust imports later
# from app.models.user_models import User, PlayerProfile
# from app.models.tournament_models import TournamentCategory

class Registration(db.Model):
    __tablename__ = 'registration'
    id = db.Column(db.Integer, primary_key=True)

    # Tournament relationship
    category_id = db.Column(db.Integer, db.ForeignKey('tournament_category.id'))

    # Links to player profiles when they exist
    player_id = db.Column(db.Integer, db.ForeignKey('player_profile.id'), nullable=True)
    partner_id = db.Column(db.Integer, db.ForeignKey('player_profile.id'), nullable=True)

    # Pre-profile player information (used if player_id is null)
    player1_name = db.Column(db.String(100), nullable=True)
    player1_email = db.Column(db.String(120), nullable=True)
    player1_phone = db.Column(db.String(20), nullable=True)
    player1_dupr_id = db.Column(db.String(50), nullable=True)
    player1_dupr_rating = db.Column(db.Float, nullable=True) # Fetched/Calculated
    player1_date_of_birth = db.Column(db.Date, nullable=True)
    player1_nationality = db.Column(db.String(50), nullable=True)
    player1_account_created = db.Column(db.Boolean, default=False) # Flag if account was auto-created
    player1_temp_password = db.Column(db.String(20), nullable=True) # Store temp password if auto-created
    player1_ic_number = db.Column(db.String(50), nullable=True)

    # Pre-profile partner information (used if partner_id is null and is_team_registration is true)
    player2_name = db.Column(db.String(100), nullable=True)
    player2_email = db.Column(db.String(120), nullable=True)
    player2_phone = db.Column(db.String(20), nullable=True)
    player2_dupr_id = db.Column(db.String(50), nullable=True)
    player2_dupr_rating = db.Column(db.Float, nullable=True) # Fetched/Calculated
    player2_date_of_birth = db.Column(db.Date, nullable=True)
    player2_nationality = db.Column(db.String(50), nullable=True)
    player2_account_created = db.Column(db.Boolean, default=False) # Flag if account was auto-created
    player2_temp_password = db.Column(db.String(20), nullable=True) # Store temp password if auto-created
    player2_ic_number = db.Column(db.String(50), nullable=True)

    # Registration logistics
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_approved = db.Column(db.Boolean, default=False) # Final approval status
    registration_fee = db.Column(db.Float, default=0.0)
    seed = db.Column(db.Integer, nullable=True) # For tournament seeding

    # Payment tracking
    payment_status = db.Column(db.String(20), default='pending') # pending, uploaded, paid, rejected, free
    payment_date = db.Column(db.DateTime, nullable=True)
    payment_reference = db.Column(db.String(100), nullable=True) # Reference code for payment
    payment_proof = db.Column(db.String(255), nullable=True) # Path to uploaded proof file
    payment_proof_uploaded_at = db.Column(db.DateTime, nullable=True)
    payment_notes = db.Column(db.Text, nullable=True) # Notes from player during upload
    payment_verified = db.Column(db.Boolean, default=False) # Has an organizer verified the proof?
    payment_verified_at = db.Column(db.DateTime, nullable=True)
    payment_verified_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) # User ID of verifier
    payment_rejection_reason = db.Column(db.Text, nullable=True) # Reason if payment proof rejected

    # Agreement tracking
    terms_agreement = db.Column(db.Boolean, default=False)
    liability_waiver = db.Column(db.Boolean, default=False)
    media_release = db.Column(db.Boolean, default=False)
    pdpa_consent = db.Column(db.Boolean, default=False)

    # Additional info
    special_requests = db.Column(db.Text, nullable=True)

    # Registration type flag
    is_team_registration = db.Column(db.Boolean, default=True) # True for doubles, False for singles

    # Admin fields
    admin_notes = db.Column(db.Text, nullable=True) # Internal notes by organizer/admin

    # Check-in status (added from requirements)
    checked_in = db.Column(db.Boolean, default=False)
    check_in_time = db.Column(db.DateTime, nullable=True)

    # Relationships (use strings)
    # category relationship defined in TournamentCategory model via backref
    # player relationship defined in PlayerProfile model via backref
    # partner relationship defined in PlayerProfile model via backref
    # verifier relationship defined in User model via backref

    @property
    def tournament(self):
        """Get the tournament through the category relationship"""
        # Ensure category is loaded
        if self.category:
            return self.category.tournament
        return None

    @property
    def team_name(self):
        """Return team name or player name for single registrations"""
        p1_display_name = self.player.full_name if self.player else self.player1_name
        if self.is_team_registration:
            p2_display_name = self.partner.full_name if self.partner else self.player2_name
            return f"{p1_display_name} / {p2_display_name}"
        else:
            return p1_display_name

    @property
    def team_dupr(self):
        """Calculate average DUPR rating for the team"""
        # Use fetched ratings stored on the registration model
        rating1 = self.player1_dupr_rating
        rating2 = self.player2_dupr_rating if self.is_team_registration else None

        if self.is_team_registration:
            if rating1 is not None and rating2 is not None:
                return (rating1 + rating2) / 2
            # Handle cases where one partner might have a rating
            elif rating1 is not None:
                return rating1 # Or decide how to handle partial ratings
            elif rating2 is not None:
                return rating2 # Or decide how to handle partial ratings
            else:
                return None # No ratings available
        else:
            # For singles, just return player1's rating
            return rating1

    @property
    def is_eligible(self):
        """Check if team/player is eligible for the selected category based on restrictions"""
        if not self.category:
            return False # Cannot determine eligibility without category info

        # Check DUPR Rating
        if self.category.min_dupr_rating is not None:
            if self.player1_dupr_rating is None or self.player1_dupr_rating < self.category.min_dupr_rating:
                return False
            if self.is_team_registration and (self.player2_dupr_rating is None or self.player2_dupr_rating < self.category.min_dupr_rating):
                return False
        if self.category.max_dupr_rating is not None:
            if self.player1_dupr_rating is None or self.player1_dupr_rating > self.category.max_dupr_rating:
                return False
            if self.is_team_registration and (self.player2_dupr_rating is None or self.player2_dupr_rating > self.category.max_dupr_rating):
                return False

        # Check Age
        p1_dob = self.player.date_of_birth if self.player else self.player1_date_of_birth
        p2_dob = self.partner.date_of_birth if self.partner else self.player2_date_of_birth

        if p1_dob:
            p1_age = calculate_age(p1_dob)
            if self.category.min_age is not None and p1_age < self.category.min_age:
                return False
            if self.category.max_age is not None and p1_age > self.category.max_age:
                return False
        else:
             # If DOB is missing, cannot verify age restriction - decide on policy (allow/deny)
             if self.category.min_age is not None or self.category.max_age is not None:
                 # current_app.logger.warning(f"Cannot verify age for registration {self.id} player 1 - DOB missing.")
                 pass # Or return False if strict age check required

        if self.is_team_registration and p2_dob:
            p2_age = calculate_age(p2_dob)
            if self.category.min_age is not None and p2_age < self.category.min_age:
                return False
            if self.category.max_age is not None and p2_age > self.category.max_age:
                return False
        elif self.is_team_registration:
             if self.category.min_age is not None or self.category.max_age is not None:
                 # current_app.logger.warning(f"Cannot verify age for registration {self.id} player 2 - DOB missing.")
                 pass # Or return False

        # Check Gender (Requires gender info on PlayerProfile or User model)
        # TODO: Implement gender check if gender_restriction and player gender data exist

        return True

    def fetch_dupr_ratings(self):
        """Fetch DUPR ratings from API based on DUPR IDs"""
        # Placeholder - Actual implementation needed
        self.player1_dupr_rating = self._fetch_dupr_rating(self.player1_dupr_id)
        if self.is_team_registration:
            self.player2_dupr_rating = self._fetch_dupr_rating(self.player2_dupr_id)

    def _fetch_dupr_rating(self, dupr_id):
        """Placeholder for DUPR API call"""
        if not dupr_id:
            return None
        # TODO: Implement actual API call to DUPR
        # import requests
        # url = f"https://api.mydupr.com/players/{dupr_id}/rating" # Example
        # try:
        #     response = requests.get(url, headers={'Authorization': 'Bearer YOUR_API_KEY'}) # Example auth
        #     if response.status_code == 200:
        #         data = response.json()
        #         # Extract the correct rating value (e.g., data.get('singlesRating') or data.get('doublesRating'))
        #         # This depends heavily on the actual API response structure
        #         rating = data.get('rating') # Placeholder
        #         if isinstance(rating, (int, float)):
        #             return float(rating)
        #         current_app.logger.warning(f"Unexpected DUPR rating format for {dupr_id}: {rating}")
        #     else:
        #          current_app.logger.error(f"DUPR API error for {dupr_id}: {response.status_code} - {response.text}")
        # except Exception as e:
        #     current_app.logger.error(f"Error fetching DUPR rating for {dupr_id}: {e}")
        return None # Return None if rating couldn't be fetched or validated

    def create_user_accounts(self):
        """Create user accounts for players if they don't exist."""
        # Import models locally to avoid circular imports at module level
        from app.models.user_models import User, PlayerProfile
        from app.helpers.registration import generate_temp_password

        user1 = None
        profile1 = None
        if self.player1_email and not self.player_id:
            user1 = User.query.filter_by(email=self.player1_email).first()
            if not user1:
                self.player1_temp_password = generate_temp_password()
                user1 = User(
                    username=self.player1_email.split('@')[0] + str(db.session.query(User).count() + 1), # Basic unique username
                    email=self.player1_email,
                    full_name=self.player1_name,
                    phone=self.player1_phone,
                    role='PLAYER', # Use string or UserRole enum if imported
                    ic_number=self.player1_ic_number
                )
                user1.set_password(self.player1_temp_password)
                db.session.add(user1)
                self.player1_account_created = True
                db.session.flush() # Get user1.id

                profile1 = PlayerProfile(
                    user_id=user1.id,
                    full_name=self.player1_name,
                    country=self.player1_nationality,
                    age=calculate_age(self.player1_date_of_birth) if self.player1_date_of_birth else None,
                    dupr_id=self.player1_dupr_id,
                    date_of_birth=self.player1_date_of_birth,
                )
                db.session.add(profile1)
                db.session.flush() # Get profile1.id
                self.player_id = profile1.id
            elif user1.player_profile:
                 self.player_id = user1.player_profile.id
            # Handle case where user exists but profile doesn't (less likely but possible)
            elif not user1.player_profile:
                 # Create profile with available data from registration
                 profile1 = PlayerProfile(
                     user_id=user1.id,
                     full_name=self.player1_name,
                     country=self.player1_nationality,
                     age=calculate_age(self.player1_date_of_birth) if self.player1_date_of_birth else None,
                     dupr_id=self.player1_dupr_id,
                     date_of_birth=self.player1_date_of_birth
                 )
                 db.session.add(profile1)
                 db.session.flush() # Get profile1.id
                 self.player_id = profile1.id


        user2 = None
        profile2 = None
        if self.is_team_registration and self.player2_email and not self.partner_id:
            user2 = User.query.filter_by(email=self.player2_email).first()
            if not user2:
                self.player2_temp_password = generate_temp_password()
                user2 = User(
                    username=self.player2_email.split('@')[0] + str(db.session.query(User).count() + 1), # Basic unique username
                    email=self.player2_email,
                    full_name=self.player2_name,
                    phone=self.player2_phone,
                    role='PLAYER', # Use string or UserRole enum if imported
                    ic_number=self.player2_ic_number
                )
                user2.set_password(self.player2_temp_password)
                db.session.add(user2)
                self.player2_account_created = True
                db.session.flush() # Get user2.id

                profile2 = PlayerProfile(
                    user_id=user2.id,
                    full_name=self.player2_name,
                    country=self.player2_nationality,
                    age=calculate_age(self.player2_date_of_birth) if self.player2_date_of_birth else None,
                    dupr_id=self.player2_dupr_id,
                    date_of_birth=self.player2_date_of_birth,
                )
                db.session.add(profile2)
                db.session.flush() # Get profile2.id
                self.partner_id = profile2.id
            elif user2.player_profile:
                self.partner_id = user2.player_profile.id
            elif not user2.player_profile:
                 # Create profile with available data from registration
                 profile2 = PlayerProfile(
                     user_id=user2.id,
                     full_name=self.player2_name,
                     country=self.player2_nationality,
                     age=calculate_age(self.player2_date_of_birth) if self.player2_date_of_birth else None,
                     dupr_id=self.player2_dupr_id,
                     date_of_birth=self.player2_date_of_birth
                 )
                 db.session.add(profile2)
                 db.session.flush() # Get profile2.id
                 self.partner_id = profile2.id

        # Commit changes if any accounts/profiles were created
        if self.player1_account_created or self.player2_account_created:
            try:
                db.session.commit()
                # Send emails only after successful commit
                self.send_confirmation_emails()
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error creating user accounts/profiles for registration {self.id}: {e}")
                # Optionally re-raise or handle the error

    def send_confirmation_emails(self):
        """Send confirmation emails to players, including temp passwords if accounts were created."""
        # Import locally
        from app.helpers.email_utils import send_email

        # Ensure category and tournament are loaded
        if not self.category or not self.tournament:
             current_app.logger.error(f"Cannot send confirmation for registration {self.id}: Missing category or tournament info.")
             return

        subject = f"Registration Confirmation - {self.tournament.name}"
        login_url = url_for('auth.login', _external=True) # Assuming url_for is available or imported

        # --- Email for Player 1 ---
        player1_email_to_send = self.player.user.email if self.player else self.player1_email
        player1_name_to_send = self.player.full_name if self.player else self.player1_name

        if player1_email_to_send:
            html_body_p1 = f"""
            <p>Dear {player1_name_to_send},</p>
            <p>Thank you for registering for <strong>{self.tournament.name}</strong> in the <strong>{self.category.name}</strong> category.</p>
            <p><strong>Team:</strong> {self.team_name}</p>
            <p><strong>Registration Fee:</strong> RM{self.registration_fee:.2f}</p>
            <p><strong>Payment Status:</strong> {self.payment_status.capitalize()}</p>
            """
            if self.player1_account_created and self.player1_temp_password:
                html_body_p1 += f"""
                <p>A temporary account has been created for you:</p>
                <ul>
                    <li><strong>Email:</strong> {self.player1_email}</li>
                    <li><strong>Temporary Password:</strong> {self.player1_temp_password}</li>
                </ul>
                <p>Please <a href="{login_url}">log in</a> to change your password and complete your profile.</p>
                """
            else:
                 html_body_p1 += f"""
                 <p>You can view your registration details by logging into your account.</p>
                 <p><a href="{login_url}">Log In Here</a></p>
                 """
            # Add payment instructions if applicable
            if self.payment_status == 'pending' and self.registration_fee > 0:
                 payment_url = url_for('player.payment', registration_id=self.id, _external=True)
                 html_body_p1 += f"""
                 <p><strong>Action Required:</strong> Please complete your payment of RM{self.registration_fee:.2f}.</p>
                 <p><a href="{payment_url}" style="display: inline-block; padding: 10px 15px; background-color: #007bff; color: white; text-decoration: none; border-radius: 4px;">Make Payment / Upload Proof</a></p>
                 """

            # Use a proper HTML email template structure
            full_html_p1 = f"<html><body>{html_body_p1}<p>Regards,<br>SportsSync Team</p></body></html>" # Basic structure
            try:
                send_email(subject, [player1_email_to_send], full_html_p1)
            except Exception as e:
                 current_app.logger.error(f"Failed to send confirmation email to {player1_email_to_send}: {e}")


        # --- Email for Player 2 (if applicable) ---
        if self.is_team_registration:
            player2_email_to_send = self.partner.user.email if self.partner else self.player2_email
            player2_name_to_send = self.partner.full_name if self.partner else self.player2_name

            if player2_email_to_send:
                html_body_p2 = f"""
                <p>Dear {player2_name_to_send},</p>
                <p>You have been registered by your partner for <strong>{self.tournament.name}</strong> in the <strong>{self.category.name}</strong> category.</p>
                <p><strong>Team:</strong> {self.team_name}</p>
                <p><strong>Registration Fee:</strong> RM{self.registration_fee:.2f}</p>
                <p><strong>Payment Status:</strong> {self.payment_status.capitalize()}</p>
                """
                if self.player2_account_created and self.player2_temp_password:
                    html_body_p2 += f"""
                    <p>A temporary account has been created for you:</p>
                    <ul>
                        <li><strong>Email:</strong> {self.player2_email}</li>
                        <li><strong>Temporary Password:</strong> {self.player2_temp_password}</li>
                    </ul>
                    <p>Please <a href="{login_url}">log in</a> to change your password and complete your profile.</p>
                    """
                else:
                     html_body_p2 += f"""
                     <p>You can view your registration details by logging into your account.</p>
                     <p><a href="{login_url}">Log In Here</a></p>
                     """
                # Add payment note (usually player 1 handles payment, but inform player 2)
                if self.payment_status == 'pending' and self.registration_fee > 0:
                     html_body_p2 += f"""
                     <p>Please coordinate with your partner ({player1_name_to_send}) to ensure payment is completed.</p>
                     """

                full_html_p2 = f"<html><body>{html_body_p2}<p>Regards,<br>SportsSync Team</p></body></html>" # Basic structure
                try:
                    send_email(subject, [player2_email_to_send], full_html_p2)
                except Exception as e:
                     current_app.logger.error(f"Failed to send confirmation email to {player2_email_to_send}: {e}")


    def __repr__(self):
        return f'<Registration {self.id} - Category {self.category_id} - Team {self.team_name}>'

# Need to import url_for for email links
from flask import url_for