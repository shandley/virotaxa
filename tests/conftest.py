"""Pytest configuration and fixtures for virotaxa tests."""

import pytest


@pytest.fixture
def sample_vhdb_data() -> str:
    """Sample VHDB TSV content for testing."""
    return """virus_tax_id\tvirus_name\tvirus_lineage\trefseq_id\tKEGG_GENOME\tKEGG_DISEASE\tDISEASE\thost_tax_id\thost_name\thost_lineage\tpmid\tevidence\tsample_type\tsource_organism
11676\tHuman immunodeficiency virus 1\tViruses; Riboviria; Pararnavirae; Artverviricota; Revtraviricetes; Ortervirales; Retroviridae; Orthoretrovirinae; Lentivirus\tNC_001802.1\t\t\tAIDS\t9606\tHomo sapiens\tEukaryota; Metazoa; Chordata; Vertebrata; Mammalia; Primates; Hominidae; Homo\t12345678\tLiterature\t\t
11320\tInfluenza A virus\tViruses; Riboviria; Orthornavirae; Negarnaviricota; Polyploviricotina; Insthoviricetes; Articulavirales; Orthomyxoviridae\tNC_002016.1\t\t\tInfluenza\t9606\tHomo sapiens\tEukaryota; Metazoa; Chordata; Vertebrata; Mammalia; Primates; Hominidae; Homo\t\tRefSeq\t\t
1518022\tSiphovirus contig89\tViruses; Duplodnaviria; Caudoviricetes; unclassified Caudoviricetes\tNC_999999.1\t\t\t\t9606\tHomo sapiens\tEukaryota; Metazoa; Chordata; Vertebrata; Mammalia; Primates; Hominidae; Homo\t\tRefSeq\t\t
12637\tZika virus\tViruses; Riboviria; Orthornavirae; Kitrinoviricota; Flasuviricetes; Amarillovirales; Flaviviridae; Flavivirus\tNC_012532.1\t\t\tZika fever\t9606\tHomo sapiens\tEukaryota; Metazoa; Chordata; Vertebrata; Mammalia; Primates; Hominidae; Homo\t\tLiterature\t\t
999999\tBat coronavirus HKU9\tViruses; Riboviria; Orthornavirae; Pisuviricota; Pisoniviricetes; Nidovirales; Cornidovirineae; Coronaviridae; Orthocoronavirinae; Betacoronavirus\tNC_009021.1\t\t\t\t9397\tPteropus alecto\tEukaryota; Metazoa; Chordata; Vertebrata; Mammalia; Chiroptera; Pteropodidae; Pteropus\t\tRefSeq\t\t
"""
