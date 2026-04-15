"""SQLite → Neo4j sync: reads ORM entities and writes them to the graph."""
import logging
from sqlalchemy.orm import Session
from . import models
from .neo4j_client import neo4j_client
from .embeddings import embedding_service

logger = logging.getLogger(__name__)


def sync_contract_to_graph(contract_id: str, db: Session) -> None:
    if neo4j_client is None:
        return

    contract = db.query(models.Contract).get(contract_id)
    if not contract:
        logger.warning(f"Contract {contract_id} not found in SQLite; skipping sync.")
        return

    with neo4j_client.get_session() as session:
        # Contract node
        _merge_node(session, "Contract", contract.id, {
            "id": contract.id,
            "name": contract.name or "",
            "governing_law": contract.governing_law or "",
            "jurisdiction": contract.jurisdiction or "",
            "effective_date": contract.effective_date or "",
            "end_date": contract.expiration_date or "",
        }, "Contract")

        # Party nodes + HAS_PARTY edges
        party_ids = {role.party_id for role in contract.roles if role.party_id}
        for pid in party_ids:
            party = db.query(models.Party).get(pid)
            if not party:
                continue
            _merge_node(session, "Party", party.id, {
                "id": party.id,
                "name": party.name or "",
                "type": party.type or "",
                "contract_id": contract_id,
            }, "Party")
            session.run(
                "MATCH (c:Contract {id: $cid}), (p:Party {id: $pid}) "
                "MERGE (c)-[:HAS_PARTY]->(p)",
                cid=contract_id, pid=party.id,
            )

        # Role nodes + PLAYS_ROLE edges
        for role in contract.roles:
            _merge_node(session, "Role", role.id, {
                "id": role.id,
                "label": role.label or "",
                "contract_id": contract_id,
                "party_id": role.party_id or "",
            }, "Role")
            if role.party_id:
                session.run(
                    "MATCH (p:Party {id: $pid}), (r:Role {id: $rid}) "
                    "MERGE (p)-[:PLAYS_ROLE]->(r)",
                    pid=role.party_id, rid=role.id,
                )

        # Clause nodes + HAS_CLAUSE edges
        for clause in contract.clauses:
            _merge_node(session, "Clause", clause.id, {
                "id": clause.id,
                "contract_id": contract_id,
                "section_number": clause.section_number or "",
                "text": clause.text or "",
                "ontology_tag": clause.ontology_tag or "",
            }, "Clause")
            session.run(
                "MATCH (c:Contract {id: $cid}), (cl:Clause {id: $clid}) "
                "MERGE (c)-[:HAS_CLAUSE]->(cl)",
                cid=contract_id, clid=clause.id,
            )

        # Asset nodes + INVOLVES_ASSET edges
        for asset in contract.assets:
            _merge_node(session, "Asset", asset.id, {
                "id": asset.id,
                "contract_id": contract_id,
                "name": asset.name or "",
                "type": asset.type or "",
                "description": asset.description or "",
            }, "Asset")
            session.run(
                "MATCH (c:Contract {id: $cid}), (a:Asset {id: $aid}) "
                "MERGE (c)-[:INVOLVES_ASSET]->(a)",
                cid=contract_id, aid=asset.id,
            )

        # Obligation nodes + HAS_OBLIGATION + DEBTOR/CREDITOR edges
        for obl in contract.obligations:
            debtor_role = db.query(models.Role).get(obl.debtor_role_id) if obl.debtor_role_id else None
            creditor_role = db.query(models.Role).get(obl.creditor_role_id) if obl.creditor_role_id else None
            _merge_node(session, "Obligation", obl.id, {
                "id": obl.id,
                "contract_id": contract_id,
                "description": obl.description or "",
                "surviving": obl.surviving or False,
                "debtor_role": debtor_role.label if debtor_role else "?",
                "creditor_role": creditor_role.label if creditor_role else "?",
            }, "Obligation")
            session.run(
                "MATCH (c:Contract {id: $cid}), (o:Obligation {id: $oid}) "
                "MERGE (c)-[:HAS_OBLIGATION]->(o)",
                cid=contract_id, oid=obl.id,
            )
            if obl.debtor_role_id:
                session.run(
                    "MATCH (o:Obligation {id: $oid}), (r:Role {id: $rid}) "
                    "MERGE (o)-[:DEBTOR]->(r)",
                    oid=obl.id, rid=obl.debtor_role_id,
                )
            if obl.creditor_role_id:
                session.run(
                    "MATCH (o:Obligation {id: $oid}), (r:Role {id: $rid}) "
                    "MERGE (o)-[:CREDITOR]->(r)",
                    oid=obl.id, rid=obl.creditor_role_id,
                )

        # Power nodes + HAS_POWER + CREDITOR/DEBTOR edges
        for pwr in contract.powers:
            creditor_role = db.query(models.Role).get(pwr.creditor_role_id) if pwr.creditor_role_id else None
            debtor_role = db.query(models.Role).get(pwr.debtor_role_id) if pwr.debtor_role_id else None
            _merge_node(session, "Power", pwr.id, {
                "id": pwr.id,
                "contract_id": contract_id,
                "description": pwr.description or "",
                "creditor_role": creditor_role.label if creditor_role else "?",
                "debtor_role": debtor_role.label if debtor_role else "?",
            }, "Power")
            session.run(
                "MATCH (c:Contract {id: $cid}), (pw:Power {id: $pid}) "
                "MERGE (c)-[:HAS_POWER]->(pw)",
                cid=contract_id, pid=pwr.id,
            )
            if pwr.creditor_role_id:
                session.run(
                    "MATCH (pw:Power {id: $pid}), (r:Role {id: $rid}) "
                    "MERGE (pw)-[:CREDITOR]->(r)",
                    pid=pwr.id, rid=pwr.creditor_role_id,
                )
            if pwr.debtor_role_id:
                session.run(
                    "MATCH (pw:Power {id: $pid}), (r:Role {id: $rid}) "
                    "MERGE (pw)-[:DEBTOR]->(r)",
                    pid=pwr.id, rid=pwr.debtor_role_id,
                )

        # Constraint nodes + HAS_CONSTRAINT edges
        for constr in contract.constraints:
            _merge_node(session, "Constraint", constr.id, {
                "id": constr.id,
                "contract_id": contract_id,
                "description": constr.description or "",
                "expression": constr.expression or "",
            }, "Constraint")
            session.run(
                "MATCH (c:Contract {id: $cid}), (cn:Constraint {id: $cnid}) "
                "MERGE (c)-[:HAS_CONSTRAINT]->(cn)",
                cid=contract_id, cnid=constr.id,
            )

    logger.info(f"Synced contract {contract_id} to Neo4j.")


