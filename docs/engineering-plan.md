# Engineering Plan: Data and Parsing Pipeline
## US Law Normative Knowledge Graph

**Project**: Building a normative knowledge graph of US federal law + New York state pilot
**Status**: Planning Phase
**Last Updated**: 2026-04-02

---

## Overview

This document covers the SOFTWARE ENGINEERING of the knowledge graph system: how to acquire data, prepare context, and extract normative content using AI agents and APIs. This is NOT about ontology design (covered separately) — it's about implementation.

**Technology Stack**:
- **Data Storage**: RDF/OWL triple store (Apache Jena Fuseki or GraphDB Community)
- **Application Database**: PostgreSQL (job tracking, human review queue, caching)
- **APIs**: Anthropic Claude (Opus 4.6, Sonnet, Haiku), various government APIs
- **Language**: Python 3.10+
- **Triple Store**: Apache Jena Fuseki or GraphDB Community Edition

---

## Part A: Data Gathering Agents

### Architecture Overview

All data gathering agents will inherit from a common base class to ensure consistent error handling, rate limiting, and logging.

**Base Module Structure**:
```
src/
  agents/
    __init__.py
    base.py                    # BaseDataAgent class
    federal/
      __init__.py
      uscode.py               # US Code agent
      cfr.py                  # CFR agent
      executive_orders.py     # Executive Orders agent
      bills_and_statutes.py   # Congressional Bills/Public Laws agent
      federal_register.py     # Federal Register agent
      crs_reports.py          # CRS Reports agent
      court_opinions.py       # Federal/Supreme Court opinions agent
    ny_state/
      __init__.py
      ny_consolidated_laws.py # NY statutes agent
      nyc_admin_code.py       # NYC Administrative Code agent
      ny_regulations.py       # NY regulations (NYCRR) agent
      ny_court_opinions.py    # NY court opinions agent
    context_gathering/
      __init__.py
      definitions.py          # Definitions resolution
      cross_references.py     # Cross-reference resolution
      legislative_history.py  # Legislative history agent
      court_interpretations.py # Court interpretation context
      academic_databases.py   # Academic database cataloging
      entity_resolution.py    # Entity consolidation
```

### Base Agent Class

```python
# src/agents/base.py

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
import logging
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
import time
import requests

class BaseDataAgent(ABC):
    """
    Base class for all data gathering agents.
    Provides: rate limiting, retry logic, storage, logging, checkpointing.
    """

    def __init__(self, source_name: str, storage_root: Path, config: Dict):
        self.source_name = source_name
        self.storage_root = storage_root / source_name
        self.storage_root.mkdir(parents=True, exist_ok=True)

        self.config = config
        self.rate_limit_delay = config.get('rate_limit_delay_seconds', 0.5)
        self.max_retries = config.get('max_retries', 3)
        self.retry_backoff = config.get('retry_backoff_factor', 2)

        # Set up logging
        self.logger = logging.getLogger(f"agent.{source_name}")
        log_file = self.storage_root / f"{source_name}_agent.log"
        handler = logging.FileHandler(log_file)
        handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

        # State tracking
        self.checkpoint_file = self.storage_root / "checkpoint.json"
        self.checkpoint = self._load_checkpoint()

    def _load_checkpoint(self) -> Dict:
        """Load checkpoint to resume from previous run."""
        if self.checkpoint_file.exists():
            with open(self.checkpoint_file, 'r') as f:
                return json.load(f)
        return {'last_successful_run': None, 'processed_items': []}

    def _save_checkpoint(self):
        """Save checkpoint to allow resumption."""
        with open(self.checkpoint_file, 'w') as f:
            json.dump(self.checkpoint, f, indent=2, default=str)

    def fetch_with_retry(self, url: str, method: str = 'GET',
                        headers: Optional[Dict] = None,
                        params: Optional[Dict] = None,
                        json_body: Optional[Dict] = None,
                        timeout: int = 30) -> Optional[requests.Response]:
        """
        Fetch URL with exponential backoff retry logic.
        Returns Response object or None if all retries exhausted.
        """
        attempt = 0
        last_exception = None

        while attempt < self.max_retries:
            try:
                time.sleep(self.rate_limit_delay)  # Rate limiting

                if method == 'GET':
                    response = requests.get(url, headers=headers, params=params,
                                          timeout=timeout)
                elif method == 'POST':
                    response = requests.post(url, headers=headers, json=json_body,
                                           timeout=timeout)
                else:
                    raise ValueError(f"Unsupported method: {method}")

                response.raise_for_status()
                self.logger.info(f"Successfully fetched {url}")
                return response

            except (requests.ConnectionError, requests.Timeout,
                   requests.HTTPError) as e:
                last_exception = e
                attempt += 1
                if attempt < self.max_retries:
                    wait_time = self.rate_limit_delay * (self.retry_backoff ** attempt)
                    self.logger.warning(
                        f"Attempt {attempt} failed for {url}. Retrying in {wait_time}s: {e}"
                    )
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"All retries exhausted for {url}: {e}")

        return None

    @abstractmethod
    def gather(self, incremental: bool = True) -> Dict[str, Any]:
        """
        Main entry point for data gathering.
        Args:
            incremental: If True, only fetch new/changed items since last run
        Returns:
            Dict with summary: {'items_fetched': N, 'items_new': N, 'errors': [...]}
        """
        pass

    def save_raw_content(self, content: str, path: Path,
                        metadata: Optional[Dict] = None):
        """Save raw content to file with optional metadata."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

        if metadata:
            meta_path = path.with_suffix(path.suffix + '.metadata.json')
            with open(meta_path, 'w') as f:
                json.dump(metadata, f, indent=2, default=str)

        self.logger.info(f"Saved content to {path}")
```

### Individual Data Agents

#### 1. US Code Agent (USLM XML)

**Data Source**: uscode.house.gov/download/download.shtml
**Format**: XML (USLM schema)
**Volume**: ~54 titles, ~100,000+ sections
**Update Frequency**: Annual bulk releases + periodic updates

```python
# src/agents/federal/uscode.py

from base import BaseDataAgent
from pathlib import Path
from typing import Dict, Any, List
import xml.etree.ElementTree as ET
import zipfile
import io

class USCodeAgent(BaseDataAgent):
    """
    Fetches US Code (USC) from House.gov in USLM XML format.
    Bulk downloads all 54 titles, organized by title number.
    """

    BASE_URL = "https://uscode.house.gov/download/download.shtml"
    BULK_DOWNLOAD_BASE = "https://uscode.house.gov/download/releasepoints/"

    def __init__(self, storage_root: Path, config: Dict):
        super().__init__('uscode', storage_root, config)
        self.api_key = None  # No key required

    def gather(self, incremental: bool = True) -> Dict[str, Any]:
        """
        Download all USC titles in XML format.
        Storage structure: storage_root/title_001/...xml files
        """
        self.logger.info("Starting US Code data gathering")
        summary = {'items_fetched': 0, 'items_new': 0, 'errors': []}

        # List of all 54 titles (simplified; full version needs all 54)
        titles = [f"{i:03d}" for i in range(1, 55)]

        for title in titles:
            try:
                # Construct download URL for each title
                download_url = f"{self.BULK_DOWNLOAD_BASE}2024-01-01/usc_{title}.zip"

                response = self.fetch_with_retry(download_url)
                if not response:
                    summary['errors'].append(f"Failed to fetch title {title}")
                    continue

                # Extract ZIP and save XML files
                with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
                    title_dir = self.storage_root / f"title_{title}"
                    title_dir.mkdir(parents=True, exist_ok=True)

                    for file_info in zip_ref.filelist:
                        content = zip_ref.read(file_info.filename).decode('utf-8')
                        output_path = title_dir / file_info.filename
                        self.save_raw_content(content, output_path, {
                            'source': 'uscode.house.gov',
                            'title': title,
                            'format': 'USLM XML'
                        })
                        summary['items_new'] += 1

                summary['items_fetched'] += 1

            except Exception as e:
                self.logger.error(f"Error processing title {title}: {e}")
                summary['errors'].append(f"Title {title}: {str(e)}")

        # Update checkpoint
        self.checkpoint['last_successful_run'] = datetime.now().isoformat()
        self._save_checkpoint()

        self.logger.info(f"Completed US Code gathering: {summary}")
        return summary
```

**Storage Structure**:
```
storage_root/uscode/
  title_001/
    usc_001.xml
    usc_001.xml.metadata.json
  title_002/
  ...
  title_054/
  checkpoint.json
  uscode_agent.log
```

---

#### 2. CFR Agent (Code of Federal Regulations)

**Data Sources**:
- Bulk: govinfo.gov/bulkdata/CFR (annual releases)
- Daily updates: ecfr.gov API

```python
# src/agents/federal/cfr.py

from base import BaseDataAgent
from pathlib import Path
from typing import Dict, Any
import json
from datetime import datetime, timedelta

class CFRAgent(BaseDataAgent):
    """
    Fetches Code of Federal Regulations (CFR) from govinfo.gov bulk data
    and ecfr.gov API for daily updates.
    """

    GOVINFO_BULK_BASE = "https://www.govinfo.gov/bulkdata/CFR"
    ECFR_API_BASE = "https://www.ecfr.gov/api/versioner/v1"

    def __init__(self, storage_root: Path, config: Dict):
        super().__init__('cfr', storage_root, config)

    def gather(self, incremental: bool = True) -> Dict[str, Any]:
        """
        Fetch CFR in two phases:
        1. Bulk XML from govinfo.gov (annual)
        2. Daily updates from ecfr.gov API
        """
        self.logger.info("Starting CFR data gathering")
        summary = {'items_fetched': 0, 'items_new': 0, 'errors': []}

        # Phase 1: Bulk download (typically run once or quarterly)
        if not incremental or self._should_refresh_bulk():
            summary.update(self._fetch_bulk_cfr())

        # Phase 2: Daily updates from eCFR API
        summary_updates = self._fetch_daily_updates()
        summary['items_fetched'] += summary_updates['items_fetched']
        summary['items_new'] += summary_updates['items_new']
        summary['errors'].extend(summary_updates['errors'])

        self.checkpoint['last_successful_run'] = datetime.now().isoformat()
        self._save_checkpoint()

        return summary

    def _fetch_bulk_cfr(self) -> Dict[str, Any]:
        """Fetch complete CFR from govinfo.gov bulk data."""
        summary = {'items_fetched': 0, 'items_new': 0, 'errors': []}

        # List all 50 CFR titles
        for title in range(1, 51):
            try:
                # Download URL for annual release (update year as needed)
                bulk_url = f"{self.GOVINFO_BULK_BASE}/2024/CFR-2024-title-{title:02d}.zip"

                response = self.fetch_with_retry(bulk_url)
                if response:
                    # Extract and save (similar to USC agent)
                    summary['items_fetched'] += 1
                    summary['items_new'] += 1

            except Exception as e:
                self.logger.error(f"Error fetching CFR title {title}: {e}")
                summary['errors'].append(f"Title {title}: {str(e)}")

        return summary

    def _fetch_daily_updates(self) -> Dict[str, Any]:
        """Fetch daily updates from eCFR API."""
        summary = {'items_fetched': 0, 'items_new': 0, 'errors': []}

        # Get last update date from checkpoint
        last_update = self.checkpoint.get('last_ecfr_update')
        if last_update:
            last_update_date = datetime.fromisoformat(last_update)
        else:
            last_update_date = datetime.now() - timedelta(days=7)

        # Query eCFR API for changes since last update
        # API endpoint: GET /versions?date=YYYY-MM-DD

        update_date = last_update_date
        while update_date <= datetime.now():
            try:
                url = f"{self.ECFR_API_BASE}/versions?date={update_date.date()}"
                response = self.fetch_with_retry(url)

                if response:
                    versions = response.json().get('versions', [])
                    for version in versions:
                        # Save version info
                        version_path = self.storage_root / f"ecfr_version_{version['id']}.json"
                        self.save_raw_content(
                            json.dumps(version, indent=2),
                            version_path,
                            {'source': 'ecfr.gov', 'type': 'version_info'}
                        )
                        summary['items_new'] += 1

                    summary['items_fetched'] += 1

            except Exception as e:
                self.logger.error(f"Error fetching eCFR updates for {update_date}: {e}")
                summary['errors'].append(str(e))

            update_date += timedelta(days=1)

        self.checkpoint['last_ecfr_update'] = datetime.now().isoformat()
        return summary

    def _should_refresh_bulk(self) -> bool:
        """Check if bulk CFR should be refreshed (e.g., yearly)."""
        last_run = self.checkpoint.get('last_bulk_cfr_run')
        if not last_run:
            return True

        last_run_date = datetime.fromisoformat(last_run)
        return (datetime.now() - last_run_date).days > 365
```

