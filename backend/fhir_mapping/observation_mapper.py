# backend/fhir_mapping/observation_mapper.py
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

from .regex_definitions import REGEX_BLOOD_PRESSURE, REGEX_PULSE, REGEX_TEMPERATURE, REGEX_HEIGHT, REGEX_WEIGHT
from .nlp_utils import find_nlp_entities_near_keyword, extract_value_and_unit_from_nlp_entity_text
from .id_utils import generate_fhir_id

logger = logging.getLogger(__name__)

def parse_blood_pressure_data(nlp_entities: Optional[List[Dict[str, Any]]], text: str, quality_issues_list: List[Dict[str, Any]]) -> dict:
    """
    Parsování dat pro krevní tlak z textu.
    (Původně parse_observation_data, přejmenováno pro jasnost)
    """
    observation_data = {}
    found_bp_by_nlp = False

    bp_keywords = [r"\bTK\b", r"Krevní tlak", r"Krevni tlak"]
    bp_target_entity_types = ['CARDINAL', 'NUMBER']
    bp_nlp_window_size = 30

    if nlp_entities and text:
        logger.debug(f"parse_blood_pressure_data: Pokus o NLP extrakci krevního tlaku.")
        for keyword_pattern in bp_keywords:
            for keyword_match in re.finditer(keyword_pattern, text, re.IGNORECASE):
                search_start_offset = keyword_match.end()
                search_end_offset = search_start_offset + bp_nlp_window_size
                candidate_bp_entities = []
                for entity in nlp_entities:
                    if entity.get('type') in bp_target_entity_types and \
                       entity['start_char'] >= search_start_offset and \
                       entity['end_char'] <= search_end_offset:
                        candidate_bp_entities.append(entity)
                candidate_bp_entities.sort(key=lambda x: x['start_char'])

                logger.debug(f"Pro klíčové slovo '{keyword_match.group(0)}', nalezeno {len(candidate_bp_entities)} kandidátských entit: {candidate_bp_entities}")

                if len(candidate_bp_entities) >= 2:
                    systolic_entity = candidate_bp_entities[0]
                    diastolic_entity = candidate_bp_entities[1]
                    systolic_text = systolic_entity['text'].strip()
                    diastolic_text = diastolic_entity['text'].strip()
                    systolic_val_match = re.search(r'\d+', systolic_text)
                    diastolic_val_match = re.search(r'\d+', diastolic_text)

                    if systolic_val_match and diastolic_val_match:
                        s_val = systolic_val_match.group(0)
                        d_val = diastolic_val_match.group(0)
                        bp_value_nlp = f"{s_val}/{d_val}"
                        observation_data["blood_pressure_value"] = bp_value_nlp
                        observation_data["measurement_time_fhir"] = datetime.now().isoformat()
                        found_bp_by_nlp = True
                        logger.debug(f"Nalezen krevní tlak (NLP) pomocí '{keyword_match.group(0)}': {bp_value_nlp}")
                        break
            if found_bp_by_nlp:
                break

    if not found_bp_by_nlp and text:
        bp_match_regex = re.search(REGEX_BLOOD_PRESSURE, text, re.IGNORECASE)
        if bp_match_regex:
            bp_text_regex_capture = bp_match_regex.group(1)
            bp_value_from_regex = "/".join([part.strip() for part in bp_text_regex_capture.split('/')])
            observation_data["blood_pressure_value"] = bp_value_from_regex
            observation_data["measurement_time_fhir"] = datetime.now().isoformat()
            logger.debug(f"Nalezen krevní tlak (Regex fallback): {observation_data['blood_pressure_value']}")
        else:
            quality_issues_list.append({"level": "info", "message": "Krevní tlak nenalezen.", "field": "blood_pressure"})
    elif not text and not nlp_entities and not found_bp_by_nlp :
         quality_issues_list.append({"level": "info", "message": "Krevní tlak nelze hledat - chybí text i NLP entity.", "field": "blood_pressure"})

    return observation_data

