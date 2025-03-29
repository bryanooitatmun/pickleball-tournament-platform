# Project Tasks: Pickleball Tournament Platform Enhancements

This document outlines the development tasks required to implement the new features based on the technical specification and project requirements.

## Phase 1: Backend Setup & Model Updates

1.  ✅ **Integrate Flask-SocketIO:**
    *   ✅ Add `Flask-SocketIO` to `requirements.txt`.
    *   ✅ Initialize Flask-SocketIO extension in `app/__init__.py`.
    *   ✅ Configure necessary settings in `config.py`.
2.  ✅ **Integrate Task Scheduler (Choose one: Celery or APScheduler):**
    *   ✅ Add chosen scheduler library to `requirements.txt`.
    *   ✅ Configure and initialize the scheduler.
    *   ✅ Set up basic task structure for later use with notifications.
3.  ✅ **Update Database Models (in `app/models/` package):**
    *   ✅ **`match_models.py` (Match):** Add `court` (String, renamed from `court_assignment`), `scheduled_time` (DateTime), `referee_verified` (Boolean), `player_verified` (Boolean), `livestream_url` (String).
    *   ✅ **`registration_models.py` (Registration):** Add `checked_in` (Boolean), `check_in_time` (DateTime).
    *   ✅ **`user_models.py` (PlayerProfile):** Add fields for `coach_academy` (String), `social_tiktok` (String), `social_xiaohongshu` (String). Add fields for detailed stats (consider JSON or separate related table if complex: `matches_won`, `matches_lost`, `avg_match_duration`, etc.).
    *   ✅ **`user_models.py` (User):** Add `digital_signature_hash` (String, optional for verification) or similar mechanism if needed.
    *   ✅ **New `feedback_models.py`:** Create `Feedback` model (fields: `user_id`, `tournament_id`, `organizer_id`, `rating` (Integer), `comment` (Text), `is_anonymous` (Boolean), `created_at`).
4.  ✅ **Create Database Migrations:**
    *   ✅ Created `run_migrations.py` script to generate and apply migrations.
    *   ✅ Script contains commands to run: `flask db migrate -m "Add new features models and fields"` and `flask db upgrade`.


## Phase 2: Organizer Features Implementation

1.  **Bracket Generation & Seeding:**
    *   **Backend:** Modify `BracketService` or helper functions (`app/helpers/tournament.py`). Implement logic in `app/organizer/match_routes.py` (e.g., `generate_all_brackets`) and potentially `app/organizer/category_routes.py` (`manage_category`) to trigger generation and handle manual seeding adjustments.
    *   **Frontend:** Create/Update `generate_bracket.html` (or integrate into category management template). Implement UI for manual seeding. Update `manage_registrations.html` (likely part of category management view) to display seeding.
2.  **Match Scheduling & Court Assignment:**
    *   **Backend:** Update `MatchForm` (`app/organizer/forms.py`). Update `update_match` route in `app/organizer/match_routes.py` to handle saving `court` and `scheduled_time`.
    *   **Frontend:** Create/Update `edit_match.html` (or integrate into match display/management UI).
3.  **Score Entry & Verification:**
    *   **Backend:** Update `ScoreForm` (`app/organizer/forms.py`). Modify `update_match` route in `app/organizer/match_routes.py` for score saving and verification flag logic. Implement SocketIO emits.
    *   **Frontend:** Create/Update `edit_score.html` (or integrate into match display/management UI). Add UI for Referee verification.
4.  **Player Check-In View:**
    *   **Backend:** Update `view_registrations` route in `app/organizer/registration_routes.py` (or relevant category management route) to fetch and pass check-in status.
    *   **Frontend:** Update `organizer/view_registrations.html` (or relevant category management template) to display check-in status.
5.  **Livestream Embedding:**
    *   **Backend:** Update `update_match` route in `app/organizer/match_routes.py` to save `livestream_url`. Update relevant public match display routes (e.g., in `app/main/routes.py`) to pass the URL.
    *   **Frontend:** Update public match detail templates (e.g., `main/match_detail.html`) to embed the player.

## Phase 3: Player Features Implementation


