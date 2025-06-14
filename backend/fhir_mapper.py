# backend/fhir_mapper.py
import re
import json
from typing import Union, List, Dict, Any, Optional
from datetime import datetime, timedelta
import uuid
import unicodedata # Potřebné pro odstranění diakritiky

# --- Regulární výrazy (Regex) ---
# Každý regex je navržen tak, aby zachytil specifickou informaci z textu lékařské zprávy.
# Používá se `re.IGNORECASE` pro většinu vyhledávání, aby se zajistila flexibilita vůči velikosti písmen.

# Regex pro jméno pacienta:
# - Hledá klíčová slova jako "Pacient", "Pacientka", "Jméno pacienta", "Vyšetřovaný", "Vyšetřovaná".
# - Následuje dvojtečka a mezery.
# - Zachytává jméno a příjmení (případně více jmen/příjmení, včetně těch s pomlčkou).
# - Jména začínají velkým písmenem, ostatní písmena jsou malá (včetně české diakritiky).
# - Upraveno tak, aby končilo před dalším klíčovým slovem jako "Datum narození", "Nar." atd., nebo před novým řádkem, pokud za ním nenásleduje další část jména.
REGEX_PATIENT_NAME = r"(?:Pacient(?:ka)?|Jméno pacienta|Vyšetřovan(?:ý|á))\s*:\s*([A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+(?:-[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+)?(?:\s+[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+(?:-[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+)?)*)(?=\s*(?:Datum narození|Nar\.|Narozena|Dat\. nar\.|Narozen\(a\)|R(?:odné|\.č\.)|Bydliště|Poznámka|---|$))"

# Regex pro datum narození:
# - Hledá klíčová slova jako "Datum narození", "Nar.", "Narozena", "Dat. nar.", "Narozen(a)".
# - Následuje dvojtečka a mezery.
# - Zachytává datum ve formátu DD.MM.YYYY, DD/MM/YYYY, DD MM YYYY, nebo textové měsíce (např. "1. ledna 1955").
# - Upraveno pro flexibilnější zachycení data: vezme zbytek řádku po klíčovém slově.
#   Čištění se provádí v parse_patient_data.
REGEX_BIRTH_DATE = r"(?:Datum narození|Nar\.|Narozena|Dat\. nar\.|Narozen\(a\))\s*:\s*([^\n\r]+)"

# Regex pro rodné číslo:
# - Hledá klíčová slova jako "Rodné číslo", "RČ", "R.č.".
# - Následuje dvojtečka a mezery.
# - Zachytává rodné číslo ve formátu XXXXXX/XXXX nebo XXXXXXYYYY (6 číslic, volitelné lomítko, 3 nebo 4 číslice).
REGEX_BIRTH_NUMBER = r"(?:Rodné číslo|RČ|R\.č\.)\s*:\s*(\d{6}\/?\d{3,4})"

# Regex pro krevní tlak:
# - Hledá klíčová slova "Krevní tlak" nebo zkratku "TK".
# - Následuje dvojtečka a mezery.
# - Zachytává hodnotu tlaku ve formátu SYSTOLICKÝ/DIASTICKÝ (např. 120/80).
# - Volitelně může obsahovat jednotku "mmHg".
REGEX_BLOOD_PRESSURE = r"(?:Krevní tlak|TK)\s*:\s*(\d{2,3}\s*\/\s*\d{2,3})\s*(?:mmHg)?"

# Regex pro pulz (srdeční frekvenci):
# - Hledá klíčová slova jako "Pulz", "Puls", "Srdeční frekvence", "SF".
# - Následuje dvojtečka a mezery.
# - Zachytává číselnou hodnotu pulzu (2-3 číslice).
# - Volitelně může obsahovat jednotku "/min", "tepů/min" nebo "/min.".
REGEX_PULSE = r"(?:Pulz|Puls|Srdeční frekvence|SF)\s*:\s*(\d{2,3})\s*(?:/min|tepů/min|/min\.)"

# Regex pro tělesnou teplotu:
# - Hledá klíčová slova "Teplota" nebo zkratku "T".
# - Následuje dvojtečka a mezery.
# - Zachytává číselnou hodnotu teploty (např. 36.5, 37,2), s tečkou nebo čárkou jako desetinným oddělovačem.
# - Volitelně může obsahovat jednotku "°C" nebo "C".
REGEX_TEMPERATURE = r"(?:Teplota|T)\s*:\s*(\d{2}(?:[\.,]\d{1,2})?)\s*(?:°C|C)"

# Regex pro tělesnou výšku:
# - Hledá klíčová slova jako "Výška", "Výš.".
# - Následuje dvojtečka a mezery.
# - Zachytává číselnou hodnotu výšky (např. 175, 180.5), s tečkou nebo čárkou jako desetinným oddělovačem.
# - Volitelně může obsahovat jednotku "cm".
REGEX_HEIGHT = r"(?:Výška|Výš\.)\s*:\s*(\d{2,3}(?:[\.,]\d{1,2})?)\s*(cm)?"

# Regex pro tělesnou hmotnost:
# - Hledá klíčová slova jako "Hmotnost", "Hm.", "Váha".
# - Následuje dvojtečka a mezery.
# - Zachytává číselnou hodnotu hmotnosti (např. 70, 75.5, 102.3), s tečkou nebo čárkou.
# - Volitelně může obsahovat jednotku "kg".
REGEX_WEIGHT = r"(?:Hmotnost|Hm\.|Váha)\s*:\s*(\d{1,3}(?:[\.,]\d{1,2})?)\s*(kg)?"

# Regex pro text diagnózy/závěru:
# - Hledá klíčová slova jako "Diagnóza", "Dg.", "Závěr".
# - Následuje dvojtečka a mezery.
# - Zachytává text diagnózy (.+?) až po specifické ukončovací tokeny nebo konec textu.
# - Ukončovací tokeny zahrnují prázdné řádky, "Poznámka:", "Medikace:", "Doporučení:", atd.,
#   aby se zabránilo zachycení příliš velkého bloku textu.
# - Používá re.DOTALL, aby tečka (.) zahrnovala i nové řádky.
REGEX_DIAGNOSIS_TEXT = r"(?:Diagnóza|Dg\.|Závěr)\s*:\s*(.+?)(?:\s*\n\s*|\Z|Poznámka:|Medikace:|Doporučení:|Terapie:|Výška:|Hmotnost:|Kontrola:|Prognóza:)"


