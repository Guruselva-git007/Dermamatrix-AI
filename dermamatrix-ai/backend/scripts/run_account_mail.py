"""Run one explicitly configured account-mail cycle. No installed scheduler."""
import argparse
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['DERMAMATRIX_INITIALISE_SCHEMA']='false'
import app
from account_mail_worker import process_account_messages

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run-once',action='store_true');args=parser.parse_args()
    if not args.run_once or not app.app.config.get('CONSUMER_ENABLED'):
        parser.exit(2,'Enable consumer features and explicitly pass --run-once. No email sent.\n')
    connection=app.database()
    try:
        with app.app.app_context():
            from collections import Counter
            print(dict(Counter(process_account_messages(connection))))
    finally:connection.close()
