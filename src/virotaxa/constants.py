"""Constants for virotaxa.

This module contains all constants used for viral taxa selection including
taxonomy IDs, catalog modes, bacteriophage families, and evidence priorities.
"""

from pathlib import Path

# Virus-Host Database URL
VHDB_URL = "https://www.genome.jp/ftp/db/virushostdb/virushostdb.tsv"

# Host taxonomy IDs
HUMAN_TAXID = 9606

# Default cache directory for VHDB version pinning
DEFAULT_CACHE_DIR = Path.home() / ".virotaxa" / "cache" / "vhdb"

# Catalog modes for different use cases
MODE_CLINICAL = "clinical"  # Human hosts only - for clinical diagnostics
MODE_PANDEMIC = "pandemic"  # All vertebrate hosts - for pandemic preparedness
MODE_MAMMAL = "mammal"  # Mammalian hosts only - for zoonotic focus

VALID_MODES = {MODE_CLINICAL, MODE_PANDEMIC, MODE_MAMMAL}

# Evidence priority for deduplication (lower = higher priority)
EVIDENCE_PRIORITY = {
    "Literature": 0,
    "RefSeq": 1,
    "UniProt": 2,
}

# Bacteriophage families to exclude
# These infect bacteria, not eukaryotic cells. They appear in Virus-Host DB
# as "human-associated" because they're detected in human microbiome samples,
# but they don't actually infect human cells.
BACTERIOPHAGE_FAMILIES = {
    # Core bacteriophage families (Caudovirales and related)
    "Siphoviridae",  # Long non-contractile tail dsDNA phages
    "Myoviridae",  # Contractile tail dsDNA phages
    "Podoviridae",  # Short tail dsDNA phages
    "Ackermannviridae",  # Contractile tail phages (formerly Myoviridae)
    "Autographiviridae",  # T7-like phages
    "Chaseviridae",  # dsDNA phages
    "Demerecviridae",  # T4-like phages
    "Drexlerviridae",  # Lambda-like phages
    "Guelinviridae",  # dsDNA phages
    "Herelleviridae",  # SPO1-like phages
    "Rountreeviridae",  # dsDNA phages
    "Salasmaviridae",  # Phi29-like phages
    "Schitoviridae",  # N4-like phages
    "Straboviridae",  # dsDNA phages
    "Zobellviridae",  # dsDNA phages
    # ssDNA phages
    "Microviridae",  # ssDNA phages (includes Gokushovirinae) - major contaminant
    "Inoviridae",  # Filamentous ssDNA phages
    # RNA phages
    "Leviviridae",  # ssRNA phages (MS2-like)
    "Cystoviridae",  # dsRNA phages
    "Fiersviridae",  # ssRNA phages
    # Other phage families
    "Tectiviridae",  # Linear dsDNA phages with lipid membrane
    "Corticoviridae",  # Circular dsDNA phages
    "Plasmaviridae",  # Mycoplasma phages
    "Sphaerolipoviridae",  # Archaeal/bacterial viruses
    "Finnlakeviridae",  # dsDNA phages
    "Haloferuviridae",  # Archaeal viruses
    # CrAssphage and related (gut bacteriophages)
    "Intestiviridae",  # CrAssphage family - abundant gut bacteriophages
    "Crevaviridae",  # Related crAss-like phages
    "Steigviridae",  # Related crAss-like phages
    "Suoliviridae",  # Related crAss-like phages
}

# Bacteriophage keywords for name/lineage matching
# Used to catch phages that lack formal family classification
BACTERIOPHAGE_KEYWORDS = [
    "bacteriophage",
    "bacterial virus",
    " phage ",  # Space-bounded to avoid "macrophage"
    "gokushovirus",  # Microviridae subfamily
    "chlamydiamicrovirus",  # Microviridae subfamily
    "crassphage",  # Gut bacteriophage (various spellings)
    "crass-like",  # CrAss-like phages
    # Informal morphotype names for unclassified tailed phages
    "siphovirus",
    "myovirus",
    "podovirus",
]

# VHDB column names
VHDB_COLUMNS = [
    "virus_tax_id",
    "virus_name",
    "virus_lineage",
    "refseq_id",
    "KEGG_GENOME",
    "KEGG_DISEASE",
    "DISEASE",
    "host_tax_id",
    "host_name",
    "host_lineage",
    "pmid",
    "evidence",
    "sample_type",
    "source_organism",
]

# NCBI E-utilities settings
NCBI_EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
DEFAULT_BATCH_SIZE = 100
DEFAULT_DELAY_NO_KEY = 0.4  # 3 requests/second without API key
DEFAULT_DELAY_WITH_KEY = 0.1  # 10 requests/second with API key

# Primate homolog settings
# Used to augment clinical catalogs with primate virus homologs
# to improve capture of high-diversity human viruses (HHV-8, HCMV, EBV, HPV)

# Great ape taxids (closest evolutionary distance to humans)
CHIMP_TAXID = 9598  # Pan troglodytes
BONOBO_TAXID = 9597  # Pan paniscus
GREAT_APE_TAXIDS = {CHIMP_TAXID, BONOBO_TAXID}

# Primate homolog modes
PRIMATE_MODE_NONE = "none"  # No primate homologs (default)
PRIMATE_MODE_STRICT = "strict"  # Chimp/bonobo only (+66 viruses)
PRIMATE_MODE_EXTENDED = "extended"  # All non-human primates (+505 viruses)

VALID_PRIMATE_MODES = {PRIMATE_MODE_NONE, PRIMATE_MODE_STRICT, PRIMATE_MODE_EXTENDED}

# High-diversity families where primate homologs are most valuable
# These families have significant intra-species strain diversity
HIGH_DIVERSITY_FAMILIES = {
    "Herpesviridae",  # HHV-8, HCMV, EBV - strains differ by 20kb+
    "Orthoherpesviridae",  # Modern herpesvirus taxonomy
    "Papillomaviridae",  # HPV - 200+ types
    "Retroviridae",  # HIV - high diversity
    "Polyomaviridae",  # BK, JC viruses
    "Adenoviridae",  # Many serotypes
}