---

#### 3. Executive Orders Agent

**Data Source**: Federal Register API (federalregister.gov/developers)
**Format**: JSON
**No API key required** (public data)
**Rate limit**: 10 req/sec recommended

```python
# src/agents/federal/executive_orders.py

from base import BaseDataAgent
from pathlib import Path
from typing import Dict, Any
import json
from datetime import datetime, timedelta

class ExecutiveOrdersAgent(BaseDataAgent):
    """
    Fetches Executive Orders from Federal Register API.
    Includes presidential executive orders and memoranda.
    """

    API_BASE = "https://api.federalregister.gov/v1"

    def __init__(self, storage_root: Path, config: Dict):
        super().__init__('executive_orders', storage_root, config)
        self.rate_limit_delay = 0.1  # 10 req/sec = 0.1s per request

    def gather(self, incremental: bool = True) -> Dict[str, Any]:
        """
        Fetch executive orders from Federal Register.
        Uses pagination to handle large result sets.
        """
        self.logger.info("Starting Executive Orders data gathering")
        summary = {'items_fetched': 0, 'items_new': 0, 'errors': []}

        # Query parameters
        params = {
            'conditions[type]': 'EXECUTIVE_ORDER',
            'order': '-publication_date',
            'per_page': 100
        }

        # If incremental, fetch only since last update
        if incremental and self.checkpoint.get('last_successful_run'):
            last_run = datetime.fromisoformat(self.checkpoint['last_successful_run'])
            params['conditions[publication_date][gte]'] = last_run.date().isoformat()

        page = 1
        while True:
            params['page'] = page

            try:
                url = f"{self.API_BASE}/documents"
                response = self.fetch_with_retry(url, params=params)

                if not response:
                    summary['errors'].append(f"Failed to fetch page {page}")
                    break

                data = response.json()
                results = data.get('results', [])

                if not results:
                    break  # No more results

                for eo in results:
                    eo_num = eo.get('executive_order_number', 'unknown')
                    eo_date = eo.get('publication_date', 'unknown')

                    eo_path = self.storage_root / f"eo_{eo_num}_{eo_date}.json"
                    self.save_raw_content(
                        json.dumps(eo, indent=2),
                        eo_path,
                        {
                            'source': 'federalregister.gov',
                            'type': 'executive_order',
                            'order_number': eo_num
                        }
                    )

                    if eo_num not in self.checkpoint.get('processed_items', []):
                        summary['items_new'] += 1
                        self.checkpoint['processed_items'].append(eo_num)

                    summary['items_fetched'] += 1

                # Check for more pages
                total_pages = data.get('total_pages', 1)
                if page >= total_pages:
                    break

                page += 1

            except Exception as e:
                self.logger.error(f"Error fetching page {page}: {e}")
                summary['errors'].append(str(e))
                break

        self.checkpoint['last_successful_run'] = datetime.now().isoformat()
        self._save_checkpoint()

        self.logger.info(f"Completed Executive Orders gathering: {summary}")
        return summary
```

---

#### 4. Bills & Public Laws Agent

**Data Sources**:
- govinfo.gov bulk data (BILLS + USLM XML for enacted laws)
- Congress.gov API (bills/statuses, requires api.data.gov key)

```python
# src/agents/federal/bills_and_statutes.py

from base import BaseDataAgent
from pathlib import Path
from typing import Dict, Any
import json
from datetime import datetime

class BillsAndStatutesAgent(BaseDataAgent):
    """
    Fetches Congressional bills, their status, and enacted Public Laws.
    Uses Congress.gov API for bill tracking + govinfo for full text.
    """

    CONGRESS_API_BASE = "https://api.congress.gov/v3"

    def __init__(self, storage_root: Path, config: Dict):
        super().__init__('bills_and_statutes', storage_root, config)
        self.api_key = config.get('congress_api_key')  # Requires key from api.data.gov
        if not self.api_key:
            self.logger.warning("Congress.gov API key not found. Bill tracking will be limited.")

    def gather(self, incremental: bool = True) -> Dict[str, Any]:
        """
        Fetch bills and public laws.
        Focus on enacted bills (public laws) since those are normative.
        """
        self.logger.info("Starting Bills & Public Laws data gathering")
        summary = {'items_fetched': 0, 'items_new': 0, 'errors': []}

        # Phase 1: Enacted bills (public laws)
        summary_laws = self._fetch_public_laws(incremental)
        summary['items_fetched'] += summary_laws['items_fetched']
        summary['items_new'] += summary_laws['items_new']
        summary['errors'].extend(summary_laws['errors'])

        # Phase 2: Recent bill statuses (for understanding enactment pipeline)
        if self.api_key:
            summary_bills = self._fetch_bill_statuses(incremental)
            summary['items_fetched'] += summary_bills['items_fetched']
            summary['items_new'] += summary_bills['items_new']
            summary['errors'].extend(summary_bills['errors'])

        self.checkpoint['last_successful_run'] = datetime.now().isoformat()
        self._save_checkpoint()

        return summary

    def _fetch_public_laws(self, incremental: bool) -> Dict[str, Any]:
        """Fetch enacted public laws from govinfo bulk data."""
        summary = {'items_fetched': 0, 'items_new': 0, 'errors': []}

        # Public laws from recent Congresses (e.g., 118th, 117th)
        for congress_num in range(118, 110, -1):  # Last 8 Congresses
            try:
                # govinfo bulk data URL pattern
                bulk_url = f"https://www.govinfo.gov/bulkdata/BILLS/{congress_num}x"

                # Would need to iterate through bill types (hr, s, hjres, sjres, etc.)
                # and download USLM XML for enacted bills

                summary['items_fetched'] += 1  # Placeholder

            except Exception as e:
                self.logger.error(f"Error fetching Congress {congress_num}: {e}")
                summary['errors'].append(str(e))

        return summary

    def _fetch_bill_statuses(self, incremental: bool) -> Dict[str, Any]:
        """Fetch bill tracking data from Congress.gov API."""
        summary = {'items_fetched': 0, 'items_new': 0, 'errors': []}

        if not self.api_key:
            return summary

        # Get current Congress number (119th in 2025)
        current_congress = 119

        try:
            # Query bills in current congress
            url = f"{self.CONGRESS_API_BASE}/bill/{current_congress}"
            headers = {'X-API-Key': self.api_key}
            params = {'limit': 100}

            page = 1
            while True:
                params['offset'] = (page - 1) * 100
                response = self.fetch_with_retry(url, headers=headers, params=params)

                if not response:
                    break

                bills = response.json().get('bills', [])
                if not bills:
                    break

                for bill in bills:
                    bill_num = bill.get('number')
                    bill_type = bill.get('type')

                    bill_path = self.storage_root / f"bill_{bill_type}{bill_num}.json"
                    self.save_raw_content(
                        json.dumps(bill, indent=2),
                        bill_path,
                        {'source': 'congress.gov', 'type': 'bill', 'congress': current_congress}
                    )
                    summary['items_new'] += 1

                summary['items_fetched'] += len(bills)
                page += 1

        except Exception as e:
            self.logger.error(f"Error fetching bill statuses: {e}")
            summary['errors'].append(str(e))

        return summary
```

---

#### 5. Federal Register Agent

**Data Source**: Federal Register API (federalregister.gov/developers)
**Types**: Rules, Proposed Rules, Notices, Documents
**Format**: JSON/XML

```python
# src/agents/federal/federal_register.py

from base import BaseDataAgent
from pathlib import Path
from typing import Dict, Any
import json
from datetime import datetime, timedelta

class FederalRegisterAgent(BaseDataAgent):
    """
    Fetches documents from Federal Register:
    - Final rules
    - Proposed rules
    - Notices
    - Agency documents

    Public API, no key required.
    """

    API_BASE = "https://api.federalregister.gov/v1"

    def __init__(self, storage_root: Path, config: Dict):
        super().__init__('federal_register', storage_root, config)

    def gather(self, incremental: bool = True) -> Dict[str, Any]:
        """
        Fetch Federal Register documents.
        Prioritize rules and proposed rules (these are normative).
        """
        self.logger.info("Starting Federal Register data gathering")
        summary = {'items_fetched': 0, 'items_new': 0, 'errors': []}

        # Document types to prioritize
        doc_types = ['RULE', 'PROPOSED_RULE', 'NOTICE']

        for doc_type in doc_types:
            summary_docs = self._fetch_documents_by_type(doc_type, incremental)
            summary['items_fetched'] += summary_docs['items_fetched']
            summary['items_new'] += summary_docs['items_new']
            summary['errors'].extend(summary_docs['errors'])

        self.checkpoint['last_successful_run'] = datetime.now().isoformat()
        self._save_checkpoint()

        return summary

    def _fetch_documents_by_type(self, doc_type: str, incremental: bool) -> Dict:
        """Fetch all documents of a given type."""
        summary = {'items_fetched': 0, 'items_new': 0, 'errors': []}

        params = {
            'conditions[type]': doc_type,
            'order': '-publication_date',
            'per_page': 100
        }

        # If incremental, fetch only recent
        if incremental and self.checkpoint.get('last_successful_run'):
            last_run = datetime.fromisoformat(self.checkpoint['last_successful_run'])
            params['conditions[publication_date][gte]'] = (last_run - timedelta(days=7)).date().isoformat()

        page = 1
        while page <= 10:  # Limit to 1000 documents per type for efficiency
            params['page'] = page

            try:
                url = f"{self.API_BASE}/documents"
                response = self.fetch_with_retry(url, params=params)

                if not response:
                    break

                docs = response.json().get('results', [])
                if not docs:
                    break

                for doc in docs:
                    doc_num = doc.get('document_number', f"doc_{page}_{len(docs)}")

                    doc_path = self.storage_root / f"{doc_type}" / f"{doc_num}.json"
                    self.save_raw_content(
                        json.dumps(doc, indent=2),
                        doc_path,
                        {'source': 'federalregister.gov', 'type': doc_type}
                    )
                    summary['items_new'] += 1

                summary['items_fetched'] += len(docs)
                page += 1

            except Exception as e:
                self.logger.error(f"Error fetching {doc_type} page {page}: {e}")
                summary['errors'].append(str(e))
                break

        return summary
```

