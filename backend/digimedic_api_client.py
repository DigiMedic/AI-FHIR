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
    def __init__(self, api_base_url=None, auth_token=None, simulate: bool = True):
        """
        Inicializace klienta.

        Args:
            api_base_url (str, optional): Základní URL FHIR API.
            auth_token (str, optional): Autentizační token.
            simulate (bool, optional): Pokud True (výchozí), klient bude pouze simulovat
                                       odesílání dat. Pokud False, pokusí se o reálná
                                       HTTP volání (vyžaduje implementaci).
        """
        self.base_url = api_base_url or SIMULATED_API_BASE_URL
        self.auth_token = auth_token or SIMULATED_API_TOKEN
        self.simulate = simulate
        self.headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/fhir+json",
            "Accept": "application/fhir+json"
        }
        print(f"DEBUG [API Client]: Inicializován s base_url: {self.base_url}, token: {'*' * len(self.auth_token) if self.auth_token else 'None'}. Režim: {'Simulovaný' if self.simulate else 'Reálný'}")

    def send_fhir_resource(self, fhir_resource: dict) -> dict:
        """
        Odešle jednotlivý FHIR zdroj na server.
        Pokud je klient v simulačním režimu, odeslání pouze simuluje.
        """
        if self.simulate:
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
        else:
            # TODO: Implementovat reálné HTTP POST/PUT volání pro jednotlivý FHIR zdroj
            # resource_type = fhir_resource.get("resourceType", "NeznámýResource")
            # resource_id = fhir_resource.get("id", None) # Získat ID pro případné PUT
            # url = f"{self.base_url}/{resource_type}"
            # method = "POST" # Defaultně POST pro vytvoření nového zdroje
            # if resource_id: # Pokud zdroj má ID, zvážit PUT pro aktualizaci
            #     url = f"{self.base_url}/{resource_type}/{resource_id}"
            #     method = "PUT"

            # print(f"INFO [API Client]: REÁLNÉ ODESLÁNÍ ({method}) FHIR ZDROJE ({resource_type}/{resource_id or 'nový'}) na {url}")
            # print(f"INFO [API Client]: Data:\n{json.dumps(fhir_resource, indent=2, ensure_ascii=False)}")
            # try:
            #     if method == "POST":
            #         response = requests.post(url, headers=self.headers, json=fhir_resource, timeout=10)
            #     else: # PUT
            #         response = requests.put(url, headers=self.headers, json=fhir_resource, timeout=10)

            #     response.raise_for_status() # Vyvolá HTTPError pro chybové statusy 4xx/5xx
            #     print(f"INFO [API Client]: Reálná odpověď ({response.status_code}):\n{json.dumps(response.json(), indent=2, ensure_ascii=False)}")
            #     return response.json()
            # except requests.exceptions.Timeout:
            #     print(f"CHYBA [API Client]: HTTP volání na {url} vypršelo.")
            #     return {"status": "error", "message": "Request timed out", "resourceType": "OperationOutcome", "issue": [{"severity": "error", "code": "timeout", "diagnostics": f"Request to {url} timed out."}]}
            # except requests.exceptions.HTTPError as e:
            #     print(f"CHYBA [API Client]: HTTP chyba při volání na {url}: {e.response.status_code} {e.response.reason}")
            #     try:
            #         return e.response.json() # Pokusit se vrátit OperationOutcome z těla odpovědi
            #     except ValueError: # json.JSONDecodeError
            #         return {"status": "error", "message": f"HTTP error {e.response.status_code} with non-JSON response", "resourceType": "OperationOutcome", "issue": [{"severity": "error", "code": "exception", "diagnostics": f"HTTP error {e.response.status_code} {e.response.reason} when calling {url}. Response: {e.response.text}"}]}
            # except requests.exceptions.RequestException as e:
            #     print(f"CHYBA [API Client]: Obecná chyba HTTP volání na {url}: {e}")
            #     return {"status": "error", "message": str(e), "resourceType": "OperationOutcome", "issue": [{"severity": "error", "code": "exception", "diagnostics": f"General request exception when calling {url}: {e}"}]}

            print("INFO [API Client]: Reálné odeslání FHIR zdroje zatím není implementováno. Použijte simulovaný režim.")
            # Dočasně vrátit simulovanou chybovou odpověď, aby bylo jasné, že reálné volání neproběhlo
            return {
                "status": "error",
                "message": "Real API call not implemented",
                "resourceType": "OperationOutcome",
                "issue": [{
                    "severity": "error",
                    "code": "not-supported",
                    "diagnostics": "Real API call for send_fhir_resource is not implemented yet."
                }]
            }

    def send_fhir_bundle(self, fhir_bundle: dict) -> dict:
        """
        Odešle FHIR Bundle na server.
        Pokud je klient v simulačním režimu, odeslání pouze simuluje.
        """
        if self.simulate:
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
        else:
            # TODO: Implementovat reálné HTTP POST volání pro FHIR Bundle
            # url = f"{self.base_url}" # Pro Bundle se obvykle posílá na kořen FHIR endpointu
            # bundle_id = fhir_bundle.get("id", "bezID")
            # bundle_type = fhir_bundle.get("type", "neznámýTyp")

            # print(f"INFO [API Client]: REÁLNÉ ODESLÁNÍ FHIR BUNDLE (ID: {bundle_id}, Typ: {bundle_type}) na {url}")
            # print(f"INFO [API Client]: Data Bundle (prvních pár záznamů):\n{json.dumps(fhir_bundle.get('entry', [])[:2], indent=2, ensure_ascii=False)}")
            # try:
            #     response = requests.post(url, headers=self.headers, json=fhir_bundle, timeout=30) # Delší timeout pro bundle
            #     response.raise_for_status()
            #     print(f"INFO [API Client]: Reálná odpověď ({response.status_code}):\n{json.dumps(response.json(), indent=2, ensure_ascii=False)}")
            #     return response.json()
            # except requests.exceptions.Timeout:
            #     print(f"CHYBA [API Client]: HTTP volání na {url} pro Bundle vypršelo.")
            #     return {"status": "error", "message": "Request timed out for Bundle", "resourceType": "OperationOutcome", "issue": [{"severity": "error", "code": "timeout", "diagnostics": f"Request to {url} for Bundle {bundle_id} timed out."}]}
            # except requests.exceptions.HTTPError as e:
            #     print(f"CHYBA [API Client]: HTTP chyba při volání na {url} pro Bundle: {e.response.status_code} {e.response.reason}")
            #     try:
            #         return e.response.json()
            #     except ValueError:
            #         return {"status": "error", "message": f"HTTP error {e.response.status_code} with non-JSON response for Bundle", "resourceType": "OperationOutcome", "issue": [{"severity": "error", "code": "exception", "diagnostics": f"HTTP error {e.response.status_code} {e.response.reason} when calling {url} for Bundle {bundle_id}. Response: {e.response.text}"}]}
            # except requests.exceptions.RequestException as e:
            #     print(f"CHYBA [API Client]: Obecná chyba HTTP volání na {url} pro Bundle: {e}")
            #     return {"status": "error", "message": str(e), "resourceType": "OperationOutcome", "issue": [{"severity": "error", "code": "exception", "diagnostics": f"General request exception when calling {url} for Bundle {bundle_id}: {e}"}]}

            print("INFO [API Client]: Reálné odeslání FHIR Bundle zatím není implementováno. Použijte simulovaný režim.")
            return {
                "status": "error",
                "message": "Real API call not implemented",
                "resourceType": "OperationOutcome",
                "issue": [{
                    "severity": "error",
                    "code": "not-supported",
                    "diagnostics": "Real API call for send_fhir_bundle is not implemented yet."
                }]
            }

