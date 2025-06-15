# backend/fhir_mapping/orchestrator.py
import logging
from typing import Union, List, Dict, Any, Optional

# Importy z nově vytvořených modulů
from .patient_mapper import parse_patient_data, create_fhir_patient_resource
from .observation_mapper import parse_blood_pressure_data, parse_vital_signs_data, \
                                create_fhir_observation_bp_resource, \
                                create_fhir_observation_pulse_resource, \
                                create_fhir_observation_temperature_resource, \
                                create_fhir_observation_height_resource, \
                                create_fhir_observation_weight_resource
from .condition_mapper import parse_condition_data, create_fhir_condition_resource
# generate_fhir_id se používá v builderech, takže zde není přímo potřeba, pokud ho nevoláme explicitně

logger = logging.getLogger(__name__)

def map_text_to_fhir(processed_input: Union[str, List[Dict[str, Any]]], original_text: Optional[str] = None) -> Dict[str, List[Any]]:
    """
    Hlavní funkce pro mapování textu lékařské zprávy na FHIR zdroje a problémy s kvalitou.
    Orchestruje parsování a tvorbu FHIR zdrojů voláním funkcí z ostatních modulů.
    """
    fhir_resources: List[Dict[str, Any]] = []
    aggregated_quality_issues_list: List[Dict[str, Any]] = []

    nlp_entities: Optional[List[Dict[str, Any]]] = None
    text_to_parse_with_regex: str = ""

    if isinstance(processed_input, list):
        nlp_entities = processed_input
        if original_text:
            text_to_parse_with_regex = original_text
        else:
            aggregated_quality_issues_list.append({
                "level": "warning",
                "message": "NLP entity byly poskytnuty, ale chybí original_text. Regex fallback nebude spolehlivý.",
                "field": "original_text_input"
            })
            text_to_parse_with_regex = " "
    elif isinstance(processed_input, str):
        text_to_parse_with_regex = processed_input
    else:
        aggregated_quality_issues_list.append({
            "level": "critical",
            "message": f"Neočekávaný typ vstupních dat: {type(processed_input)}. Očekáván str nebo List[Dict].",
            "field": "processed_input_type"
        })
        return {"fhir_resources": [], "quality_issues": aggregated_quality_issues_list}

    text_for_regex_parsers = text_to_parse_with_regex

    if (not text_for_regex_parsers or not text_for_regex_parsers.strip()) and not nlp_entities:
        aggregated_quality_issues_list.append({
            "level": "error",
            "message": "Vstupní text i NLP entity jsou prázdné. Nelze zpracovat.",
            "field": "input_data"
        })
        return {"fhir_resources": [], "quality_issues": aggregated_quality_issues_list}

    patient_ref_id: Optional[str] = None
    logger.info(f"Zahájení mapování textu na FHIR. Vstupní typ: {'NLP entity' if nlp_entities else 'Čistý text'}.")

    # 1. Parsovat a vytvořit pacienta
    extracted_patient_data = parse_patient_data(nlp_entities, text_for_regex_parsers, aggregated_quality_issues_list)
    patient_resource, patient_creation_issues = create_fhir_patient_resource(extracted_patient_data)
    aggregated_quality_issues_list.extend(patient_creation_issues)
    if patient_resource:
        fhir_resources.append(patient_resource)
        patient_ref_id = f"Patient/{patient_resource['id']}"
        logger.info(f"Patient resource úspěšně vytvořen (ID: {patient_resource['id']}).")
    else:
        aggregated_quality_issues_list.append({
            "level": "critical",
            "message": "Patient resource nemohl být vytvořen. Další navázané FHIR zdroje nebudou generovány.",
            "field": "Patient"
        })
        # V tomto případě nemá smysl pokračovat, protože ostatní zdroje závisí na pacientovi
        return {"fhir_resources": fhir_resources, "quality_issues": aggregated_quality_issues_list}

    # 2. Parsovat a vytvořit Observation pro krevní tlak
    # Použijeme parse_blood_pressure_data (přejmenováno z parse_observation_data)
    extracted_bp_data = parse_blood_pressure_data(nlp_entities, text_for_regex_parsers, aggregated_quality_issues_list)
    if extracted_bp_data.get("blood_pressure_value"):
        observation_bp_resource, bp_creation_issues = create_fhir_observation_bp_resource(extracted_bp_data, patient_ref_id)
        aggregated_quality_issues_list.extend(bp_creation_issues)
        if observation_bp_resource:
            fhir_resources.append(observation_bp_resource)
            logger.info(f"Observation (BP) resource úspěšně vytvořen (ID: {observation_bp_resource['id']}).")

    # 3. Parsovat a vytvořit Observations pro další vitální funkce
    vital_signs_data = parse_vital_signs_data(nlp_entities, text_for_regex_parsers, aggregated_quality_issues_list)

    if vital_signs_data.get("pulse_value"):
        pulse_resource, pulse_creation_issues = create_fhir_observation_pulse_resource(vital_signs_data, patient_ref_id)
        aggregated_quality_issues_list.extend(pulse_creation_issues)
        if pulse_resource:
            fhir_resources.append(pulse_resource)
            logger.info(f"Observation (Pulz) resource úspěšně vytvořen (ID: {pulse_resource['id']}).")

    if vital_signs_data.get("temperature_value"):
        temperature_resource, temp_creation_issues = create_fhir_observation_temperature_resource(vital_signs_data, patient_ref_id)
        aggregated_quality_issues_list.extend(temp_creation_issues)
        if temperature_resource:
            fhir_resources.append(temperature_resource)
            logger.info(f"Observation (Teplota) resource úspěšně vytvořen (ID: {temperature_resource['id']}).")

    if vital_signs_data.get("height_value"):
        height_resource, height_creation_issues = create_fhir_observation_height_resource(vital_signs_data, patient_ref_id)
        aggregated_quality_issues_list.extend(height_creation_issues)
        if height_resource:
            fhir_resources.append(height_resource)
            logger.info(f"Observation (Výška) resource úspěšně vytvořen (ID: {height_resource['id']}).")

    if vital_signs_data.get("weight_value"):
        weight_resource, weight_creation_issues = create_fhir_observation_weight_resource(vital_signs_data, patient_ref_id)
        aggregated_quality_issues_list.extend(weight_creation_issues)
        if weight_resource:
            fhir_resources.append(weight_resource)
            logger.info(f"Observation (Hmotnost) resource úspěšně vytvořen (ID: {weight_resource['id']}).")

    # 4. Parsovat a vytvořit Condition pro diagnózu
    extracted_condition_data = parse_condition_data(nlp_entities, text_for_regex_parsers, aggregated_quality_issues_list)
    if extracted_condition_data.get("diagnosis_text"):
        condition_resource, cond_creation_issues = create_fhir_condition_resource(extracted_condition_data, patient_ref_id)
        aggregated_quality_issues_list.extend(cond_creation_issues)
        if condition_resource:
            fhir_resources.append(condition_resource)
            logger.info(f"Condition (Diagnóza) resource úspěšně vytvořen (ID: {condition_resource['id']}).")

    if not fhir_resources:
        logger.info("Nebyly vytvořeny žádné FHIR zdroje.")
    logger.info(f"Celkem vytvořeno {len(fhir_resources)} FHIR zdrojů.")
    logger.debug(f"Celkem {len(aggregated_quality_issues_list)} problémů s kvalitou zaznamenáno.")

    return {"fhir_resources": fhir_resources, "quality_issues": aggregated_quality_issues_list}
