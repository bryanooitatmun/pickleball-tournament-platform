# Pickleball Tournament Platform

A comprehensive Flask-based platform for managing pickleball tournaments with player rankings, tournament organization, and live scoring.

## Features

- **User Roles**: Admin, Player, and Organizer with specific permissions
- **Tournament Management**: Create, update, and manage tournaments with tiers, formats, and categories
- **Live Scoring**: Real-time updates for tournament matches and brackets
- **Player Rankings**: Track player performance and rankings based on tournament results
- **Responsive Design**: Works on desktop and mobile devices

## Project Structure

```
pickleball-tournament-platform/
├── app/                      # Main application package
│   ├── models/               # Database models
│   ├── routes/               # Route handlers
│   ├── forms/                # Form definitions
│   ├── templates/            # HTML templates
│   └── static/               # Static files (CSS, JS, images)
├── migrations/               # Database migrations
├── tests/                    # Test suite
├── .env                      # Environment variables
├── config.py                 # Application configuration
├── requirements.txt          # Python dependencies
├── run.py                    # Application entry point
└── seed.py                   # Database seeding script
```

## Setup and Installation

1. Clone the repository
2. Create and activate a virtual environment
3. Install dependencies: `pip install -r requirements.txt`
4. Set up environment variables
5. Initialize the database: `flask db init`, `flask db migrate`, `flask db upgrade`
6. Run the application: `python run.py`

## License

MIT License
