# GraphRAG Implementation Plan

## Prerequisites

Before starting, ensure:
- Neo4j Community Edition installed (Docker recommended)
- Python 3.10+
- Existing contract-ontology-db codebase running
- At least one parsed contract in SQLite

---

## Phase 1: Neo4j Setup & Data Migration (Week 1-2)

### 1.1 Install & Configure Neo4j

```bash
# Docker (recommended)
docker run -d --name neo4j-contracts \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/contractgraph \
  -e NEO4J_PLUGINS='["graph-data-science"]' \
  neo4j:5-community

# Add to .env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=contractgraph
```

**Files to create/modify:**
- `backend/app/neo4j_client.py` — Neo4j connection manager (driver init, session factory, health check)
- `backend/app/database.py` — Add Neo4j connection alongside SQLite
- `requirements.txt` — Add `neo4j`, `neo4j-graphrag-python`

### 1.2 Define Graph Schema

**File:** `backend/app/graph_schema.py`

Create Cypher constraints and indexes:
```cypher
CREATE CONSTRAINT contract_id IF NOT EXISTS FOR (c:Contract) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT party_id IF NOT EXISTS FOR (p:Party) REQUIRE p.id IS UNIQUE;
-- ... for all entity types

CREATE VECTOR INDEX entity_embeddings IF NOT EXISTS
FOR (n:Entity) ON (n.embedding)
OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: 'cosine'}};

CREATE FULLTEXT INDEX clause_text IF NOT EXISTS FOR (c:Clause) ON EACH [c.text];
```

### 1.3 Build SQLite → Neo4j Sync

**File:** `backend/app/graph_sync.py`

Functions:
- `sync_contract_to_graph(contract_id)` — Read from SQLite, create/update in Neo4j
- `sync_all_contracts()` — Full rebuild
- `delete_contract_from_graph(contract_id)` — Remove on delete

**Hook into existing code:**
- `main.py` POST `/api/parse-and-save` → call `sync_contract_to_graph()` after SQLite save
- `main.py` DELETE `/api/contracts/{id}` → call `delete_contract_from_graph()` after SQLite delete

### 1.4 Migration Script

**File:** `scripts/migrate_to_neo4j.py`

One-time script to load all existing SQLite contracts into Neo4j.

**Deliverable:** All existing contracts queryable in Neo4j. Verify with Neo4j Browser at `http://localhost:7474`.

---

## Phase 2: Embedding Pipeline (Week 2-3)

### 2.1 Embedding Service

**File:** `backend/app/embeddings.py`

```python
class EmbeddingService:
    def __init__(self, model="text-embedding-3-small"):  # or voyage-3
        ...

    def embed_text(self, text: str) -> list[float]:
        ...

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        ...

    def embed_entity(self, entity_type: str, properties: dict) -> list[float]:
        """Create a descriptive string from entity properties, then embed."""
        ...
```

**Add to `.env`:** `OPENAI_API_KEY=...` (or `VOYAGE_API_KEY=...`)
**Add to `requirements.txt`:** `openai` (or `voyageai`)

### 2.2 Entity Embedding Templates

Create natural language descriptions for each entity type to embed:

| Entity | Description Template |
|--------|---------------------|
| Contract | "{name}: {governing_law} contract between {parties}, effective {date}" |
| Party | "{name}: {description}" |
| Obligation | "{name}: {debtor_role} must {description} for {creditor_role}. Trigger: {trigger}" |
| Power | "{name}: {holder_role} may {description}. Trigger: {trigger}" |
| Clause | "{clause_number}: {text}" (full clause text) |
| Constraint | "{type}: {description} — {expression}" |

### 2.3 Embed & Store

**File:** `backend/app/graph_sync.py` (extend)

After syncing entities to Neo4j, generate embeddings and store as node properties:
```cypher
MATCH (n:Obligation {id: $id})
SET n.embedding = $embedding, n.description_text = $desc
```

