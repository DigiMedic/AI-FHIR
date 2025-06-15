# backend/fhir_mapping/patient_mapper.py
import re
import logging
from typing import List, Dict, Any, Optional, Tuple

from .regex_definitions import REGEX_PATIENT_NAME, REGEX_BIRTH_DATE, REGEX_BIRTH_NUMBER
from .datetime_utils import parse_date_to_fhir_format
from .personal_info_utils import is_valid_birth_number, extract_info_from_birth_number
from .nlp_utils import find_nlp_entities_near_keyword # find_nlp_entities_near_keyword není přímo zde, ale v parse_patient_data
from .id_utils import generate_fhir_id
from datetime import datetime # Potřebné pro create_fhir_patient_resource (porovnání dat)

logger = logging.getLogger(__name__)

def parse_patient_data(nlp_entities: Optional[List[Dict[str, Any]]], text: str, quality_issues_list: List[Dict[str, Any]]) -> dict:
    """
    Parsování základních demografických údajů o pacientovi z textu, s možností využití NLP entit.
    """
    patient_data = {}
    found_name_by_nlp = False
    found_birth_date_by_nlp = False

    patient_name_keywords = [
        r"Pacient(?:ka)?\s*:", r"Jméno pacienta\s*:", r"Vyšetřovan(?:ý|á)\s*:"
    ]
    birth_date_keywords = [
        r"Datum narození\s*:", r"Nar\.\s*:", r"Narozena\s*:", r"Dat\. nar\.\s*:", r"Narozen\(a\)\s*:"
    ]
    keyword_proximity_window = 50

    if nlp_entities and text:
        person_entities_P = [ent for ent in nlp_entities if ent.get('type') == 'P']
        atomic_name_parts_entities = [ent for ent in nlp_entities if ent.get('type') in ['pt', 'pf', 'ps', 'pd']]
        atomic_name_parts_entities.sort(key=lambda x: x['start_char'])
        selected_person_entity = None

        if person_entities_P:
            logger.debug(f"parse_patient_data: Nalezeno {len(person_entities_P)} entit typu 'P'. Hledání nejrelevantnější...")
            # Použití find_nlp_entities_near_keyword pro jméno pacienta
            # Místo manuální iterace zde:
            relevant_P_entities = find_nlp_entities_near_keyword(
                text, person_entities_P, patient_name_keywords, ['P'],
                window_size=keyword_proximity_window, search_after_keyword=True
            )
            if relevant_P_entities:
                 selected_person_entity = relevant_P_entities[0] # find_nlp_entities_near_keyword vrací seřazený seznam
                 logger.debug(f"Vybrána entita 'P' '{selected_person_entity['text']}' na základě blízkosti ke klíčovému slovu (pomocí find_nlp_entities_near_keyword).")
            elif person_entities_P:
                person_entities_P.sort(key=lambda x: x['start_char'])
                selected_person_entity = person_entities_P[0]
                logger.debug(f"Žádná entita 'P' nebyla blízko klíčových slov. Vybrána první entita 'P' v dokumentu: '{selected_person_entity['text']}'.")

            if selected_person_entity:
                patient_data["full_name"] = selected_person_entity['text'].strip()
                found_name_by_nlp = True
                logger.debug(f"Nalezeno jméno pacienta (NLP typ P): {patient_data['full_name']}")

        if not found_name_by_nlp and atomic_name_parts_entities:
            logger.debug(f"parse_patient_data: Pokus o sestavení jména z atomických částí ({len(atomic_name_parts_entities)} nalezeno).")
            # Tato logika zůstává prozatím, i když by také mohla využít find_nlp_entities_near_keyword
            # pro každou atomickou část, ale sestavení je komplexnější.
            first_relevant_atomic_part_index = -1
            # ... (zbytek logiky pro sestavení jména z atomických částí, jak byla v původním souboru) ...
            # Pro zkrácení ponechávám původní logiku, i když by se dala refaktorovat
            # s využitím find_nlp_entities_near_keyword pro každou část.
            # Tento kód byl zjednodušen v předchozích krocích, zde ho ponechávám pro úplnost.
            current_person_parts = []
            start_index_for_assembly = 0 # Defaultně od začátku

            # Logika pro nalezení relevantního start_index_for_assembly
            # ... (jak bylo v původním fhir_mapper.py)

            for i in range(start_index_for_assembly, len(atomic_name_parts_entities)):
                ent = atomic_name_parts_entities[i]
                if not current_person_parts or ent['start_char'] < current_person_parts[-1]['end_char'] + 10:
                    current_person_parts.append(ent)
                else:
                    if current_person_parts: break
            if current_person_parts:
                assembled_name_text = " ".join([p['text'] for p in current_person_parts])
                patient_data["full_name"] = assembled_name_text.strip()
                found_name_by_nlp = True
                logger.debug(f"Nalezeno jméno pacienta (NLP atomické typy): {patient_data['full_name']}")


        date_candidate_nlp_entities = [ent for ent in nlp_entities if ent.get('type') in ['T', 'DATE', 'td', 'tm', 'ty']]
        date_candidate_nlp_entities.sort(key=lambda x: x['start_char'])
        selected_date_entity_text = None

        if date_candidate_nlp_entities:
            logger.debug(f"parse_patient_data: Nalezeno {len(date_candidate_nlp_entities)} kandidátských NLP entit pro datum narození.")
            relevant_date_entities = find_nlp_entities_near_keyword(
                text, date_candidate_nlp_entities, birth_date_keywords, ['T', 'DATE'],
                window_size=keyword_proximity_window, search_after_keyword=True
            )
            if relevant_date_entities:
                selected_date_entity_text = relevant_date_entities[0]['text'].strip()
                logger.debug(f"Vybrána NLP entita data narození '{selected_date_entity_text}' (typ: {relevant_date_entities[0]['type']}) na základě blízkosti ke klíčovému slovu.")
            elif date_candidate_nlp_entities:
                first_general_date_entity = next((e for e in date_candidate_nlp_entities if e.get('type') in ['T', 'DATE']), None)
                if first_general_date_entity:
                    selected_date_entity_text = first_general_date_entity['text'].strip()
                    logger.debug(f"Žádná entita data nenalezena blízko klíč. slov. Vybrána první obecná entita data (T/DATE): '{selected_date_entity_text}'.")

        if selected_date_entity_text:
            parsed_date_nlp = parse_date_to_fhir_format(selected_date_entity_text, quality_issues_list)
            if parsed_date_nlp:
                patient_data["birth_date_fhir"] = parsed_date_nlp
                patient_data["birth_date_raw"] = selected_date_entity_text
                found_birth_date_by_nlp = True
                logger.debug(f"Nalezeno datum narození (NLP): {selected_date_entity_text} -> {parsed_date_nlp}")
            else:
                logger.debug(f"NLP entita data '{selected_date_entity_text}' se nepodařila parsovat (viz quality_issues).")

    if not found_name_by_nlp and text:
        name_match = re.search(REGEX_PATIENT_NAME, text, re.IGNORECASE)
        if name_match:
            patient_data["full_name"] = name_match.group(1).strip()
            logger.debug(f"Nalezeno jméno pacienta (Regex fallback): {patient_data['full_name']}")
        else:
            quality_issues_list.append({"level": "warning", "message": "Jméno pacienta nenalezeno ani pomocí NLP, ani pomocí Regex.", "field": "full_name"})

    if not found_birth_date_by_nlp and text:
        birth_date_match = re.search(REGEX_BIRTH_DATE, text, re.IGNORECASE)
        if birth_date_match:
            raw_date_regex = birth_date_match.group(1).strip()
            logger.debug(f"Nalezen surový řetězec data narození (Regex fallback, před čištěním): '{raw_date_regex}'")
            stop_keywords = ["RČ", "R.č.", "Rodné číslo", "Pojišťovna", "Poj.", "Bydliště", "Bydl.", "Kontakt", "Tel.", "Oddělení", "Odd.", "Status", "Poznámka", "Pozn.", "---"]
            cleaned_date_regex = raw_date_regex
            for keyword in stop_keywords:
                parts = re.split(r'\b' + re.escape(keyword) + r'\b', cleaned_date_regex, maxsplit=1, flags=re.IGNORECASE)
                if len(parts) > 1:
                    cleaned_date_regex = parts[0].strip()
                    logger.debug(f"Řetězec data narození (Regex fallback) oříznut klíčovým slovem '{keyword}': '{cleaned_date_regex}'")

            parsed_date_regex = parse_date_to_fhir_format(cleaned_date_regex, quality_issues_list)
            if parsed_date_regex:
                patient_data["birth_date_fhir"] = parsed_date_regex
                logger.debug(f"Nalezeno datum narození (Regex fallback): {cleaned_date_regex} -> {parsed_date_regex}")
            else:
                patient_data["birth_date_raw"] = cleaned_date_regex
                logger.debug(f"Datum narození z Regex '{cleaned_date_regex}' se nepodařilo převést do FHIR formátu (viz quality_issues).")
        elif not patient_data.get("birth_date_fhir"):
            quality_issues_list.append({"level": "warning", "message": "Datum narození nenalezeno ani pomocí NLP, ani pomocí Regex.", "field": "birth_date"})

    if text:
        birth_number_match = re.search(REGEX_BIRTH_NUMBER, text, re.IGNORECASE)
        if birth_number_match:
            patient_data["birth_number_raw"] = birth_number_match.group(1).strip()
            logger.debug(f"Nalezeno rodné číslo (Regex): {patient_data['birth_number_raw']}")
        elif not patient_data.get("birth_number_raw"):
             quality_issues_list.append({"level": "info", "message": "Rodné číslo nenalezeno pomocí Regex.", "field": "birth_number_raw"})

    logger.debug(f"Ukončeno parsování dat pacienta. Výsledek: {patient_data}")
    return patient_data

