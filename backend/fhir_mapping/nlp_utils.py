# backend/fhir_mapping/nlp_utils.py
import re
import logging
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

def find_nlp_entities_near_keyword(
    text_segment_for_search: str,
    nlp_entities: List[Dict[str, Any]],
    keyword_patterns: List[str],
    target_entity_types: List[str],
    window_size: int = 30,
    search_after_keyword: bool = True
) -> List[Dict[str, Any]]:
    """
    Vyhledá NLP entity daného typu v textovém segmentu v určitém okně okolo pozice klíčového slova.
    """
    found_entities_details = []
    processed_text_segment = text_segment_for_search

    for keyword_pattern in keyword_patterns:
        try:
            for match in re.finditer(keyword_pattern, processed_text_segment, re.IGNORECASE):
                keyword_start, keyword_end = match.span()

                if search_after_keyword:
                    search_window_start = keyword_end
                    search_window_end = keyword_end + window_size
                else:
                    search_window_start = max(0, keyword_start - window_size)
                    search_window_end = keyword_start

                candidate_entities = []
                for entity in nlp_entities:
                    entity_type = entity.get('type')
                    entity_start = entity.get('start_char')
                    entity_end = entity.get('end_char')

                    if entity_type in target_entity_types and \
                       entity_start is not None and entity_end is not None:
                        if entity_start >= search_window_start and entity_end <= search_window_end:
                            candidate_entities.append(entity)
                        elif entity_start >= search_window_start and entity_start < search_window_end:
                             candidate_entities.append(entity)
                        elif entity_end > search_window_start and entity_end <= search_window_end:
                             candidate_entities.append(entity)
                        elif entity_start < search_window_start and entity_end > search_window_end:
                             candidate_entities.append(entity)

                for ent in sorted(candidate_entities, key=lambda x: x['start_char']):
                    if ent not in found_entities_details:
                        found_entities_details.append(ent)
        except re.error as e:
            logger.debug(f"Chyba regexu v find_nlp_entities_near_keyword pro vzor '{keyword_pattern}': {e}")
            continue

    logger.debug(f"Nalezeno {len(found_entities_details)} NLP entit poblíž klíčových slov: {found_entities_details}")
    return sorted(found_entities_details, key=lambda x: x['start_char'])

def extract_value_and_unit_from_nlp_entity_text(
    entity_text: str,
    surrounding_text: str,
    unit_regex_map: Dict[str, str],
    default_unit: Optional[str] = None
) -> Tuple[Optional[str], Optional[str]]:
    """
    Pokusí se z textu NLP entity a jejího okolí extrahovat číselnou hodnotu a její jednotku.
    """
    value_match = re.search(r'(\d+([\.,]\d+)?)', entity_text)
    if not value_match:
        logger.debug(f"extract_value_and_unit: Hodnota nenalezena v textu entity '{entity_text}'.")
        return None, None

    extracted_value_str = value_match.group(1)
    normalized_value_str = extracted_value_str.replace(',', '.')

    search_text_for_unit = entity_text[value_match.end():].strip() + " " + surrounding_text.strip()
    search_text_for_unit = search_text_for_unit.strip()

    found_unit = None
    for standard_unit, unit_regex_pattern in unit_regex_map.items():
        try:
            unit_match = re.search(r"^\s*" + unit_regex_pattern, search_text_for_unit, re.IGNORECASE)
            if unit_match:
                found_unit = standard_unit
                logger.debug(f"extract_value_and_unit: Nalezena jednotka '{found_unit}' pro hodnotu '{normalized_value_str}' v textu '{search_text_for_unit}' (vzor: '{unit_regex_pattern}').")
                break
        except re.error as e:
            logger.debug(f"Chyba regexu v extract_value_and_unit_from_nlp_entity_text pro vzor jednotky '{unit_regex_pattern}': {e}")
            continue

    if not found_unit and default_unit:
        found_unit = default_unit
        logger.debug(f"extract_value_and_unit: Jednotka nenalezena explicitně, použita výchozí jednotka '{default_unit}' pro hodnotu '{normalized_value_str}'.")
    elif not found_unit:
        logger.debug(f"extract_value_and_unit: Jednotka nenalezena a není výchozí pro hodnotu '{normalized_value_str}' v textu '{search_text_for_unit}'.")

    return normalized_value_str, found_unit
