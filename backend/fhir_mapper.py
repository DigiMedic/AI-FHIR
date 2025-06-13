# backend/fhir_mapper.py
import re
import json
from datetime import datetime
import uuid

# --- Regulární výrazy ---
REGEX_PATIENT_NAME = r"Pacient(?:ka)?:\s*([A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+(?:-[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+)?(?:\s+[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+(?:-[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+)?)+)"
REGEX_BIRTH_DATE = r"(?:Datum narození|Nar\.|Narozena):\s*(\d{1,2}[\.\/\s]+\d{1,2}[\.\/\s]+\d{4})"
REGEX_BLOOD_PRESSURE = r"Krevní tlak\s*(?:TK)?:\s*(\d{2,3}\s*\/\s*\d{2,3})\s*(?:mmHg)?"
REGEX_DIAGNOSIS_TEXT = r"(?:Diagnóza|Dg\.|Závěr)\s*:\s*(.+?)(?:

|\Z|Poznámka:|Medikace:|Doporučení:)"

# --- Helper funkce pro parsování ---
def parse_date_to_fhir_format(date_str: str) -> str | None:
    """
    Parsování data z různých formátů na FHIR formát (YYYY-MM-DD).
    """
    if not date_str:
        return None
    cleaned_date_str = re.sub(r'[\/\s]+', '.', date_str)
    parts = cleaned_date_str.split('.')
    try:
        day = int(parts[0])
        month = int(parts[1])
        year = int(parts[2])
        if not (1880 <= year <= datetime.now().year + 1):
             print(f"Varování: Neobvyklý rok v datu narození: {year}")
        return datetime(year, month, day).strftime('%Y-%m-%d')
    except (ValueError, IndexError):
        print(f"Chyba: Neplatný formát data: {date_str}")
        return None

def generate_fhir_id() -> str:
    """Generuje unikátní FHIR ID."""
    return str(uuid.uuid4())

# --- Funkce pro parsování specifických dat ---
def parse_patient_data(text: str) -> dict:
    patient_data = {}
    name_match = re.search(REGEX_PATIENT_NAME, text, re.IGNORECASE)
    if name_match:
        patient_data["full_name"] = name_match.group(1).strip()

    birth_date_match = re.search(REGEX_BIRTH_DATE, text, re.IGNORECASE)
    if birth_date_match:
        raw_date = birth_date_match.group(1).strip()
        patient_data["birth_date_fhir"] = parse_date_to_fhir_format(raw_date)
        if not patient_data["birth_date_fhir"]:
            patient_data["birth_date_raw"] = raw_date

    print(f"DEBUG [FHIR Mapper]: Parsed patient data: {patient_data}")
    return patient_data

def parse_observation_data(text: str) -> dict:
    observation_data = {}
    bp_match = re.search(REGEX_BLOOD_PRESSURE, text, re.IGNORECASE)
    if bp_match:
        observation_data["blood_pressure_value"] = bp_match.group(1).replace(" ", "")
        observation_data["measurement_time_fhir"] = datetime.now().isoformat()

    print(f"DEBUG [FHIR Mapper]: Parsed observation data: {observation_data}")
    return observation_data

def parse_condition_data(text: str) -> dict:
    condition_data = {}
    diagnosis_match = re.search(REGEX_DIAGNOSIS_TEXT, text, re.IGNORECASE | re.DOTALL)
    if diagnosis_match:
        condition_data["diagnosis_text"] = diagnosis_match.group(1).strip()
        condition_data["diagnosis_text"] = re.sub(r'[\.,]$', '', condition_data["diagnosis_text"])
        condition_data["onset_date_time_fhir"] = datetime.now().isoformat()

    print(f"DEBUG [FHIR Mapper]: Parsed condition data: {condition_data}")
    return condition_data

