"""Catalog building functionality.

Provides the main functions for building viral taxa catalogs from VHDB.
"""

import logging
from pathlib import Path

import pandas as pd

from virotaxa.catalog.metadata import generate_metadata
from virotaxa.constants import MODE_CLINICAL, PRIMATE_MODE_NONE
from virotaxa.vhdb.filters import (
    deduplicate_by_evidence,
    filter_bacteriophages,
    filter_by_host,
    filter_with_refseq,
    get_primate_homologs,
)
from virotaxa.vhdb.parse import load_vhdb
from virotaxa.vhdb.taxonomy import extract_taxonomy, parse_refseq_ids

logger = logging.getLogger(__name__)


def build_catalog(
    vhdb_path: Path | str,
    mode: str = MODE_CLINICAL,
    exclude_bacteriophages: bool = True,
    primate_homologs: str = PRIMATE_MODE_NONE,
    primate_families: set[str] | None = None,
) -> pd.DataFrame:
    """Build a catalog of viruses with RefSeq sequences.

    This is the main entry point for viral taxa selection. Returns a DataFrame
    suitable for downstream analysis or probe design.

    Two catalog modes are supported:

    **Clinical mode** (default): Human hosts only
        - Includes only viruses with documented human infections
        - Suitable for clinical diagnostic panels
        - ~1,400 viruses

    **Pandemic mode**: All vertebrate hosts
        - Includes all vertebrate-infecting viruses
        - Captures pre-emergent zoonotic threats (bat coronaviruses, etc.)
        - Suitable for pandemic preparedness and surveillance
        - ~4,000+ viruses

    **Primate homologs**: Can augment any mode with non-human primate viruses
        - Improves capture of high-diversity viruses (HHV-8, HCMV, EBV, HPV)
        - "strict": Chimp/bonobo only (+66 viruses)
        - "extended": All non-human primates (+505 viruses)

    Args:
        vhdb_path: Path to virushostdb.tsv file
        mode: Catalog mode - "clinical" for human hosts only,
            "pandemic" for all vertebrate hosts, "mammal" for mammals only.
        exclude_bacteriophages: If True, remove bacteriophage families.
            Bacteriophages infect bacteria (not human cells) but appear in
            Virus-Host DB because they're detected in human microbiome samples.
        primate_homologs: Mode for including primate homologs - "none" (default),
            "strict" (chimp/bonobo), or "extended" (all non-human primates).
        primate_families: Optional set of viral families to include homologs for
            (e.g., {"Herpesviridae", "Papillomaviridae"}). If None, all families.

    Returns:
        DataFrame with columns: taxid, name, family, order, refseq_ids, evidence, pmid

    Example:
        >>> catalog = build_catalog("data/vhdb.tsv", mode="clinical")
        >>> print(f"Built catalog with {len(catalog)} viruses")
        >>> catalog.to_csv("catalog.tsv", sep="\\t", index=False)

        >>> # Include chimp/bonobo homologs for better herpesvirus capture
        >>> catalog = build_catalog(
        ...     "data/vhdb.tsv",
        ...     mode="clinical",
        ...     primate_homologs="strict",
        ...     primate_families={"Herpesviridae", "Papillomaviridae"},
        ... )
    """
    vhdb_path = Path(vhdb_path)

    # Load VHDB
    df = load_vhdb(vhdb_path)
    logger.info(f"Loaded {len(df)} total virus-host relationships")

    # Filter by host
    filtered = filter_by_host(df, mode=mode)

    # Deduplicate by evidence (one entry per virus)
    unique = deduplicate_by_evidence(filtered, prefer_human=True)

    # Require RefSeq
    with_refseq = filter_with_refseq(unique)

    # Remove bacteriophages
    if exclude_bacteriophages:
        with_refseq = filter_bacteriophages(with_refseq, exclude=True)

    # Add primate homologs if requested
    if primate_homologs != PRIMATE_MODE_NONE:
        homologs = get_primate_homologs(df, mode=primate_homologs, families=primate_families)

        if len(homologs) > 0:
            # Deduplicate homologs
            homologs_unique = deduplicate_by_evidence(homologs, prefer_human=False)

            # Remove bacteriophages from homologs too
            if exclude_bacteriophages:
                homologs_unique = filter_bacteriophages(homologs_unique, exclude=True)

            # Combine with main catalog (avoid duplicates by virus_tax_id)
            existing_taxids = set(with_refseq["virus_tax_id"])
            new_homologs = homologs_unique[~homologs_unique["virus_tax_id"].isin(existing_taxids)]

            logger.info(f"Adding {len(new_homologs)} primate homologs to catalog")
            with_refseq = pd.concat([with_refseq, new_homologs], ignore_index=True)

    # Build catalog records
    records = []
    for _, row in with_refseq.iterrows():
        taxonomy = extract_taxonomy(row["virus_lineage"])
        refseq_ids = parse_refseq_ids(row["refseq_id"])

        records.append({
            "taxid": row["virus_tax_id"],
            "name": row["virus_name"],
            "family": taxonomy["family"],
            "order": taxonomy["order"],
            "refseq_ids": refseq_ids,
            "evidence": row["evidence"],
            "pmid": row["pmid"] if pd.notna(row["pmid"]) else None,
        })

    catalog = pd.DataFrame(records)
    total_refseq = catalog["refseq_ids"].apply(len).sum()
    logger.info(
        f"Built catalog: {len(catalog)} viruses, "
        f"{catalog['family'].nunique()} families, "
        f"{total_refseq} RefSeq entries"
    )

    return catalog


