"""Contract Ontology Database — FastAPI application."""
from dotenv import load_dotenv
import pathlib
load_dotenv(pathlib.Path(__file__).resolve().parent.parent.parent / ".env", override=True)

from datetime import datetime, timezone
from fastapi import FastAPI, Depends, HTTPException, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os
import uuid

from . import models, schemas
from .database import engine, get_db, Base
from .graph_builder import build_graph
from .validator import validate_contract
from .llm_parser import parse_contract
from .extractor import extract_text

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Contract Ontology Database", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Serve frontend static files
# ---------------------------------------------------------------------------
# __file__ = backend/app/main.py  →  go up 3 levels to reach the project root
FRONTEND_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "frontend", "dist",
)

if os.path.isdir(FRONTEND_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")), name="assets")


# ---------------------------------------------------------------------------
# Helper: serialize a full contract with all nested entities
# ---------------------------------------------------------------------------

def _serialize_contract_full(contract: models.Contract, db: Session) -> dict:
    """Build the full nested dict for a contract."""
    party_ids = set()
    roles_out = []
    for r in contract.roles:
        party_ids.add(r.party_id)
        roles_out.append({
            "id": r.id, "label": r.label,
            "party_id": r.party_id, "contract_id": r.contract_id,
            "party": {"id": r.party.id, "name": r.party.name, "type": r.party.type,
                       "identifiers": r.party.identifiers} if r.party else None,
        })

    parties_out = []
    for pid in party_ids:
        p = db.query(models.Party).get(pid)
        if p:
            parties_out.append({"id": p.id, "name": p.name, "type": p.type, "identifiers": p.identifiers})

    obligations_out = [
        {"id": o.id, "contract_id": o.contract_id, "debtor_role_id": o.debtor_role_id,
         "creditor_role_id": o.creditor_role_id, "description": o.description,
         "consequent": o.consequent, "temporal_constraint": o.temporal_constraint,
         "condition": o.condition, "surviving": o.surviving,
         "survival_period": o.survival_period, "clause_id": o.clause_id}
        for o in contract.obligations
    ]

    powers_out = [
        {"id": p.id, "contract_id": p.contract_id, "creditor_role_id": p.creditor_role_id,
         "debtor_role_id": p.debtor_role_id, "description": p.description,
         "trigger_condition": p.trigger_condition, "consequent": p.consequent,
         "clause_id": p.clause_id}
        for p in contract.powers
    ]

    constraints_out = [
        {"id": c.id, "contract_id": c.contract_id, "description": c.description,
         "expression": c.expression, "clause_id": c.clause_id}
        for c in contract.constraints
    ]

    clauses_out = [
        {"id": c.id, "contract_id": c.contract_id, "section_number": c.section_number,
         "heading": c.heading, "text": c.text, "start_offset": c.start_offset,
         "end_offset": c.end_offset, "ontology_tag": c.ontology_tag}
        for c in contract.clauses
    ]

    assets_out = [
        {"id": a.id, "contract_id": a.contract_id, "name": a.name, "type": a.type,
         "description": a.description, "owned_by_id": a.owned_by_id, "properties": a.properties}
        for a in contract.assets
    ]

    # Legal positions for this contract's roles
    role_ids = [r.id for r in contract.roles]
    positions = db.query(models.LegalPosition).filter(
        models.LegalPosition.holder_role_id.in_(role_ids)
    ).all()
    positions_out = [
        {"id": p.id, "position_type": p.position_type, "holder_role_id": p.holder_role_id,
         "counter_role_id": p.counter_role_id, "correlative_id": p.correlative_id,
         "description": p.description, "object": p.object, "polarity": p.polarity,
         "condition": p.condition, "clause_id": p.clause_id}
        for p in positions
    ]

    return {
        "id": contract.id, "name": contract.name,
        "effective_date": contract.effective_date,
        "expiration_date": contract.expiration_date,
        "governing_law": contract.governing_law,
        "jurisdiction": contract.jurisdiction,
        "source_text": contract.source_text,
        "json_ld": contract.json_ld,
        "created_at": contract.created_at,
        "updated_at": contract.updated_at,
        "parties": parties_out,
        "roles": roles_out,
        "assets": assets_out,
        "obligations": obligations_out,
        "powers": powers_out,
        "constraints": constraints_out,
        "clauses": clauses_out,
        "legal_positions": positions_out,
    }


# ---------------------------------------------------------------------------
# CONTRACTS
# ---------------------------------------------------------------------------

@app.get("/api/contracts", response_model=list[schemas.ContractOut])
def list_contracts(db: Session = Depends(get_db)):
    return db.query(models.Contract).all()


@app.post("/api/contracts", response_model=schemas.ContractOut)
def create_contract(data: schemas.ContractCreate, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc).isoformat()
    contract = models.Contract(
        id=str(uuid.uuid4()), name=data.name,
        effective_date=data.effective_date, expiration_date=data.expiration_date,
        governing_law=data.governing_law, jurisdiction=data.jurisdiction,
        source_text=data.source_text, created_at=now, updated_at=now,
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)
    return contract


@app.get("/api/contracts/{contract_id}")
def get_contract(contract_id: str, db: Session = Depends(get_db)):
    contract = db.query(models.Contract).get(contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return _serialize_contract_full(contract, db)


@app.delete("/api/contracts/{contract_id}")
def delete_contract(contract_id: str, db: Session = Depends(get_db)):
    contract = db.query(models.Contract).get(contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    db.delete(contract)
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# GRAPH
# ---------------------------------------------------------------------------

@app.get("/api/contracts/{contract_id}/graph", response_model=schemas.GraphResponse)
def get_contract_graph(contract_id: str, db: Session = Depends(get_db)):
    contract = db.query(models.Contract).get(contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    data = _serialize_contract_full(contract, db)
    return build_graph(data)


# ---------------------------------------------------------------------------
# VALIDATE
# ---------------------------------------------------------------------------

@app.get("/api/contracts/{contract_id}/validate", response_model=schemas.ValidationResult)
def validate_contract_endpoint(contract_id: str, db: Session = Depends(get_db)):
    contract = db.query(models.Contract).get(contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    data = _serialize_contract_full(contract, db)
    return validate_contract(data)


# ---------------------------------------------------------------------------
# PARTIES
# ---------------------------------------------------------------------------

@app.get("/api/parties", response_model=list[schemas.PartyOut])
def list_parties(db: Session = Depends(get_db)):
    return db.query(models.Party).all()


@app.post("/api/parties", response_model=schemas.PartyOut)
def create_party(data: schemas.PartyCreate, db: Session = Depends(get_db)):
    party = models.Party(id=str(uuid.uuid4()), name=data.name, type=data.type, identifiers=data.identifiers)
    db.add(party)
    db.commit()
    db.refresh(party)
    return party


# ---------------------------------------------------------------------------
# ROLES
# ---------------------------------------------------------------------------

@app.post("/api/roles", response_model=schemas.RoleOut)
def create_role(data: schemas.RoleCreate, db: Session = Depends(get_db)):
    role = models.Role(id=str(uuid.uuid4()), label=data.label,
                       party_id=data.party_id, contract_id=data.contract_id)
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


# ---------------------------------------------------------------------------
# OBLIGATIONS
# ---------------------------------------------------------------------------

@app.post("/api/obligations", response_model=schemas.ObligationOut)
def create_obligation(data: schemas.ObligationCreate, db: Session = Depends(get_db)):
    obl = models.Obligation(
        id=str(uuid.uuid4()), contract_id=data.contract_id,
        debtor_role_id=data.debtor_role_id, creditor_role_id=data.creditor_role_id,
        description=data.description, consequent=data.consequent,
        temporal_constraint=data.temporal_constraint.model_dump() if data.temporal_constraint else None,
        condition=data.condition.model_dump() if data.condition else None,
        surviving=data.surviving, survival_period=data.survival_period,
        clause_id=data.clause_id,
    )
    db.add(obl)
    db.commit()
    db.refresh(obl)
    return obl


# ---------------------------------------------------------------------------
# POWERS
# ---------------------------------------------------------------------------

@app.post("/api/powers", response_model=schemas.PowerOut)
def create_power(data: schemas.PowerCreate, db: Session = Depends(get_db)):
    pwr = models.Power(
        id=str(uuid.uuid4()), contract_id=data.contract_id,
        creditor_role_id=data.creditor_role_id, debtor_role_id=data.debtor_role_id,
        description=data.description, consequent=data.consequent,
        trigger_condition=data.trigger_condition.model_dump() if data.trigger_condition else None,
        clause_id=data.clause_id,
    )
    db.add(pwr)
    db.commit()
    db.refresh(pwr)
    return pwr


# ---------------------------------------------------------------------------
# CLAUSES
# ---------------------------------------------------------------------------

@app.post("/api/clauses", response_model=schemas.ClauseOut)
def create_clause(data: schemas.ClauseCreate, db: Session = Depends(get_db)):
    cl = models.Clause(
        id=str(uuid.uuid4()), contract_id=data.contract_id,
        section_number=data.section_number, heading=data.heading,
        text=data.text, start_offset=data.start_offset, end_offset=data.end_offset,
        ontology_tag=data.ontology_tag,
    )
    db.add(cl)
    db.commit()
    db.refresh(cl)
    return cl


# ---------------------------------------------------------------------------
# ASSETS
# ---------------------------------------------------------------------------

@app.post("/api/assets", response_model=schemas.AssetOut)
def create_asset(data: schemas.AssetCreate, db: Session = Depends(get_db)):
    asset = models.Asset(
        id=str(uuid.uuid4()), contract_id=data.contract_id,
        name=data.name, type=data.type, description=data.description,
        owned_by_id=data.owned_by_id, properties=data.properties,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


# ---------------------------------------------------------------------------
# LLM PARSE
# ---------------------------------------------------------------------------

@app.post("/api/parse")
def parse_contract_endpoint(req: schemas.ParseRequest, db: Session = Depends(get_db)):
    """Parse natural language contract text into ontology structure using LLM."""
    result = parse_contract(req.text, req.contract_name or "Untitled")

    if "error" in result and not result.get("parties"):
        return result  # pass through error

    return result


def _save_parsed_contract(parsed: dict, name: str, source_text: str, db: Session) -> models.Contract:
    """Shared logic: take LLM-parsed JSON and persist all entities to the DB.

    Key design decisions:
    - Roles are deduplicated by label — only one Role row per unique label.
    - Multiple parties can share one role (each gets a separate Role row with
      the same label but different party_id, but the role_map used for linking
      obligations/powers points to the FIRST canonical role for that label).
    - Parties declare which role they play via a 'role' field (new prompt) or
      legacy 'party_name' on the role object (old prompt). Both are supported.
    - Fuzzy matching: obligation/power role lookups are case-insensitive.
    """
    now = datetime.now(timezone.utc).isoformat()

    # Create contract
    contract = models.Contract(
        id=str(uuid.uuid4()),
        name=name,
        source_text=source_text,
        json_ld=parsed,
        created_at=now,
        updated_at=now,
    )
    db.add(contract)
    db.flush()

    # ------------------------------------------------------------------
    # Create parties
    # ------------------------------------------------------------------
    party_map = {}  # name -> Party model
    for p in parsed.get("parties", []):
        party = models.Party(
            id=str(uuid.uuid4()),
            name=p["name"],
            type=p.get("type", "Organization"),
            identifiers=p.get("identifiers"),
        )
        db.add(party)
        party_map[p["name"]] = party
    db.flush()

    # ------------------------------------------------------------------
    # Build party→role mapping from both new and legacy formats
    # New format: party has {"role": "Limited Partner"}
    # Legacy format: role has {"party_name": "Acme Corp"}
    # ------------------------------------------------------------------
    party_role_assignments: dict[str, str] = {}  # party_name -> role_label

    # New prompt format: each party declares its role
    for p in parsed.get("parties", []):
        if p.get("role"):
            party_role_assignments[p["name"]] = p["role"]

    # Legacy format: role declares its party_name
    for r in parsed.get("roles", []):
        if r.get("party_name"):
            party_role_assignments[r["party_name"]] = r["label"]

    # ------------------------------------------------------------------
    # Create roles — deduplicated by label
    # For each unique label, create one "canonical" Role (first party found).
    # Then create additional Role rows for other parties sharing the label.
    # role_map always points to the canonical one for obligation/power linking.
    # ------------------------------------------------------------------
    role_map: dict[str, models.Role] = {}        # label -> canonical Role
    role_map_lower: dict[str, models.Role] = {}  # lowercase label -> canonical Role

    # First pass: create one canonical Role per unique label
    seen_labels: set[str] = set()
    for r in parsed.get("roles", []):
        label = r["label"]
        if label in seen_labels:
            continue
        seen_labels.add(label)

        # Find the first party assigned to this role
        first_party = None
        if r.get("party_name") and r["party_name"] in party_map:
            first_party = party_map[r["party_name"]]
        else:
            for pname, rlabel in party_role_assignments.items():
                if rlabel == label and pname in party_map:
                    first_party = party_map[pname]
                    break

        role = models.Role(
            id=str(uuid.uuid4()),
            label=label,
            party_id=first_party.id if first_party else None,
            contract_id=contract.id,
        )
        db.add(role)
        role_map[label] = role
        role_map_lower[label.lower()] = role

    db.flush()

    # Second pass: create additional Role rows for remaining parties
    # that share an already-created role label (so graph can link them).
    assigned_parties: set[str] = set()
    # Track which parties already got a role row above
    for label, role in role_map.items():
        if role.party_id:
            for pname, p in party_map.items():
                if p.id == role.party_id:
                    assigned_parties.add(pname)
                    break

    for pname, rlabel in party_role_assignments.items():
        if pname in assigned_parties:
            continue
        if pname not in party_map:
            continue
        party = party_map[pname]
        role = models.Role(
            id=str(uuid.uuid4()),
            label=rlabel,
            party_id=party.id,
            contract_id=contract.id,
        )
        db.add(role)
        assigned_parties.add(pname)
        # Don't overwrite role_map — the canonical one stays

    db.flush()

    # ------------------------------------------------------------------
    # Helper: resolve a role label string to the canonical Role
    # ------------------------------------------------------------------
    def _resolve_role(label: str | None) -> models.Role | None:
        if not label:
            return None
        # Exact match first
        if label in role_map:
            return role_map[label]
        # Case-insensitive fallback
        return role_map_lower.get(label.lower())

    # ------------------------------------------------------------------
    # Create clauses
    # ------------------------------------------------------------------
    for c in parsed.get("clauses", []):
        db.add(models.Clause(
            id=str(uuid.uuid4()),
            contract_id=contract.id,
            section_number=c.get("section_number"),
            heading=c.get("heading"),
            text=c["text"],
            ontology_tag=c.get("ontology_tag"),
        ))
    db.flush()

    # ------------------------------------------------------------------
    # Create assets
    # ------------------------------------------------------------------
    for a in parsed.get("assets", []):
        db.add(models.Asset(
            id=str(uuid.uuid4()),
            contract_id=contract.id,
            name=a["name"],
            type=a.get("type"),
            description=a.get("description"),
            properties=a.get("properties"),
        ))

    # ------------------------------------------------------------------
    # Create obligations
    # ------------------------------------------------------------------
    for o in parsed.get("obligations", []):
        debtor = _resolve_role(o.get("debtor_role"))
        creditor = _resolve_role(o.get("creditor_role"))
        db.add(models.Obligation(
            id=str(uuid.uuid4()),
            contract_id=contract.id,
            debtor_role_id=debtor.id if debtor else None,
            creditor_role_id=creditor.id if creditor else None,
            description=o["description"],
            consequent=o.get("consequent"),
            temporal_constraint=o.get("temporal_constraint"),
            condition=o.get("condition"),
            surviving=o.get("surviving", False),
            survival_period=o.get("survival_period"),
        ))

    # ------------------------------------------------------------------
    # Create powers
    # ------------------------------------------------------------------
    for p in parsed.get("powers", []):
        creditor = _resolve_role(p.get("creditor_role"))
        debtor = _resolve_role(p.get("debtor_role"))
        db.add(models.Power(
            id=str(uuid.uuid4()),
            contract_id=contract.id,
            creditor_role_id=creditor.id if creditor else None,
            debtor_role_id=debtor.id if debtor else None,
            description=p["description"],
            trigger_condition={"description": p["trigger"]} if p.get("trigger") else None,
            consequent=p.get("consequent"),
        ))

    # ------------------------------------------------------------------
    # Create constraints
    # ------------------------------------------------------------------
    for c in parsed.get("constraints", []):
        db.add(models.Constraint(
            id=str(uuid.uuid4()),
            contract_id=contract.id,
            description=c["description"],
            expression=c.get("expression"),
        ))

    db.commit()
    db.refresh(contract)
    return contract


@app.post("/api/parse-and-save")
def parse_and_save(req: schemas.ParseRequest, db: Session = Depends(get_db)):
    """Parse contract text via LLM and save to database in one step."""
    parsed = parse_contract(req.text, req.contract_name or "Untitled")

    if "error" in parsed and not parsed.get("parties"):
        raise HTTPException(status_code=500, detail=parsed["error"])

    contract = _save_parsed_contract(
        parsed, req.contract_name or "Untitled Contract", req.text, db
    )
    return _serialize_contract_full(contract, db)


# ---------------------------------------------------------------------------
# FILE UPLOAD PARSE (PDF / DOCX)
# ---------------------------------------------------------------------------

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


@app.post("/api/parse-file")
async def parse_file_endpoint(
    file: UploadFile,
    contract_name: str = Form(None),
):
    """Extract text from a PDF/DOCX file and return parsed ontology JSON."""
    raw = await file.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 10 MB limit.")

    try:
        text = extract_text(raw, file.filename or "unknown.pdf")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    name = contract_name or file.filename or "Untitled"
    result = parse_contract(text, name)

    if "error" in result and not result.get("parties"):
        return result

    return result


@app.post("/api/parse-file-and-save")
async def parse_file_and_save(
    file: UploadFile,
    contract_name: str = Form(None),
    db: Session = Depends(get_db),
):
    """Extract text from PDF/DOCX, parse via LLM, and save to database."""
    raw = await file.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 10 MB limit.")

    try:
        text = extract_text(raw, file.filename or "unknown.pdf")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    name = contract_name or file.filename or "Untitled"
    parsed = parse_contract(text, name)

    if "error" in parsed and not parsed.get("parties"):
        raise HTTPException(status_code=500, detail=parsed["error"])

    contract = _save_parsed_contract(parsed, name, text, db)
    return _serialize_contract_full(contract, db)


# ---------------------------------------------------------------------------
# Catch-all: serve frontend index.html
# ---------------------------------------------------------------------------

@app.get("/{full_path:path}")
def serve_frontend(full_path: str):
    index = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.isfile(index):
        return FileResponse(index)
    return {"message": "Contract Ontology Database API", "docs": "/docs"}