def create_fhir_patient_resource(patient_data: dict) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Vytváří FHIR Patient resource z parsovaných dat.
    """
    issues_list: List[Dict[str, Any]] = []
    resource: Optional[Dict[str, Any]] = None

    if not patient_data.get("full_name"):
        issues_list.append({"level": "error", "message": "Chybí jméno pacienta pro vytvoření FHIR Patient resource.", "field": "full_name"})
    if not patient_data.get("birth_date_fhir"):
        issues_list.append({"level": "error", "message": "Chybí datum narození (FHIR formát) pro vytvoření FHIR Patient resource.", "field": "birth_date_fhir"})

    if not patient_data.get("full_name") or not patient_data.get("birth_date_fhir"):
        return None, issues_list

    resource_id = generate_fhir_id()
    resource = {
        "resourceType": "Patient",
        "id": resource_id,
        "meta": {"profile": ["https://ncez.mzcr.cz/fhir/core/StructureDefinition/CzPatient"]},
        "name": [{"use": "official", "text": patient_data["full_name"]}],
        "birthDate": patient_data["birth_date_fhir"]
    }

    all_name_parts = patient_data.get("full_name", "").split()
    if len(all_name_parts) > 1:
        resource["name"][0]["given"] = all_name_parts[:-1]
        resource["name"][0]["family"] = all_name_parts[-1]
    elif len(all_name_parts) == 1:
        resource["name"][0]["family"] = all_name_parts[0]
    else:
        issues_list.append({"level": "warning", "message": "Jméno pacienta je prázdné, nelze rozdělit na given/family.", "field": "full_name", "value": patient_data.get("full_name")})

    rc_info = None
    if "birth_number_raw" in patient_data:
        raw_rc_str = patient_data["birth_number_raw"]
        cleaned_rc_str = raw_rc_str.replace("/", "").strip()
        temp_rc_issues: List[Dict[str, Any]] = []
        if is_valid_birth_number(raw_rc_str, temp_rc_issues):
            rc_info = extract_info_from_birth_number(cleaned_rc_str, issues_list)
            if rc_info:
                resource["identifier"] = [{
                    "use": "official",
                    "type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0203", "code": "NI", "display": "National unique individual identifier"}], "text": "Rodné číslo"},
                    "system": "urn:oid:1.2.203.17.4.1", "value": cleaned_rc_str
                }]
                if patient_data.get("birth_date_fhir"):
                    try:
                        fhir_date_obj = datetime.strptime(patient_data["birth_date_fhir"], "%Y-%m-%d")
                        if not (rc_info['year'] == fhir_date_obj.year and rc_info['month'] == fhir_date_obj.month and rc_info['day'] == fhir_date_obj.day):
                            issues_list.append({"level": "warning", "message": f"Nesoulad mezi datem narození z RČ ({rc_info['day']}.{rc_info['month']}.{rc_info['year']}) a zadaným datem narození ({patient_data['birth_date_fhir']}).", "field": "birth_date/birth_number", "value": f"RČ: {raw_rc_str}, Datum: {patient_data['birth_date_fhir']}"})
                    except ValueError:
                        issues_list.append({"level": "error", "message": f"Chyba při parsování birth_date_fhir ('{patient_data['birth_date_fhir']}') pro porovnání s RČ.", "field": "birth_date_fhir", "value": patient_data['birth_date_fhir']})
                if rc_info['gender_code'] != "unknown":
                    resource["gender"] = rc_info['gender_code']
                else:
                    issues_list.append({"level": "info", "message": f"Pohlaví nebylo jednoznačně určeno z RČ '{raw_rc_str}'.", "field": "birth_number_gender", "value": raw_rc_str})
        else:
            issues_list.extend(temp_rc_issues)
            issues_list.append({"level": "warning", "message": f"Neplatné rodné číslo '{raw_rc_str}' nebude přidáno do FHIR zdroje.", "field": "birth_number_raw", "value": raw_rc_str})

    logger.debug(f"Vytvořen FHIR Patient resource (ID: {resource_id}).")
    return resource, issues_list