# --- Pomocné (Helper) funkce pro parsování ---

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

    Args:
        text_segment_for_search: Textový segment, ve kterém se hledají klíčová slova a entity.
                                 Pozice entit (start_char, end_char) musí být relativní k tomuto segmentu
                                 nebo k celému dokumentu, pokud jsou entity filtrovány předem.
        nlp_entities: Seznam všech NLP entit pro daný text. Pozice entit by měly být
                      absolutní vzhledem k původnímu textu, ze kterého `text_segment_for_search` pochází.
        keyword_patterns: Seznam regex vzorů pro identifikaci klíčových slov.
        target_entity_types: Seznam typů NLP entit, které se mají hledat (např. ['CARDINAL', 'NUMBER']).
        window_size: Velikost okna (počet znaků) za/před klíčovým slovem, ve kterém se hledají entity.
        search_after_keyword: True pro hledání za klíčovým slovem, False pro hledání před.

    Returns:
        Seznam nalezených NLP entit, seřazených podle jejich pozice.
    """
    found_entities_details = []
    processed_text_segment = text_segment_for_search # Může být již normalizovaný (např. lowercase)

    for keyword_pattern in keyword_patterns:
        try:
            # Hledáme všechny výskyty klíčového slova
            for match in re.finditer(keyword_pattern, processed_text_segment, re.IGNORECASE):
                keyword_start, keyword_end = match.span()

                # Definice oblasti hledání entit na základě pozice klíčového slova
                if search_after_keyword:
                    search_window_start = keyword_end
                    search_window_end = keyword_end + window_size
                else: # Hledání před klíčovým slovem
                    search_window_start = max(0, keyword_start - window_size)
                    search_window_end = keyword_start

                # Filtrování a sběr entit v definovaném okně
                # Předpokládáme, že nlp_entities mají 'start_char' a 'end_char' absolutní k originálnímu textu.
                # Pokud text_segment_for_search je jen částí originálního textu,
                # musíme buď upravit pozice entit, nebo zajistit, že `nlp_entities`
                # jsou již relevantní pro `text_segment_for_search` a jejich pozice jsou upraveny.
                # Pro jednoduchost zde předpokládáme, že `text_segment_for_search` je celý text
                # a `nlp_entities` mají absolutní pozice.
                # Pokud by `text_segment_for_search` byl podřetězec, museli bychom upravit
                # `search_window_start` a `search_window_end` tak, aby odpovídaly absolutním pozicím,
                # nebo filtrovat a upravovat pozice entit.

                # Tento příklad předpokládá, že `text_segment_for_search` JE celý text,
                # a `nlp_entities` mají absolutní pozice.
                candidate_entities = []
                for entity in nlp_entities:
                    entity_type = entity.get('type')
                    entity_start = entity.get('start_char')
                    entity_end = entity.get('end_char')

                    if entity_type in target_entity_types and \
                       entity_start is not None and entity_end is not None:
                        # Kontrola, zda entita spadá do vyhledávacího okna
                        if entity_start >= search_window_start and entity_end <= search_window_end:
                            candidate_entities.append(entity)
                        # Případ, kdy entita začíná v okně, ale končí mimo (částečný překryv)
                        elif entity_start >= search_window_start and entity_start < search_window_end:
                             candidate_entities.append(entity)
                        # Případ, kdy entita končí v okně, ale začíná před (částečný překryv)
                        elif entity_end > search_window_start and entity_end <= search_window_end:
                             candidate_entities.append(entity)
                        # Případ, kdy entita zcela obklopuje okno (méně časté pro krátká okna)
                        elif entity_start < search_window_start and entity_end > search_window_end:
                             candidate_entities.append(entity)


                # Seřadíme nalezené kandidáty podle jejich pozice a přidáme je
                # (pokud jich je více, vrátí se všechny relevantní z tohoto okna)
                # Odstranění duplikátů, pokud by se nějaké objevily (např. z překrývajících se klíč. slov)
                for ent in sorted(candidate_entities, key=lambda x: x['start_char']):
                    if ent not in found_entities_details:
                        found_entities_details.append(ent)

        except re.error as e:
            print(f"DEBUG [FHIR Mapper]: Chyba regexu v find_nlp_entities_near_keyword pro vzor '{keyword_pattern}': {e}")
            continue # Pokračujeme s dalším vzorem

    # Finální seřazení všech nalezených entit z různých klíčových slov/oken
    return sorted(found_entities_details, key=lambda x: x['start_char'])


def extract_value_and_unit_from_nlp_entity_text(
    entity_text: str,
    surrounding_text: str, # Text okolo entity pro lepší detekci jednotek
    unit_regex_map: Dict[str, str],
    default_unit: Optional[str] = None
) -> Tuple[Optional[str], Optional[str]]:
    """
    Pokusí se z textu NLP entity a jejího okolí extrahovat číselnou hodnotu a její jednotku.

    Args:
        entity_text: Text samotné NLP entity (očekává se, že obsahuje číselnou hodnotu).
        surrounding_text: Text v okolí NLP entity (např. pár znaků/slov za ní),
                          kde by se mohla nacházet jednotka.
        unit_regex_map: Slovník, kde klíč je standardní jednotka (např. "kg")
                        a hodnota je regex pro detekci této jednotky a jejích variant.
        default_unit: Volitelná výchozí jednotka, pokud žádná není nalezena.

    Returns:
        Tuple (hodnota, jednotka). Hodnota je řetězec obsahující číslo (normalizované),
        jednotka je standardizovaná jednotka z `unit_regex_map`.
        Vrací (None, None) pokud nelze extrahovat hodnotu.
        Vrací (hodnota, None) pokud je nalezena hodnota, ale žádná jednotka (a není default_unit).
        Vrací (hodnota, default_unit) pokud je nalezena hodnota, žádná explicitní jednotka, ale je default_unit.
    """
    # 1. Extrakce číselné hodnoty z textu entity
    #    Regex hledá čísla, která mohou být celá nebo desetinná (s tečkou nebo čárkou).
    #    Může být na začátku, uprostřed nebo na konci textu entity.
    value_match = re.search(r'(\d+([\.,]\d+)?)', entity_text)
    if not value_match:
        print(f"DEBUG [FHIR Mapper]: extract_value_and_unit: Hodnota nenalezena v textu entity '{entity_text}'.")
        return None, None

    extracted_value_str = value_match.group(1)
    # Normalizace desetinné čárky na tečku
    normalized_value_str = extracted_value_str.replace(',', '.')

    # 2. Hledání jednotky v textu entity samotné nebo v jejím blízkém okolí
    #    Kombinujeme text entity a okolní text pro hledání jednotky,
    #    protože jednotka může být přímo za číslem v entitě, nebo těsně za ní.
    #    Dáváme přednost jednotce nalezené blíže k hodnotě.
    search_text_for_unit = entity_text[value_match.end():].strip() + " " + surrounding_text.strip()
    search_text_for_unit = search_text_for_unit.strip() # Odstranění přebytečných mezer

    found_unit = None
    # Iterujeme přes mapu jednotek a jejich regexů
    for standard_unit, unit_regex_pattern in unit_regex_map.items():
        try:
            # Hledáme na začátku kombinovaného textu (entity_suffix + surrounding_text)
            # Používáme re.match, abychom zajistili, že jednotka následuje těsně.
            # Pokud by jednotka mohla být oddělena mezerou, regex by to měl zahrnovat (např. r"\s*kg")
            # nebo bychom museli použít re.search a kontrolovat pozici.
            # Pro jednoduchost zde předpokládáme, že regexy v unit_regex_map
            # jsou navrženy tak, aby odpovídaly jednotkám na začátku `search_text_for_unit`.
            unit_match = re.search(r"^\s*" + unit_regex_pattern, search_text_for_unit, re.IGNORECASE)
            if unit_match:
                found_unit = standard_unit
                print(f"DEBUG [FHIR Mapper]: extract_value_and_unit: Nalezena jednotka '{found_unit}' pro hodnotu '{normalized_value_str}' v textu '{search_text_for_unit}' (vzor: '{unit_regex_pattern}').")
                break # Našli jsme jednotku, můžeme přestat hledat
        except re.error as e:
            print(f"DEBUG [FHIR Mapper]: Chyba regexu v extract_value_and_unit_from_nlp_entity_text pro vzor jednotky '{unit_regex_pattern}': {e}")
            continue

    if not found_unit and default_unit:
        found_unit = default_unit
        print(f"DEBUG [FHIR Mapper]: extract_value_and_unit: Jednotka nenalezena explicitně, použita výchozí jednotka '{default_unit}' pro hodnotu '{normalized_value_str}'.")
    elif not found_unit:
        print(f"DEBUG [FHIR Mapper]: extract_value_and_unit: Jednotka nenalezena a není výchozí pro hodnotu '{normalized_value_str}' v textu '{search_text_for_unit}'.")


    return normalized_value_str, found_unit


def parse_date_to_fhir_format(date_str: str) -> str | None:
    """
    Parsování data z různých českých textových formátů na FHIR standardní formát (YYYY-MM-DD).

    Podporuje číselné formáty (DD.MM.YYYY, DD/MM/YYYY, DD MM YYYY) a také formáty
    s českými názvy měsíců (např. "15. května 1980", "5 ledna 2003").
    Zpracovává názvy měsíců s i bez diakritiky, v nominativu i genitivu,
    a některé běžné zkratky (led, úno, pro, atd.).

    Args:
        date_str: Řetězec obsahující datum k parsování.

    Returns:
        Řetězec s datem ve formátu YYYY-MM-DD, pokud parsování proběhne úspěšně,
        jinak None.
    """
    if not date_str:
        print(f"DEBUG [FHIR Mapper]: parse_date_to_fhir_format: Prázdný vstupní date_str.")
        return None

    original_date_str = str(date_str) # Uložíme si původní vstup pro detailnější logování chyb

    # Regex pro formáty YYYY-MM-DD, YYYY.MM.DD, YYYY/MM/DD
    REGEX_YYYY_MM_DD = r"(\d{4})[\.\/\-](\d{1,2})[\.\/\-](\d{1,2})"

    # 1. Pokus o parsování formátů s rokem na začátku (YYYY-MM-DD, YYYY.MM.DD, YYYY/MM/DD)
    # Používáme re.match, protože chceme shodu od začátku řetězce.
    match_yyyy_mm_dd = re.match(REGEX_YYYY_MM_DD, original_date_str.strip())
    if match_yyyy_mm_dd:
        print(f"DEBUG [FHIR Mapper]: parse_date_to_fhir_format: Nalezena shoda s REGEX_YYYY_MM_DD pro '{original_date_str}'.")
        year_str, month_str, day_str = match_yyyy_mm_dd.groups()

        if not (day_str.isdigit() and month_str.isdigit() and year_str.isdigit()):
            print(f"DEBUG [FHIR Mapper]: Chyba parsování data (YYYY-MM-DD): Den, měsíc a rok musí být číslice. Získáno: rok='{year_str}', měsíc='{month_str}', den='{day_str}' (původní: '{original_date_str}'). Pokračuji na další metody parsování.")
        else:
            try:
                year = int(year_str)
                month = int(month_str)
                day = int(day_str)

                # Validace rozsahu hodnot (stejná jako v existující logice)
                if not (1880 <= year <= datetime.now().year + 5):
                    print(f"DEBUG [FHIR Mapper]: Varování parsování data (YYYY-MM-DD): Neobvyklý rok {year} (původní: '{original_date_str}'). Povolený rozsah: 1880-{datetime.now().year + 5}. Pokračuji na další metody parsování.")
                elif not (1 <= month <= 12):
                    print(f"DEBUG [FHIR Mapper]: Chyba parsování data (YYYY-MM-DD): Neplatný měsíc {month} (původní: '{original_date_str}'). Měsíc musí být 1-12. Pokračuji na další metody parsování.")
                elif not (1 <= day <= 31): # Základní kontrola
                    print(f"DEBUG [FHIR Mapper]: Chyba parsování data (YYYY-MM-DD): Neplatný den {day} (původní: '{original_date_str}'). Den musí být 1-31. Pokračuji na další metody parsování.")
                else:
                    # Vytvoření datetime objektu pro finální validaci a formátování
                    parsed_date = datetime(year, month, day).strftime('%Y-%m-%d')
                    print(f"DEBUG [FHIR Mapper]: parse_date_to_fhir_format: Úspěšně parsováno '{original_date_str}' jako YYYY-MM-DD na '{parsed_date}'.")
                    return parsed_date
            except ValueError as e:
                print(f"DEBUG [FHIR Mapper]: Chyba parsování data (YYYY-MM-DD): Neplatná hodnota data (např. 30. února): {e}. Části: rok='{year_str}', měsíc='{month_str}', den='{day_str}' (původní: '{original_date_str}'). Pokračuji na další metody parsování.")
            # Pokud dojde k chybě nebo selže validace, necháme funkci pokračovat k dalším metodám parsování.

    # 2. Pokus o parsování formátů s textovými měsíci a DD.MM.YYYY
    # Slovníky pro mapování českých názvů měsíců na číselné reprezentace
    # Genitiv (např. "ledna", "února")
    MONTH_MAP_GENITIVE = {
        "ledna": "01", "února": "02", "března": "03", "dubna": "04", "května": "05", "června": "06",
        "července": "07", "srpna": "08", "září": "09", "října": "10", "listopadu": "11", "prosince": "12",
        "led": "01", "úno": "02", "bře": "03", "dub": "04", "kvě": "05", "čvn": "06",
        "čvc": "07", "srp": "08", "zář": "09", "říj": "10", "lis": "11", "pro": "12", # Běžné zkratky
    }
    # Nominativ (např. "leden", "únor")
    MONTH_MAP_NOMINATIVE = {
        "leden": "01", "únor": "02", "březen": "03", "duben": "04", "květen": "05", "červen": "06",
        "červenec": "07", "srpen": "08", "září": "09", "říjen": "10", "listopad": "11", "prosinec": "12",
    }
    # Kombinovaný slovník pro snadnější zpracování, klíče jsou malými písmeny.
    # Dáváme přednost delším názvům (genitiv), pokud by existovaly konflikty (zde ne).
    FULL_MONTH_MAP = {k.lower(): v for k, v in {**MONTH_MAP_NOMINATIVE, **MONTH_MAP_GENITIVE}.items()}

    def strip_accents(text_to_strip: str) -> str:
        """Odstraní diakritiku z textu."""
        return "".join(c for c in unicodedata.normalize('NFD', text_to_strip) if unicodedata.category(c) != 'Mn')

    # Vytvoření mapy měsíců, která je case-insensitive a accent-insensitive.
    # Zahrnuje i varianty s tečkou pro zkratky (např. "pro.").
    ACCENT_INSENSITIVE_MONTH_MAP = {}
    for name, num_str in FULL_MONTH_MAP.items():
        ACCENT_INSENSITIVE_MONTH_MAP[name] = num_str
        ACCENT_INSENSITIVE_MONTH_MAP[strip_accents(name)] = num_str
        if len(name) <= 3 or name.endswith('.'): # Pro krátké názvy nebo názvy již s tečkou
            name_no_dot = name.rstrip('.')
            ACCENT_INSENSITIVE_MONTH_MAP[name_no_dot + '.'] = num_str # např. pro.
            ACCENT_INSENSITIVE_MONTH_MAP[strip_accents(name_no_dot) + '.'] = num_str # např. pro. (bez diakritiky)

    # Nahrazení textových měsíců jejich číselnými ekvivalenty
    # Iterujeme přes připravenou mapu a nahrazujeme v `date_str`
    temp_date_str = str(date_str) # Pracovní kopie pro nahrazování měsíců
    for month_name, month_num_str in ACCENT_INSENSITIVE_MONTH_MAP.items():
        # Používáme `re.escape` pro případ, že by název měsíce obsahoval speciální regex znaky (např. tečku).
        # `\b` zajišťuje, že nahrazujeme celá slova (např. "května", nikoli část slova "květináč").
        pattern = r'\b' + re.escape(month_name) + r'\b'
        temp_date_str = re.sub(pattern, month_num_str, temp_date_str, flags=re.IGNORECASE)

    # Standardizace oddělovačů a odstranění nadbytečných mezer/znaků.
    # Cílem je získat formát "DD.MM.YYYY".
    cleaned_date_str = temp_date_str.strip()
    # Nahradí běžné oddělovače a sekvence mezer jednou tečkou
    cleaned_date_str = re.sub(r'\s*[\.\/\s]\s*', '.', cleaned_date_str)
    # Odstraní případné vícenásobné tečky vzniklé předchozím krokem
    cleaned_date_str = re.sub(r'\.+', '.', cleaned_date_str)
    if cleaned_date_str.endswith('.'): # Odstraní tečku na konci, pokud existuje
        cleaned_date_str = cleaned_date_str[:-1]
    if cleaned_date_str.startswith('.'): # Odstraní tečku na začátku, pokud existuje
        cleaned_date_str = cleaned_date_str[1:]


    parts = cleaned_date_str.split('.')
    if len(parts) != 3:
        print(f"DEBUG [FHIR Mapper]: Chyba parsování data: Neočekávaný počet částí ({len(parts)}) po rozdělení '{cleaned_date_str}' (původní: '{original_date_str}').")
        return None

    try:
        day_str, month_str, year_str = parts[0], parts[1], parts[2]

        if not (day_str.isdigit() and month_str.isdigit() and year_str.isdigit()):
            print(f"DEBUG [FHIR Mapper]: Chyba parsování data: Den, měsíc a rok musí být číslice. Získáno: den='{day_str}', měsíc='{month_str}', rok='{year_str}' (původní: '{original_date_str}').")
            return None

        day = int(day_str)
        month = int(month_str)
        year = int(year_str)

        # Validace rozsahu hodnot
        if not (1880 <= year <= datetime.now().year + 5):
            print(f"DEBUG [FHIR Mapper]: Varování parsování data: Neobvyklý rok {year} (původní: '{original_date_str}'). Povolený rozsah: 1880-{datetime.now().year + 5}.")
        if not (1 <= month <= 12):
            print(f"DEBUG [FHIR Mapper]: Chyba parsování data: Neplatný měsíc {month} (původní: '{original_date_str}'). Měsíc musí být 1-12.")
            return None
        if not (1 <= day <= 31): # Základní kontrola, `datetime` objekt pak ověří platnost dne v měsíci
            print(f"DEBUG [FHIR Mapper]: Chyba parsování data: Neplatný den {day} (původní: '{original_date_str}'). Den musí být 1-31.")
            return None

        # Vytvoření datetime objektu pro finální validaci (např. 30. února) a formátování
        return datetime(year, month, day).strftime('%Y-%m-%d')
    except ValueError as e:
        print(f"DEBUG [FHIR Mapper]: Chyba parsování data: Neplatná hodnota data (např. 30. února): {e}. Části: den='{day_str}', měsíc='{month_str}', rok='{year_str}' (původní: '{original_date_str}').")
        return None
    except IndexError: # Tento by neměl nastat díky kontrole len(parts)
        print(f"DEBUG [FHIR Mapper]: Chyba parsování data: Indexová chyba při přístupu k částem data (původní: '{original_date_str}').")
        return None

def is_valid_birth_number(birth_number_str: str) -> bool:
    """
    Validuje formát a kontrolní součet českého rodného čísla.

    Args:
        birth_number_str: Řetězec rodného čísla (může obsahovat lomítko).

    Returns:
        True pokud je RČ validní, jinak False.
    """
def is_valid_birth_number(birth_number_str: str) -> bool:
    if not birth_number_str:
        return False
    cleaned_rc = birth_number_str.replace("/", "").strip()

    if not cleaned_rc.isdigit():
        print(f"DEBUG [FHIR Mapper]: is_valid_birth_number: RČ '{birth_number_str}' obsahuje nečíselné znaky po očištění.")
        return False

    if not (len(cleaned_rc) == 9 or len(cleaned_rc) == 10):
        print(f"DEBUG [FHIR Mapper]: is_valid_birth_number: Neplatná délka RČ: {len(cleaned_rc)} pro '{birth_number_str}'. Musí být 9 nebo 10.")
        return False

    extracted_info = extract_info_from_birth_number(cleaned_rc)
    if not extracted_info:
        # extract_info_from_birth_number již loguje detaily, zde jen obecná zpráva.
        print(f"DEBUG [FHIR Mapper]: is_valid_birth_number: RČ '{birth_number_str}' neobsahuje validní datumové informace.")
        return False

    # Kontrola dělitelnosti 11 pro desetimístná RČ vydaná v letech 1954 až 2003 včetně.
    # Tato kontrola se nevztahuje na RČ vydaná před 1954 (9místná) ani po 2003 (nový formát měsíců).
    if len(cleaned_rc) == 10:
        year_from_rc = extracted_info['year']

        original_month_in_rc = int(cleaned_rc[2:4])
        is_post_2003_format_check = False
        if (original_month_in_rc >= 21 and original_month_in_rc <= 32) or \
           (original_month_in_rc >= 71 and original_month_in_rc <= 82):
            is_post_2003_format_check = True

        if 1954 <= year_from_rc <= 2003 and not is_post_2003_format_check:
            # print(f"DEBUG PRE-INT CONVERSION: cleaned_rc='{cleaned_rc}', type={type(cleaned_rc)}") # Temporary debug
            rc_as_int = int(cleaned_rc)
            modulo_result = rc_as_int % 11
            # print(f"DEBUG MODULO CHECK: RC_INT={rc_as_int}, MODULO_RESULT={modulo_result}") # Temporary debug print
            if modulo_result != 0:
                print(f"DEBUG [FHIR Mapper]: is_valid_birth_number: RČ '{birth_number_str}' (rok {year_from_rc}, formát do 2003) není dělitelné 11 (mod={modulo_result}).")
                return False
    return True

def generate_fhir_id() -> str:
    """
    Generuje unikátní identifikátor (UUID) pro FHIR zdroje.

    Returns:
        Řetězec reprezentující UUID.
    """
    return str(uuid.uuid4())

def extract_info_from_birth_number(birth_number_str: str) -> Optional[Dict[str, Any]]:
    """
    Extrahuje rok, měsíc, den a pohlaví z českého rodného čísla.
    Args:
        birth_number_str: Řetězec rodného čísla (očekává se již očištěný, tj. pouze číslice).
    Returns:
        Slovník s klíči 'year', 'month', 'day', 'gender_code' ('male'/'female'/'unknown'),
        nebo None pokud extrakce selže nebo je RČ nekonzistentní.
    """
    if not (len(birth_number_str) == 9 or len(birth_number_str) == 10):
        # print(f"DEBUG [FHIR Mapper]: extract_info_from_birth_number: Neplatná délka RČ: {len(birth_number_str)}.")
        return None
    if not birth_number_str.isdigit():
        # print(f"DEBUG [FHIR Mapper]: extract_info_from_birth_number: RČ '{birth_number_str}' obsahuje nečíselné znaky.")
        return None

    try:
        year_short = int(birth_number_str[0:2])
        month_raw = int(birth_number_str[2:4])
        day_raw = int(birth_number_str[4:6])

        # Určení století a roku
        # Pravidla pro určení století:
        # Pro RČ do roku 1985 včetně: YYMMDDXXX (9 číslic) nebo YYMMDDXXXX (10 číslic, od 1954)
        #   - Rok 19xx
        # Pro RČ od roku 1986: YYMMDDXXXX (10 číslic)
        #   - Rok 19xx nebo 20xx. Pokud YY < 54 (pro RČ vydaná do 2003) => 20YY, jinak 19YY.
        #   - Pro RČ vydaná od 2004: měsíc +20 (muži) nebo +70 (ženy), rok je vždy 20YY.
        # Toto je komplexní, pro zjednodušení se zde zaměříme na základní logiku.

        year_full = 0
        if len(birth_number_str) == 9: # Před 1954
            year_full = 1900 + year_short
            # Kontrola, zda rok není příliš nízký (např. 1880, pokud je to relevantní hranice)
            if year_full < 1880: # Arbitrary lower bound for sanity
                 # print(f"DEBUG [FHIR Mapper]: extract_info_from_birth_number: Rok {year_full} z 9místného RČ je příliš nízký.")
                 return None

        elif len(birth_number_str) == 10:
            # Pro RČ od 1.1.2004 se k měsíci přidává +20 (muži) nebo +70 (ženy)
            # a rok je vždy 20xx. Tato RČ mají také neměnnou třetí číslici za lomítkem (index 6) > 1.
            # Pro RČ vydaná 1954-2003:
            #   Pokud YYMMDD/XXXX, rok < 54 => 20YY, jinak 19YY
            # Toto rozlišení je klíčové. Třetí číslice za lomítkem (birth_number_str[6]) může pomoci.
            # Pokud je birth_number_str[6] např. '0' nebo '1', jde pravděpodobně o RČ formátu do r.2003.
            # Pokud je '2' a výše, jde o RČ po r.2003.

            is_post_2003_format = False
            # Kontrola, zda formát měsíce odpovídá post-2003 pravidlům
            if (21 <= month_raw <= 32) or (71 <= month_raw <= 82):
                 is_post_2003_format = True

            if is_post_2003_format:
                year_full = 2000 + year_short
            else: # Formát RČ do roku 2003 (nebo 9místné, kde je rok vždy 19xx)
                  # Pro 10místné RČ vydané do r. 2003: rok < 54 znamená 20xx, jinak 19xx.
                  # Toto pravidlo se aplikuje na datum narození osoby, ne na rok vydání RČ.
                if year_short < 54 :
                    year_full = 2000 + year_short
                else: # 54-99 -> 1954-1999
                    year_full = 1900 + year_short

        # Extrakce měsíce a pohlaví
        month = month_raw
        gender_code = "unknown"

        if 51 <= month_raw <= 62: # Žena (starý formát, nebo nový pokud rok > 2003 a měsíc není +70)
            month = month_raw - 50
            gender_code = "female"
        elif 71 <= month_raw <= 82 and year_full >= 2004: # Žena, RČ od 2004
            month = month_raw - 70
            gender_code = "female"
        elif 21 <= month_raw <= 32 and year_full >= 2004: # Muž, RČ od 2004
            month = month_raw - 20
            gender_code = "male"
        elif 1 <= month_raw <= 12: # Muž (starý formát)
            gender_code = "male"
        else:
            # print(f"DEBUG [FHIR Mapper]: extract_info_from_birth_number: Neplatný kód měsíce v RČ: {month_raw}.")
            return None

        # Validace dne
        if not (1 <= day_raw <= 31):
            # print(f"DEBUG [FHIR Mapper]: extract_info_from_birth_number: Neplatný den v RČ: {day_raw}.")
            return None

        try:
            datetime(year_full, month, day_raw)
        except ValueError:
            # print(f"DEBUG [FHIR Mapper]: extract_info_from_birth_number: Neplatná kombinace den/měsíc/rok v RČ: {day_raw}/{month}/{year_full}.")
            return None

        return {'year': year_full, 'month': month, 'day': day_raw, 'gender_code': gender_code}

    except ValueError:
        # print(f"DEBUG [FHIR Mapper]: extract_info_from_birth_number: RČ '{birth_number_str}' obsahuje nečíselné znaky v date části.")
        return None


# --- Funkce pro parsování specifických dat z textu ---

def parse_patient_data(nlp_entities: Optional[List[Dict[str, Any]]], text: str) -> dict:
    """
    Parsování základních demografických údajů o pacientovi z textu, s možností využití NLP entit.

    Extrahuje jméno, datum narození a rodné číslo.

    Args:
        nlp_entities: Seznam NLP entit (může být None).
        text: Vstupní text lékařské zprávy pro regex fallback.

    Returns:
        Slovník s extrahovanými daty pacienta. Klíče:
        - "full_name": Celé jméno pacienta.
        - "birth_date_fhir": Datum narození ve FHIR formátu (YYYY-MM-DD).
        - "birth_date_raw": Původní extrahovaný řetězec data narození (pokud FHIR formát selže).
        - "birth_number_raw": Extrahované rodné číslo (s nebo bez lomítka).
    """
    patient_data = {}
    found_name_by_nlp = False
    found_birth_date_by_nlp = False

    # Klíčová slova pro identifikaci sekcí relevantních pro jméno a datum narození pacienta
    patient_name_keywords = [
        r"Pacient(?:ka)?\s*:", r"Jméno pacienta\s*:", r"Vyšetřovan(?:ý|á)\s*:"
    ]
    birth_date_keywords = [
        r"Datum narození\s*:", r"Nar\.\s*:", r"Narozena\s*:", r"Dat\. nar\.\s*:", r"Narozen\(a\)\s*:"
    ]
    # Maximální vzdálenost entity od klíčového slova, aby byla považována za relevantní
    keyword_proximity_window = 50 # Počet znaků za klíčovým slovem

    if nlp_entities and text:
        # --- Extrakce jména pacienta pomocí NLP ---
        person_entities_P = [ent for ent in nlp_entities if ent.get('type') == 'P']
        atomic_name_parts_entities = [ent for ent in nlp_entities if ent.get('type') in ['pt', 'pf', 'ps', 'pd']]
        atomic_name_parts_entities.sort(key=lambda x: x['start_char'])

        selected_person_entity = None

        if person_entities_P:
            print(f"DEBUG [FHIR Mapper]: parse_patient_data: Nalezeno {len(person_entities_P)} entit typu 'P'. Hledání nejrelevantnější...")
            relevant_P_entities_near_keywords = []
            for kw_pattern in patient_name_keywords:
                for kw_match in re.finditer(kw_pattern, text, re.IGNORECASE):
                    kw_end_pos = kw_match.end()
                    for p_ent in person_entities_P:
                        # Entita by měla začínat po klíčovém slově a v definovaném okně
                        if p_ent['start_char'] >= kw_end_pos and \
                           p_ent['start_char'] < kw_end_pos + keyword_proximity_window:
                            distance = p_ent['start_char'] - kw_end_pos
                            relevant_P_entities_near_keywords.append({'entity': p_ent, 'distance': distance})

            if relevant_P_entities_near_keywords:
                relevant_P_entities_near_keywords.sort(key=lambda x: x['distance'])
                selected_person_entity = relevant_P_entities_near_keywords[0]['entity']
                print(f"DEBUG [FHIR Mapper]: Vybrána entita 'P' '{selected_person_entity['text']}' na základě blízkosti ke klíčovému slovu.")
            elif person_entities_P: # Pokud žádná není blízko klíč. slov, vezmeme první dle dokumentu
                person_entities_P.sort(key=lambda x: x['start_char'])
                selected_person_entity = person_entities_P[0]
                print(f"DEBUG [FHIR Mapper]: Žádná entita 'P' nebyla blízko klíčových slov. Vybrána první entita 'P' v dokumentu: '{selected_person_entity['text']}'.")

            if selected_person_entity:
                patient_data["full_name"] = selected_person_entity['text'].strip()
                found_name_by_nlp = True
                print(f"DEBUG [FHIR Mapper]: Nalezeno jméno pacienta (NLP typ P): {patient_data['full_name']}")

        if not found_name_by_nlp and atomic_name_parts_entities:
            # Logika pro skládaná jména, preferujeme části blízko klíčových slov
            print(f"DEBUG [FHIR Mapper]: parse_patient_data: Pokus o sestavení jména z atomických částí ({len(atomic_name_parts_entities)} nalezeno).")
            relevant_atomic_parts = []
            # Pokud máme kontext klíčových slov, zkusíme filtrovat atomické části
            # Tento výběr je složitější, protože části jména mohou být rozptýlené.
            # Pro zjednodušení: pokud existuje 'selected_person_entity' (i když třeba nebylo použito),
            # můžeme se pokusit hledat atomické části v jeho okolí.
            # Nebo jednoduše vezmeme ty, které jsou blízko jakémukoliv patient_name_keyword.

            # Prozatím zjednodušená logika: Sestavíme jméno z částí, které jsou blízko sebe.
            # Ideálně bychom chtěli identifikovat "hlavní" blok jména.
            current_person_parts = []
            # Hledáme první sadu atomických částí, které jsou blízko nějakému klíčovému slovu,
            # nebo pokud takové nejsou, tak první sadu na začátku dokumentu.
            # Tento kód je z původní verze a může být dále vylepšen kontextovým filtrováním.
            # Zde by se hodila sofistikovanější logika pro seskupování částí jména.
            # Prozatím ponecháme původní logiku seskupování, ale s vědomím možného vylepšení.

            # Zkusíme najít první atomickou část, která je blízko klíčového slova
            first_relevant_atomic_part_index = -1
            if patient_name_keywords and text:
                 for kw_pattern in patient_name_keywords:
                    for kw_match in re.finditer(kw_pattern, text, re.IGNORECASE):
                        kw_end_pos = kw_match.end()
                        for idx, atom_ent in enumerate(atomic_name_parts_entities):
                            if atom_ent['start_char'] >= kw_end_pos and \
                               atom_ent['start_char'] < kw_end_pos + keyword_proximity_window:
                                if first_relevant_atomic_part_index == -1 or idx < first_relevant_atomic_part_index:
                                    first_relevant_atomic_part_index = idx
                        if first_relevant_atomic_part_index != -1: break
                    if first_relevant_atomic_part_index != -1: break

            start_index_for_assembly = 0
            if first_relevant_atomic_part_index != -1:
                start_index_for_assembly = first_relevant_atomic_part_index
                print(f"DEBUG [FHIR Mapper]: Začínám sestavovat jméno z atomických částí od indexu {start_index_for_assembly} (blízko klíč. slova).")
            else:
                print(f"DEBUG [FHIR Mapper]: Žádné atomické části jména nebyly blízko klíč. slov. Sestavuji od začátku seřazených atom. částí.")

            for i in range(start_index_for_assembly, len(atomic_name_parts_entities)):
                ent = atomic_name_parts_entities[i]
                if not current_person_parts or ent['start_char'] < current_person_parts[-1]['end_char'] + 10: # Zvětšené okno pro mezery
                    current_person_parts.append(ent)
                else:
                    # Pokud narazíme na větší mezeru, a už máme nějaké části, ukončíme.
                    if current_person_parts:
                        break

            if current_person_parts:
                assembled_name_text = " ".join([p['text'] for p in current_person_parts])
                patient_data["full_name"] = assembled_name_text.strip()
                found_name_by_nlp = True
                print(f"DEBUG [FHIR Mapper]: Nalezeno jméno pacienta (NLP atomické typy): {patient_data['full_name']}")

        # --- Extrakce data narození pomocí NLP ---
        # Entity typu 'T' (čas), 'DATE' (obecné datum), 'td', 'tm', 'ty' (den, měsíc, rok)
        date_candidate_nlp_entities = [ent for ent in nlp_entities if ent.get('type') in ['T', 'DATE', 'td', 'tm', 'ty']]
        date_candidate_nlp_entities.sort(key=lambda x: x['start_char'])

        selected_date_entity_text = None

        if date_candidate_nlp_entities:
            print(f"DEBUG [FHIR Mapper]: parse_patient_data: Nalezeno {len(date_candidate_nlp_entities)} kandidátských NLP entit pro datum narození.")
            relevant_date_entities = []
            for kw_pattern in birth_date_keywords:
                for kw_match in re.finditer(kw_pattern, text, re.IGNORECASE):
                    kw_end_pos = kw_match.end()
                    for date_ent in date_candidate_nlp_entities:
                        # Preferujeme entity typu T nebo DATE, pokud jsou dostupné
                        # a nacházejí se v okně za klíčovým slovem.
                        if date_ent.get('type') in ['T', 'DATE'] and \
                           date_ent['start_char'] >= kw_end_pos and \
                           date_ent['start_char'] < kw_end_pos + keyword_proximity_window:
                            distance = date_ent['start_char'] - kw_end_pos
                            relevant_date_entities.append({'entity': date_ent, 'distance': distance})

            if relevant_date_entities:
                relevant_date_entities.sort(key=lambda x: x['distance'])
                selected_date_entity_text = relevant_date_entities[0]['entity']['text'].strip()
                print(f"DEBUG [FHIR Mapper]: Vybrána NLP entita data narození '{selected_date_entity_text}' (typ: {relevant_date_entities[0]['entity']['type']}) na základě blízkosti ke klíčovému slovu.")
            elif date_candidate_nlp_entities:
                # Fallback: Pokud žádná entita není blízko klíč. slov, zkusíme první 'T' nebo 'DATE'
                first_general_date_entity = next((e for e in date_candidate_nlp_entities if e.get('type') in ['T', 'DATE']), None)
                if first_general_date_entity:
                    selected_date_entity_text = first_general_date_entity['text'].strip()
                    print(f"DEBUG [FHIR Mapper]: Žádná entita data nenalezena blízko klíč. slov. Vybrána první obecná entita data (T/DATE): '{selected_date_entity_text}'.")
                # TODO: Zvážit sestavení data z atomických částí (td, tm, ty), pokud nejsou 'T'/'DATE' entity.
                # Toto je komplexnější a prozatím vynecháno.

        if selected_date_entity_text:
            parsed_date_nlp = parse_date_to_fhir_format(selected_date_entity_text)
            if parsed_date_nlp:
                patient_data["birth_date_fhir"] = parsed_date_nlp
                patient_data["birth_date_raw"] = selected_date_entity_text
                found_birth_date_by_nlp = True
                print(f"DEBUG [FHIR Mapper]: Nalezeno datum narození (NLP): {selected_date_entity_text} -> {parsed_date_nlp}")
            else:
                print(f"DEBUG [FHIR Mapper]: NLP entita data '{selected_date_entity_text}' se nepodařila parsovat.")


    # Fallback na Regex pro jméno, pokud NLP nenašlo nebo selhalo
    if not found_name_by_nlp and text:
        name_match = re.search(REGEX_PATIENT_NAME, text, re.IGNORECASE)
        if name_match:
            patient_data["full_name"] = name_match.group(1).strip()
            print(f"DEBUG [FHIR Mapper]: Nalezeno jméno pacienta (Regex fallback): {patient_data['full_name']}")

    # Fallback na Regex pro datum narození, pokud NLP nenašlo
    if not found_birth_date_by_nlp and text:
        birth_date_match = re.search(REGEX_BIRTH_DATE, text, re.IGNORECASE)
        if birth_date_match:
            raw_date_regex = birth_date_match.group(1).strip()
            print(f"DEBUG [FHIR Mapper]: Nalezen surový řetězec data narození (Regex fallback, před čištěním): '{raw_date_regex}'")
            stop_keywords = [
                "RČ", "R.č.", "Rodné číslo", "Pojišťovna", "Poj.", "Bydliště", "Bydl.",
                "Kontakt", "Tel.", "Oddělení", "Odd.", "Status", "Poznámka", "Pozn.", "---"
            ]
            cleaned_date_regex = raw_date_regex
            for keyword in stop_keywords:
                parts = re.split(r'\b' + re.escape(keyword) + r'\b', cleaned_date_regex, maxsplit=1, flags=re.IGNORECASE)
                if len(parts) > 1:
                    cleaned_date_regex = parts[0].strip()
                    print(f"DEBUG [FHIR Mapper]: Řetězec data narození (Regex fallback) oříznut klíčovým slovem '{keyword}': '{cleaned_date_regex}'")

            parsed_date_regex = parse_date_to_fhir_format(cleaned_date_regex)
            if parsed_date_regex:
                patient_data["birth_date_fhir"] = parsed_date_regex
                print(f"DEBUG [FHIR Mapper]: Nalezeno datum narození (Regex fallback): {cleaned_date_regex} -> {parsed_date_regex}")
            else:
                patient_data["birth_date_raw"] = cleaned_date_regex # Uložíme původní z regexu
                print(f"DEBUG [FHIR Mapper]: Datum narození z Regex '{cleaned_date_regex}' se nepodařilo převést do FHIR formátu.")

    # Extrakce rodného čísla (zatím primárně Regex, NLP by mohlo být přidáno později)
    if text: # Rodné číslo stále hledáme v textu pomocí regexu
        birth_number_match = re.search(REGEX_BIRTH_NUMBER, text, re.IGNORECASE)
        if birth_number_match:
            patient_data["birth_number_raw"] = birth_number_match.group(1).strip()
            print(f"DEBUG [FHIR Mapper]: Nalezeno rodné číslo (Regex): {patient_data['birth_number_raw']}")

    print(f"DEBUG [FHIR Mapper]: Ukončeno parsování dat pacienta. Výsledek: {patient_data}")
    return patient_data

def parse_observation_data(nlp_entities: Optional[List[Dict[str, Any]]], text: str) -> dict:
    """
    Parsování dat pro krevní tlak z textu.
    Poznámka: Tato funkce je v současnosti zaměřena pouze na krevní tlak.
    Pro rozšíření o další pozorování by bylo vhodné ji refaktorovat nebo vytvořit obecnější parser.

    Args:
        nlp_entities: Seznam NLP entit (aktuálně se nevyužívá v této funkci).
        text: Vstupní text lékařské zprávy.

    Returns:
        Slovník s daty o krevním tlaku. Klíče:
        - "blood_pressure_value": Hodnota krevního tlaku (např. "120/80").
        - "measurement_time_fhir": Čas měření ve FHIR formátu (ISO).
    """
    observation_data = {}
    found_bp_by_nlp = False

    # Klíčová slova pro krevní tlak (TK)
    # Regexy by měly být dostatečně specifické, aby se předešlo falešným pozitivům.
    # Např. r"\bTK\b" zajistí, že "TK" je celé slovo.
    bp_keywords = [r"\bTK\b", r"Krevní tlak", r"Krevni tlak"] # Přidána varianta bez diakritiky
    # Typy NLP entit, které hledáme pro hodnoty TK (očekáváme čísla)
    bp_target_entity_types = ['CARDINAL', 'NUMBER'] # Ověřit dle NLP modelu, zda 'NUM' nebo jiné nejsou relevantní
    # Okno pro hledání hodnot za klíčovým slovem (v znacích)
    # Např. "TK: 120/80" - okno cca 10-15 by mělo stačit.
    # Větší okno, např. 20-30, pro případy jako "TK naměřen ... 120 / 80"
    bp_nlp_window_size = 30

    if nlp_entities and text: # Potřebujeme entity i původní text pro NLP přístup
        print(f"DEBUG [FHIR Mapper]: parse_observation_data: Pokus o NLP extrakci krevního tlaku. Počet NLP entit: {len(nlp_entities)}")
        # Iterujeme přes definovaná klíčová slova pro krevní tlak
        for keyword_pattern in bp_keywords:
            # Najdeme všechny výskyty klíčového slova v textu
            # Používáme re.finditer, abychom získali pozice (start, end) každého výskytu
            for keyword_match in re.finditer(keyword_pattern, text, re.IGNORECASE):
                # Pro každý nalezený výskyt klíčového slova hledáme blízké číselné entity
                # `keyword_match.end()` je pozice konce klíčového slova. Hledáme za ním.
                # `text` je zde `original_text` s původní velikostí písmen.
                # `nlp_entities` mají pozice `start_char`, `end_char` vztažené k `original_text`.

                # Definovali jsme, že `find_nlp_entities_near_keyword` očekává,
                # že `text_segment_for_search` je celý text, a `nlp_entities` mají absolutní pozice.
                # To je zde splněno, protože `text` je celý originální text.
                # Hledáme v okně *za* klíčovým slovem.
                # Začátek okna je konec klíčového slova, konec okna je konec klíčového slova + window_size.
                # `find_nlp_entities_near_keyword` interně filtruje entity, které spadají do tohoto okna.

                # Pro krevní tlak potřebujeme najít entity v oblasti za klíčovým slovem.
                # `find_nlp_entities_near_keyword` již pracuje s `keyword_match.end()` pro `search_after_keyword=True`
                # a interně si nastaví `search_window_start` a `search_window_end`.
                # Důležité je, aby `nlp_entities` byly všechny dostupné entity z `text`.

                # Použijeme `find_nlp_entities_near_keyword` k nalezení entit v okně za klíčovým slovem.
                # `text` je celý text, ve kterém NLP entity byly detekovány.
                # Musíme předat `nlp_entities` tak, jak jsou (s absolutními pozicemi).
                # `find_nlp_entities_near_keyword` by měl být volán jen jednou per keyword_pattern,
                # ale iteruje přes všechny matche klíčového slova.
                # Raději ho zavoláme jednou s celým textem a necháme ho najít všechny instance.
                # NE, find_nlp_entities_near_keyword je navržen tak, že se volá pro KAŽDÝ match klíčového slova
                # a hledá v jeho specifickém okolí.

                # Úprava: find_nlp_entities_near_keyword by měla být volána pro každý `keyword_match`
                # a měla by dostat `nlp_entities` a `text`.
                # `keyword_match.end()` je konec aktuálního nalezeného klíčového slova.
                # Oblast hledání bude (keyword_match.end(), keyword_match.end() + bp_nlp_window_size).
                # `find_nlp_entities_near_keyword` si sama filtruje entity v tomto okně.

                # Vytvoříme dočasný seznam klíčových slov jen s aktuálním vzorem,
                # protože `find_nlp_entities_near_keyword` iteruje přes `keyword_patterns`.
                # Toto není ideální, funkce by měla spíše přijímat jeden `keyword_match`.
                # Prozatím to tak necháme, ale je to neefektivní.
                # Lepší by bylo, kdyby `find_nlp_entities_near_keyword` přijala `keyword_match_object`
                # a `nlp_entities`, a hledala jen v okolí tohoto jednoho matche.

                # Refaktorovaný přístup: Iterujeme přes matche a pro každý voláme `find_nlp_entities_near_keyword`
                # s tím, že `find_nlp_entities_near_keyword` by měla být schopna pracovat s jedním keyword_pattern
                # a jedním textem, a najít všechny jeho instance.
                # NEBO, předáme `keyword_match.span()` do funkce.

                # Zůstaneme u původního návrhu `find_nlp_entities_near_keyword`, která iteruje přes `keyword_patterns`.
                # Ale zde potřebujeme najít entity specificky pro *tento* `keyword_match`.
                # Takže `find_nlp_entities_near_keyword` musíme upravit nebo použít jinak.

                # JEDNODUŠŠÍ PŘÍSTUP PRO TEĎ:
                # Pro aktuální `keyword_match`, definujeme search_start a search_end.
                # A pak ručně filtrujeme `nlp_entities`.
                search_start_offset = keyword_match.end()
                search_end_offset = search_start_offset + bp_nlp_window_size

                candidate_bp_entities = []
                for entity in nlp_entities:
                    if entity.get('type') in bp_target_entity_types and \
                       entity['start_char'] >= search_start_offset and \
                       entity['end_char'] <= search_end_offset:
                        candidate_bp_entities.append(entity)

                # Seřadíme je podle pozice
                candidate_bp_entities.sort(key=lambda x: x['start_char'])

                print(f"DEBUG [FHIR Mapper]: parse_observation_data: Pro klíčové slovo '{keyword_match.group(0)}' (pozice {keyword_match.span()}), "
                      f"nalezeno {len(candidate_bp_entities)} kandidátských entit v okně [{search_start_offset}-{search_end_offset}]: {candidate_bp_entities}")

                if len(candidate_bp_entities) >= 2:
                    # Máme alespoň dvě číselné entity, předpokládáme systolický/diastolický.
                    # Entity jsou již seřazeny.
                    systolic_entity = candidate_bp_entities[0]
                    diastolic_entity = candidate_bp_entities[1]

                    systolic_text = systolic_entity['text'].strip()
                    diastolic_text = diastolic_entity['text'].strip()

                    # Základní validace, zda texty vypadají jako čísla
                    # (může být zpřesněno, např. kontrola rozsahu)
                    # Použijeme regex pro extrakci číselné hodnoty, abychom byli robustnější vůči textu jako "cca 120".
                    systolic_val_match = re.search(r'\d+', systolic_text)
                    diastolic_val_match = re.search(r'\d+', diastolic_text)

                    if systolic_val_match and diastolic_val_match:
                        s_val = systolic_val_match.group(0)
                        d_val = diastolic_val_match.group(0)

                        # Sestavení hodnoty krevního tlaku
                        bp_value_nlp = f"{s_val}/{d_val}"
                        observation_data["blood_pressure_value"] = bp_value_nlp
                        observation_data["measurement_time_fhir"] = datetime.now().isoformat() # Aktuální čas
                        found_bp_by_nlp = True
                        print(f"DEBUG [FHIR Mapper]: Nalezen krevní tlak (NLP) pomocí klíč. slova '{keyword_match.group(0)}': {bp_value_nlp} (Systole: '{s_val}' z '{systolic_text}', Diastole: '{d_val}' z '{diastolic_text}')")
                        break # Úspěšně nalezeno, přerušíme iteraci přes matche klíčového slova

            if found_bp_by_nlp:
                break # Úspěšně nalezeno, přerušíme iteraci přes typy klíčových slov

    # Fallback na Regex, pokud NLP nenašlo krevní tlak nebo nebyly NLP entity k dispozici
    if not found_bp_by_nlp and text: # Potřebujeme `text` pro regex
        bp_match_regex = re.search(REGEX_BLOOD_PRESSURE, text, re.IGNORECASE)
        if bp_match_regex:
            bp_text_regex_capture = bp_match_regex.group(1) # Text zachycený regexem, např. "120 / 80"
            # Odstranění mezer kolem lomítka
            bp_value_from_regex = "/".join([part.strip() for part in bp_text_regex_capture.split('/')])

            observation_data["blood_pressure_value"] = bp_value_from_regex
            observation_data["measurement_time_fhir"] = datetime.now().isoformat() # Aktuální čas
            print(f"DEBUG [FHIR Mapper]: Nalezen krevní tlak (Regex fallback): {observation_data['blood_pressure_value']}")
        else:
            print(f"DEBUG [FHIR Mapper]: Krevní tlak nenalezen ani pomocí NLP, ani pomocí Regex.")
    elif not text and not nlp_entities:
         print(f"DEBUG [FHIR Mapper]: Krevní tlak nelze hledat - chybí text i NLP entity.")
    elif not text and nlp_entities and not found_bp_by_nlp: # Máme NLP, ale nemáme text pro regex (nemělo by nastat)
        print(f"DEBUG [FHIR Mapper]: Krevní tlak nenalezen pomocí NLP, a chybí text pro Regex fallback.")


    return observation_data

def parse_condition_data(nlp_entities: Optional[List[Dict[str, Any]]], text: str) -> dict:
    """
    Parsování textu diagnózy z lékařské zprávy.

    Args:
        nlp_entities: Seznam NLP entit (aktuálně se nevyužívá v této funkci).
        text: Vstupní text lékařské zprávy.

    Returns:
        Slovník s textem diagnózy. Klíče:
        - "diagnosis_text": Extrahovaný text diagnózy.
        - "onset_date_time_fhir": Předpokládaný čas stanovení diagnózy (aktuální čas).
    """
    condition_data = {}
    found_diagnosis_by_nlp = False

    # Klíčová slova pro diagnózu/závěr
    diagnosis_keywords = [
        r"Diagnóza\s*:", r"Dg\.\s*:", r"Závěr\s*:", r"Zaver\s*:"
    ]
    # Typy NLP entit pro diagnózy (ověřit dle používaného NLP modelu)
    diagnosis_entity_type = 'DIS'
    # Okno pro hledání DIS entit za klíčovým slovem
    diag_keyword_proximity_window = 150 # Zvětšené okno, diagnózy mohou být delší
    # Max mezera mezi DIS entitami pro jejich spojení
    max_gap_between_dis_entities = 20 # Počet znaků (včetně mezer, čárek atd.)

    if nlp_entities and text:
        print(f"DEBUG [FHIR Mapper]: parse_condition_data: Pokus o NLP extrakci diagnózy. Počet NLP entit: {len(nlp_entities)}")
        all_dis_entities_near_keywords = []

        for kw_pattern in diagnosis_keywords:
            for kw_match in re.finditer(kw_pattern, text, re.IGNORECASE):
                kw_end_pos = kw_match.end()
                # Hledáme DIS entity v definovaném okně za tímto klíčovým slovem
                for entity in nlp_entities:
                    if entity.get('type') == diagnosis_entity_type and \
                       entity['start_char'] >= kw_end_pos and \
                       entity['start_char'] < kw_end_pos + diag_keyword_proximity_window:
                        # Přidáme entitu i pozici klíčového slova pro případné pozdější upřesnění
                        if entity not in all_dis_entities_near_keywords: # Abychom neměli duplicity
                             all_dis_entities_near_keywords.append(entity)

        if all_dis_entities_near_keywords:
            all_dis_entities_near_keywords.sort(key=lambda x: x['start_char'])
            print(f"DEBUG [FHIR Mapper]: Nalezeno {len(all_dis_entities_near_keywords)} DIS entit v blízkosti klíčových slov: {[e['text'] for e in all_dis_entities_near_keywords]}")

            # Spojování těsně navazujících DIS entit
            if len(all_dis_entities_near_keywords) > 1:
                merged_dis_text_parts = []
                current_merged_entity = all_dis_entities_near_keywords[0].copy() # Začneme s první

                for i in range(1, len(all_dis_entities_near_keywords)):
                    next_entity = all_dis_entities_near_keywords[i]
                    # Kontrola, zda `next_entity` těsně navazuje na `current_merged_entity`
                    gap = next_entity['start_char'] - current_merged_entity['end_char']
                    intervening_text = text[current_merged_entity['end_char']:next_entity['start_char']]

                    # Podmínky pro spojení: malá mezera a intervenující text neobsahuje signály nového odstavce/věty
                    # Regex pro kontrolu, zda intervenující text obsahuje jen povolené znaky pro spojení
                    # (mezery, čárky, středníky, spojky "a", "i")
                    allowed_intervening_chars_pattern = r"^[,\sAaiI]*$"

                    if gap >= 0 and gap <= max_gap_between_dis_entities and \
                       re.fullmatch(allowed_intervening_chars_pattern, intervening_text):
                        print(f"DEBUG [FHIR Mapper]: Spojuji DIS entitu '{current_merged_entity['text']}' s '{next_entity['text']}' (mezera: {gap}, text mezi: '{intervening_text}').")
                        # Rozšíříme text a end_char aktuální spojené entity
                        current_merged_entity['text'] += intervening_text + next_entity['text']
                        current_merged_entity['end_char'] = next_entity['end_char']
                    else:
                        # Entita nenavazuje, uložíme dosud spojenou a začneme novou
                        merged_dis_text_parts.append(current_merged_entity)
                        current_merged_entity = next_entity.copy()
                        print(f"DEBUG [FHIR Mapper]: DIS entita '{next_entity['text']}' nenavazuje na předchozí. Začínám nový blok.")

                merged_dis_text_parts.append(current_merged_entity) # Přidáme poslední (nebo jedinou) spojenou entitu

                # Prozatím vezmeme text z prvního bloku spojených entit
                # TODO: Zvážit, zda nevytvářet více Condition, pokud je více nesouvislých bloků DIS
                if merged_dis_text_parts:
                    final_dis_entity_data = merged_dis_text_parts[0] # Bereme první blok
                    diagnosis_text_raw_nlp = final_dis_entity_data['text']
                    original_end_char = final_dis_entity_data['end_char']
                    print(f"DEBUG [FHIR Mapper]: Surový text spojených DIS entit (první blok): '{diagnosis_text_raw_nlp}', původní end_char: {original_end_char}")

                    # Experimentální rozšíření konce diagnózy
                    # Zkusíme rozšířit o pár znaků, pokud to vypadá, že konec chybí
                    # Např. pokud končí písmenem a za ním je tečka/čárka v originálním textu
                    # Toto je velmi opatrný pokus.
                    extended_text = diagnosis_text_raw_nlp
                    potential_end_char = original_end_char
                    # Rozšíříme maximálně o 5 znaků, jeden po druhém
                    for i in range(5):
                        if potential_end_char + i < len(text):
                            char_to_add = text[potential_end_char + i]
                            # Podmínka: přidáváme jen interpunkci nebo pokračování slova
                            # Nepřidáváme, pokud je to nová věta (velké písmeno po mezeře) nebo výrazná mezera
                            if char_to_add.isspace() and i > 0: # Pokud už jsme něco přidali a teď je mezera, zvážit konec
                                 # Pokud za mezerou následuje velké písmeno, pravděpodobně nová myšlenka
                                if potential_end_char + i + 1 < len(text) and text[potential_end_char + i + 1].isupper():
                                    break
                            if char_to_add.isalnum() or char_to_add in ['.', ',', ';', ')']: # Povolene znaky pro rozšíření
                                extended_text += char_to_add
                            else: # Narazili jsme na znak, který nechceme (např. nový řádek, speciální znak)
                                break
                        else: # Jsme na konci textu
                            break

                    if extended_text != diagnosis_text_raw_nlp:
                        print(f"DEBUG [FHIR Mapper]: Experimentální rozšíření textu diagnózy na: '{extended_text}'")
                        diagnosis_text_raw_nlp = extended_text

                    condition_data["diagnosis_text"] = re.sub(r'[\.,;\s]$', '', diagnosis_text_raw_nlp).strip() # Finální čištění
                    condition_data["onset_date_time_fhir"] = datetime.now().isoformat()
                    found_diagnosis_by_nlp = True
                    print(f"DEBUG [FHIR Mapper]: Nalezena diagnóza (NLP, spojené/rozšířené DIS): '{condition_data['diagnosis_text']}' (Raw NLP: '{diagnosis_text_raw_nlp}')")

            elif all_dis_entities_near_keywords: # Jen jedna DIS entita nalezena
                selected_entity = all_dis_entities_near_keywords[0]
                diagnosis_text_raw_nlp = selected_entity['text'].strip()
                # Zde by se také mohlo aplikovat experimentální rozšíření, pokud je relevantní.
                # Pro zjednodušení to nyní vynecháme pro jednotlivé entity, ale je to možnost.
                condition_data["diagnosis_text"] = re.sub(r'[\.,;]$', '', diagnosis_text_raw_nlp).strip()
                condition_data["onset_date_time_fhir"] = datetime.now().isoformat()
                found_diagnosis_by_nlp = True
                print(f"DEBUG [FHIR Mapper]: Nalezena diagnóza (NLP, jedna DIS entita): '{condition_data['diagnosis_text']}' (Raw NLP: '{diagnosis_text_raw_nlp}')")

    # Fallback na Regex, pokud NLP nenašlo diagnózu nebo nebyly NLP entity/text
    if not found_diagnosis_by_nlp and text:
        # re.DOTALL umožňuje tečce (.) zachytit i znaky nového řádku, což je pro víceřádkové diagnózy důležité.
        diagnosis_match = re.search(REGEX_DIAGNOSIS_TEXT, text, re.IGNORECASE | re.DOTALL)
        if diagnosis_match:
            diagnosis_text_raw_regex = diagnosis_match.group(1).strip()
            # Odstranění běžných interpunkčních znamének na konci textu diagnózy pro čistší data.
            condition_data["diagnosis_text"] = re.sub(r'[\.,;]$', '', diagnosis_text_raw_regex).strip()
            # Předpokládáme, že diagnóza byla zaznamenána v aktuálním čase.
            condition_data["onset_date_time_fhir"] = datetime.now().isoformat()
            print(f"DEBUG [FHIR Mapper]: Nalezena diagnóza (Regex fallback): '{condition_data['diagnosis_text']}' (Raw Regex: '{diagnosis_text_raw_regex}')")
        else:
            print(f"DEBUG [FHIR Mapper]: Diagnóza nenalezena ani pomocí NLP, ani pomocí Regex.")
    elif not text and not found_diagnosis_by_nlp:
        print(f"DEBUG [FHIR Mapper]: Diagnóza nenalezena (NLP neaktivní/neúspěšné a chybí text pro Regex).")


    # print(f"DEBUG [FHIR Mapper]: Parsed condition data: {condition_data}")
    return condition_data

def parse_vital_signs_data(nlp_entities: Optional[List[Dict[str, Any]]], text: str) -> dict:
    """
    Parsování textu pro extrakci vitálních funkcí: pulz, teplota, výška a hmotnost.

    Args:
        nlp_entities: Seznam NLP entit (aktuálně se nevyužívá v této funkci).
        text: Vstupní text lékařské zprávy.

    Returns:
        Slovník s extrahovanými daty o vitálních funkcích. Klíče:
        - "pulse_value": Hodnota pulzu.
        - "pulse_unit": Jednotka pulzu (standardizováno na "/min").
        - "temperature_value": Hodnota teploty (desetinná čárka normalizována na tečku).
        - "temperature_unit": Jednotka teploty (standardizováno na "°C").
        - "height_value": Hodnota výšky (desetinná čárka normalizována na tečku).
        - "height_unit": Jednotka výšky (standardizováno na "cm").
        - "weight_value": Hodnota hmotnosti (desetinná čárka normalizována na tečku).
        - "weight_unit": Jednotka hmotnosti (standardizováno na "kg").
    """
    vital_signs_data = {}
    # Společné parametry pro NLP vyhledávání
    vital_sign_target_entity_types = ['CARDINAL', 'NUMBER'] # Typy entit pro číselné hodnoty
    vital_sign_nlp_window_size = 25 # Okno v znacích za klíčovým slovem
    surrounding_text_window = 15 # Okno za entitou pro hledání jednotky

    # --- Pulz (Srdeční frekvence) ---
    found_pulse_by_nlp = False
    pulse_keywords = [r"\bPulz\b", r"\bPuls\b", r"\bSF\b", r"Srdeční frekvence", r"Srdecni frekvence"]
    pulse_unit_regex_map = {
        "/min": r"/min|tepů/min|tepu/min|bpm" # standardní jednotka: regex pro její varianty
    }
    if nlp_entities and text:
        print(f"DEBUG [FHIR Mapper]: parse_vital_signs_data: Pokus o NLP extrakci pro Pulz.")
        for keyword_pattern in pulse_keywords:
            for keyword_match in re.finditer(keyword_pattern, text, re.IGNORECASE):
                search_start_offset = keyword_match.end()
                search_end_offset = search_start_offset + vital_sign_nlp_window_size

                candidate_entities = []
                for entity in nlp_entities:
                    if entity.get('type') in vital_sign_target_entity_types and \
                       entity['start_char'] >= search_start_offset and \
                       entity['end_char'] <= search_end_offset:
                        candidate_entities.append(entity)
                candidate_entities.sort(key=lambda x: x['start_char'])

                if candidate_entities:
                    # Vezmeme první nalezenou číselnou entitu
                    value_entity = candidate_entities[0]
                    entity_text_content = value_entity['text']
                    # Okolí za entitou pro hledání jednotky
                    # text[value_entity['end_char'] : value_entity['end_char'] + surrounding_text_window]
                    # zajistí, že bereme text z originálního dokumentu hned za entitou
                    surrounding = text[value_entity['end_char']: value_entity['end_char'] + surrounding_text_window]

                    value, unit = extract_value_and_unit_from_nlp_entity_text(
                        entity_text_content, surrounding, pulse_unit_regex_map, default_unit="/min"
                    )
                    if value and unit: # Potřebujeme hodnotu i jednotku
                        vital_signs_data["pulse_value"] = value
                        vital_signs_data["pulse_unit"] = unit
                        found_pulse_by_nlp = True
                        print(f"DEBUG [FHIR Mapper]: Nalezen Pulz (NLP) pomocí '{keyword_match.group(0)}': {value} {unit}")
                        break
                    elif value_entity: # NLP našlo číslo, ale extrakce selhala (např. chybí jednotka)
                        print(f"DEBUG [FHIR Mapper]: Pulz: NLP našlo entitu '{value_entity['text']}', ale extrakce hodnoty/jednotky selhala. Zkouším kontextový Regex.")
                        context_offset_before = 10
                        context_offset_after = 20 # Větší za, pro jednotku
                        segment_start = max(0, value_entity['start_char'] - context_offset_before)
                        segment_end = min(len(text), value_entity['end_char'] + context_offset_after)
                        contextual_text_segment = text[segment_start:segment_end]

                        pulse_match_context = re.search(REGEX_PULSE, contextual_text_segment, re.IGNORECASE)
                        if pulse_match_context:
                            vital_signs_data["pulse_value"] = pulse_match_context.group(1).strip()
                            vital_signs_data["pulse_unit"] = "/min"
                            found_pulse_by_nlp = True # Označíme jako nalezené NLP cestou (i když s pomocí kontext. regexu)
                            print(f"DEBUG [FHIR Mapper]: Nalezen Pulz (Kontextový Regex fallback) v segmentu '{contextual_text_segment}': {vital_signs_data['pulse_value']} {vital_signs_data['pulse_unit']}")
                            break
            if found_pulse_by_nlp:
                break

    if not found_pulse_by_nlp and text:
        print(f"DEBUG [FHIR Mapper]: Pulz: NLP ani kontextový Regex nebyly úspěšné. Provádím globální Regex fallback.")
        pulse_match_regex = re.search(REGEX_PULSE, text, re.IGNORECASE)
        if pulse_match_regex:
            vital_signs_data["pulse_value"] = pulse_match_regex.group(1).strip()
            vital_signs_data["pulse_unit"] = "/min"
            print(f"DEBUG [FHIR Mapper]: Nalezen Pulz (Globální Regex fallback): {vital_signs_data['pulse_value']} {vital_signs_data['pulse_unit']}")
        else:
            print(f"DEBUG [FHIR Mapper]: Pulz nenalezen ani pomocí NLP, ani pomocí Regex (kontextového i globálního).")

    # --- Tělesná teplota ---
    found_temp_by_nlp = False
    temp_keywords = [r"\bTeplota\b", r"\bT\b"]
    temp_unit_regex_map = {
        "°C": r"°C|C|st\.C|stupňů Celsia" # stupnu Celsia
    }
    if nlp_entities and text:
        print(f"DEBUG [FHIR Mapper]: parse_vital_signs_data: Pokus o NLP extrakci pro Teplotu.")
        for keyword_pattern in temp_keywords:
            for keyword_match in re.finditer(keyword_pattern, text, re.IGNORECASE):
                search_start_offset = keyword_match.end()
                search_end_offset = search_start_offset + vital_sign_nlp_window_size
                candidate_entities = []
                for entity in nlp_entities:
                    if entity.get('type') in vital_sign_target_entity_types and \
                       entity['start_char'] >= search_start_offset and \
                       entity['end_char'] <= search_end_offset:
                        candidate_entities.append(entity)
                candidate_entities.sort(key=lambda x: x['start_char'])

                if candidate_entities:
                    value_entity = candidate_entities[0]
                    entity_text_content = value_entity['text']
                    surrounding = text[value_entity['end_char']: value_entity['end_char'] + surrounding_text_window]
                    value, unit = extract_value_and_unit_from_nlp_entity_text(
                        entity_text_content, surrounding, temp_unit_regex_map, default_unit="°C"
                    )
                    if value and unit:
                        vital_signs_data["temperature_value"] = value
                        vital_signs_data["temperature_unit"] = unit
                        found_temp_by_nlp = True
                        print(f"DEBUG [FHIR Mapper]: Nalezena Teplota (NLP) pomocí '{keyword_match.group(0)}': {value} {unit}")
                        break
                    elif value_entity:
                        print(f"DEBUG [FHIR Mapper]: Teplota: NLP našlo entitu '{value_entity['text']}', ale extrakce hodnoty/jednotky selhala. Zkouším kontextový Regex.")
                        context_offset_before = 10
                        context_offset_after = 20
                        segment_start = max(0, value_entity['start_char'] - context_offset_before)
                        segment_end = min(len(text), value_entity['end_char'] + context_offset_after)
                        contextual_text_segment = text[segment_start:segment_end]

                        temp_match_context = re.search(REGEX_TEMPERATURE, contextual_text_segment, re.IGNORECASE)
                        if temp_match_context:
                            temp_val_raw = temp_match_context.group(1).strip()
                            vital_signs_data["temperature_value"] = temp_val_raw.replace(",", ".")
                            vital_signs_data["temperature_unit"] = "°C"
                            found_temp_by_nlp = True
                            print(f"DEBUG [FHIR Mapper]: Nalezena Teplota (Kontextový Regex fallback) v segmentu '{contextual_text_segment}': {vital_signs_data['temperature_value']} {vital_signs_data['temperature_unit']}")
                            break
            if found_temp_by_nlp:
                break

    if not found_temp_by_nlp and text:
        print(f"DEBUG [FHIR Mapper]: Teplota: NLP ani kontextový Regex nebyly úspěšné. Provádím globální Regex fallback.")
        temp_match_regex = re.search(REGEX_TEMPERATURE, text, re.IGNORECASE)
        if temp_match_regex:
            temperature_value_raw = temp_match_regex.group(1).strip()
            vital_signs_data["temperature_value"] = temperature_value_raw.replace(",", ".")
            vital_signs_data["temperature_unit"] = "°C"
            print(f"DEBUG [FHIR Mapper]: Nalezena Teplota (Globální Regex fallback): {vital_signs_data['temperature_value']} {vital_signs_data['temperature_unit']} (Raw: '{temperature_value_raw}')")
        else:
            print(f"DEBUG [FHIR Mapper]: Teplota nenalezena ani pomocí NLP, ani pomocí Regex (kontextového i globálního).")

    # --- Tělesná výška ---
    found_height_by_nlp = False
    height_keywords = [r"\bVýška\b", r"\bVýš\.", r"Vyska"]
    height_unit_regex_map = {"cm": r"cm|centimetrů"}
    if nlp_entities and text:
        print(f"DEBUG [FHIR Mapper]: parse_vital_signs_data: Pokus o NLP extrakci pro Výšku.")
        for keyword_pattern in height_keywords:
            for keyword_match in re.finditer(keyword_pattern, text, re.IGNORECASE):
                search_start_offset = keyword_match.end()
                search_end_offset = search_start_offset + vital_sign_nlp_window_size
                candidate_entities = []
                for entity in nlp_entities:
                    if entity.get('type') in vital_sign_target_entity_types and \
                       entity['start_char'] >= search_start_offset and \
                       entity['end_char'] <= search_end_offset:
                        candidate_entities.append(entity)
                candidate_entities.sort(key=lambda x: x['start_char'])

                if candidate_entities:
                    value_entity = candidate_entities[0]
                    entity_text_content = value_entity['text']
                    surrounding = text[value_entity['end_char']: value_entity['end_char'] + surrounding_text_window]
                    value, unit = extract_value_and_unit_from_nlp_entity_text(
                        entity_text_content, surrounding, height_unit_regex_map, default_unit="cm"
                    )
                    if value and unit:
                        vital_signs_data["height_value"] = value
                        vital_signs_data["height_unit"] = unit
                        found_height_by_nlp = True
                        print(f"DEBUG [FHIR Mapper]: Nalezena Výška (NLP) pomocí '{keyword_match.group(0)}': {value} {unit}")
                        break
                    elif value_entity:
                        print(f"DEBUG [FHIR Mapper]: Výška: NLP našlo entitu '{value_entity['text']}', ale extrakce hodnoty/jednotky selhala. Zkouším kontextový Regex.")
                        context_offset_before = 10
                        context_offset_after = 20
                        segment_start = max(0, value_entity['start_char'] - context_offset_before)
                        segment_end = min(len(text), value_entity['end_char'] + context_offset_after)
                        contextual_text_segment = text[segment_start:segment_end]

                        height_match_context = re.search(REGEX_HEIGHT, contextual_text_segment, re.IGNORECASE)
                        if height_match_context:
                            height_val_raw = height_match_context.group(1).strip()
                            vital_signs_data["height_value"] = height_val_raw.replace(",", ".")
                            vital_signs_data["height_unit"] = height_match_context.group(2) if height_match_context.group(2) and height_match_context.group(2).lower() == "cm" else "cm"
                            found_height_by_nlp = True
                            print(f"DEBUG [FHIR Mapper]: Nalezena Výška (Kontextový Regex fallback) v segmentu '{contextual_text_segment}': {vital_signs_data['height_value']} {vital_signs_data['height_unit']}")
                            break
            if found_height_by_nlp:
                break

    if not found_height_by_nlp and text:
        print(f"DEBUG [FHIR Mapper]: Výška: NLP ani kontextový Regex nebyly úspěšné. Provádím globální Regex fallback.")
        height_match_regex = re.search(REGEX_HEIGHT, text, re.IGNORECASE)
        if height_match_regex:
            height_value_raw = height_match_regex.group(1).strip()
            vital_signs_data["height_value"] = height_value_raw.replace(",", ".")
            vital_signs_data["height_unit"] = height_match_regex.group(2) if height_match_regex.group(2) and height_match_regex.group(2).lower() == "cm" else "cm"
            print(f"DEBUG [FHIR Mapper]: Nalezena Výška (Globální Regex fallback): {vital_signs_data['height_value']} {vital_signs_data['height_unit']} (Raw: '{height_value_raw}')")
        else:
            print(f"DEBUG [FHIR Mapper]: Výška nenalezena ani pomocí NLP, ani pomocí Regex (kontextového i globálního).")

    # --- Tělesná hmotnost ---
    found_weight_by_nlp = False
    weight_keywords = [r"\bHmotnost\b", r"\bHm\.", r"\bVáha\b", r"Vaha"]
    weight_unit_regex_map = {"kg": r"kg|kilogramů"}
    if nlp_entities and text:
        print(f"DEBUG [FHIR Mapper]: parse_vital_signs_data: Pokus o NLP extrakci pro Hmotnost.")
        for keyword_pattern in weight_keywords:
            for keyword_match in re.finditer(keyword_pattern, text, re.IGNORECASE):
                search_start_offset = keyword_match.end()
                search_end_offset = search_start_offset + vital_sign_nlp_window_size
                candidate_entities = []
                for entity in nlp_entities:
                    if entity.get('type') in vital_sign_target_entity_types and \
                       entity['start_char'] >= search_start_offset and \
                       entity['end_char'] <= search_end_offset:
                        candidate_entities.append(entity)
                candidate_entities.sort(key=lambda x: x['start_char'])

                if candidate_entities:
                    value_entity = candidate_entities[0]
                    entity_text_content = value_entity['text']
                    surrounding = text[value_entity['end_char']: value_entity['end_char'] + surrounding_text_window]
                    value, unit = extract_value_and_unit_from_nlp_entity_text(
                        entity_text_content, surrounding, weight_unit_regex_map, default_unit="kg"
                    )
                    if value and unit:
                        vital_signs_data["weight_value"] = value
                        vital_signs_data["weight_unit"] = unit
                        found_weight_by_nlp = True
                        print(f"DEBUG [FHIR Mapper]: Nalezena Hmotnost (NLP) pomocí '{keyword_match.group(0)}': {value} {unit}")
                        break
                    elif value_entity:
                        print(f"DEBUG [FHIR Mapper]: Hmotnost: NLP našlo entitu '{value_entity['text']}', ale extrakce hodnoty/jednotky selhala. Zkouším kontextový Regex.")
                        context_offset_before = 10
                        context_offset_after = 20
                        segment_start = max(0, value_entity['start_char'] - context_offset_before)
                        segment_end = min(len(text), value_entity['end_char'] + context_offset_after)
                        contextual_text_segment = text[segment_start:segment_end]

                        weight_match_context = re.search(REGEX_WEIGHT, contextual_text_segment, re.IGNORECASE)
                        if weight_match_context:
                            weight_val_raw = weight_match_context.group(1).strip()
                            vital_signs_data["weight_value"] = weight_val_raw.replace(",", ".")
                            vital_signs_data["weight_unit"] = weight_match_context.group(2) if weight_match_context.group(2) and weight_match_context.group(2).lower() == "kg" else "kg"
                            found_weight_by_nlp = True
                            print(f"DEBUG [FHIR Mapper]: Nalezena Hmotnost (Kontextový Regex fallback) v segmentu '{contextual_text_segment}': {vital_signs_data['weight_value']} {vital_signs_data['weight_unit']}")
                            break
            if found_weight_by_nlp:
                break

    if not found_weight_by_nlp and text:
        print(f"DEBUG [FHIR Mapper]: Hmotnost: NLP ani kontextový Regex nebyly úspěšné. Provádím globální Regex fallback.")
        weight_match_regex = re.search(REGEX_WEIGHT, text, re.IGNORECASE)
        if weight_match_regex:
            weight_value_raw = weight_match_regex.group(1).strip()
            vital_signs_data["weight_value"] = weight_value_raw.replace(",", ".")
            vital_signs_data["weight_unit"] = weight_match_regex.group(2) if weight_match_regex.group(2) and weight_match_regex.group(2).lower() == "kg" else "kg"
            print(f"DEBUG [FHIR Mapper]: Nalezena Hmotnost (Globální Regex fallback): {vital_signs_data['weight_value']} {vital_signs_data['weight_unit']} (Raw: '{weight_value_raw}')")
        else:
            print(f"DEBUG [FHIR Mapper]: Hmotnost nenalezena ani pomocí NLP, ani pomocí Regex (kontextového i globálního).")

    if not text and not nlp_entities: # Přesunuto na konec funkce pro obecnou zprávu
        print(f"DEBUG [FHIR Mapper]: parse_vital_signs_data: Nelze hledat vitální funkce - chybí text i NLP entity.")
    return vital_signs_data

# --- Funkce pro vytváření jednotlivých FHIR zdrojů ---

def create_fhir_patient_resource(patient_data: dict) -> dict | None:
    """
    Vytváří FHIR Patient resource z parsovaných dat.

    Args:
        patient_data: Slovník s daty pacienta (jméno, datum narození, RČ).
                      Očekává klíče "full_name" a "birth_date_fhir".
                      Volitelně "birth_number_raw".

    Returns:
        Slovník reprezentující FHIR Patient resource, nebo None pokud chybí potřebná data.
    """
    # Základní validace potřebných dat
    if not patient_data.get("full_name") or not patient_data.get("birth_date_fhir"):
        print("DEBUG [FHIR Mapper]: Nedostatek dat (jméno nebo datum narození) pro vytvoření FHIR Patient resource.")
        return None

    resource_id = generate_fhir_id()
    resource = {
        "resourceType": "Patient",
        "id": resource_id,
        "meta": { # Metadata specifikující profil pro český kontext
            "profile": ["https://ncez.mzcr.cz/fhir/core/StructureDefinition/CzPatient"]
        },
        "name": [{ # Jméno pacienta
            "use": "official", # Oficiální jméno
            "text": patient_data["full_name"] # Celé jméno jako text
        }],
        "birthDate": patient_data["birth_date_fhir"] # Datum narození
    }

    # Pokus o rozdělení jména na 'given' (křestní) a 'family' (příjmení)
    all_name_parts = patient_data["full_name"].split()
    if len(all_name_parts) > 1:
        resource["name"][0]["given"] = all_name_parts[:-1] # Všechna jména kromě posledního
        resource["name"][0]["family"] = all_name_parts[-1]  # Poslední jméno jako příjmení
    elif len(all_name_parts) == 1: # Pokud je jen jedno slovo, předpokládáme, že je to příjmení
        resource["name"][0]["family"] = all_name_parts[0]

    # Zpracování rodného čísla, validace a porovnání s datem narození
    rc_info = None
    if "birth_number_raw" in patient_data:
        raw_rc_str = patient_data["birth_number_raw"]
        cleaned_rc_str = raw_rc_str.replace("/", "").strip()
        if is_valid_birth_number(raw_rc_str): # is_valid_birth_number interně volá extract_info_from_birth_number
            rc_info = extract_info_from_birth_number(cleaned_rc_str) # Znovu voláme pro získání dat

            if rc_info:
                # Přidání RČ jako identifikátoru
                resource["identifier"] = [
                    {
                        "use": "official",
                        "type": {
                            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0203", "code": "NI", "display": "National unique individual identifier"}],
                            "text": "Rodné číslo"
                        },
                        "system": "urn:oid:1.2.203.17.4.1",
                        "value": cleaned_rc_str
                    }
                ]

                # Porovnání data z RČ s poskytnutým datem narození
                if patient_data.get("birth_date_fhir"):
                    try:
                        # Parsování birth_date_fhir (YYYY-MM-DD) na komponenty
                        fhir_date_obj = datetime.strptime(patient_data["birth_date_fhir"], "%Y-%m-%d")
                        fhir_year = fhir_date_obj.year
                        fhir_month = fhir_date_obj.month
                        fhir_day = fhir_date_obj.day

                        if not (rc_info['year'] == fhir_year and \
                                rc_info['month'] == fhir_month and \
                                rc_info['day'] == fhir_day):
                            print(f"VAROVÁNÍ [FHIR Mapper]: Nesoulad mezi datem narození z RČ ({rc_info['day']}.{rc_info['month']}.{rc_info['year']}) "
                                  f"a zadaným datem narození ({patient_data['birth_date_fhir']}). RČ: '{raw_rc_str}'.")
                    except ValueError:
                        print(f"DEBUG [FHIR Mapper]: Chyba při parsování birth_date_fhir ('{patient_data['birth_date_fhir']}') pro porovnání s RČ.")

                # Přidání pohlaví z RČ
                if rc_info['gender_code'] != "unknown":
                    resource["gender"] = rc_info['gender_code']
                else: # Pokud RČ neumožňuje jednoznačné určení pohlaví (např. stará 9místná RČ)
                    print(f"DEBUG [FHIR Mapper]: Pohlaví nebylo jednoznačně určeno z RČ '{raw_rc_str}'.")
            else: # rc_info je None i po is_valid_birth_number (nemělo by nastat, pokud is_valid_birth_number prošlo)
                 print(f"DEBUG [FHIR Mapper]: Nepodařilo se extrahovat informace z validního RČ '{raw_rc_str}' pro účely Patient resource.")
        else:
            print(f"VAROVÁNÍ [FHIR Mapper]: Neplatný formát nebo kontrolní součet rodného čísla: '{raw_rc_str}'. RČ nebude přidáno do FHIR zdroje.")

    print(f"DEBUG [FHIR Mapper]: Vytvořen FHIR Patient resource (ID: {resource_id}).")
    return resource

def create_fhir_observation_bp_resource(observation_data: dict, patient_reference_id: str) -> dict | None:
    """
    Vytváří FHIR Observation resource pro krevní tlak (komponentní).

    Args:
        observation_data: Slovník s daty o krevním tlaku (očekává klíč "blood_pressure_value").
        patient_reference_id: Referenční ID pacienta (např. "Patient/uuid").

    Returns:
        Slovník reprezentující FHIR Observation resource pro krevní tlak,
        nebo None pokud chybí data nebo jsou v neplatném formátu.
    """
    if not observation_data.get("blood_pressure_value"):
        print("DEBUG [FHIR Mapper]: Nedostatek dat (blood_pressure_value) pro vytvoření FHIR Observation (BP).")
        return None

    try:
        # Rozdělení hodnoty TK na systolický a diastolický tlak
        systolic_str, diastolic_str = observation_data["blood_pressure_value"].split('/')
        systolic = int(systolic_str.strip())
        diastolic = int(diastolic_str.strip())

        # Standardizované rozsahy a logování
        systolic_min, systolic_max = 50, 300
        diastolic_min, diastolic_max = 30, 200

        if not (systolic_min <= systolic <= systolic_max):
            print(f"VAROVÁNÍ [FHIR Mapper]: Hodnota Systolický krevní tlak ({systolic} mmHg) je mimo očekávaný fyziologický rozsah ({systolic_min}-{systolic_max} mmHg).")
        if not (diastolic_min <= diastolic <= diastolic_max):
            print(f"VAROVÁNÍ [FHIR Mapper]: Hodnota Diastolický krevní tlak ({diastolic} mmHg) je mimo očekávaný fyziologický rozsah ({diastolic_min}-{diastolic_max} mmHg).")

    except ValueError:
        print(f"CHYBA [FHIR Mapper]: Neplatný formát hodnoty krevního tlaku: '{observation_data['blood_pressure_value']}'. Nelze rozdělit nebo převést na int.")
        return None

    resource_id = generate_fhir_id()
    current_time_iso = datetime.now().isoformat() # Jednotný čas záznamu

    resource = {
        "resourceType": "Observation",
        "id": resource_id,
        "meta": {"profile": ["https://ncez.mzcr.cz/fhir/core/StructureDefinition/VitalSignsObservation"]},
        "status": "final", # Stav pozorování
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs", "display": "Vital Signs"}]}],
        "code": { # Kód pro panel krevního tlaku
            "coding": [{"system": "http://loinc.org", "code": "85354-9", "display": "Blood pressure panel with all children optional"}],
            "text": "Krevní tlak"
        },
        "subject": {"reference": patient_reference_id}, # Reference na pacienta
        # TODO: Validovat effectiveDateTime proti datu narození pacienta, pokud je dostupné.
        "effectiveDateTime": observation_data.get("measurement_time_fhir", current_time_iso), # Čas měření
        "component": [ # Komponenty pro systolický a diastolický tlak
            {
                "code": {"coding": [{"system": "http://loinc.org", "code": "8480-6", "display": "Systolic blood pressure"}], "text": "Systolický krevní tlak"},
                "valueQuantity": {"value": systolic, "unit": "mmHg", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}
            },
            {
                "code": {"coding": [{"system": "http://loinc.org", "code": "8462-4", "display": "Diastolic blood pressure"}], "text": "Diastolický krevní tlak"},
                "valueQuantity": {"value": diastolic, "unit": "mmHg", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}
            }
        ]
    }
    print(f"DEBUG [FHIR Mapper]: Vytvořen FHIR Observation (BP) resource (ID: {resource_id}).")
    return resource

def create_fhir_observation_pulse_resource(observation_data: dict, patient_reference_id: str) -> dict | None:
    """
    Vytváří FHIR Observation resource pro pulz.

    Args:
        observation_data: Slovník obsahující data o pulzu (očekává klíč "pulse_value").
        patient_reference_id: Referenční ID pacienta (např. "Patient/uuid").

    Returns:
        Slovník reprezentující FHIR Observation resource pro pulz, nebo None pokud chybí data.
    """
    if not observation_data.get("pulse_value"):
        print("DEBUG [FHIR Mapper]: Nedostatek dat (pulse_value) pro vytvoření FHIR Observation (Pulz).")
        return None

    resource_id = generate_fhir_id()
    current_time_iso = datetime.now().isoformat()
    measurement_time_to_check = observation_data.get("measurement_time_fhir", current_time_iso) # measurement_time_fhir by mělo být z parse_observation_data

    # Kontrola, zda čas měření není v daleké budoucnosti
    try:
        # Odebrání 'Z' pokud je přítomno, protože fromisoformat to nemusí vždy správně zpracovat s 'Z' v Pythonu < 3.11
        if isinstance(measurement_time_to_check, str) and measurement_time_to_check.endswith('Z'):
            dt_to_check = datetime.fromisoformat(measurement_time_to_check[:-1])
        else:
            dt_to_check = datetime.fromisoformat(str(measurement_time_to_check)) # Zajistíme, že je to string

        if dt_to_check > datetime.now() + timedelta(days=1):
            print(f"VAROVÁNÍ [FHIR Mapper]: effectiveDateTime pro Pulz ('{measurement_time_to_check}') je v daleké budoucnosti.")
    except Exception as e:
        print(f"DEBUG [FHIR Mapper]: Chyba při validaci effectiveDateTime pro Pulz ('{measurement_time_to_check}'): {e}")


    try:
        pulse_val = int(observation_data["pulse_value"])
        pulse_min, pulse_max = 20, 300 # tepů/min
        if not (pulse_min <= pulse_val <= pulse_max):
            print(f"VAROVÁNÍ [FHIR Mapper]: Hodnota Pulz ({pulse_val} /min) je mimo očekávaný fyziologický rozsah ({pulse_min}-{pulse_max} /min).")
    except ValueError:
        print(f"CHYBA [FHIR Mapper]: Neplatná hodnota pulzu: '{observation_data['pulse_value']}'. Nelze převést na int.")
        return None

    resource = {
        "resourceType": "Observation",
        "id": resource_id,
        "meta": {"profile": ["https://ncez.mzcr.cz/fhir/core/StructureDefinition/VitalSignsObservation"]},
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs", "display": "Vital Signs"}]}],
        "code": { # Kód pro srdeční frekvenci
            "coding": [{"system": "http://loinc.org", "code": "8867-4", "display": "Heart rate"}],
            "text": "Pulz"
        },
        "subject": {"reference": patient_reference_id},
        # TODO: Validovat effectiveDateTime proti datu narození pacienta, pokud je dostupné.
        "effectiveDateTime": measurement_time_to_check,
        "valueQuantity": { # Hodnota pulzu
            "value": pulse_val,
            "unit": observation_data.get("pulse_unit", "/min"), # Jednotka (standardizovaná)
            "system": "http://unitsofmeasure.org", # Systém jednotek
            "code": "/min" # UCUM kód
        }
    }
    print(f"DEBUG [FHIR Mapper]: Vytvořen FHIR Observation (Pulz) resource (ID: {resource_id}).")
    return resource

def create_fhir_observation_temperature_resource(observation_data: dict, patient_reference_id: str) -> dict | None:
    """
    Vytváří FHIR Observation resource pro tělesnou teplotu.

    Args:
        observation_data: Slovník obsahující data o teplotě (očekává klíč "temperature_value").
        patient_reference_id: Referenční ID pacienta (např. "Patient/uuid").

    Returns:
        Slovník reprezentující FHIR Observation resource pro teplotu, nebo None pokud chybí data.
    """
    if not observation_data.get("temperature_value"):
        print("DEBUG [FHIR Mapper]: Nedostatek dat (temperature_value) pro vytvoření FHIR Observation (Teplota).")
        return None

    resource_id = generate_fhir_id()
    current_time_iso = datetime.now().isoformat()
    # Pro teplotu, výšku, váhu se measurement_time_fhir typicky nenastavuje v parse_vital_signs_data,
    # takže zde použijeme current_time_iso jako základ pro kontrolu.
    measurement_time_to_check = current_time_iso
    try:
        dt_to_check = datetime.fromisoformat(str(measurement_time_to_check).rstrip('Z'))
        if dt_to_check > datetime.now() + timedelta(days=1):
            print(f"VAROVÁNÍ [FHIR Mapper]: effectiveDateTime pro Teplotu ('{measurement_time_to_check}') je v daleké budoucnosti.")
    except Exception as e:
        print(f"DEBUG [FHIR Mapper]: Chyba při validaci effectiveDateTime pro Teplotu ('{measurement_time_to_check}'): {e}")

    try:
        # Hodnota teploty by měla být již normalizována na tečku jako desetinný oddělovač
        temp_val = float(observation_data["temperature_value"])
        temp_min, temp_max = 30.0, 45.0 # °C
        if not (temp_min <= temp_val <= temp_max):
            print(f"VAROVÁNÍ [FHIR Mapper]: Hodnota Tělesná teplota ({temp_val} °C) je mimo očekávaný fyziologický rozsah ({temp_min}-{temp_max} °C).")
    except ValueError:
        print(f"CHYBA [FHIR Mapper]: Neplatná hodnota teploty: '{observation_data['temperature_value']}'. Nelze převést na float.")
        return None

    resource = {
        "resourceType": "Observation",
        "id": resource_id,
        "meta": {"profile": ["https://ncez.mzcr.cz/fhir/core/StructureDefinition/VitalSignsObservation"]},
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs", "display": "Vital Signs"}]}],
        "code": { # Kód pro tělesnou teplotu
            "coding": [{"system": "http://loinc.org", "code": "8310-5", "display": "Body temperature"}],
            "text": "Tělesná teplota"
        },
        "subject": {"reference": patient_reference_id},
        # TODO: Validovat effectiveDateTime proti datu narození pacienta, pokud je dostupné.
        "effectiveDateTime": measurement_time_to_check,
        "valueQuantity": { # Hodnota teploty
            "value": temp_val,
            "unit": observation_data.get("temperature_unit", "°C"), # Jednotka (standardizovaná)
            "system": "http://unitsofmeasure.org", # Systém jednotek
            "code": "Cel" # UCUM kód pro stupně Celsia
        }
    }
    print(f"DEBUG [FHIR Mapper]: Vytvořen FHIR Observation (Teplota) resource (ID: {resource_id}).")
    return resource

def create_fhir_observation_height_resource(observation_data: dict, patient_reference_id: str) -> dict | None:
    """
    Vytváří FHIR Observation resource pro tělesnou výšku.

    Args:
        observation_data: Slovník obsahující data o výšce (očekává klíč "height_value").
        patient_reference_id: Referenční ID pacienta (např. "Patient/uuid").

    Returns:
        Slovník reprezentující FHIR Observation resource pro výšku, nebo None pokud chybí data.
    """
    if not observation_data.get("height_value"):
        print("DEBUG [FHIR Mapper]: Nedostatek dat (height_value) pro vytvoření FHIR Observation (Výška).")
        return None

    resource_id = generate_fhir_id()
    current_time_iso = datetime.now().isoformat()
    measurement_time_to_check = current_time_iso
    try:
        dt_to_check = datetime.fromisoformat(str(measurement_time_to_check).rstrip('Z'))
        if dt_to_check > datetime.now() + timedelta(days=1):
            print(f"VAROVÁNÍ [FHIR Mapper]: effectiveDateTime pro Výšku ('{measurement_time_to_check}') je v daleké budoucnosti.")
    except Exception as e:
        print(f"DEBUG [FHIR Mapper]: Chyba při validaci effectiveDateTime pro Výšku ('{measurement_time_to_check}'): {e}")

    try:
        height_val = float(observation_data["height_value"])
        height_min, height_max = 40.0, 250.0 # cm
        if not (height_min <= height_val <= height_max):
            print(f"VAROVÁNÍ [FHIR Mapper]: Hodnota Tělesná výška ({height_val} cm) je mimo očekávaný fyziologický rozsah ({height_min}-{height_max} cm).")
    except ValueError:
        print(f"CHYBA [FHIR Mapper]: Neplatná hodnota výšky: '{observation_data['height_value']}'. Nelze převést na float.")
        return None

    resource = {
        "resourceType": "Observation",
        "id": resource_id,
        "meta": {"profile": ["https://ncez.mzcr.cz/fhir/core/StructureDefinition/VitalSignsObservation"]},
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs", "display": "Vital Signs"}]}],
        "code": { # Kód pro tělesnou výšku
            "coding": [{"system": "http://loinc.org", "code": "8302-2", "display": "Body height"}],
            "text": "Tělesná výška"
        },
        "subject": {"reference": patient_reference_id},
        # TODO: Validovat effectiveDateTime proti datu narození pacienta, pokud je dostupné.
        "effectiveDateTime": measurement_time_to_check,
        "valueQuantity": { # Hodnota výšky
            "value": height_val,
            "unit": observation_data.get("height_unit", "cm"), # Jednotka (standardizovaná)
            "system": "http://unitsofmeasure.org", # Systém jednotek
            "code": "cm" # UCUM kód pro cm
        }
    }
    print(f"DEBUG [FHIR Mapper]: Vytvořen FHIR Observation (Výška) resource (ID: {resource_id}).")
    return resource

def create_fhir_observation_weight_resource(observation_data: dict, patient_reference_id: str) -> dict | None:
    """
    Vytváří FHIR Observation resource pro tělesnou hmotnost.

    Args:
        observation_data: Slovník obsahující data o hmotnosti (očekává klíč "weight_value").
        patient_reference_id: Referenční ID pacienta (např. "Patient/uuid").

    Returns:
        Slovník reprezentující FHIR Observation resource pro hmotnost, nebo None pokud chybí data.
    """
    if not observation_data.get("weight_value"):
        print("DEBUG [FHIR Mapper]: Nedostatek dat (weight_value) pro vytvoření FHIR Observation (Hmotnost).")
        return None

    resource_id = generate_fhir_id()
    current_time_iso = datetime.now().isoformat()
    measurement_time_to_check = current_time_iso
    try:
        dt_to_check = datetime.fromisoformat(str(measurement_time_to_check).rstrip('Z'))
        if dt_to_check > datetime.now() + timedelta(days=1):
            print(f"VAROVÁNÍ [FHIR Mapper]: effectiveDateTime pro Hmotnost ('{measurement_time_to_check}') je v daleké budoucnosti.")
    except Exception as e:
        print(f"DEBUG [FHIR Mapper]: Chyba při validaci effectiveDateTime pro Hmotnost ('{measurement_time_to_check}'): {e}")

    try:
        weight_val = float(observation_data["weight_value"])
        weight_min, weight_max = 1.0, 300.0 # kg
        if not (weight_min <= weight_val <= weight_max):
            print(f"VAROVÁNÍ [FHIR Mapper]: Hodnota Tělesná hmotnost ({weight_val} kg) je mimo očekávaný fyziologický rozsah ({weight_min}-{weight_max} kg).")
    except ValueError:
        print(f"CHYBA [FHIR Mapper]: Neplatná hodnota hmotnosti: '{observation_data['weight_value']}'. Nelze převést na float.")
        return None

    resource = {
        "resourceType": "Observation",
        "id": resource_id,
        "meta": {"profile": ["https://ncez.mzcr.cz/fhir/core/StructureDefinition/VitalSignsObservation"]},
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs", "display": "Vital Signs"}]}],
        "code": { # Kód pro tělesnou hmotnost
            "coding": [{"system": "http://loinc.org", "code": "29463-7", "display": "Body weight"}],
            "text": "Tělesná hmotnost"
        },
        "subject": {"reference": patient_reference_id},
        # TODO: Validovat effectiveDateTime proti datu narození pacienta, pokud je dostupné.
        "effectiveDateTime": measurement_time_to_check,
        "valueQuantity": { # Hodnota hmotnosti
            "value": weight_val,
            "unit": observation_data.get("weight_unit", "kg"), # Jednotka (standardizovaná)
            "system": "http://unitsofmeasure.org", # Systém jednotek
            "code": "kg" # UCUM kód pro kg
        }
    }
    print(f"DEBUG [FHIR Mapper]: Vytvořen FHIR Observation (Hmotnost) resource (ID: {resource_id}).")
    return resource

def create_fhir_condition_resource(condition_data: dict, patient_reference_id: str) -> dict | None:
    """
    Vytváří FHIR Condition resource pro diagnózu.

    Args:
        condition_data: Slovník s daty o diagnóze (očekává klíč "diagnosis_text").
        patient_reference_id: Referenční ID pacienta (např. "Patient/uuid").

    Returns:
        Slovník reprezentující FHIR Condition resource, nebo None pokud chybí text diagnózy.
    """
    if not condition_data.get("diagnosis_text"):
        print("DEBUG [FHIR Mapper]: Nedostatek dat (diagnosis_text) pro vytvoření FHIR Condition (Diagnóza).")
        return None

    resource_id = generate_fhir_id()
    current_time_iso = datetime.now().isoformat() # Čas záznamu diagnózy
    recorded_date_to_check = condition_data.get("onset_date_time_fhir", current_time_iso)

    try:
        # Odebrání 'Z' pokud je přítomno
        if isinstance(recorded_date_to_check, str) and recorded_date_to_check.endswith('Z'):
            dt_to_check = datetime.fromisoformat(recorded_date_to_check[:-1])
        else:
            dt_to_check = datetime.fromisoformat(str(recorded_date_to_check))

        if dt_to_check > datetime.now() + timedelta(days=1):
            print(f"VAROVÁNÍ [FHIR Mapper]: recordedDate pro Condition ('{recorded_date_to_check}') je v daleké budoucnosti.")
    except Exception as e:
        print(f"DEBUG [FHIR Mapper]: Chyba při validaci recordedDate pro Condition ('{recorded_date_to_check}'): {e}")

    resource = {
        "resourceType": "Condition",
        "id": resource_id,
        "meta": {"profile": ["https://ncez.mzcr.cz/fhir/core/StructureDefinition/CzCondition"]},
        "clinicalStatus": { # Klinický stav (povinné dle CzCondition profilu)
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active", "display": "Active"}]
        },
        "verificationStatus": { # Stav ověření (povinné dle CzCondition profilu)
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-ver-status", "code": "confirmed", "display": "Confirmed"}]
        },
        "category": [{ # Kategorie diagnózy
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-category", "code": "encounter-diagnosis", "display": "Encounter Diagnosis"}]
        }],
        "code": { # Textový popis diagnózy
            "text": condition_data["diagnosis_text"]
        },
        "subject": {"reference": patient_reference_id}, # Reference na pacienta
        # TODO: Validovat recordedDate proti datu narození pacienta, pokud je dostupné.
        "recordedDate": recorded_date_to_check
    }
    print(f"DEBUG [FHIR Mapper]: Vytvořen FHIR Condition (Diagnóza) resource (ID: {resource_id}).")
    return resource

# --- Hlavní mapovací funkce ---

def map_text_to_fhir(processed_input: Union[str, List[Dict[str, Any]]], original_text: Optional[str] = None) -> list:
    """
    Hlavní funkce pro mapování textu lékařské zprávy na seznam FHIR zdrojů.
    Nyní přijímá buď přímo text, nebo výstup z NLP (seznam entit).

    Postupně parsuje a vytváří:
    1. Patient resource.
    2. Observation resource pro krevní tlak.
    3. Observation resources pro pulz, teplotu, výšku a hmotnost.
    4. Condition resource pro diagnózu.

    Args:
        processed_input (Union[str, List[Dict[str, Any]]]): Buď přímo text lékařské zprávy,
                                                              nebo seznam NLP entit.
        original_text (Optional[str]): Původní nezpracovaný text, důležitý pro regex fallback,
                                       pokud `processed_input` je seznam NLP entit.

    Returns:
        Seznam slovníků, kde každý slovník reprezentuje jeden FHIR resource.
    """
    nlp_entities: Optional[List[Dict[str, Any]]] = None
    text_to_parse_with_regex: str = ""
    # Proměnná pro uchování původního textu s originální velikostí písmen, pokud je k dispozici
    raw_text_for_nlp_fallback: Optional[str] = original_text

    if isinstance(processed_input, list):
        nlp_entities = processed_input
        if original_text:
            text_to_parse_with_regex = original_text # Pro regex fallback použijeme originální text
        else:
            # Fallback, pokud original_text není k dispozici - méně ideální
            print("VAROVÁNÍ [FHIR Mapper]: NLP entity byly poskytnuty, ale chybí original_text. Regex fallback může být méně spolehlivý.")
            # Zde je důležité, aby text_to_parse_with_regex měl zachovanou velikost písmen, pokud možno.
            # Regexy jsou většinou IGNORECASE, ale kontext může být důležitý.
            # Spojení textů entit není dobrý nápad, protože regexy očekávají souvislý text.
            # Pokud original_text není, regex fallback na celý text nebude možný.
            # Můžeme nastavit text_to_parse_with_regex na prázdný string, aby regexy nic nenašly,
            # nebo se pokusit použít text z první entity, což je ale velmi hrubé.
            # Pro tuto fázi, pokud original_text chybí, regex fallbacky budou v podstatě vypnuty pro NLP cestu.
            text_to_parse_with_regex = " " # Nastavíme na něco, co pravděpodobně regexy nenajdou
            if nlp_entities: # Pokud máme alespoň nějaké entity, zkusíme z nich poskládat text
                 # Toto je stále problematické, protože start_char a end_char se vztahují k původnímu textu
                 # Prozatím to necháme takto s varováním.
                 pass # text_to_parse_with_regex zůstane prázdný nebo se použije níže.
    elif isinstance(processed_input, str):
        text_to_parse_with_regex = processed_input # Toto je již normalizovaný text z text_extractor
        raw_text_for_nlp_fallback = processed_input # Pro konzistenci, i když NLP se zde nepoužilo
    else:
        print(f"CHYBA [FHIR Mapper]: Neočekávaný typ vstupních dat: {type(processed_input)}. Očekáván str nebo List[Dict].")
        return []

    # Pokud je text_to_parse_with_regex stále prázdný a máme NLP entity, a original_text nebyl dodán
    # (což by znamenalo, že regex fallbacky nemají na čem pracovat),
    # je to problém v logice volání. Prozatím pokračujeme.
    # Vstup 'text' pro parsovací funkce bude nyní 'text_to_parse_with_regex' nebo 'raw_text_for_nlp_fallback'
    # v závislosti na tom, zda chceme regexům dávat text s původní velikostí písmen nebo normalizovaný.
    # Pro regexy, které jsou většinou IGNORECASE, by normalizovaný text měl být v pořádku.
    # Ale pro konzistenci a případné case-sensitive části regexů (i když by neměly být),
    # je lepší použít text, který nejvíce odpovídá tomu, na co byly regexy původně psány.
    # Pokud máme NLP entity, `original_text` by měl být k dispozici.
    # Pokud máme jen `processed_input` jako string, ten je již normalizovaný (např. lowercase).
    # Použijeme `text_to_parse_with_regex`, který je buď `original_text` (z NLP cesty)
    # nebo `processed_input` (z non-NLP cesty, již normalizovaný).

    if not text_to_parse_with_regex and nlp_entities and not original_text:
        # Toto je stav, kdy nemáme text pro regexy.
        # Můžeme zkusit vytvořit text z entit, ale je to nouzovka.
        # Pro jednoduchost, parsovací funkce dostanou prázdný text, pokud selže vše ostatní.
        print("KRITICKÉ VAROVÁNÍ [FHIR Mapper]: Chybí textový vstup pro regexy, NLP nemusí pokrýt vše.")
        # text_for_regex_parsers = " " # Aby regexy nic nenašly
    # else:
    text_for_regex_parsers = text_to_parse_with_regex # Toto bude text pro regexové parsery


    if not text_for_regex_parsers or not text_for_regex_parsers.strip():
        if not nlp_entities: # Pokud nemáme ani text, ani NLP entity, pak opravdu není co zpracovat
            print("DEBUG [FHIR Mapper]: Vstupní text i NLP entity jsou prázdné. Nebudou vytvořeny žádné FHIR zdroje.")
            return []
        # Pokud máme NLP entity, ale text_for_regex_parsers je prázdný (např. chyběl original_text),
        # stále můžeme zkusit vytvořit pacienta jen z NLP. Regex parsery dostanou prázdný text.
        print("DEBUG [FHIR Mapper]: Vstupní text pro regexy je prázdný, ale NLP entity jsou k dispozici. Pokračuje se zpracováním.")


    fhir_resources = []
    patient_ref_id = None # Bude nastaveno po úspěšném vytvoření Patient resource

    # 1. Parsovat a vytvořit pacienta
    extracted_patient_data = parse_patient_data(nlp_entities, text_for_regex_parsers)
    patient_resource = create_fhir_patient_resource(extracted_patient_data)
    if patient_resource:
        fhir_resources.append(patient_resource)
        patient_ref_id = f"Patient/{patient_resource['id']}"
        print(f"INFO [FHIR Mapper]: Patient resource úspěšně vytvořen (ID: {patient_resource['id']}).")
    else:
        print("INFO [FHIR Mapper]: Patient resource nemohl být vytvořen. Další navázané FHIR zdroje nebudou generovány.")
        return fhir_resources

    # 2. Parsovat a vytvořit Observation pro krevní tlak
    extracted_bp_data = parse_observation_data(nlp_entities, text_for_regex_parsers)
    if extracted_bp_data.get("blood_pressure_value"):
        observation_bp_resource = create_fhir_observation_bp_resource(extracted_bp_data, patient_ref_id)
        if observation_bp_resource:
            fhir_resources.append(observation_bp_resource)
            print(f"INFO [FHIR Mapper]: Observation (BP) resource úspěšně vytvořen (ID: {observation_bp_resource['id']}).")

    # 3. Parsovat a vytvořit Observations pro další vitální funkce
    vital_signs_data = parse_vital_signs_data(nlp_entities, text_for_regex_parsers)
    if vital_signs_data.get("pulse_value"):
        pulse_resource = create_fhir_observation_pulse_resource(vital_signs_data, patient_ref_id)
        if pulse_resource:
            fhir_resources.append(pulse_resource)
            print(f"INFO [FHIR Mapper]: Observation (Pulz) resource úspěšně vytvořen (ID: {pulse_resource['id']}).")

    if vital_signs_data.get("temperature_value"):
        temperature_resource = create_fhir_observation_temperature_resource(vital_signs_data, patient_ref_id)
        if temperature_resource:
            fhir_resources.append(temperature_resource)
            print(f"INFO [FHIR Mapper]: Observation (Teplota) resource úspěšně vytvořen (ID: {temperature_resource['id']}).")

    if vital_signs_data.get("height_value"):
        height_resource = create_fhir_observation_height_resource(vital_signs_data, patient_ref_id)
        if height_resource:
            fhir_resources.append(height_resource)
            print(f"INFO [FHIR Mapper]: Observation (Výška) resource úspěšně vytvořen (ID: {height_resource['id']}).")

    if vital_signs_data.get("weight_value"):
        weight_resource = create_fhir_observation_weight_resource(vital_signs_data, patient_ref_id)
        if weight_resource:
            fhir_resources.append(weight_resource)
            print(f"INFO [FHIR Mapper]: Observation (Hmotnost) resource úspěšně vytvořen (ID: {weight_resource['id']}).")

    # 4. Parsovat a vytvořit Condition pro diagnózu
    extracted_condition_data = parse_condition_data(nlp_entities, text_for_regex_parsers)
    if extracted_condition_data.get("diagnosis_text"):
        condition_resource = create_fhir_condition_resource(extracted_condition_data, patient_ref_id)
        if condition_resource:
            fhir_resources.append(condition_resource)
            print(f"INFO [FHIR Mapper]: Condition (Diagnóza) resource úspěšně vytvořen (ID: {condition_resource['id']}).")

    if not fhir_resources:
        print("DEBUG [FHIR Mapper]: Nebyly vytvořeny žádné FHIR zdroje.")

    print(f"INFO [FHIR Mapper]: Celkem vytvořeno {len(fhir_resources)} FHIR zdrojů.")
    return fhir_resources

# --- Příklad použití pro testování (běží pouze při přímém spuštění skriptu) ---
if __name__ == '__main__':
    # Rozšířené testovací případy pro lepší pokrytí
    sample_text_1 = """
    Pacient: MUDr. Jana Nováková, CSc.
    Datum narození: 15. května 1980
    RČ: 805515/1234 (Validní RČ)
    Bydliště: Někde 123, Město
    ---
    Pacient: Karel Novotný
    Nar.: 20 / 3 / 1975
    Rodné číslo: 7503201234 (Validní RČ)
    Kontakt: 123456789
    ---
    Subjektivní potíže: Bolest hlavy.
    Objektivní nález:
    Krevní tlak: 135 / 88 mmHg
    Pulz: 70/min pravidelný
    Teplota: 36.5 C
    Výška: 175 cm
    Hmotnost: 78.5 kg
    ---
    Diagnóza: Hypertenze esenciální (primární) I10. Dg. Diabetes Mellitus E11.
    Medikace: Prestarium Neo 5 mg 1-0-0
    Doporučení: Kontrola za 3 měsíce.
    """

    sample_text_2 = """
    Zpráva o vyšetření
    Pacientka: Eva Svobodová-Kučerová
    Narozena: 1. ledna 1955
    R.č.: 555101/9876
    ---
    TK: 150/90. Jinak bez výrazných potíží. Puls: 85/min. Teplota 36,8°C.
    Závěr: Lehká arteriální hypertenze.
    Poznámka: Pacientka objednána na další kontrolu.
    """

    sample_text_3 = "Dnes je venku hezky, žádná lékařská data zde nejsou." # Text bez relevantních dat

    sample_text_4 = """
    Jméno pacienta: Petr Pavel
    Dat. nar.: 1.11.1961
    RČ: 611101/0000
    Dg. : Akutní bronchitida J20.9.
    Krevní tlak : 120/80
    SF: 65 /min.
    T: 37,1C
    Výš.: 180cm
    Hm.: 82 kg
    """
    sample_text_5_no_year = """
    Pacientka: Anna Krátká
    Narozena: 10. července
    RČ: 905710/1111
    Závěr: Nachlazení.
    """ # Očekává se chyba při parsování data (chybí rok)

    sample_text_6_bad_date = """
    Pacient: Testovací Subjekt
    Datum narození: 30. února 1990
    Závěr: Chyba v datu.
    """ # Neplatné datum

    sample_text_7_short_month = """
    Pacient: Jan Krátký
    Nar: 5 pro 1988
    Puls: 77/min.
    Závěr: OK.
    """ # Datum se zkráceným názvem měsíce

    sample_text_8_only_patient = """
    Vyšetřovaný: Oldřich Tichý
    Narozen(a): 12. dubna 1960
    Rodné číslo: 600412/0123
    """ # Text obsahující pouze data pacienta

    sample_text_9_no_patient_data = """
    TK: 110/70 mmHg
    Pulz: 60/min
    Teplota: 36.2°C
    Závěr: Pacient se cítí dobře.
    """ # Text bez identifikace pacienta

    sample_text_invalid_data = """
    Pacient: Chyboslav Datel
    Nar.: 10.10.1980
    RČ: 12345/123 (Krátké RČ)
    RČ: 805515/1235 (Neplatné RČ pro 1980 - nedělitelné 11)
    RČ: 405515/1234 (Platné RČ pro <1954 i bez dělitelnosti 11, pokud je 10 číslic)
    RČ: 805515123A (Nečíselné RČ)
    ---
    Objektivní nález:
    Krevní tlak: 40/20 mmHg (Nízký TK)
    TK: 350/250 mmHg (Vysoký TK)
    Pulz: 10/min (Nízký pulz)
    SF: 350/min (Vysoký pulz)
    Teplota: 25 °C (Nízká teplota)
    T: 50C (Vysoká teplota)
    Výška: 30 cm (Nízká výška)
    Výš.: 300 cm (Vysoká výška)
    Hmotnost: 0.5 kg (Nízká hmotnost)
    Hm.: 500 kg (Vysoká hmotnost)
    ---
    Diagnóza: Syndrom nevalidních dat.
    """

    sample_text_height_weight_1 = """
    Pacient: Testovací Subjekt VýškaVáha
    Datum narození: 01.01.1990
    RČ: 900101/1234
    ---
    Subjektivní potíže: Žádné.
    Objektivní nález:
    Krevní tlak: 125/85 mmHg
    Pulz: 60/min
    Teplota: 36.6 C
    Výška: 175.5 cm
    Hmotnost: 68.2 kg
    ---
    Diagnóza: Zdráv.
    """

    sample_text_height_weight_2 = """
    Jméno pacienta: Druhý Testovací Subjekt
    Dat. nar.: 02.02.1985
    RČ: 850202/5678
    ---
    Výš.: 160,5 cm
    Hm.: 70,0 kg
    TK: 130/80
    SF: 75 /min.
    T: 37,0C
    Závěr: Lehce zvýšený TK.
    """

    sample_text_height_weight_3 = """
    Pacientka: Třetí Subjektová
    Narozena: 03.03.1977
    R.č.: 775303/7890
    ---
    Výška: 165
    Váha: 65
    (Jednotky neuvedeny, očekává se cm a kg)
    Teplota: 36.5
    Pulz: 58
    Diagnóza: Bez pozoruhodností.
    """

    sample_text_height_weight_4 = """
    Pacient: Josef Novák
    Narozen: 10.10.1960
    Výška: 181 cm, Hmotnost: 95.3kg, TK: 140/92, Puls: 72/min.
    Závěr: Hypertenze.
    """


    test_texts = {
        "Komplexní zpráva 1": sample_text_1,
        "Komplexní zpráva 2": sample_text_2,
        "Data s nevalidními hodnotami": sample_text_invalid_data,
        "Žádná data": sample_text_3,
        "Krátká zpráva": sample_text_4,
        "Datum bez roku (očekává se chyba)": sample_text_5_no_year,
        "Neplatné datum (30.února)": sample_text_6_bad_date,
        "Datum se zkráceným měsícem (pro)": sample_text_7_short_month,
        "Pouze data pacienta": sample_text_8_only_patient,
        "Data bez pacienta (očekává se chyba pacienta)": sample_text_9_no_patient_data,
        "ISO Datum": "Pacient: Test ISO\nNar.: 2023-07-15",
        "ISO Datum s tečkami": "Pacient: Test ISO Tečky\nNar.: 2024.01.20",
        "ISO Datum s lomítky": "Pacient: Test ISO Lomítka\nNar.: 2022/11/05",
        "Neplatné ISO Datum (měsíc)": "Pacient: Test ISO Měsíc\nNar.: 2023-13-01",
        "Neplatné ISO Datum (den)": "Pacient: Test ISO Den\nNar.: 2023-02-30",
        "Zpráva s výškou a hmotností (des. tečka)": sample_text_height_weight_1,
        "Zpráva s výškou a hmotností (des. čárka, různé klíč. slova)": sample_text_height_weight_2,
        "Zpráva s výškou a hmotností (bez jednotek)": sample_text_height_weight_3,
        "Zpráva s výškou a hmotností (jedna řádka, zkratky)": sample_text_height_weight_4,
    }

    for test_name, sample_text_or_data in test_texts.items():
        print(f"\n--- Testovací případ: {test_name} ---")

        # Rozlišení, zda je vstupem celý text zprávy nebo jen řetězec data pro parse_date_to_fhir_format
        # Pro testování nové funkce map_text_to_fhir budeme vždy předávat text.
        # Testování s NLP entitami by vyžadovalo mockované NLP výstupy.

        current_input_text = ""
        if isinstance(sample_text_or_data, str):
            current_input_text = sample_text_or_data
        elif isinstance(sample_text_or_data, dict) and "text" in sample_text_or_data: # Pro budoucí testy s NLP
            current_input_text = sample_text_or_data["text"]
            # nlp_input = sample_text_or_data["nlp_entities"] # TODO pro testování NLP větve

        if "Pacient:" in current_input_text or "TK:" in current_input_text or "Závěr:" in current_input_text or "Jméno pacienta:" in current_input_text or "Vyšetřovaný:" in current_input_text:
            # Jedná se o komplexní text zprávy
            print(f"Vstupní text (komplexní zpráva):\n{current_input_text}\n")
            # Voláme s `processed_input` jako textem a `original_text` také jako textem (pro simulaci non-NLP cesty s možností fallbacku)
            fhir_result_list = map_text_to_fhir(current_input_text, original_text=current_input_text)
        else:
            # Jedná se o přímý test funkce parse_date_to_fhir_format (ponecháno pro ladění parse_date_to_fhir_format)
            # V tomto případě `sample_text_or_date_string` je samotný date string (poslední řádek po "Nar.: ")
            # nebo je to přímo date string, pokud neobsahuje "Pacient:" atd.
            date_to_test = sample_text_or_date_string
            if "\n" in date_to_test: # Pokud je to vícerádkový string, vezmeme poslední část po "Nar.: "
                 lines = date_to_test.split("\n")
                 for line in reversed(lines):
                     if "Nar.:" in line:
                         date_to_test = line.split("Nar.:")[-1].strip()
                         break
            print(f"Vstupní řetězec data pro parse_date_to_fhir_format: '{date_to_test}'")
            parsed_date = parse_date_to_fhir_format(date_to_test)
            print(f"Výsledek parse_date_to_fhir_format: '{parsed_date}'")
            # Pro konzistenci výstupu můžeme vytvořit "falešný" FHIR list
            if parsed_date:
                 # Vytvoříme jednoduchý Patient resource pro ukázku, pokud datum prošlo
                 fhir_result_list = [{
                     "resourceType": "Patient", "id": "test-patient",
                     "birthDate": parsed_date,
                     "name": [{"text": test_name.replace(" (očekává se chyba)", "")}]
                 }]
            else:
                fhir_result_list = []


        if fhir_result_list:
            print(f"--- Výsledné FHIR zdroje pro '{test_name}' (JSON Bundle) ---")
            # Vytvoření Bundle pro přehlednější výstup
            bundle_resource = {
                "resourceType": "Bundle",
                "id": f"bundle-{generate_fhir_id()}", # Unikátní ID pro Bundle
                "type": "collection", # Typ Bundle
                "entry": [] # Seznam zdrojů v Bundle
            }
            for res_idx, res in enumerate(fhir_result_list):
                bundle_resource["entry"].append({
                    "fullUrl": f"urn:uuid:{res['id']}", # Použití urn:uuid pro interní reference
                    "resource": res # Samotný FHIR zdroj
                })
            # Tisk JSON Bundle s odsazením pro čitelnost a povolením non-ASCII znaků
            print(json.dumps(bundle_resource, indent=2, ensure_ascii=False))
        else:
            print(f"Pro '{test_name}' nebyly vygenerovány žádné FHIR zdroje nebo došlo k chybě při jejich tvorbě.")
