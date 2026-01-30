"""Core genome fetching functionality.

Provides functions for fetching viral genome sequences from NCBI
using Biopython's Entrez module.
"""

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd
from Bio import Entrez, SeqIO

from virotaxa.constants import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_DELAY_NO_KEY,
    DEFAULT_DELAY_WITH_KEY,
)

logger = logging.getLogger(__name__)


@dataclass
class GenomeFetchResult:
    """Result of a genome fetch operation.

    Attributes:
        total_taxa: Number of taxa in the catalog
        total_sequences: Number of RefSeq IDs to fetch
        successful: Number of successfully fetched sequences
        failed: List of RefSeq IDs that failed to fetch
        output_dir: Directory containing output files
        files: Dict mapping taxid to output file info
    """

    total_taxa: int
    total_sequences: int
    successful: int
    failed: list[str] = field(default_factory=list)
    output_dir: Path = field(default_factory=Path)
    files: dict[str, dict[str, Any]] = field(default_factory=dict)


def fetch_sequence(
    refseq_id: str,
    email: str,
    api_key: str | None = None,
) -> str:
    """Fetch a single sequence from NCBI.

    Args:
        refseq_id: NCBI RefSeq accession (e.g., NC_001802.1)
        email: Email address for NCBI (required by NCBI policy)
        api_key: Optional NCBI API key for higher rate limits

    Returns:
        FASTA format sequence string

    Raises:
        RuntimeError: If the sequence cannot be fetched

    Example:
        >>> seq = fetch_sequence("NC_001802.1", "user@example.com")
        >>> print(seq[:50])
        >NC_001802.1 Human immunodeficiency virus 1...
    """
    Entrez.email = email  # type: ignore[assignment]
    if api_key:
        Entrez.api_key = api_key  # type: ignore[assignment]

    try:
        handle = Entrez.efetch(  # type: ignore[no-untyped-call]
            db="nucleotide",
            id=refseq_id,
            rettype="fasta",
            retmode="text",
        )
        sequence: str = handle.read()
        handle.close()
        return sequence
    except Exception as e:
        raise RuntimeError(f"Failed to fetch {refseq_id}: {e}") from e


def _load_catalog(catalog_path: Path) -> pd.DataFrame:
    """Load a catalog TSV file.

    Args:
        catalog_path: Path to catalog TSV file

    Returns:
        DataFrame with catalog data, refseq_ids parsed as lists
    """
    catalog = pd.read_csv(catalog_path, sep="\t")

    # Parse refseq_ids from semicolon-separated string to list
    if "refseq_ids" in catalog.columns:
        catalog["refseq_ids"] = catalog["refseq_ids"].apply(
            lambda x: x.split(";") if pd.notna(x) and x else []
        )

    return catalog


def _get_delay(api_key: str | None) -> float:
    """Get appropriate delay based on API key presence."""
    if api_key:
        return DEFAULT_DELAY_WITH_KEY
    return DEFAULT_DELAY_NO_KEY


