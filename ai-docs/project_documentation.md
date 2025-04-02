# Project Documentation: Pickleball Tournament Platform

## 1. Introduction

This document provides detailed documentation for the Pickleball Tournament Platform, a comprehensive web application built using Flask. The platform facilitates the management of pickleball tournaments, including user registration, tournament creation, player participation, live scoring, match verification, ranking calculation, and administrative oversight.

## 2. Features

Based on the `README.md` and code analysis, the platform offers the following features:

*   **User Roles:** Distinct roles (Admin, Organizer, Referee, Player) with specific permissions and dashboards.
*   **Authentication:** Secure user login, registration, logout, and password reset functionality (email sending is currently a placeholder).
*   **Player Profiles:** Players can create and manage detailed profiles including personal information, playing style, equipment, social media links (Instagram, Facebook, Twitter, TikTok, XiaoHongShu), coach/academy affiliations, and images.
*   **Tournament Management:** Organizers can create, update, and manage tournaments, defining details like name, dates, location, description, tier, format, status, prize pool, logo, banner, payment settings, and door gifts.
*   **Category Management:** Organizers can define specific categories within a tournament (e.g., Men's Singles, Women's Doubles) with settings for:
    *   Maximum participants
    *   Points awarded
    *   Registration fees
    *   Eligibility restrictions (DUPR rating, age, gender)
    *   Custom prize and points distribution rules
    *   Format-specific settings (e.g., group stage configuration)
*   **Tournament Registration:** Players can register for tournament categories, including support for doubles partners (found via IC number lookup). The process includes agreement checkboxes and payment handling.
*   **Payment Processing:** Players upload proof of payment, which organizers can then verify or reject. Includes payment dashboard for organizers.
*   **Check-In & Live Status:** Players can check-in online before their matches. Organizers can see check-in status on the management dashboard.
*   **Bracket Generation & Seeding:** Organizers can generate tournament brackets based on selected formats (Single Elimination, Group Stage + Knockout). Includes automatic seeding and manual seeding adjustment.
*   **Match Scheduling & Court Assignment:** Organizers can assign courts and specific time slots to matches, with notifications for changes.
*   **Match Management:** Organizers/Referees can update match scores and determine winners, set by set.
*   **Score Verification:** Two-step verification process requiring both Referee and Player approval of match results.
*   **Livestream Integration:** Organizers can embed YouTube livestream links on match detail pages.
*   **Placing Calculation:** Automated calculation of final player/team placings within a category based on match results.
*   **Prize Distribution:** Automated calculation and potential distribution of prize money based on pre-defined rules.
*   **Player Rankings:** The system tracks player points per category based on tournament performance, viewable on a dedicated rankings page.
*   **Player Statistics:** Detailed player statistics including win/loss ratio and average match duration.
*   **Feedback/Rating System:** Players can submit tournament feedback with ratings, including anonymous submission option.
*   **Upcoming Match Bar:** Persistent UI element showing the player's next scheduled match with countdown.
*   **Live Match & Court View:** Real-time dashboard showing status of all courts in a tournament.
*   **Real-time Updates:** Uses WebSockets for live scoring and bracket updates.
*   **Email Notifications:** Automated emails for upcoming matches and schedule changes.
*   **Venue Management:** Organizers/Admins can create and manage venue information, including images.
*   **Sponsor Management:** Organizers/Admins can manage platform sponsors and associate them with specific tournaments.
*   **Admin Dashboard & Management:** Admins have oversight of users, tournaments, and players, with system statistics and the ability to manage user roles and activation status.
*   **Responsive Design:** Intended to work on various devices (as per README).
*   **Support System:** Basic support ticket system (`app/support`, `app/models.py`).

## 3. Technology Stack