---

#### 6. CRS Reports Agent

**Data Source**: everycrsreport.com bulk download
**Format**: PDF + JSON metadata
**Volume**: ~23,000+ reports

```python
# src/agents/federal/crs_reports.py

from base import BaseDataAgent
from pathlib import Path
from typing import Dict, Any
import json
from datetime import datetime
import requests

class CRSReportsAgent(BaseDataAgent):
    """
    Fetches Congressional Research Service (CRS) reports from everycrsreport.com.
    These provide legislative analysis and interpretation of statutes.
    """

    API_BASE = "https://api.everycrsreport.com/api/reports"

    def __init__(self, storage_root: Path, config: Dict):
        super().__init__('crs_reports', storage_root, config)

    def gather(self, incremental: bool = True) -> Dict[str, Any]:
        """
        Fetch all CRS reports.
        Store as PDF + extracted metadata.
        """
        self.logger.info("Starting CRS Reports data gathering")
        summary = {'items_fetched': 0, 'items_new': 0, 'errors': []}

        try:
            # Query all reports from API
            response = self.fetch_with_retry(self.API_BASE)

            if not response:
                summary['errors'].append("Failed to fetch CRS reports index")
                return summary

            reports = response.json()

            for report in reports:
                try:
                    report_id = report.get('id')
                    report_num = report.get('report_number')

                    # Download PDF
                    pdf_url = report.get('pdf_url')
                    if pdf_url:
                        pdf_response = self.fetch_with_retry(pdf_url)
                        if pdf_response:
                            pdf_path = self.storage_root / f"reports" / f"{report_num}.pdf"
                            pdf_path.parent.mkdir(parents=True, exist_ok=True)
                            with open(pdf_path, 'wb') as f:
                                f.write(pdf_response.content)

                    # Save metadata
                    meta_path = self.storage_root / f"reports" / f"{report_num}.metadata.json"
                    self.save_raw_content(
                        json.dumps(report, indent=2),
                        meta_path,
                        {'source': 'everycrsreport.com', 'type': 'crs_report'}
                    )

                    summary['items_new'] += 1

                except Exception as e:
                    self.logger.error(f"Error processing report {report_num}: {e}")
                    summary['errors'].append(str(e))

            summary['items_fetched'] = len(reports)

        except Exception as e:
            self.logger.error(f"Error fetching CRS reports: {e}")
            summary['errors'].append(str(e))

        self.checkpoint['last_successful_run'] = datetime.now().isoformat()
        self._save_checkpoint()

        return summary
```

---

#### 7. Court Opinions Agent

**Data Source**: CourtListener API (courtlistener.com/help/api/)
**Types**: Federal district, circuit, Supreme Court; NY state courts
**Volume**: 9M+ federal opinions

```python
# src/agents/federal/court_opinions.py

from base import BaseDataAgent
from pathlib import Path
from typing import Dict, Any
import json
from datetime import datetime, timedelta

class CourtOpinionsAgent(BaseDataAgent):
    """
    Fetches court opinions from CourtListener API.
    Covers federal courts (district, circuit, Supreme) and state courts.
    """

    API_BASE = "https://www.courtlistener.com/api/rest/v3"

    def __init__(self, storage_root: Path, config: Dict):
        super().__init__('court_opinions', storage_root, config)
        self.api_key = config.get('courtlistener_api_key')
        self.rate_limit_delay = 1.0  # CourtListener: 1 request/second

    def gather(self, incremental: bool = True) -> Dict[str, Any]:
        """
        Fetch opinions from federal and state courts.
        Strategy: Fetch recent opinions first, prioritizing higher courts.
        """
        self.logger.info("Starting Court Opinions data gathering")
        summary = {'items_fetched': 0, 'items_new': 0, 'errors': []}

        # Court jurisdictions to fetch (priority order)
        courts = [
            ('scotus', 'Supreme Court'),
            ('fed', 'Federal Circuit'),
            ('d_cir', 'DC Circuit'),
            ('fed_dist', 'Federal District Courts'),
            ('ny_app', 'NY Appellate Division'),
            ('ny_sup', 'NY Supreme Court'),
        ]

        for court_abbr, court_name in courts:
            summary_court = self._fetch_court_opinions(court_abbr, incremental)
            summary['items_fetched'] += summary_court['items_fetched']
            summary['items_new'] += summary_court['items_new']
            summary['errors'].extend(summary_court['errors'])

        self.checkpoint['last_successful_run'] = datetime.now().isoformat()
        self._save_checkpoint()

        return summary

    def _fetch_court_opinions(self, court_abbr: str, incremental: bool) -> Dict:
        """Fetch opinions from a specific court."""
        summary = {'items_fetched': 0, 'items_new': 0, 'errors': []}

        params = {
            'court': court_abbr,
            'order_by': '-date_filed',
            'format': 'json',
            'limit': 100
        }

        # If incremental, fetch only recent (last 30 days)
        if incremental:
            recent_date = (datetime.now() - timedelta(days=30)).date()
            params['date_filed__gte'] = recent_date.isoformat()

        if self.api_key:
            params['api_key'] = self.api_key

        page = 1
        while page <= 100:  # Limit to 10k opinions per court
            params['page'] = page

            try:
                url = f"{self.API_BASE}/opinions"
                response = self.fetch_with_retry(url, params=params)

                if not response:
                    break

                data = response.json()
                results = data.get('results', [])

                if not results:
                    break

                for opinion in results:
                    opinion_id = opinion.get('id')
                    opinion_path = self.storage_root / f"opinions" / f"opinion_{opinion_id}.json"

                    self.save_raw_content(
                        json.dumps(opinion, indent=2),
                        opinion_path,
                        {
                            'source': 'courtlistener.com',
                            'type': 'court_opinion',
                            'court': court_abbr
                        }
                    )
                    summary['items_new'] += 1

                summary['items_fetched'] += len(results)

                # Check for more pages
                if not data.get('next'):
                    break

                page += 1

            except Exception as e:
                self.logger.error(f"Error fetching {court_abbr} opinions page {page}: {e}")
                summary['errors'].append(str(e))
                break

        return summary
```

---

#### 8. New York Consolidated Laws Agent

**Data Source**: Open Legislation API (legislation.nysenate.gov)
**Format**: JSON
**Free API key available**

```python
# src/agents/ny_state/ny_consolidated_laws.py

from base import BaseDataAgent
from pathlib import Path
from typing import Dict, Any
import json
from datetime import datetime

class NYConsolidatedLawsAgent(BaseDataAgent):
    """
    Fetches New York Consolidated Laws from NYSenate Open Legislation API.
    Covers all NY statutes.
    """

    API_BASE = "https://legislation.nysenate.gov/api/v3"

    def __init__(self, storage_root: Path, config: Dict):
        super().__init__('ny_consolidated_laws', storage_root, config)
        self.api_key = config.get('nysenate_api_key')  # Free key from nysenate.gov

    def gather(self, incremental: bool = True) -> Dict[str, Any]:
        """
        Fetch all NY Consolidated Laws organized by chapter.
        """
        self.logger.info("Starting NY Consolidated Laws data gathering")
        summary = {'items_fetched': 0, 'items_new': 0, 'errors': []}

        try:
            # List all law chapters
            url = f"{self.API_BASE}/laws"
            params = {'limit': 200}
            if self.api_key:
                params['key'] = self.api_key

            response = self.fetch_with_retry(url, params=params)
            if not response:
                summary['errors'].append("Failed to fetch NY law chapters")
                return summary

            laws = response.json().get('result', {}).get('items', [])

            for law in laws:
                law_id = law.get('lawId')
                law_name = law.get('name')

                try:
                    # Fetch full law with all sections
                    law_url = f"{self.API_BASE}/laws/{law_id}"
                    law_response = self.fetch_with_retry(law_url, params=params)

                    if law_response:
                        law_data = law_response.json().get('result', {})

                        law_path = self.storage_root / f"laws" / f"{law_id}.json"
                        self.save_raw_content(
                            json.dumps(law_data, indent=2),
                            law_path,
                            {
                                'source': 'legislation.nysenate.gov',
                                'type': 'ny_law',
                                'law_id': law_id,
                                'name': law_name
                            }
                        )
                        summary['items_new'] += 1

                except Exception as e:
                    self.logger.error(f"Error fetching NY law {law_id}: {e}")
                    summary['errors'].append(str(e))

            summary['items_fetched'] = len(laws)

        except Exception as e:
            self.logger.error(f"Error fetching NY laws: {e}")
            summary['errors'].append(str(e))

        self.checkpoint['last_successful_run'] = datetime.now().isoformat()
        self._save_checkpoint()

        return summary
```

---

#### 9. NYC Administrative Code Agent

**Data Source**: NYC Council website (XML)
**Format**: XML
**Storage**: Organized by title

