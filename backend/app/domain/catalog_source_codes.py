"""Workbook source code -> canonical measurement key (lookup helper: catalog_map.map_code).

The codes are one buyer's entries in the POM synonym table (``data/pom_synonyms.json``).
"""
from app.domain.pom_synonyms import source_codes

MAPPING = dict(source_codes())