def parse_vital_signs_data(nlp_entities: Optional[List[Dict[str, Any]]], text: str, quality_issues_list: List[Dict[str, Any]]) -> dict:
    """
    Parsování textu pro extrakci vitálních funkcí: pulz, teplota, výška a hmotnost.
    """
    vital_signs_data = {}
    vital_sign_target_entity_types = ['CARDINAL', 'NUMBER']
    # Zvětšené okno pro hledání entit, aby zachytilo i kontextově vzdálenější čísla od klíčového slova.
    vital_sign_nlp_window_size = 35
    # Okno pro hledání jednotek za číselnou entitou.
    surrounding_text_window_for_units = 20

    # --- Pulz (Srdeční frekvence) ---
    found_pulse_by_nlp = False
    pulse_keywords = [r"\bPulz\b", r"\bPuls\b", r"\bSF\b", r"Srdeční frekvence", r"Srdecni frekvence", r"Tepová frekvence", r"Tepova frekvence"]
    pulse_unit_regex_map = {"/min": r"/min|tepů/min|tepu/min|bpm|/min\.|za min"}

    if nlp_entities and text:
        logger.debug("parse_vital_signs_data: Pokus o NLP extrakci pro Pulz.")
        relevant_pulse_entities = find_nlp_entities_near_keyword(
            text, nlp_entities, pulse_keywords, vital_sign_target_entity_types,
            window_size=vital_sign_nlp_window_size, search_after_keyword=True
        )
        if relevant_pulse_entities:
            logger.debug(f"Nalezeny relevantní NLP entity pro Pulz: {relevant_pulse_entities}")
            for entity in relevant_pulse_entities:
                entity_text_for_value_extraction = entity['text']
                actual_surrounding_text_start = entity['end_char']
                actual_surrounding_text_end = actual_surrounding_text_start + surrounding_text_window_for_units
                actual_surrounding_text = text[actual_surrounding_text_start:actual_surrounding_text_end]

                value_str, unit_str = extract_value_and_unit_from_nlp_entity_text(
                    entity_text_for_value_extraction,
                    actual_surrounding_text,
                    pulse_unit_regex_map,
                    default_unit="/min"
                )
                if value_str:
                    try:
                        pulse_val_check = float(value_str)
                        if 30 <= pulse_val_check <= 300: # Fyziologický rozsah pro pulz
                            vital_signs_data["pulse_value"] = value_str
                            vital_signs_data["pulse_unit"] = unit_str if unit_str else "/min"
                            found_pulse_by_nlp = True
                            logger.info(f"Nalezen Pulz (NLP): {value_str} {vital_signs_data['pulse_unit']} z entity '{entity['text']}' a okolí '{actual_surrounding_text}'.")
                            break
                        else:
                            logger.debug(f"Hodnota pulzu {pulse_val_check} z NLP je mimo fyziologický rozsah.")
                            quality_issues_list.append({"level": "warning", "message": f"Nalezená hodnota pulzu '{value_str}' ({unit_str}) je mimo očekávaný rozsah.", "field": "pulse_value", "value": value_str})
                    except ValueError:
                        logger.debug(f"Hodnota pulzu z NLP entity '{entity['text']}' není platné číslo: {value_str}")
            if not found_pulse_by_nlp:
                logger.debug("NLP extrakce pulzu nevedla k validní hodnotě/jednotce z nalezených entit.")

    if not found_pulse_by_nlp and text:
        pulse_match_regex = re.search(REGEX_PULSE, text, re.IGNORECASE)
        if pulse_match_regex:
            value_str = pulse_match_regex.group(1).strip()
            try:
                pulse_val_check = float(value_str)
                if 30 <= pulse_val_check <= 300:
                    vital_signs_data["pulse_value"] = value_str
                    unit_match_in_regex = re.search(pulse_unit_regex_map["/min"], pulse_match_regex.group(0), re.IGNORECASE)
                    vital_signs_data["pulse_unit"] = "/min" if unit_match_in_regex else "/min"
                    logger.info(f"Nalezen Pulz (Regex fallback): {vital_signs_data['pulse_value']} {vital_signs_data['pulse_unit']}")
                else:
                    logger.debug(f"Hodnota pulzu {pulse_val_check} z Regex je mimo fyziologický rozsah.")
                    quality_issues_list.append({"level": "warning", "message": f"Nalezená hodnota pulzu '{value_str}' (Regex) je mimo očekávaný rozsah.", "field": "pulse_value", "value": value_str})
            except ValueError:
                 logger.debug(f"Hodnota pulzu z Regex '{value_str}' není platné číslo.")
        elif not vital_signs_data.get("pulse_value"):
            logger.info("Hodnota pulzu nenalezena ani pomocí NLP ani Regex.")
            quality_issues_list.append({"level": "info", "message": "Hodnota pulzu nenalezena.", "field": "pulse_value"})

    # --- Tělesná teplota ---
    found_temp_by_nlp = False
    temp_keywords = [r"\bTeplota\b", r"\bT\s*:", r"\bTT\b", r"Tělesná teplota", r"Telesna teplota"]
    temp_unit_regex_map = {"°C": r"°C|C|st\.C|stupňů Celsia|stC"}
    if nlp_entities and text:
        logger.debug("parse_vital_signs_data: Pokus o NLP extrakci pro Teplotu.")
        relevant_temp_entities = find_nlp_entities_near_keyword(
            text, nlp_entities, temp_keywords, vital_sign_target_entity_types,
            window_size=vital_sign_nlp_window_size, search_after_keyword=True
        )
        if relevant_temp_entities:
            logger.debug(f"Nalezeny relevantní NLP entity pro Teplotu: {relevant_temp_entities}")
            for entity in relevant_temp_entities:
                entity_text_for_value_extraction = entity['text']
                actual_surrounding_text_start = entity['end_char']
                actual_surrounding_text_end = actual_surrounding_text_start + surrounding_text_window_for_units
                actual_surrounding_text = text[actual_surrounding_text_start:actual_surrounding_text_end]

                value_str, unit_str = extract_value_and_unit_from_nlp_entity_text(
                    entity_text_for_value_extraction,
                    actual_surrounding_text,
                    temp_unit_regex_map,
                    default_unit="°C"
                )
                if value_str:
                    try:
                        temp_val_check = float(value_str.replace(",", ".")) # Normalizace desetinné čárky
                        if 30 <= temp_val_check <= 45: # Fyziologický rozsah pro teplotu
                            vital_signs_data["temperature_value"] = str(temp_val_check)
                            vital_signs_data["temperature_unit"] = unit_str if unit_str else "°C"
                            found_temp_by_nlp = True
                            logger.info(f"Nalezena Teplota (NLP): {str(temp_val_check)} {vital_signs_data['temperature_unit']} z entity '{entity['text']}' a okolí '{actual_surrounding_text}'.")
                            break
                        else:
                            logger.debug(f"Hodnota teploty {temp_val_check} z NLP je mimo fyziologický rozsah.")
                            quality_issues_list.append({"level": "warning", "message": f"Nalezená hodnota teploty '{value_str}' ({unit_str}) je mimo očekávaný rozsah.", "field": "temperature_value", "value": value_str})
                    except ValueError:
                        logger.debug(f"Hodnota teploty z NLP entity '{entity['text']}' není platné číslo: {value_str}")
            if not found_temp_by_nlp:
                logger.debug("NLP extrakce teploty nevedla k validní hodnotě/jednotce z nalezených entit.")

    if not found_temp_by_nlp and text:
        temp_match_regex = re.search(REGEX_TEMPERATURE, text, re.IGNORECASE)
        if temp_match_regex:
            value_str = temp_match_regex.group(1).strip().replace(",",".")
            try:
                temp_val_check = float(value_str)
                if 30 <= temp_val_check <= 45:
                    vital_signs_data["temperature_value"] = value_str
                    vital_signs_data["temperature_unit"] = "°C"
                    logger.info(f"Nalezena Teplota (Regex fallback): {vital_signs_data['temperature_value']} {vital_signs_data['temperature_unit']}")
                else:
                    logger.debug(f"Hodnota teploty {temp_val_check} z Regex je mimo fyziologický rozsah.")
                    quality_issues_list.append({"level": "warning", "message": f"Nalezená hodnota teploty '{value_str}' (Regex) je mimo očekávaný rozsah.", "field": "temperature_value", "value": value_str})
            except ValueError:
                logger.debug(f"Hodnota teploty z Regex '{value_str}' není platné číslo.")
        elif not vital_signs_data.get("temperature_value"):
            logger.info("Hodnota teploty nenalezena ani pomocí NLP ani Regex.")
            quality_issues_list.append({"level": "info", "message": "Hodnota teploty nenalezena.", "field": "temperature_value"})

    # --- Tělesná výška ---
    found_height_by_nlp = False
    height_keywords = [r"\bVýška\b", r"\bVýš\.", r"Vyska", r"Výška \(cm\)", r"Výška cm"]
    height_unit_regex_map = {"cm": r"cm|centimetrů", "m": r"m|metrů"} # Podpora pro metry
    if nlp_entities and text:
        logger.debug("parse_vital_signs_data: Pokus o NLP extrakci pro Výšku.")
        relevant_height_entities = find_nlp_entities_near_keyword(
            text, nlp_entities, height_keywords, vital_sign_target_entity_types,
            window_size=vital_sign_nlp_window_size, search_after_keyword=True
        )
        if relevant_height_entities:
            logger.debug(f"Nalezeny relevantní NLP entity pro Výšku: {relevant_height_entities}")
            for entity in relevant_height_entities:
                entity_text_for_value_extraction = entity['text']
                actual_surrounding_text_start = entity['end_char']
                actual_surrounding_text_end = actual_surrounding_text_start + surrounding_text_window_for_units
                actual_surrounding_text = text[actual_surrounding_text_start:actual_surrounding_text_end]

                value_str, unit_str = extract_value_and_unit_from_nlp_entity_text(
                    entity_text_for_value_extraction,
                    actual_surrounding_text,
                    height_unit_regex_map,
                    default_unit="cm" # Default na cm, pokud není specifikováno
                )
                if value_str:
                    try:
                        height_val_check = float(value_str.replace(",", "."))
                        # Převod metrů na cm, pokud je to nutné
                        if unit_str == "m":
                            height_val_check *= 100
                            unit_str = "cm" # Normalizace na cm

                        if 50 <= height_val_check <= 250: # Fyziologický rozsah pro výšku v cm
                            vital_signs_data["height_value"] = str(height_val_check)
                            vital_signs_data["height_unit"] = "cm" # Vždy ukládáme v cm
                            found_height_by_nlp = True
                            logger.info(f"Nalezena Výška (NLP): {str(height_val_check)} cm z entity '{entity['text']}' (pův. jednotka: {unit_str if unit_str else 'neznámá'}) a okolí '{actual_surrounding_text}'.")
                            break
                        else:
                            logger.debug(f"Hodnota výšky {height_val_check} cm z NLP je mimo fyziologický rozsah.")
                            quality_issues_list.append({"level": "warning", "message": f"Nalezená hodnota výšky '{value_str}' (pův. jednotka: {unit_str}) je mimo očekávaný rozsah po převodu na cm.", "field": "height_value", "value": value_str})
                    except ValueError:
                        logger.debug(f"Hodnota výšky z NLP entity '{entity['text']}' není platné číslo: {value_str}")
            if not found_height_by_nlp:
                logger.debug("NLP extrakce výšky nevedla k validní hodnotě/jednotce z nalezených entit.")

    if not found_height_by_nlp and text:
        height_match_regex = re.search(REGEX_HEIGHT, text, re.IGNORECASE)
        if height_match_regex:
            value_str = height_match_regex.group(1).strip().replace(",",".")
            unit_from_regex = height_match_regex.group(2).lower() if height_match_regex.group(2) else "cm"
            try:
                height_val_check = float(value_str)
                if unit_from_regex == "m":
                    height_val_check *= 100

                if 50 <= height_val_check <= 250:
                    vital_signs_data["height_value"] = str(height_val_check)
                    vital_signs_data["height_unit"] = "cm"
                    logger.info(f"Nalezena Výška (Regex fallback): {str(height_val_check)} cm (pův. jednotka z Regex: {unit_from_regex})")
                else:
                    logger.debug(f"Hodnota výšky {height_val_check} cm z Regex je mimo fyziologický rozsah.")
                    quality_issues_list.append({"level": "warning", "message": f"Nalezená hodnota výšky '{value_str}' (Regex, jednotka: {unit_from_regex}) je mimo očekávaný rozsah po převodu na cm.", "field": "height_value", "value": value_str})
            except ValueError:
                logger.debug(f"Hodnota výšky z Regex '{value_str}' není platné číslo.")
        elif not vital_signs_data.get("height_value"):
            logger.info("Hodnota výšky nenalezena ani pomocí NLP ani Regex.")
            quality_issues_list.append({"level": "info", "message": "Hodnota výšky nenalezena.", "field": "height_value"})

    # --- Tělesná hmotnost ---
    found_weight_by_nlp = False
    weight_keywords = [r"\bHmotnost\b", r"\bHm\.", r"\bVáha\b", r"Vaha", r"Hmotnost \(kg\)", r"Váha kg"]
    weight_unit_regex_map = {"kg": r"kg|kilogramů|kilogramy"}
    if nlp_entities and text:
        logger.debug("parse_vital_signs_data: Pokus o NLP extrakci pro Hmotnost.")
        relevant_weight_entities = find_nlp_entities_near_keyword(
            text, nlp_entities, weight_keywords, vital_sign_target_entity_types,
            window_size=vital_sign_nlp_window_size, search_after_keyword=True
        )
        if relevant_weight_entities:
            logger.debug(f"Nalezeny relevantní NLP entity pro Hmotnost: {relevant_weight_entities}")
            for entity in relevant_weight_entities:
                entity_text_for_value_extraction = entity['text']
                actual_surrounding_text_start = entity['end_char']
                actual_surrounding_text_end = actual_surrounding_text_start + surrounding_text_window_for_units
                actual_surrounding_text = text[actual_surrounding_text_start:actual_surrounding_text_end]

                value_str, unit_str = extract_value_and_unit_from_nlp_entity_text(
                    entity_text_for_value_extraction,
                    actual_surrounding_text,
                    weight_unit_regex_map,
                    default_unit="kg"
                )
                if value_str:
                    try:
                        weight_val_check = float(value_str.replace(",", "."))
                        if 1 <= weight_val_check <= 300: # Fyziologický rozsah pro hmotnost
                            vital_signs_data["weight_value"] = str(weight_val_check)
                            vital_signs_data["weight_unit"] = unit_str if unit_str else "kg"
                            found_weight_by_nlp = True
                            logger.info(f"Nalezena Hmotnost (NLP): {str(weight_val_check)} {vital_signs_data['weight_unit']} z entity '{entity['text']}' a okolí '{actual_surrounding_text}'.")
                            break
                        else:
                            logger.debug(f"Hodnota hmotnosti {weight_val_check} z NLP je mimo fyziologický rozsah.")
                            quality_issues_list.append({"level": "warning", "message": f"Nalezená hodnota hmotnosti '{value_str}' ({unit_str}) je mimo očekávaný rozsah.", "field": "weight_value", "value": value_str})
                    except ValueError:
                        logger.debug(f"Hodnota hmotnosti z NLP entity '{entity['text']}' není platné číslo: {value_str}")
            if not found_weight_by_nlp:
                logger.debug("NLP extrakce hmotnosti nevedla k validní hodnotě/jednotce z nalezených entit.")

    if not found_weight_by_nlp and text:
        weight_match_regex = re.search(REGEX_WEIGHT, text, re.IGNORECASE)
        if weight_match_regex:
            value_str = weight_match_regex.group(1).strip().replace(",",".")
            try:
                weight_val_check = float(value_str)
                if 1 <= weight_val_check <= 300:
                    vital_signs_data["weight_value"] = value_str
                    # Regex pro hmotnost by měl zachytit jednotku ve skupině 2, ale pro jistotu default
                    unit_from_regex = weight_match_regex.group(2).lower() if weight_match_regex.group(2) and weight_match_regex.group(2).lower() == "kg" else "kg"
                    vital_signs_data["weight_unit"] = unit_from_regex
                    logger.info(f"Nalezena Hmotnost (Regex fallback): {vital_signs_data['weight_value']} {vital_signs_data['weight_unit']}")
                else:
                    logger.debug(f"Hodnota hmotnosti {weight_val_check} z Regex je mimo fyziologický rozsah.")
                    quality_issues_list.append({"level": "warning", "message": f"Nalezená hodnota hmotnosti '{value_str}' (Regex) je mimo očekávaný rozsah.", "field": "weight_value", "value": value_str})
            except ValueError:
                logger.debug(f"Hodnota hmotnosti z Regex '{value_str}' není platné číslo.")
        elif not vital_signs_data.get("weight_value"):
            logger.info("Hodnota hmotnosti nenalezena ani pomocí NLP ani Regex.")
            quality_issues_list.append({"level": "info", "message": "Hodnota hmotnosti nenalezena.", "field": "weight_value"})

    if not text and not nlp_entities and not vital_signs_data: # Kontrola, zda byla nějaká data k dispozici
        logger.info("parse_vital_signs_data: Nelze hledat vitální funkce - chybí text i NLP entity.")
        # Přidání obecného quality issue, pokud žádná data nebyla nalezena a nebyly ani vstupy
        if not quality_issues_list: # Jen pokud ještě nebyly přidány specifické issues
             quality_issues_list.append({"level": "info", "message": "Nebyly poskytnuty žádné vstupní data (text/NLP) pro parsování vitálních funkcí."})
    elif not vital_signs_data: # Pokud byly vstupy, ale nic se nenašlo
        logger.info("parse_vital_signs_data: Nepodařilo se extrahovat žádné vitální funkce.")
        # quality_issues_list již budou obsahovat zprávy pro jednotlivé nenalezené funkce

    return vital_signs_data


