# Project Requirements: Pickleball Tournament Platform Enhancements

This document outlines the functional and non-functional requirements for the new features specified in the technical specification.

## 1. Functional Requirements

### 1.1 Organizer Features

*   **Tournament Creation & Management:**
    *   Organizers must be able to create new tournaments.
    *   The creation form must include fields for: Prize pool, points awarded per placing, tournament tier, format, location, time, and description.
    *   Organizers must be able to define multiple categories within a tournament (e.g., Men's Singles, Women's Doubles).
    *   Each category must allow for separate prize and points distribution settings.
    *   The primary template for tournament creation/editing is `organizer/manage_tournament/create_tournament.html`.
*   **Bracket & Seeding Management:**
    *   The system must generate tournament brackets based on the selected format (Single/Double Elimination, Round Robin, etc.).
    *   Bracket generation must support automatic seeding (based on player ranking/points).
    *   Organizers must have the ability to manually adjust seeding after generation (e.g., drag-and-drop or editing seed values).
    *   Relevant templates: `generate_bracket.html`, `manage_registrations.html`.
*   **Match Scheduling & Court Assignment:**
    *   Organizers must be able to assign specific courts (e.g., "Standard Court 1") to matches.
    *   Organizers must be able to assign specific start times to matches.
    *   This functionality should be available via an "edit match" interface.
    *   Relevant template: `edit_match.html`.
*   **Score Entry & Verification:**
    *   Organizers and Referees must be able to enter match scores, set by set.
    *   Relevant template: `edit_score.html`.
    *   Match results require verification from both the Referee entering the score AND the team captain (Player).
    *   Verification mechanism should be a digital signature or checkbox confirmation.
    *   Finalized results should only be processed after both verifications are complete.
*   **Player Check-In & Livestream:**
    *   Players must be able to mark themselves as checked-in online before their matches.
    *   Check-in status must be visible to organizers on the `manage_registrations.html` page.
    *   Organizers must be able to embed YouTube livestream links on match detail pages.

### 1.2 Player Features

*   **Dashboard & Profile:**
    *   The player dashboard must display: Name, photo, coach/academy affiliation, match history, detailed statistics (win/loss ratio, average match duration), and ranking points.
    *   Player profiles must display links/icons for social media: Instagram, Facebook, TikTok, XiaoHongShu.
    *   A persistent UI bar must be visible across pages displaying the player's next upcoming match details (opponent, court, time).
    *   Clicking the upcoming match bar should navigate the user to the relevant tournament page and highlight the player's name/match.
*   **Feedback / Rating System:**
    *   Players must be able to submit feedback about tournaments or organizers.
    *   Feedback submission must include a rating scale.
    *   Players must have the option to submit feedback anonymously.
    *   Consider implementing as a new module or extending the existing support ticket system.
*   **Social Media Integration:**
    *   Player profiles must allow storing and displaying links for Instagram, Facebook, TikTok, and XiaoHongShu.
    *   Relevant templates to display this info: `tournament/bracket.html`, `live_match.html`, `live_scoring.html`, `match_detail.html`, `participants.html`, `prize_distribution.html`, `results.html`, `schedule.html`.

### 1.3 Live Match & Court View

*   **Visual Dashboard:**
    *   A dedicated view must display the status of all courts in a tournament.
    *   For each court, the view must show:
        *   The currently active match with live scoring updates.
        *   The next scheduled match (opponent, court type/number, time).
    *   Updates to scores and bracket progression must be displayed in real-time.

### 1.4 Roles & Permissions

*   **Role Definitions:**
    *   **Organizer:** Full tournament management capabilities (create, edit, manage brackets, schedule, enter scores).
    *   **Referee:** Can input scores and perform the first step of match result verification.
    *   **Player:** Can register, check-in, view dashboards/tournaments, and perform the second step of match result verification (captain verification).
*   **Access Control:**
    *   Implement route protection using Flask-Login decorators based on user roles.

### 1.5 Notifications

*   **Email Alerts:**
    *   The system must send email notifications for:
        *   Upcoming match reminders.
        *   Schedule or court assignment changes.
        *   New system messages or announcements (if applicable).

## 2. Non-Functional Requirements

*   **Real-time Updates:** Live scoring and bracket updates must use WebSockets (Flask-SocketIO) for instant broadcasting.
*   **Usability:** Interfaces for bracket management (drag-and-drop seeding), scheduling, and score entry should be intuitive.
*   **Performance:** Real-time updates should be efficient and not overload the server. Database queries, especially for dashboards and rankings, should be optimized.
*   **Maintainability:** Code should follow specified coding patterns (simplicity, DRY, clean organization, file size limits). New features should integrate cleanly with the existing architecture.
*   **Testability:** Major functionality requires thorough testing.
*   **Security:** Role-based access control must be strictly enforced. Input validation is crucial for forms (scores, feedback, etc.).

## 3. Implementation Technologies

*   **Backend:** Python Flask, Flask-SQLAlchemy, Flask-Migrate, Flask-Login, Flask-WTF, Flask-SocketIO, Flask-Mail.
*   **Task Queue (Notifications):** Celery or APScheduler.
*   **Frontend:** HTML, CSS (Tailwind), JavaScript (for real-time updates, persistent bar, drag-and-drop).