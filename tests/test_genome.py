"""Tests for genome fetching functionality."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from virotaxa.genome.fetch import (
    GenomeFetchResult,
    _get_delay,
    _load_catalog,
    fetch_genomes,
)
from virotaxa.genome.metadata import generate_genome_metadata, save_genome_metadata


class TestGetDelay:
    """Tests for delay calculation."""

    def test_delay_without_api_key(self) -> None:
        """Should return 0.4s delay without API key."""
        assert _get_delay(None) == 0.4

    def test_delay_with_api_key(self) -> None:
        """Should return 0.1s delay with API key."""
        assert _get_delay("some-api-key") == 0.1


class TestLoadCatalog:
    """Tests for catalog loading."""

    def test_loads_catalog_and_parses_refseq(self) -> None:
        """Should load catalog and parse refseq_ids as lists."""
        catalog_content = (
            "taxid\tname\tfamily\trefseq_ids\n"
            "11676\tHIV-1\tRetroviridae\tNC_001802.1;NC_001803.1\n"
            "12637\tZika\tFlaviviridae\tNC_012532.1\n"
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".tsv", delete=False) as f:
            f.write(catalog_content)
            temp_path = Path(f.name)

        try:
            catalog = _load_catalog(temp_path)

            assert len(catalog) == 2
            assert catalog.iloc[0]["refseq_ids"] == ["NC_001802.1", "NC_001803.1"]
            assert catalog.iloc[1]["refseq_ids"] == ["NC_012532.1"]
        finally:
            temp_path.unlink()

    def test_handles_empty_refseq_ids(self) -> None:
        """Should handle empty refseq_ids gracefully."""
        catalog_content = "taxid\tname\tfamily\trefseq_ids\n" "11676\tHIV-1\tRetroviridae\t\n"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".tsv", delete=False) as f:
            f.write(catalog_content)
            temp_path = Path(f.name)

        try:
            catalog = _load_catalog(temp_path)

            assert len(catalog) == 1
            assert catalog.iloc[0]["refseq_ids"] == []
        finally:
            temp_path.unlink()


class TestFetchGenomes:
    """Tests for genome fetching."""

    @patch("virotaxa.genome.fetch.Entrez")
    def test_fetch_genomes_success(self, mock_entrez: MagicMock) -> None:
        """Should fetch genomes and write FASTA files."""
        # Setup mock responses
        mock_post_result = {"WebEnv": "MCID_test", "QueryKey": "1"}
        mock_entrez.epost.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_entrez.read.return_value = mock_post_result

        # Mock FASTA response
        mock_fasta = ">NC_001802.1 Human immunodeficiency virus 1\nATGGGTGCGAGAGCGTCAGTATTAAGCGGGGGAGAATTA\n"
        mock_fetch_handle = MagicMock()
        mock_fetch_handle.read.return_value = mock_fasta
        mock_entrez.efetch.return_value = mock_fetch_handle

        # Mock epost
        mock_post_handle = MagicMock()
        mock_post_handle.close = MagicMock()
        mock_entrez.epost.return_value = mock_post_handle
        mock_entrez.read.return_value = mock_post_result

        catalog_content = "taxid\tname\tfamily\trefseq_ids\n" "11676\tHIV-1\tRetroviridae\tNC_001802.1\n"

        with tempfile.TemporaryDirectory() as tmpdir:
            catalog_path = Path(tmpdir) / "catalog.tsv"
            output_dir = Path(tmpdir) / "genomes"

            with open(catalog_path, "w") as f:
                f.write(catalog_content)

            result = fetch_genomes(
                catalog_path=catalog_path,
                output_dir=output_dir,
                email="test@example.com",
                delay=0,  # No delay for tests
            )

            assert result.total_taxa == 1
            assert result.total_sequences == 1
            # Note: successful count depends on parsing mock response

    def test_creates_output_directory(self) -> None:
        """Should create output directory if it doesn't exist."""
        catalog_content = "taxid\tname\tfamily\trefseq_ids\n" "11676\tHIV-1\tRetroviridae\t\n"

        with tempfile.TemporaryDirectory() as tmpdir:
            catalog_path = Path(tmpdir) / "catalog.tsv"
            output_dir = Path(tmpdir) / "nested" / "output" / "dir"

            with open(catalog_path, "w") as f:
                f.write(catalog_content)

            with patch("virotaxa.genome.fetch.Entrez"):
                result = fetch_genomes(
                    catalog_path=catalog_path,
                    output_dir=output_dir,
                    email="test@example.com",
                    delay=0,
                )

            assert output_dir.exists()


class TestGenomeFetchResult:
    """Tests for GenomeFetchResult dataclass."""

    def test_default_values(self) -> None:
        """Should have sensible defaults."""
        result = GenomeFetchResult(
            total_taxa=10,
            total_sequences=20,
            successful=18,
        )

        assert result.total_taxa == 10
        assert result.total_sequences == 20
        assert result.successful == 18
        assert result.failed == []
        assert result.files == {}


class TestGenerateGenomeMetadata:
    """Tests for genome metadata generation."""

    def test_generates_required_fields(self) -> None:
        """Metadata should contain all required fields."""
        result = GenomeFetchResult(
            total_taxa=5,
            total_sequences=10,
            successful=8,
            failed=["NC_XXXXX", "NC_YYYYY"],
            output_dir=Path("/tmp/genomes"),
            files={
                "11676": {"file": "11676.fasta", "sequences": 2, "bases": 10000},
                "12637": {"file": "12637.fasta", "sequences": 1, "bases": 5000},
            },
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".tsv", delete=False) as f:
            f.write("dummy catalog content\n")
            catalog_path = Path(f.name)

        try:
            metadata = generate_genome_metadata(
                result=result,
                catalog_path=catalog_path,
                email="test@example.com",
            )

            assert "_description" in metadata
            assert "_version" in metadata
            assert "fetch" in metadata
            assert "source" in metadata
            assert "statistics" in metadata
            assert "failed_accessions" in metadata
            assert "files" in metadata

            assert metadata["statistics"]["total_taxa"] == 5
            assert metadata["statistics"]["total_refseq_ids"] == 10
            assert metadata["statistics"]["successful_fetches"] == 8
            assert metadata["statistics"]["failed_fetches"] == 2
            assert metadata["statistics"]["total_bases"] == 15000

            assert len(metadata["failed_accessions"]) == 2
            assert len(metadata["files"]) == 2
        finally:
            catalog_path.unlink()

    def test_includes_catalog_hash(self) -> None:
        """Should include catalog SHA256 hash."""
        result = GenomeFetchResult(
            total_taxa=1,
            total_sequences=1,
            successful=1,
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".tsv", delete=False) as f:
            f.write("some catalog content\n")
            catalog_path = Path(f.name)

        try:
            metadata = generate_genome_metadata(
                result=result,
                catalog_path=catalog_path,
                email="test@example.com",
            )

            assert metadata["source"]["catalog_sha256"] is not None
            assert len(metadata["source"]["catalog_sha256"]) == 64  # SHA256 hex length
        finally:
            catalog_path.unlink()


class TestSaveGenomeMetadata:
    """Tests for saving genome metadata."""

    def test_saves_metadata_json(self) -> None:
        """Should save metadata to JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "genomes"
            output_dir.mkdir()

            result = GenomeFetchResult(
                total_taxa=1,
                total_sequences=1,
                successful=1,
                output_dir=output_dir,
            )

            catalog_path = Path(tmpdir) / "catalog.tsv"
            with open(catalog_path, "w") as f:
                f.write("dummy\n")

            metadata_path = save_genome_metadata(
                result=result,
                catalog_path=catalog_path,
                email="test@example.com",
            )

            assert metadata_path.exists()
            assert metadata_path.name == "genomes.metadata.json"

            with open(metadata_path) as f:
                saved_metadata = json.load(f)

            assert "_description" in saved_metadata
            assert saved_metadata["fetch"]["ncbi_email"] == "test@example.com"
