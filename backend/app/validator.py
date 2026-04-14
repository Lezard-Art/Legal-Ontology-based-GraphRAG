"""Ontology validator — enforces Hohfeld correlative pairing and structural rules."""
from .schemas import HOHFELD_CORRELATIVES, VALID_POSITION_TYPES, ValidationResult


def validate_contract(contract_data: dict) -> ValidationResult:
    """Validate a full contract dict (as returned by /contracts/{id}/full)."""
    errors = []
    warnings = []

    roles = {r["id"]: r for r in contract_data.get("roles", [])}
    parties = {p["id"]: p for p in contract_data.get("parties", [])}
    clauses = {c["id"]: c for c in contract_data.get("clauses", [])}
    obligations = contract_data.get("obligations", [])
    powers = contract_data.get("powers", [])
    positions = contract_data.get("legal_positions", [])

    # --- Rule 1: At least 2 parties / 2 roles ---
    if len(roles) < 2:
        errors.append("Contract must have at least 2 roles.")
    if len(parties) < 2:
        warnings.append("Contract has fewer than 2 distinct parties.")

    # --- Rule 2: Every role references a valid party ---
    for role in roles.values():
        if role.get("party_id") and role["party_id"] not in parties:
            errors.append(f"Role '{role['label']}' references unknown party '{role['party_id']}'.")

    # --- Rule 3: Every obligation has valid debtor and creditor ---
    for obl in obligations:
        if obl.get("debtor_role_id") not in roles:
            errors.append(f"Obligation '{obl['description'][:50]}' has invalid debtor role.")
        if obl.get("creditor_role_id") not in roles:
            errors.append(f"Obligation '{obl['description'][:50]}' has invalid creditor role.")
        if obl.get("debtor_role_id") == obl.get("creditor_role_id"):
            warnings.append(f"Obligation '{obl['description'][:50]}' has same debtor and creditor.")

    # --- Rule 4: Every power has valid creditor and debtor ---
    for pwr in powers:
        if pwr.get("creditor_role_id") not in roles:
            errors.append(f"Power '{pwr['description'][:50]}' has invalid creditor role.")
        if pwr.get("debtor_role_id") not in roles:
            errors.append(f"Power '{pwr['description'][:50]}' has invalid debtor role.")

    # --- Rule 5: Legal positions have valid types ---
    for pos in positions:
        if pos.get("position_type") not in VALID_POSITION_TYPES:
            errors.append(f"Legal position has invalid type '{pos.get('position_type')}'.")

    # --- Rule 6: Hohfeld correlative pairing ---
    positions_by_id = {p["id"]: p for p in positions}
    for pos in positions:
        corr_id = pos.get("correlative_id")
        if corr_id:
            corr = positions_by_id.get(corr_id)
            if not corr:
                errors.append(
                    f"Position '{pos['description'][:50]}' references missing correlative '{corr_id}'."
                )
            else:
                expected = HOHFELD_CORRELATIVES.get(pos["position_type"])
                if corr["position_type"] != expected:
                    errors.append(
                        f"Position '{pos['position_type']}' should pair with '{expected}', "
                        f"but correlative is '{corr['position_type']}'."
                    )
        else:
            warnings.append(
                f"Position '{pos.get('description', '?')[:50]}' has no correlative linked."
            )

    # --- Rule 7: Clause references are valid ---
    for obl in obligations:
        if obl.get("clause_id") and obl["clause_id"] not in clauses:
            warnings.append(f"Obligation references unknown clause '{obl['clause_id']}'.")

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )
