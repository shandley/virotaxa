"""Tests for catalog building and validation."""

import json
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from virotaxa.catalog.builder import build_catalog
from virotaxa.catalog.metadata import generate_metadata, get_environment_info
from virotaxa.catalog.validate import validate_catalog


class TestBuildCatalog:
    """Tests for catalog building."""

    def test_builds_from_sample_data(self, sample_vhdb_data: str) -> None:
        """Should build catalog from sample VHDB data."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".tsv", delete=False) as f:
            f.write(sample_vhdb_data)
            temp_path = Path(f.name)

        try:
            catalog = build_catalog(temp_path, mode="clinical")

            # Should have HIV, Influenza, Zika (not phage, not bat virus)
            assert len(catalog) == 3
            assert "Human immunodeficiency virus 1" in catalog["name"].values
            assert "Siphovirus contig89" not in catalog["name"].values
        finally:
            temp_path.unlink()

    def test_pandemic_mode_includes_bat_virus(self, sample_vhdb_data: str) -> None:
        """Pandemic mode should include bat coronavirus."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".tsv", delete=False) as f:
            f.write(sample_vhdb_data)
            temp_path = Path(f.name)

        try:
            catalog = build_catalog(temp_path, mode="pandemic")

            # Should include bat coronavirus
            assert "Bat coronavirus HKU9" in catalog["name"].values
            # But still exclude phages
            assert "Siphovirus contig89" not in catalog["name"].values
        finally:
            temp_path.unlink()


class TestGenerateMetadata:
    """Tests for metadata generation."""

    def test_generates_required_fields(self) -> None:
        """Metadata should contain all required fields."""
        catalog = pd.DataFrame({
            "taxid": [1, 2],
            "name": ["Virus A", "Virus B"],
            "family": ["Familyviridae", "Familyviridae"],
            "order": [None, None],
            "refseq_ids": [["NC_001"], ["NC_002"]],
            "evidence": ["Literature", "RefSeq"],
            "pmid": [None, None],
        })

        with tempfile.NamedTemporaryFile(mode="w", suffix=".tsv", delete=False) as f:
            f.write("dummy\n")
            temp_path = Path(f.name)

        try:
            metadata = generate_metadata(
                catalog=catalog,
                source_path=temp_path,
                mode="clinical",
                exclude_bacteriophages=True,
            )

            assert "_version" in metadata
            assert "generation" in metadata
            assert "environment" in metadata
            assert "source" in metadata
            assert "parameters" in metadata
            assert "statistics" in metadata
            assert "reproducibility" in metadata

            assert metadata["statistics"]["total_taxa"] == 2
            assert metadata["parameters"]["mode"] == "clinical"
        finally:
            temp_path.unlink()


class TestGetEnvironmentInfo:
    """Tests for environment info collection."""

    def test_includes_python_version(self) -> None:
        """Should include Python version."""
        env = get_environment_info()
        assert "python_version" in env
        assert env["python_version"].startswith("3.")

    def test_includes_dependencies(self) -> None:
        """Should include dependency versions."""
        env = get_environment_info()
        assert "dependencies" in env
        assert "pandas" in env["dependencies"]


class TestValidateCatalog:
    """Tests for catalog validation."""

    def test_validates_correct_catalog(self) -> None:
        """Should pass validation for correct catalog."""
        catalog = pd.DataFrame({
            "taxid": [1, 2],
            "name": ["Virus A", "Virus B"],
            "family": ["Family1", "Family2"],
            "refseq_ids": ["NC_001", "NC_002"],
        })

        metadata = {
            "_version": "1.0",
            "statistics": {
                "total_taxa": 2,
                "unique_families": 2,
            },
            "generation": {
                "timestamp": "2026-01-29T12:00:00Z",
                "virotaxa_version": "0.1.0",
            },
            "parameters": {
                "mode": "clinical",
                "exclude_bacteriophages": True,
            },
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            catalog_path = Path(tmpdir) / "catalog.tsv"
            metadata_path = Path(tmpdir) / "catalog.metadata.json"

            catalog.to_csv(catalog_path, sep="\t", index=False)
            with open(metadata_path, "w") as f:
                json.dump(metadata, f)

            result = validate_catalog(catalog_path)

            assert result.is_valid
            assert len(result.errors) == 0

    def test_fails_on_count_mismatch(self) -> None:
        """Should fail if taxa count doesn't match."""
        catalog = pd.DataFrame({
            "taxid": [1],
            "name": ["Virus A"],
            "family": ["Family1"],
        })

        metadata = {
            "statistics": {"total_taxa": 5},  # Wrong count
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            catalog_path = Path(tmpdir) / "catalog.tsv"
            metadata_path = Path(tmpdir) / "catalog.metadata.json"

            catalog.to_csv(catalog_path, sep="\t", index=False)
            with open(metadata_path, "w") as f:
                json.dump(metadata, f)

            result = validate_catalog(catalog_path)

            assert not result.is_valid
            assert any("mismatch" in e.lower() for e in result.errors)
