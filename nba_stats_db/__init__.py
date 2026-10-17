"""
nba_stats_db - A robust NBA stats database powered by nba_api, SQLite, and curl_cffi.
"""

# Safeguard for Windows ctypes threadpoolctl DLL symbol inspection
try:
    import threadpoolctl
    _orig_make = threadpoolctl._ThreadpoolInfo._make_module_from_path

    def _safe_make(self, filepath):
        try:
            return _orig_make(self, filepath)
        except Exception:
            return None

    threadpoolctl._ThreadpoolInfo._make_module_from_path = _safe_make
except Exception:
    pass

from .client import configure_nba_api_client
from .database import NBADatabase
from .ingestion import NBADataIngestor
from .queries import NBAQueryHelper

__all__ = [
    "configure_nba_api_client",
    "NBADatabase",
    "NBADataIngestor",
    "NBAQueryHelper",
]
