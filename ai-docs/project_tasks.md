# Project Tasks

## Current Bug Fixes

1. [✅] **Report Button Issue**
   - Report button works initially but doesn't work after scrolling at app/template/tournaments/participants.html
   - Fixed by updating the toggleDropdown function to position the dropdown menu relative to the button using fixed positioning and window.scrollY
   - Added scroll event listener to update dropdown position when scrolling

2. [✅] **Doubles Matches Display Issues in Live Views**
   - Fixed issue where `match_detail.html` and `live_scoring.html` didn't properly display doubles matches
   - Consolidated `live_match.html` into `match_detail.html` to eliminate redundancy
   - Enhanced `match_detail.html` with live scoring functionality
   - Updated templates to conditionally render singles or doubles matches based on match.is_doubles
   - Improved display of team information in all match view templates

3. [✅] **Live Courts Incorrect Next Match Display**
   - Fixed issue with `app/templates/tournament/live_courts.html` not showing correct next match information
   - Updated the route logic to properly identify current and upcoming matches based on scheduled time
   - Fixed the template to properly display doubles matches with correctly nested team references
   - Added better time difference display with "ago" for past times

4. [✅] **Live Scoring "No Matches" Issue**
   - Fixed `live_scoring.html` incorrectly showing "no matches currently in progress" 
   - Updated query to also account for doubles matches:
     ```python
     ongoing_matches = Match.query.join(TournamentCategory).filter(
         TournamentCategory.tournament_id == id,
         Match.completed == False,
         # For singles matches OR doubles matches
         ((Match.player1_id.isnot(None) & Match.player2_id.isnot(None)) |
          (Match.team1_id.isnot(None) & Match.team2_id.isnot(None)))
     ).all()
     ```
   - Updated template to render doubles matches properly, showing both team members
   - Also updated API endpoint for scores to include doubles match information

5. [✅] **Schedule Display Issues**
   - Fixed `app/templates/tournament/schedule.html` display issues
   - Added proper group stage display in the schedule table
   - Fixed player list display for doubles matches using the proper team relationships
   - Added category filtering functionality to allow viewing schedule by specific category

6. [ ] **Manage Category Issues at app/template/organizer/manage_tournament/manage_category.html**
   - ✅ Calculate placing form doesn't work (missing CSRF token) - Fixed by changing the template to use proper hidden input for CSRF token
   - Difficult to view long lists of matches
   - Need to improve organization - possibly view by groups, rounds, or player search
   - Generate bracket functionality broken - routes and template are mismatched

## Future Enhancements

- To be determined after bug fixes are completed