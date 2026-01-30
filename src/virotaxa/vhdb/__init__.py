"""Virus-Host Database integration.

This module provides functionality for downloading, parsing, and filtering
the Virus-Host Database (https://www.genome.jp/virushostdb/).
"""

from virotaxa.vhdb.download import download_vhdb, get_vhdb_metadata
from virotaxa.vhdb.filters import (
    deduplicate_by_evidence,
    filter_bacteriophages,
    filter_by_host,
    filter_with_refseq,
)
from virotaxa.vhdb.parse import load_vhdb
from virotaxa.vhdb.taxonomy import extract_taxonomy, parse_refseq_ids

__all__ = [
    "deduplicate_by_evidence",
    "download_vhdb",
    "extract_taxonomy",
    "filter_bacteriophages",
    "filter_by_host",
    "filter_with_refseq",
    "get_vhdb_metadata",
    "load_vhdb",
    "parse_refseq_ids",
]
