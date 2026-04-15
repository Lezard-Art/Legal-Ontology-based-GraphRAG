"""Neo4j connection manager for the GraphRAG layer."""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class Neo4jClient:
    def __init__(self, uri: str, user: str, password: str):
        from neo4j import GraphDatabase
        self._driver = GraphDatabase.driver(uri, auth=(user, password))

    def get_session(self):
        return self._driver.session()

    def health_check(self) -> bool:
        try:
            with self._driver.session() as session:
                session.run("RETURN 1")
            return True
        except Exception:
            return False

    def close(self):
        self._driver.close()


def _create_neo4j_client() -> Optional["Neo4jClient"]:
    uri = os.environ.get("NEO4J_URI")
    user = os.environ.get("NEO4J_USER")
    password = os.environ.get("NEO4J_PASSWORD")
    if not all([uri, user, password]):
        logger.warning(
            "Neo4j credentials not configured (NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD). "
            "GraphRAG features will be disabled."
        )
        return None
    try:
        client = Neo4jClient(uri, user, password)
        return client
    except Exception as e:
        logger.warning(f"Failed to create Neo4j client: {e}")
        return None


neo4j_client: Optional[Neo4jClient] = _create_neo4j_client()
