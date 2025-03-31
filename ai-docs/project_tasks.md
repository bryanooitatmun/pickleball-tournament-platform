app/helpers/tournament.py have to be enhanced.
 Perhaps create all matches (including group stage and knockout) even ones that arent completed yet. Each team/player (team for doubles and player for singles) should have a code number assigned (example A1 for group A first placing, B2 for group B second placing). For incomplete matches (especially during the knockout stage) , the UI should show something like A1 vs B2. Even for knockout there should be a code. For quarters there are four matches, they could be named (1, 2, 3, 4), so that for semis, you can show 1 vs 2 (for the incomplete semis match). Once the code is setup, then the seeding can go in. I believe there isnt a page now to change seedings. There should be a page for the organizer to view the participant list alongside their seed, and they can drag and drop the teams/players to different seeds.  How about tiebreaks? Tiebreaker for groups should be number of h2h record with the other tied players followed by number of points. How about BYES? If two team is advancing per group of 5 groups, there will be 10 players. But a round of 16 needs to have 16 players, so there will be 6 BYES. Obviously the top 6 seed will be playing against the BYES and get a free entry to the quarters. This logic has to be coded in. 

 I have pictures to show as example what the brackets should look like. Look at ppa bracket 1.jpg for desktop site, and look at ppa bracket 2.jpg for the mobile site. Perhaps the app/static/js/bracket-visualisation.js can also be change to fit the looks from the image
 Enhance app/template/tournaments/brackets.html too afterwards to fit these changes. 

 Then, update my tests in my tests file to test these changes. If there are existing test that already test similar/same requirements, then you dont have to add it.


Actually I believe it's only necessary to have Number of groups and teams advancing per group. The teams per group can be calculated programmitically. I believe app/template/organizer/manage_tournament/manage_category.html, app/organizer/category_routes.py and perhaps app/helpers/tournament.py have to be changed to accomodate for this.

There must be an easy way to edit all the matches in bulk easily for the organizer. Right now in app/template/organizer/manage_tournament/manage_category.html, the organizer will have to go into each match one by one to edit the matches individually. I'm not sure, is a table to edit all of the match details for all matches a good way to go? Maybe a confirmation later in the ui to really make sure that the organizer can double check

