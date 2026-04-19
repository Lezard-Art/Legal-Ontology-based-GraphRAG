# LegalCorpusPipeline — Execution Plan (for Sonnet)

Take this repo from scaffolding-only to a working normative knowledge graph over all US federal law (plus a NY state pilot). Follow the phase structure in the project's authoritative planning docs; this file is the execution order and the set of guardrails.

## 0. Ground truth — read before touching anything

### 0.1 Authoritative docs (in `Ontology/` parent, NOT yet in this repo)

| Doc | Use |
|---|---|
| [`Combined_Normative_Ontology_Schema.md`](../Combined_Normative_Ontology_Schema.md) | Canonical ontology spec (4 layers). Source of truth for any schema question. |
| [`Engineering_Plan_Data_and_Parsing_Pipeline.md`](../Engineering_Plan_Data_and_Parsing_Pipeline.md) | Detailed engineering plan — agents, modules, prompts, batch API, infra. |
| [`Planning_Addendum_Decisions_and_Data.md`](../Planning_Addendum_Decisions_and_Data.md) | Decisions log + data catalog + the Phase 0–5 timeline this plan executes. |
| [`Normative_Ontology_Planning_Document.rtf`](../Normative_Ontology_Planning_Document.rtf) | Original planning doc — historical reference only. |

### 0.2 Ontology stack — **no Symboleo**

The schema in this project uses **four layers**:

1. **UFO-L** — Hohfeldian legal positions extended with Alexy's triadic model.
2. **LegalRuleML** — normative rules, defeasibility, deontic operators, conflict resolution.
3. **Domain Ontology** — real-world things norms regulate (persons, orgs, places, activities, substances, events, thresholds).
4. **USLM / Akoma Ntoso** — document hierarchy and cross-references.

**Symboleo is deliberately excluded.** It is a contract-specification DSL and does not apply to statutory/regulatory law. If you encounter Symboleo anywhere — in a doc, a dependency, a prompt, a schema field — it is a mistake; remove it. In particular, do **not** pull from `Ontology/PROPOSAL_Contract_Ontology.md` or `Ontology/02_Prototype_Specification.md` — those describe the separate contract-ontology-db project and use Symboleo.

### 0.3 Repo state (as of writing)

- **Not a git repo yet.** `git status` from `LegalCorpusPipeline/` returns "not a git repository".
- **Scaffolding only, per [README.md](README.md):** the `Fetcher` ABC exists, a partial `USCodeFetcher` stub is in `app/fetchers/uscode.py` (3 titles, not wired), the `Parser` seam has only `NoOpParser`, FastAPI app with dashboard + parse queue + document APIs is working, Alembic is stubbed (`metadata.create_all` at startup).
- **No concrete fetchers, no real parser, no triple store, no LLM integration.**

### 0.4 GitHub remote — decision required before any push

