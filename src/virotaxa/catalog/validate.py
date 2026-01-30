"""Catalog validation functionality.

Provides functions for validating catalogs against their metadata
to verify reproducibility.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from virotaxa.vhdb.download import compute_file_hash

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of catalog validation."""

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info: dict[str, str] = field(default_factory=dict)


def validate_catalog(catalog_path: Path | str) -> ValidationResult:
    """Validate a catalog file against its metadata.

    Performs the following checks:
    - Catalog file exists and is readable
    - Metadata file exists
    - Catalog statistics match metadata (virus count, family count)
    - Source VHDB hash matches if source file exists

    Args:
        catalog_path: Path to catalog TSV file

    Returns:
        ValidationResult with is_valid flag, errors, warnings, and info

    Example:
        >>> result = validate_catalog("catalog.tsv")
        >>> if result.is_valid:
        ...     print("Catalog is valid!")
        >>> else:
        ...     for error in result.errors:
        ...         print(f"Error: {error}")
    """
    catalog_path = Path(catalog_path)
    result = ValidationResult(is_valid=True)

    # Check catalog file exists
    if not catalog_path.exists():
        result.errors.append(f"Catalog file not found: {catalog_path}")
        result.is_valid = False
        return result

    # Check metadata file exists
    metadata_path = catalog_path.with_suffix(".metadata.json")
    if not metadata_path.exists():
        result.errors.append(f"Metadata file not found: {metadata_path}")
        result.is_valid = False
        return result

    # Load metadata
    try:
        with open(metadata_path) as f:
            metadata = json.load(f)
    except json.JSONDecodeError as e:
        result.errors.append(f"Invalid metadata JSON: {e}")
        result.is_valid = False
        return result

    # Load catalog
    try:
        catalog = pd.read_csv(catalog_path, sep="\t")
    except Exception as e:
        result.errors.append(f"Failed to parse catalog: {e}")
        result.is_valid = False
        return result

    # Store info
    result.info["catalog_rows"] = str(len(catalog))
    result.info["metadata_version"] = metadata.get("_version", "unknown")

    # Verify virus count matches
    expected_count = metadata.get("statistics", {}).get("total_taxa")
    if expected_count is not None:
        if len(catalog) != expected_count:
            result.errors.append(
                f"Taxa count mismatch: catalog has {len(catalog)}, "
                f"metadata says {expected_count}"
            )
            result.is_valid = False
        else:
            result.info["taxa_count_verified"] = "yes"

    # Verify family count matches
    expected_families = metadata.get("statistics", {}).get("unique_families")
    if expected_families is not None:
        actual_families = catalog["family"].nunique()
        if actual_families != expected_families:
            result.warnings.append(
                f"Family count mismatch: {actual_families} vs {expected_families}"
            )
        else:
            result.info["family_count_verified"] = "yes"

    # Check source VHDB hash if available
    source_info = metadata.get("source", {})
    source_path_str = source_info.get("file_path")
    source_hash = source_info.get("file_sha256")

    if source_path_str and source_hash:
        source_path = Path(source_path_str)
        if source_path.exists():
            actual_hash = compute_file_hash(source_path)
            if actual_hash == source_hash:
                result.info["source_hash_verified"] = "yes"
            else:
                result.warnings.append(
                    "Source VHDB has changed since catalog was generated"
                )
        else:
            result.warnings.append(f"Source VHDB not found: {source_path}")
            result.info["recorded_source_hash"] = source_hash[:16] + "..."

    # Store generation info
    gen_info = metadata.get("generation", {})
    if gen_info:
        result.info["generated_at"] = gen_info.get("timestamp", "unknown")
        result.info["virotaxa_version"] = gen_info.get("virotaxa_version", "unknown")

    # Store parameters
    params = metadata.get("parameters", {})
    if params:
        result.info["mode"] = params.get("mode", "unknown")
        result.info["exclude_bacteriophages"] = str(
            params.get("exclude_bacteriophages", "unknown")
        )

    return result