```python
# src/agents/ny_state/nyc_admin_code.py

from base import BaseDataAgent
from pathlib import Path
from typing import Dict, Any
import json
from datetime import datetime

class NYCAdminCodeAgent(BaseDataAgent):
    """
    Fetches NYC Administrative Code from NYC Council.
    Note: Less structured than NY laws; primarily XML.
    """

    DOWNLOAD_BASE = "https://www1.nyc.gov/assets/law/"

    def __init__(self, storage_root: Path, config: Dict):
        super().__init__('nyc_admin_code', storage_root, config)

    def gather(self, incremental: bool = True) -> Dict[str, Any]:
        """
        Fetch NYC Admin Code.
        Strategy: Download from NYC Law website if available.
        """
        self.logger.info("Starting NYC Admin Code data gathering")
        summary = {'items_fetched': 0, 'items_new': 0, 'errors': []}

        # NYC Admin Code has 70 titles
        for title in range(1, 71):
            try:
                # Construct URL (adjust based on actual NYC Council structure)
                url = f"{self.DOWNLOAD_BASE}/xml/nyc_admin_code_title_{title:02d}.xml"

                response = self.fetch_with_retry(url)
                if response:
                    xml_path = self.storage_root / f"title_{title:02d}" / "admin_code.xml"
                    self.save_raw_content(
                        response.text,
                        xml_path,
                        {
                            'source': 'nyc.gov',
                            'type': 'nyc_admin_code',
                            'title': title
                        }
                    )
                    summary['items_new'] += 1

                summary['items_fetched'] += 1

            except Exception as e:
                self.logger.error(f"Error fetching NYC Admin Code title {title}: {e}")
                summary['errors'].append(str(e))

        self.checkpoint['last_successful_run'] = datetime.now().isoformat()
        self._save_checkpoint()

        return summary
```

---

#### 10. NY Regulations (NYCRR) Agent

**Data Source**: NY Department of State (NOT well-structured; requires scraping)
**Gap Note**: NYCRR is not available in structured format. This agent documents the gap and provides scraping strategy.

```python
# src/agents/ny_state/ny_regulations.py

from base import BaseDataAgent
from pathlib import Path
from typing import Dict, Any
import json
from datetime import datetime

class NYRegulationsAgent(BaseDataAgent):
    """
    New York Code of Rules and Regulations (NYCRR) Agent.

    STATUS: PARTIAL / REQUIRES SCRAPING

    The NY Department of State does NOT provide bulk structured data for NYCRR.
    Regulations are published in:
    1. NY Register (weekly publication) - PDF format
    2. Department websites (scattered, inconsistent)
    3. No centralized XML or JSON API

    RECOMMENDED APPROACH:
    - Scrape NY Register PDFs (dos.ny.gov/agencies/department-state/ny-register)
    - Extract regulatory text using PDF parsing + OCR where needed
    - Categorize by agency and regulatory chapter
    - Note: This requires significant additional engineering effort

    For MVP: Catalog known departments and point to their websites
    """

    REGISTER_BASE = "https://dos.ny.gov/agencies/department-state/ny-register"

    def __init__(self, storage_root: Path, config: Dict):
        super().__init__('ny_regulations', storage_root, config)
        self.logger.warning("NYCRR data gathering: Limited functionality due to lack of structured source data")

    def gather(self, incremental: bool = True) -> Dict[str, Any]:
        """
        Partial implementation: Document gap and catalog known resources.
        """
        self.logger.info("Starting NY Regulations (NYCRR) data gathering")
        summary = {'items_fetched': 0, 'items_new': 0, 'errors': []}

        # Known NY regulatory bodies (non-exhaustive)
        agencies = {
            'DEC': 'Department of Environmental Conservation',
            'DOH': 'Department of Health',
            'DOS': 'Department of State',
            'DFS': 'Department of Financial Services',
            'DEC-DKA': 'Department of Environmental Conservation - Division of Kenworthy Avoidance',
            # ... more
        }

        # Document the gap
        gap_doc = {
            'status': 'INCOMPLETE',
            'reason': 'NYCRR is not available in structured digital format',
            'data_sources': [
                {
                    'name': 'NY Register',
                    'url': 'https://dos.ny.gov/agencies/department-state/ny-register',
                    'format': 'PDF (weekly)',
                    'accessibility': 'Requires PDF parsing/OCR'
                },
                {
                    'name': 'Agency Websites',
                    'url': 'Various (department-specific)',
                    'format': 'HTML/PDF (inconsistent)',
                    'accessibility': 'Requires scraping'
                }
            ],
            'recommended_approach': 'Scrape NY Register + agency websites with PDF extraction + OCR',
            'effort_estimate': '3-4 weeks engineering',
            'known_agencies': agencies
        }

        gap_path = self.storage_root / "NYCRR_GAP_ANALYSIS.json"
        self.save_raw_content(
            json.dumps(gap_doc, indent=2),
            gap_path,
            {'type': 'gap_analysis'}
        )

        summary['errors'].append('NYCRR data source not structured; see NYCRR_GAP_ANALYSIS.json')

        return summary
```

---

### Summary of Data Agents

| Agent | Source | Format | Volume | Update Freq | API Key |
|-------|--------|--------|--------|-------------|---------|
| US Code | uscode.house.gov | XML (USLM) | 54 titles | Annual | None |
| CFR | govinfo.gov + ecfr.gov | XML + JSON API | 50 titles | Annual + Daily | None |
| Executive Orders | Federal Register API | JSON | 1000s | Real-time | None |
| Bills/Laws | Congress.gov + govinfo | JSON + XML | 10000s/session | Real-time | api.data.gov key |
| Federal Register | federalregister.gov API | JSON/XML | 1000s/month | Real-time | None |
| CRS Reports | everycrsreport.com | PDF + JSON | 23,000+ | Ad-hoc | None |
| Court Opinions | CourtListener API | JSON | 9M+ | Daily | Optional |
| NY Laws | Open Legislation API | JSON | 1800+ | Real-time | Free |
| NYC Admin Code | nyc.gov | XML | 70 titles | Periodic | None |
| NY Regulations | N/A (gap) | PDF (Register) | Unknown | Weekly | N/A |

---

## Part B: Context Gathering Agents

These agents run AFTER data gathering but BEFORE parsing to prepare supporting context that improves extraction quality.

### 6.1 Base Context Agent

```python
# src/agents/context_gathering/base_context.py

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, List
import logging
import json

class BaseContextAgent(ABC):
    """
    Base class for context gathering agents.
    Context agents enrich raw legal text with supporting data:
    - Definitions
    - Cross-references
    - Legislative history
    - Court interpretations
    """

    def __init__(self, name: str, storage_root: Path):
        self.name = name
        self.storage_root = storage_root
        self.storage_root.mkdir(parents=True, exist_ok=True)

        self.logger = logging.getLogger(f"context.{name}")
        handler = logging.FileHandler(self.storage_root / f"{name}_context.log")
        handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        self.logger.addHandler(handler)

    @abstractmethod
    def build_context(self) -> Dict[str, Any]:
        """Build context from raw data."""
        pass
```

### 6.2 Definitions Resolution Agent

```python
# src/agents/context_gathering/definitions.py

from base_context import BaseContextAgent
from pathlib import Path
from typing import Dict, Any, List, Tuple
import json
import xml.etree.ElementTree as ET
from collections import defaultdict

class DefinitionsAgent(BaseContextAgent):
    """
    Deterministic agent that extracts all definitions from legal text.

    Strategy:
    1. Parse all <definition> tags in USLM XML
    2. Extract definition text and scope (which title/chapter)
    3. Build index: term -> {scope, definition_text, source_section}
    4. Handle cross-scope references (e.g., "as defined in Title X")

    Output: definitions.json keyed by (term, scope)
    """

    def __init__(self, storage_root: Path, raw_data_root: Path):
        super().__init__('definitions', storage_root)
        self.raw_data_root = raw_data_root

    def build_context(self) -> Dict[str, Any]:
        """
        Extract definitions from USC, CFR, NY laws, etc.
        Returns: {
            'definitions': {
                'term|scope': {
                    'text': '...',
                    'source_section': '42 U.S.C. § 100',
                    'source_title': '42',
                    'statute': 'USC',
                    'scope': 'title_42'  # or 'chapter_X'
                },
                ...
            },
            'cross_scope_refs': [...]
        }
        """
        self.logger.info("Building definitions index")

        definitions = defaultdict(dict)
        cross_scope_refs = []

        # Process USC
        uscode_root = self.raw_data_root / 'uscode'
        for title_dir in uscode_root.glob('title_*'):
            title_num = title_dir.name.split('_')[1]

            for xml_file in title_dir.glob('*.xml'):
                try:
                    defs_in_file = self._extract_definitions_from_xml(
                        xml_file, 'USC', f'title_{title_num}'
                    )

                    for term, def_info in defs_in_file.items():
                        key = f"{term}|{def_info['scope']}"
                        definitions[key] = def_info

                except Exception as e:
                    self.logger.error(f"Error processing {xml_file}: {e}")

        # Process CFR similarly
        cfr_root = self.raw_data_root / 'cfr'
        for title_dir in cfr_root.glob('*'):
            if title_dir.is_dir():
                for xml_file in title_dir.glob('*.xml'):
                    try:
                        defs_in_file = self._extract_definitions_from_xml(
                            xml_file, 'CFR', title_dir.name
                        )
                        for term, def_info in defs_in_file.items():
                            key = f"{term}|{def_info['scope']}"
                            definitions[key] = def_info
                    except Exception as e:
                        self.logger.error(f"Error processing {xml_file}: {e}")

        # Save definitions index
        output = {
            'definitions': definitions,
            'cross_scope_refs': cross_scope_refs,
            'total_unique_terms': len(set(k.split('|')[0] for k in definitions.keys()))
        }

        output_path = self.storage_root / 'definitions_index.json'
        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2, default=str)

        self.logger.info(f"Built definitions index: {output['total_unique_terms']} unique terms")
        return output

    def _extract_definitions_from_xml(self, xml_path: Path, statute: str,
                                     scope: str) -> Dict[str, Dict]:
        """Extract <definition> elements from USLM XML."""
        definitions = {}

        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            # USLM schema uses <definition> tags
            for def_elem in root.findall('.//{urn:us:gov:doc:uslm}definition'):
                term = def_elem.get('term')
                if term:
                    def_text = ET.tostring(def_elem, encoding='unicode', method='text').strip()

                    definitions[term] = {
                        'term': term,
                        'text': def_text,
                        'source_section': xml_path.name,
                        'statute': statute,
                        'scope': scope
                    }

        except Exception as e:
            self.logger.error(f"Error parsing XML {xml_path}: {e}")

        return definitions
```

**Output Structure**: `definitions_index.json`
```json
{
  "definitions": {
    "Administrator|title_42": {
      "term": "Administrator",
      "text": "The Administrator of the Environmental Protection Agency...",
      "source_section": "42 U.S.C. § 7601",
      "statute": "USC",
      "scope": "title_42"
    },
    "...": {}
  },
  "cross_scope_refs": [],
  "total_unique_terms": 15000
}
```

---

### 6.3 Cross-Reference Resolution Agent

