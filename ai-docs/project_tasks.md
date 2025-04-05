# Pickleball Tournament Platform - Project Tasks

## Bug Fixes

1. [✅] **Payment Rejection Issue**
   - Problem: Payment rejection happens to the wrong user (e.g., when rejecting someone from women's doubles, it affects someone from men's doubles)
   - Priority: High
   - Files to check: (app\templates\organizer\verify_payments.html, app\templates\organizer\view_registration.html,
   app\templates\organizer\view_registrations.html, app\templates\organizer\manage_tournament\manage_registrations.html), app\organizer\registration_routes.py, payment verification and rejection logic

2. [✅] **Mobile UI Issues - Category Management**
   - Problem: Manage category tabs not working correctly on mobile devices
   - Details: Match filtering and search option tabs should be in a grid on mobile, but tabs are currently overflowing past their container
   - Priority: Medium
   - Files to check: app\templates\organizer\manage_tournament\manage_category.html
   - Additional improvements:
     - Added stage filtering via dropdown menu instead of tabs
     - Enhanced mobile table view below 1024px to prevent horizontal scrolling
     - Fixed participants display on mobile by styling the "vs" element appropriately
     - Removed redundant Group Stage and Knockout tabs from the filtering options

3. [✅] **Group Stage Scores Display**
   - Problem: Group stage scores need improvement on mobile view
   - Requirements:
     - Show scores in mobile page for Group stage similar to desktop version
     - Add tiebreaker stats for both desktop and mobile (hidden by default with toggle)
     - Add dropdown to filter by stages and groups
   - Priority: Medium
   - Files updated: 
     - app\templates\tournament\bracket.html (refactored into smaller sections)
     - Created app\templates\tournament\bracket_sections\ folder with component files

4. [✅] **Incorrect Round Details**
   - Problem: Live scoring and match detail showing wrong round details (e.g., group stages match from the GROUP_KNOCKOUT not showing correctly)
   - Priority: High
   - Files updated: 
     - app\models\match_models.py (enhanced round_name property for group stage matches)
     - app\templates\tournament\live_scoring.html (updated to use match.round_name)
     - app\templates\tournament\match_detail.html (updated to use match.round_name in all places)

5. [✅] **Tournament/Category Editing Issue**
   - Problem: Potential bug in edit tournament/category/prizes functionality
   - Details: An input exists that wipes out all category details
   - Priority: High
   - Files updated:
     - app\organizer\category_routes.py (fixed category update logic to prevent data loss)

6. [✅] **Image Aspect Ratio Problem**
   - Problem: Images throughout platform don't maintain aspect ratio, also all forms which have upload image input do not have javascript validation for images.
   - Example: Tournament banner images
   - Solution: Fix all images to maintain proper aspect ratio and have javascript validation for all forms fields which allows image upload. If possible, look to edit the js/css section of the app\templates\base.html file, and all templates will be extending this.
   - Priority: Medium
   - Files updated:
     - app\templates\base.html (added JavaScript validation for image uploads and CSS for proper aspect ratio)
     - app\templates\organizer\edit_tournament.html (added CSS classes for maintaining aspect ratio)
     - app\templates\organizer\edit_tournament\edit_sponsor.html (added CSS classes for maintaining aspect ratio)
     - app\templates\organizer\edit_tournament\edit_venue_details.html (added CSS classes for maintaining aspect ratio)
     - app\templates\player\edit_profile.html (added CSS classes for maintaining aspect ratio)
     - app\helpers\registration.py (enhanced image resizing to maintain proper aspect ratio based on image type)

## Feature Implementations

1. [✅] **User Interface Improvements**
   - Problem: Category and prize editing interfaces were difficult to use with many categories/prizes
   - Solution: Redesigned interfaces with collapsible sections, quick navigation, search, and mobile optimization
   - Priority: Medium
   - Files updated:
     - app\templates\organizer\edit_categories.html (complete redesign with improved navigation)
     - app\templates\organizer\edit_prizes.html (complete redesign with improved navigation and prize type management)

2. [ ] **Admin Account Management**
   - Feature: Admin should be able to create accounts, create tournaments, and assign referee and organizer roles to tournaments
   - Priority: High
   - Files to check: Admin routes, user management logic, tournament assignment functionality

## Testing Tasks

1. [ ] **Comprehensive Feature Testing**
   - Test edit tournament functionality
   - Test edit category functionality
   - Test edit prizes functionality
   - Identify any additional bugs or issues
   - Priority: Medium

## Notes
- ✅ symbol will be used to mark completed tasks
- All fixes should follow coding-preferences.mdc and workflow-preferences.mdc
- Ensure thorough testing after each fix
- Document any additional issues discovered during implementation
