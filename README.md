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
│   ├── models.py             # Database models
│   ├── decorators.py         # Custom decorators for role-based access
│   ├── admin/                # Admin blueprint
│   ├── auth/                 # Authentication blueprint
│   ├── errors/               # Error handling
│   ├── main/                 # Main site blueprint
│   ├── organizer/            # Organizer blueprint
│   ├── player/               # Player blueprint
│   ├── tournament/           # Tournament blueprint
│   ├── static/               # Static files (CSS, JS, images)
│   └── templates/            # HTML templates
├── migrations/               # Database migrations (created by Flask-Migrate)
├── .env                      # Environment variables (create this file)
├── config.py                 # Application configuration
├── requirements.txt          # Python dependencies
├── run.py                    # Application entry point
└── seed.py                   # Database seeding script
```

## Setup and Installation

1. Clone the repository
   ```bash
   git clone https://github.com/bryanooitatmun/pickleball-tournament-platform.git
   cd pickleball-tournament-platform
   ```

2. Create and activate a virtual environment
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows, use: venv\Scripts\activate
   ```

3. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables (create a `.env` file):
   ```
   SECRET_KEY=your-secret-key
   FLASK_APP=run.py
   FLASK_ENV=development
   ADMIN_EMAIL=admin@example.com
   ```

5. Initialize the database
   ```bash
   flask db init
   flask db migrate -m "Initial migration"
   flask db upgrade
   ```

6. Seed the database with sample data
   ```bash
   python seed.py
   ```

7. Run the application
   ```bash
   python run.py
   ```

8. Access the application at `http://localhost:5000`

## User Roles

The platform has three different types of users:

1. **Admin**
   - Can manage all users, tournaments, and players
   - Access to system statistics and configuration

2. **Organizer**
   - Can create and manage tournaments
   - Can input scores and update tournament brackets
   - Can approve player registrations

3. **Player**
   - Can register for tournaments
   - Can view their profile and rankings
   - Can track their tournament history

## Setting up the server

1. apt update

2. apt install nginx

3. nano /etc/nginx/sites-available/pickleball

4. ln -s /etc/nginx/sites-available/pickleball /etc/nginx/sites-enabled/

5. systemctl restart nginx

6. nano /etc/systemd/system/pickleball.service

7. sudo systemctl daemon-reload

8. sudo systemctl enable pickleball

9. sudo systemctl start pickleball

9. sudo systemctl restart pickleball

9. sudo systemctl status pickleball

10. sudo journalctl -u pickleball

11. cd /var/www/pickleball-tournament-platform

12. source new_venv/bin/activate

13. sudo chown www-data:www-data /var/www/pickleball-tournament-platform/app.db

## Default Accounts

After running the seed script, the following accounts will be available:

- **Admin**: admin@example.com / password
- **Organizer**: organizer@example.com / password
- **Player**: player1@example.com through player30@example.com / password

## Tournament Features

- **Tournament Tiers**: Different tournament levels (SLATE, CUP, OPEN, CHALLENGE) with varying point values
- **Tournament Formats**: Single Elimination, Double Elimination, Round Robin, and Group Stage + Knockout
- **Categories**: Men's Singles, Women's Singles, Men's Doubles, Women's Doubles, and Mixed Doubles
- **Live Scoring**: Real-time updates of match scores and brackets
- **Point Distribution**: Automatically awards ranking points based on tournament performance

## Development Notes

- Make sure to run `flask db migrate` and `flask db upgrade` whenever you make changes to models
- All static files should be placed in the `app/static` directory
- Templates follow the blueprint structure for organization
- The application uses Tailwind CSS for styling, loaded via CDN

## License

MIT License

