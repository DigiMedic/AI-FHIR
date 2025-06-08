# backend/fhir_mapper.py
import re
import json
from datetime import datetime

# Základní regulární výrazy pro extrakci informací
# Tyto regexy jsou velmi jednoduché a budou potřebovat vylepšení pro reálné použití.
REGEX_PATIENT_NAME = r"Pacient:\s*([A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+(?:\s+[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+)+)"
REGEX_BIRTH_DATE = r"Datum narození:\s*(\d{1,2}\.\d{1,2}\.\d{4})"
REGEX_BLOOD_PRESSURE = r"Krevní tlak:\s*(\d{2,3}\/\d{2,3})\s*mmHg"

def parse_patient_data(text: str) -> dict:
    """
    Parsování základních informací o pacientovi z textu.

    Args:
        text (str): Extrahovaný text z dokumentu.

    Returns:
        dict: Slovník s daty pacienta (jmeno, datum_narozeni) nebo prázdný slovník.
    """
    patient_data = {}
    name_match = re.search(REGEX_PATIENT_NAME, text, re.IGNORECASE)
    if name_match:
        patient_data["jmeno"] = name_match.group(1).strip()

    birth_date_match = re.search(REGEX_BIRTH_DATE, text)
    if birth_date_match:
        try:
            # Převod data na FHIR formát (YYYY-MM-DD)
            day, month, year = map(int, birth_date_match.group(1).split('.'))
            patient_data["datum_narozeni"] = datetime(year, month, day).strftime('%Y-%m-%d')
        except ValueError:
            print(f"Chyba: Neplatný formát data narození: {birth_date_match.group(1)}")
            patient_data["datum_narozeni_raw"] = birth_date_match.group(1)


    print(f"DEBUG [FHIR Mapper]: Parsed patient data: {patient_data}")
    return patient_data

def create_fhir_patient_resource(patient_data: dict, patient_id: str = "pacient1") -> dict:
    """
    Vytvoření FHIR Patient resource ze slovníku dat.

    Args:
        patient_data (dict): Slovník s daty pacienta.
        patient_id (str): Interní ID pacienta pro FHIR resource.

    Returns:
        dict: FHIR Patient resource jako slovník.
    """
    if not patient_data.get("jmeno") or not patient_data.get("datum_narozeni"):
        print("DEBUG [FHIR Mapper]: Nedostatek dat pro vytvoření FHIR Patient resource.")
        return {}

    resource = {
        "resourceType": "Patient",
        "id": patient_id,
        "meta": {
            "profile": [
                "https://ncez.mzcr.cz/fhir/core/StructureDefinition/CzPatient"
            ]
        },
        "name": [{
            "use": "official",
            "family": patient_data["jmeno"],
        }],
        "birthDate": patient_data["datum_narozeni"]
    }
    name_parts = patient_data["jmeno"].split(" ", 1)
    if len(name_parts) == 2:
        resource["name"][0]["given"] = [name_parts[0]]
        resource["name"][0]["family"] = name_parts[1]
    else:
        resource["name"][0]["family"] = patient_data["jmeno"] # fallback if no space

    print(f"DEBUG [FHIR Mapper]: Vytvořen FHIR Patient resource: {json.dumps(resource, indent=2, ensure_ascii=False)}")
    return resource

def parse_observation_data(text: str) -> dict:
    """
    Parsování dat pro FHIR Observation resource (zatím jen krevní tlak).

    Args:
        text (str): Extrahovaný text z dokumentu.

    Returns:
        dict: Slovník s daty pro pozorování nebo prázdný slovník.
    """
    observation_data = {}
    bp_match = re.search(REGEX_BLOOD_PRESSURE, text, re.IGNORECASE)
    if bp_match:
        observation_data["krevni_tlak_hodnota"] = bp_match.group(1)
        observation_data["cas_mereni"] = datetime.now().isoformat()

    print(f"DEBUG [FHIR Mapper]: Parsed observation data: {observation_data}")
    return observation_data

