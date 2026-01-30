"""Tests for VHDB filtering functionality."""

import pandas as pd
import pytest

from virotaxa.vhdb.filters import (
    deduplicate_by_evidence,
    filter_bacteriophages,
    filter_by_host,
    filter_with_refseq,
)


class TestFilterByHost:
    """Tests for host filtering."""

    def test_clinical_mode_filters_human_only(self) -> None:
        """Clinical mode should only include human hosts."""
        df = pd.DataFrame({
            "virus_tax_id": [1, 2, 3],
            "virus_name": ["Virus A", "Virus B", "Virus C"],
            "host_tax_id": [9606, 10090, 9606],  # Human, Mouse, Human
            "host_lineage": [
                "Vertebrata; Mammalia; Homo",
                "Vertebrata; Mammalia; Mus",
                "Vertebrata; Mammalia; Homo",
            ],
        })

        result = filter_by_host(df, mode="clinical")
        assert len(result) == 2
        assert set(result["virus_tax_id"]) == {1, 3}

    def test_pandemic_mode_includes_vertebrates(self) -> None:
        """Pandemic mode should include all vertebrate hosts."""
        df = pd.DataFrame({
            "virus_tax_id": [1, 2, 3],
            "virus_name": ["Human virus", "Bat virus", "Insect virus"],
            "host_tax_id": [9606, 9397, 7227],
            "host_lineage": [
                "Vertebrata; Mammalia; Homo",
                "Vertebrata; Mammalia; Chiroptera",
                "Arthropoda; Insecta; Drosophila",
            ],
        })

        result = filter_by_host(df, mode="pandemic")
        assert len(result) == 2  # Human and Bat
        assert 7227 not in result["host_tax_id"].values

    def test_mammal_mode_includes_mammals(self) -> None:
        """Mammal mode should include mammalian hosts only."""
        df = pd.DataFrame({
            "virus_tax_id": [1, 2, 3],
            "virus_name": ["Human virus", "Bird virus", "Bat virus"],
            "host_tax_id": [9606, 9031, 9397],
            "host_lineage": [
                "Vertebrata; Mammalia; Homo",
                "Vertebrata; Aves; Gallus",
                "Vertebrata; Mammalia; Chiroptera",
            ],
        })

        result = filter_by_host(df, mode="mammal")
        assert len(result) == 2  # Human and Bat
        assert 9031 not in result["host_tax_id"].values

    def test_invalid_mode_raises_error(self) -> None:
        """Invalid mode should raise ValueError."""
        df = pd.DataFrame({"host_tax_id": [9606]})
        with pytest.raises(ValueError, match="Invalid mode"):
            filter_by_host(df, mode="invalid")


class TestFilterBacteriophages:
    """Tests for bacteriophage filtering."""

    def test_filters_siphovirus_morphotype(self) -> None:
        """Siphovirus entries should be filtered."""
        df = pd.DataFrame({
            "virus_name": ["Siphovirus contig89", "Zika virus"],
            "virus_lineage": [
                "Viruses; Caudoviricetes; unclassified",
                "Viruses; Flaviviridae; Flavivirus",
            ],
        })

        result = filter_bacteriophages(df, exclude=True)
        assert len(result) == 1
        assert result.iloc[0]["virus_name"] == "Zika virus"

    def test_filters_by_family(self) -> None:
        """Known phage families should be filtered."""
        df = pd.DataFrame({
            "virus_name": ["Lambda phage", "Influenza A"],
            "virus_lineage": [
                "Viruses; Siphoviridae",
                "Viruses; Orthomyxoviridae",
            ],
        })

        result = filter_bacteriophages(df, exclude=True)
        assert len(result) == 1
        assert result.iloc[0]["virus_name"] == "Influenza A"

    def test_keep_phages_option(self) -> None:
        """exclude=False should keep only phages."""
        df = pd.DataFrame({
            "virus_name": ["Lambda phage", "Influenza A"],
            "virus_lineage": [
                "Viruses; Siphoviridae",
                "Viruses; Orthomyxoviridae",
            ],
        })

        result = filter_bacteriophages(df, exclude=False)
        assert len(result) == 1
        assert result.iloc[0]["virus_name"] == "Lambda phage"


class TestFilterWithRefseq:
    """Tests for RefSeq filtering."""

    def test_keeps_entries_with_refseq(self) -> None:
        """Should keep entries with RefSeq IDs."""
        df = pd.DataFrame({
            "virus_name": ["Virus A", "Virus B", "Virus C"],
            "refseq_id": ["NC_001802.1", "", None],
        })

        result = filter_with_refseq(df)
        assert len(result) == 1
        assert result.iloc[0]["virus_name"] == "Virus A"


class TestDeduplicateByEvidence:
    """Tests for evidence-based deduplication."""

    def test_prefers_literature_evidence(self) -> None:
        """Literature evidence should be preferred."""
        df = pd.DataFrame({
            "virus_tax_id": [1, 1],
            "virus_name": ["HIV", "HIV"],
            "evidence": ["RefSeq", "Literature"],
            "host_tax_id": [9606, 9606],
        })

        result = deduplicate_by_evidence(df)
        assert len(result) == 1
        assert result.iloc[0]["evidence"] == "Literature"

    def test_prefers_human_host(self) -> None:
        """Human host entries should be preferred."""
        df = pd.DataFrame({
            "virus_tax_id": [1, 1],
            "virus_name": ["Virus", "Virus"],
            "evidence": ["RefSeq", "RefSeq"],
            "host_tax_id": [9397, 9606],  # Bat, Human
        })

        result = deduplicate_by_evidence(df, prefer_human=True)
        assert len(result) == 1
        assert result.iloc[0]["host_tax_id"] == 9606
