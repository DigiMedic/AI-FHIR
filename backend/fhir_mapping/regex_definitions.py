# backend/fhir_mapping/regex_definitions.py
import re

# Tento soubor obsahuje definice regulárních výrazů používaných pro parsování
# lékařských zpráv v rámci fhir_mapping balíčku.

# Regex pro jméno pacienta:
REGEX_PATIENT_NAME = r"(?:Pacient(?:ka)?|Jméno pacienta|Vyšetřovan(?:ý|á))\s*:\s*([A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+(?:-[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+)?(?:\s+[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+(?:-[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+)?)*)(?=\s*(?:Datum narození|Nar\.|Narozena|Dat\. nar\.|Narozen\(a\)|R(?:odné|\.č\.)|Bydliště|Poznámka|---|$))"

# Regex pro datum narození:
REGEX_BIRTH_DATE = r"(?:Datum narození|Nar\.|Narozena|Dat\. nar\.|Narozen\(a\))\s*:\s*([^\n\r]+)"

# Regex pro rodné číslo:
REGEX_BIRTH_NUMBER = r"(?:Rodné číslo|RČ|R\.č\.)\s*:\s*(\d{6}\/?\d{3,4})"

# Regex pro krevní tlak:
REGEX_BLOOD_PRESSURE = r"(?:Krevní tlak|TK)\s*:\s*(\d{2,3}\s*\/\s*\d{2,3})\s*(?:mmHg)?"

# Regex pro pulz (srdeční frekvenci):
REGEX_PULSE = r"(?:Pulz|Puls|Srdeční frekvence|SF)\s*:\s*(\d{2,3})\s*(?:/min|tepů/min|/min\.)"

# Regex pro tělesnou teplotu:
REGEX_TEMPERATURE = r"(?:Teplota|T)\s*:\s*(\d{2}(?:[\.,]\d{1,2})?)\s*(?:°C|C)"

# Regex pro tělesnou výšku:
REGEX_HEIGHT = r"(?:Výška|Výš\.)\s*:\s*(\d{2,3}(?:[\.,]\d{1,2})?)\s*(cm)?"

# Regex pro tělesnou hmotnost:
REGEX_WEIGHT = r"(?:Hmotnost|Hm\.|Váha)\s*:\s*(\d{1,3}(?:[\.,]\d{1,2})?)\s*(kg)?"

# Regex pro text diagnózy/závěru:
REGEX_DIAGNOSIS_TEXT = r"(?:Diagnóza|Dg\.|Závěr)\s*:\s*(.+?)(?:\s*\n\s*|\Z|Poznámka:|Medikace:|Doporučení:|Terapie:|Výška:|Hmotnost:|Kontrola:|Prognóza:)"

# Regex pro formáty YYYY-MM-DD, YYYY.MM.DD, YYYY/MM/DD (použito v datetime_utils)
REGEX_YYYY_MM_DD = r"(\d{4})[\.\/\-](\d{1,2})[\.\/\-](\d{1,2})"
