# backend/fhir_mapping/__init__.py

# This file makes the `fhir_mapping` directory a Python package.
# Export key functions from the submodules here for easier access.

from .orchestrator import map_text_to_fhir
from .id_utils import generate_fhir_id

__all__ = [
    "map_text_to_fhir",
    "generate_fhir_id"
]
