"""
Download 25 sample contracts from SEC EDGAR (the same source used by CUAD and
the Stanford Material Contracts Corpus) and parse them into the ontology DB.

Strategy:
  1. Query the EDGAR EFTS full-text search for EX-10 exhibits (material contracts)
  2. For each hit, resolve the actual document URL from the filing directory
  3. Download and strip HTML
  4. Parse via Claude → save to DB

References in project README:
  - CUAD: https://www.atticusprojectai.org/cuad (sources contracts from EDGAR)
  - Stanford MCC: https://mcc.law.stanford.edu (also from EDGAR)
  - SEC EDGAR direct: https://efts.sec.gov/LATEST/search-index?q=...
"""
import sys
import os
import re
import json
import uuid
import time
import urllib.request
import urllib.parse
import urllib.error
from html.parser import HTMLParser
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Setup paths so we can import project modules
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env", override=True)

from backend.app.database import SessionLocal, engine
from backend.app import models
from backend.app.llm_parser import parse_contract
from backend.app.database import Base

Base.metadata.create_all(bind=engine)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
NUM_CONTRACTS = 25
# Truncate contract text (keeps costs manageable; ~3-4K input tokens)
MAX_CHARS = 15_000
# EDGAR rate limit: 10 req/sec; we stay well under it
REQUEST_DELAY = 0.15
# Pause between Claude API calls
CLAUDE_DELAY = 2.0

# User-Agent required by SEC EDGAR robots policy
EDGAR_UA = "contract-ontology-research/1.0 contact@research.example.com"

# EFTS search — queries that return material contracts
SEARCH_QUERIES = [
    "license agreement",
    "supply agreement",
    "service agreement",
    "employment agreement",
    "purchase agreement",
]


# ---------------------------------------------------------------------------
# HTML text extractor
# ---------------------------------------------------------------------------

class TextExtractor(HTMLParser):
    """Minimal HTML → plain-text converter using stdlib only."""

    SKIP_TAGS = {"script", "style", "head", "meta", "link"}

    def __init__(self):
        super().__init__()
        self.chunks: list[str] = []
        self._skip_depth = 0
        self._current_skip: str | None = None

    def handle_starttag(self, tag, attrs):
        if tag.lower() in self.SKIP_TAGS:
            self._skip_depth += 1
            self._current_skip = tag

    def handle_endtag(self, tag):
        if tag.lower() in self.SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth == 0:
            self.chunks.append(data)

    def get_text(self) -> str:
        raw = "".join(self.chunks)
        # Collapse whitespace
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        return "\n".join(lines)


def html_to_text(html: str) -> str:
    p = TextExtractor()
    try:
        p.feed(html)
        return p.get_text()
    except Exception:
        # Fallback: strip tags with regex
        text = re.sub(r"<[^>]+>", " ", html)
        return re.sub(r"\s+", " ", text).strip()


# ---------------------------------------------------------------------------
# EDGAR helpers
# ---------------------------------------------------------------------------

def edgar_get(url: str, as_text: bool = True) -> str | bytes:
    """Fetch a URL from EDGAR with proper rate limiting and User-Agent."""
    req = urllib.request.Request(url, headers={"User-Agent": EDGAR_UA})
    time.sleep(REQUEST_DELAY)
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    return data.decode("utf-8", errors="replace") if as_text else data


def efts_search(query: str, page_size: int = 40) -> list[dict]:
    """
    Query the EDGAR EFTS full-text search and return hits that are EX-10 exhibits.
    """
    params = urllib.parse.urlencode({
        "q": f'"{query}"',
        "dateRange": "custom",
        "startdt": "2023-01-01",
        "enddt": "2024-12-31",
    })
    url = f"https://efts.sec.gov/LATEST/search-index?{params}"
    raw = edgar_get(url)
    data = json.loads(raw)
    hits = data.get("hits", {}).get("hits", [])

    # Keep only EX-10 exhibit hits
    return [h for h in hits if h.get("_source", {}).get("file_type", "").upper().startswith("EX-10")]


