"""Pydantic schemas for request/response validation and Hohfeld enforcement."""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field
import uuid


def _uuid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Hohfeld correlative map
# ---------------------------------------------------------------------------

HOHFELD_CORRELATIVES = {
    "Right": "Duty",
    "Duty": "Right",
    "Permission": "NoRight",
    "NoRight": "Permission",
    "Power": "Subjection",
    "Subjection": "Power",
    "Immunity": "Disability",
    "Disability": "Immunity",
}

VALID_POSITION_TYPES = set(HOHFELD_CORRELATIVES.keys())


# ---------------------------------------------------------------------------
# Core schemas
# ---------------------------------------------------------------------------

class PartyCreate(BaseModel):
    name: str
    type: str = Field(..., pattern="^(Person|Organization|Institution)$")
    identifiers: Optional[list[dict]] = None

class PartyOut(PartyCreate):
    id: str
    class Config:
        from_attributes = True


class RoleCreate(BaseModel):
    label: str
    party_id: str
    contract_id: str

class RoleOut(RoleCreate):
    id: str
    class Config:
        from_attributes = True


class AssetCreate(BaseModel):
    contract_id: str
    name: str
    type: Optional[str] = None
    description: Optional[str] = None
    owned_by_id: Optional[str] = None
    properties: Optional[list[dict]] = None

class AssetOut(AssetCreate):
    id: str
    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Legal positions
# ---------------------------------------------------------------------------

class LegalPositionCreate(BaseModel):
    position_type: str
    holder_role_id: str
    counter_role_id: str
    description: str
    object: Optional[str] = None
    polarity: Optional[str] = None
    condition: Optional[dict] = None
    clause_id: Optional[str] = None

class LegalPositionOut(LegalPositionCreate):
    id: str
    correlative_id: Optional[str] = None
    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Deontics
# ---------------------------------------------------------------------------

class TemporalConstraintSchema(BaseModel):
    type: str                                # Deadline | Period | PointInTime | Relative
    reference_date: Optional[str] = None
    offset_days: Optional[int] = None
    description: Optional[str] = None


class ConditionSchema(BaseModel):
    type: str = "Simple"                     # Simple | Compound | Temporal
    description: str
    expression: Optional[str] = None
    sub_conditions: Optional[list[ConditionSchema]] = None
    operator: Optional[str] = None           # AND | OR | NOT


class ObligationCreate(BaseModel):
    contract_id: str
    debtor_role_id: str
    creditor_role_id: str
    description: str
    consequent: Optional[str] = None
    temporal_constraint: Optional[TemporalConstraintSchema] = None
    condition: Optional[ConditionSchema] = None
    surviving: bool = False
    survival_period: Optional[str] = None
    clause_id: Optional[str] = None

class ObligationOut(BaseModel):
    id: str
    contract_id: str
    debtor_role_id: str
    creditor_role_id: str
    description: str
    consequent: Optional[str] = None
    temporal_constraint: Optional[dict] = None
    condition: Optional[dict] = None
    surviving: bool = False
    survival_period: Optional[str] = None
    clause_id: Optional[str] = None
    class Config:
        from_attributes = True


class PowerCreate(BaseModel):
    contract_id: str
    creditor_role_id: str
    debtor_role_id: str
    description: str
    trigger_condition: Optional[ConditionSchema] = None
    consequent: Optional[str] = None
    clause_id: Optional[str] = None

class PowerOut(BaseModel):
    id: str
    contract_id: str
    creditor_role_id: str
    debtor_role_id: str
    description: str
    trigger_condition: Optional[dict] = None
    consequent: Optional[str] = None
    clause_id: Optional[str] = None
    class Config:
        from_attributes = True


class ConstraintCreate(BaseModel):
    contract_id: str
    description: str
    expression: Optional[str] = None
    clause_id: Optional[str] = None

class ConstraintOut(ConstraintCreate):
    id: str
    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Document module
# ---------------------------------------------------------------------------

class ClauseCreate(BaseModel):
    contract_id: str
    section_number: Optional[str] = None
    heading: Optional[str] = None
    text: str
    start_offset: Optional[int] = None
    end_offset: Optional[int] = None
    ontology_tag: Optional[str] = None

class ClauseOut(ClauseCreate):
    id: str
    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Contract (composite)
# ---------------------------------------------------------------------------

class ContractCreate(BaseModel):
    name: str
    effective_date: Optional[str] = None
    expiration_date: Optional[str] = None
    governing_law: Optional[str] = None
    jurisdiction: Optional[str] = None
    source_text: Optional[str] = None

class ContractOut(ContractCreate):
    id: str
    json_ld: Optional[dict] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    class Config:
        from_attributes = True


class ContractFull(ContractOut):
    """Contract with all nested entities for detail view."""
    roles: list[RoleOut] = []
    assets: list[AssetOut] = []
    obligations: list[ObligationOut] = []
    powers: list[PowerOut] = []
    constraints: list[ConstraintOut] = []
    clauses: list[ClauseOut] = []
    parties: list[PartyOut] = []         # assembled from roles


# ---------------------------------------------------------------------------
# Graph response (for visualization)
# ---------------------------------------------------------------------------

class GraphNode(BaseModel):
    id: str
    label: str
    type: str                            # Party, Role, Obligation, Power, Asset, Clause
    data: Optional[dict] = None

class GraphEdge(BaseModel):
    source: str
    target: str
    label: str
    type: str                            # playsRole, owes, empowers, concerns, sourcedFrom

class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


# ---------------------------------------------------------------------------
# Parse request/response
# ---------------------------------------------------------------------------

class ParseRequest(BaseModel):
    text: str
    contract_name: Optional[str] = None

class ParseResponse(BaseModel):
    contract: ContractFull
    confidence: Optional[float] = None
    warnings: list[str] = []


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class ValidationResult(BaseModel):
    valid: bool
    errors: list[str] = []
    warnings: list[str] = []
