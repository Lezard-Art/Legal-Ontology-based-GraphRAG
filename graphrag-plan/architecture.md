# GraphRAG Architecture Plan

## Contract Ontology GraphRAG System

### Overview

A Graph-based Retrieval Augmented Generation (GraphRAG) system built on top of the Contract Ontology Database. This system enables natural language querying over contract knowledge graphs, leveraging the structured ontological relationships (UFO-L, Symboleo, Hohfeld) already captured by the existing system.

### Why GraphRAG over Standard RAG?

| Aspect | Standard RAG | GraphRAG (Ours) |
|--------|-------------|-----------------|
| Data structure | Flat text chunks + embeddings | Ontological graph with typed entities & relationships |
| Retrieval | Vector similarity on text | Graph traversal + community summaries + vector search |
| Multi-hop reasoning | Poor (single-chunk retrieval) | Strong (traverse Party → Role → Obligation → Constraint chains) |
| Legal relationship awareness | None (treats text as bags of words) | Explicit (Hohfeld correlatives, role pairs, temporal constraints) |
| Cross-contract analysis | Requires all contracts in context | Community detection groups related patterns across contracts |

Our existing ontology (Parties, Roles, Obligations, Powers, Constraints, Clauses) already provides the **entity extraction** that most GraphRAG systems must build from scratch. This is a significant advantage.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interface Layer                     │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │ Chat / Query  │  │ Graph Explorer│  │ Existing Contract │  │
│  │   Interface   │  │  (Cytoscape)  │  │   Management UI   │  │
│  └──────┬───────┘  └──────┬───────┘  └───────────────────┘  │
└─────────┼─────────────────┼──────────────────────────────────┘
          │                 │
┌─────────▼─────────────────▼──────────────────────────────────┐
│                     API Gateway (FastAPI)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐   │
│  │ /api/query    │  │ /api/search   │  │ Existing endpoints │   │
│  │ (NL queries)  │  │ (hybrid)      │  │ (CRUD, parse, etc) │   │
│  └──────┬───────┘  └──────┬───────┘  └───────────────────┘   │
└─────────┼─────────────────┼──────────────────────────────────┘
          │                 │
┌─────────▼─────────────────▼──────────────────────────────────┐
│                    Query Processing Layer                      │
│                                                               │
│  ┌─────────────────┐  ┌────────────────┐  ┌──────────────┐   │
│  │ Query Classifier │→│ Query Decomposer│→│ Query Router  │   │
│  │ (local/global/   │  │ (break complex  │  │ (route to    │   │
│  │  hybrid)         │  │  into sub-      │  │  retrieval   │   │
│  │                  │  │  queries)       │  │  strategy)   │   │
│  └─────────────────┘  └────────────────┘  └──────┬───────┘   │
│                                                   │           │
│  ┌────────────────────────────────────────────────▼────────┐  │
│  │                  Retrieval Strategies                    │  │
│  │  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │  │
│  │  │ Local Search │  │ Global Search │  │ Hybrid Search │  │  │
│  │  │ (entity →   │  │ (community   │  │ (local +      │  │  │
│  │  │  neighbors)  │  │  summaries)  │  │  global)      │  │  │
│  │  └─────────────┘  └──────────────┘  └───────────────┘  │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │              Answer Synthesis (Claude LLM)               │  │
│  │  Retrieved context → Grounded, cited answer              │  │
│  └─────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────┘
          │                 │
┌─────────▼─────────────────▼──────────────────────────────────┐
│                    Knowledge Graph Layer                       │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐   │
│  │                    Neo4j Graph Database                  │   │
│  │                                                         │   │
│  │  Nodes:                    Edges:                       │   │
│  │  • Contract                • HAS_PARTY                  │   │
│  │  • Party                   • PLAYS_ROLE                 │   │
│  │  • Role                    • HAS_OBLIGATION             │   │
│  │  • Obligation              • HAS_POWER                  │   │
│  │  • Power                   • DEBTOR_OF / CREDITOR_OF    │   │
│  │  • Constraint              • CONSTRAINED_BY             │   │
│  │  • Clause                  • TAGGED_AS                  │   │
│  │  • Asset                   • INVOLVES_ASSET             │   │
│  │  • LegalPosition           • CORRELATIVE_OF (Hohfeld)   │   │
│  │  • Community (generated)   • MEMBER_OF                  │   │
│  │                                                         │   │
│  │  Indexes:                                               │   │
│  │  • Vector index on node embeddings (for similarity)     │   │
│  │  • Full-text index on clause text                       │   │
│  │  • Composite index on entity types + properties         │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐   │
│  │              Community Detection Layer                   │   │
│  │  • Leiden algorithm on contract subgraphs               │   │
│  │  • Hierarchical communities (contract → clause-group    │   │
│  │    → obligation-cluster)                                │   │
│  │  • LLM-generated community summaries                    │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐   │
│  │              Embedding Store                             │   │
│  │  • Entity description embeddings (via Voyage/OpenAI)    │   │
│  │  • Clause text embeddings                               │   │
│  │  • Community summary embeddings                         │   │
│  └────────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. Neo4j Graph Database (replaces SQLite for graph layer)

The existing SQLite database handles relational storage well, but graph traversal queries are where Neo4j excels. **Both databases coexist**: SQLite remains the source of truth for CRUD operations; Neo4j serves as the graph query layer, synced on contract creation/update.

