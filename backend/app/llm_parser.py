"""LLM-based contract parser — sends contract text to Claude, gets back structured JSON."""
import os
import json
from anthropic import Anthropic

SYSTEM_PROMPT = """You are a legal ontology extraction engine. You receive the full text of a contract and must return a structured JSON representation following this ontology:

## Entity Types

**Party**: A legal person or organization mentioned in the contract.
- name (string, required)
- type: "Person" | "Organization" | "Institution"
- role (string, required) — the label of the Role this party plays (must match a Role label exactly)

**Role**: A unique contractual position within the contract (e.g. "Seller", "Buyer", "Limited Partner", "General Partner").
- label (string, required) — e.g. "Seller"

CRITICAL — Role vs Party distinction:
- A Role is a CONTRACTUAL POSITION (e.g. "Limited Partner", "General Partner", "Lessee").
- A Party is a SPECIFIC ENTITY that fills a role.
- If 5 companies are all Limited Partners, create ONE role {"label": "Limited Partner"} and 5 parties, each with "role": "Limited Partner".
- Do NOT create duplicate roles with the same label. Each unique contractual position appears exactly ONCE in the roles array.
- Obligations and powers reference ROLES (not parties). All parties sharing a role share the same obligations.

**Asset**: A tangible or intangible thing of value that the contract concerns.
- name (string, required)
- type: "Tangible" | "Intangible"
- description (string)

**Obligation**: Something one role MUST do for another role. An obligation has a debtor (who must act) and a creditor (who is owed the action).
- debtor_role (string) — label of the debtor Role (must match a Role label exactly)
- creditor_role (string) — label of the creditor Role (must match a Role label exactly)
- description (string, required) — what must be done
- consequent (string) — the specific action/outcome required
- temporal_constraint (object, optional):
  - type: "Deadline" | "Period" | "PointInTime" | "Relative"
  - description: human-readable description
  - reference_date: if applicable
  - offset_days: if applicable
- surviving (boolean) — does this survive contract termination?
- condition (object, optional): under what circumstances this obligation applies

**Power**: The right of one role to change the legal relationship (e.g. terminate, suspend, modify).
- creditor_role (string) — who holds the power (must match a Role label exactly)
- debtor_role (string) — who is subject to it (must match a Role label exactly)
- description (string, required)
- trigger (string) — what activates this power
- consequent (string) — what the power-holder can do

**Constraint**: A structural constraint on the contract (e.g. non-assignment, exclusivity).
- description (string, required)
- expression (string, optional) — semi-formal expression

**Clause**: A tagged section of the contract text.
- section_number (string) — e.g. "3.1"
- heading (string) — section heading if any
- text (string, required) — the exact text
- ontology_tag (string) — one of: "preamble", "definition", "party_identification",
  "obligation", "power", "right", "permission", "prohibition", "condition",
  "temporal_provision", "asset_description", "consideration", "termination",
  "dispute_resolution", "governing_law", "confidentiality", "indemnification",
  "limitation_of_liability", "force_majeure", "assignment", "amendment",
  "notice", "severability", "entire_agreement", "signature", "boilerplate", "other"

## Rules
1. Every obligation MUST have both a debtor_role and creditor_role that exactly match a label in the roles array.
2. Every power MUST have both a creditor_role and debtor_role that exactly match a label in the roles array.
3. Identify ALL parties and which role each plays. Multiple parties can share one role.
4. The roles array must contain NO duplicate labels. Each unique contractual position appears once.
5. Tag EVERY meaningful section of the contract as a Clause with the correct ontology_tag.
6. Temporal conditions (deadlines, periods) are structural facts — include them.
7. Be thorough: extract ALL obligations, powers, and constraints, not just the obvious ones.

## Output Format
Return ONLY valid JSON (no markdown, no explanation) with this structure:
{
  "parties": [...],
  "roles": [...],
  "assets": [...],
  "obligations": [...],
  "powers": [...],
  "constraints": [...],
  "clauses": [...]
}"""


def parse_contract(text: str, contract_name: str = "Untitled Contract") -> dict:
    """Parse contract text using Claude API. Returns structured dict."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    if not api_key:
        # Return a helpful error structure instead of crashing
        return {
            "error": "ANTHROPIC_API_KEY not set. Set it as an environment variable to enable LLM parsing.",
            "parties": [],
            "roles": [],
            "assets": [],
            "obligations": [],
            "powers": [],
            "constraints": [],
            "clauses": [],
        }

    client = Anthropic(api_key=api_key)

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Parse the following contract into the ontology structure.\n\nContract name: {contract_name}\n\n---\n\n{text}",
            }
        ],
    )

    response_text = message.content[0].text.strip()

    # Try to extract JSON from the response
    try:
        # Handle case where model wraps in ```json blocks
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        result = json.loads(response_text)
    except json.JSONDecodeError:
        # Try to find JSON object in the response
        start = response_text.find("{")
        end = response_text.rfind("}") + 1
        if start >= 0 and end > start:
            result = json.loads(response_text[start:end])
        else:
            result = {"error": "Failed to parse LLM response as JSON", "raw": response_text}

    return result
