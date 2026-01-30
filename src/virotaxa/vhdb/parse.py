"""Parsing functionality for Virus-Host Database.

Provides functions for loading and parsing the VHDB TSV file into pandas DataFrames.
"""

import logging
from pathlib import Path

import pandas as pd

from virotaxa.constants import VHDB_COLUMNS

logger = logging.getLogger(__name__)


def load_vhdb(tsv_path: Path | str) -> pd.DataFrame:
    """Load Virus-Host Database TSV into DataFrame.

    Args:
        tsv_path: Path to virushostdb.tsv file

    Returns:
        DataFrame with all virus-host relationships

    Example:
        >>> df = load_vhdb("data/vhdb.tsv")
        >>> print(f"Loaded {len(df)} virus-host relationships")
    """
    tsv_path = Path(tsv_path)

    df = pd.read_csv(tsv_path, sep="\t", names=VHDB_COLUMNS, header=0)

    # Convert to nullable integer types (handles NA values)
    df["virus_tax_id"] = pd.to_numeric(df["virus_tax_id"], errors="coerce").astype("Int64")
    df["host_tax_id"] = pd.to_numeric(df["host_tax_id"], errors="coerce").astype("Int64")

    logger.info(f"Loaded {len(df)} virus-host relationships from {tsv_path}")
    return df