def fetch_genomes(
    catalog_path: Path | str,
    output_dir: Path | str,
    email: str,
    api_key: str | None = None,
    batch_size: int = DEFAULT_BATCH_SIZE,
    delay: float | None = None,
) -> GenomeFetchResult:
    """Fetch all genomes for a catalog.

    Downloads genome sequences for all taxa in a virotaxa catalog.
    Sequences are saved as FASTA files, one per taxon.

    Args:
        catalog_path: Path to catalog TSV file
        output_dir: Directory to save FASTA files
        email: Email address for NCBI (required by NCBI policy)
        api_key: Optional NCBI API key for higher rate limits
        batch_size: Number of sequences to fetch per batch
        delay: Delay between requests in seconds (auto-calculated if None)

    Returns:
        GenomeFetchResult with fetch statistics

    Example:
        >>> result = fetch_genomes(
        ...     "clinical_catalog.tsv",
        ...     "genomes/",
        ...     email="user@example.com"
        ... )
        >>> print(f"Fetched {result.successful} sequences")
    """
    catalog_path = Path(catalog_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if delay is None:
        delay = _get_delay(api_key)

    # Configure Entrez
    Entrez.email = email  # type: ignore[assignment]
    if api_key:
        Entrez.api_key = api_key  # type: ignore[assignment]

    # Load catalog
    catalog = _load_catalog(catalog_path)
    logger.info(f"Loaded catalog with {len(catalog)} taxa")

    # Collect all RefSeq IDs and map to taxa
    refseq_to_taxid: dict[str, int] = {}
    for _, row in catalog.iterrows():
        taxid = row["taxid"]
        refseq_ids = row.get("refseq_ids", [])
        if isinstance(refseq_ids, str):
            refseq_ids = refseq_ids.split(";") if refseq_ids else []
        for refseq_id in refseq_ids:
            if refseq_id:
                refseq_to_taxid[refseq_id.strip()] = taxid

    all_refseq_ids = list(refseq_to_taxid.keys())
    total_sequences = len(all_refseq_ids)
    logger.info(f"Total RefSeq IDs to fetch: {total_sequences}")

    # Fetch sequences in batches
    successful = 0
    failed: list[str] = []
    sequences_by_taxid: dict[int, list[str]] = {}

    for i in range(0, total_sequences, batch_size):
        batch = all_refseq_ids[i : i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (total_sequences + batch_size - 1) // batch_size
        logger.info(f"Fetching batch {batch_num}/{total_batches} ({len(batch)} sequences)")

        try:
            # Use EPost to upload IDs to history
            post_handle = Entrez.epost(  # type: ignore[no-untyped-call]
                db="nucleotide", id=",".join(batch)
            )
            post_result = Entrez.read(post_handle)  # type: ignore[no-untyped-call]
            post_handle.close()

            webenv = post_result["WebEnv"]
            query_key = post_result["QueryKey"]

            # Fetch sequences using history
            fetch_handle = Entrez.efetch(  # type: ignore[no-untyped-call]
                db="nucleotide",
                rettype="fasta",
                retmode="text",
                webenv=webenv,
                query_key=query_key,
            )
            fasta_data = fetch_handle.read()
            fetch_handle.close()

            # Parse the FASTA data and organize by taxid
            from io import StringIO

            for record in SeqIO.parse(  # type: ignore[no-untyped-call]
                StringIO(fasta_data), "fasta"
            ):
                # Extract accession from record ID
                accession = record.id.split(".")[0]
                # Try to match with version
                matched_id = None
                for refseq_id in batch:
                    if refseq_id.startswith(accession):
                        matched_id = refseq_id
                        break

                if matched_id and matched_id in refseq_to_taxid:
                    taxid = refseq_to_taxid[matched_id]
                    if taxid not in sequences_by_taxid:
                        sequences_by_taxid[taxid] = []
                    # Format as FASTA string
                    fasta_str = f">{record.id} {record.description}\n{str(record.seq)}\n"
                    sequences_by_taxid[taxid].append(fasta_str)
                    successful += 1
                else:
                    logger.warning(f"Could not match sequence {record.id} to catalog")

            # Check for missing sequences in this batch
            fetched_accessions: set[str] = set()
            for record in SeqIO.parse(  # type: ignore[no-untyped-call]
                StringIO(fasta_data), "fasta"
            ):
                fetched_accessions.add(record.id.split(".")[0])

            for refseq_id in batch:
                base_acc = refseq_id.split(".")[0]
                if base_acc not in fetched_accessions:
                    failed.append(refseq_id)
                    logger.warning(f"Failed to fetch: {refseq_id}")

        except Exception as e:
            logger.error(f"Batch fetch failed: {e}")
            failed.extend(batch)

        # Rate limiting
        if i + batch_size < total_sequences:
            time.sleep(delay)

    # Write FASTA files per taxon
    files: dict[str, dict[str, Any]] = {}
    for taxid, sequences in sequences_by_taxid.items():
        fasta_path = output_dir / f"{taxid}.fasta"
        with open(fasta_path, "w") as f:
            for seq in sequences:
                f.write(seq)

        # Calculate total bases
        total_bases = sum(len(s.split("\n", 1)[1].replace("\n", "")) for s in sequences)
        files[str(taxid)] = {
            "file": f"{taxid}.fasta",
            "sequences": len(sequences),
            "bases": total_bases,
        }
        logger.info(f"Wrote {fasta_path}: {len(sequences)} sequences, {total_bases} bases")

    result = GenomeFetchResult(
        total_taxa=len(catalog),
        total_sequences=total_sequences,
        successful=successful,
        failed=failed,
        output_dir=output_dir,
        files=files,
    )

    logger.info(
        f"Fetch complete: {successful}/{total_sequences} sequences, "
        f"{len(failed)} failed"
    )

    return result
