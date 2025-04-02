import pytest
from flask import url_for, json
from app.models import (User, UserRole, Tournament, PlatformSponsor, SponsorTier)
from tests.test_organizer_tournament_routes import create_test_tournament # Reuse helper

# --- Helper Functions ---

def create_test_sponsor(db, name="Test Sponsor", tier=SponsorTier.SUPPORTING, display_order=1):
    """Helper to create a platform sponsor."""
    sponsor = PlatformSponsor(
        name=name,
        tier=tier,
        website="http://example.com",
        display_order=display_order
    )
    db.session.add(sponsor)
    db.session.commit()
    return sponsor

# --- Tests for Platform Sponsor Management ---

def test_manage_sponsors_get(client, organizer_user, test_db):
    """ Test listing all platform sponsors """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    sponsor1 = create_test_sponsor(test_db, name="Alpha Sponsor", tier=SponsorTier.PREMIER)
    sponsor2 = create_test_sponsor(test_db, name="Beta Sponsor", tier=SponsorTier.SUPPORTING)

    response = client.get(url_for('organizer.manage_sponsors'))

    assert response.status_code == 200
    assert b'Manage Sponsors' in response.data
    assert b'Alpha Sponsor' in response.data
    assert b'Beta Sponsor' in response.data
    # Check if sorted correctly (Premier before Supporting)
    assert response.data.find(b'Alpha Sponsor') < response.data.find(b'Beta Sponsor')

def test_create_sponsor_get(client, organizer_user):
    """ Test GET request for create sponsor page """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    response = client.get(url_for('organizer.create_sponsor'))
    assert response.status_code == 200
    assert b'Create Sponsor' in response.data
    assert b'Sponsor Name' in response.data
    assert b'Tier' in response.data

def test_create_sponsor_post_success(client, organizer_user, test_db):
    """ Test successfully creating a new platform sponsor """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)

    sponsor_data = {
        'name': 'New Awesome Sponsor',
        'tier': SponsorTier.FEATURED.name,
        'description': 'Provides awesome things.',
        'website': 'http://awesome.co',
        'is_featured': True,
        'display_order': 10,
        'contact_name': 'John Doe',
        'contact_email': 'john@awesome.co',
        'contact_phone': '123456789'
        # Logo/Banner upload tested separately if needed
    }

    response = client.post(url_for('organizer.create_sponsor'), data=sponsor_data, follow_redirects=False)

    assert response.status_code == 302 # Redirects to manage sponsors list
    assert url_for('organizer.manage_sponsors') in response.location

    # Verify sponsor created in DB
    sponsor = PlatformSponsor.query.filter_by(name='New Awesome Sponsor').first()
    assert sponsor is not None
    assert sponsor.tier == SponsorTier.FEATURED
    assert sponsor.website == 'http://awesome.co'
    assert sponsor.is_featured is True
    assert sponsor.display_order == 10
    assert sponsor.contact_email == 'john@awesome.co'

def test_edit_sponsor_get(client, organizer_user, test_db):
    """ Test GET request for edit sponsor page """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    sponsor = create_test_sponsor(test_db, name="Sponsor To Edit", tier=SponsorTier.OFFICIAL)

    response = client.get(url_for('organizer.edit_sponsor', id=sponsor.id))

    assert response.status_code == 200
    assert f'Edit Sponsor: {sponsor.name}'.encode() in response.data
    assert b'value="Sponsor To Edit"' in response.data # Check name pre-filled
    assert f'<option value="OFFICIAL" selected>'.encode() in response.data # Check tier selected

def test_edit_sponsor_post_success(client, organizer_user, test_db):
    """ Test successfully editing an existing platform sponsor """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    sponsor = create_test_sponsor(test_db, name="Old Name", tier=SponsorTier.SUPPORTING, display_order=5)

    edit_data = {
        'name': 'Updated Sponsor Name',
        'tier': SponsorTier.PREMIER.name, # Change tier
        'description': 'Updated description.',
        'website': sponsor.website,
        'is_featured': False,
        'display_order': 1, # Change order
        'contact_name': sponsor.contact_name,
        'contact_email': sponsor.contact_email,
        'contact_phone': sponsor.contact_phone
    }

    response = client.post(url_for('organizer.edit_sponsor', id=sponsor.id), data=edit_data, follow_redirects=False)

    assert response.status_code == 302 # Redirects to manage sponsors list
    assert url_for('organizer.manage_sponsors') in response.location

    # Verify sponsor updated in DB
    test_db.session.refresh(sponsor)
    assert sponsor.name == 'Updated Sponsor Name'
    assert sponsor.tier == SponsorTier.PREMIER
    assert sponsor.description == 'Updated description.'
    assert sponsor.display_order == 1

