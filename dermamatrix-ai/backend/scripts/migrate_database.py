"""Explicit local migration: back up first, test an isolated database, then opt in."""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["DERMAMATRIX_INITIALISE_SCHEMA"] = "false"
import app
from consumer_schema import migrate

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Explicitly apply additive migrations to the configured database")
    args = parser.parse_args()
    if not args.apply:
        parser.exit(2, "No changes made. Review target configuration and backup; pass --apply.\n")
    app.initialise_database()
    if app.DATABASE_BOOT_ERROR:
        raise SystemExit("Base schema could not be prepared; no consumer migration attempted.")
    connection = app.database()
    try:
        print("Consumer migration applied." if migrate(connection) else "Consumer migration already applied.")
    finally:
        connection.close()