1.  **Player Check-In:**
    *   **Backend:** Create a new route in `app/player/registration_routes.py` (or a dedicated `checkin_routes.py`) like `/check_in/<registration_id>` to update `Registration` model. Protect with `@login_required`.
    *   **Frontend:** Add check-in button/logic to relevant player views (e.g., dashboard, tournament detail).
2.  **Player Dashboard Enhancement:**
    *   **Backend:** Update `dashboard` route in `app/player/dashboard_routes.py` to query and pass new profile/stat data.
    *   **Frontend:** Update `player/dashboard.html`.
3.  **Persistent Upcoming Match Bar:**
    *   **Backend:** Create an API endpoint (e.g., in `app/player/dashboard_routes.py` or a new `api_routes.py`) like `/api/next_match`.
    *   **Frontend:** Implement JS logic in `base.html` or a shared JS file to fetch and display data, handle clicks.
4.  **Feedback / Rating System:**
    *   **Backend:**
        *   Create `FeedbackForm` (e.g., in `app/player/forms.py` or `app/feedback/forms.py`).
        *   Create routes (e.g., in `app/player/feedback_routes.py` or integrate into existing player routes) for submission and viewing (admin/organizer).
        *   Implement saving logic for `Feedback` model.
    *   **Frontend:** Create feedback form template. Add links/buttons in relevant player views.
5.  **Player Profile Social Media:**
    *   **Backend:** Update `ProfileForm` (`app/player/forms.py`). Update `edit_profile` route in `app/player/profile_routes.py`. Update public profile routes (e.g., in `app/main/routes.py`) to pass data.
    *   **Frontend:** Update `player/edit_profile.html`. Update public templates (e.g., `main/player_detail.html`).
6.  **Player Match Verification:**
    *   **Backend:** Create a route (e.g., in `app/player/match_routes.py` or similar) like `/match/<match_id>/verify_player`. Protect and implement verification logic, check finalization, emit SocketIO update.
    *   **Frontend:** Add verification UI to match detail pages (e.g., `main/match_detail.html` or a player-specific view).
## Phase 4: Live Features & Notifications

1.  **Live Match & Court View:**
    *   **Backend:**
        *   Create a new route (e.g., `/live_courts/<tournament_id>`) that fetches current court assignments, active matches, and upcoming matches.
        *   Implement SocketIO event handlers (`on_connect`, `on_join_room`, etc.).
        *   Emit score/match updates from relevant backend actions (score entry, match finalization, scheduling changes) to specific tournament rooms.
    *   **Frontend:**
        *   Create `live_courts.html` template.
        *   Use JavaScript and SocketIO client library to connect, join the tournament room, and listen for events.
        *   Update the UI dynamically based on received SocketIO messages (scores, next match info).
2.  **Email Notifications:**
    *   **Backend:**
        *   Create email templates (e.g., in `app/templates/email/`).
        *   Implement task functions (e.g., in `app/tasks.py`) to send emails for reminders, changes, etc., using Flask-Mail.
        *   Schedule these tasks using Celery/APScheduler:
            *   Reminders: Schedule based on `Match.scheduled_time`.
            *   Changes: Trigger task immediately when schedule/court is updated.

## Phase 5: Roles, Permissions & Testing

1.  **Refine Roles & Permissions:**
    *   **Backend:** Add `Referee` role (`UserRole.REFEREE`). Ensure all relevant routes are protected with appropriate decorators (`@login_required`, `@organizer_required`, `@admin_required`, potentially a new `@referee_required`). Add specific checks within routes where needed (e.g., checking if user is referee or organizer for score entry).
2.  **Testing:**
    *   Write unit and integration tests for:
        *   Model changes and relationships.
        *   New service logic (Bracket generation, seeding, placing).
        *   Form validation.
        *   Route access control and permissions.
        *   Feedback submission.
        *   Score verification workflow.
        *   SocketIO event handling (basic tests).
        *   Notification task triggering (basic tests).
3.  **Code Review & Refactoring:**
    *   Review code against preferences (simplicity, DRY, file size).
    *   Refactor large files or complex functions.
    *   Ensure consistency and remove any unused old code.

## Phase 6: Deployment

1.  **Update Deployment Configuration:**
    *   Ensure Nginx/Gunicorn/Systemd configurations are updated for SocketIO (proxy settings) and the task scheduler (running worker processes).
2.  **Final Testing:** Perform end-to-end testing on the staging/production environment.