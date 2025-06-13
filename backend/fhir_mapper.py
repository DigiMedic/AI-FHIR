# backend/fhir_mapper.py
import re
import json
from datetime import datetime
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
REGEX_PATIENT_NAME = r"(?:Pacient(?:ka)?|Jméno pacienta|Vyšetřovan(?:ý|á))\s*:\s*([A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+(?:-[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+)?(?:\s+[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+(?:-[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+)?)+)"

# Regex pro datum narození:
# - Hledá klíčová slova jako "Datum narození", "Nar.", "Narozena", "Dat. nar.", "Narozen(a)".
# - Následuje dvojtečka a mezery.
# - Zachytává datum ve formátu DD.MM.YYYY, DD/MM/YYYY nebo DD MM YYYY (s různými oddělovači).
REGEX_BIRTH_DATE = r"(?:Datum narození|Nar\.|Narozena|Dat\. nar\.|Narozen\(a\))\s*:\s*(\d{1,2}[\.\/\s]+\d{1,2}[\.\/\s]+\d{4})"

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
REGEX_DIAGNOSIS_TEXT = r"(?:Diagnóza|Dg\.|Závěr)\s*:\s*(.+?)(?:
\s*
|\Z|Poznámka:|Medikace:|Doporučení:|Terapie:|Výška:|Hmotnost:|Kontrola:|Prognóza:)"


# --- Pomocné (Helper) funkce pro parsování ---

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
    cleaned_date_str = re.sub(r'\s*[\.\/]\s*', '.', cleaned_date_str) # Nahradí mezery/lomítka tečkami
    cleaned_date_str = cleaned_date_str.replace(' ', '.') # Nahradí zbylé mezery tečkami (např. "15. 05. 1980")
    if cleaned_date_str.endswith('.'): # Odstraní tečku na konci, pokud existuje
        cleaned_date_str = cleaned_date_str[:-1]

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
    if not birth_number_str:
        return False
    cleaned_rc = birth_number_str.replace("/", "")

    if not (len(cleaned_rc) == 9 or len(cleaned_rc) == 10):
        print(f"DEBUG [FHIR Mapper]: Neplatná délka RČ: {len(cleaned_rc)} pro '{birth_number_str}'. Musí být 9 nebo 10.")
        return False

    if not cleaned_rc.isdigit():
        print(f"DEBUG [FHIR Mapper]: RČ '{birth_number_str}' obsahuje nečíselné znaky.")
        return False

    # Pro RČ přidělovaná od 1. ledna 1954 (desetimístná) se kontroluje dělitelnost 11.
    # RČ přidělovaná od 1.1.2004 již nemusí být dělitelná 11, ale pro zjednodušení
    # tuto kontrolu zde ponecháváme pro starší RČ, kde platila.
    # Pro devítimístná RČ (před 1954) tato kontrola obecně neplatí.
    if len(cleaned_rc) == 10:
        year_prefix = int(cleaned_rc[:2])
        # Kontrola dělitelnosti 11 pro RČ vydaná v roce 1954 a později.
        # Pro RČ vydaná před rokem 1954 (první dvojčíslí < 54) se dělitelnost 11 typicky nekontrolovala
        # nebo měla jiná pravidla, která zde pro zjednodušení neimplementujeme.
        # Dále, RČ od 2004 nemusí být dělitelná 11.
        # Tato podmínka je tedy zjednodušením pro běžná RČ z let 1954-2003.
        if year_prefix >= 54 : # Zahrnuje roky 1954-1999 a 2054+ (což je v budoucnu)
                               # a také roky 2004-2053 (kde už dělitelnost platit nemusí)
                               # Pro jednoduchost zde kontrolujeme pro všechny 10-místné RČ s rokem >= 54
            if int(cleaned_rc) % 11 != 0:
                print(f"DEBUG [FHIR Mapper]: RČ '{birth_number_str}' (10místné, rok >= 1954) není dělitelné 11.")
                return False
    return True

def generate_fhir_id() -> str:
    """
    Generuje unikátní identifikátor (UUID) pro FHIR zdroje.

    Returns:
        Řetězec reprezentující UUID.
    """
    return str(uuid.uuid4())

# --- Funkce pro parsování specifických dat z textu ---

