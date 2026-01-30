"""Filtering functionality for Virus-Host Database.

Provides functions for filtering viral taxa by host, removing bacteriophages,
requiring RefSeq accessions, and deduplicating by evidence type.
"""

import logging

import pandas as pd

from virotaxa.constants import (
    BACTERIOPHAGE_FAMILIES,
    BACTERIOPHAGE_KEYWORDS,
    EVIDENCE_PRIORITY,
    GREAT_APE_TAXIDS,
    HUMAN_TAXID,
    MODE_CLINICAL,
    MODE_MAMMAL,
    MODE_PANDEMIC,
    PRIMATE_MODE_NONE,
    PRIMATE_MODE_STRICT,
    VALID_MODES,
    VALID_PRIMATE_MODES,
)

logger = logging.getLogger(__name__)


def filter_by_host(
    df: pd.DataFrame,
    mode: str = MODE_CLINICAL,
) -> pd.DataFrame:
    """Filter Virus-Host Database by host taxonomy.

    Three modes are available:
    - clinical: Human hosts only (TaxID 9606)
    - pandemic: All vertebrate hosts (Vertebrata in lineage)
    - mammal: Mammalian hosts only (Mammalia in lineage)

    Args:
        df: Full Virus-Host Database DataFrame
        mode: Filtering mode - "clinical", "pandemic", or "mammal"

    Returns:
        DataFrame filtered to specified host type

    Raises:
        ValueError: If mode is not valid

    Example:
        >>> filtered = filter_by_host(df, mode="pandemic")
        >>> print(f"Found {len(filtered)} vertebrate-infecting viruses")
    """
    if mode not in VALID_MODES:
        raise ValueError(f"Invalid mode: {mode}. Must be one of {VALID_MODES}")

    if mode == MODE_CLINICAL:
        # Human hosts only
        filtered = df[df["host_tax_id"] == HUMAN_TAXID].copy()
        logger.info(f"Filtered to {len(filtered)} human-infecting viruses (clinical mode)")

    elif mode == MODE_PANDEMIC:
        # All vertebrate hosts
        has_vertebrate_host = df["host_lineage"].fillna("").str.contains("Vertebrata", case=False)
        filtered = df[has_vertebrate_host].copy()
        logger.info(f"Filtered to {len(filtered)} vertebrate-infecting viruses (pandemic mode)")

    elif mode == MODE_MAMMAL:
        # Mammalian hosts only
        has_mammal_host = df["host_lineage"].fillna("").str.contains("Mammalia", case=False)
        filtered = df[has_mammal_host].copy()
        logger.info(f"Filtered to {len(filtered)} mammal-infecting viruses (mammal mode)")

    return filtered


def deduplicate_by_evidence(
    df: pd.DataFrame,
    prefer_human: bool = True,
) -> pd.DataFrame:
    """Deduplicate to one entry per virus, prioritizing by evidence type.

    When a virus has multiple host entries, keeps the one with highest priority:
    Literature > RefSeq > UniProt

    Optionally prefers human host entries when available.

    Args:
        df: DataFrame of viruses (may have duplicates)
        prefer_human: If True, prefer human host entries when deduplicating

    Returns:
        DataFrame with one entry per virus TaxID

    Example:
        >>> unique = deduplicate_by_evidence(df)
        >>> assert unique["virus_tax_id"].is_unique
    """
    working = df.copy()

    # Add evidence priority ranking
    working["_evidence_rank"] = working["evidence"].map(
        lambda x: EVIDENCE_PRIORITY.get(x, 99)
    )

    if prefer_human:
        # Also prefer human host entries
        working["_is_human"] = working["host_tax_id"] == HUMAN_TAXID
        working = working.sort_values(
            ["_is_human", "_evidence_rank"],
            ascending=[False, True],
        )
        working = working.drop_duplicates(subset=["virus_tax_id"], keep="first")
        working = working.drop(columns=["_evidence_rank", "_is_human"])
    else:
        working = working.sort_values("_evidence_rank")
        working = working.drop_duplicates(subset=["virus_tax_id"], keep="first")
        working = working.drop(columns=["_evidence_rank"])

    logger.info(f"Deduplicated to {len(working)} unique viruses")
    return working


def filter_with_refseq(df: pd.DataFrame) -> pd.DataFrame:
    """Filter for viruses that have RefSeq IDs.

    Args:
        df: DataFrame of viruses

    Returns:
        DataFrame with only viruses that have RefSeq entries

    Example:
        >>> with_refseq = filter_with_refseq(df)
        >>> print(f"Found {len(with_refseq)} viruses with RefSeq")
    """
    has_refseq = df["refseq_id"].notna() & (df["refseq_id"] != "")
    filtered = df[has_refseq].copy()

    logger.info(f"Filtered to {len(filtered)} viruses with RefSeq IDs")
    return filtered


