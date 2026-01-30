"""Virotaxa: Reproducible viral taxa selection from Virus-Host Database.

Virotaxa provides tools for downloading, filtering, and cataloging viral taxa
from the Virus-Host Database (VHDB) with full reproducibility tracking.

Example:
    >>> from virotaxa import build_catalog, download_vhdb
    >>> vhdb_path = download_vhdb("data/vhdb.tsv")
    >>> catalog = build_catalog(vhdb_path, mode="clinical")
"""

__version__ = "0.1.0"

from virotaxa.catalog.builder import build_catalog, save_catalog
from virotaxa.vhdb.download import download_vhdb, get_vhdb_metadata

__all__ = [
    "__version__",
    "build_catalog",
    "download_vhdb",
    "get_vhdb_metadata",
    "save_catalog",
]