**Deliverable:** All entities in Neo4j have `.embedding` vector properties. Vector index is populated.

---

## Phase 3: Community Detection & Summarization (Week 3-4)

### 3.1 Community Detection

**File:** `backend/app/communities.py`

Option A — **Neo4j GDS** (preferred if GDS plugin installed):
```cypher
CALL gds.graph.project('contracts', '*', '*')
CALL gds.leiden.write('contracts', {
  writeProperty: 'community_id',
  maxLevels: 3
})
```

Option B — **Python graspologic** (if no GDS):
```python
from graspologic.partition import leiden
# Export adjacency from Neo4j → run leiden → write back community IDs
```

### 3.2 Community Summary Generation

For each community:
1. Collect all member entities and their relationships
2. Send to Claude with prompt:
   ```
   Summarize the following group of contract entities and their relationships.
   Focus on: what obligations exist, between whom, under what conditions,
   and what powers or remedies are available.
   ```
3. Store summary text + embedding on `(:Community)` node

**File:** `backend/app/communities.py` — `generate_community_summaries()`

### 3.3 Rebuild Pipeline

**File:** `backend/app/communities.py` — `rebuild_communities()`

Full pipeline: detect → summarize → embed → store. Triggered by:
- POST `/api/graph/rebuild`
- Optionally after each new contract ingestion (if corpus is small)

**Deliverable:** Community nodes in Neo4j with summaries. Queryable hierarchy.

---

## Phase 4: Query Engine (Week 4-6)

### 4.1 Query Classifier

**File:** `backend/app/query_engine.py`

```python
class QueryClassifier:
    def classify(self, question: str) -> Literal["local", "global", "hybrid", "cypher"]:
        """Use Claude to classify query intent."""
        # Prompt: Given this question about contracts, classify as:
        # - local: about specific entities/contracts
        # - global: about patterns/themes across contracts
        # - hybrid: needs both specific and broad context
        # - cypher: directly translatable to graph query
```

### 4.2 Local Search

**File:** `backend/app/retrievers.py`

```python
class LocalRetriever:
    def retrieve(self, question: str, top_k: int = 10) -> list[dict]:
        # 1. Embed the question
        # 2. Vector search in Neo4j for nearest entities
        # 3. For each matched entity, traverse 1-2 hops
        # 4. Collect: entity props, relationships, clause texts, community summary
        # 5. Rank and trim to fit context window
        # 6. Return structured context
```

### 4.3 Global Search

**File:** `backend/app/retrievers.py`

```python
class GlobalRetriever:
    def retrieve(self, question: str, community_level: int = 1) -> list[dict]:
        # 1. Fetch all community summaries at target level
        # 2. MAP: For each community, ask Claude:
        #    "Given this community summary, what is relevant to: {question}?"
        # 3. Filter out empty/irrelevant responses
        # 4. REDUCE: Combine relevant community responses
        # 5. Return aggregated context
```

### 4.4 Answer Synthesis

**File:** `backend/app/query_engine.py`

```python
class QueryEngine:
    def query(self, question: str, strategy: str = "auto") -> QueryResult:
        # 1. Classify query (if auto)
        # 2. Route to retriever(s)
        # 3. Assemble context
        # 4. Send to Claude with system prompt:
        #    "Answer based ONLY on the provided context.
        #     Cite specific entities and clauses.
        #     If the context doesn't contain the answer, say so."
        # 5. Return answer + sources + graph context
```

### 4.5 API Endpoints

**File:** `backend/app/main.py` (extend)

```python
@app.post("/api/query")
async def query_graph(request: QueryRequest, db: Session = Depends(get_db)):
    engine = QueryEngine(neo4j_driver, embedding_service, llm_client)
    result = engine.query(request.question, strategy=request.strategy)
    return result

@app.post("/api/graph/rebuild")
async def rebuild_graph(db: Session = Depends(get_db)):
    sync_all_contracts(db, neo4j_driver)
    rebuild_communities(neo4j_driver, llm_client, embedding_service)
    return {"status": "rebuilt"}
```

