from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.db.corpus import CorpusSession
from app.models.corpus import Document, FetchRun, ParseQueue, Source

router = APIRouter(tags=["dashboard"])


_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><title>Legal Corpus Pipeline</title>
<style>body{font-family:system-ui,sans-serif;margin:2rem;max-width:960px}
h1{color:#1F3864} table{width:100%;border-collapse:collapse;margin-bottom:1.5rem}
td,th{padding:.4rem .6rem;border:1px solid #ddd;text-align:left;font-size:.9rem}
th{background:#D5E8F0}</style></head><body>
<h1>Legal Corpus Pipeline</h1>
<p id="ts"></p>
<h2>Sources</h2><div id="sources"></div>
<h2>Parse queue</h2><div id="queue"></div>
<h2>Recent fetch runs</h2><div id="runs"></div>
<script>
async function j(u){const r=await fetch(u);return r.json()}
function tbl(rows,cols){if(!rows.length)return'<p><em>none</em></p>';
let h='<table><tr>'+cols.map(c=>`<th>${c}</th>`).join('')+'</tr>';
for(const r of rows){h+='<tr>'+cols.map(c=>`<td>${r[c]??''}</td>`).join('')+'</tr>'}return h+'</table>'}
async function refresh(){
  document.getElementById('ts').textContent='updated '+new Date().toLocaleTimeString();
  const s=await j('/api/dashboard-data');
  document.getElementById('sources').innerHTML=tbl(s.sources,['key','jurisdiction','enabled','documents','licensing_status']);
  document.getElementById('queue').innerHTML=tbl(s.queue_summary,['status','count']);
  document.getElementById('runs').innerHTML=tbl(s.recent_runs,['source_key','status','started_at','finished_at']);
}
refresh(); setInterval(refresh,5000);
</script></body></html>"""


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard() -> str:
    return _HTML


@router.get("/api/dashboard-data")
def dashboard_data() -> dict[str, object]:
    with CorpusSession() as db:
        sources = db.query(Source).all()
        src_rows = []
        for s in sources:
            doc_count = db.query(Document).filter_by(source_id=s.id).count()
            src_rows.append(
                {
                    "key": s.key,
                    "jurisdiction": s.jurisdiction,
                    "enabled": s.enabled,
                    "documents": doc_count,
                    "licensing_status": s.licensing_status,
                }
            )
        queue = db.query(ParseQueue).all()
        summary: dict[str, int] = {}
        for q in queue:
            summary[q.status] = summary.get(q.status, 0) + 1
        runs = (
            db.query(FetchRun).order_by(FetchRun.started_at.desc()).limit(20).all()
        )
        src_by_id = {s.id: s.key for s in sources}
        run_rows = [
            {
                "source_key": src_by_id.get(r.source_id, "?"),
                "status": r.status,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            }
            for r in runs
        ]
        return {
            "sources": src_rows,
            "queue_summary": [{"status": k, "count": v} for k, v in summary.items()],
            "recent_runs": run_rows,
        }
