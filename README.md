# Virotaxa

Reproducible viral taxa selection from the Virus-Host Database.

## Overview

Virotaxa provides tools for downloading, filtering, and cataloging viral taxa from the [Virus-Host Database (VHDB)](https://www.genome.jp/virushostdb/) with full reproducibility tracking. It generates curated catalogs of viral species suitable for downstream applications like hybrid capture probe design, metagenomic analysis, and surveillance panels.

## Features

- **Host-based filtering**: Clinical (human only), pandemic (all vertebrates), or mammal modes
- **Bacteriophage exclusion**: Removes 26+ phage families and morphotypes
- **Evidence prioritization**: Literature > RefSeq > UniProt
- **Version pinning**: Cache VHDB files by SHA256 hash
- **Reproducibility metadata**: Track all parameters for exact reproduction
- **Validation**: Verify catalogs against their metadata

## Installation

```bash
pip install virotaxa

# Or from source
pip install -e ".[dev]"
```

## Quick Start

### Download and Build Catalog

```bash
# Download the latest Virus-Host Database
virotaxa download -o data/vhdb.tsv

# Build a clinical catalog (human hosts only)
virotaxa catalog build data/vhdb.tsv -o catalog.tsv --mode clinical

# Build a pandemic preparedness catalog (all vertebrates)
virotaxa catalog build data/vhdb.tsv -o catalog.tsv --mode pandemic
```

### Version Pinning for Reproducibility

```bash
# Download VHDB directly to cache
virotaxa cache download
# Output: Hash 7a3f2b1c8d4e...

# List cached versions
virotaxa cache list

# Use a specific cached version
virotaxa cache use 7a3f2b1c -o data/vhdb.tsv

# Validate catalog reproducibility
virotaxa catalog validate catalog.tsv
```

## Catalog Modes

| Mode | Description | Typical Count |
|------|-------------|---------------|
| `clinical` | Human hosts only | ~1,400 viruses |
| `pandemic` | All vertebrate hosts | ~4,000+ viruses |
| `mammal` | Mammalian hosts only | ~3,000 viruses |

## Output Format

**catalog.tsv:**
```
taxid   name                        family          order           refseq_ids      evidence
11676   Human immunodeficiency...   Retroviridae    Ortervirales    NC_001802.1     Literature
11320   Influenza A virus           Orthomyxoviridae Articulavirales NC_002016.1    Literature
```

**catalog.metadata.json:**
```json
{
  "generation": {
    "timestamp": "2026-01-29T12:00:00Z",
    "virotaxa_version": "0.1.0"
  },
  "source": {
    "sha256": "7a3f2b1c..."
  },
  "parameters": {
    "mode": "clinical",
    "exclude_bacteriophages": true
  },
  "statistics": {
    "total_taxa": 1088,
    "unique_families": 48
  }
}
```

## Python API

```python
from virotaxa import build_catalog, download_vhdb
from virotaxa.cache import cache_download, get_cached

# Download VHDB
vhdb_path = download_vhdb("data/vhdb.tsv")

# Build catalog
catalog = build_catalog(vhdb_path, mode="clinical")
print(f"Built catalog with {len(catalog)} viruses")

# Use cached version for reproducibility
cached_path, hash_value = cache_download()
catalog = build_catalog(cached_path, mode="pandemic")
```

## Filtering Pipeline

```
Virus-Host Database
        │
        ▼
┌───────────────────────┐
│ 1. Host Filtering     │  clinical/pandemic/mammal
└───────────────────────┘
        │
        ▼
┌───────────────────────┐
│ 2. Evidence Dedup     │  Literature > RefSeq > UniProt
└───────────────────────┘
        │
        ▼
┌───────────────────────┐
│ 3. RefSeq Requirement │  Must have RefSeq accession
└───────────────────────┘
        │
        ▼
┌───────────────────────┐
│ 4. Phage Removal      │  26 families + keywords
└───────────────────────┘
        │
        ▼
    Catalog
```

## Data Source

[Virus-Host Database](https://www.genome.jp/virushostdb/) provides curated virus-host relationships with literature evidence.

## License

MIT

## Citation

If you use virotaxa, please cite:

> Virotaxa: Reproducible viral taxa selection from Virus-Host Database.
> https://github.com/shandley/virotaxa