```python
# src/agents/context_gathering/cross_references.py

from base_context import BaseContextAgent
from pathlib import Path
from typing import Dict, Any, List, Tuple
import json
import xml.etree.ElementTree as ET
import re

class CrossReferenceAgent(BaseContextAgent):
    """
    Deterministic agent that resolves cross-references in legal text.

    Extracts all <ref> tags, resolves them to actual provision texts,
    builds a cross-reference graph.

    Output: xref_graph.json with {provision: {outgoing_refs: [...], incoming_refs: [...]}}
    """

    def __init__(self, storage_root: Path, raw_data_root: Path):
        super().__init__('cross_references', storage_root)
        self.raw_data_root = raw_data_root
        self.provision_cache = {}  # Caches provisions for fast lookup

    def build_context(self) -> Dict[str, Any]:
        """Build cross-reference graph."""
        self.logger.info("Building cross-reference graph")

        # Phase 1: Build provision lookup index
        self._build_provision_index()

        # Phase 2: Extract all references from USLM XML
        xref_graph = defaultdict(lambda: {'outgoing': [], 'incoming': []})

        uscode_root = self.raw_data_root / 'uscode'
        for xml_file in uscode_root.rglob('*.xml'):
            refs = self._extract_references_from_xml(xml_file)
            for source_provision, target_ref in refs:
                xref_graph[source_provision]['outgoing'].append(target_ref)
                xref_graph[target_ref]['incoming'].append(source_provision)

        # Phase 3: Normalize references (resolve shorthand like "this section" -> actual citation)
        normalized_graph = self._normalize_references(xref_graph)

        # Save
        output_path = self.storage_root / 'xref_graph.json'
        with open(output_path, 'w') as f:
            json.dump(normalized_graph, f, indent=2, default=str)

        self.logger.info(f"Built xref graph with {len(normalized_graph)} provisions")
        return {'xref_graph': normalized_graph}

    def _build_provision_index(self):
        """Cache all provisions for fast lookup."""
        # Simplified: would build full citation -> section mapping
        pass

    def _extract_references_from_xml(self, xml_path: Path) -> List[Tuple[str, str]]:
        """Extract all <ref> elements from USLM XML."""
        references = []

        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            for ref_elem in root.findall('.//{urn:us:gov:doc:uslm}ref'):
                href = ref_elem.get('href')
                ref_text = ref_elem.text

                if href:
                    # Determine source provision (context of this ref)
                    source_provision = self._get_containing_provision(ref_elem)
                    references.append((source_provision, href))

        except Exception as e:
            self.logger.error(f"Error parsing {xml_path}: {e}")

        return references

    def _get_containing_provision(self, elem) -> str:
        """Get the immediate parent provision (section/subsection) of this element."""
        # Walk up XML tree to find parent <section> tag
        pass

    def _normalize_references(self, xref_graph) -> Dict:
        """Resolve relative references (e.g., 'this section')."""
        # Placeholder for normalization logic
        return dict(xref_graph)
```

---

### 6.4 Legislative History Agent

```python
# src/agents/context_gathering/legislative_history.py

from base_context import BaseContextAgent
from pathlib import Path
from typing import Dict, Any, List
import json
from datetime import datetime

class LegislativeHistoryAgent(BaseContextAgent):
    """
    Gathers legislative history for key provisions:
    - Committee reports
    - Floor statements
    - CRS analyses

    Uses Congress.gov API + CRS reports to build legislative context.
    This context helps interpret legislative intent.
    """

    def __init__(self, storage_root: Path, config: Dict):
        super().__init__('legislative_history', storage_root)
        self.congress_api_key = config.get('congress_api_key')

    def build_context(self) -> Dict[str, Any]:
        """
        For a given public law, retrieve:
        1. Bill number and full text
        2. Committee report (House and Senate)
        3. CRS report if available
        4. Floor statements/debates

        Keyed by: public_law_citation -> {bill_num, committees, crs_report, debates}
        """
        self.logger.info("Building legislative history context")

        legislative_history = {}

        # Query recent public laws from Congress.gov API
        # ... fetch and organize by law ...

        return {'legislative_history': legislative_history}
```

---

### 6.5 Court Interpretations Agent

```python
# src/agents/context_gathering/court_interpretations.py

from base_context import BaseContextAgent
from pathlib import Path
from typing import Dict, Any, List
import json
import requests

class CourtInterpretationsAgent(BaseContextAgent):
    """
    For each statutory provision, retrieves court opinions that cite/interpret it.

    Strategy:
    1. Parse statutory citations from USC/CFR/NY laws
    2. Query CourtListener for cases citing each provision
    3. Rank by: (a) court level, (b) citation frequency, (c) recency
    4. Store top N interpretations per provision

    IMPORTANT: Court data is MAIN DATA, not supplementary.
    Extracted court interpretations become norm instances in the graph.
    """

    COURTLISTENER_API = "https://www.courtlistener.com/api/rest/v3"

    def __init__(self, storage_root: Path, config: Dict):
        super().__init__('court_interpretations', storage_root)
        self.api_key = config.get('courtlistener_api_key')
        self.rate_limit_delay = 1.0  # 1 req/sec

    def build_context(self) -> Dict[str, Any]:
        """
        Build court interpretation index.
        Output: {provision_citation: {opinions: [...], summary: ...}}
        """
        self.logger.info("Building court interpretations context")

        interpretations = {}

        # For each statute provision, query CourtListener
        # statute_citations = self._load_statute_citations()

        # for citation in statute_citations:
        #     opinions = self._fetch_citing_opinions(citation)
        #     ranked_opinions = self._rank_opinions(opinions)
        #     interpretations[citation] = ranked_opinions

        # Save
        output_path = self.storage_root / 'court_interpretations.json'
        with open(output_path, 'w') as f:
            json.dump(interpretations, f, indent=2, default=str)

        self.logger.info(f"Built court interpretations for provisions")
        return {'court_interpretations': interpretations}

    def _fetch_citing_opinions(self, statute_citation: str) -> List[Dict]:
        """Query CourtListener for all opinions citing this provision."""
        # API query: search?q=statute_citation
        pass

    def _rank_opinions(self, opinions: List[Dict]) -> List[Dict]:
        """
        Rank opinions by:
        1. Court level (Supreme Court > Circuit > District)
        2. Citation frequency (how often cited in subsequent cases)
        3. Recency (more recent = higher authority if controlling)
        """
        # Ranking logic
        pass
```

---

### 6.6 Academic Database Identification Agent

```python
# src/agents/context_gathering/academic_databases.py

from base_context import BaseContextAgent
from pathlib import Path
from typing import Dict, Any, List
import json

class AcademicDatabaseAgent(BaseContextAgent):
    """
    Identifies and catalogs academic databases relevant to statutory interpretation.

    These are for FUTURE integration — we catalog them now for reference.
    """

    def __init__(self, storage_root: Path):
        super().__init__('academic_databases', storage_root)

    def build_context(self) -> Dict[str, Any]:
        """
        Catalog academic databases with access info and costs.
        """
        databases = {
            'heinonline': {
                'name': 'HeinOnline',
                'url': 'https://heinonline.org',
                'description': 'Largest comprehensive law journal database',
                'coverage': 'Law reviews, government documents, historical materials',
                'access': 'Institutional subscription required',
                'cost': '~$3000/year (institution dependent)',
                'api_available': False,
                'notes': 'Partner with law school or academic institution'
            },
            'ssrn': {
                'name': 'SSRN Legal Studies Network',
                'url': 'https://papers.ssrn.com',
                'description': 'Preprints and working papers in law',
                'coverage': 'Legal scholarship, working papers',
                'access': 'Free (open)',
                'cost': None,
                'api_available': True,
                'api_url': 'https://www.ssrn.com/developers',
                'notes': 'Good for emerging scholarship and working papers'
            },
            'scholar': {
                'name': 'Google Scholar',
                'url': 'https://scholar.google.com',
                'description': 'Academic search engine including law',
                'coverage': 'Legal opinions, law reviews, books',
                'access': 'Free (scraping limited)',
                'cost': None,
                'api_available': False,
                'notes': 'Covers many law review articles; limited API'
            },
            'westlaw': {
                'name': 'Westlaw',
                'url': 'https://www.westlaw.com',
                'description': 'Commercial legal research platform',
                'coverage': 'Cases, statutes, secondary sources, treatises',
                'access': 'Institutional subscription or individual license',
                'cost': '$500-5000/month (varies)',
                'api_available': True,
                'api_notes': 'REST API available to subscribers',
                'notes': 'Premium option; integrated with Thomson Reuters'
            },
            'lexisnexis': {
                'name': 'LexisNexis',
                'url': 'https://www.lexisnexis.com',
                'description': 'Commercial legal research platform',
                'coverage': 'Cases, statutes, secondary sources',
                'access': 'Institutional subscription or individual license',
                'cost': '$500-5000/month (varies)',
                'api_available': True,
                'api_notes': 'REST API available to subscribers',
                'notes': 'Competitor to Westlaw'
            },
            'university_repositories': {
                'name': 'University Institutional Repositories',
                'url': 'Various (e.g., bepress.com, law.bepress.com)',
                'description': 'Law school repositories of faculty scholarship',
                'coverage': 'Law review articles, faculty papers',
                'access': 'Variable (many open)',
                'cost': None,
                'api_available': False,
                'notes': 'Distributed; requires aggregation'
            },
            'jlc': {
                'name': 'Justia Law Cases',
                'url': 'https://law.justia.com',
                'description': 'Free legal research platform',
                'coverage': 'Cases (US federal and state)',
                'access': 'Free (public)',
                'cost': None,
                'api_available': True,
                'api_url': 'https://www.justia.com/developers/',
                'notes': 'Good free alternative to Westlaw/LexisNexis'
            }
        }

        output = {
            'databases': databases,
            'recommendation': 'Start with free sources (SSRN, Google Scholar, Justia, university repos); negotiate institutional access to Westlaw/LexisNexis or HeinOnline for comprehensive coverage',
            'integration_priorities': [
                '1. SSRN API (free, available)',
                '2. Google Scholar (scraping, limited)',
                '3. University repositories (aggregated)',
                '4. Westlaw/LexisNexis (negotiate access)',
                '5. HeinOnline (partner with institution)'
            ]
        }

        output_path = self.storage_root / 'academic_databases_catalog.json'
        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2)

        self.logger.info("Cataloged academic databases")
        return output
```

---

### 6.7 Entity Resolution Agent