def filter_bacteriophages(
    df: pd.DataFrame,
    exclude: bool = True,
) -> pd.DataFrame:
    """Remove bacteriophages from virus DataFrame.

    Bacteriophages infect bacteria, not eukaryotic cells. They appear in
    Virus-Host DB as "human-associated" because they're detected in human
    microbiome samples (gut, skin, etc.), but including them in a human
    virus catalog would be incorrect.

    Filtering is done by:
    1. Excluding known bacteriophage families from virus lineage
    2. Checking for phage-related keywords in virus name/lineage

    Args:
        df: DataFrame of viruses with virus_lineage column
        exclude: If True, remove phages. If False, keep only phages.

    Returns:
        DataFrame with bacteriophages removed (or kept if exclude=False)

    Example:
        >>> no_phages = filter_bacteriophages(df, exclude=True)
        >>> only_phages = filter_bacteriophages(df, exclude=False)
    """
    initial_count = len(df)

    def is_bacteriophage(row: pd.Series) -> bool:
        """Check if a virus entry is a bacteriophage."""
        lineage = str(row.get("virus_lineage", "")) if pd.notna(row.get("virus_lineage")) else ""
        name = str(row.get("virus_name", "")) if pd.notna(row.get("virus_name")) else ""

        # Check for bacteriophage families in lineage
        lineage_lower = lineage.lower()
        for family in BACTERIOPHAGE_FAMILIES:
            if family.lower() in lineage_lower:
                return True

        # Check for phage keywords in name or lineage
        combined = lineage_lower + " " + name.lower()
        for keyword in BACTERIOPHAGE_KEYWORDS:
            if keyword in combined:
                return True

        return False

    # Apply filter
    phage_mask = df.apply(is_bacteriophage, axis=1)

    if exclude:
        filtered = df[~phage_mask].copy()
        removed_count = initial_count - len(filtered)
        if removed_count > 0:
            logger.info(f"Removed {removed_count} bacteriophages from catalog")
    else:
        filtered = df[phage_mask].copy()
        logger.info(f"Kept {len(filtered)} bacteriophages")

    return filtered


def get_primate_homologs(
    df: pd.DataFrame,
    mode: str = PRIMATE_MODE_STRICT,
    families: set[str] | None = None,
) -> pd.DataFrame:
    """Get non-human primate virus homologs from VHDB.

    Primate homologs can improve capture of high-diversity human viruses
    (HHV-8, HCMV, EBV, HPV) by providing additional probe templates that
    span sequence space between divergent human strains.

    Two modes are available:
    - strict: Chimp and bonobo only (~66 viruses) - closest evolutionary distance
    - extended: All non-human primates (~505 viruses) - maximum coverage

    Optionally filter to specific viral families.

    Args:
        df: Full Virus-Host Database DataFrame
        mode: "strict" for chimp/bonobo only, "extended" for all primates
        families: Optional set of viral families to include (e.g., {"Herpesviridae"}).
                  If None, includes all families.

    Returns:
        DataFrame of primate virus homologs with RefSeq entries

    Raises:
        ValueError: If mode is not valid

    Example:
        >>> # Get all chimp/bonobo viruses
        >>> homologs = get_primate_homologs(df, mode="strict")
        >>>
        >>> # Get only herpesvirus homologs from all primates
        >>> herpes = get_primate_homologs(df, mode="extended",
        ...                               families={"Herpesviridae"})
    """
    if mode not in VALID_PRIMATE_MODES:
        raise ValueError(f"Invalid primate mode: {mode}. Must be one of {VALID_PRIMATE_MODES}")

    if mode == PRIMATE_MODE_NONE:
        return pd.DataFrame(columns=df.columns)

    # Filter by host
    if mode == PRIMATE_MODE_STRICT:
        # Great apes only (chimp + bonobo)
        is_great_ape = df["host_tax_id"].isin(GREAT_APE_TAXIDS)
        filtered = df[is_great_ape].copy()
        logger.info(f"Found {len(filtered)} great ape virus entries (strict mode)")
    else:
        # All non-human primates
        is_primate = df["host_lineage"].fillna("").str.contains("Primates", case=False)
        is_human = df["host_tax_id"] == HUMAN_TAXID
        filtered = df[is_primate & ~is_human].copy()
        logger.info(f"Found {len(filtered)} non-human primate virus entries (extended mode)")

    # Require RefSeq
    has_refseq = filtered["refseq_id"].notna() & (filtered["refseq_id"] != "")
    filtered = filtered[has_refseq].copy()

    # Filter by families if specified
    if families:
        def has_target_family(lineage: str) -> bool:
            if pd.isna(lineage):
                return False
            lineage_lower = lineage.lower()
            for family in families:
                if family.lower() in lineage_lower:
                    return True
            return False

        family_mask = filtered["virus_lineage"].apply(has_target_family)
        filtered = filtered[family_mask].copy()
        logger.info(f"Filtered to {len(filtered)} entries in families: {families}")

    unique_count = filtered["virus_tax_id"].nunique()
    logger.info(f"Primate homologs: {unique_count} unique viruses with RefSeq")

    return filtered
