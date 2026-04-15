"""Migrate all existing SQLite contracts into Neo4j.

Usage:
    python -m scripts.migrate_to_neo4j
"""
import sys
import os
import logging

# Load .env before importing app modules
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'), override=True)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

from app.database import SessionLocal
from app.neo4j_client import neo4j_client
from app.graph_schema import init_schema
from app.graph_sync import sync_all_contracts


def main() -> None:
    if neo4j_client is None:
        print(
            "ERROR: Neo4j credentials not configured. "
            "Set NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD in your .env file."
        )
        sys.exit(1)

    print("Checking Neo4j connection...")
    if not neo4j_client.health_check():
        print("ERROR: Cannot connect to Neo4j. Is it running?")
        sys.exit(1)
    print("Connected.")

    print("Initializing schema...")
    with neo4j_client.get_session() as session:
        init_schema(session)

    print("Syncing all contracts from SQLite to Neo4j...")
    db = SessionLocal()
    try:
        sync_all_contracts(db)
    finally:
        db.close()

    print("Migration complete.")


if __name__ == "__main__":
    main()
