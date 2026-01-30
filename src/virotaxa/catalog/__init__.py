"""Catalog generation and management.

This module provides functionality for building viral taxa catalogs
from the Virus-Host Database with full metadata tracking.
"""

from virotaxa.catalog.builder import build_catalog, save_catalog
from virotaxa.catalog.metadata import generate_metadata, get_environment_info
from virotaxa.catalog.validate import validate_catalog

__all__ = [
    "build_catalog",
    "generate_metadata",
    "get_environment_info",
    "save_catalog",
    "validate_catalog",
]
