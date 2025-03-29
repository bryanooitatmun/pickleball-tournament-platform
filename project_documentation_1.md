# Pickleball Tournament Platform Documentation

## Project Overview

The Pickleball Tournament Platform is a comprehensive web application built with Flask that allows organizers to create and manage pickleball tournaments, while players can register, view tournament details, track scores, and follow rankings. The platform features a role-based permission system, tournament management capabilities, live scoring, player rankings, and responsive design for both desktop and mobile devices.

## Table of Contents

1. [Technology Stack](#technology-stack)
2. [Project Structure](#project-structure)
3. [Features](#features)
4. [Database Schema](#database-schema)
5. [User Roles and Permissions](#user-roles-and-permissions)
6. [Core Functionality](#core-functionality)
7. [Development Notes](#development-notes)

## Technology Stack

- **Backend Framework**: Flask (Python)
- **Database**: SQLite (SQLAlchemy ORM)
- **Frontend**: HTML, CSS (Tailwind CSS), JavaScript
- **Authentication**: Flask-Login
- **Form Handling**: Flask-WTF
- **Email**: Flask-Mail
- **Database Migrations**: Flask-Migrate
- **Web Server**: Nginx with Gunicorn (for production)

## Project Structure

```
pickleball-tournament-platform/
├── app/                      # Main application package
│   ├── __init__.py           # Flask app initialization
│   ├── models.py             # Database models
│   ├── decorators.py         # Custom decorators for role-based access
│   ├── admin/                # Admin blueprint
│   ├── auth/                 # Authentication blueprint
│   ├── errors/               # Error handling
│   ├── helpers/              # Helper functions
│   ├── main/                 # Main site blueprint
│   ├── organizer/            # Organizer blueprint
│   ├── player/               # Player blueprint
│   ├── services/             # Service layer
│   ├── support/              # Support ticket system
│   ├── tournament/           # Tournament blueprint
│   ├── static/               # Static files (CSS, JS, images)
│   └── templates/            # HTML templates
├── migrations/               # Database migrations (created by Flask-Migrate)
├── .env                      # Environment variables
├── config.py                 # Application configuration
├── requirements.txt          # Python dependencies
├── run.py                    # Application entry point
├── wsgi.py                   # WSGI entry point for production
└── seed.py                   # Database seeding script
```


## Features

### User Management

- User registration and authentication
- Role-based permissions (Admin, Organizer, Player, Referee)
- User profiles with personal information
- Password reset functionality

### Tournament Management

- Create and manage tournaments
- Multiple tournament formats:
  - Single Elimination
  - Double Elimination
  - Round Robin
  - Group Stage + Knockout
- Tournament categories (Men's Singles, Women's Singles, Men's Doubles, Women's Doubles, Mixed Doubles)
- Tournament tiers with different point values:
  - SLATE (2000 points)
  - CUP (3200 points)
  - OPEN (1400 points)
  - CHALLENGE (925 points)
- Category restrictions (DUPR rating, age, gender)
- Registration management with payment tracking
- Automated bracket generation

### Player Features

- Player profiles with stats and history
- Tournament registration
- View upcoming and past tournaments
- Track rankings and points across categories
- Equipment and sponsor management
- Support ticket system

### Scoring and Brackets

- Live scoring updates
- Match scheduling
- Generate brackets automatically
- Multiple bracket formats
- Print/export brackets
- Match history and results
- Group stage management

### Venue Management

- Venue profiles with detailed information
- Photo galleries for venues
- Court management
- Venue selection for tournaments

### Sponsorship Management

- Platform-wide sponsors
- Tournament-specific sponsors
- Sponsor tiers and hierarchies
- Sponsor logo display

### Prize Management

- Cash prizes
- Merchandise prizes
- Door gifts
- Custom prize distribution settings

### Support System

- Support tickets for issues
- Player reporting
- Issue tracking and resolution

## Database Schema

The database schema includes the following main entities:

### Core Entities

- **Users**: Authentication and role information
- **PlayerProfile**: Extended player information and stats
- **Tournament**: Tournament details and configuration
- **TournamentCategory**: Categories within tournaments
- **Registration**: Player registrations with payment tracking
- **Match**: Match information including scores and results
- **MatchScore**: Individual set scores for matches
- **Team**: Teams for doubles matches
- **Group/GroupStanding**: Group stage management

### Supporting Entities

- **Venue/VenueImage**: Venue information and photos
- **PlatformSponsor**: Sponsor information
- **Equipment**: Player equipment details
- **PlayerSponsor**: Sponsor relationships for players
- **Prize**: Prize information for tournaments
- **SupportTicket/TicketResponse**: Support system

## User Roles and Permissions

### Admin
- Complete system access
- Manage all users, tournaments, venues, and settings
- View system statistics
- Approve/reject organizers

### Organizer
- Create and manage tournaments
- Manage registrations and payments
- Input scores and update tournament brackets
- Add venues and sponsors
- View tournament statistics

### Player
- Register for tournaments
- Manage personal profile
- View tournament schedule and results
- Track rankings and tournament history
- Submit support tickets

### Referee (Planned)
- Input match scores
- Manage match progress
- Flag issues for organizers

## Core Functionality

### Tournament Creation Process

1. Organizers create a tournament with basic details
2. Add tournament categories and formats
3. Set up prize information and registration fees
4. Configure payment details and door gifts
5. Add sponsors and venue information
6. Publish the tournament for player registration

### Registration Process

1. Players browse available tournaments
2. Select a tournament and category
3. Register as individual or team
4. Complete registration form with partner details if needed
5. Submit payment information
6. Organizer verifies payment and approves registration

### Tournament Bracket Management

1. Organizer generates brackets after registration closes
2. System supports various bracket formats
3. Optional seeding for top players
4. Match scheduling with court assignments
5. Live score updates during the tournament
6. Results calculation and point distribution
7. Final standings calculation

### Ranking System

1. Players earn points based on tournament performance
2. Points vary by tournament tier and placement
3. Separate rankings for different categories
4. Historical tracking of player progress


## Development Notes

### Database Migrations

Always run migrations when modifying the database schema:
```bash
flask db migrate -m "Description of changes"
flask db upgrade
```

### Security Considerations

- All user passwords are hashed using Werkzeug's security functions
- CSRF protection is implemented for all forms
- Role-based access control is enforced throughout the application
- Input validation is performed on all forms

### Template Structure

- Templates follow the blueprint structure for organization
- Base templates extend from `base.html`
- The application uses Tailwind CSS for styling
- Responsive design that works on both desktop and mobile


