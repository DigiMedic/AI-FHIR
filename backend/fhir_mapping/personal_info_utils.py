# backend/fhir_mapping/personal_info_utils.py
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime # Potřebné pro extract_info_from_birth_number

logger = logging.getLogger(__name__)

def extract_info_from_birth_number(birth_number_str: str, quality_issues_list: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Extrahuje rok, měsíc, den a pohlaví z českého rodného čísla.
    Přidává problémy s kvalitou do poskytnutého seznamu.

    Args:
        birth_number_str: Řetězec rodného čísla (očekává se již očištěný, tj. pouze číslice).
        quality_issues_list: Seznam pro shromažďování problémů s kvalitou dat.

    Returns:
        Slovník s klíči 'year', 'month', 'day', 'gender_code' ('male'/'female'/'unknown'),
        nebo None pokud extrakce selže nebo je RČ nekonzistentní.
    """
    if not (len(birth_number_str) == 9 or len(birth_number_str) == 10):
        quality_issues_list.append({"level": "error", "message": f"Neplatná délka pro extrakci z RČ: {len(birth_number_str)}. Očekáváno 9 nebo 10.", "field": "birth_number_cleaned", "value": birth_number_str})
        return None
    if not birth_number_str.isdigit():
        quality_issues_list.append({"level": "error", "message": f"RČ '{birth_number_str}' pro extrakci obsahuje nečíselné znaky.", "field": "birth_number_cleaned", "value": birth_number_str})
        return None

    try:
        year_short = int(birth_number_str[0:2])
        month_raw = int(birth_number_str[2:4])
        day_raw = int(birth_number_str[4:6])

        year_full = 0
        if len(birth_number_str) == 9: # Před 1954
            year_full = 1900 + year_short
            if year_full < 1880:
                 quality_issues_list.append({"level": "warning", "message": f"Rok {year_full} z 9místného RČ '{birth_number_str}' je neobvykle nízký.", "field": "birth_number_cleaned", "value": birth_number_str})
        elif len(birth_number_str) == 10:
            is_post_2003_format = False
            if (21 <= month_raw <= 32) or (71 <= month_raw <= 82):
                 is_post_2003_format = True

            if is_post_2003_format:
                year_full = 2000 + year_short
            else:
                if year_short < 54 :
                    year_full = 2000 + year_short
                else:
                    year_full = 1900 + year_short

        month = month_raw
        gender_code = "unknown"

        if 51 <= month_raw <= 62:
            month = month_raw - 50
            gender_code = "female"
        elif 71 <= month_raw <= 82 and year_full >= 2004:
            month = month_raw - 70
            gender_code = "female"
        elif 21 <= month_raw <= 32 and year_full >= 2004:
            month = month_raw - 20
            gender_code = "male"
        elif 1 <= month_raw <= 12:
            gender_code = "male"
        else:
            quality_issues_list.append({"level": "error", "message": f"Neplatný kód měsíce v RČ: {month_raw}.", "field": "birth_number_cleaned", "value": birth_number_str})
            return None

        if not (1 <= day_raw <= 31):
            quality_issues_list.append({"level": "error", "message": f"Neplatný den v RČ: {day_raw}.", "field": "birth_number_cleaned", "value": birth_number_str})
            return None

        try:
            datetime(year_full, month, day_raw)
        except ValueError:
            quality_issues_list.append({"level": "error", "message": f"Neplatná kombinace den/měsíc/rok v RČ: {day_raw}/{month}/{year_full}.", "field": "birth_number_cleaned", "value": birth_number_str})
            return None

        logger.debug(f"Extrahované informace z RČ '{birth_number_str}': rok={year_full}, měsíc={month}, den={day_raw}, pohlaví='{gender_code}'")
        return {'year': year_full, 'month': month, 'day': day_raw, 'gender_code': gender_code}

    except ValueError:
        quality_issues_list.append({"level": "error", "message": f"RČ '{birth_number_str}' obsahuje nečíselné znaky v části data.", "field": "birth_number_cleaned", "value": birth_number_str})
        return None

def is_valid_birth_number(birth_number_str: str, quality_issues_list: List[Dict[str, Any]]) -> bool:
    """
    Validuje formát a kontrolní součet českého rodného čísla.
    Přidává problémy s kvalitou do poskytnutého seznamu.
    """
    if not birth_number_str:
        quality_issues_list.append({"level": "error", "message": "Prázdný vstupní řetězec pro validaci rodného čísla.", "field": "birth_number", "value": str(birth_number_str)})
        return False
    cleaned_rc = birth_number_str.replace("/", "").strip()

    if not cleaned_rc.isdigit():
        quality_issues_list.append({"level": "error", "message": f"Rodné číslo '{birth_number_str}' obsahuje nečíselné znaky po očištění.", "field": "birth_number", "value": birth_number_str})
        return False

    if not (len(cleaned_rc) == 9 or len(cleaned_rc) == 10):
        quality_issues_list.append({"level": "error", "message": f"Neplatná délka rodného čísla: {len(cleaned_rc)} pro '{birth_number_str}'. Musí být 9 nebo 10.", "field": "birth_number", "value": birth_number_str})
        return False

    extracted_info = extract_info_from_birth_number(cleaned_rc, quality_issues_list)
    if not extracted_info:
        quality_issues_list.append({"level": "error", "message": f"Rodné číslo '{birth_number_str}' neobsahuje validní datumové nebo genderové informace (podrobněji viz předchozí chyby).", "field": "birth_number", "value": birth_number_str})
        return False

    if len(cleaned_rc) == 10:
        year_from_rc = extracted_info['year']
        original_month_in_rc = int(cleaned_rc[2:4])
        is_post_2003_format_check = False
        if (original_month_in_rc >= 21 and original_month_in_rc <= 32) or \
           (original_month_in_rc >= 71 and original_month_in_rc <= 82):
            is_post_2003_format_check = True

        if 1954 <= year_from_rc <= 2003 and not is_post_2003_format_check:
            try:
                rc_as_int = int(cleaned_rc)
                modulo_result = rc_as_int % 11
                if modulo_result != 0:
                    quality_issues_list.append({"level": "error", "message": f"Rodné číslo '{birth_number_str}' (rok {year_from_rc}, formát do 2003) není dělitelné 11 (mod={modulo_result}).", "field": "birth_number", "value": birth_number_str})
                    return False
            except ValueError: # Should not happen due to isdigit check, but as a safeguard
                quality_issues_list.append({"level": "error", "message": f"Neočekávaná chyba při kontrole dělitelnosti RČ '{birth_number_str}'.", "field": "birth_number", "value": birth_number_str})
                return False
    logger.debug(f"Rodné číslo '{birth_number_str}' je validní.")
    return True