```python
# src/agents/context_gathering/entity_resolution.py

from base_context import BaseContextAgent
from pathlib import Path
from typing import Dict, Any, List, Set
import json
from difflib import SequenceMatcher

class EntityResolutionAgent(BaseContextAgent):
    """
    Consolidates entities across provisions.

    Example: "EPA Administrator", "the Administrator" (in EPA context),
    "Administrator of the Environmental Protection Agency" -> single canonical entity.

    Uses definitions index + fuzzy matching.
    """

    def __init__(self, storage_root: Path, definitions_index_path: Path):
        super().__init__('entity_resolution', storage_root)
        self.definitions_index_path = definitions_index_path

    def build_context(self) -> Dict[str, Any]:
        """
        Build entity consolidation map.
        Output: {canonical_entity_id: {names: [...], context: {...}}}
        """
        self.logger.info("Building entity consolidation map")

        # Load definitions index
        with open(self.definitions_index_path) as f:
            definitions = json.load(f).get('definitions', {})

        # Extract entities from definition names and values
        entities = {}
        entity_clusters = {}  # Groups variant names -> canonical form

        # Process definitions
        for term, def_info in definitions.items():
            # Each defined term is an entity
            term_clean = term.strip()

            # Check if this is a variant of an existing entity
            canonical = self._find_canonical_entity(term_clean, entity_clusters)

            if canonical:
                entity_clusters[canonical].add(term_clean)
            else:
                # New entity
                entity_clusters[term_clean] = {term_clean}

        # Build canonical mapping
        entity_map = {}
        for canonical, variants in entity_clusters.items():
            entity_id = canonical.lower().replace(' ', '_')
            entity_map[entity_id] = {
                'canonical_name': canonical,
                'variant_names': list(variants),
                'definitions': [
                    def_info for term, def_info in definitions.items()
                    if term in variants
                ]
            }

        output_path = self.storage_root / 'entity_consolidation.json'
        with open(output_path, 'w') as f:
            json.dump(entity_map, f, indent=2)

        self.logger.info(f"Built entity map with {len(entity_map)} canonical entities")
        return {'entity_map': entity_map}

    def _find_canonical_entity(self, term: str, clusters: Dict[str, Set]) -> str:
        """Find if this term is a variant of an existing canonical entity."""
        for canonical, variants in clusters.items():
            for variant in variants:
                # Fuzzy match with threshold
                similarity = SequenceMatcher(None, term.lower(), variant.lower()).ratio()
                if similarity > 0.85:
                    return canonical
        return None
```

---

## Summary of Context Agents

All context agents inherit from `BaseContextAgent` and output to JSON files in `storage_root/context/`:

1. **Definitions**: `definitions_index.json` — 15,000+ terms with scopes
2. **Cross-References**: `xref_graph.json` — provision connectivity
3. **Legislative History**: `legislative_history.json` — bill history + committee reports
4. **Court Interpretations**: `court_interpretations.json` — cited cases per provision
5. **Academic DBs**: `academic_databases_catalog.json` — future integration sources
6. **Entity Resolution**: `entity_consolidation.json` — canonical entity names

These outputs feed directly into the parsing pipeline as "context windows" alongside raw legal text.

---

## Part C: Parsing Pipeline

The AI-driven extraction pipeline uses Claude models via Anthropic API to extract normative content from raw legal text enriched with context from Part B.

### C.1: Pipeline Architecture

The parsing pipeline has six sequential stages, each optimized for cost and quality:

```
Stage 1: Structural Parsing
  ├─ Input: Raw legal document (USLM XML, HTML, PDF text)
  ├─ Task: Extract hierarchy (titles → chapters → sections → subsections)
  ├─ Model: Sonnet 4 (cheaper; this is deterministic)
  ├─ Output: Document tree with provision IDs
  └─ Time: ~30s per document

Stage 2: Definitions Extraction
  ├─ Input: Document tree + definition sections
  ├─ Task: Extract all definitions; validate scope
  ├─ Model: Sonnet 4 (structured, rule-based extraction)
  ├─ Output: Definitions list (already indexed in context agents)
  └─ Time: ~20s per document

Stage 3: Normative Extraction (THE MAIN EVENT)
  ├─ Input: Each provision + context (definitions, cross-refs, court cases)
  ├─ Task: Extract norms, deontic operators, conditions, consequences
  ├─ Model: Opus 4.6 (complex reasoning; use Sonnet for straightforward)
  ├─ Output: JSON conforming to NormativeExtraction schema
  ├─ Confidence scores for each norm
  └─ Time: ~2-3min per provision (batched via Batch API)

Stage 4: Court Opinion Extraction
  ├─ Input: Citing court opinions + statute being interpreted
  ├─ Task: Extract court's interpretation as norms
  ├─ Model: Opus 4.6 (interpreting judicial reasoning)
  ├─ Output: Norm instances with court authority + citation
  └─ Time: ~2-3min per opinion

Stage 5: Entity Resolution (Consolidation Pass)
  ├─ Input: Extracted norms with entity mentions
  ├─ Task: Map entities to canonical forms (from Part B)
  ├─ Model: Haiku or deterministic string matching
  ├─ Output: Norms with normalized entity references
  └─ Time: ~10s per provision

Stage 6: Validation & Quality Assurance
  ├─ Input: Extracted + normalized norms
  ├─ Task: Check schema conformance, cross-ref consistency
  ├─ Model: Sonnet 4 (structured validation)
  ├─ Output: Pass/fail + human review queue for failures
  └─ Time: ~15s per provision
```

### C.2: Core Parsing Modules

```python
# src/parsing/
  __init__.py
  pipeline.py               # Main orchestrator
  stages/
    __init__.py
    structural_parsing.py   # Stage 1
    definitions_extraction.py  # Stage 2
    normative_extraction.py # Stage 3 (main)
    court_extraction.py     # Stage 4
    entity_resolution.py    # Stage 5
    validation.py           # Stage 6
  prompts/
    __init__.py
    system_prompts.py       # Ontology schema + guidelines
    few_shot_examples.py    # 15-20 hand-annotated provisions
    context_assembly.py     # Build context windows
  batch_api/
    __init__.py
    client.py               # Anthropic Batch API wrapper
    request_builder.py      # Build batch requests
    result_processor.py     # Parse batch results
  database/
    __init__.py
    models.py               # SQLAlchemy models for job tracking
    human_review_queue.py   # Store low-confidence extractions
  schemas/
    __init__.py
    normative_extraction.py # Pydantic models matching ontology
```

### C.3: API Call Architecture

#### Stage 3 Implementation (Normative Extraction - Main)

```python
# src/parsing/stages/normative_extraction.py

from anthropic import Anthropic
from pathlib import Path
from typing import Dict, Any, List, Optional
import json
import logging
from datetime import datetime
import time

class NormativeExtractionStage:
    """
    Main extraction stage: uses Claude Opus 4.6 (Batch API) to extract norms
    from statutory/regulatory provisions.

    Features:
    - Batch API for cost savings (50% discount, 24hr turnaround)
    - Prompt caching for repeated ontology schema
    - Rate limiting + retry logic
    - Confidence scoring
    - Checkpoint-based resumption
    """

    def __init__(self, config: Dict, db_session):
        self.client = Anthropic(api_key=config['anthropic_api_key'])
        self.config = config
        self.db = db_session
        self.logger = logging.getLogger('NormativeExtraction')

        # For Batch API
        self.batch_requests: List[Dict] = []
        self.batch_size = config.get('batch_size', 50)
        self.checkpoint_dir = Path(config['checkpoint_dir'])
        self.checkpoint_dir.mkdir(exist_ok=True)

    def extract_provision(self, provision_text: str, provision_id: str,
                         context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract norms from a single provision.

        Args:
            provision_text: Raw text of the provision
            provision_id: Identifier (e.g., "42-USC-7602")
            context: {
                'definitions': [...],
                'cross_references': [...],
                'court_interpretations': [...],
                'legislative_history': {...}
            }

        Returns:
            {
                'provision_id': str,
                'norms': [{
                    'deontic_operator': 'SHALL' | 'MAY' | 'SHALL NOT' | ...,
                    'subject': str,
                    'action': str,
                    'object': str,
                    'conditions': [str],
                    'exceptions': [str],
                    'consequences': [str],
                    'authority': str,
                    'defeasible': bool,
                    'confidence': float
                }],
                'status': 'extracted' | 'requires_review',
                'extraction_timestamp': datetime,
                'model_used': 'opus-4-6-20250514',
                'tokens_used': {
                    'input': int,
                    'output': int,
                    'cache_read': int,
                    'cache_creation': int
                }
            }
        """

        # Build prompt with caching
        system_prompt = self._build_system_prompt()
        context_window = self._build_context_window(context)
        user_prompt = self._build_user_prompt(provision_text, provision_id)

        # Check if we should use batch API (non-urgent) or streaming (urgent/testing)
        if self.config.get('use_batch_api', True):
            return self._queue_for_batch(provision_id, system_prompt, context_window, user_prompt)
        else:
            return self._extract_streaming(system_prompt, context_window, user_prompt)

    def _build_system_prompt(self) -> Dict[str, Any]:
        """
        Build system prompt with cached ontology schema + annotation guidelines.
        Caching saves ~2,000 tokens per request when processing 100+ provisions.
        """
        # Load ontology schema from document
        ontology_schema = self._load_ontology_schema()
        annotation_guidelines = self._load_annotation_guidelines()

        return {
            'type': 'text',
            'text': f"""You are an expert legal AI assistant trained to extract normative content from US law.

## Ontology Schema

{ontology_schema}

## Annotation Guidelines

{annotation_guidelines}

## Your Task

Extract all normative provisions from the provided legal text. For each norm, identify:
1. Deontic operator (SHALL, MAY, SHALL NOT, MUST, CAN, etc.)
2. Subject (who/what the norm applies to)
3. Action (what they must/may/must not do)
4. Object (what the action applies to)
5. Conditions (when the norm applies)
6. Exceptions (when the norm doesn't apply)
7. Consequences (what happens if violated)
8. Defeasibility (can this norm be overridden? under what conditions?)

Output ONLY valid JSON conforming to the NormativeExtraction schema.
Do NOT output explanations or markdown — just pure JSON.
If extraction is uncertain, set confidence < 0.75 and the human review queue will handle it.""",
            'cache_control': {'type': 'ephemeral'}  # Cache for 5 minutes
        }

    def _build_context_window(self, context: Dict) -> str:
        """
        Assemble context window: definitions, cross-refs, court cases, etc.
        This gets sent with every provision for consistent reasoning.
        """
        parts = []

        if context.get('definitions'):
            parts.append("## Definitions\n\n")
            for term, def_text in context['definitions'].items():
                parts.append(f"- **{term}**: {def_text}\n")

        if context.get('cross_references'):
            parts.append("\n## Related Provisions\n\n")
            for ref in context['cross_references'][:10]:  # Top 10 most relevant
                parts.append(f"- {ref['citation']}: {ref['summary']}\n")

        if context.get('court_interpretations'):
            parts.append("\n## Court Interpretations\n\n")
            for case in context['court_interpretations'][:5]:  # Top 5 most authoritative
                parts.append(f"- {case['citation']}: {case['holding']}\n")

        return ''.join(parts)

    def _build_user_prompt(self, provision_text: str, provision_id: str) -> str:
        """Build user prompt for this specific provision."""
        return f"""Extract norms from this provision:

**Provision ID**: {provision_id}

**Provision Text**:
{provision_text}

Output JSON only, conforming to NormativeExtraction schema."""

    def _queue_for_batch(self, provision_id: str, system_prompt: Dict,
                        context_window: str, user_prompt: str) -> Dict:
        """Queue request for Batch API processing."""
        request = {
            'custom_id': provision_id,
            'params': {
                'model': 'claude-opus-4-6-20250514',
                'max_tokens': 2000,
                'messages': [
                    {
                        'role': 'user',
                        'content': [
                            {'type': 'text', 'text': context_window},
                            {'type': 'text', 'text': user_prompt}
                        ]
                    }
                ],
                'system': system_prompt
            }
        }

        self.batch_requests.append(request)

        # When batch reaches threshold, submit it
        if len(self.batch_requests) >= self.batch_size:
            batch_id = self._submit_batch()
            self.logger.info(f"Submitted batch {batch_id} with {self.batch_size} requests")
            self.batch_requests = []

        return {'status': 'queued', 'provision_id': provision_id}

    def _submit_batch(self) -> str:
        """Submit accumulated batch to API."""
        batch_file = self.checkpoint_dir / f"batch_{datetime.now().isoformat()}.jsonl"

        with open(batch_file, 'w') as f:
            for req in self.batch_requests:
                f.write(json.dumps({'custom_id': req['custom_id'], 'params': req['params']}) + '\n')

        # Upload batch file
        with open(batch_file, 'rb') as f:
            response = self.client.beta.files.upload(
                file=f,
                betas=['files-api-2025-04-14']
            )

        file_id = response.id

        # Submit batch job
        batch = self.client.beta.batches.create(
            requests=self.batch_requests,
            betas=['batch-2025-04-14']
        )

        return batch.id

    def _extract_streaming(self, system_prompt: Dict, context_window: str,
                          user_prompt: str) -> Dict:
        """Extract using streaming (for testing/interactive use)."""
        response = self.client.messages.create(
            model='claude-opus-4-6-20250514',
            max_tokens=2000,
            system=[system_prompt],
            messages=[
                {
                    'role': 'user',
                    'content': context_window + '\n' + user_prompt
                }
            ]
        )

        # Parse response JSON
        try:
            result = json.loads(response.content[0].text)
            return {
                'status': 'extracted',
                'norms': result.get('norms', []),
                'tokens_used': {
                    'input': response.usage.input_tokens,
                    'output': response.usage.output_tokens,
                    'cache_read': response.usage.cache_read_input_tokens or 0,
                    'cache_creation': response.usage.cache_creation_input_tokens or 0
                }
            }
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse model response: {e}")
            return {'status': 'parse_error', 'error': str(e)}

    def _load_ontology_schema(self) -> str:
        """Load ontology schema from Combined_Ontology_Schema.md."""
        # This is cached via prompt_caching, so loading it repeatedly is cheap
        with open(self.config['ontology_schema_path']) as f:
            return f.read()

    def _load_annotation_guidelines(self) -> str:
        """Load annotation guidelines."""
        with open(self.config['annotation_guidelines_path']) as f:
            return f.read()
```

