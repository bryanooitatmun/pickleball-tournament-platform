Report button works initially, but doesn't work after scrolling

Live_match.html and Live_score.html, doesn't take into account doubles matches

Live_courts.html, next match is not showing the correct match. Example:

        CURRENT MATCH
        Men's Doubles - Semifinal

        Thomas Chen / William Zhang

        0
        Kenneth Park / George Huang

        0
        Match in progress

        View Match
        NEXT MATCH
        Men's Doubles - Semifinal

        19:58 (2869.0 mins)

        Thomas Chen / William Zhang

        Kenneth Park / George Huang

live_scoring.html, it's showing that no matches currently in progress. Because for the routes:
    ongoing_matches = Match.query.join(TournamentCategory).filter(
        TournamentCategory.tournament_id == id,
        Match.completed == False,
        Match.player1_id.isnot(None),
        Match.player2_id.isnot(None)
    ).all()
    it's not taking into account doubles matches.

schedule.html not showing correctly. Categories by group stages if applicable, and the player list isn't taking into account for doubles matches. 

manage_category.html:
    calculate placing form doesn't work because no form csrf_token

    Organize matches, very hard to view long lists of matches. Don't overcomplicate. Maybe view by groups (if applicable), view by rounds, or search players

    generate bracket doesn't work. Routes and template is mismatched.