# Triple Store Setup — Apache Jena Fuseki

This document describes how to start, configure, and load data into the Apache Jena Fuseki SPARQL endpoint used by LegalCorpusPipeline.

---

## Why Fuseki?

- **Apache-licensed** — no registration, no usage caps.
- **TDB2 backend** — on-disk RDF store with ACID transactions.
- **SPARQL 1.1** — full query and update support.
- **OWL/Turtle** — native Turtle ingestion, namespace-aware.
- **Docker image available** — `stain/jena-fuseki`.

---

## Quick Start (Docker Compose)

The `docker-compose.yml` in the project root includes a `fuseki` service.

```bash
# Start Fuseki (and the two Postgres databases) in the background:
docker compose up -d fuseki

# Verify Fuseki is ready (status 200):
curl -s -o /dev/null -w "%{http_code}" http://localhost:3030/$/ping
```

Fuseki listens on **http://localhost:3030**. The admin UI is at that same address.

Admin credentials (change in production):
- Username: `admin`
- Password: `admin` (set via `ADMIN_PASSWORD` in docker-compose.yml)

---

## Create the `normgraph` Dataset

Fuseki does not create datasets automatically. Run this once after the container starts:

```bash
curl -u admin:admin \
  -X POST http://localhost:3030/$/datasets \
  --data "dbName=normgraph&dbType=tdb2"
```

Verify:
```bash
curl -s http://localhost:3030/$/datasets | python3 -m json.tool
```

The dataset is now accessible at:
- **SPARQL Query**: `http://localhost:3030/normgraph/sparql`
- **SPARQL Update**: `http://localhost:3030/normgraph/update`
- **Graph Store** (upload): `http://localhost:3030/normgraph/data`

---

## Load the Ontology Vocabularies

The four vocabulary layers and the combined integration ontology are mounted into the container at `/staging/ontology/`.

Load them into the **default graph**:

```bash
# Load all vocabulary files in dependency order:
for ttl in ufo-l legalruleml domain uslm combined; do
  echo "Loading ${ttl}.ttl ..."
  curl -u admin:admin \
    -X POST http://localhost:3030/normgraph/data \
    --data-binary @./ontology/${ttl}.ttl \
    -H "Content-Type: text/turtle"
done
```

Or load each into its own **named graph** for cleaner provenance:

```bash
curl -u admin:admin \
  -X PUT http://localhost:3030/normgraph/data?graph=urn:normgraph:onto/ufo-l \
  --data-binary @./ontology/ufo-l.ttl \
  -H "Content-Type: text/turtle"

curl -u admin:admin \
  -X PUT http://localhost:3030/normgraph/data?graph=urn:normgraph:onto/legalruleml \
  --data-binary @./ontology/legalruleml.ttl \
  -H "Content-Type: text/turtle"

curl -u admin:admin \
  -X PUT http://localhost:3030/normgraph/data?graph=urn:normgraph:onto/domain \
  --data-binary @./ontology/domain.ttl \
  -H "Content-Type: text/turtle"

curl -u admin:admin \
  -X PUT http://localhost:3030/normgraph/data?graph=urn:normgraph:onto/uslm \
  --data-binary @./ontology/uslm.ttl \
  -H "Content-Type: text/turtle"

curl -u admin:admin \
  -X PUT http://localhost:3030/normgraph/data?graph=urn:normgraph:onto/combined \
  --data-binary @./ontology/combined.ttl \
  -H "Content-Type: text/turtle"
```

Verify the triple count:
```sparql
# Via the Fuseki web UI at http://localhost:3030 → normgraph → query:
SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }
```

---

## Load Parsed NormativeExtraction Data

Once the parser (Phase 1) produces Turtle/JSON-LD output, load it into a named graph keyed by the source provision:

```bash
# Example: load extracted triples for 42 USC § 1983
curl -u admin:admin \
  -X POST "http://localhost:3030/normgraph/data?graph=urn:uslm:statute:usc:42/1983" \
  --data-binary @./data/extractions/42-usc-1983.ttl \
  -H "Content-Type: text/turtle"
```

---

## SPARQL Endpoint

Query the store directly with `curl`:

```bash
curl -G http://localhost:3030/normgraph/sparql \
  --data-urlencode "query=SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10"
```

Or use the Fuseki web UI at http://localhost:3030, navigate to the `normgraph` dataset, and use the SPARQL editor.

See `docs/competency-questions.md` for the full set of analytical queries.

---

## Persistent Data

The `fuseki_data` Docker volume persists all datasets across container restarts. The volume is defined in `docker-compose.yml`.

To wipe and start fresh:
```bash
docker compose down -v   # WARNING: destroys all Fuseki data
docker compose up -d fuseki
# Then re-create dataset and re-load ontologies.
```

---

## TDB2 Backup

For a point-in-time backup of the `normgraph` dataset:

```bash
curl -u admin:admin \
  -X POST http://localhost:3030/$/backup/normgraph
# Backup appears in the container at /fuseki/backups/
```

---

## Environment Variables

| Variable         | Default  | Description                          |
|-----------------|----------|--------------------------------------|
| `ADMIN_PASSWORD` | `admin`  | Fuseki admin password                |
| `JVM_ARGS`       | `-Xmx2g` | JVM heap for the Fuseki process      |

Set `ADMIN_PASSWORD` via an `.env` file or Docker secrets in production.

---

## Python Client (rdflib + SPARQLWrapper)

For integration in the pipeline (Phase 2+), use `rdflib`'s SPARQL connector:

```python
from rdflib import ConjunctiveGraph
from rdflib.plugins.stores.sparqlstore import SPARQLUpdateStore

store = SPARQLUpdateStore(
    query_endpoint="http://localhost:3030/normgraph/sparql",
    update_endpoint="http://localhost:3030/normgraph/update",
)
g = ConjunctiveGraph(store=store)
```

Or use `SPARQLWrapper` directly for fire-and-forget updates.
