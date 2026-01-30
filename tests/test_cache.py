"""Tests for VHDB cache registry."""

import json
from pathlib import Path

import pytest

from virotaxa.cache.registry import (
    add_to_cache,
    get_cached,
    list_cached,
    remove_cached,
)


class TestCacheRegistry:
    """Tests for cache registry functionality."""

    def test_add_and_list(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Adding a file should make it listable."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        monkeypatch.setattr("virotaxa.cache.registry.DEFAULT_CACHE_DIR", cache_dir)

        # Create test file
        test_file = tmp_path / "test_vhdb.tsv"
        test_file.write_text("col1\tcol2\nval1\tval2\n")

        # Add to cache
        file_hash = add_to_cache(test_file)
        assert len(file_hash) == 64  # SHA256 hex

        # List should show it
        versions = list_cached()
        assert len(versions) == 1
        assert versions[0]["hash"] == file_hash

    def test_get_by_prefix(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should retrieve by hash prefix."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        monkeypatch.setattr("virotaxa.cache.registry.DEFAULT_CACHE_DIR", cache_dir)

        test_file = tmp_path / "test.tsv"
        test_file.write_text("content\n")
        file_hash = add_to_cache(test_file)

        # Get by prefix
        cached_path = get_cached(file_hash[:8])
        assert cached_path is not None
        assert cached_path.exists()
        assert cached_path.read_text() == "content\n"

    def test_get_not_found(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should return None for unknown hash."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        monkeypatch.setattr("virotaxa.cache.registry.DEFAULT_CACHE_DIR", cache_dir)

        result = get_cached("abcd1234")
        assert result is None

    def test_prefix_too_short(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should raise for prefix < 8 chars."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        monkeypatch.setattr("virotaxa.cache.registry.DEFAULT_CACHE_DIR", cache_dir)

        with pytest.raises(ValueError, match="at least 8"):
            get_cached("abc")

    def test_remove(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should remove cached version."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        monkeypatch.setattr("virotaxa.cache.registry.DEFAULT_CACHE_DIR", cache_dir)

        test_file = tmp_path / "test.tsv"
        test_file.write_text("content\n")
        file_hash = add_to_cache(test_file)

        assert len(list_cached()) == 1

        result = remove_cached(file_hash[:8])
        assert result is True
        assert len(list_cached()) == 0

    def test_remove_not_found(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Removing nonexistent should return False."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        monkeypatch.setattr("virotaxa.cache.registry.DEFAULT_CACHE_DIR", cache_dir)

        result = remove_cached("abcd1234abcd")
        assert result is False

    def test_preserves_metadata(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should preserve download metadata."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        monkeypatch.setattr("virotaxa.cache.registry.DEFAULT_CACHE_DIR", cache_dir)

        # Create file with metadata
        test_file = tmp_path / "test.tsv"
        test_file.write_text("content\n")

        metadata_file = tmp_path / "test.metadata.json"
        metadata_file.write_text(json.dumps({
            "download_timestamp": "2026-01-29T10:00:00Z",
            "sha256": "dummy",
        }))

        file_hash = add_to_cache(test_file)

        versions = list_cached()
        assert versions[0]["download_timestamp"] == "2026-01-29T10:00:00Z"
