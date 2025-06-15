# backend/fhir_mapping/datetime_utils.py
import re
import unicodedata
from datetime import datetime
from typing import List, Dict, Any, Optional # Optional byl v fhir_mapper.py, pro konzistenci
import logging

# Import REGEX_YYYY_MM_DD z regex_definitions
from .regex_definitions import REGEX_YYYY_MM_DD

logger = logging.getLogger(__name__)

# Slovníky pro mapování českých názvů měsíců na číselné reprezentace
MONTH_MAP_GENITIVE = {
    "ledna": "01", "února": "02", "března": "03", "dubna": "04", "května": "05", "června": "06",
    "července": "07", "srpna": "08", "září": "09", "října": "10", "listopadu": "11", "prosince": "12",
    "led": "01", "úno": "02", "bře": "03", "dub": "04", "kvě": "05", "čvn": "06",
    "čvc": "07", "srp": "08", "zář": "09", "říj": "10", "lis": "11", "pro": "12",
}
MONTH_MAP_NOMINATIVE = {
    "leden": "01", "únor": "02", "březen": "03", "duben": "04", "květen": "05", "červen": "06",
    "červenec": "07", "srpen": "08", "září": "09", "říjen": "10", "listopad": "11", "prosinec": "12",
}
FULL_MONTH_MAP = {k.lower(): v for k, v in {**MONTH_MAP_NOMINATIVE, **MONTH_MAP_GENITIVE}.items()}

def strip_accents(text_to_strip: str) -> str:
    """Odstraní diakritiku z textu."""
    if not isinstance(text_to_strip, str):
        logger.warning(f"strip_accents: Očekáván řetězec, obdrženo {type(text_to_strip)}. Vracím nezměněno.")
        return text_to_strip
    return "".join(c for c in unicodedata.normalize('NFD', text_to_strip) if unicodedata.category(c) != 'Mn')

# Vytvoření mapy měsíců, která je case-insensitive a accent-insensitive.
ACCENT_INSENSITIVE_MONTH_MAP = {}
for name, num_str in FULL_MONTH_MAP.items():
    ACCENT_INSENSITIVE_MONTH_MAP[name] = num_str
    ACCENT_INSENSITIVE_MONTH_MAP[strip_accents(name)] = num_str
    if len(name) <= 3 or name.endswith('.'):
        name_no_dot = name.rstrip('.')
        ACCENT_INSENSITIVE_MONTH_MAP[name_no_dot + '.'] = num_str
        ACCENT_INSENSITIVE_MONTH_MAP[strip_accents(name_no_dot) + '.'] = num_str

