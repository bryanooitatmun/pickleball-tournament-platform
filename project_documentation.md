# Project Documentation: Pickleball Tournament Platform

## 1. Introduction

This document provides detailed documentation for the Pickleball Tournament Platform, a comprehensive web application built using Flask. The platform facilitates the management of pickleball tournaments, including user registration, tournament creation, player participation, live scoring (implied), ranking calculation, and administrative oversight.

## 2. Features

Based on the `README.md` and code analysis, the platform offers the following features:

*   **User Roles:** Distinct roles (Admin, Organizer, Player) with specific permissions and dashboards.
*   **Authentication:** Secure user login, registration, logout, and password reset functionality (email sending is currently a placeholder).
*   **Player Profiles:** Players can create and manage detailed profiles including personal information, playing style, equipment, social links, and images.
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
*   **Bracket Generation:** Organizers can generate tournament brackets based on selected formats (Single Elimination, Group Stage + Knockout). Seeding logic is implied.
*   **Match Management:** Organizers can update match scores and determine winners.
*   **Placing Calculation:** Automated calculation of final player/team placings within a category based on match results.
*   **Prize Distribution:** Automated calculation and potential distribution of prize money based on pre-defined rules.
*   **Player Rankings:** The system tracks player points per category based on tournament performance, viewable on a dedicated rankings page.
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
*   **Forms:** Flask-WTF (implied by form imports)
*   **CSRF Protection:** Flask-WTF
*   **Email:** Flask-Mail (setup in `config.py` and `app/__init__.py`)
*   **Frontend Styling:** Tailwind CSS (via CDN, as per README)
*   **Web Server (Deployment):** Nginx (recommended in README)
*   **Application Server (Deployment):** Gunicorn (implied by `wsgi.py`)
*   **Process Management (Deployment):** Systemd (recommended in README)

## 4. Project Structure

