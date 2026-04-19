import os
import tempfile

# Point both DBs and blob store at a throwaway tempdir BEFORE app import.
_tmp = tempfile.mkdtemp(prefix="lcp-test-")
os.environ["DATABASE_URL_CORPUS"] = f"sqlite:///{_tmp}/corpus.db"
os.environ["DATABASE_URL_PARSED"] = f"sqlite:///{_tmp}/parsed.db"
os.environ["BLOB_STORE_ROOT"] = f"{_tmp}/blobs"