#### Batch Processing Results Handler

```python
# src/parsing/batch_api/result_processor.py

from anthropic import Anthropic
from pathlib import Path
from typing import Dict, List, Any
import json
import logging
import time

class BatchResultProcessor:
    """
    Polls completed batch jobs and processes results.
    Results are written to database and human review queue.
    """

    def __init__(self, client: Anthropic, db_session, config: Dict):
        self.client = client
        self.db = db_session
        self.config = config
        self.logger = logging.getLogger('BatchProcessor')

    def monitor_and_process_batch(self, batch_id: str, poll_interval: int = 30):
        """
        Monitor a batch job until completion, then process results.
        Args:
            batch_id: ID returned from batch submission
            poll_interval: Seconds between status checks (default 30)
        """
        self.logger.info(f"Monitoring batch {batch_id}")

        while True:
            batch = self.client.beta.batches.retrieve(batch_id)

            self.logger.info(
                f"Batch {batch_id}: {batch.request_counts.succeeded}/"
                f"{batch.request_counts.total} completed"
            )

            if batch.processing_status == 'ended':
                # Download results
                self._process_completed_batch(batch_id)
                break
            elif batch.processing_status == 'failed':
                self.logger.error(f"Batch {batch_id} failed: {batch.error_message}")
                break

            time.sleep(poll_interval)

    def _process_completed_batch(self, batch_id: str):
        """Download and process all results from completed batch."""
        result_stream = self.client.beta.batches.results(batch_id)

        for result in result_stream:
            custom_id = result.custom_id
            message = result.result.message

            try:
                # Extract JSON from response
                response_text = message.content[0].text
                extraction = json.loads(response_text)

                # Determine if extraction quality is good
                confidence = min(
                    [norm.get('confidence', 0.5) for norm in extraction.get('norms', [])]
                )

                if confidence < self.config.get('review_threshold', 0.75):
                    # Queue for human review
                    self.db.add(
                        HumanReviewQueueItem(
                            provision_id=custom_id,
                            extraction=json.dumps(extraction),
                            confidence_score=confidence,
                            status='pending_review'
                        )
                    )
                else:
                    # Write directly to database
                    self.db.add(
                        ExtractedNorm(
                            provision_id=custom_id,
                            norms=json.dumps(extraction['norms']),
                            confidence_score=confidence,
                            status='extracted',
                            batch_id=batch_id,
                            tokens_used=json.dumps(extraction.get('tokens_used', {}))
                        )
                    )

            except Exception as e:
                self.logger.error(f"Error processing result for {custom_id}: {e}")
                self.db.add(
                    HumanReviewQueueItem(
                        provision_id=custom_id,
                        error_message=str(e),
                        status='error'
                    )
                )

        self.db.commit()
        self.logger.info(f"Processed batch {batch_id}")
```

### C.4: Cost Optimization Strategy

**Tiered Model Usage**:
- **Opus 4.6**: Complex provisions, court opinion interpretation (~40% of requests)
- **Sonnet 4**: Structural parsing, straightforward definitions, validation (~50%)
- **Haiku**: Entity matching, simple lookups (~10%)

**API Strategy**:
1. **Batch API** (50% discount):
   - Use for all non-urgent processing
   - 24-hour turnaround acceptable
   - Best for bulk provision extraction

2. **Prompt Caching**:
   - Cache ontology schema + few-shot examples (~4,000 tokens)
   - Saves 90% cost on repeated context (2-3 tokens vs 50 tokens per provision)
   - Estimated savings: $200-400 per 1,000 provisions

3. **Context Window Assembly**:
   - Don't include all definitions/cross-refs
   - Prioritize top N most relevant items
   - Reduces token count by 30-40%

**Cost Estimates** (per provision, averaged):

| Stage | Model | Tokens In | Tokens Out | Cost/Prov | Volume | Total |
|-------|-------|-----------|-----------|-----------|--------|-------|
| Structural | Sonnet | 200 | 150 | $0.0018 | 100K | $180 |
| Defs | Sonnet | 400 | 200 | $0.0032 | 100K | $320 |
| **Norms** | **Opus** | **1500** | **1000** | **$0.065** | **100K** | **$6500** |
| Court | Opus | 2000 | 1200 | $0.085 | 50K | $4250 |
| Entity | Haiku | 300 | 100 | $0.0008 | 100K | $80 |
| Validation | Sonnet | 500 | 300 | $0.0028 | 100K | $280 |
| **TOTAL** | | | | | | **~$11,610** |

**Optimized** (with Batch API + caching + tiered models):
- Base cost: $11,610
- Batch API discount: -$5,805 (50% off normative extraction)
- Prompt caching savings: -$1,200 (repeated context)
- **Final: ~$4,605 for 100K provisions**

For complete federal corpus (~300K provisions):
- **Estimated total: $13,800-18,000** (depending on complexity distribution)
- Plus smaller costs for court opinion extraction

### C.5: Prompt Design Principles

#### Few-Shot Examples

Create 15-20 hand-annotated examples covering all norm types from your ontology:

```python
# src/parsing/prompts/few_shot_examples.py

FEW_SHOT_EXAMPLES = [
    {
        'provision_id': 'example-1',
        'provision_text': '''
        The Administrator of the Environmental Protection Agency shall establish
        national ambient air quality standards for each air pollutant specified
        in the Clean Air Act, giving consideration to health effects and
        secondary effects. The Administrator may promulgate revised standards
        if the health evidence warrants.
        ''',
        'expected_extraction': {
            'norms': [
                {
                    'id': 'norm-1',
                    'deontic_operator': 'SHALL',
                    'subject': 'Administrator of the EPA',
                    'action': 'establish',
                    'object': 'national ambient air quality standards',
                    'conditions': [
                        'for each air pollutant specified in the Clean Air Act'
                    ],
                    'consequences': [
                        'the specified pollutant will have enforceable standards',
                        'states must maintain compliance with the standards'
                    ],
                    'authority': 'EPA Administrator (delegated from Congress)',
                    'defeasible': False,
                    'confidence': 0.95
                },
                {
                    'id': 'norm-2',
                    'deontic_operator': 'MAY',
                    'subject': 'Administrator of the EPA',
                    'action': 'promulgate',
                    'object': 'revised standards',
                    'conditions': [
                        'the health evidence warrants'
                    ],
                    'consequences': [
                        'existing standards may be updated',
                        'compliance obligations may change'
                    ],
                    'authority': 'EPA Administrator discretion',
                    'defeasible': True,  # Discretionary authority
                    'confidence': 0.88
                }
            ]
        }
    },
    # 14-19 more examples covering:
    # - Prohibition norms (SHALL NOT)
    # - Permission norms (MAY)
    # - Obligation norms (MUST)
    # - Complex conditions and exceptions
    # - Court interpretation examples
    # - Multi-party norms
    # - Defeasible/conditional norms
]
```

#### Annotation Guidelines

```
## Annotation Guidelines for Norm Extraction

### Deontic Operators

1. **SHALL** (mandatory positive obligation)
   - Indicates legal requirement
   - Example: "The agency SHALL issue regulations"
   - Confidence: High (95%+)

2. **SHALL NOT** (mandatory prohibition)
   - Indicates prohibition/forbidden action
   - Example: "No person shall discharge pollution"
   - Confidence: High (95%+)

3. **MAY** (permission/discretion)
   - Indicates permissible action or agency discretion
   - Example: "The Secretary may grant exceptions"
   - Confidence: Medium (75-85%)

4. **MUST** (similar to SHALL, varies by jurisdiction)
   - Generally mandatory in federal law
   - Example: "Applicants MUST submit certification"

### Conditions
- Extract temporal conditions (e.g., "within 30 days")
- Extract contingent conditions (e.g., "if the applicant fails to...")
- Extract applicability conditions (e.g., "for facilities with capacity >X")

### Exceptions
- Explicitly stated exceptions ("except that...", "provided that...")
- Implicit exceptions from related provisions
- Flag exceptions that need cross-reference resolution

### Confidence Scoring
- 95%+: Unambiguous norm, clear deontic operator
- 85-94%: Clear norm, minor ambiguity in scope
- 75-84%: Extraction plausible, some uncertainty in interpretation
- <75%: Requires human review (queue for human review)

### Defeasibility
Mark as defeasible (True) if:
- Norm is explicitly described as overridable
- Norm uses permissive language ("may be", "unless")
- Norm is from a discretionary delegation
- Judicial interpretation has limited this norm

Mark as non-defeasible (False) if:
- Norm is mandatory and absolute
- No exceptions or overrides are mentioned
- Norm is foundational/constitutional in nature
```

