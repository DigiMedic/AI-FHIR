# backend/fhir_mapping/id_utils.py
import uuid
import logging

logger = logging.getLogger(__name__)

def generate_fhir_id() -> str:
    """
    Generuje unikátní identifikátor (UUID) pro FHIR zdroje.

    Returns:
        Řetězec reprezentující UUID.
    """
    new_id = str(uuid.uuid4())
    logger.debug(f"Generated new FHIR ID: {new_id}")
    return new_id
