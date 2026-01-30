"""VHDB cache registry for version pinning.

This module provides a local cache for Virus-Host Database files,
enabling reproducible builds by pinning to specific versions.
"""

from virotaxa.cache.registry import (
    add_to_cache,
    cache_download,
    get_cached,
    list_cached,
    remove_cached,
)

__all__ = [
    "add_to_cache",
    "cache_download",
    "get_cached",
    "list_cached",
    "remove_cached",
]