### C.6: Quality Assurance

**Gold Standard Creation**:
1. Manually extract norms from 20 representative provisions
   - 5 from USC (environmental law)
   - 5 from CFR (agency regulations)
   - 5 from NY law (state law variation)
   - 5 from court opinions

2. Have 2-3 legal experts review independently
3. Build consensus annotations

**Accuracy Metrics**:
- **Deontic operator recall**: % of norms correctly identified as SHALL/MAY/etc
  - Target: 85%+
- **Relationship extraction accuracy**: % of condition/consequence/exception relationships correctly extracted
  - Target: 75%+
- **Entity identification precision**: % of correctly identified subjects/objects
  - Target: 80%+
- **False positive rate**: % of extracted norms that are spurious
  - Target: <5%

**Evaluation Process**:
1. Extract on gold standard
2. Compare model output vs. consensus annotations
3. Calculate precision/recall/F1 per metric
4. Analyze error patterns
5. Iterate prompt + few-shot examples
6. Repeat until metrics meet targets

### C.7: Infrastructure & Storage

**PostgreSQL Schema**:
```sql
-- Job tracking
CREATE TABLE parsing_jobs (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(255) UNIQUE NOT NULL,
    batch_id VARCHAR(255),
    status VARCHAR(50) NOT NULL,  -- 'pending', 'processing', 'completed', 'failed'
    provisions_total INT,
    provisions_completed INT,
    provisions_errored INT,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- Extracted norms
CREATE TABLE extracted_norms (
    id SERIAL PRIMARY KEY,
    provision_id VARCHAR(255) UNIQUE NOT NULL,
    norms JSONB NOT NULL,  -- Array of norm objects
    confidence_score FLOAT,
    status VARCHAR(50),
    batch_id VARCHAR(255),
    tokens_used JSONB,  -- {input, output, cache_read, cache_creation}
    created_at TIMESTAMP DEFAULT NOW()
);

-- Human review queue
CREATE TABLE human_review_queue (
    id SERIAL PRIMARY KEY,
    provision_id VARCHAR(255) NOT NULL,
    extraction JSONB,
    confidence_score FLOAT,
    reason VARCHAR(255),  -- 'low_confidence', 'parse_error', 'contradiction'
    status VARCHAR(50),  -- 'pending_review', 'reviewed', 'approved', 'rejected'
    reviewer_id INT,
    reviewer_feedback TEXT,
    reviewed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- RDF/OWL triples (canonical storage)
CREATE TABLE rdf_triples (
    id SERIAL PRIMARY KEY,
    subject VARCHAR(255) NOT NULL,
    predicate VARCHAR(255) NOT NULL,
    object TEXT NOT NULL,
    object_type VARCHAR(50),  -- 'literal', 'uri', 'bnode'
    source_provision_id VARCHAR(255),
    confidence_score FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(subject, predicate, object)
);
```

**RDF Triple Store** (Apache Jena Fuseki):
- Every extracted norm becomes RDF triples
- Example:
  ```
  <norm/usc_42_7602_1> rdf:type norm:DeonticNorm ;
    norm:deonticOperator "SHALL" ;
    norm:subject <entity/epa_administrator> ;
    norm:action <action/establish> ;
    norm:object <entity/air_quality_standards> ;
    norm:appliesTo <statute/clean_air_act> ;
    norm:confidence 0.95 ;
    norm:sourceProvision "42 U.S.C. § 7602(1)" .
  ```

---

## Part D: Execution Timeline

**Total Duration**: 40 weeks
**Parallel Tracks**: Data gathering + ontology finalization happens concurrently with prompt development

### Weeks 1-6: Data Acquisition & Ontology Finalization

| Week | Task | Owner | Deliverables |
|------|------|-------|---------------|
| 1-2 | Set up data storage; implement BaseDataAgent | Eng | Base class, logging framework, 3 sample agents |
| 2-4 | Implement remaining data agents (US Code, CFR, etc.) | Eng | All 10 data agents operational |
| 4-5 | Finalize ontology schema (with legal domain expert) | Legal + Eng | Combined_Ontology_Schema.md (frozen) |
| 5-6 | Create annotation guidelines + 20 gold standard examples | Legal + Eng | Annotation_Guidelines.md, gold_standard.json |

**Parallel Effort**: Ontology refinement from user feedback

### Weeks 7-10: Structural & Definition Parsing

| Week | Task | Owner | Deliverables |
|------|------|-------|---------------|
| 7 | Implement Stage 1 (structural parsing) + tests | Eng | Structural parser, ~500 test documents parsed |
| 8 | Implement Stage 2 (definitions extraction) | Eng | Definitions extractor, definitions_index.json |
| 9 | Implement Stages 5-6 (entity resolution, validation) | Eng | Entity resolver, validation pipeline |
| 10 | Build context agents (Part B) | Eng | All 6 context agents, context JSON files |

**Deliverable**: Definitions index (15,000+ terms), cross-reference graph, entity map

### Weeks 11-16: Prompt Development & Testing

| Week | Task | Owner | Deliverables |
|------|------|-------|---------------|
| 11 | Draft normative extraction prompts | Legal + Eng | Initial system prompt, few-shot examples |
| 12-13 | Test on gold standard (iterative refinement) | Eng + Legal | Prompt v1 achieving 75%+ accuracy |
| 14 | Optimize for cost (tiered models, caching, batching) | Eng | Batch API integration, cost analysis |
| 15 | Build Batch API infrastructure (submission, polling, result handling) | Eng | Batch processor, job tracker |
| 16 | Final accuracy testing + prompts finalization | Legal + Eng | Prompt frozen; accuracy metrics documented |

**Key Metrics**: 85%+ deontic operator identification, 75%+ relationship extraction

### Weeks 17-30: Federal Corpus Extraction

| Week | Task | Owner | Timeline |
|------|------|-------|----------|
| 17-20 | Extract all USC titles (54 × ~2000 sections = 108K provisions) | Eng | Batches submitted; weekly monitoring |
| 21-24 | Extract CFR titles (50 × ~2000 sections = 100K provisions) | Eng | Batches submitted |
| 25-27 | Extract Federal Register recent (5 years), Executive Orders, Bills | Eng | ~20K additional documents |
| 28-30 | Court opinion extraction (9M opinions; sample representative cases) | Eng | ~100K high-authority opinions processed |

**Weekly Monitoring**: Job status, error rates, human review queue size
**Result**: ~230K federal norms extracted, confidence-scored, and stored in RDF

### Weeks 31-40: NY State + Refinement

| Week | Task | Owner | Timeline |
|------|------|-------|----------|
| 31-33 | Extract NY Consolidated Laws (70+ chapters, ~8K sections) | Eng | Full NY statute extraction |
| 34-35 | Extract NYC Admin Code (70 titles) + NY court interpretations | Eng | Full NYC + NY appellate coverage |
| 36 | NYCRR data gap remediation (scraping strategy TBD) | Eng | Gap analysis, scraping prototype if feasible |
| 37-38 | Quality assurance pass; human review of flagged items | Legal + Eng | Human review queue cleared |
| 39 | Final validation; RDF export for triple store | Eng | RDF dump, schema conformance check |
| 40 | Documentation + knowledge graph beta launch | Eng + PM | User guide, API documentation |

**Deliverable**: Complete knowledge graph with ~300K norms (federal + NY), accessible via:
- RDF SPARQL endpoint
- REST API (PostgreSQL → JSON)
- Web interface for search/browse

---

## Appendix: File Organization & Checkpointing

### Raw Data Storage
```
/data/raw/
  uscode/
    title_001/
      usc_001.xml
      usc_001.xml.metadata.json
    ...
    title_054/
    checkpoint.json          # Last run timestamp + processed items
    uscode_agent.log
  cfr/
  federal_register/
  court_opinions/
  ny_state/
  ...
```

### Context Data
```
/data/context/
  definitions_index.json           # All definitions with scope
  xref_graph.json                  # Cross-reference connectivity
  legislative_history.json         # Bill history + committee reports
  court_interpretations.json       # Citing cases per provision
  entity_consolidation.json        # Entity normalization mapping
  academic_databases_catalog.json  # Future integration sources
  checkpoint.json                  # Context agent state
```

### Extracted Norms
```
/data/extracted/
  uscode_norms.jsonl               # 1 JSON per line (newline-delimited)
  cfr_norms.jsonl
  federal_register_norms.jsonl
  court_norms.jsonl
  ny_state_norms.jsonl
  batch_jobs.json                  # Batch job tracking
  human_review_queue/
    provision_xyz.json             # Flagged for human review
    ...
  rdf_dump.ttl                     # Final RDF/Turtle export
```

### Checkpointing Strategy

Every agent saves checkpoint.json containing:
```json
{
  "last_successful_run": "2026-04-02T15:30:00Z",
  "processed_items": [
    "title_001",
    "title_002"
  ],
  "last_error": null,
  "total_items_processed": 54,
  "estimated_completion": "2026-04-03T10:00:00Z"
}
```

This enables:
- Resume from interruption without reprocessing
- Incremental updates (fetch only new items since last run)
- Progress tracking for users

---

## Cost Summary & ROI

**Total Estimated Cost**:
- API calls (Claude): ~$15,000-20,000
- Infrastructure (servers, storage): ~$5,000-8,000/month
- Labor (10 weeks eng + 8 weeks legal): ~$40,000-60,000
- **Total MVP: ~$65,000-95,000 (3 months)**

**Operational Cost** (monthly, post-launch):
- API incremental updates: ~$500-1,000/month
- Infrastructure: ~$5,000-8,000/month
- Maintenance: ~$3,000/month
- **Total: ~$8,500-12,000/month**

**ROI Drivers**:
- Automated legal research (vs. $200/hour attorneys)
- Policy compliance checking (automated gap detection)
- Legal tech licensing opportunities
- Government contracts (CRS, Legal Assistance Corp)

---

## Success Criteria

**Technical**:
- 85%+ precision in norm identification
- 75%+ accuracy in relationship extraction
- <5% false positive rate
- <$0.05 cost per provision (with optimization)

**Operational**:
- 100K provisions processed in <4 weeks
- Batch processing pipeline operational
- <2 hour mean time to resolution for errors
- RDF triple store queryable

**Strategic**:
- Complete federal + NY state coverage
- Court interpretation integration
- Ready for commercial legal applications
- Foundation for expanded practice areas

I'll continue with Part C covering the parsing pipeline architecture, API strategy, prompt design, and execution timeline in the next response.