def parse_date_to_fhir_format(date_str: str, quality_issues_list: List[Dict[str, Any]]) -> Optional[str]:
    """
    Parsování data z různých českých textových formátů na FHIR standardní formát (YYYY-MM-DD).
    Přidává problémy s kvalitou do poskytnutého seznamu.
    """
    if not date_str:
        quality_issues_list.append({"level": "warning", "message": "Prázdný vstupní řetězec pro parsování data.", "field": "date_str", "value": str(date_str)})
        return None

    original_date_str = str(date_str)
    logger.debug(f"Pokus o parsování data: '{original_date_str}'")

    match_yyyy_mm_dd = re.match(REGEX_YYYY_MM_DD, original_date_str.strip())
    if match_yyyy_mm_dd:
        year_str, month_str, day_str = match_yyyy_mm_dd.groups()
        if not (day_str.isdigit() and month_str.isdigit() and year_str.isdigit()):
            quality_issues_list.append({"level": "error", "message": f"Chyba parsování data (formát YYYY-MM-DD): Den, měsíc a rok musí být číslice. Získáno: rok='{year_str}', měsíc='{month_str}', den='{day_str}'.", "field": "date_str", "value": original_date_str})
        else:
            try:
                year = int(year_str)
                month = int(month_str)
                day = int(day_str)
                valid_date = True
                if not (1880 <= year <= datetime.now().year + 5):
                    quality_issues_list.append({"level": "warning", "message": f"Neobvyklý rok {year} (formát YYYY-MM-DD). Povolený rozsah: 1880-{datetime.now().year + 5}.", "field": "date_str", "value": original_date_str})
                if not (1 <= month <= 12):
                    quality_issues_list.append({"level": "error", "message": f"Neplatný měsíc {month} (formát YYYY-MM-DD). Měsíc musí být 1-12.", "field": "date_str", "value": original_date_str})
                    valid_date = False
                if not (1 <= day <= 31):
                    quality_issues_list.append({"level": "error", "message": f"Neplatný den {day} (formát YYYY-MM-DD). Den musí být 1-31.", "field": "date_str", "value": original_date_str})
                    valid_date = False
                if valid_date:
                    try:
                        parsed_date = datetime(year, month, day).strftime('%Y-%m-%d')
                        logger.debug(f"Úspěšně parsováno '{original_date_str}' jako YYYY-MM-DD na '{parsed_date}'.")
                        return parsed_date
                    except ValueError as e:
                        quality_issues_list.append({"level": "error", "message": f"Neplatná kombinace den/měsíc/rok (formát YYYY-MM-DD): {e}. Získáno: rok='{year_str}', měsíc='{month_str}', den='{day_str}'.", "field": "date_str", "value": original_date_str})
            except ValueError as e:
                quality_issues_list.append({"level": "error", "message": f"Chyba konverze data na číselné hodnoty (formát YYYY-MM-DD): {e}. Získáno: rok='{year_str}', měsíc='{month_str}', den='{day_str}'.", "field": "date_str", "value": original_date_str})

    temp_date_str = str(date_str)
    for month_name, month_num_str in ACCENT_INSENSITIVE_MONTH_MAP.items():
        pattern = r'\b' + re.escape(month_name) + r'\b'
        temp_date_str = re.sub(pattern, month_num_str, temp_date_str, flags=re.IGNORECASE)

    cleaned_date_str = temp_date_str.strip()
    cleaned_date_str = re.sub(r'\s*[\.\/\s]\s*', '.', cleaned_date_str)
    cleaned_date_str = re.sub(r'\.+', '.', cleaned_date_str)
    cleaned_date_str = cleaned_date_str.strip('.')

    parts = cleaned_date_str.split('.')
    if len(parts) != 3:
        quality_issues_list.append({"level": "error", "message": f"Neočekávaný počet částí ({len(parts)}) po normalizaci a rozdělení data: '{cleaned_date_str}'.", "field": "date_str", "value": original_date_str})
        return None

    try:
        day_str, month_str, year_str = parts[0], parts[1], parts[2]
        if not (day_str.isdigit() and month_str.isdigit() and year_str.isdigit()):
            quality_issues_list.append({"level": "error", "message": f"Den, měsíc a rok musí být číslice po normalizaci. Získáno: den='{day_str}', měsíc='{month_str}', rok='{year_str}'.", "field": "date_str", "value": original_date_str})
            return None

        day = int(day_str)
        month = int(month_str)
        year = int(year_str)

        if not (1880 <= year <= datetime.now().year + 5):
            quality_issues_list.append({"level": "warning", "message": f"Neobvyklý rok {year} po normalizaci. Povolený rozsah: 1880-{datetime.now().year + 5}.", "field": "date_str", "value": original_date_str})
        if not (1 <= month <= 12):
            quality_issues_list.append({"level": "error", "message": f"Neplatný měsíc {month} po normalizaci. Měsíc musí být 1-12.", "field": "date_str", "value": original_date_str})
            return None
        if not (1 <= day <= 31):
            quality_issues_list.append({"level": "error", "message": f"Neplatný den {day} po normalizaci. Den musí být 1-31.", "field": "date_str", "value": original_date_str})
            return None

        parsed_date_final = datetime(year, month, day).strftime('%Y-%m-%d')
        logger.debug(f"Úspěšně parsováno '{original_date_str}' (po textové normalizaci) na '{parsed_date_final}'.")
        return parsed_date_final
    except ValueError as e:
        quality_issues_list.append({"level": "error", "message": f"Chyba při finální konverzi nebo validaci data: {e}. Části: den='{day_str}', měsíc='{month_str}', rok='{year_str}'.", "field": "date_str", "value": original_date_str})
        return None
    except IndexError:
        quality_issues_list.append({"level": "error", "message": "Indexová chyba při přístupu k částem data po normalizaci.", "field": "date_str", "value": original_date_str})
        return None
