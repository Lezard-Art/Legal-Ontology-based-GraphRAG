"""Neo4j schema initialization — constraints and indexes for the contract ontology graph."""
import logging

logger = logging.getLogger(__name__)

_CONSTRAINTS = [
    "CREATE CONSTRAINT contract_id IF NOT EXISTS FOR (c:Contract) REQUIRE c.id IS UNIQUE",
    "CREATE CONSTRAINT party_id IF NOT EXISTS FOR (p:Party) REQUIRE p.id IS UNIQUE",
    "CREATE CONSTRAINT role_id IF NOT EXISTS FOR (r:Role) REQUIRE r.id IS UNIQUE",
    "CREATE CONSTRAINT obligation_id IF NOT EXISTS FOR (o:Obligation) REQUIRE o.id IS UNIQUE",
    "CREATE CONSTRAINT power_id IF NOT EXISTS FOR (pw:Power) REQUIRE pw.id IS UNIQUE",
    "CREATE CONSTRAINT constraint_id IF NOT EXISTS FOR (cn:Constraint) REQUIRE cn.id IS UNIQUE",
    "CREATE CONSTRAINT clause_id IF NOT EXISTS FOR (cl:Clause) REQUIRE cl.id IS UNIQUE",
    "CREATE CONSTRAINT asset_id IF NOT EXISTS FOR (a:Asset) REQUIRE a.id IS UNIQUE",
    "CREATE CONSTRAINT legal_position_id IF NOT EXISTS FOR (lp:LegalPosition) REQUIRE lp.id IS UNIQUE",
]

_VECTOR_INDEX = (
    "CREATE VECTOR INDEX entity_embeddings IF NOT EXISTS "
    "FOR (n:Entity) ON (n.embedding) "
    "OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: 'cosine'}}"
)

_FULLTEXT_INDEX = (
    "CREATE FULLTEXT INDEX clause_text IF NOT EXISTS "
    "FOR (c:Clause) ON EACH [c.text]"
)


def init_schema(session) -> None:
    for cypher in _CONSTRAINTS:
        try:
            session.run(cypher)
        except Exception as e:
            logger.warning(f"Schema constraint skipped ({e})")
    try:
        session.run(_VECTOR_INDEX)
    except Exception as e:
        logger.warning(f"Vector index skipped ({e})")
    try:
        session.run(_FULLTEXT_INDEX)
    except Exception as e:
        logger.warning(f"Fulltext index skipped ({e})")
    logger.info("Neo4j schema initialized.")
