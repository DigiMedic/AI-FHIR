# backend/digimedic_api_client.py
import json
import os
import requests # Pro budoucí reálná HTTP volání
import logging

logger = logging.getLogger(__name__)

# Simulované API endpointy a konfigurace
SIMULATED_API_BASE_URL = "https://api.digimedic.example.cz/fhir"
SIMULATED_API_TOKEN = "simulated_api_token_placeholder"

class DigiMedicAPIClient:
    """
    Klient pro (simulovanou) komunikaci s DigiMedic FHIR Backend API.
    """
    def __init__(self, api_base_url: str = None, auth_token: str = None, simulate: bool = True):
        """
        Inicializace klienta.

        Args:
            api_base_url (str, optional): Základní URL FHIR API.
            auth_token (str, optional): Autentizační token.
            simulate (bool, optional): Pokud True (výchozí), klient bude pouze simulovat
                                       odesílání dat. Pokud False, pokusí se o reálná
                                       HTTP volání.
        """
        self.simulate = simulate
        effective_base_url = None
        effective_auth_token = None
        source_info = ""

        if not self.simulate:
            env_base_url = os.environ.get("DIGIMEDIC_API_BASE_URL")
            env_auth_token = os.environ.get("DIGIMEDIC_API_TOKEN")

            if api_base_url and auth_token:
                effective_base_url = api_base_url
                effective_auth_token = auth_token
                source_info = "z argumentů funkce"
            elif env_base_url and env_auth_token:
                effective_base_url = env_base_url
                effective_auth_token = env_auth_token
                source_info = "z proměnných prostředí (DIGIMEDIC_API_BASE_URL, DIGIMEDIC_API_TOKEN)"
            else:
                logger.warning("[API Client]: Reálný režim je aktivní, ale chybí konfigurace API (URL nebo token) jak v argumentech, tak v proměnných prostředí. Používají se simulované hodnoty jako fallback.")
                effective_base_url = api_base_url or SIMULATED_API_BASE_URL
                effective_auth_token = auth_token or SIMULATED_API_TOKEN
                source_info = "z simulovaných fallback hodnot (konfigurace pro reálný režim chybí!)"
        else: # Simulovaný režim
            effective_base_url = api_base_url or SIMULATED_API_BASE_URL
            effective_auth_token = auth_token or SIMULATED_API_TOKEN
            source_info = "z argumentů funkce (simulace) nebo defaultních simulovaných hodnot"
            if not api_base_url and not auth_token:
                 source_info = "z defaultních simulovaných hodnot"
            elif api_base_url and auth_token:
                 source_info = "z argumentů funkce (simulace)"


        self.base_url = effective_base_url
        self.auth_token = effective_auth_token

        self.headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/fhir+json",
            "Accept": "application/fhir+json"
        }

        token_display = f"{'*' * (len(self.auth_token) - 3)}{self.auth_token[-3:]}" if self.auth_token and len(self.auth_token) > 3 else ('Token přítomen' if self.auth_token else 'Token nepřítomen')
        logger.info(f"[API Client]: Klient inicializován. Režim: {'Simulovaný' if self.simulate else 'Reálný'}.")
        logger.info(f"[API Client]: API Base URL: {self.base_url} ({source_info}).")
        logger.info(f"[API Client]: Auth Token: {token_display}.")


    def send_fhir_resource(self, fhir_resource: dict) -> dict:
        """
        Odešle jednotlivý FHIR zdroj na server.
        Pokud je klient v simulačním režimu, odeslání pouze simuluje.
        """
        if self.simulate:
            resource_type = fhir_resource.get("resourceType", "NeznámýResource")
            resource_id = fhir_resource.get("id", "bezID")

            logger.info(f"[API Client]: SIMULACE ODESLÁNÍ FHIR ZDROJE ({resource_type}/{resource_id}) na {self.base_url}/{resource_type}")
            logger.info(f"[API Client]: Data:\n{json.dumps(fhir_resource, indent=2, ensure_ascii=False)}")

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
            logger.info(f"[API Client]: Simulovaná odpověď:\n{json.dumps(simulated_response, indent=2, ensure_ascii=False)}")
            return simulated_response
        else:
            resource_type = fhir_resource.get("resourceType")
            if not resource_type:
                logger.error("[API Client]: Chybí 'resourceType' v odesílaném FHIR zdroji.")
                return {
                    "status": "error", "message": "Missing resourceType in FHIR resource",
                    "resourceType": "OperationOutcome", "issue": [{"severity": "error", "code": "invalid", "diagnostics": "FHIR resource must have a resourceType."}]
                }

            resource_id = fhir_resource.get("id")
            method = "POST"
            url = f"{self.base_url}/{resource_type}"

            if resource_id:
                method = "PUT"
                url = f"{self.base_url}/{resource_type}/{resource_id}"

            logger.info(f"[API Client]: REÁLNÉ ODESLÁNÍ ({method}) FHIR zdroje '{resource_type}{'/' + resource_id if resource_id else ''}' na {url}")
            # Logování části dat pro debug (např. bez citlivých polí, pokud by byla)
            # logger.debug(f"[API Client]: Data k odeslání (část):\n{json.dumps({k:v for k,v in fhir_resource.items() if k != 'photo'}, indent=2, ensure_ascii=False)}")


            try:
                if method == "POST":
                    response = requests.post(url, headers=self.headers, json=fhir_resource, timeout=15)
                else: # PUT
                    response = requests.put(url, headers=self.headers, json=fhir_resource, timeout=15)

                response.raise_for_status() # Vyvolá HTTPError pro chybové statusy 4xx/5xx

                # Logování úspěšné odpovědi
                try:
                    response_json = response.json()
                    logger.info(f"[API Client]: Úspěšná odpověď ({response.status_code}) z {method} {url}:\n{json.dumps(response_json, indent=2, ensure_ascii=False)}")
                    return response_json
                except json.JSONDecodeError:
                    logger.info(f"[API Client]: Úspěšná odpověď ({response.status_code}), ale tělo odpovědi není platný JSON. Text odpovědi: {response.text}")
                    # Vrátit OperationOutcome pro úspěch, ale s poznámkou o ne-JSON odpovědi, pokud je to relevantní
                    # Nebo prostě vrátit úspěch, pokud status kód je např. 200 OK bez těla nebo 204 No Content
                    if response.status_code == 204: # No Content
                         return {"status": "success", "message": f"Zdroj {resource_type}{'/' + resource_id if resource_id else ''} úspěšně zpracován (204 No Content)."}
                    return {"status": "success", "message": f"Zdroj {resource_type}{'/' + resource_id if resource_id else ''} úspěšně zpracován, ale odpověď nebyla JSON (status: {response.status_code})."}


            except requests.exceptions.Timeout:
                logger.error(f"[API Client]: HTTP volání ({method}) na {url} vypršelo.", exc_info=True)
                return {"resourceType": "OperationOutcome", "issue": [{"severity": "error", "code": "timeout", "diagnostics": f"Request ({method}) to {url} timed out after 15 seconds."}]}
            except requests.exceptions.HTTPError as e:
                logger.error(f"[API Client]: HTTP chyba ({method}) při volání na {url}: {e.response.status_code} {e.response.reason}", exc_info=True)
                try:
                    # Pokusit se vrátit OperationOutcome z těla odpovědi serveru
                    error_response_json = e.response.json()
                    logger.debug(f"[API Client]: Tělo chybové odpovědi (HTTPError):\n{json.dumps(error_response_json, indent=2, ensure_ascii=False)}")
                    # Pokud server vrátil OperationOutcome, můžeme ho přímo použít nebo zabalit
                    if error_response_json.get("resourceType") == "OperationOutcome":
                        return error_response_json
                    else: # Převod na OperationOutcome strukturu
                        return {"resourceType": "OperationOutcome", "issue": [{"severity": "error", "code": "processing", "diagnostics": f"HTTP error {e.response.status_code} {e.response.reason}. Server response: {json.dumps(error_response_json)}."}]}
                except json.JSONDecodeError:
                    # Tělo odpovědi nebylo JSON
                    logger.debug(f"[API Client]: Tělo chybové odpovědi (HTTPError) nebylo JSON: {e.response.text}")
                    return {"resourceType": "OperationOutcome", "issue": [{"severity": "error", "code": "exception", "diagnostics": f"HTTP error {e.response.status_code} {e.response.reason}. Response: {e.response.text}"}]}
            except requests.exceptions.RequestException as e:
                logger.error(f"[API Client]: Obecná chyba HTTP volání ({method}) na {url}: {e}", exc_info=True)
                return {"resourceType": "OperationOutcome", "issue": [{"severity": "error", "code": "exception", "diagnostics": f"General request exception for {method} {url}: {e}"}]}


    def send_fhir_bundle(self, fhir_bundle: dict) -> dict:
        """
        Odešle FHIR Bundle na server.
        Pokud je klient v simulačním režimu, odeslání pouze simuluje.
        """
        if self.simulate:
            bundle_id = fhir_bundle.get("id", "bezID")
            bundle_type = fhir_bundle.get("type", "neznámýTyp")

            logger.info(f"[API Client]: SIMULACE ODESLÁNÍ FHIR BUNDLE (ID: {bundle_id}, Typ: {bundle_type}) na {self.base_url}")
            logger.info(f"[API Client]: Data Bundle (prvních pár záznamů):\n{json.dumps(fhir_bundle.get('entry', [])[:2], indent=2, ensure_ascii=False)}")

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
            logger.info(f"[API Client]: Simulovaná odpověď:\n{json.dumps(simulated_response, indent=2, ensure_ascii=False)}")
            return simulated_response
        else:
            url = f"{self.base_url}" # Pro Bundle se obvykle posílá na kořen FHIR endpointu (bez /resourceType)
            bundle_id = fhir_bundle.get("id", "neznáméID")
            bundle_type = fhir_bundle.get("type", "neznámýTyp")

            logger.info(f"[API Client]: REÁLNÉ ODESLÁNÍ FHIR BUNDLE (ID: {bundle_id}, Typ: {bundle_type}) na {url}")
            # Logování jen části bundle pro přehlednost, např. počet záznamů
            num_entries = len(fhir_bundle.get("entry", []))
            logger.debug(f"[API Client]: Bundle obsahuje {num_entries} záznamů.")

            try:
                response = requests.post(url, headers=self.headers, json=fhir_bundle, timeout=30) # Delší timeout pro bundle
                response.raise_for_status()

                try:
                    response_json = response.json()
                    logger.info(f"[API Client]: Úspěšná odpověď ({response.status_code}) z POST {url} pro Bundle:\n{json.dumps(response_json, indent=2, ensure_ascii=False)}")
                    return response_json
                except json.JSONDecodeError:
                    logger.info(f"[API Client]: Úspěšná odpověď ({response.status_code}) pro Bundle, ale tělo odpovědi není platný JSON. Text odpovědi: {response.text}")
                    if response.status_code == 204: # No Content
                         return {"status": "success", "message": f"Bundle {bundle_id} úspěšně zpracován (204 No Content)."}
                    return {"status": "success", "message": f"Bundle {bundle_id} úspěšně zpracován, ale odpověď nebyla JSON (status: {response.status_code})."}

            except requests.exceptions.Timeout:
                logger.error(f"[API Client]: HTTP volání na {url} pro Bundle (ID: {bundle_id}) vypršelo.", exc_info=True)
                return {"resourceType": "OperationOutcome", "issue": [{"severity": "error", "code": "timeout", "diagnostics": f"Request to {url} for Bundle (ID: {bundle_id}) timed out after 30 seconds."}]}
            except requests.exceptions.HTTPError as e:
                logger.error(f"[API Client]: HTTP chyba při volání na {url} pro Bundle (ID: {bundle_id}): {e.response.status_code} {e.response.reason}", exc_info=True)
                try:
                    error_response_json = e.response.json()
                    logger.debug(f"[API Client]: Tělo chybové odpovědi (HTTPError) pro Bundle:\n{json.dumps(error_response_json, indent=2, ensure_ascii=False)}")
                    if error_response_json.get("resourceType") == "OperationOutcome":
                        return error_response_json
                    else:
                        return {"resourceType": "OperationOutcome", "issue": [{"severity": "error", "code": "processing", "diagnostics": f"HTTP error {e.response.status_code} {e.response.reason} for Bundle. Server response: {json.dumps(error_response_json)}."}]}
                except json.JSONDecodeError:
                    logger.debug(f"[API Client]: Tělo chybové odpovědi (HTTPError) pro Bundle nebylo JSON: {e.response.text}")
                    return {"resourceType": "OperationOutcome", "issue": [{"severity": "error", "code": "exception", "diagnostics": f"HTTP error {e.response.status_code} {e.response.reason} for Bundle. Response: {e.response.text}"}]}
            except requests.exceptions.RequestException as e:
                logger.error(f"[API Client]: Obecná chyba HTTP volání na {url} pro Bundle (ID: {bundle_id}): {e}", exc_info=True)
                return {"resourceType": "OperationOutcome", "issue": [{"severity": "error", "code": "exception", "diagnostics": f"General request exception for Bundle {url} (ID: {bundle_id}): {e}"}]}

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info("--- Test DigiMedicAPIClient ---")
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

    logger.info("\n--- Test odeslání jednotlivého zdroje (Patient) v SIMULOVANÉM režimu ---")
    response_patient = client_simulated.send_fhir_resource(sample_patient)

    logger.info("\n--- Test odeslání jednotlivého zdroje (Observation) v SIMULOVANÉM režimu ---")
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
    logger.info("\n--- Test odeslání Bundle v SIMULOVANÉM režimu ---")
    response_bundle = client_simulated.send_fhir_bundle(sample_bundle)

    # Příklad, jak by mohl být klient inicializován a použit pro reálné API volání.
    # Pro spuštění reálných testů:
    # 1. Nastavte proměnné prostředí:
    #    export DIGIMEDIC_API_BASE_URL="https://vase-realne-api.cz/fhir"
    #    export DIGIMEDIC_API_TOKEN="vas_realny_token"
    # 2. Spusťte skript. Následující blok se pokusí o reálná volání.
    logger.info("\n--- Testování DigiMedicAPIClient v REÁLNÉM režimu ---")
    logger.info("INFO: Pro reálné testy musí být nastaveny proměnné prostředí DIGIMEDIC_API_BASE_URL a DIGIMEDIC_API_TOKEN.")

    real_api_url_from_env = os.environ.get("DIGIMEDIC_API_BASE_URL")
    real_api_token_from_env = os.environ.get("DIGIMEDIC_API_TOKEN")

    if real_api_url_from_env and real_api_token_from_env:
        logger.info(f"Nalezeny proměnné prostředí: DIGIMEDIC_API_BASE_URL, DIGIMEDIC_API_TOKEN. Inicializuji klienta v reálném režimu.")
        client_real = DigiMedicAPIClient(simulate=False) # Načte URL a token z proměnných prostředí

        logger.info("\n--- Pokus o odeslání jednotlivého zdroje (Patient) v REÁLNÉM režimu ---")
        # Můžete si upravit `sample_patient` nebo vytvořit nový pro reálný test
        # Ujistěte se, že ID zdroje je unikátní nebo že server podporuje PUT pro aktualizaci
        real_patient_to_send = sample_patient.copy()
        # real_patient_to_send["id"] = "test-pacient-" + datetime.now().strftime("%Y%m%d%H%M%S") # Příklad unikátního ID

        response_real_patient = client_real.send_fhir_resource(real_patient_to_send)
        logger.info(f"Odpověď z reálného API (odeslání pacienta):\n{json.dumps(response_real_patient, indent=2, ensure_ascii=False)}")

        logger.info("\n--- Pokus o odeslání Bundle v REÁLNÉM režimu ---")
        # Můžete si upravit `sample_bundle` nebo vytvořit nový
        real_bundle_to_send = sample_bundle.copy()
        # real_bundle_to_send["id"] = "test-bundle-" + datetime.now().strftime("%Y%m%d%H%M%S")

        response_real_bundle = client_real.send_fhir_bundle(real_bundle_to_send)
        logger.info(f"Odpověď z reálného API (odeslání bundle):\n{json.dumps(response_real_bundle, indent=2, ensure_ascii=False)}")

        # Příklad s explicitně zadanými URL a tokenem (přepíše proměnné prostředí)
        # client_real_args = DigiMedicAPIClient(
        #     api_base_url="https://jine-realne-api.cz/fhir",
        #     auth_token="jiny_realny_token",
        #     simulate=False
        # )
        # logger.info("\n--- Pokus o odeslání s explicitními argumenty v REÁLNÉM režimu ---")
        # response_real_patient_args = client_real_args.send_fhir_resource(sample_patient)
        # logger.info(f"Odpověď (args): {json.dumps(response_real_patient_args, indent=2, ensure_ascii=False)}")

    else:
        logger.warning("Proměnné prostředí DIGIMEDIC_API_BASE_URL a/nebo DIGIMEDIC_API_TOKEN nejsou nastaveny.")
        logger.warning("Reálné testy budou přeskočeny. Klient bude inicializován s fallback hodnotami (pravděpodobně simulovanými).")
        client_real_fallback = DigiMedicAPIClient(simulate=False) # Ukázka fallbacku
        # Pokud byste chtěli vynutit chybu, pokud nejsou proměnné nastaveny:
        # raise ValueError("Pro reálné testy je nutné nastavit DIGIMEDIC_API_BASE_URL a DIGIMEDIC_API_TOKEN.")
        logger.info("\n--- Testování fallbacku při chybějících env proměnných (simulate=False) ---")
        # Toto volání použije simulované hodnoty, protože reálné nebyly nalezeny
        response_fallback_patient = client_real_fallback.send_fhir_resource(sample_patient)
        logger.info(f"Odpověď z fallback klienta (pacient):\n{json.dumps(response_fallback_patient, indent=2, ensure_ascii=False)}")

    logger.info("\n--- Konec testů DigiMedicAPIClient ---")
