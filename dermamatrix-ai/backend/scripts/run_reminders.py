"""Run one bounded reminder cycle; does not install a scheduled task."""
import argparse
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['DERMAMATRIX_INITIALISE_SCHEMA'] = 'false'
import app
from reminder_worker import plan, run_due

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-once', action='store_true')
    args = parser.parse_args()
    if not args.run_once:
        parser.exit(2, 'No work performed. Configure transport, then pass --run-once.\n')
    if not app.app.config.get('CONSUMER_ENABLED'):
        parser.exit(2, 'Apply consumer migrations and enable consumer features first.\n')
    connection = app.database()
    try:
        created = plan(connection)
        outcomes = run_due(connection)
        from collections import Counter
        print({'scheduled': created, 'outcomes': dict(Counter(o['state'] for o in outcomes)), 'delivery_confirmed': False})
    finally:
        connection.close()
