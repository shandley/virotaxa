# Virotaxa

Reproducible viral taxa selection from the Virus-Host Database.

## Overview

Virotaxa provides tools for downloading, filtering, and cataloging viral taxa from the [Virus-Host Database (VHDB)](https://www.genome.jp/virushostdb/) with full reproducibility tracking. It generates curated catalogs of viral species suitable for downstream applications like hybrid capture probe design, metagenomic analysis, and surveillance panels.

## Features

- **Host-based filtering**: Clinical (human only), pandemic (all vertebrates), or mammal modes
- **Bacteriophage exclusion**: Removes 30 phage families and morphotypes
- **Evidence prioritization**: Literature > RefSeq > UniProt
- **Primate homologs**: Augment catalogs with chimp/bonobo viruses for better capture of high-diversity human viruses
- **Genome fetching**: Download RefSeq sequences from NCBI for probe design
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

### Primate Homologs for Better Capture

High-diversity human viruses (HHV-8, HCMV, EBV, HPV) have strains that differ by 20kb+. Adding primate homologs improves probe capture by spanning sequence space:

```bash
# Add chimp/bonobo homologs (strict mode, +25 viruses)
virotaxa catalog build data/vhdb.tsv --primate-homologs strict -o catalog.tsv

# Add all primate homologs, filtered to key families
virotaxa catalog build data/vhdb.tsv --primate-homologs extended \
  --primate-families Herpesviridae,Papillomaviridae -o catalog.tsv
```

### Fetch Genome Sequences

```bash
# Download RefSeq genomes for all taxa in catalog
virotaxa genome fetch catalog.tsv --email you@example.com -o genomes/

# With NCBI API key for faster downloads (10 req/s vs 3 req/s)
virotaxa genome fetch catalog.tsv --email you@example.com --api-key YOUR_KEY
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
| `mammal` | Mammalian hosts only | ~3,400 viruses |

## Primate Homolog Modes

| Mode | Description | Added Viruses |
|------|-------------|---------------|
| `none` | No primate homologs (default) | — |
| `strict` | Chimp/bonobo only | +25 to clinical |
| `extended` | All non-human primates | +56 to clinical |

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
    "exclude_bacteriophages": true,
    "primate_homologs": "strict"
  },
  "statistics": {
    "total_taxa": 1457,
    "unique_families": 48
  }
}
```

**genomes/ (after genome fetch):**
```
genomes/
├── 11676.fasta          # HIV-1
├── 11320.fasta          # Influenza A
├── ...
└── genomes.metadata.json
```

## Python API

```python
from virotaxa.catalog.builder import build_catalog
from virotaxa.vhdb.download import download_vhdb
from virotaxa.genome import fetch_genomes

# Download VHDB
vhdb_path = download_vhdb("data/vhdb.tsv")

# Build catalog with primate homologs
catalog = build_catalog(
    vhdb_path,
    mode="clinical",
    primate_homologs="strict",
    primate_families={"Herpesviridae", "Papillomaviridae"},
)
print(f"Built catalog with {len(catalog)} viruses")

# Fetch genomes
result = fetch_genomes(
    catalog_path="catalog.tsv",
    output_dir="genomes/",
    email="you@example.com",
)
print(f"Fetched {result.successful} sequences")
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
│ 4. Phage Removal      │  30 families + keywords
└───────────────────────┘
        │
        ▼
┌───────────────────────┐
│ 5. Primate Homologs   │  Optional: strict/extended
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
