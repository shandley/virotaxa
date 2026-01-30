"""VHDB cache registry implementation.

Provides functions for caching VHDB files by SHA256 hash for version pinning
and reproducible catalog generation.
"""

import json
import logging
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any

from virotaxa.constants import DEFAULT_CACHE_DIR
from virotaxa.vhdb.download import compute_file_hash, download_vhdb, get_vhdb_metadata

logger = logging.getLogger(__name__)


def _get_cache_dir() -> Path:
    """Get the VHDB cache directory, creating it if necessary.

    Returns:
        Path to the cache directory
    """
    cache_dir = DEFAULT_CACHE_DIR
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _get_registry_path() -> Path:
    """Get the path to the cache registry file.

    Returns:
        Path to registry.json
    """
    return _get_cache_dir() / "registry.json"


def _load_registry() -> dict[str, Any]:
    """Load the cache registry from disk.

    Returns:
        Registry dict mapping hashes to metadata
    """
    registry_path = _get_registry_path()
    if registry_path.exists():
        with open(registry_path) as f:
            return json.load(f)
    return {"_version": "1.0", "entries": {}}


def _save_registry(registry: dict[str, Any]) -> None:
    """Save the cache registry to disk.

    Args:
        registry: Registry dict to save
    """
    registry_path = _get_registry_path()
    with open(registry_path, "w") as f:
        json.dump(registry, f, indent=2)


def add_to_cache(
    vhdb_path: Path | str,
    metadata: dict[str, Any] | None = None,
) -> str:
    """Add a VHDB file to the version cache.

    Copies the file to the cache directory and registers it by hash.

    Args:
        vhdb_path: Path to the VHDB TSV file
        metadata: Optional metadata dict (will load from .metadata.json if not provided)

    Returns:
        SHA256 hash of the cached file

    Example:
        >>> hash_value = add_to_cache("data/vhdb.tsv")
        >>> print(f"Cached with hash: {hash_value[:12]}")
    """
    vhdb_path = Path(vhdb_path)

    if not vhdb_path.exists():
        raise FileNotFoundError(f"VHDB file not found: {vhdb_path}")

    # Compute hash
    file_hash = compute_file_hash(vhdb_path)

    # Get or create cache directory
    cache_dir = _get_cache_dir()
    cached_file = cache_dir / f"vhdb_{file_hash[:12]}.tsv"

    # Copy file if not already cached
    if not cached_file.exists():
        shutil.copy2(vhdb_path, cached_file)
        logger.info(f"Cached VHDB file as {cached_file.name}")

    # Load metadata if not provided
    if metadata is None:
        metadata = get_vhdb_metadata(vhdb_path)

    # Update registry
    registry = _load_registry()
    registry["entries"][file_hash] = {
        "filename": cached_file.name,
        "cached_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "file_size_bytes": cached_file.stat().st_size,
        "download_metadata": metadata,
    }
    _save_registry(registry)

    return file_hash


def list_cached() -> list[dict[str, Any]]:
    """List all cached VHDB versions.

    Returns:
        List of dicts with hash, filename, cached_at, and metadata

    Example:
        >>> for version in list_cached():
        ...     print(f"{version['short_hash']}: {version['cached_at']}")
    """
    registry = _load_registry()
    cache_dir = _get_cache_dir()

    versions = []
    for file_hash, entry in registry.get("entries", {}).items():
        cached_file = cache_dir / entry["filename"]
        if cached_file.exists():
            versions.append({
                "hash": file_hash,
                "short_hash": file_hash[:12],
                "filename": entry["filename"],
                "cached_at": entry.get("cached_at", "unknown"),
                "file_size_bytes": entry.get("file_size_bytes", 0),
                "download_timestamp": (
                    entry.get("download_metadata", {}).get("download_timestamp")
                    if entry.get("download_metadata")
                    else None
                ),
            })

    # Sort by cached_at descending (most recent first)
    versions.sort(key=lambda x: x.get("cached_at", ""), reverse=True)
    return versions


def get_cached(hash_prefix: str) -> Path | None:
    """Get a cached VHDB file by hash prefix.

    Args:
        hash_prefix: Full or partial (at least 8 chars) SHA256 hash

    Returns:
        Path to cached file, or None if not found

    Raises:
        ValueError: If hash prefix is ambiguous (matches multiple entries)
            or is too short (less than 8 characters)

    Example:
        >>> path = get_cached("7a3f2b1c")
        >>> if path:
        ...     catalog = build_catalog(path)
    """
    if len(hash_prefix) < 8:
        raise ValueError("Hash prefix must be at least 8 characters")

    registry = _load_registry()
    cache_dir = _get_cache_dir()

    matches = []
    for file_hash, entry in registry.get("entries", {}).items():
        if file_hash.startswith(hash_prefix):
            cached_file = cache_dir / entry["filename"]
            if cached_file.exists():
                matches.append((file_hash, cached_file))

    if len(matches) == 0:
        return None
    if len(matches) > 1:
        hash_list = ", ".join(h[:12] for h, _ in matches)
        raise ValueError(f"Ambiguous hash prefix '{hash_prefix}' matches: {hash_list}")

    return matches[0][1]


def remove_cached(hash_prefix: str) -> bool:
    """Remove a cached VHDB file by hash prefix.

    Args:
        hash_prefix: Full or partial (at least 8 chars) SHA256 hash

    Returns:
        True if removed, False if not found

    Raises:
        ValueError: If hash prefix is ambiguous or too short

    Example:
        >>> if remove_cached("7a3f2b1c"):
        ...     print("Removed successfully")
    """
    if len(hash_prefix) < 8:
        raise ValueError("Hash prefix must be at least 8 characters")

    registry = _load_registry()
    cache_dir = _get_cache_dir()

    matches = []
    for file_hash in registry.get("entries", {}).keys():
        if file_hash.startswith(hash_prefix):
            matches.append(file_hash)

    if len(matches) == 0:
        return False
    if len(matches) > 1:
        raise ValueError(f"Ambiguous hash prefix '{hash_prefix}'")

    # Remove file and registry entry
    full_hash = matches[0]
    entry = registry["entries"][full_hash]
    cached_file = cache_dir / entry["filename"]
    if cached_file.exists():
        cached_file.unlink()

    del registry["entries"][full_hash]
    _save_registry(registry)

    logger.info(f"Removed cached VHDB: {full_hash[:12]}")
    return True


def cache_download(timeout: float = 60.0) -> tuple[Path, str]:
    """Download VHDB and add to version cache.

    Downloads the latest VHDB and caches it for future reproducibility.

    Args:
        timeout: HTTP request timeout

    Returns:
        Tuple of (cached_file_path, hash)

    Example:
        >>> path, hash_value = cache_download()
        >>> print(f"Cached at {path} with hash {hash_value[:12]}")
    """
    # Download to temp location first
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir) / "vhdb.tsv"
        download_vhdb(tmp_path, timeout=timeout, save_metadata=True)

        # Add to cache
        file_hash = add_to_cache(tmp_path)

        # Get the cached path
        cached_path = get_cached(file_hash)
        if cached_path is None:
            raise RuntimeError("Failed to cache VHDB after download")

    return cached_path, file_hash
