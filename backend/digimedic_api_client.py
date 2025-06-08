# backend/digimedic_api_client.py
import json
import requests # Pro budoucí reálná HTTP volání

# Simulované API endpointy a konfigurace
SIMULATED_API_BASE_URL = "https://api.digimedic.example.cz/fhir"
SIMULATED_API_TOKEN = "simulated_api_token_placeholder"

class DigiMedicAPIClient:
    """
    Klient pro (simulovanou) komunikaci s DigiMedic FHIR Backend API.
    """
    def __init__(self, api_base_url=None, auth_token=None):
        """
        Inicializace klienta.

        Args:
            api_base_url (str, optional): Základní URL FHIR API.
            auth_token (str, optional): Autentizační token.
        """
        self.base_url = api_base_url or SIMULATED_API_BASE_URL
        self.auth_token = auth_token or SIMULATED_API_TOKEN
        self.headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/fhir+json",
            "Accept": "application/fhir+json"
        }
        print(f"DEBUG [API Client]: Inicializován s base_url: {self.base_url}, token: {'*' * len(self.auth_token) if self.auth_token else 'None'}")

    def send_fhir_resource(self, fhir_resource: dict) -> dict:
        """
        (Simulovaně) odešle jednotlivý FHIR zdroj na server.
        """
        resource_type = fhir_resource.get("resourceType", "NeznámýResource")
        resource_id = fhir_resource.get("id", "bezID")

        print(f"INFO [API Client]: SIMULACE ODESLÁNÍ FHIR ZDROJE ({resource_type}/{resource_id}) na {self.base_url}/{resource_type}")
        print(f"INFO [API Client]: Data:\n{json.dumps(fhir_resource, indent=2, ensure_ascii=False)}")

        simulated_response = {
            "status": "success",
            "message": f"Zdroj {resource_type}/{resource_id} byl úspěšně (simulovaně) odeslán.",
            "resource_id_on_server": resource_id,
            "operation_outcome": {
                "resourceType": "OperationOutcome",
                "issue": [{
                    "severity": "information",
                    "code": "informational",
                    "diagnostics": f"Successfully created resource {resource_type}/{resource_id}."
                }]
            }
        }
        print(f"INFO [API Client]: Simulovaná odpověď:\n{json.dumps(simulated_response, indent=2, ensure_ascii=False)}")
        return simulated_response

    def send_fhir_bundle(self, fhir_bundle: dict) -> dict:
        """
        (Simulovaně) odešle FHIR Bundle na server.
        """
        bundle_id = fhir_bundle.get("id", "bezID")
        bundle_type = fhir_bundle.get("type", "neznámýTyp")

        print(f"INFO [API Client]: SIMULACE ODESLÁNÍ FHIR BUNDLE (ID: {bundle_id}, Typ: {bundle_type}) na {self.base_url}")
        print(f"INFO [API Client]: Data Bundle (prvních pár záznamů):\n{json.dumps(fhir_bundle.get('entry', [])[:2], indent=2, ensure_ascii=False)}")

        simulated_response = {
            "status": "success",
            "message": f"Bundle {bundle_id} byl úspěšně (simulovaně) odeslán.",
            "operation_outcome": {
                "resourceType": "OperationOutcome",
                "issue": [{
                    "severity": "information",
                    "code": "informational",
                    "diagnostics": f"Successfully processed Bundle {bundle_id}."
                }]
            }
        }
        print(f"INFO [API Client]: Simulovaná odpověď:\n{json.dumps(simulated_response, indent=2, ensure_ascii=False)}")
        return simulated_response

if __name__ == '__main__':
    print("--- Test DigiMedicAPIClient ---")
    client = DigiMedicAPIClient()

    sample_patient = {
        "resourceType": "Patient",
        "id": "pacient-karel-novotny-19750320",
        "name": [{"family": "Novotný", "given": ["Karel"]}],
        "birthDate": "1975-03-20"
    }

    sample_observation = {
        "resourceType": "Observation",
        "id": "obs-pacient-karel-novotny-19750320-bp1",
        "status": "final",
        "code": {"text": "Krevní tlak"},
        "subject": {"reference": "Patient/pacient-karel-novotny-19750320"},
        "valueString": "130/85 mmHg"
    }

    print("\n--- Test odeslání jednotlivého zdroje (Patient) ---")
    response_patient = client.send_fhir_resource(sample_patient)

    print("\n--- Test odeslání jednotlivého zdroje (Observation) ---")
    response_observation = client.send_fhir_resource(sample_observation)

    sample_bundle = {
        "resourceType": "Bundle",
        "id": "bundle-karel-novotny-1",
        "type": "transaction",
        "entry": [
            {
                "fullUrl": "Patient/pacient-karel-novotny-19750320",
                "resource": sample_patient,
                "request": {
                    "method": "PUT",
                    "url": "Patient/pacient-karel-novotny-19750320"
                }
            },
            {
                "fullUrl": "Observation/obs-pacient-karel-novotny-19750320-bp1",
                "resource": sample_observation,
                "request": {
                    "method": "POST",
                    "url": "Observation"
                }
            }
        ]
    }
    print("\n--- Test odeslání Bundle ---")
    response_bundle = client.send_fhir_bundle(sample_bundle)