def create_fhir_observation_resource(observation_data: dict, patient_reference_id: str, observation_id: str = "pozorovani1") -> dict:
    """
    Vytvoření FHIR Observation resource pro krevní tlak.

    Args:
        observation_data (dict): Slovník s daty o pozorování.
        patient_reference_id (str): Reference na pacienta (např. "Patient/pacient1").
        observation_id (str): Interní ID pozorování.

    Returns:
        dict: FHIR Observation resource jako slovník.
    """
    if not observation_data.get("krevni_tlak_hodnota"):
        print("DEBUG [FHIR Mapper]: Nedostatek dat pro vytvoření FHIR Observation resource (krevní tlak).")
        return {}

    systolic, diastolic = observation_data["krevni_tlak_hodnota"].split('/')

    resource = {
        "resourceType": "Observation",
        "id": observation_id,
        "meta": {
            "profile": [
                "https://ncez.mzcr.cz/fhir/core/StructureDefinition/VitalSignsObservation"
            ]
        },
        "status": "final",
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "vital-signs",
                "display": "Vital Signs"
            }]
        }],
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "85354-9",
                "display": "Blood pressure panel with all children optional"
            }],
            "text": "Krevní tlak"
        },
        "subject": {
            "reference": patient_reference_id
        },
        "effectiveDateTime": observation_data.get("cas_mereni", datetime.now().isoformat()),
        "component": [
            {
                "code": {
                    "coding": [{"system": "http://loinc.org", "code": "8480-6", "display": "Systolic blood pressure"}],
                    "text": "Systolický krevní tlak"
                },
                "valueQuantity": {"value": int(systolic), "unit": "mmHg", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}
            },
            {
                "code": {
                    "coding": [{"system": "http://loinc.org", "code": "8462-4", "display": "Diastolic blood pressure"}],
                    "text": "Diastolický krevní tlak"
                },
                "valueQuantity": {"value": int(diastolic), "unit": "mmHg", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}
            }
        ]
    }
    print(f"DEBUG [FHIR Mapper]: Vytvořen FHIR Observation resource: {json.dumps(resource, indent=2, ensure_ascii=False)}")
    return resource


def map_text_to_fhir(text: str) -> list:
    """
    Hlavní funkce pro mapování extrahovaného textu na seznam FHIR zdrojů.

    Args:
        text (str): Extrahovaný text.

    Returns:
        list: Seznam FHIR zdrojů (jako slovníky).
    """
    fhir_resources = []

    patient_data_extracted = parse_patient_data(text)
    if patient_data_extracted.get("jmeno") and patient_data_extracted.get("datum_narozeni"): # Přidána kontrola jména i data narození
        patient_id_suffix = "".join(filter(str.isalnum, patient_data_extracted.get("jmeno", "neznámý"))).lower()
        birth_date_suffix = patient_data_extracted.get("datum_narozeni", "").replace("-","")
        patient_fhir_id = f"pac-{patient_id_suffix[:10]}-{birth_date_suffix}"

        patient_resource = create_fhir_patient_resource(patient_data_extracted, patient_id=patient_fhir_id)
        if patient_resource:
            fhir_resources.append(patient_resource)

            observation_data_extracted = parse_observation_data(text)
            if observation_data_extracted.get("krevni_tlak_hodnota"):
                observation_fhir_id = f"obs-{patient_fhir_id}-bp1"
                observation_resource = create_fhir_observation_resource(
                    observation_data_extracted,
                    patient_reference_id=f"Patient/{patient_resource['id']}",
                    observation_id=observation_fhir_id
                )
                if observation_resource:
                    fhir_resources.append(observation_resource)

    if not fhir_resources:
        print("DEBUG [FHIR Mapper]: Nebyly vytvořeny žádné FHIR zdroje z daného textu.")

    return fhir_resources


if __name__ == '__main__':
    sample_extracted_text = """
    Toto je nějaký úvodní text.
    Pacient: Karel Novotný, Datum narození: 20.3.1975.
    Další informace o pacientovi.
    Krevní tlak: 130/85 mmHg.
    Závěr vyšetření.
    """
    print(f"Vstupní text pro FHIR mapování:\n{sample_extracted_text}\n")

    fhir_result_list = map_text_to_fhir(sample_extracted_text)

    if fhir_result_list:
        print("\n--- Výsledné FHIR zdroje (JSON Bundle) ---")
        bundle_resource = {
            "resourceType": "Bundle",
            "id": "bundle-example",
            "type": "collection",
            "entry": []
        }
        for res in fhir_result_list:
            bundle_resource["entry"].append({
                "fullUrl": f"{res['resourceType']}/{res['id']}", # Používáme f-string správně
                "resource": res
            })

        print(json.dumps(bundle_resource, indent=2, ensure_ascii=False))
    else:
        print("Nebyly vygenerovány žádné FHIR zdroje.")

    print("\n--- Test s textem bez relevantních dat ---")
    empty_text = "Dnes je hezky."
    print(f"Vstupní text:\n{empty_text}\n")
    empty_bundle_list = map_text_to_fhir(empty_text)
    if not empty_bundle_list: # Kontrolujeme, zda je list prázdný
        print("Správně nebyly vygenerovány žádné FHIR zdroje.")