def parse_patient_data(text: str) -> dict:
    """
    Parsování základních demografických údajů o pacientovi z textu.

    Extrahuje jméno, datum narození a rodné číslo.

    Args:
        text: Vstupní text lékařské zprávy.

    Returns:
        Slovník s extrahovanými daty pacienta. Klíče:
        - "full_name": Celé jméno pacienta.
        - "birth_date_fhir": Datum narození ve FHIR formátu (YYYY-MM-DD).
        - "birth_date_raw": Původní extrahovaný řetězec data narození (pokud FHIR formát selže).
        - "birth_number_raw": Extrahované rodné číslo (s nebo bez lomítka).
    """
    patient_data = {} # Inicializace prázdného slovníku pro data pacienta

    # Extrakce jména pacienta
    name_match = re.search(REGEX_PATIENT_NAME, text, re.IGNORECASE)
    if name_match:
        patient_data["full_name"] = name_match.group(1).strip()
        print(f"DEBUG [FHIR Mapper]: Nalezeno jméno pacienta: {patient_data['full_name']}")

    # Extrakce data narození
    birth_date_match = re.search(REGEX_BIRTH_DATE, text, re.IGNORECASE)
    if birth_date_match:
        raw_date = birth_date_match.group(1).strip()
        print(f"DEBUG [FHIR Mapper]: Nalezen řetězec data narození: '{raw_date}'")
        patient_data["birth_date_fhir"] = parse_date_to_fhir_format(raw_date)
        if not patient_data["birth_date_fhir"]:
            patient_data["birth_date_raw"] = raw_date # Uložíme původní, pokud parsování selhalo
            print(f"DEBUG [FHIR Mapper]: Datum narození se nepodařilo převést do FHIR formátu, uloženo raw: '{raw_date}'")
        else:
            print(f"DEBUG [FHIR Mapper]: Datum narození převedeno do FHIR formátu: {patient_data['birth_date_fhir']}")

    # Extrakce rodného čísla
    birth_number_match = re.search(REGEX_BIRTH_NUMBER, text, re.IGNORECASE)
    if birth_number_match:
        patient_data["birth_number_raw"] = birth_number_match.group(1).strip()
        print(f"DEBUG [FHIR Mapper]: Nalezeno rodné číslo: {patient_data['birth_number_raw']}")

    print(f"DEBUG [FHIR Mapper]: Ukončeno parsování dat pacienta. Výsledek: {patient_data}")
    return patient_data

def parse_observation_data(text: str) -> dict:
    """
    Parsování dat pro krevní tlak z textu.
    Poznámka: Tato funkce je v současnosti zaměřena pouze na krevní tlak.
    Pro rozšíření o další pozorování by bylo vhodné ji refaktorovat nebo vytvořit obecnější parser.

    Args:
        text: Vstupní text lékařské zprávy.

    Returns:
        Slovník s daty o krevním tlaku. Klíče:
        - "blood_pressure_value": Hodnota krevního tlaku (např. "120/80").
        - "measurement_time_fhir": Čas měření ve FHIR formátu (ISO).
    """
    observation_data = {} # Inicializace prázdného slovníku

    # Extrakce krevního tlaku
    bp_match = re.search(REGEX_BLOOD_PRESSURE, text, re.IGNORECASE)
    if bp_match:
        # Odstranění mezer z hodnoty TK, např. "120 / 80" -> "120/80"
        observation_data["blood_pressure_value"] = bp_match.group(1).replace(" ", "")
        # Předpokládáme aktuální čas měření, pokud není specifikován jinak
        observation_data["measurement_time_fhir"] = datetime.now().isoformat()
        print(f"DEBUG [FHIR Mapper]: Nalezen krevní tlak: {observation_data['blood_pressure_value']}")

    # Pokud by funkce parsovala více typů pozorování, log by byl zde obecnější.
    # print(f"DEBUG [FHIR Mapper]: Parsed specific observation data: {observation_data}")
    return observation_data

