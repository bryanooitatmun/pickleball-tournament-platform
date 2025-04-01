# Pickleball Tournament Platform - Project Tasks

## Tournament Bracket Enhancement

### Requirements

1. Enhance bracket generation and visualization with team/player coding
   - Assign code numbers to teams/players (A1, B2, etc. for group stage)
   - Show TBD matches as "A1 vs B2" for future matches
   - Implement coding for knockout stage (1, 2, 3, 4 for quarter matches)
   - Display 1 vs 2 for incomplete semi matches
   - Make sure bracket styling matches PPA bracket reference images

2. Implement seeding functionality
   - Create a page for organizers to view the participant list with their seeds
   - Allow organizers to drag and drop teams/players to different seeds
   - Implement back-end to store and use the seed changes

3. Implement tiebreak rules for groups
   - Primary: Head-to-head record with other tied players
   - Secondary: Number of points
   - Update the group standing calculation logic

4. Add support for byes in brackets
   - Handle scenarios where 2 teams per group from 5 groups advance (10 players in round of 16) (The numbers given is just an example, please handle generically for all cases)
   - Give top 6 seeds byes to quarters (free entry) (The numbers given is just an example, please handle generically for all cases)
   - Implement the logic for bye allocation

5. Simplify category configuration
   - Make it so only number of groups and teams advancing per group are necessary
   - Calculate teams per group programmatically
   - Update the relevant templates and routes

6. Implement bulk match editing
   - Create an interface for organizers to edit multiple matches at once
   - Add a confirmation step for review before saving changes

### Current Progress

❓ = Not started  
🔄 = In progress  
✅ = Completed

✅ Implement team/player coding system in brackets
✅ Create match visualization with code-based future matches (A1 vs B2)
✅ Implement knockout stage coding (1, 2, 3, 4)
✅ Update bracket visualization to match PPA bracket design
❓ Create seeding UI for drag and drop functionality
❓ Implement back-end for storing seed changes
❓ Update tiebreaking logic for group standings
❓ Implement bye logic for incomplete brackets
✅ Simplify category configuration inputs
❓ Implement bulk match editing functionality
❓ Add confirmation step for bulk edits

### Implementation Tasks Breakdown

#### 1. Team/Player Coding System

- ✅ Update the `tournament.py` helpers to assign codes based on group/position
- ✅ Modify the bracket generation code to include these codes
- ✅ Update `bracket.html` template to show codes for TBD matches
- ✅ Update `bracket-visualization.js` to handle and display codes
- ✅ Create thorough unit and integration tests _generate_cross_group_seeding in `tournament.py`.

#### 2. Seeding Interface

- ❓ Create new route and template for seeding management
- ❓ Implement drag and drop UI with JavaScript
- ❓ Update the back-end to store the seed changes
- ❓ Integrate with existing bracket generation code

#### 3. Tiebreak Implementation

- ❓ Update the `_calculate_group_positions` method in `bracket_service.py`
- ❓ Add head-to-head comparison as primary tiebreaker
- ❓ Use point differential as secondary tiebreaker
- ❓ Add tests for the new tiebreaking logic

#### 4. Bye Logic

- ❓ Update bracket generation in `tournament.py` to handle byes
- ❓ Modify the visualization to properly display byes
- ❓ Ensure the top seeds get byes when appropriate

#### 5. Simplified Category Configuration

- ✅ Update category registration logic to calculate teams per group
- ✅ Modify `category_routes.py` to handle the simplified inputs
- ✅ Update `tournament.py` to calculate teams per group

#### 6. Bulk Match Editing

- ❓ Design and implement UI for editing multiple matches
- ❓ Create new route for handling bulk updates
- ❓ Add confirmation step before applying changes
- ❓ Update templates and JavaScript for the new functionality

### Notes

- Reference the PPA bracket images for design inspiration
- Look at existing bracket generation logic in `tournament.py` and `bracket_service.py`
- Build upon the existing code where possible
- Add tests for all new functionality

### Recent Updates

- Added support for generating knockout brackets without completed group stage
- Enhanced position codes for all rounds of knockout matches, not just semis and finals
- Added automatic code generation for TBD matches in all tournament rounds
- Added test to verify knockout bracket generation works without completed group standings
- All TBD matches now display appropriate position codes (e.g., "A1 vs B2", "QF1 vs QF2")