# --- Funkce pro vytváření jednotlivých FHIR Observation zdrojů ---
# (create_fhir_observation_bp_resource, create_fhir_observation_pulse_resource, atd. budou zde)
# Pro zkrácení je zde neuvádím celé, ale budou zkopírovány z fhir_mapper.py

def create_fhir_observation_bp_resource(observation_data: dict, patient_reference_id: str) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    # ... (obsah z fhir_mapper.py) ...
    issues_list: List[Dict[str, Any]] = [] # Placeholder
    bp_value = observation_data.get("blood_pressure_value")
    if not bp_value: return None, issues_list # Zjednodušená logika
    try:
        systolic_str, diastolic_str = bp_value.split('/')
        systolic = int(systolic_str.strip())
        diastolic = int(diastolic_str.strip())
    except ValueError:
        issues_list.append({"level": "error", "message": f"Neplatný formát BP: {bp_value}", "field": "blood_pressure_value", "value": bp_value})
        return None, issues_list

    resource_id = generate_fhir_id()
    resource = {
        "resourceType": "Observation", "id": resource_id, "status": "final",
        "code": {"text": "Krevní tlak"}, "subject": {"reference": patient_reference_id},
        "effectiveDateTime": observation_data.get("measurement_time_fhir", datetime.now().isoformat()),
        "component": [
            {"code": {"text": "Systolický"}, "valueQuantity": {"value": systolic, "unit": "mmHg"}},
            {"code": {"text": "Diastolický"}, "valueQuantity": {"value": diastolic, "unit": "mmHg"}}
        ]
    } # Zjednodušený resource pro ukázku
    logger.debug(f"Vytvořen FHIR Observation (BP) resource (ID: {resource_id}).")
    return resource, issues_list