```
pickleball-tournament-platform/
├── .env                      # Environment variables (needs creation)
├── .gitignore                # Git ignore rules
├── config.py                 # Application configuration classes
├── db_diagnostics.py         # Database diagnostic script
├── debug_seed.py             # Debug seeding script
├── instance/                 # Instance folder (e.g., for SQLite DB)
│   └── app.db                # SQLite database file
├── migrations/               # Database migration scripts (Flask-Migrate)
├── package.json              # Frontend dependencies (if any, likely for Tailwind setup)
├── package-lock.json         # Frontend dependency lock file
├── project_documentation.md  # This file
├── README.md                 # Project overview and setup guide
├── requirements.txt          # Python dependencies
├── reset_db.py               # Script to reset the database
├── run.py                    # Application entry point (for development server)
├── seed.py                   # Main database seeding script
├── seed_old.py               # Older seeding script version
├── seed_user.py              # User-specific seeding script
├── test_db.py                # Database testing script
├── wsgi.py                   # WSGI entry point (for production servers like Gunicorn)
├── app/                      # Main application package
│   ├── __init__.py           # Application factory (create_app)
│   ├── decorators.py         # Custom decorators (e.g., @admin_required, @organizer_required)
│   ├── models/               # SQLAlchemy database models package
│   │   ├── __init__.py       # Makes models importable (e.g., from app.models import User)
│   │   ├── enums.py          # Enum definitions
│   │   ├── user_models.py    # User, PlayerProfile models
│   │   ├── tournament_models.py # Tournament, TournamentCategory models
│   │   ├── match_models.py   # Match, Team, Group, etc. models
│   │   ├── registration_models.py # Registration model
│   │   ├── venue_sponsor_models.py # Venue, Sponsor models
│   │   ├── support_models.py # SupportTicket models
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
│   │   ├── errors/
│   │   ├── main/
│   │   ├── organizer/
│   │   ├── player/
│   │   ├── support/
│   │   ├── tournament/
│   │   └── base.html         # Base template
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
│   │   └── dashboard_routes.py
│   ├── support/              # Support ticket blueprint
│   │   ├── __init__.py
│   │   ├── forms.py
│   │   └── routes.py
│   └── tournament/           # Tournament-specific blueprint (potentially shared views)
│       ├── __init__.py
│       ├── forms.py
│       └── routes.py         # (May contain routes or be used by other blueprints)
└── venv/                     # Virtual environment directory (if created)
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

## 6. Database Models (`app/models/`)

Defines the application's data structure using SQLAlchemy, organized into modules within the `app/models` package. Key models include:

*   **`user_models.py`**: `User`, `PlayerProfile`. Includes `UserMixin` for Flask-Login and the `load_user` function.
*   **`tournament_models.py`**: `Tournament`, `TournamentCategory`, `partnerships` association table.
*   **`match_models.py`**: `Match`, `MatchScore`, `Team`, `Group`, `GroupStanding`.
*   **`registration_models.py`**: `Registration`.
*   **`venue_sponsor_models.py`**: `Venue`, `VenueImage`, `PlatformSponsor`, `PlayerSponsor`, `tournament_sponsors` association table.
*   **`support_models.py`**: `SupportTicket`, `TicketResponse`.
*   **`prize_models.py`**: `Prize`.
*   **`misc_models.py`**: `Equipment`, `Advertisement`.
*   **`enums.py`**: Contains all `enum.Enum` definitions (e.g., `UserRole`, `TournamentTier`, `CategoryType`).
*   **`__init__.py`**: Imports all models and enums for easier access (e.g., `from app.models import User`).
*   **`app/models.py`**: (Outer file) Maintained for backward compatibility, imports everything from the `app/models` package.

## 7. Application Flow & Blueprints

The application uses the Flask application factory pattern (`create_app` in `app/__init__.py`).

1.  **Initialization**: `create_app` initializes Flask, loads config, sets up extensions (DB, Migrate, Login, Mail, CSRF).
2.  **Blueprint Registration**: Different parts of the application are modularized into Blueprints, each registered with a specific URL prefix:
    *   `main` (/): Publicly accessible pages (homepage, events, rankings, public player/tournament views). Routes defined in `app/main/routes.py`.
    *   `auth` (/auth): User authentication (login, logout, register, password reset). Routes defined in `app/auth/routes.py`.
    *   `player` (/player): Player-specific dashboard and actions. Routes are split into modules (`profile_routes.py`, `registration_routes.py`, `dashboard_routes.py`) imported by `app/player/__init__.py`.
    *   `organizer` (/organizer): Organizer-specific dashboard and actions. Routes are split into modules (`tournament_routes.py`, `registration_routes.py`, `category_routes.py`, etc.) imported by `app/organizer/__init__.py`.
    *   `admin` (/admin): Admin-specific dashboard and actions. Routes defined in `app/admin/routes.py`.
    *   `support` (/support): Handles support tickets. Routes defined in `app/support/routes.py`.
    *   `tournament` (/tournament): Potentially shared tournament views or actions. Routes defined in `app/tournament/routes.py`.
    *   `errors`: Handles application-wide error pages (e.g., 404, 500). Handlers defined in `app/errors/handlers.py`.
3.  **Request Handling**: Incoming requests are routed to the appropriate blueprint and view function based on the URL and the imported route modules.
4.  **Decorators**: View functions are often protected by decorators (`@login_required`, `@organizer_required`, `@admin_required`) to enforce access control based on user authentication and role.
5.  **Templates**: Jinja2 templates located in `app/templates/` (organized by blueprint) are used to render HTML responses.

## 8. User Roles & Permissions

*   **Player (`UserRole.PLAYER`)**:
    *   Can register, log in, log out, reset password.
    *   Can create/edit their `PlayerProfile`.
    *   Can register for tournaments (singles or doubles).
    *   Can view their registrations and payment status.
    *   Can upload payment proof.
    *   Can view public tournament/player details and rankings.
    *   Access restricted to `main`, `auth`, and `player` blueprints (plus `support`).
*   **Organizer (`UserRole.ORGANIZER`)**:
    *   All Player permissions.
    *   Can create and manage `Tournament` details.
    *   Can create and manage `TournamentCategory` details within their tournaments.
    *   Can manage `Venue` and `PlatformSponsor` information.
    *   Can view and manage registrations for their tournaments (approve/reject payments).
    *   Can generate brackets and manage `Match` scores for their tournaments.
    *   Can calculate placings and distribute prizes.
    *   Access restricted to `main`, `auth`, `player`, `organizer` blueprints (plus `support`). Requires `@organizer_required` decorator for organizer-specific actions.
*   **Admin (`UserRole.ADMIN`)**:
    *   All Organizer permissions (implicitly, often checked via `or current_user.is_admin()`).
    *   Can view an admin dashboard with system statistics.
    *   Can manage all `User` accounts (change roles, activate/deactivate).
    *   Can view details of all players and tournaments.
    *   Access to all blueprints. Requires `@admin_required` decorator for admin-specific actions.

## 9. Key Functionalities (Detailed)

*   **Authentication**: Uses Flask-Login. Stores password hashes (`werkzeug.security`). Redirects based on role after login.
*   **Profile Management**: Players use `ProfileForm` to create/edit `PlayerProfile`. Images are saved using a helper function (`save_picture`).
*   **Tournament Creation**: Organizers use `TournamentForm` to create/edit `Tournament` objects. Includes image uploads for logo/banner.
*   **Category Management**: Organizers use `CategoryForm` (within `edit_categories` route) and manage settings directly in `manage_category` route. Includes complex settings like restrictions and prize/points distribution stored as JSON in the DB.
*   **Registration**: Players use `RegistrationForm`. Handles singles/doubles logic. Finds partners via IC number using an AJAX endpoint (`/find_user_by_ic`). Checks category limits and existing registrations. Creates `Registration` record with pending status. Fetches DUPR ratings via API call (placeholder/potential external dependency).
*   **Payment Verification**: Players upload proof via `PaymentForm`. Organizers view pending payments (`/registrations?status=pending`) and use buttons in `view_registration` to trigger `verify_registration` or `reject_registration` routes, updating the `Registration` status.
*   **Bracket Generation**: Triggered by organizers in `manage_category` or `generate_all_brackets`. Uses helper functions (`_generate_group_stage`, `_generate_single_elimination`, etc.) in `app/helpers/tournament.py` to create `Match` objects based on `Registration` data and tournament format. Seeding logic likely exists within these helpers.
*   **Match Scoring**: Organizers use `CompleteMatchForm` (within `update_match` route) to input scores and select winners for `Match` objects. Updates `MatchScore` and `Match` status.
*   **Rankings**: Points (`mens_singles_points`, etc.) are stored in `PlayerProfile`. Points are likely awarded when placings are calculated (e.g., in `PlacingService` or related logic, triggered after tournament completion). The `/rankings` route queries `PlayerProfile` ordered by points.

## 10. Setup & Running

Follow the instructions in `README.md`:

1.  Clone repository.
2.  Create and activate a Python virtual environment.
3.  Install dependencies: `pip install -r requirements.txt`.
4.  Create a `.env` file with necessary variables (`SECRET_KEY`, `FLASK_APP`, `FLASK_ENV`, `ADMIN_EMAIL`, potentially `MAIL_...` variables).
5.  Initialize database: `flask db init`, `flask db migrate`, `flask db upgrade`.
6.  Seed database: `python seed.py`.
7.  Run development server: `python run.py`.
8.  Access at `http://localhost:5000`.

## 11. Deployment (`README.md`)

The README provides basic steps for deploying on a Linux server using:

*   **Nginx:** As a reverse proxy. Requires configuration (`/etc/nginx/sites-available/pickleball`).
*   **Gunicorn/WSGI:** Implied by `wsgi.py`. The Flask app needs to be served by a WSGI server.
*   **Systemd:** To manage the application process as a service (`/etc/systemd/system/pickleball.service`).
*   Requires setting up file permissions (`chown www-data:www-data app.db`).

## 12. Dependencies (`requirements.txt`)

Contains a list of all Python packages required by the project (e.g., Flask, Flask-SQLAlchemy, Flask-Login, Flask-Migrate, Flask-WTF, Flask-Mail, requests).

## 13. Seeding (`seed.py`, `debug_seed.py`, etc.)

Scripts used to populate the database with initial data (e.g., admin user, sample players, tournaments). `seed.py` is the main script mentioned in the setup.