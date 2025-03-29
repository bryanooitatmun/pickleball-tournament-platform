from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, IntegerField, SelectField, SubmitField, HiddenField, BooleanField
from wtforms.validators import DataRequired, Length, NumberRange, Optional

class FeedbackForm(FlaskForm):
    """Form for submitting feedback on tournaments or organizers"""
    # What the feedback is about (one or the other should be set)
    tournament_id = HiddenField('Tournament ID')
    organizer_id = HiddenField('Organizer ID')
    
    # Rating (1-5 stars)
    rating = SelectField('Rating', 
                      choices=[(1, '1 - Poor'), (2, '2 - Below Average'), (3, '3 - Average'), 
                               (4, '4 - Good'), (5, '5 - Excellent')],
                      coerce=int,
                      validators=[DataRequired()])
    
    # Feedback comment
    comment = TextAreaField('Comment', 
                        validators=[Optional(), Length(max=1000, message="Comment must be less than 1000 characters")],
                        render_kw={"placeholder": "Share your experience, feedback, and suggestions...", "rows": 5})
    
    # Privacy settings
    is_anonymous = BooleanField('Submit Anonymously', default=False, 
                             description="Your name will not be displayed with this feedback")
    
    submit = SubmitField('Submit Feedback')
    
    def validate(self, extra_validators=None):
        """Custom validation to ensure either tournament_id or organizer_id is set"""
        if not super(FeedbackForm, self).validate(extra_validators=extra_validators):
            return False
            
        # Ensure either tournament_id or organizer_id is set
        if not self.tournament_id.data and not self.organizer_id.data:
            self.tournament_id.errors = ['You must provide either a tournament or organizer to review']
            return False
            
        return True