if __name__ == '__main__':
    print("--- Test DigiMedicAPIClient ---")
    client_simulated = DigiMedicAPIClient() # Výchozí je simulate=True

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
        "valueString": "130/85 mmHg" # V reálném FHIR by zde byla strukturovaná Quantity nebo component
    }

    print("\n--- Test odeslání jednotlivého zdroje (Patient) v SIMULOVANÉM režimu ---")
    response_patient = client_simulated.send_fhir_resource(sample_patient)

    print("\n--- Test odeslání jednotlivého zdroje (Observation) v SIMULOVANÉM režimu ---")
    response_observation = client_simulated.send_fhir_resource(sample_observation)

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
    print("\n--- Test odeslání Bundle v SIMULOVANÉM režimu ---")
    response_bundle = client_simulated.send_fhir_bundle(sample_bundle)

    # Příklad, jak by mohl být klient inicializován a použit pro reálné API volání (aktuálně neprovede nic)
    print("\n--- Ukázka inicializace a volání pro DigiMedicAPIClient v REÁLNÉM režimu (není implementováno) ---")
    client_real_example = DigiMedicAPIClient(
        api_base_url="https://skutecne.api.digimedic.cz/fhir", # Nahradit reálnou URL
        auth_token="skutecny_api_token_example", # Nahradit reálným tokenem
        simulate=False
    )

    # Tato volání by se pokusila o reálné HTTP requesty, pokud by simulate=False a kód byl implementován
    # V současném stavu (s TODO) vrátí chybovou zprávu "Real API call not implemented".
    if not client_real_example.simulate:
        print("\n--- Pokus o odeslání jednotlivého zdroje (Patient) v REÁLNÉM režimu ---")
        response_real_patient = client_real_example.send_fhir_resource(sample_patient)
        print(f"Odpověď z 'reálného' API (pacient): {json.dumps(response_real_patient, indent=2, ensure_ascii=False)}")

        print("\n--- Pokus o odeslání Bundle v REÁLNÉM režimu ---")
        response_real_bundle = client_real_example.send_fhir_bundle(sample_bundle)
        print(f"Odpověď z 'reálného' API (bundle): {json.dumps(response_real_bundle, indent=2, ensure_ascii=False)}")
    else:
        # Toto by se nemělo stát, pokud simulate=False
        print("INFO: Klient pro reálné API byl neočekávaně inicializován v simulovaném režimu.")

    # Test reálného klienta, který je ale stále v simulovaném režimu (protože simulate=False nebylo vynuceno výše)
    # nebo pokud by byl explicitně client_real_example inicializován s simulate=True
    if client_real_example.simulate: # Pokud by byl client_real_example přece jen v simulaci
         print("\n--- Test klienta `client_real_example` (který je v simulovaném režimu) ---")
         response_sim_patient_again = client_real_example.send_fhir_resource(sample_patient)
         print(f"Odpověď z `client_real_example` (pacient, simulace): {json.dumps(response_sim_patient_again, indent=2, ensure_ascii=False)}")
