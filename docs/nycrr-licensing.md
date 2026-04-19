# NYCRR Licensing Block

## What is NYCRR?

The New York Codes, Rules and Regulations (NYCRR) is the official compilation of
all New York State agency regulations (administrative law), analogous to the federal CFR.

## Why is it blocked?

Unlike the federal CFR (freely available from ecfr.gov) or NY Consolidated Laws
(freely available via Open Legislation), NYCRR is not published in a machine-readable
format by the State. The only authoritative digital versions are:

- **Westlaw** (Thomson Reuters) — commercial license required
- **LexisNexis** — commercial license required
- **NY Register** (weekly gazette, not consolidated) — available via DEC and DOS websites
  in PDF/HTML but not as machine-readable bulk XML

The NYS Department of State maintains the NY Register at `dos.ny.gov` and publishes
individual rulemakings, but does not offer a consolidated NYCRR download.

## What to do instead

| Option | Notes |
|--------|-------|
| **NY Register (recent rules only)** | DOS publishes the NY Register weekly in PDF. Could be scraped for recent rulemakings but is not consolidated historical law. |
| **OpenElections / APA watch** | Some advocacy orgs publish NYCRR sections; coverage is incomplete. |
| **LexisNexis Academic / Institutional access** | If the project has institutional access to LexisNexis Academic, bulk export may be permissible under the license. Confirm with legal. |
| **NY State contract** | The State has contracted with both Westlaw and LexisNexis for state agency access. A formal data-sharing agreement with an agency could provide access. |
| **SPARQL-accessible alternatives** | The NYU School of Law maintains some NY regulatory content in structured form — worth investigating. |

## Current status

**Blocked indefinitely** until a licensed or government-provided bulk source becomes
available. The `NYCRRFetcher` class is registered as a stub so the source row exists
in the DB, but calling `discover()` or `fetch_one()` raises `NotImplementedError`.

Do not enable this source in the DB until a licensed access path is confirmed.