def resolve_document_url(hit: dict) -> str | None:
    """
    Given an EFTS hit, return a direct HTTPS URL for the exhibit document,
    by consulting the filing's directory listing on EDGAR.
    """
    src = hit.get("_source", {})
    adsh: str = src.get("adsh", "")
    ciks: list = src.get("ciks", [])
    sequence: int = src.get("sequence", 0)
    file_type: str = src.get("file_type", "")

    if not adsh or not ciks:
        return None

    cik_raw = ciks[0].lstrip("0")  # e.g. "0001850838" → "1850838"
    adsh_no_dashes = adsh.replace("-", "")  # e.g. "000095017024038094"
    dir_url = f"https://www.sec.gov/Archives/edgar/data/{cik_raw}/{adsh_no_dashes}/"

    try:
        html = edgar_get(dir_url)
    except Exception:
        return None

    # Extract all links from the directory page
    links = re.findall(r'href="(/Archives/edgar/data/[^"]+)"', html)

    # Prefer plain .txt exhibit files, then .htm
    candidates_txt = [
        lnk for lnk in links
        if re.search(r"ex[-_]?10", lnk, re.I) and lnk.lower().endswith(".txt")
    ]
    candidates_htm = [
        lnk for lnk in links
        if re.search(r"ex[-_]?10", lnk, re.I) and lnk.lower().endswith(".htm")
    ]

    chosen = None
    if candidates_txt:
        chosen = candidates_txt[0]
    elif candidates_htm:
        chosen = candidates_htm[0]
    else:
        # Fall back to any non-index, non-main file in the right sequence region
        all_docs = [
            lnk for lnk in links
            if not lnk.endswith("-index.htm") and not lnk.endswith("-index-headers.htm")
            and not adsh_no_dashes + ".txt" in lnk
            and (lnk.endswith(".htm") or lnk.endswith(".txt"))
        ]
        # Sort and pick the one at roughly the right position
        if len(all_docs) >= sequence:
            chosen = all_docs[min(sequence - 1, len(all_docs) - 1)]
        elif all_docs:
            chosen = all_docs[0]

    return f"https://www.sec.gov{chosen}" if chosen else None


def fetch_contract_text(url: str) -> str:
    """Download a contract document (HTML or text) and return clean plain text."""
    raw = edgar_get(url)

    # Detect HTML vs plain text
    if re.search(r"<html|<!DOCTYPE", raw[:500], re.I):
        text = html_to_text(raw)
    else:
        text = raw

    # Remove EDGAR header boilerplate that appears before actual contract
    # These headers end at a blank line or "EXHIBIT" heading
    lines = text.splitlines()
    start = 0
    for i, line in enumerate(lines):
        if re.match(r"EXHIBIT\s+10|THIS AGREEMENT|AGREEMENT\s+dated", line, re.I):
            start = i
            break
    text = "\n".join(lines[start:])

    return text.strip()


def derive_contract_name(hit: dict, url: str) -> str:
    """Derive a human-readable contract name from EDGAR metadata."""
    src = hit.get("_source", {})
    entity = src.get("display_names", ["Unknown Entity"])[0]
    # Strip the ticker + CIK suffix: "Omega Therapeutics, Inc.  (OMGA)  (CIK 0001850838)"
    entity = re.sub(r"\s*\([^)]*\)\s*$", "", entity).strip()
    entity = re.sub(r"\s*\([^)]*\)\s*$", "", entity).strip()
    file_type = src.get("file_type", "EX-10")
    file_date = src.get("file_date", "")[:7]  # "YYYY-MM"
    return f"{entity} — {file_type} ({file_date})"


# ---------------------------------------------------------------------------
# DB save (mirrors parse-and-save logic in main.py)
# ---------------------------------------------------------------------------