The GitHub URL [`github.com/Lezard-Art/Legal-Ontology-based-GraphRAG`](https://github.com/Lezard-Art/Legal-Ontology-based-GraphRAG) currently holds a different project (`contract-ontology-db`). Before pushing anything, **ask the user which of these they want**:

- **(A) Replace:** archive current `main` to a branch (`contract-ontology-db-archive`), then reset `main` to LegalCorpusPipeline. Nothing is lost; `main` cleanly represents the project the user is continuing.
- **(B) Rename + new repo:** rename the GitHub repo to `contract-ontology-db` (or similar), create a new repo for LegalCorpusPipeline, push there.
- **(C) Second branch:** keep `main` as contract-ontology-db and push LegalCorpusPipeline to a separate branch on the same repo. Not recommended — branches aren't meant to hold disjoint projects.

**Default recommendation: (A).** Do NOT force-push without asking. Never delete the existing remote history.

---

## Phase −1 — Initialize and preserve the planning docs

One-time setup before Phase 0:

1. `cd LegalCorpusPipeline && git init -b main`.
2. Verify `.gitignore` excludes `.env`, `*.db`, `data/raw/`, `__pycache__/`, `.pytest_cache/`, `.venv/`. Add any missing entries.
3. Copy authoritative docs into `docs/` so they ship with the repo (the repo should be self-contained when pushed):
   - `../Combined_Normative_Ontology_Schema.md` → `docs/ontology-schema.md`
   - `../Engineering_Plan_Data_and_Parsing_Pipeline.md` → `docs/engineering-plan.md`
   - `../Planning_Addendum_Decisions_and_Data.md` → `docs/decisions.md`
   - This `EXECUTION_PLAN.md` is already in the repo root.
4. Update [README.md](README.md): add a "Project context" section linking to the three `docs/` files; add a one-line statement that the ontology is UFO-L + LegalRuleML + Domain + USLM (no Symboleo).
5. Commit: `chore: initialize git repo and import planning docs`.
6. **Pause for user decision on §0.4.** Then: add remote, push `main`.

After §0.4 is resolved, every subsequent phase ends with commit + push.

---

## Phase 0 — Foundation and data acquisition

Follows [`docs/decisions.md` §A10 Phase 0](docs/decisions.md) (Weeks 1–6).

### 0.A Data acquisition (Weeks 1–2)

Implement concrete fetchers behind the existing `Fetcher` ABC (`app/fetchers/base.py`). One file per source under `app/fetchers/`, each registered in a source registry used by the scheduler.

Priority order (MVP → full):
1. **USC** — extend `uscode.py` from 3 titles to all 54. Source: `uscode.house.gov/download/` (USLM XML).
2. **eCFR** — all 50 titles. Source: `ecfr.gov` XML bulk.
3. **Federal Register / Executive Orders** — JSON via Federal Register API.
4. **Congress.gov bills** — requires API key (user must register; add `CONGRESS_API_KEY` to `.env.example`).
5. **CourtListener** (case law) — requires API key.
6. **NY Consolidated Laws** — Open Legislation API (NY Senate).
7. **NYCRR** — *blocked on licensing* per README. Leave a stub + `docs/nycrr-licensing.md` tracking the issue; do not attempt to scrape.

For each fetcher:
- Implement `discover()` and `fetch()` per the ABC.
- Write a retrieval test (integration-tier, skipped unless `RUN_NETWORK_TESTS=1`) that fetches one small doc and asserts the SHA256 is stable.
- Add a seed entry in `scripts/seed_sources.py`.
- Document rate limits, API key requirements, and data license in a per-source docstring.

Guardrails:
- **Blob storage is content-addressed** (SHA256); never overwrite. Re-running a fetcher on unchanged upstream content must be a no-op.
- **Respect robots.txt and rate limits.** When an API key is required, fail fast with a clear message — do not silently scrape.
- Do NOT commit any downloaded data. `data/raw/` is gitignored.

Commit per fetcher: `feat(fetchers): add <source> fetcher`. Push after each.

### 0.B Ontology schema finalization (Weeks 3–4)

The schema is already defined in `docs/ontology-schema.md`. This phase turns it into a machine-executable form:

1. Write OWL/Turtle serialization of the 4 layers under `ontology/` (new dir): `ontology/ufo-l.ttl`, `ontology/legalruleml.ttl`, `ontology/domain.ttl`, `ontology/uslm.ttl`, `ontology/combined.ttl` (imports the others).
2. Add a validation test in `tests/test_ontology.py` that parses each `.ttl` with `rdflib` and asserts key classes/properties exist.
3. Stand up a triple store locally (GraphDB Community OR Apache Jena Fuseki — pick one; document in `docs/triple-store.md`). Add Docker service to `docker-compose.yml`.
4. Define competency questions — add `docs/competency-questions.md` with 10–15 concrete SPARQL queries the graph must answer (copy from `docs/engineering-plan.md` if listed there; otherwise draft and ask the user to review).

Do NOT invent ontology concepts the schema doesn't specify. If something seems missing, ask the user — don't extend unilaterally.

Commit: `feat(ontology): OWL serialization of 4-layer schema`. Push.

### 0.C Manual gold-standard extractions (Weeks 5–6)

1. Select 15–20 representative provisions spanning obligations, prohibitions, permissions, delegations, definitions, penalties, exceptions, cross-references. Document the selection criteria in `tests/gold/README.md`.
2. Manually write the `NormativeExtraction` JSON-LD for each under `tests/gold/<provision-id>.jsonld`. Validate each against the ontology schema.
3. These become both (a) few-shot examples for the parser prompt (Phase 2) and (b) the ground-truth eval set.
4. Begin drafting the parsing prompt in `app/parse/prompts/normative_v1.md` — this is a plain-markdown file that the parser reads at runtime; keep it diffable.

Commit: `feat(gold): 20 manually extracted normative provisions as gold standard`. Push.

---

## Phase 1 — Structural parsing

Follows `docs/decisions.md` §A10 Phase 1 (Weeks 7–10).

Goal: every provision in USC + CFR as a node in the graph, with cross-reference edges. No normative content yet — skeleton only.

1. Write a `StructuralParser` implementing the `Parser` ABC (`app/parse/interface.py`). Register it in `app/parse/registry.py`. **No other file should change** per the seam's design contract.
2. Parse USLM XML → RDF triples using the `uslm` ontology from Phase 0.B. Extract:
   - Hierarchy: Title → Subtitle → Chapter → Subchapter → Part → Section → Subsection → Paragraph
   - Section headings, enactment dates, amendment references
   - Cross-references (`<ref>` elements) as edges
   - Definitions sections + defined terms
3. Write triples to the triple store. Use named graphs per source (`<urn:graph:usc>`, `<urn:graph:cfr>`).
4. Parse CFR XML similarly; link CFR provisions to their authorizing USC sections.
5. Verify with competency questions from Phase 0.B — at least the structural/cross-reference ones must pass.

Commit per milestone (USC done, CFR done, linkage done). Push after each.

---

## Phase 2 — LLM parsing prompt development

Follows `docs/decisions.md` §A10 Phase 2 (Weeks 11–16). See `docs/engineering-plan.md` Part C for full prompt architecture (batch API, cost, context assembly).

1. **Context assembly pipeline** (`app/parse/context.py`): for each provision, gather definitions, cross-referenced provisions, chapter context. This is the input to the LLM prompt.
2. **Prompt v1** (`app/parse/prompts/normative_v1.md`): includes the ontology as structured-output schema, the 20 gold examples as few-shot, instructions per norm type (obligation / prohibition / permission / power / definition / exception / penalty), defeasibility handling, confidence scoring.
3. **NormativeExtraction parser** implementing `Parser`: runs the prompt via Claude, validates output against the JSON-LD schema, writes triples.
4. **Eval harness** (`scripts/eval_parser.py`): run the parser against a held-out set of 50 provisions (NOT the gold 20); compare to manual review; measure precision/recall per norm type, cross-reference accuracy, defeasibility accuracy.
5. Iterate. Targets from the plan: ≥85% deontic-content identification, ≥75% correct relationship extraction.
6. **Batch API integration** for cost: implement `app/parse/batch_api/` per `docs/engineering-plan.md` §C.3. Submit in batches of 100–500 provisions.
7. Estimate full-corpus token cost; document in `docs/cost-estimate.md` and ask user approval before Phase 3.

Commit per milestone. Push after each.

---

## Phase 3 — Full federal extraction

Follows `docs/decisions.md` §A10 Phase 3 (Weeks 17–30). Long-running batch jobs.

Split exactly as the plan describes:
- Weeks 17–20: USC Titles 1–18.
- Weeks 21–24: USC Titles 19–54 + cross-title linking + Executive Orders.
- Weeks 25–28: CFR priority titles (those corresponding to most normatively rich USC titles — decide which by counting provisions per title from Phase 1 output).
- Weeks 29–30: quality review, gap-filling, statistics.

For each batch:
- Monitor queue via existing `/api/parse-queue` dashboard.
- Human-review any provision with confidence < 0.6 or with detected conflicts. Flag in `tests/review-queue/`.
- Do NOT push extracted triples to git. They live in the triple store; back them up to blob storage nightly (`scripts/backup_triples.py`).

---

## Phase 4 — NY state pilot + judicial interpretations

Follows `docs/decisions.md` §A10 Phase 4 (Weeks 31–40). Note: the addendum header says "New York state law" in the body but "Vermont" in the phase goal — the body is authoritative; the header is a typo. This project uses **NY** as the state pilot.

1. Extract NY Consolidated Laws + NYC Admin Code. Adapt the parsing prompt for state statutory style (it differs from federal).
2. Link NY provisions to federal where NY implements a federal mandate.
3. Judicial interpretation layer: select the most-cited provisions from CourtListener; extract interpretive holdings; add as `Interpretation` nodes linked to source provisions (per `docs/decisions.md` §A4).
4. Build the SPARQL query interface + a visual explorer. Validate against the competency questions. Demo: "What must the EPA Administrator do under the Clean Air Act, and what happens if they don't?"

---

## Phase 5 — Scale and refine

Per `docs/decisions.md` §A10 Phase 5. Open-ended: additional state pilots, full CFR extraction, treaties, CRS reports, legislative history, automated conflict detection, compliance checking, public API.

Treat this as a backlog, not a sprint — pick items with the user each planning session.

---

## Cross-cutting rules (apply to every phase)

- **Commit cadence:** one commit per logical change, subject line under 72 chars, imperative mood. Use conventional-commit prefixes (`feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`).
- **Never force-push `main`.** Never skip hooks (`--no-verify`). Never amend published commits.
- **Never commit:** `.env`, API keys, `*.db` files, `data/raw/`, anything over ~1 MB without user approval. If `.gitignore` needs updating, do it in a standalone commit first.
- **Ontology edits:** `docs/ontology-schema.md` is the source of truth. Any change to the schema requires a schema-change commit (`feat(ontology): ...`) and a matching update to the OWL serialization + the gold set.
- **Before pushing:** run `ruff check .`, `mypy app`, `pytest`. If any fails, fix it or ask — do not push broken.
- **Claude API usage:** prompts live in `app/parse/prompts/*.md` so they are diffable. Use prompt caching for the ontology schema + few-shot examples (they don't change across calls within a phase).
- **Cost discipline:** before any Claude batch > 1000 calls, print the estimated cost and require a `--yes` flag. Log actual cost after each batch.
- **If a phase takes more than ~a week of work to land, stop and check in** — don't compound.

---

## Sonnet's session-start checklist

Before the first non-trivial tool call of a session:
1. `cd LegalCorpusPipeline && git status && git log --oneline -5` — confirm branch + recent work.
2. Re-read the section of `docs/decisions.md` §A10 that corresponds to the current phase.
3. If this phase touches the ontology, re-read `docs/ontology-schema.md` — do not work from memory.
4. Confirm no Symboleo references have crept in: `grep -ri symboleo . --exclude-dir=.git --exclude-dir=.venv` should return nothing.
5. Then begin.