def parse_condition_data(text: str) -> dict:
    """
    Parsování textu diagnózy z lékařské zprávy.

    Args:
        text: Vstupní text lékařské zprávy.

    Returns:
        Slovník s textem diagnózy. Klíče:
        - "diagnosis_text": Extrahovaný text diagnózy.
        - "onset_date_time_fhir": Předpokládaný čas stanovení diagnózy (aktuální čas).
    """
    condition_data = {} # Inicializace prázdného slovníku

    # Extrakce textu diagnózy
    # re.DOTALL umožňuje tečce (.) zachytit i znaky nového řádku, což je pro víceřádkové diagnózy důležité.
    diagnosis_match = re.search(REGEX_DIAGNOSIS_TEXT, text, re.IGNORECASE | re.DOTALL)
    if diagnosis_match:
        diagnosis_text_raw = diagnosis_match.group(1).strip()
        # Odstranění běžných interpunkčních znamének na konci textu diagnózy pro čistší data.
        condition_data["diagnosis_text"] = re.sub(r'[\.,;]$', '', diagnosis_text_raw).strip()
        # Předpokládáme, že diagnóza byla zaznamenána v aktuálním čase.
        condition_data["onset_date_time_fhir"] = datetime.now().isoformat()
        print(f"DEBUG [FHIR Mapper]: Nalezena diagnóza: '{condition_data['diagnosis_text']}' (Raw: '{diagnosis_text_raw}')")

    # print(f"DEBUG [FHIR Mapper]: Parsed condition data: {condition_data}")
    return condition_data

