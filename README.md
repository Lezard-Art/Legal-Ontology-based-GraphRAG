# Legal-Ontology-based-GraphRAG

A tool for parsing natural language contracts into a formal ontological format, storing them as structured data, and visualizing them as interactive knowledge graphs.

Built on three theoretical frameworks:
- **UFO-L** (Unified Foundational Ontology — Lightweight)
- **Symboleo** (domain-specific language for contract specification)
- **Hohfeld's Legal Positions** (formal framework for rights, duties, powers, and immunities)

## Features

- **LLM-powered contract parsing** — Paste or upload a contract (PDF/DOCX) and Claude extracts parties, roles, obligations, powers, constraints, and clauses into the ontology
- **Interactive graph visualization** — Explore contracts as knowledge graphs with color-coded entity types (Cytoscape.js)
- **Ontological validation** — Validates Hohfeld correlative pairings, role references, and structural consistency
- **Clause semantic tagging** — 19 clause types (obligation, power, condition, indemnification, etc.)
- **REST API** — Full CRUD + parse + validate endpoints with Swagger docs

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, SQLAlchemy, Pydantic |
| Database | SQLite |
| LLM | Claude 3.5 Sonnet (Anthropic SDK) |
| Frontend | React 19, Vite |
| Graph Viz | Cytoscape.js + Cola layout |
| File Extraction | PyMuPDF (PDF), python-docx (DOCX) |

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+ (for frontend development)
- An [Anthropic API key](https://console.anthropic.com/) for LLM parsing

### Setup

```bash
# Clone the repo
git clone https://github.com/<your-username>/contract-ontology-db.git
cd contract-ontology-db

# Create virtual environment and install dependencies
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# Seed the database with an example contract
python scripts/seed.py

# Start the backend server
./run.sh
# or: uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev    # Vite dev server with API proxy
```

### Access

- **UI:** http://localhost:8000
- **API Docs (Swagger):** http://localhost:8000/docs
- **Frontend Dev Server:** http://localhost:5173 (if running Vite separately)

## Project Structure

```
contract-ontology-db/
├── backend/
│   └── app/
│       ├── main.py           # FastAPI application, all routes
│       ├── models.py         # SQLAlchemy ORM models (ontology entities)
│       ├── schemas.py        # Pydantic schemas + Hohfeld rules
│       ├── database.py       # DB connection
│       ├── validator.py      # Ontological consistency checker
│       ├── graph_builder.py  # Builds graph for visualization
│       ├── llm_parser.py     # Claude API integration for parsing
│       └── extractor.py      # PDF/DOCX text extraction
├── frontend/
│   ├── src/
│   │   ├── App.jsx           # React UI (list, detail, graph, parse views)
│   │   └── main.jsx          # Entry point
│   └── vite.config.js        # Vite config with API proxy
├── scripts/
│   ├── seed.py               # Seeds DB with example Meat Sale contract
│   └── import_cuad.py        # Bulk importer for CUAD dataset
├── graphrag-plan/            # Architecture & implementation plans for GraphRAG
│   ├── architecture.md
│   └── implementation.md
├── requirements.txt
├── run.sh                    # Start script
└── README.md
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/contracts` | List all contracts |
| `POST` | `/api/contracts` | Create contract |
| `GET` | `/api/contracts/{id}` | Full contract with all nested entities |
| `DELETE` | `/api/contracts/{id}` | Delete contract |
| `GET` | `/api/contracts/{id}/graph` | Graph data (nodes + edges) for visualization |
| `GET` | `/api/contracts/{id}/validate` | Validate ontological consistency |
| `POST` | `/api/parse` | Parse contract text via LLM (preview only) |
| `POST` | `/api/parse-and-save` | Parse via LLM and save to database |
| `POST` | `/api/upload-and-parse` | Upload PDF/DOCX, extract text, parse via LLM |
| `POST` | `/api/upload-parse-and-save` | Upload, extract, parse, and save |
| `GET` | `/api/parties` | List all parties |
| `POST` | `/api/parties` | Create party |
| `POST` | `/api/roles` | Create role |
| `POST` | `/api/obligations` | Create obligation |
| `POST` | `/api/powers` | Create power |
| `POST` | `/api/clauses` | Create clause |
| `POST` | `/api/assets` | Create asset |

## Ontology Model

```
Contract
 ├── Party ──plays──▶ Role
 ├── Obligation (debtor Role → creditor Role)
 │    └── Constraint (deadline, condition, etc.)
 ├── Power (holder Role → subject Role)
 ├── Clause (with ontology_tag)
 ├── Asset
 └── LegalPosition (Hohfeld: Right↔Duty, Power↔Subjection, etc.)
```

## Test Contract Datasets

For testing with real contracts:

1. **[CUAD](https://www.atticusprojectai.org/cuad)** — 510 commercial contracts, expert-annotated with 41 clause types
2. **[Material Contracts Corpus](https://mcc.law.stanford.edu)** — 1M+ contracts from SEC EDGAR filings
3. **[SEC EDGAR](https://efts.sec.gov/LATEST/search-index?q=%22agreement%22&forms=10-K)** — Public company filings including material agreements
4. **[ContractNLI](https://stanfordnlp.github.io/contract-nli/)** — Contracts annotated for natural language inference

## Roadmap

- [ ] GraphRAG query system (see `graphrag-plan/`)
- [ ] Neo4j graph database integration
- [ ] Contract edit/update endpoints
- [ ] Full-text search and filtering
- [ ] OCR for scanned PDFs
- [ ] Authentication and multi-user support
- [ ] RDF/OWL export
- [ ] Test suite

## License

MIT
