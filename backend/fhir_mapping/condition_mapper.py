# backend/fhir_mapping/condition_mapper.py
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

from .regex_definitions import REGEX_DIAGNOSIS_TEXT
from .nlp_utils import find_nlp_entities_near_keyword # V parse_condition_data se používá
from .id_utils import generate_fhir_id

logger = logging.getLogger(__name__)

def parse_condition_data(nlp_entities: Optional[List[Dict[str, Any]]], text: str, quality_issues_list: List[Dict[str, Any]]) -> dict:
    """
    Parsování textu diagnózy z lékařské zprávy.
    """
    condition_data = {}
    found_diagnosis_by_nlp = False

    diagnosis_keywords = [r"Diagnóza\s*:", r"Dg\.\s*:", r"Závěr\s*:", r"Zaver\s*:"]
    diagnosis_entity_type = 'DIS'
    diag_keyword_proximity_window = 150
    max_gap_between_dis_entities = 20 # Maximální počet znaků mezi DIS entitami pro jejich spojení

    if nlp_entities and text:
        logger.debug(f"parse_condition_data: Pokus o NLP extrakci diagnózy.")
        all_dis_entities_near_keywords = []

        # Hledání entit typu DIS blízko klíčových slov
        # Tento blok je zjednodušený, find_nlp_entities_near_keyword by se mělo použít správně
        # nebo použít logiku z původního fhir_mapper.py
        for kw_pattern in diagnosis_keywords:
            for kw_match in re.finditer(kw_pattern, text, re.IGNORECASE):
                kw_end_pos = kw_match.end()
                for entity in nlp_entities:
                    if entity.get('type') == diagnosis_entity_type and \
                       entity['start_char'] >= kw_end_pos and \
                       entity['start_char'] < kw_end_pos + diag_keyword_proximity_window:
                        if entity not in all_dis_entities_near_keywords:
                             all_dis_entities_near_keywords.append(entity)

        if all_dis_entities_near_keywords:
            all_dis_entities_near_keywords.sort(key=lambda x: x['start_char'])
            logger.debug(f"Nalezeno {len(all_dis_entities_near_keywords)} DIS entit v blízkosti klíčových slov: {[e['text'] for e in all_dis_entities_near_keywords]}")

            # Zde by následovala logika pro spojování DIS entit, pokud je jich více
            # a jsou blízko sebe, jak bylo v původním fhir_mapper.py
            # Pro zjednodušení zde vezmeme text první nalezené entity.
            if all_dis_entities_near_keywords: # Pokud nějaké jsou
                # Tato část by měla obsahovat logiku pro spojování entit.
                # Pro jednoduchost nyní vezmeme první.
                selected_entity_text = all_dis_entities_near_keywords[0]['text']
                # Odebrání teček, čárek, středníků na konci
                diagnosis_text_raw_nlp = re.sub(r'[\.,;\s]$', '', selected_entity_text).strip()
                condition_data["diagnosis_text"] = diagnosis_text_raw_nlp
                condition_data["onset_date_time_fhir"] = datetime.now().isoformat() # Fallback čas
                found_diagnosis_by_nlp = True
                logger.debug(f"Nalezena diagnóza (NLP): '{condition_data['diagnosis_text']}'")

    if not found_diagnosis_by_nlp and text:
        diagnosis_match = re.search(REGEX_DIAGNOSIS_TEXT, text, re.IGNORECASE | re.DOTALL)
        if diagnosis_match:
            diagnosis_text_raw_regex = diagnosis_match.group(1).strip()
            condition_data["diagnosis_text"] = re.sub(r'[\.,;]$', '', diagnosis_text_raw_regex).strip()
            condition_data["onset_date_time_fhir"] = datetime.now().isoformat()
            logger.debug(f"Nalezena diagnóza (Regex fallback): '{condition_data['diagnosis_text']}'")
        else:
            quality_issues_list.append({"level": "info", "message": "Diagnóza nenalezena.", "field": "diagnosis_text"})
    elif not text and not found_diagnosis_by_nlp:
        quality_issues_list.append({"level": "info", "message": "Diagnóza nenalezena (NLP neúspěšné a chybí text pro Regex).", "field": "diagnosis_text"})

    return condition_data

def create_fhir_condition_resource(condition_data: dict, patient_reference_id: str) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Vytváří FHIR Condition resource pro diagnózu.
    """
    issues_list: List[Dict[str, Any]] = []
    resource: Optional[Dict[str, Any]] = None
    diagnosis_text = condition_data.get("diagnosis_text")

    if not diagnosis_text:
        issues_list.append({"level": "info", "message": "Chybí text diagnózy pro vytvoření FHIR Condition.", "field": "diagnosis_text"})
        return None, issues_list

    resource_id = generate_fhir_id()
    current_time_iso = datetime.now().isoformat()
    recorded_date_to_check = condition_data.get("onset_date_time_fhir", current_time_iso)

    try:
        # Jednoduchá validace data, plná validace by byla robustnější
        dt_to_check = datetime.fromisoformat(str(recorded_date_to_check).rstrip('Z'))
        if dt_to_check > datetime.now() + timedelta(days=1):
            issues_list.append({"level": "warning", "message": f"recordedDate pro Condition ('{recorded_date_to_check}') je v daleké budoucnosti.", "field": "condition_recorded_date", "value": recorded_date_to_check})
    except Exception as e: # Zachytí širší spektrum chyb při parsování data
        issues_list.append({"level": "warning", "message": f"Chyba při validaci recordedDate pro Condition ('{recorded_date_to_check}'): {e}", "field": "condition_recorded_date", "value": recorded_date_to_check})


    resource = {
        "resourceType": "Condition",
        "id": resource_id,
        "meta": {"profile": ["https://ncez.mzcr.cz/fhir/core/StructureDefinition/CzCondition"]},
        "clinicalStatus": {
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active", "display": "Active"}]
        },
        "verificationStatus": {
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-ver-status", "code": "confirmed", "display": "Confirmed"}]
        },
        "category": [{
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-category", "code": "encounter-diagnosis", "display": "Encounter Diagnosis"}]
        }],
        "code": {
            "text": diagnosis_text
        },
        "subject": {"reference": patient_reference_id},
        "recordedDate": recorded_date_to_check
    }
    logger.debug(f"Vytvořen FHIR Condition (Diagnóza) resource (ID: {resource_id}).")
    return resource, issues_list
