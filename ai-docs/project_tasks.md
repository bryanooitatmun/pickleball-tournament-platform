# Project Tasks

## Current Bug Fixes

1. [ ] **Report Button Issue**
   - Report button works initially but doesn't work after scrolling
   - Need to investigate event handling after page scroll

2. [✅] **Doubles Matches Display Issues in Live Views**
   - Fixed issue where `match_detail.html` and `live_scoring.html` didn't properly display doubles matches
   - Consolidated `live_match.html` into `match_detail.html` to eliminate redundancy
   - Enhanced `match_detail.html` with live scoring functionality
   - Updated templates to conditionally render singles or doubles matches based on match.is_doubles
   - Improved display of team information in all match view templates

3. [ ] **Live Courts Incorrect Next Match Display**
   - `live_courts.html` not showing correct next match information
   - Example shows incorrect timing and match details for doubles matches

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

5. [ ] **Schedule Display Issues**
   - `schedule.html` not showing correctly
   - Categories by group stages if applicable not displaying properly
   - Player list doesn't take into account doubles matches

6. [ ] **Manage Category Issues**
   - ✅ Calculate placing form doesn't work (missing CSRF token) - Fixed by changing the template to use proper hidden input for CSRF token
   - Difficult to view long lists of matches
   - Need to improve organization - possibly view by groups, rounds, or player search
   - Generate bracket functionality broken - routes and template are mismatched

## Completed Tasks

- None currently

## Future Enhancements

- To be determined after bug fixes are completed