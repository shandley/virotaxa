"""Taxonomy parsing functionality for Virus-Host Database.

Provides functions for extracting taxonomic information from virus lineage
strings and parsing RefSeq IDs.
"""

import re

import pandas as pd


def extract_taxonomy(lineage: str | None) -> dict[str, str | None]:
    """Extract taxonomic ranks from lineage string.

    Parses the semicolon-separated lineage string to extract standard
    viral taxonomy ranks based on ICTV suffixes.

    Args:
        lineage: Semicolon-separated taxonomic lineage

    Returns:
        Dict with family, order, class, phylum keys

    Example:
        >>> lineage = "Viruses; Riboviria; Orthornavirae; Flaviviridae; Flavivirus"
        >>> taxonomy = extract_taxonomy(lineage)
        >>> print(taxonomy["family"])  # "Flaviviridae"
    """
    result: dict[str, str | None] = {
        "family": None,
        "order": None,
        "class": None,
        "phylum": None,
    }

    if pd.isna(lineage) or not lineage:
        return result

    # Lineage format: "Viruses; Riboviria; ...; Flaviviridae; Flavivirus"
    parts = [p.strip() for p in lineage.split(";")]

    # Find taxonomic ranks by suffix
    for part in parts:
        if part.endswith("viridae"):
            result["family"] = part
        elif part.endswith("virales"):
            result["order"] = part
        elif part.endswith("viricetes"):
            result["class"] = part
        elif part.endswith("viricota"):
            result["phylum"] = part

    return result


def parse_refseq_ids(refseq_field: str | None) -> list[str]:
    """Parse RefSeq ID field which may contain multiple accessions.

    The refseq_id field can contain comma or semicolon-separated accessions.
    Virus-Host DB uses commas for multi-segment viruses.

    Args:
        refseq_field: RefSeq ID field value

    Returns:
        List of individual RefSeq accessions

    Example:
        >>> parse_refseq_ids("NC_001802.1;NC_001803.1")
        ['NC_001802.1', 'NC_001803.1']
        >>> parse_refseq_ids("NC_001802.1, NC_001803.1")
        ['NC_001802.1', 'NC_001803.1']
    """
    if pd.isna(refseq_field) or not refseq_field:
        return []

    # Split on comma or semicolon and strip whitespace
    accessions = [acc.strip() for acc in re.split(r"[,;]", str(refseq_field))]
    return [acc for acc in accessions if acc]