def create_fhir_observation_pulse_resource(observation_data: dict, patient_reference_id: str) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    # ... (obsah z fhir_mapper.py) ...
    issues_list: List[Dict[str, Any]] = [] # Placeholder
    pulse_value_str = observation_data.get("pulse_value")
    if not pulse_value_str: return None, issues_list
    try:
        pulse_val = int(pulse_value_str)
    except ValueError:
        issues_list.append({"level": "error", "message": f"Neplatná hodnota pulzu: {pulse_value_str}", "field": "pulse_value", "value": pulse_value_str})
        return None, issues_list

    resource_id = generate_fhir_id()
    resource = {
        "resourceType": "Observation", "id": resource_id, "status": "final",
        "code": {"text": "Pulz"}, "subject": {"reference": patient_reference_id},
        "effectiveDateTime": datetime.now().isoformat(),
        "valueQuantity": {"value": pulse_val, "unit": observation_data.get("pulse_unit", "/min")}
    } # Zjednodušený resource
    logger.debug(f"Vytvořen FHIR Observation (Pulz) resource (ID: {resource_id}).")
    return resource, issues_list

def create_fhir_observation_temperature_resource(observation_data: dict, patient_reference_id: str) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    # ... (obsah z fhir_mapper.py) ...
    issues_list: List[Dict[str, Any]] = []
    temp_value_str = observation_data.get("temperature_value")
    if not temp_value_str: return None, issues_list
    try:
        temp_val = float(temp_value_str.replace(",","."))
    except ValueError:
        issues_list.append({"level": "error", "message": f"Neplatná hodnota teploty: {temp_value_str}", "field": "temperature_value", "value": temp_value_str})
        return None, issues_list

    resource_id = generate_fhir_id()
    resource = {
        "resourceType": "Observation", "id": resource_id, "status": "final",
        "code": {"text": "Tělesná teplota"}, "subject": {"reference": patient_reference_id},
        "effectiveDateTime": datetime.now().isoformat(),
        "valueQuantity": {"value": temp_val, "unit": observation_data.get("temperature_unit", "°C")}
    } # Zjednodušený resource
    logger.debug(f"Vytvořen FHIR Observation (Teplota) resource (ID: {resource_id}).")
    return resource, issues_list

