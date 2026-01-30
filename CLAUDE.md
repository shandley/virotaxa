# Claude Project Context: Virotaxa

## Project Overview

Virotaxa is a Python CLI tool for reproducible viral taxa selection from the Virus-Host Database (VHDB). It's designed for hybrid capture probe design workflows.

## Architecture

```
src/virotaxa/
├── __init__.py          # Package version
├── constants.py         # All constants (taxids, modes, phage families)
├── cli.py               # Typer CLI with subcommands
├── vhdb/
│   ├── download.py      # VHDB download with metadata
│   ├── parse.py         # Load TSV into DataFrame
│   ├── filters.py       # Host, phage, RefSeq, primate filters
│   └── taxonomy.py      # Extract family/order from lineage
├── catalog/
│   ├── builder.py       # Main build_catalog() function
│   ├── metadata.py      # Generate reproducibility metadata
│   └── validate.py      # Validate catalog against metadata
├── cache/
│   └── registry.py      # SHA256-based VHDB version pinning
└── genome/
    ├── fetch.py         # Biopython Entrez genome fetching
    └── metadata.py      # Genome fetch metadata
```

## Key Design Decisions

1. **Biopython for NCBI**: Uses `Bio.Entrez` with automatic rate limiting (0.4s without API key, 0.1s with)

2. **Primate homologs**: Added to improve capture of high-diversity human viruses (HHV-8, HCMV, EBV, HPV). Two modes:
   - `strict`: Chimp/bonobo only (taxids 9598, 9597)
   - `extended`: All non-human primates

3. **Metadata tracking**: Every catalog and genome fetch produces a `.metadata.json` with full provenance

4. **Phage exclusion**: 30 bacteriophage families + keyword matching to remove false "human-associated" phages from microbiome samples

## CLI Commands

```bash
virotaxa download                    # Download VHDB
virotaxa info <file>                 # Show VHDB stats
virotaxa families <file>             # List families

virotaxa cache download              # Cache VHDB by hash
virotaxa cache list                  # List cached versions
virotaxa cache use <hash>            # Use cached version

virotaxa catalog build <file>        # Build catalog
  --mode {clinical,pandemic,mammal}
  --primate-homologs {none,strict,extended}
  --primate-families FAM1,FAM2
virotaxa catalog validate <file>     # Validate catalog

virotaxa genome fetch <catalog>      # Fetch RefSeq genomes
  --email EMAIL (required)
  --api-key KEY (optional)
```

## Testing

```bash
pytest tests/ -v                     # Run all tests (40 tests)
mypy src/virotaxa/                   # Type checking
ruff check src/virotaxa/             # Linting
```

## Current Stats (VHDB as of 2026-01)

| Catalog | Taxa | RefSeq IDs |
|---------|------|------------|
| Clinical | 1,432 | 1,918 |
| Clinical + strict primates | 1,457 | 1,943 |
| Pandemic | 3,992 | 5,400+ |
| Mammal | 3,368 | 4,500+ |

## Future Enhancements (Not Yet Implemented)

- Genome caching (hash-based like VHDB cache)
- Retry failed downloads command
- Progress bar for large downloads
- Parallel fetching with rate limiting

## Dependencies

- pandas, httpx, typer, rich (core)
- biopython (genome fetching)
- pytest, mypy, ruff (dev)
