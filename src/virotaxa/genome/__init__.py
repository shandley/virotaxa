"""Genome fetching functionality for virotaxa.

Provides tools for fetching viral genome sequences from NCBI RefSeq
based on virotaxa catalogs.
"""

from virotaxa.genome.fetch import GenomeFetchResult, fetch_genomes, fetch_sequence

__all__ = ["fetch_genomes", "fetch_sequence", "GenomeFetchResult"]