def test_delete_sponsor_post_success(client, organizer_user, test_db):
    """ Test successfully deleting a platform sponsor """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    sponsor_to_delete = create_test_sponsor(test_db, name="Delete Me Sponsor")
    sponsor_id = sponsor_to_delete.id

    response = client.post(url_for('organizer.delete_sponsor', id=sponsor_id), follow_redirects=False)

    assert response.status_code == 302 # Redirects to manage sponsors list
    assert url_for('organizer.manage_sponsors') in response.location

    # Verify sponsor deleted from DB
    deleted_sponsor = PlatformSponsor.query.get(sponsor_id)
    assert deleted_sponsor is None

# --- Tests for Tournament Sponsor Assignment ---

# Note: There are duplicate route definitions for '/tournament/<int:id>/sponsors'
# One seems to be GET/POST for editing, another POST only? Testing the GET/POST one.
# Assuming 'edit_tournament_sponsors' is the intended route for assignment.

def test_edit_tournament_sponsors_get(client, organizer_user, test_db):
    """ Test GET request for assigning sponsors to a tournament """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    tournament = create_test_tournament(test_db, organizer_user)
    sponsor1 = create_test_sponsor(test_db, name="Sponsor A")
    sponsor2 = create_test_sponsor(test_db, name="Sponsor B")
    sponsor3 = create_test_sponsor(test_db, name="Sponsor C")

    # Pre-assign sponsor1 to the tournament
    tournament.platform_sponsors.append(sponsor1)
    test_db.session.commit()

    response = client.get(url_for('organizer.edit_tournament_sponsors', id=tournament.id))

    assert response.status_code == 200
    assert f'Edit Sponsors for {tournament.name}'.encode() in response.data
    assert b'Sponsor A' in response.data
    assert b'Sponsor B' in response.data
    assert b'Sponsor C' in response.data
    # Check that sponsor1 is marked as selected (e.g., checkbox checked)
    assert f'value="{sponsor1.id}" checked'.encode() in response.data
    assert f'value="{sponsor2.id}"'.encode() in response.data # Not checked
    assert f'value="{sponsor3.id}"'.encode() in response.data # Not checked

def test_edit_tournament_sponsors_post_update_assignment(client, organizer_user, test_db):
    """ Test POST request to update sponsor assignments for a tournament """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    tournament = create_test_tournament(test_db, organizer_user)
    sponsor1 = create_test_sponsor(test_db, name="Sponsor A")
    sponsor2 = create_test_sponsor(test_db, name="Sponsor B")
    sponsor3 = create_test_sponsor(test_db, name="Sponsor C")

    # Pre-assign sponsor1
    tournament.platform_sponsors.append(sponsor1)
    test_db.session.commit()

    # Update assignment: Keep sponsor1, add sponsor3, remove sponsor2 (if it was there), ignore sponsor2
    post_data = {
        'selected_sponsors': [str(sponsor1.id), str(sponsor3.id)]
        # The route logic seems to handle adding/removing based on this list vs current state
    }

    response = client.post(url_for('organizer.edit_tournament_sponsors', id=tournament.id), data=post_data, follow_redirects=False)

    assert response.status_code == 302 # Redirects to edit tournament page
    assert url_for('organizer.edit_tournament', id=tournament.id) in response.location

    # Verify assignments in DB
    test_db.session.refresh(tournament)
    assigned_sponsor_ids = {s.id for s in tournament.platform_sponsors}
    assert sponsor1.id in assigned_sponsor_ids
    assert sponsor2.id not in assigned_sponsor_ids
    assert sponsor3.id in assigned_sponsor_ids
    assert len(assigned_sponsor_ids) == 2

def test_edit_tournament_sponsors_post_remove_all(client, organizer_user, test_db):
    """ Test POST request to remove all sponsor assignments """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    tournament = create_test_tournament(test_db, organizer_user)
    sponsor1 = create_test_sponsor(test_db, name="Sponsor A")
    sponsor2 = create_test_sponsor(test_db, name="Sponsor B")

    # Pre-assign sponsors
    tournament.platform_sponsors.append(sponsor1)
    tournament.platform_sponsors.append(sponsor2)
    test_db.session.commit()

    # Submit form with no sponsors selected
    post_data = {
        # 'selected_sponsors': [] # Empty list or omitted field
    }

    response = client.post(url_for('organizer.edit_tournament_sponsors', id=tournament.id), data=post_data, follow_redirects=False)

    assert response.status_code == 302

    # Verify assignments in DB
    test_db.session.refresh(tournament)
    assert len(tournament.platform_sponsors) == 0

def test_edit_tournament_sponsors_permission_denied(client, organizer_user, other_organizer_user, test_db):
    """ Test organizer cannot assign sponsors for another organizer's tournament """
    tournament = create_test_tournament(test_db, other_organizer_user)
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)

    response_get = client.get(url_for('organizer.edit_tournament_sponsors', id=tournament.id), follow_redirects=True)
    assert b'You do not have permission to edit sponsors for this tournament.' in response_get.data

    response_post = client.post(url_for('organizer.edit_tournament_sponsors', id=tournament.id), data={}, follow_redirects=True)
    assert b'You do not have permission to edit sponsors for this tournament.' in response_post.data