# --- Funkce pro vytváření FHIR zdrojů ---
def create_fhir_patient_resource(patient_data: dict) -> dict | None:
    if not patient_data.get("full_name") or not patient_data.get("birth_date_fhir"):
        print("DEBUG [FHIR Mapper]: Nedostatek dat pro vytvoření FHIR Patient resource.")
        return None

    resource_id = generate_fhir_id()
    resource = {
        "resourceType": "Patient",
        "id": resource_id,
        "meta": {
            "profile": ["https://ncez.mzcr.cz/fhir/core/StructureDefinition/CzPatient"]
        },
        "name": [{
            "use": "official",
            "text": patient_data["full_name"]
        }],
        "birthDate": patient_data["birth_date_fhir"]
    }

    all_name_parts = patient_data["full_name"].split()
    if len(all_name_parts) > 1:
        resource["name"][0]["given"] = all_name_parts[:-1]
        resource["name"][0]["family"] = all_name_parts[-1]
    elif len(all_name_parts) == 1:
        resource["name"][0]["family"] = all_name_parts[0]

    print(f"DEBUG [FHIR Mapper]: Vytvořen FHIR Patient resource: {resource_id}")
    return resource

def create_fhir_observation_bp_resource(observation_data: dict, patient_reference_id: str) -> dict | None:
    if not observation_data.get("blood_pressure_value"):
        print("DEBUG [FHIR Mapper]: Nedostatek dat pro vytvoření FHIR Observation (BP).")
        return None

    try:
        systolic, diastolic = map(int, observation_data["blood_pressure_value"].split('/'))
    except ValueError:
        print(f"CHYBA: Neplatný formát krevního tlaku: {observation_data['blood_pressure_value']}")
        return None

    resource_id = generate_fhir_id()
    resource = {
        "resourceType": "Observation",
        "id": resource_id,
        "meta": {
            "profile": ["https://ncez.mzcr.cz/fhir/core/StructureDefinition/VitalSignsObservation"]
        },
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs", "display": "Vital Signs"}]}],
        "code": {"coding": [{"system": "http://loinc.org", "code": "85354-9", "display": "Blood pressure panel with all children optional"}], "text": "Krevní tlak"},
        "subject": {"reference": patient_reference_id},
        "effectiveDateTime": observation_data.get("measurement_time_fhir", datetime.now().isoformat()),
        "component": [
            {"code": {"coding": [{"system": "http://loinc.org", "code": "8480-6", "display": "Systolic blood pressure"}], "text": "Systolický krevní tlak"}, "valueQuantity": {"value": systolic, "unit": "mmHg", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}},
            {"code": {"coding": [{"system": "http://loinc.org", "code": "8462-4", "display": "Diastolic blood pressure"}], "text": "Diastolický krevní tlak"}, "valueQuantity": {"value": diastolic, "unit": "mmHg", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}}
        ]
    }
    print(f"DEBUG [FHIR Mapper]: Vytvořen FHIR Observation (BP) resource: {resource_id}")
    return resource

def create_fhir_condition_resource(condition_data: dict, patient_reference_id: str) -> dict | None:
    if not condition_data.get("diagnosis_text"):
        print("DEBUG [FHIR Mapper]: Nedostatek dat pro vytvoření FHIR Condition.")
        return None

    resource_id = generate_fhir_id()
    resource = {
        "resourceType": "Condition",
        "id": resource_id,
        "meta": {
            "profile": ["https://ncez.mzcr.cz/fhir/core/StructureDefinition/CzCondition"]
        },
        "clinicalStatus": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                "code": "active",
                "display": "Active"
            }]
        },
        "verificationStatus": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                "code": "confirmed",
                "display": "Confirmed"
            }]
        },
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/condition-category",
                "code": "encounter-diagnosis",
                "display": "Encounter Diagnosis"
            }]
        }],
        "code": {
            "text": condition_data["diagnosis_text"]
        },
        "subject": {"reference": patient_reference_id},
        "recordedDate": condition_data.get("onset_date_time_fhir", datetime.now().isoformat())
    }
    print(f"DEBUG [FHIR Mapper]: Vytvořen FHIR Condition resource: {resource_id}")
    return resource

