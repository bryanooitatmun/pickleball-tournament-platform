"""
Main seeding script for the Pickleball Tournament Platform.
Coordinates all seeding operations across different modules.
"""

from seed_base import app, db, commit_changes, reset_db
from datetime import datetime
import sys
import time
import argparse

def run_seed_module(module_name, description):
    """Run a specific seed module and time its execution"""
    print(f"\n{'=' * 80}")
    print(f"Running {module_name}: {description}")
    print(f"{'=' * 80}")
    start_time = time.time()
    
    try:
        __import__(module_name).main()
        end_time = time.time()
        print(f"\n✓ Completed {module_name} in {round(end_time - start_time, 2)} seconds")
        return True
    except Exception as e:
        print(f"\n✗ Error in {module_name}: {e}")
        return False

def main():
    """Main seeding function"""
    parser = argparse.ArgumentParser(description='Seed the Pickleball Tournament Platform database.')
    parser.add_argument('--reset', action='store_true', help='Reset the database before seeding')
    parser.add_argument('--users-only', action='store_true', help='Only seed users')
    parser.add_argument('--tournament-only', action='store_true', help='Only seed tournament structure')
    parser.add_argument('--mens-doubles', action='store_true', help='Only seed Men\'s Doubles category and matches')
    parser.add_argument('--womens-doubles', action='store_true', help='Only seed Women\'s Doubles category and registrations')
    parser.add_argument('--skip-brackets', action='store_true', help='Skip bracket generation')
    parser.add_argument('--skip-matches', action='store_true', help='Skip match scheduling and scoring')
    
    args = parser.parse_args()
    
    print(f"{'=' * 80}")
    print(f"Pickleball Tournament Platform - Database Seeding")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 80}")
    
    # Reset database if requested
    if args.reset:
        reset_db()
    
    # Track execution time
    start_time = time.time()
    
    # Run appropriate seed modules based on arguments
    if args.users_only:
        run_seed_module('seed_users', 'Creating users with different roles')
    elif args.tournament_only:
        run_seed_module('seed_users', 'Creating users with different roles')
        run_seed_module('seed_tournament', 'Creating tournament with categories')
    elif args.mens_doubles:
        run_seed_module('seed_users', 'Creating users with different roles')
        run_seed_module('seed_tournament', 'Creating tournament with categories')
        run_seed_module('seed_registrations', 'Creating team registrations')
        if not args.skip_brackets:
            run_seed_module('seed_brackets', 'Generating brackets and groups')
        if not args.skip_matches:
            run_seed_module('seed_matches', 'Scheduling and scoring matches')
    elif args.womens_doubles:
        run_seed_module('seed_users', 'Creating users with different roles')
        run_seed_module('seed_tournament', 'Creating tournament with categories')
        run_seed_module('seed_registrations', 'Creating Women\'s Doubles registrations')
    else:
        # Run all seed modules in order
        modules = [
            ('seed_users', 'Creating users with different roles'),
            ('seed_tournament', 'Creating tournament with categories and prizes'),
            ('seed_registrations', 'Creating team registrations')
        ]
        
        if not args.skip_brackets:
            modules.append(('seed_brackets', 'Generating brackets and groups'))
        
        if not args.skip_matches:
            modules.append(('seed_matches', 'Scheduling and scoring matches'))
        
        for module_name, description in modules:
            success = run_seed_module(module_name, description)
            if not success and module_name != 'seed_users':
                print(f"Stopping due to error in {module_name}")
                break
    
    end_time = time.time()
    print(f"\n{'=' * 80}")
    print(f"Seeding completed in {round(end_time - start_time, 2)} seconds")
    print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 80}")

if __name__ == "__main__":
    with app.app_context():
        main()