def save_to_db(db, contract_name: str, contract_text: str, parsed: dict) -> str:
    """Persist a parsed contract and all its entities. Returns contract ID."""
    now = datetime.now(timezone.utc).isoformat()

    contract = models.Contract(
        id=str(uuid.uuid4()),
        name=contract_name,
        source_text=contract_text,
        json_ld=parsed,
        created_at=now,
        updated_at=now,
    )
    db.add(contract)
    db.flush()

    # Parties
    party_map: dict[str, models.Party] = {}
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

    # Roles
    role_map: dict[str, models.Role] = {}
    for r in parsed.get("roles", []):
        party = party_map.get(r.get("party_name", ""))
        role = models.Role(
            id=str(uuid.uuid4()),
            label=r["label"],
            party_id=party.id if party else None,
            contract_id=contract.id,
        )
        db.add(role)
        role_map[r["label"]] = role
    db.flush()

    # Clauses
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

    # Assets
    for a in parsed.get("assets", []):
        db.add(models.Asset(
            id=str(uuid.uuid4()),
            contract_id=contract.id,
            name=a["name"],
            type=a.get("type"),
            description=a.get("description"),
            properties=a.get("properties"),
        ))

    # Obligations
    for o in parsed.get("obligations", []):
        debtor = role_map.get(o.get("debtor_role", ""))
        creditor = role_map.get(o.get("creditor_role", ""))
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

    # Powers
    for p in parsed.get("powers", []):
        creditor = role_map.get(p.get("creditor_role", ""))
        debtor = role_map.get(p.get("debtor_role", ""))
        db.add(models.Power(
            id=str(uuid.uuid4()),
            contract_id=contract.id,
            creditor_role_id=creditor.id if creditor else None,
            debtor_role_id=debtor.id if debtor else None,
            description=p["description"],
            trigger_condition={"description": p["trigger"]} if p.get("trigger") else None,
            consequent=p.get("consequent"),
        ))

    # Constraints
    for c in parsed.get("constraints", []):
        db.add(models.Constraint(
            id=str(uuid.uuid4()),
            contract_id=contract.id,
            description=c["description"],
            expression=c.get("expression"),
        ))

    db.commit()
    return contract.id


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 65)
    print("  SEC EDGAR Material Contract Importer")
    print("  (Same source used by CUAD & Stanford Material Contracts Corpus)")
    print("=" * 65)
    print()

    # ---- Collect candidate hits across multiple search queries ----
    print("Searching SEC EDGAR for EX-10 material contracts...")
    seen_adsh: set[str] = set()
    candidates: list[tuple[dict, str]] = []  # (hit, doc_url)

    for query in SEARCH_QUERIES:
        if len(candidates) >= NUM_CONTRACTS + 10:
            break
        print(f"  query: \"{query}\"", end=" ", flush=True)
        try:
            hits = efts_search(query)
            print(f"→ {len(hits)} EX-10 hits")
        except Exception as e:
            print(f"→ ERROR: {e}")
            continue

        for hit in hits:
            src = hit.get("_source", {})
            adsh = src.get("adsh", "")
            if not adsh or adsh in seen_adsh:
                continue
            seen_adsh.add(adsh)

            doc_url = resolve_document_url(hit)
            if doc_url:
                candidates.append((hit, doc_url))
                if len(candidates) >= NUM_CONTRACTS + 10:
                    break

    print(f"\nResolved {len(candidates)} document URLs\n")

    if not candidates:
        print("ERROR: No contracts found. Check your internet connection.")
        sys.exit(1)

    # ---- Parse and save ----
    db = SessionLocal()
    imported = 0
    failed = 0
    total = min(NUM_CONTRACTS, len(candidates))

    for i, (hit, doc_url) in enumerate(candidates[:total], 1):
        name = derive_contract_name(hit, doc_url)
        label = f"[{i:02d}/{total}]"
        print(f"{label} {name}")
        print(f"         {doc_url}")

        try:
            # Download contract text
            text = fetch_contract_text(doc_url)
            if len(text) < 100:
                print(f"         SKIP: document too short ({len(text)} chars)")
                failed += 1
                continue

            truncated = len(text) > MAX_CHARS
            display_len = min(len(text), MAX_CHARS)
            if truncated:
                text_for_parsing = text[:MAX_CHARS] + "\n\n[... contract continues ...]"
            else:
                text_for_parsing = text

            suffix = f" (truncated {len(text):,}→{display_len:,} chars)" if truncated else f" ({len(text):,} chars)"
            print(f"         downloaded{suffix}")

            # Parse via Claude
            parsed = parse_contract(text_for_parsing, name)

            if "error" in parsed and not parsed.get("parties"):
                print(f"         ERROR: {parsed['error']}")
                failed += 1
                continue

            # Save to DB
            contract_id = save_to_db(db, name, text_for_parsing, parsed)

            n_parties = len(parsed.get("parties", []))
            n_roles = len(parsed.get("roles", []))
            n_obligations = len(parsed.get("obligations", []))
            n_powers = len(parsed.get("powers", []))
            n_clauses = len(parsed.get("clauses", []))
            print(
                f"         OK  id={contract_id[:8]}  "
                f"parties={n_parties}  roles={n_roles}  "
                f"obligations={n_obligations}  powers={n_powers}  clauses={n_clauses}"
            )
            imported += 1

        except Exception as e:
            print(f"         FAILED: {e}")
            try:
                db.rollback()
            except Exception:
                pass
            failed += 1
            continue

        # Rate-limit Claude API calls
        if i < total:
            time.sleep(CLAUDE_DELAY)

    db.close()

    print()
    print("=" * 65)
    print(f"  Done: {imported} imported, {failed} failed / skipped")
    print(f"  Database: {PROJECT_ROOT / 'contracts.db'}")
    print("=" * 65)


if __name__ == "__main__":
    main()