def sync_all_contracts(db: Session) -> None:
    if neo4j_client is None:
        return
    contracts = db.query(models.Contract).all()
    for contract in contracts:
        try:
            sync_contract_to_graph(contract.id, db)
        except Exception as e:
            logger.warning(f"Failed to sync contract {contract.id}: {e}")
    logger.info(f"Synced {len(contracts)} contracts to Neo4j.")


def delete_contract_from_graph(contract_id: str) -> None:
    if neo4j_client is None:
        return
    try:
        with neo4j_client.get_session() as session:
            # Delete all non-contract nodes that belong to this contract
            session.run(
                "MATCH (n:Entity {contract_id: $cid}) DETACH DELETE n",
                cid=contract_id,
            )
            # Delete the contract node itself
            session.run(
                "MATCH (c:Contract {id: $cid}) DETACH DELETE c",
                cid=contract_id,
            )
        logger.info(f"Deleted contract {contract_id} from Neo4j.")
    except Exception as e:
        logger.warning(f"Failed to delete contract {contract_id} from Neo4j: {e}")


def _merge_node(session, label: str, node_id: str, props: dict, entity_type: str) -> None:
    other_props = {k: v for k, v in props.items() if k != "id"}
    if other_props:
        set_clauses = ", ".join(f"n.{k} = ${k}" for k in other_props)
        cypher = (
            f"MERGE (n:{label}:Entity {{id: $id}}) "
            f"SET {set_clauses}, n.entity_type = $entity_type"
        )
    else:
        cypher = (
            f"MERGE (n:{label}:Entity {{id: $id}}) "
            f"SET n.entity_type = $entity_type"
        )
    session.run(cypher, id=node_id, entity_type=entity_type, **other_props)

    if embedding_service is not None:
        try:
            embedding = embedding_service.embed_entity(entity_type, props)
            session.run(
                f"MATCH (n:{label} {{id: $id}}) SET n.embedding = $embedding",
                id=node_id,
                embedding=embedding,
            )
        except Exception as e:
            logger.warning(f"Failed to embed {entity_type} {node_id}: {e}")