**Graph Schema (Cypher):**
```cypher
// Core ontology nodes
(:Contract {id, name, governing_law, jurisdiction, effective_date, end_date})
(:Party {id, name, description})
(:Role {id, label, description})
(:Obligation {id, name, description, trigger, surviving})
(:Power {id, name, description, trigger})
(:Constraint {id, constraint_type, description, expression})
(:Clause {id, clause_number, text, ontology_tag})
(:Asset {id, name, description, asset_type})
(:LegalPosition {id, position_type, holder_role, counter_role})

// GraphRAG-specific nodes
(:Community {id, level, summary, summary_embedding})

// Relationships
(:Contract)-[:HAS_PARTY]->(:Party)
(:Party)-[:PLAYS_ROLE]->(:Role)
(:Contract)-[:HAS_OBLIGATION]->(:Obligation)
(:Obligation)-[:DEBTOR]->(:Role)
(:Obligation)-[:CREDITOR]->(:Role)
(:Contract)-[:HAS_POWER]->(:Power)
(:Contract)-[:HAS_CLAUSE]->(:Clause)
(:Obligation)-[:CONSTRAINED_BY]->(:Constraint)
(:Contract)-[:INVOLVES_ASSET]->(:Asset)
(:LegalPosition)-[:CORRELATIVE_OF]->(:LegalPosition)

// Community membership
(:Entity)-[:MEMBER_OF]->(:Community)
(:Community)-[:PARENT_OF]->(:Community)
```

### 2. Query Classification & Routing

| Query Type | Example | Strategy |
|-----------|---------|----------|
| **Local** (entity-specific) | "What are AgriCorp's delivery obligations?" | Entity lookup → neighbor traversal → context assembly |
| **Global** (thematic/aggregate) | "What common obligation patterns exist across all contracts?" | Community summaries → map-reduce synthesis |
| **Hybrid** | "How do indemnification clauses compare across tech contracts?" | Entity search + community context |
| **Cypher-direct** | "Find all contracts where the buyer has a termination power" | LLM generates Cypher → execute → format |

### 3. Local Search Flow

```
User Query
    │
    ▼
Embed query text
    │
    ▼
Find nearest entities (vector similarity on Neo4j)
    │
    ▼
Graph traversal (1-3 hops from matched entities)
    │
    ▼
Collect: entity properties + relationships + clause text + community summary
    │
    ▼
Assemble context window (prioritize by relevance score)
    │
    ▼
LLM generates grounded answer with citations
```

### 4. Global Search Flow

```
User Query
    │
    ▼
Retrieve all community summaries at target level
    │
    ▼
MAP: Query each community independently (parallel)
    │
    ▼
REDUCE: Roll up community answers into final synthesis
    │
    ▼
LLM generates comprehensive answer
```

### 5. Community Detection Pipeline

Run after contract ingestion or on-demand:

1. **Export subgraph** from Neo4j (all entity nodes + relationships)
2. **Run Leiden algorithm** (via `graspologic` or Neo4j GDS)
3. **Assign community IDs** at multiple hierarchy levels
4. **Generate summaries** for each community using Claude
5. **Embed summaries** for similarity search
6. **Store back** in Neo4j as `(:Community)` nodes

### 6. Embedding Strategy

| Content | Embedding Model | Storage |
|---------|----------------|---------|
| Entity descriptions | `voyage-3` or `text-embedding-3-small` | Neo4j vector index |
| Clause text | Same | Neo4j vector index |
| Community summaries | Same | Neo4j vector index |
| User queries | Same (at query time) | In-memory |

---

## Data Flow: Contract Ingestion → Graph

```
Upload/Paste Contract
        │
        ▼
  Claude LLM Parse (existing)
        │
        ▼
  Save to SQLite (existing)
        │
        ▼
  ┌─────────────────────────┐
  │  NEW: Sync to Neo4j     │
  │  • Create entity nodes  │
  │  • Create relationships │
  │  • Generate embeddings  │
  │  • Update communities   │
  └─────────────────────────┘
```

---

## Technology Choices

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Graph DB | **Neo4j Community Edition** | Native graph, Cypher query language, vector index support, GDS for community detection |
| Embeddings | **Voyage AI** or **OpenAI text-embedding-3-small** | High quality, affordable, good for legal text |
| Community detection | **Neo4j GDS Leiden** or **graspologic** (Python) | Leiden is standard for GraphRAG; GDS runs in-database |
| LLM | **Claude 3.5 Sonnet** (existing) | Already integrated; excellent at structured extraction and synthesis |
| Python graph lib | **neo4j Python driver** + **neo4j-graphrag-python** | Official Neo4j GraphRAG toolkit |

---

## API Design (New Endpoints)

```
POST /api/query                    # Natural language query over the graph
  Body: { "question": "...", "strategy": "auto|local|global|hybrid" }
  Response: { "answer": "...", "sources": [...], "graph_context": {...} }

POST /api/query/cypher             # Direct Cypher query (advanced users)
  Body: { "question": "..." }
  Response: { "cypher": "...", "results": [...] }

GET  /api/graph/communities        # List all communities with summaries
GET  /api/graph/communities/{id}   # Community detail with members

POST /api/graph/rebuild            # Trigger full graph rebuild from SQLite
POST /api/graph/reindex            # Regenerate embeddings + communities

GET  /api/graph/search             # Hybrid search (vector + graph)
  Params: q, entity_type, limit
```

---

## Security Considerations

- **Cypher injection prevention**: Use parameterized queries only; never interpolate user input into Cypher strings
- **LLM-generated Cypher**: Validate against allowlist of patterns; read-only transaction mode
- **API key management**: Neo4j credentials in `.env`, never committed
- **Rate limiting**: On `/api/query` to prevent LLM cost abuse
