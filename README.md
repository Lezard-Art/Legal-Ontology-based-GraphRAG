# Legal Corpus Pipeline

Ingestion + parsing pipeline for a normative knowledge graph over all US federal law (+ NY state pilot). Extracts statutes, regulations, and case law into a 4-layer formal ontology:

- **UFO-L** — Hohfeldian legal positions (Right, Duty, Power, Immunity, ...) extended with Alexy's triadic model
- **LegalRuleML** — normative rules, defeasibility, deontic operators, conflict resolution
- **Domain Ontology** — real-world things norms regulate (persons, orgs, places, activities, substances, events, thresholds)
- **USLM / Akoma Ntoso** — US legislative document hierarchy and cross-references

> **Symboleo is not used.** This project covers statutory and regulatory law, not individual contracts.

See [`docs/ontology-schema.md`](docs/ontology-schema.md) for the canonical schema, [`docs/engineering-plan.md`](docs/engineering-plan.md) for the full engineering plan, and [`docs/decisions.md`](docs/decisions.md) for the decisions log and phase timeline.

---

**Current state:** pipeline scaffolding only. **No concrete fetchers and no parser are implemented.**
The `Fetcher` ABC is in place for later source agents; the `Parser` seam has only
a `NoOpParser` stub that returns `{"bytes": N}`.

## Quick start (SQLite, zero infra)

```bash
pip install -e ".[dev]"
export DATABASE_URL_CORPUS="sqlite:///./corpus.db"
export DATABASE_URL_PARSED="sqlite:///./parsed.db"
export BLOB_STORE_ROOT="./data/raw"
python -m scripts.seed_sources
uvicorn app.main:app --reload
```

Visit http://localhost:8000/dashboard and http://localhost:8000/docs.

## Quick start (Postgres, plan-spec)

```bash
cp .env.example .env
docker compose up -d corpus_db parsed_db
pip install -e ".[dev]"
python -m scripts.seed_sources
uvicorn app.main:app --reload
```

## End-to-end NoOp flow

```bash
# 1. Insert a fake Document + DocumentVersion for testing (no fetcher yet).
python -m scripts.insert_fake_document

# 2. Enqueue it for parsing with the NoOp parser.
curl -X POST http://localhost:8000/api/documents/<doc_id>/parse

# 3. Watch the queue process it.
curl http://localhost:8000/api/parse-queue
curl http://localhost:8000/api/documents/<doc_id>/parse-history
```

## Running tests

```bash
pytest
ruff check .
mypy app
```

## What is intentionally NOT in this repo

- Concrete fetchers (USC, eCFR, Federal Register, NY Senate, CourtListener, NYCRR).
  The `Fetcher` ABC is the integration point. NYCRR is additionally blocked on
  commercial licensing — see `docs/nycrr-licensing.md` (TBD).
- Any real parser. Replace `app/parse/noop.py` with your parser implementing
  `app.parse.interface.Parser` and register it in `app/parse/registry.py`.
  **No other file should need to change.**
- Alembic migrations are stubbed; the app currently calls `metadata.create_all`
  on startup for v1 convenience. Swap for real Alembic revisions before prod.