def save_catalog(
    catalog: pd.DataFrame,
    output_path: Path | str,
    vhdb_path: Path | str,
    mode: str,
    exclude_bacteriophages: bool,
    primate_homologs: str = PRIMATE_MODE_NONE,
    primate_families: set[str] | None = None,
    virotaxa_version: str | None = None,
) -> tuple[Path, Path]:
    """Save catalog TSV and accompanying metadata JSON.

    Args:
        catalog: The catalog DataFrame to save
        output_path: Path for the output TSV file
        vhdb_path: Path to the source VHDB file
        mode: Catalog mode used
        exclude_bacteriophages: Whether bacteriophages were excluded
        primate_homologs: Primate homolog mode used ("none", "strict", "extended")
        primate_families: Families for which primate homologs were included
        virotaxa_version: Version of virotaxa used (defaults to installed version)

    Returns:
        Tuple of (catalog_path, metadata_path)

    Example:
        >>> catalog = build_catalog("data/vhdb.tsv")
        >>> tsv_path, meta_path = save_catalog(
        ...     catalog, "catalog.tsv", "data/vhdb.tsv",
        ...     mode="clinical", exclude_bacteriophages=True
        ... )
    """
    import json

    from virotaxa import __version__

    output_path = Path(output_path)
    vhdb_path = Path(vhdb_path)

    if virotaxa_version is None:
        virotaxa_version = __version__

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Export catalog - expand refseq_ids list to semicolon-separated string
    catalog_export = catalog.copy()
    catalog_export["refseq_ids"] = catalog_export["refseq_ids"].apply(
        lambda x: ";".join(x) if x else ""
    )
    catalog_export.to_csv(output_path, sep="\t", index=False)
    logger.info(f"Saved catalog to {output_path}")

    # Generate and save metadata
    metadata = generate_metadata(
        catalog=catalog,
        source_path=vhdb_path,
        mode=mode,
        exclude_bacteriophages=exclude_bacteriophages,
        primate_homologs=primate_homologs,
        primate_families=primate_families,
        virotaxa_version=virotaxa_version,
    )
    metadata_path = output_path.with_suffix(".metadata.json")
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    logger.info(f"Saved catalog metadata to {metadata_path}")

    return output_path, metadata_path