def create_fhir_observation_height_resource(observation_data: dict, patient_reference_id: str) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    # ... (obsah z fhir_mapper.py) ...
    issues_list: List[Dict[str, Any]] = []
    height_value_str = observation_data.get("height_value")
    if not height_value_str: return None, issues_list
    try:
        height_val = float(height_value_str.replace(",","."))
    except ValueError:
        issues_list.append({"level": "error", "message": f"Neplatná hodnota výšky: {height_value_str}", "field": "height_value", "value": height_value_str})
        return None, issues_list

    resource_id = generate_fhir_id()
    resource = {
        "resourceType": "Observation", "id": resource_id, "status": "final",
        "code": {"text": "Tělesná výška"}, "subject": {"reference": patient_reference_id},
        "effectiveDateTime": datetime.now().isoformat(),
        "valueQuantity": {"value": height_val, "unit": observation_data.get("height_unit", "cm")}
    } # Zjednodušený resource
    logger.debug(f"Vytvořen FHIR Observation (Výška) resource (ID: {resource_id}).")
    return resource, issues_list

def create_fhir_observation_weight_resource(observation_data: dict, patient_reference_id: str) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    # ... (obsah z fhir_mapper.py) ...
    issues_list: List[Dict[str, Any]] = []
    weight_value_str = observation_data.get("weight_value")
    if not weight_value_str: return None, issues_list
    try:
        weight_val = float(weight_value_str.replace(",","."))
    except ValueError:
        issues_list.append({"level": "error", "message": f"Neplatná hodnota hmotnosti: {weight_value_str}", "field": "weight_value", "value": weight_value_str})
        return None, issues_list

    resource_id = generate_fhir_id()
    resource = {
        "resourceType": "Observation", "id": resource_id, "status": "final",
        "code": {"text": "Tělesná hmotnost"}, "subject": {"reference": patient_reference_id},
        "effectiveDateTime": datetime.now().isoformat(),
        "valueQuantity": {"value": weight_val, "unit": observation_data.get("weight_unit", "kg")}
    } # Zjednodušený resource
    logger.debug(f"Vytvořen FHIR Observation (Hmotnost) resource (ID: {resource_id}).")
    return resource, issues_list
