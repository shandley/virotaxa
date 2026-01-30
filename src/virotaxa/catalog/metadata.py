"""Metadata generation for catalog reproducibility.

Provides functions for generating comprehensive metadata that tracks
all parameters needed to reproduce a catalog.
"""

import platform
import time
from pathlib import Path
from typing import Any

import pandas as pd

from virotaxa.constants import (
    BACTERIOPHAGE_FAMILIES,
    HUMAN_TAXID,
    MODE_CLINICAL,
)
from virotaxa.vhdb.download import compute_file_hash, get_vhdb_metadata


def get_environment_info() -> dict[str, Any]:
    """Get environment information for reproducibility tracking.

    Returns:
        Dict with Python version, platform, and key dependency versions

    Example:
        >>> env = get_environment_info()
        >>> print(f"Python: {env['python_version']}")
    """
    env_info: dict[str, Any] = {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "dependencies": {},
    }

    # Get versions of key dependencies
    dependencies = ["pandas", "httpx"]
    for dep in dependencies:
        try:
            import importlib.metadata

            env_info["dependencies"][dep] = importlib.metadata.version(dep)
        except Exception:
            env_info["dependencies"][dep] = "unknown"

    return env_info


def generate_metadata(
    catalog: pd.DataFrame,
    source_path: Path,
    mode: str,
    exclude_bacteriophages: bool,
    virotaxa_version: str = "0.1.0",
) -> dict[str, Any]:
    """Generate metadata for a virus catalog for reproducibility tracking.

    Args:
        catalog: The generated catalog DataFrame
        source_path: Path to the source VHDB file
        mode: Catalog mode used (clinical, pandemic, or mammal)
        exclude_bacteriophages: Whether bacteriophages were excluded
        virotaxa_version: Version of virotaxa used

    Returns:
        Metadata dictionary suitable for JSON serialization

    Example:
        >>> metadata = generate_metadata(catalog, vhdb_path, "clinical", True)
        >>> with open("catalog.metadata.json", "w") as f:
        ...     json.dump(metadata, f, indent=2)
    """
    # Try to load source VHDB metadata if available
    vhdb_metadata = get_vhdb_metadata(source_path)

    # Compute source file hash for reproducibility
    source_hash = compute_file_hash(source_path) if source_path.exists() else None

    # Calculate statistics
    evidence_counts = catalog["evidence"].value_counts().to_dict()
    family_counts = catalog["family"].value_counts().to_dict()
    total_refseq = catalog["refseq_ids"].apply(len).sum()

    # Get environment info
    env_info = get_environment_info()

    # Build mode description
    mode_descriptions = {
        "clinical": "Human hosts only (clinical diagnostics)",
        "pandemic": "All vertebrate hosts (pandemic preparedness)",
        "mammal": "Mammalian hosts only (zoonotic focus)",
    }

    metadata: dict[str, Any] = {
        "_description": "Virotaxa catalog metadata for reproducibility",
        "_version": "1.0",
        "generation": {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "virotaxa_version": virotaxa_version,
        },
        "environment": env_info,
        "source": {
            "file_path": str(source_path),
            "file_sha256": source_hash,
            "vhdb_metadata": vhdb_metadata,
        },
        "parameters": {
            "mode": mode,
            "mode_description": mode_descriptions.get(mode, "Unknown mode"),
            "exclude_bacteriophages": exclude_bacteriophages,
            "human_taxid": HUMAN_TAXID,
            "bacteriophage_families_excluded": len(BACTERIOPHAGE_FAMILIES),
        },
        "filters_applied": {
            "host_filter": "human_only" if mode == MODE_CLINICAL else mode,
            "requires_refseq": True,
            "evidence_priority": ["Literature", "RefSeq", "UniProt"],
        },
        "statistics": {
            "total_taxa": len(catalog),
            "unique_families": catalog["family"].nunique(),
            "total_refseq_entries": int(total_refseq),
            "evidence_distribution": evidence_counts,
            "top_families": dict(list(family_counts.items())[:10]),
        },
        "reproducibility": {
            "commands": [
                f"virotaxa download -o {source_path}",
                f"virotaxa catalog build {source_path} --mode {mode} "
                + ("--exclude-bacteriophages" if exclude_bacteriophages else "--include-bacteriophages")
                + " -o <output.tsv>",
            ],
            "requirements": [
                f"virotaxa=={virotaxa_version}",
                f"python>={env_info['python_version'][:4]}",
            ],
            "verification": "virotaxa catalog validate <output.tsv>",
        },
    }

    return metadata
