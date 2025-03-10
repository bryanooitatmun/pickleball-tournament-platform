from app import create_app, db
from app.models import (User, PlayerProfile, Tournament, TournamentCategory, Match, 
MatchScore, Registration, Equipment, PlayerSponsor, PlatformSponsor, Venue, Advertisement)

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db, 
        'User': User, 
        'PlayerProfile': PlayerProfile,
        'Tournament': Tournament,
        'TournamentCategory': TournamentCategory,
        'Match': Match,
        'MatchScore': MatchScore,
        'Registration': Registration,
        'Equipment': Equipment,
        'PlayerSponsor': PlayerSponsor,
        'PlatformSponsor': PlatformSponsor,
        'Venue': Venue,
        'Advertisement': Advertisement
    }

if __name__ == '__main__':
    app.run(debug=True)