# --- Hlavní mapovací funkce ---
def map_text_to_fhir(text: str) -> list:
    if not text or not text.strip():
        print("DEBUG [FHIR Mapper]: Vstupní text je prázdný, nebudou vytvořeny žádné FHIR zdroje.")
        return []

    fhir_resources = []
    patient_ref_id = None

    extracted_patient_data = parse_patient_data(text)
    if extracted_patient_data:
        patient_resource = create_fhir_patient_resource(extracted_patient_data)
        if patient_resource:
            fhir_resources.append(patient_resource)
            patient_ref_id = f"Patient/{patient_resource['id']}"

    if not patient_ref_id:
        print("INFO [FHIR Mapper]: Pacient nemohl být vytvořen, další navázané zdroje nebudou generovány.")
        return fhir_resources

    extracted_observation_data = parse_observation_data(text)
    if extracted_observation_data:
        observation_bp_resource = create_fhir_observation_bp_resource(extracted_observation_data, patient_ref_id)
        if observation_bp_resource:
            fhir_resources.append(observation_bp_resource)

    extracted_condition_data = parse_condition_data(text)
    if extracted_condition_data:
        condition_resource = create_fhir_condition_resource(extracted_condition_data, patient_ref_id)
        if condition_resource:
            fhir_resources.append(condition_resource)

    if not fhir_resources:
        print("DEBUG [FHIR Mapper]: Nebyly vytvořeny žádné FHIR zdroje z daného textu.")

    return fhir_resources

# --- Příklad použití pro testování ---
if __name__ == '__main__':
    sample_text_1 = """
    Pacient: MUDr. Jana Nováková, CSc.
    Datum narození: 15.05.1980
    Bydliště: Někde 123, Město
    ---
    Pacient: Karel Novotný
    Nar.: 20 / 3 / 1975
    Kontakt: 123456789
    ---
    Subjektivní potíže: Bolest hlavy.
    Objektivní nález:
    Krevní tlak: 135 / 88 mmHg
    Pulz: 70/min pravidelný
    Teplota: 36.5 C
    ---
    Diagnóza: Hypertenze esenciální (primární) I10
    Medikace: Prestarium Neo 5 mg 1-0-0
    Doporučení: Kontrola za 3 měsíce.
    """

    sample_text_2 = """
    Zpráva o vyšetření
    Pacientka: Eva Svobodová-Kučerová
    Narozena: 1. 1. 1955
    ---
    TK: 150/90. Jinak bez výrazných potíží.
    Závěr: Lehká arteriální hypertenze.
    Poznámka: Pacientka objednána na další kontrolu.
    """

    sample_text_3 = "Dnes je venku hezky, žádná lékařská data zde nejsou."

    sample_text_4 = """
    Pacient: Petr Pavel
    Datum narození: 1.11.1961
    Dg. : Akutní bronchitida J20.9
    Krevní tlak : 120/80
    """

    test_texts = {
        "Komplexní zpráva": sample_text_1,
        "Jednodušší zpráva": sample_text_2,
        "Žádná data": sample_text_3,
        "Krátká zpráva": sample_text_4
    }

    for test_name, sample_text in test_texts.items():
        print(f"--- Testovací případ: {test_name} ---")
        print(f"Vstupní text:\n{sample_text}\n")

        fhir_result_list = map_text_to_fhir(sample_text)

        if fhir_result_list:
            print(f"--- Výsledné FHIR zdroje pro '{test_name}' (JSON Bundle) ---")
            bundle_resource = {
                "resourceType": "Bundle",
                "id": f"bundle-{generate_fhir_id()}",
                "type": "collection",
                "entry": []
            }
            for res in fhir_result_list:
                bundle_resource["entry"].append({
                    "fullUrl": f"{res['resourceType']}/{res['id']}",
                    "resource": res
                })
            print(json.dumps(bundle_resource, indent=2, ensure_ascii=False))
        else:
            print(f"Pro '{test_name}' nebyly vygenerovány žádné FHIR zdroje.")