*   **Backend Framework:** Flask
*   **Database:** SQLite (default, as per `config.py`)
*   **ORM:** Flask-SQLAlchemy
*   **Database Migrations:** Flask-Migrate
*   **Authentication:** Flask-Login
*   **Forms:** Flask-WTF
*   **CSRF Protection:** Flask-WTF
*   **Email:** Flask-Mail
*   **WebSockets:** Flask-SocketIO (for real-time updates)
*   **Task Scheduling:** APScheduler (for notifications)
*   **Frontend Styling:** Tailwind CSS (via CDN)
*   **Frontend Interactivity:** JavaScript
*   **Web Server (Deployment):** Nginx
*   **Application Server (Deployment):** Gunicorn
*   **Process Management (Deployment):** Systemd

## 4. Project Structure

```
pickleball-tournament-platform/
├── .env                      # Environment variables (needs creation)
├── .gitignore                # Git ignore rules
├── config.py                 # Application configuration classes
├── instance/                 # Instance folder (e.g., for SQLite DB)
│   └── app.db                # SQLite database file
├── migrations/               # Database migration scripts (Flask-Migrate)
├── package.json              # Frontend dependencies
├── package-lock.json         # Frontend dependency lock file
├── ai-docs/                  # Documents to store markdown files to the LLM to understand this project, and structuring tasks
│   ├── project_documentation.md  # This file
│   ├── project_requirements.md   # Project requirements
│   ├── project_tasks.md          # Project implementation tasks
│   ├── ...          
├── seed/                     # Seed files for starting out the project
│   ├── seed_main.py              # Main script that coordinates all seeding operations
│   ├── ... 
├── README.md                 # Project overview and setup guide
├── requirements.txt          # Python dependencies
├── run.py                    # Application entry point (for development server)
├── wsgi.py                   # WSGI entry point (for production servers like Gunicorn)
├── app/                      # Main application package
│   ├── __init__.py           # Application factory (create_app)
│   ├── decorators.py         # Custom decorators (e.g., @admin_required, @organizer_required)
│   ├── models/               # SQLAlchemy database models package
│   │   ├── __init__.py       # Makes models importable
│   │   ├── enums.py          # Enum definitions
│   │   ├── user_models.py    # User, PlayerProfile models
│   │   ├── tournament_models.py # Tournament, TournamentCategory models
│   │   ├── match_models.py   # Match, Team, Group, etc. models
│   │   ├── registration_models.py # Registration model
│   │   ├── venue_sponsor_models.py # Venue, Sponsor models
│   │   ├── support_models.py # SupportTicket models
│   │   ├── feedback_models.py # Feedback model
│   │   ├── prize_models.py   # Prize model
│   │   └── misc_models.py    # Equipment, Advertisement models
│   ├── models.py             # Compatibility import file (imports from app/models/)
│   ├── services/             # Service layer (e.g., BracketService, PlacingService)
│   ├── helpers/              # Helper functions (e.g., registration, tournament logic)
│   ├── static/               # Static files (CSS, JS, images)
│   │   └── uploads/          # User-uploaded files (profile pics, payment proofs, etc.)
│   ├── templates/            # Jinja2 HTML templates (organized by blueprint)
│   │   ├── admin/
│   │   ├── auth/
│   │   ├── email/
│   │   ├── errors/
│   │   ├── main/
│   │   ├── organizer/
│   │   ├── player/
│   │   ├── support/
│   │   ├── tournament/
│   │   └── base.html         # Base template
│   ├── scheduler.py          # Task scheduler initialization
│   ├── socket/               # SocketIO event handlers
│   ├── tasks/                # Scheduled tasks (e.g., email notifications)
│   ├── admin/                # Admin blueprint
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── auth/                 # Authentication blueprint
│   │   ├── __init__.py
│   │   ├── forms.py
│   │   └── routes.py
│   ├── errors/               # Error handling blueprint
│   │   ├── __init__.py
│   │   └── handlers.py
│   ├── main/                 # Main site blueprint (public pages)
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── organizer/            # Organizer blueprint
│   │   ├── __init__.py       # Imports route modules
│   │   ├── forms.py
│   │   ├── tournament_routes.py
│   │   ├── registration_routes.py
│   │   ├── category_routes.py
│   │   ├── prize_routes.py
│   │   ├── venue_routes.py
│   │   ├── sponsor_routes.py
│   │   └── match_routes.py
│   ├── player/               # Player blueprint
│   │   ├── __init__.py       # Imports route modules
│   │   ├── forms.py
│   │   ├── profile_routes.py
│   │   ├── registration_routes.py
│   │   ├── dashboard_routes.py
│   │   ├── checkin_routes.py
│   │   ├── feedback_routes.py
│   │   ├── feedback_forms.py
│   │   └── match_routes.py
│   ├── support/              # Support ticket blueprint
│   │   ├── __init__.py
│   │   ├── forms.py
│   │   └── routes.py
│   └── tournament/           # Tournament-specific blueprint (potentially shared views)
│       ├── __init__.py
│       ├── forms.py
│       └── routes.py
└── venv/                     # Virtual environment directory (if created)
└── tests/                     # Tests file directory
```

