"""SQLAlchemy ORM models — mirrors the ontology from 02_Prototype_Specification.md."""
import uuid
from sqlalchemy import Column, String, Text, Boolean, Integer, Date, ForeignKey, JSON
from sqlalchemy.orm import relationship
from .database import Base


def new_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Core Module
# ---------------------------------------------------------------------------

class Contract(Base):
    __tablename__ = "contracts"

    id = Column(String, primary_key=True, default=new_id)
    name = Column(String, nullable=False)
    effective_date = Column(String)          # ISO date string
    expiration_date = Column(String)
    governing_law = Column(String)
    jurisdiction = Column(String)
    source_text = Column(Text)               # full original contract text
    json_ld = Column(JSON)                   # complete serialized contract
    created_at = Column(String)
    updated_at = Column(String)

    # relationships
    roles = relationship("Role", back_populates="contract", cascade="all, delete-orphan")
    assets = relationship("Asset", back_populates="contract", cascade="all, delete-orphan")
    obligations = relationship("Obligation", back_populates="contract", cascade="all, delete-orphan")
    powers = relationship("Power", back_populates="contract", cascade="all, delete-orphan")
    constraints = relationship("Constraint", back_populates="contract", cascade="all, delete-orphan")
    clauses = relationship("Clause", back_populates="contract", cascade="all, delete-orphan")


class Party(Base):
    __tablename__ = "parties"

    id = Column(String, primary_key=True, default=new_id)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)     # Person | Organization | Institution
    identifiers = Column(JSON)                # [{ key, value }]

    roles = relationship("Role", back_populates="party")


class Role(Base):
    __tablename__ = "roles"

    id = Column(String, primary_key=True, default=new_id)
    label = Column(String, nullable=False)
    party_id = Column(String, ForeignKey("parties.id"))
    contract_id = Column(String, ForeignKey("contracts.id"))

    party = relationship("Party", back_populates="roles")
    contract = relationship("Contract", back_populates="roles")
    held_positions = relationship("LegalPosition", foreign_keys="LegalPosition.holder_role_id", back_populates="holder")


class Asset(Base):
    __tablename__ = "assets"

    id = Column(String, primary_key=True, default=new_id)
    contract_id = Column(String, ForeignKey("contracts.id"))
    name = Column(String, nullable=False)
    type = Column(String)                     # Tangible | Intangible
    description = Column(Text)
    owned_by_id = Column(String, ForeignKey("parties.id"))
    properties = Column(JSON)

    contract = relationship("Contract", back_populates="assets")


# ---------------------------------------------------------------------------
# Legal Positions Module
# ---------------------------------------------------------------------------

class LegalPosition(Base):
    __tablename__ = "legal_positions"

    id = Column(String, primary_key=True, default=new_id)
    position_type = Column(String, nullable=False)   # Right|Duty|Permission|NoRight|Power|Subjection|Immunity|Disability
    holder_role_id = Column(String, ForeignKey("roles.id"))
    counter_role_id = Column(String, ForeignKey("roles.id"))
    correlative_id = Column(String, ForeignKey("legal_positions.id"))
    description = Column(Text)
    object = Column(Text)                    # the action/state targeted
    polarity = Column(String)                # Positive | Negative
    condition = Column(JSON)
    clause_id = Column(String, ForeignKey("clauses.id"))

    holder = relationship("Role", foreign_keys=[holder_role_id], back_populates="held_positions")
    counter = relationship("Role", foreign_keys=[counter_role_id])
    correlative = relationship("LegalPosition", remote_side=[id], uselist=False)


# ---------------------------------------------------------------------------
# Deontics Module
# ---------------------------------------------------------------------------

class Obligation(Base):
    __tablename__ = "obligations"

    id = Column(String, primary_key=True, default=new_id)
    contract_id = Column(String, ForeignKey("contracts.id"))
    debtor_role_id = Column(String, ForeignKey("roles.id"))
    creditor_role_id = Column(String, ForeignKey("roles.id"))
    description = Column(Text, nullable=False)
    consequent = Column(Text)
    temporal_constraint = Column(JSON)
    condition = Column(JSON)
    surviving = Column(Boolean, default=False)
    survival_period = Column(String)
    clause_id = Column(String, ForeignKey("clauses.id"))

    contract = relationship("Contract", back_populates="obligations")
    debtor = relationship("Role", foreign_keys=[debtor_role_id])
    creditor = relationship("Role", foreign_keys=[creditor_role_id])


class Power(Base):
    __tablename__ = "powers"

    id = Column(String, primary_key=True, default=new_id)
    contract_id = Column(String, ForeignKey("contracts.id"))
    creditor_role_id = Column(String, ForeignKey("roles.id"))
    debtor_role_id = Column(String, ForeignKey("roles.id"))
    description = Column(Text, nullable=False)
    trigger_condition = Column(JSON)
    consequent = Column(Text)
    clause_id = Column(String, ForeignKey("clauses.id"))

    contract = relationship("Contract", back_populates="powers")
    creditor = relationship("Role", foreign_keys=[creditor_role_id])
    debtor = relationship("Role", foreign_keys=[debtor_role_id])


class Constraint(Base):
    __tablename__ = "constraints"

    id = Column(String, primary_key=True, default=new_id)
    contract_id = Column(String, ForeignKey("contracts.id"))
    description = Column(Text)
    expression = Column(Text)
    clause_id = Column(String, ForeignKey("clauses.id"))

    contract = relationship("Contract", back_populates="constraints")


# ---------------------------------------------------------------------------
# Document Module
# ---------------------------------------------------------------------------

class Clause(Base):
    __tablename__ = "clauses"

    id = Column(String, primary_key=True, default=new_id)
    contract_id = Column(String, ForeignKey("contracts.id"))
    section_number = Column(String)
    heading = Column(String)
    text = Column(Text, nullable=False)
    start_offset = Column(Integer)
    end_offset = Column(Integer)
    ontology_tag = Column(String)

    contract = relationship("Contract", back_populates="clauses")
