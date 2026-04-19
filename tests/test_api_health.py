from fastapi.testclient import TestClient

from app.db.corpus import init_corpus
from app.db.parsed import init_parsed
from app.main import app


def test_health_and_ready() -> None:
    init_corpus()
    init_parsed()
    with TestClient(app) as client:
        r = client.get("/api/health")
        assert r.status_code == 200
        assert r.json() == {"ok": True}
        r = client.get("/api/ready")
        assert r.status_code == 200
        body = r.json()
        assert body["corpus_db"] is True
        assert body["parsed_db"] is True
        assert body["blob_store"] is True


def test_sources_endpoint() -> None:
    from scripts.seed_sources import main as seed

    seed()
    with TestClient(app) as client:
        r = client.get("/api/sources")
        assert r.status_code == 200
        keys = {s["key"] for s in r.json()}
        assert {"usc", "ecfr", "federal_register", "ny_senate", "courtlistener", "nycrr"} <= keys