**Deliverable:** Working natural language query interface over the contract graph.

---

## Phase 5: Frontend Integration (Week 6-7)

### 5.1 Query Chat Interface

**File:** `frontend/src/App.jsx` (extend) or new component

Add a "Query" tab to the existing UI:
- Text input for natural language questions
- Strategy selector (Auto / Local / Global)
- Response display with:
  - Answer text (markdown rendered)
  - Source citations (clickable links to contracts/clauses)
  - Graph context visualization (highlight relevant subgraph in Cytoscape)

### 5.2 Community Explorer

Add to existing graph view:
- Color nodes by community membership
- Toggle community overlay
- Click community → show summary
- Expand/collapse community hierarchy

### 5.3 Query History

Simple list of recent queries + answers for the session (in-memory, no persistence needed initially).

---

## Phase 6: Optimization & Hardening (Week 7-8)

### 6.1 Caching
- Cache embeddings (avoid re-embedding unchanged entities)
- Cache community summaries (invalidate on graph change)
- Cache frequent query results (TTL-based)

### 6.2 Performance
- Batch embedding calls (reduce API round-trips)
- Async Neo4j queries
- Connection pooling for Neo4j driver
- Limit graph traversal depth to prevent runaway queries

### 6.3 Evaluation
- Create a test set of 20-30 questions with expected answers
- Measure: answer relevance, factual grounding, citation accuracy
- Compare local vs global vs hybrid strategies
- Tune: embedding model, traversal depth, context window size, community levels

### 6.4 Error Handling
- Graceful fallback if Neo4j is unavailable (existing SQLite features still work)
- Token limit management for large community summaries in global search
- Timeout on long-running Cypher queries

---

## File Summary

| File | Phase | Purpose |
|------|-------|---------|
| `backend/app/neo4j_client.py` | 1 | Neo4j connection manager |
| `backend/app/graph_schema.py` | 1 | Cypher schema definitions & indexes |
| `backend/app/graph_sync.py` | 1-2 | SQLite ↔ Neo4j sync + embedding storage |
| `backend/app/embeddings.py` | 2 | Embedding service (OpenAI/Voyage) |
| `backend/app/communities.py` | 3 | Leiden detection + LLM summarization |
| `backend/app/query_engine.py` | 4 | Query classification + answer synthesis |
| `backend/app/retrievers.py` | 4 | Local, global, hybrid retrieval strategies |
| `scripts/migrate_to_neo4j.py` | 1 | One-time data migration |
| `frontend/src/QueryView.jsx` | 5 | Chat/query UI component |

---

## Dependencies to Add

```
# requirements.txt additions
neo4j>=5.0
neo4j-graphrag-python>=1.0
openai>=1.0          # for embeddings (or voyageai)
graspologic>=3.0     # if not using Neo4j GDS for Leiden
numpy>=1.24
```

---

## Estimated Effort

| Phase | Description | Effort |
|-------|-------------|--------|
| 1 | Neo4j setup & sync | Medium |
| 2 | Embedding pipeline | Low-Medium |
| 3 | Community detection | Medium |
| 4 | Query engine | High (core logic) |
| 5 | Frontend integration | Medium |
| 6 | Optimization | Low-Medium |

**Critical path:** Phase 1 → 2 → 3 → 4 (sequential). Phase 5 can start in parallel with Phase 4. Phase 6 is iterative.

---

## Quick Start (MVP)

For a minimal viable GraphRAG, implement in this order:

1. **Phase 1.1-1.3** — Neo4j + sync (get the graph populated)
2. **Phase 2** — Embeddings (enable vector search)
3. **Phase 4.2 + 4.4** — Local search + answer synthesis (skip classification, default to local)
4. **Phase 4.5** — Single `/api/query` endpoint
5. **Phase 5.1** — Basic query input in frontend

This MVP gives you: paste a question → search the graph → get a grounded answer. Community detection and global search can be added incrementally after.
