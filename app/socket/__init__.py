from flask import request, session
from flask_login import current_user
from flask_socketio import emit, join_room, leave_room
import json

def register_socketio_handlers(socketio):
    @socketio.on('connect')
    def handle_connect():
        """Handle client connection."""
        if current_user.is_authenticated:
            # Join a room specific to the user
            join_room(f'user_{current_user.id}')
            print(f'Client connected: {current_user.username}')
        else:
            print('Anonymous client connected')

    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection."""
        if current_user.is_authenticated:
            leave_room(f'user_{current_user.id}')
            print(f'Client disconnected: {current_user.username}')
        else:
            print('Anonymous client disconnected')

    @socketio.on('join')
    def handle_join(data):
        """Handle client joining a room."""
        room = data.get('room')
        if room:
            join_room(room)
            print(f'Client joined room: {room}')
            emit('status', {'msg': f'Joined room: {room}'}, room=room)

    @socketio.on('leave')
    def handle_leave(data):
        """Handle client leaving a room."""
        room = data.get('room')
        if room:
            leave_room(room)
            print(f'Client left room: {room}')

    @socketio.on('join_tournament')
    def join_tournament(data):
        """Join a tournament-specific room."""
        tournament_id = data.get('tournament_id')
        if tournament_id:
            room = f'tournament_{tournament_id}'
            join_room(room)
            print(f'Client joined tournament room: {room}')
            
    @socketio.on('join_match')
    def join_match(data):
        """Join a match-specific room."""
        match_id = data.get('match_id')
        if match_id:
            room = f'match_{match_id}'
            join_room(room)
            print(f'Client joined match room: {room}')
            
    @socketio.on('join_courts_view')
    def join_courts_view(data):
        """Join a courts view room for live updates on all courts."""
        tournament_id = data.get('tournament_id')
        if tournament_id:
            room = f'courts_view_{tournament_id}'
            join_room(room)
            print(f'Client joined courts view room: {room}')
            emit('status', {'msg': f'Joined courts view for tournament {tournament_id}'}, room=room)