def parse_vital_signs_data(text: str) -> dict:
    """
    Parsování textu pro extrakci vitálních funkcí: pulz, teplota, výška a hmotnost.

    Args:
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
    vital_signs_data = {} # Inicializace prázdného slovníku

    # Extrakce pulzu
    pulse_match = re.search(REGEX_PULSE, text, re.IGNORECASE)
    if pulse_match:
        vital_signs_data["pulse_value"] = pulse_match.group(1).strip()
        vital_signs_data["pulse_unit"] = "/min" # Standardizovaná jednotka pro FHIR
        print(f"DEBUG [FHIR Mapper]: Nalezen pulz: {vital_signs_data['pulse_value']} {vital_signs_data['pulse_unit']}")

    # Extrakce teploty
    temp_match = re.search(REGEX_TEMPERATURE, text, re.IGNORECASE)
    if temp_match:
        temperature_value_raw = temp_match.group(1).strip()
        # Normalizace desetinného oddělovače (čárka -> tečka) pro konzistentní zpracování float()
        vital_signs_data["temperature_value"] = temperature_value_raw.replace(",", ".")
        vital_signs_data["temperature_unit"] = "°C" # Standardizovaná jednotka pro FHIR
        print(f"DEBUG [FHIR Mapper]: Nalezena teplota: {vital_signs_data['temperature_value']} {vital_signs_data['temperature_unit']} (Raw: '{temperature_value_raw}')")

    # Extrakce výšky
    height_match = re.search(REGEX_HEIGHT, text, re.IGNORECASE)
    if height_match:
        height_value_raw = height_match.group(1).strip()
        vital_signs_data["height_value"] = height_value_raw.replace(",", ".")
        # Pokud je jednotka explicitně uvedena a je "cm", použijeme ji, jinak default "cm".
        # group(2) může být None, pokud jednotka není v textu.
        vital_signs_data["height_unit"] = height_match.group(2) if height_match.group(2) and height_match.group(2).lower() == "cm" else "cm"
        print(f"DEBUG [FHIR Mapper]: Nalezena výška: {vital_signs_data['height_value']} {vital_signs_data['height_unit']} (Raw: '{height_value_raw}')")

    # Extrakce hmotnosti
    weight_match = re.search(REGEX_WEIGHT, text, re.IGNORECASE)
    if weight_match:
        weight_value_raw = weight_match.group(1).strip()
        vital_signs_data["weight_value"] = weight_value_raw.replace(",", ".")
        # Pokud je jednotka explicitně uvedena a je "kg", použijeme ji, jinak default "kg".
        # group(2) může být None.
        vital_signs_data["weight_unit"] = weight_match.group(2) if weight_match.group(2) and weight_match.group(2).lower() == "kg" else "kg"
        print(f"DEBUG [FHIR Mapper]: Nalezena hmotnost: {vital_signs_data['weight_value']} {vital_signs_data['weight_unit']} (Raw: '{weight_value_raw}')")

    # print(f"DEBUG [FHIR Mapper]: Parsed vital signs data: {vital_signs_data}")
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

    # Přidání rodného čísla jako identifikátoru, pokud bylo nalezeno
    if "birth_number_raw" in patient_data:
        raw_rc = patient_data["birth_number_raw"]
        if is_valid_birth_number(raw_rc):
            birth_number_cleaned = raw_rc.replace("/", "") # Odstranění případného lomítka
            resource["identifier"] = [
                {
                    "use": "official", # Oficiální identifikátor
                "type": { # Typ identifikátoru
                    "coding": [
                        { # Kódování typu
                            "system": "http://terminology.hl7.org/CodeSystem/v2-0203", # Systém kódování
                            "code": "NI", # National unique individual identifier
                            "display": "National unique individual identifier"
                        }
                    ],
                    "text": "Rodné číslo" # Český popis
                },
                "system": "urn:oid:1.2.203.17.4.1", # OID pro rodná čísla v ČR
                    "value": birth_number_cleaned # Hodnota rodného čísla
                }
            ]
        else:
            print(f"VAROVÁNÍ [FHIR Mapper]: Neplatný formát nebo kontrolní součet rodného čísla: '{raw_rc}'. RČ nebude přidáno do FHIR zdroje.")

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

        # Validace rozsahu hodnot
        if not (50 <= systolic <= 300):
            print(f"VAROVÁNÍ [FHIR Mapper]: Systolický tlak {systolic} je mimo očekávaný rozsah (50-300 mmHg).")
        if not (30 <= diastolic <= 200):
            print(f"VAROVÁNÍ [FHIR Mapper]: Diastolický tlak {diastolic} je mimo očekávaný rozsah (30-200 mmHg).")

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

    try:
        pulse_val = int(observation_data["pulse_value"])
        if not (20 <= pulse_val <= 300):
            print(f"VAROVÁNÍ [FHIR Mapper]: Hodnota pulzu {pulse_val} je mimo očekávaný rozsah (20-300 tepů/min).")
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
        "effectiveDateTime": current_time_iso, # Čas záznamu
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

    try:
        # Hodnota teploty by měla být již normalizována na tečku jako desetinný oddělovač
        temp_val = float(observation_data["temperature_value"])
        if not (30.0 <= temp_val <= 45.0):
            print(f"VAROVÁNÍ [FHIR Mapper]: Hodnota teploty {temp_val}°C je mimo očekávaný rozsah (30.0-45.0°C).")
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
        "effectiveDateTime": current_time_iso, # Čas záznamu
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

    try:
        height_val = float(observation_data["height_value"])
        if not (40.0 <= height_val <= 250.0):
            print(f"VAROVÁNÍ [FHIR Mapper]: Hodnota výšky {height_val} cm je mimo očekávaný rozsah (40.0-250.0 cm).")
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
        "effectiveDateTime": current_time_iso, # Čas záznamu
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

    try:
        weight_val = float(observation_data["weight_value"])
        if not (1.0 <= weight_val <= 300.0):
            print(f"VAROVÁNÍ [FHIR Mapper]: Hodnota hmotnosti {weight_val} kg je mimo očekávaný rozsah (1.0-300.0 kg).")
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
        "effectiveDateTime": current_time_iso, # Čas záznamu
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
        "recordedDate": condition_data.get("onset_date_time_fhir", current_time_iso) # Datum záznamu
    }
    print(f"DEBUG [FHIR Mapper]: Vytvořen FHIR Condition (Diagnóza) resource (ID: {resource_id}).")
    return resource

# --- Hlavní mapovací funkce ---

def map_text_to_fhir(text: str) -> list:
    """
    Hlavní funkce pro mapování textu lékařské zprávy na seznam FHIR zdrojů.

    Postupně parsuje a vytváří:
    1. Patient resource.
    2. Observation resource pro krevní tlak.
    3. Observation resources pro pulz, teplotu, výšku a hmotnost.
    4. Condition resource pro diagnózu.

    Args:
        text: Vstupní text lékařské zprávy.

    Returns:
        Seznam slovníků, kde každý slovník reprezentuje jeden FHIR resource.
        Pokud vstupní text je prázdný nebo nelze vytvořit Patient resource,
        může vrátit prázdný seznam nebo seznam s omezeným počtem zdrojů.
    """
    if not text or not text.strip(): # Kontrola prázdného nebo "whitespace-only" textu
        print("DEBUG [FHIR Mapper]: Vstupní text je prázdný nebo obsahuje pouze bílé znaky. Nebudou vytvořeny žádné FHIR zdroje.")
        return []

    fhir_resources = []
    patient_ref_id = None # Bude nastaveno po úspěšném vytvoření Patient resource

    # 1. Parsovat a vytvořit pacienta
    # Je důležité mít data pacienta jako první, protože ostatní zdroje na něj referencují.
    extracted_patient_data = parse_patient_data(text)
    # I když je slovník extracted_patient_data prázdný, funkce parse_patient_data ho vrátí.
    # create_fhir_patient_resource si poradí s případným nedostatkem klíčů.
    patient_resource = create_fhir_patient_resource(extracted_patient_data)
    if patient_resource:
        fhir_resources.append(patient_resource)
        patient_ref_id = f"Patient/{patient_resource['id']}" # Vytvoření reference pro další zdroje
        print(f"INFO [FHIR Mapper]: Patient resource úspěšně vytvořen (ID: {patient_resource['id']}).")
    else:
        # Pokud se nepodařilo vytvořit pacienta, nemá smysl pokračovat s dalšími zdroji,
        # které na něj musí referencovat.
        print("INFO [FHIR Mapper]: Patient resource nemohl být vytvořen (nedostatek dat nebo chyba). Další navázané FHIR zdroje nebudou generovány.")
        return fhir_resources # Vrátí prázdný list, pokud pacient nebyl vytvořen.

    # 2. Parsovat a vytvořit Observation pro krevní tlak
    # Poznámka: parse_observation_data aktuálně obsahuje jen krevní tlak.
    # Pokud by parsovala více věcí, bylo by lepší ji rozdělit nebo přejmenovat na např. parse_blood_pressure_data.
    extracted_bp_data = parse_observation_data(text) # Tato funkce se zaměřuje na TK
    if extracted_bp_data.get("blood_pressure_value"): # Kontrola, zda byla hodnota TK nalezena
        observation_bp_resource = create_fhir_observation_bp_resource(extracted_bp_data, patient_ref_id)
        if observation_bp_resource:
            fhir_resources.append(observation_bp_resource)
            print(f"INFO [FHIR Mapper]: Observation (BP) resource úspěšně vytvořen (ID: {observation_bp_resource['id']}).")


    # 3. Parsovat a vytvořit Observations pro další vitální funkce (pulz, teplota)
    vital_signs_data = parse_vital_signs_data(text)
    # Není třeba kontrolovat `if vital_signs_data:`, protože funkce vždy vrací slovník.
    # Kontrolujeme přítomnost specifických klíčů níže.

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
    extracted_condition_data = parse_condition_data(text)
    if extracted_condition_data.get("diagnosis_text"): # Kontrola, zda byl text diagnózy nalezen
        condition_resource = create_fhir_condition_resource(extracted_condition_data, patient_ref_id)
        if condition_resource:
            fhir_resources.append(condition_resource)
            print(f"INFO [FHIR Mapper]: Condition (Diagnóza) resource úspěšně vytvořen (ID: {condition_resource['id']}).")


    if not fhir_resources:
        print("DEBUG [FHIR Mapper]: Nebyly vytvořeny žádné FHIR zdroje z daného textu (ani Patient).")
    # Následující log je spíše pro interní kontrolu konzistence, pokud by došlo k chybě v logice výše.
    # elif len(fhir_resources) == 1 and fhir_resources[0]["resourceType"] == "Patient" and not patient_ref_id:
    #     print("DEBUG [FHIR Mapper]: Byl vytvořen pouze Patient resource, ale chybí patient_ref_id pro další zdroje. Toto by nemělo nastat.")

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
    }

    for test_name, sample_text_or_date_string in test_texts.items():
        print(f"\n--- Testovací případ: {test_name} ---")

        # Rozlišení, zda je vstupem celý text zprávy nebo jen řetězec data pro parse_date_to_fhir_format
        if "Pacient:" in sample_text_or_date_string or "TK:" in sample_text_or_date_string or not re.match(r"^\d{4}[\.\/\-]", sample_text_or_date_string.split("\n")[-1].replace("Nar.: ","").strip()):
            # Jedná se o komplexní text zprávy
            print(f"Vstupní text (komplexní zpráva):\n{sample_text_or_date_string}\n")
            fhir_result_list = map_text_to_fhir(sample_text_or_date_string)
        else:
            # Jedná se o přímý test funkce parse_date_to_fhir_format
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
