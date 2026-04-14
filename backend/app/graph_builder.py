"""Builds a node-link graph from a contract for the visualization frontend."""
from .schemas import GraphNode, GraphEdge, GraphResponse


def build_graph(contract_data: dict) -> GraphResponse:
    """Convert a full contract dict into nodes + edges for Cytoscape/D3.

    Roles with the same label are collapsed into a single visual node so that
    multi-party contracts (e.g. 5 Limited Partners) show one role node with
    multiple party nodes connected to it, rather than 5 duplicate role nodes.
    """
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []
    seen_parties = set()

    # --- Contract node (center) ---
    nodes.append(GraphNode(
        id=contract_data["id"],
        label=contract_data["name"],
        type="Contract",
        data={"governing_law": contract_data.get("governing_law"),
              "jurisdiction": contract_data.get("jurisdiction")},
    ))

    # --- Parties and Roles (collapsed by label) ---
    # Build a map: role_label -> canonical role id  (first one seen wins)
    # and a reverse map: any role_id -> canonical role id
    role_label_to_canonical: dict[str, str] = {}   # label -> canonical id
    role_id_to_canonical: dict[str, str] = {}       # any id -> canonical id

    for role in contract_data.get("roles", []):
        label = role["label"]
        rid = role["id"]

        if label not in role_label_to_canonical:
            # First time seeing this label — this is the canonical node
            role_label_to_canonical[label] = rid
            role_id_to_canonical[rid] = rid

            nodes.append(GraphNode(
                id=rid,
                label=label,
                type="Role",
            ))
            edges.append(GraphEdge(
                source=rid,
                target=contract_data["id"],
                label="in contract",
                type="inContract",
            ))
        else:
            # Duplicate label — map this id to the canonical one
            role_id_to_canonical[rid] = role_label_to_canonical[label]

        # Party node (deduplicated)
        party_id = role.get("party_id")
        if party_id and party_id not in seen_parties:
            party = role.get("party") or {}
            nodes.append(GraphNode(
                id=party_id,
                label=party.get("name", party_id),
                type="Party",
                data={"party_type": party.get("type")},
            ))
            seen_parties.add(party_id)

        # Party → canonical role edge
        if party_id:
            canonical_rid = role_id_to_canonical.get(rid, rid)
            edges.append(GraphEdge(
                source=party_id,
                target=canonical_rid,
                label="plays role",
                type="playsRole",
            ))

    # Helper: resolve any role_id to its canonical (collapsed) id
    def _resolve(role_id: str | None) -> str | None:
        if role_id is None:
            return None
        return role_id_to_canonical.get(role_id, role_id)

    # --- Assets ---
    for asset in contract_data.get("assets", []):
        nodes.append(GraphNode(
            id=asset["id"],
            label=asset["name"],
            type="Asset",
            data={"asset_type": asset.get("type"),
                  "description": asset.get("description")},
        ))
        edges.append(GraphEdge(
            source=asset["id"],
            target=contract_data["id"],
            label="concerns",
            type="concerns",
        ))

    # --- Obligations (as edges with a node for metadata) ---
    for obl in contract_data.get("obligations", []):
        obl_id = obl["id"]
        nodes.append(GraphNode(
            id=obl_id,
            label=obl["description"][:60],
            type="Obligation",
            data={
                "consequent": obl.get("consequent"),
                "surviving": obl.get("surviving"),
                "temporal_constraint": obl.get("temporal_constraint"),
            },
        ))
        # debtor → obligation
        resolved_debtor = _resolve(obl.get("debtor_role_id"))
        if resolved_debtor:
            edges.append(GraphEdge(
                source=resolved_debtor,
                target=obl_id,
                label="owes",
                type="owes",
            ))
        # obligation → creditor
        resolved_creditor = _resolve(obl.get("creditor_role_id"))
        if resolved_creditor:
            edges.append(GraphEdge(
                source=obl_id,
                target=resolved_creditor,
                label="owed to",
                type="owedTo",
            ))
        # link to clause
        if obl.get("clause_id"):
            edges.append(GraphEdge(
                source=obl_id,
                target=obl["clause_id"],
                label="sourced from",
                type="sourcedFrom",
            ))

    # --- Powers ---
    for pwr in contract_data.get("powers", []):
        pwr_id = pwr["id"]
        nodes.append(GraphNode(
            id=pwr_id,
            label=pwr["description"][:60],
            type="Power",
            data={
                "consequent": pwr.get("consequent"),
                "trigger": pwr.get("trigger_condition"),
            },
        ))
        resolved_creditor = _resolve(pwr.get("creditor_role_id"))
        if resolved_creditor:
            edges.append(GraphEdge(
                source=resolved_creditor,
                target=pwr_id,
                label="empowered",
                type="empowers",
            ))
        resolved_debtor = _resolve(pwr.get("debtor_role_id"))
        if resolved_debtor:
            edges.append(GraphEdge(
                source=pwr_id,
                target=resolved_debtor,
                label="over",
                type="subjectTo",
            ))
        if pwr.get("clause_id"):
            edges.append(GraphEdge(
                source=pwr_id,
                target=pwr["clause_id"],
                label="sourced from",
                type="sourcedFrom",
            ))

    # --- Clauses ---
    for cl in contract_data.get("clauses", []):
        nodes.append(GraphNode(
            id=cl["id"],
            label=f"§{cl.get('section_number', '?')} {cl.get('heading', '')}".strip(),
            type="Clause",
            data={"text": cl.get("text"), "ontology_tag": cl.get("ontology_tag")},
        ))

    return GraphResponse(nodes=nodes, edges=edges)
