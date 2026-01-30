"""Download functionality for Virus-Host Database.

Provides functions for downloading the VHDB TSV file with metadata tracking
for reproducibility.
"""

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any

import httpx

from virotaxa.constants import VHDB_URL

logger = logging.getLogger(__name__)


def download_vhdb(
    output_path: Path | str,
    timeout: float = 60.0,
    save_metadata: bool = True,
) -> Path:
    """Download the latest Virus-Host Database TSV file.

    Downloads the VHDB and optionally saves metadata for reproducibility tracking.
    Metadata includes download timestamp, file hash, and HTTP headers.

    Args:
        output_path: Path to save the downloaded file
        timeout: HTTP request timeout in seconds
        save_metadata: If True, save metadata JSON alongside the TSV file

    Returns:
        Path to downloaded file

    Example:
        >>> path = download_vhdb("data/vhdb.tsv")
        >>> print(f"Downloaded to {path}")
    """
    output_path = Path(output_path)
    logger.info(f"Downloading Virus-Host Database from {VHDB_URL}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    download_timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        response = client.get(VHDB_URL)
        response.raise_for_status()

        # Save the TSV file
        with open(output_path, "wb") as f:
            f.write(response.content)

        # Compute hash of downloaded content
        file_hash = hashlib.sha256(response.content).hexdigest()
        file_size_bytes = len(response.content)

        # Capture HTTP headers for versioning info
        http_headers = {
            "last_modified": response.headers.get("last-modified"),
            "etag": response.headers.get("etag"),
            "content_length": response.headers.get("content-length"),
            "date": response.headers.get("date"),
        }

    logger.info(f"Downloaded {file_size_bytes / 1024 / 1024:.1f} MB to {output_path}")
    logger.info(f"File SHA256: {file_hash}")

    # Save metadata for reproducibility
    if save_metadata:
        metadata = {
            "_description": "Virus-Host Database download metadata for reproducibility",
            "url": VHDB_URL,
            "download_timestamp": download_timestamp,
            "file_path": str(output_path),
            "file_size_bytes": file_size_bytes,
            "file_size_mb": round(file_size_bytes / 1024 / 1024, 2),
            "sha256": file_hash,
            "http_headers": http_headers,
        }
        metadata_path = output_path.with_suffix(".metadata.json")
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        logger.info(f"Saved download metadata to {metadata_path}")

    return output_path


def get_vhdb_metadata(tsv_path: Path | str) -> dict[str, Any] | None:
    """Load metadata for a Virus-Host Database file if available.

    Args:
        tsv_path: Path to the VHDB TSV file

    Returns:
        Metadata dict or None if not found

    Example:
        >>> metadata = get_vhdb_metadata("data/vhdb.tsv")
        >>> if metadata:
        ...     print(f"Downloaded: {metadata['download_timestamp']}")
    """
    tsv_path = Path(tsv_path)
    metadata_path = tsv_path.with_suffix(".metadata.json")
    if metadata_path.exists():
        with open(metadata_path) as f:
            return json.load(f)
    return None


def compute_file_hash(file_path: Path | str, algorithm: str = "sha256") -> str:
    """Compute hash of a file for integrity verification.

    Args:
        file_path: Path to the file
        algorithm: Hash algorithm (default: sha256)

    Returns:
        Hex-encoded hash string

    Example:
        >>> hash_value = compute_file_hash("data/vhdb.tsv")
        >>> print(f"SHA256: {hash_value[:16]}...")
    """
    file_path = Path(file_path)
    hash_obj = hashlib.new(algorithm)
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()