## 5. Configuration (`config.py`)

*   **`SECRET_KEY`**: Used for session security and CSRF protection. Loaded from environment variable or defaults to a placeholder.
*   **`SQLALCHEMY_DATABASE_URI`**: Database connection string (defaults to `sqlite:///app.db`).
*   **`SQLALCHEMY_TRACK_MODIFICATIONS`**: Disabled for performance.
*   **Upload Settings**: `UPLOAD_FOLDER`, `ALLOWED_EXTENSIONS`, `MAX_CONTENT_LENGTH`.
*   **Email Settings**: `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USE_TLS`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_DEFAULT_SENDER`. Loaded from environment variables with defaults.
*   **Session Settings**: `PERMANENT_SESSION_LIFETIME` (30 days).
*   **Admin Email**: `ADMIN_EMAIL` (used potentially for notifications).
*   **Tournament Settings**: Predefined `TOURNAMENT_TIERS`, `TOURNAMENT_FORMATS`, `TOURNAMENT_CATEGORIES`, and default `POINTS_DISTRIBUTION`.
*   **SocketIO Settings**: `SOCKETIO_CORS_ALLOWED_ORIGINS`, `SOCKETIO_ASYNC_MODE`.

## 6. Database Models (`app/models/`)

Defines the application's data structure using SQLAlchemy, organized into modules within the `app/models` package. Key models include:

*   **`user_models.py`**: 
    * `User`: Core user model with roles, authentication, and relationship mapping
    * `PlayerProfile`: Extended player information including social media, coach affiliation, and statistics
*   **`tournament_models.py`**:
    * `Tournament`: Tournament details, settings, and relationships
    * `TournamentCategory`: Category definitions, eligibility rules, and prize structures
*   **`match_models.py`**:
    * `Match`: Core match model with verification flags, court assignment, scheduling, and livestream URL
    * `MatchScore`: Individual set scores
    * `Team`: Team composition for doubles matches
    * `Group`: Group stage groupings
    * `GroupStanding`: Team/player standings within groups
*   **`registration_models.py`**:
    * `Registration`: Player registrations with check-in support
*   **`venue_sponsor_models.py`**:
    * `Venue`: Venue details and images
    * `VenueImage`: Supporting images for venues
    * `PlatformSponsor`: Platform-wide sponsors
    * `PlayerSponsor`: Individual player sponsors
*   **`support_models.py`**:
    * `SupportTicket`: Support ticket system
    * `TicketResponse`: Responses to support tickets
*   **`feedback_models.py`**:
    * `Feedback`: Tournament feedback and ratings
*   **`prize_models.py`**:
    * `Prize`: Prize details and distribution
*   **`misc_models.py`**:
    * `Equipment`: Player equipment
    * `Advertisement`: Platform advertisements
*   **`enums.py`**: Enumerations for consistent data typing
*   **`__init__.py`**: Imports all models for easier access

## 7. Application Flow & Blueprints

The application uses the Flask application factory pattern (`create_app` in `app/__init__.py`).

1.  **Initialization**: `create_app` initializes Flask, loads config, sets up extensions (DB, Migrate, Login, Mail, CSRF, SocketIO, APScheduler).
2.  **Blueprint Registration**: Different parts of the application are modularized into Blueprints, each registered with a specific URL prefix:
    *   `main` (/): Publicly accessible pages (homepage, events, rankings, public player/tournament views).
    *   `auth` (/auth): User authentication (login, logout, register, password reset).
    *   `player` (/player): Player-specific dashboard and actions.
    *   `organizer` (/organizer): Organizer-specific dashboard and actions.
    *   `admin` (/admin): Admin-specific dashboard and actions.
    *   `support` (/support): Handles support tickets.
    *   `tournament` (/tournament): Shared tournament views or actions.
    *   `errors`: Handles application-wide error pages (e.g., 404, 500).
3.  **SocketIO Setup**: Real-time functionality is enabled through the SocketIO extension.
4.  **Task Scheduler**: APScheduler is configured for scheduled tasks like email notifications.
5.  **Request Handling**: Incoming requests are routed to the appropriate blueprint and view function.
6.  **Decorators**: View functions are protected by decorators to enforce access control.
7.  **Templates**: Jinja2 templates are used to render HTML responses.

## 8. User Roles & Permissions

*   **Player (`UserRole.PLAYER`)**:
    *   Can register, log in, log out, reset password.
    *   Can create/edit their `PlayerProfile` with social media links and coach affiliation.
    *   Can register for tournaments (singles or doubles).
    *   Can view their registrations and payment status.
    *   Can upload payment proof.
    *   Can check-in for matches online.
    *   Can verify match results (after referee verification).
    *   Can submit tournament feedback and ratings.
    *   Can view the upcoming match bar with next match details.
    *   Can view public tournament/player details and rankings.
*   **Referee (`UserRole.REFEREE`)**:
    *   Can input scores and perform the first step of match result verification.
    *   Can view tournament brackets and match schedules.
*   **Organizer (`UserRole.ORGANIZER`)**:
    *   All Player permissions.
    *   Can create and manage `Tournament` details.
    *   Can create and manage `TournamentCategory` details.
    *   Can manage `Venue` and `PlatformSponsor` information.
    *   Can view and manage registrations (approve/reject payments).
    *   Can generate brackets and adjust seeding.
    *   Can schedule matches and assign courts.
    *   Can embed livestream links.
    *   Can enter match scores and verify as referee.
    *   Can calculate placings and distribute prizes.
*   **Admin (`UserRole.ADMIN`)**:
    *   All Organizer permissions.
    *   Can view an admin dashboard with system statistics.
    *   Can manage all `User` accounts (change roles, activate/deactivate).
    *   Can view details of all players, tournaments, and feedback.

## 9. Key Functionalities (Detailed)

*   **Authentication**: Uses Flask-Login. Stores password hashes (`werkzeug.security`). Redirects based on role after login.
*   **Profile Management**: Players use `ProfileForm` to create/edit `PlayerProfile` including social media links and coach affiliation. Images are saved using a helper function (`save_picture`).
*   **Tournament Creation**: Organizers use `TournamentForm` to create/edit `Tournament` objects. Includes image uploads for logo/banner.
*   **Category Management**: Organizers use `CategoryForm` (within `edit_categories` route) and manage settings directly in `manage_category` route. Includes complex settings like restrictions and prize/points distribution stored as JSON in the DB.
*   **Registration**: Players use `RegistrationForm`. Handles singles/doubles logic. Finds partners via IC number using an AJAX endpoint (`/find_user_by_ic`). Checks category limits and existing registrations. Creates `Registration` record with pending status. Fetches DUPR ratings via API call.
*   **Payment Verification**: Players upload proof via `PaymentForm`. Organizers view pending payments (`/registrations?status=pending`) and use buttons in `view_registration` to trigger `verify_registration` or `reject_registration` routes, updating the `Registration` status.
*   **Player Check-In**: Players can mark themselves as checked-in online before matches via `check_in_routes.py`.
*   **Bracket Generation & Seeding**: Triggered by organizers in `manage_category` or `generate_all_brackets`. Supports automatic seeding and manual adjustments. Uses helper functions to create `Match` objects based on `Registration` data and tournament format.
*   **Match Scheduling & Court Assignment**: Organizers use `MatchForm` to assign courts and schedule matches, with updates emitted via SocketIO.
*   **Score Entry & Verification**: Two-step verification process:
    1. Referee enters scores and verifies first (`referee_verified` flag)
    2. Player verifies after referee (`player_verified` flag)
    3. Only after both verifications is the match considered fully completed
*   **Livestream Embedding**: Organizers can add YouTube or other livestream URLs to match details.
*   **Real-time Updates**: Uses Flask-SocketIO for live scoring, bracket updates, and court status changes.
*   **Feedback System**: Players can submit feedback about tournaments with rating scale via `FeedbackForm`.
*   **Persistent Upcoming Match Bar**: Shows the player's next scheduled match with relevant details.
*   **Email Notifications**: APScheduler is used to send email notifications for upcoming matches and schedule changes.
*   **Rankings**: Points (`mens_singles_points`, etc.) are stored in `PlayerProfile`. The `/rankings` route queries `PlayerProfile` ordered by points.

## 10. Real-time Features (WebSockets)

The platform implements real-time features using Flask-SocketIO:

*   **Live Score Updates**: When scores are entered, updates are pushed to all clients viewing the match or tournament.
*   **Bracket Updates**: When matches are completed, bracket changes are broadcasted to all viewers.
*   **Court Status**: Real-time updates of which courts are active and what matches are in progress.
*   **Check-in Status**: Real-time updates when players check in for matches.
*   **Match Verification**: Updates when referees or players verify match results.

Key implementation components:
*   `app/socket/`: Contains SocketIO event handlers
*   `app/__init__.py`: Initializes SocketIO
*   `<tournament_id>` rooms: Clients join room for specific tournament updates
*   `emit()` calls: Used throughout the application to broadcast events

## 11. Task Scheduling & Notifications

The platform uses APScheduler for various tasks, particularly notifications:

*   **Email Reminders**: For upcoming matches (24 hours, 1 hour before)
*   **Schedule Changes**: When match timing or court assignment changes
*   **Tournament Announcements**: For updates and important notices

Key implementation components:
*   `app/scheduler.py`: Configures and initializes APScheduler
*   `app/tasks/`: Contains task definitions
*   `send_schedule_change_email()`: Example task function triggered when match details change

## 12. Setup & Running

Follow the instructions in `README.md`:

1.  Clone repository.
2.  Create and activate a Python virtual environment.
3.  Install dependencies: `pip install -r requirements.txt`.
4.  Create a `.env` file with necessary variables (`SECRET_KEY`, `FLASK_APP`, `FLASK_ENV`, `ADMIN_EMAIL`, potentially `MAIL_...` variables).
5.  Initialize database: `flask db init`, `flask db migrate`, `flask db upgrade`.
6.  Seed database: `python seed.py`.
7.  Run development server: `python run.py`.
8.  Access at `http://localhost:5000`.

## 13. Deployment (`README.md`)

The README provides basic steps for deploying on a Linux server using:

*   **Nginx:** As a reverse proxy. Requires configuration (`/etc/nginx/sites-available/pickleball`).
*   **Gunicorn/WSGI:** Implied by `wsgi.py`. The Flask app needs to be served by a WSGI server.
*   **Systemd:** To manage the application process as a service (`/etc/systemd/system/pickleball.service`).
*   Requires setting up file permissions (`chown www-data:www-data app.db`).

## 14. Dependencies (`requirements.txt`)

Contains a list of all Python packages required by the project, including:
* Flask and extensions (SQLAlchemy, Login, Migrate, WTF, Mail)
* Flask-SocketIO for real-time features
* APScheduler for task scheduling
* Other utility libraries (requests, Pillow, etc.)

## 15. Seeding (`seed.py`, `debug_seed.py`, etc.)

Scripts used to populate the database with initial data (e.g., admin user, sample players, tournaments, match brackets). `seed.py` is the main script mentioned in the setup.