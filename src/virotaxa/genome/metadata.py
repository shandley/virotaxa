"""Metadata generation for genome fetch operations.

Provides functions for generating comprehensive metadata that tracks
all parameters needed to reproduce a genome fetch operation.
"""

import json
import time
from pathlib import Path
from typing import Any

from virotaxa.genome.fetch import GenomeFetchResult
from virotaxa.vhdb.download import compute_file_hash


def generate_genome_metadata(
    result: GenomeFetchResult,
    catalog_path: Path,
    email: str,
    virotaxa_version: str = "0.1.0",
) -> dict[str, Any]:
    """Generate metadata for a genome fetch operation.

    Args:
        result: The GenomeFetchResult from fetch_genomes
        catalog_path: Path to the source catalog file
        email: Email used for NCBI access
        virotaxa_version: Version of virotaxa used

    Returns:
        Metadata dictionary suitable for JSON serialization

    Example:
        >>> metadata = generate_genome_metadata(result, catalog_path, email)
        >>> with open("genomes.metadata.json", "w") as f:
        ...     json.dump(metadata, f, indent=2)
    """
    # Compute source catalog hash
    catalog_hash = compute_file_hash(catalog_path) if catalog_path.exists() else None

    # Calculate total bases across all files
    total_bases = sum(f.get("bases", 0) for f in result.files.values())

    metadata: dict[str, Any] = {
        "_description": "Virotaxa genome fetch metadata",
        "_version": "1.0",
        "fetch": {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "virotaxa_version": virotaxa_version,
            "ncbi_email": email,
        },
        "source": {
            "catalog_path": str(catalog_path),
            "catalog_sha256": catalog_hash,
        },
        "statistics": {
            "total_taxa": result.total_taxa,
            "total_refseq_ids": result.total_sequences,
            "successful_fetches": result.successful,
            "failed_fetches": len(result.failed),
            "total_bases": total_bases,
        },
        "failed_accessions": result.failed,
        "files": result.files,
    }

    return metadata


def save_genome_metadata(
    result: GenomeFetchResult,
    catalog_path: Path,
    email: str,
    virotaxa_version: str | None = None,
) -> Path:
    """Generate and save metadata for a genome fetch operation.

    Args:
        result: The GenomeFetchResult from fetch_genomes
        catalog_path: Path to the source catalog file
        email: Email used for NCBI access
        virotaxa_version: Version of virotaxa used (defaults to installed version)

    Returns:
        Path to the saved metadata file

    Example:
        >>> meta_path = save_genome_metadata(result, catalog_path, email)
        >>> print(f"Saved metadata to {meta_path}")
    """
    from virotaxa import __version__

    if virotaxa_version is None:
        virotaxa_version = __version__

    metadata = generate_genome_metadata(
        result=result,
        catalog_path=catalog_path,
        email=email,
        virotaxa_version=virotaxa_version,
    )

    metadata_path = result.output_dir / "genomes.metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    return metadata_path
