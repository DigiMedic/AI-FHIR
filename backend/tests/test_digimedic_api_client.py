import pytest
from unittest.mock import patch, MagicMock
import os
import json
import requests # Pro typování a pro requests.exceptions

from backend.digimedic_api_client import DigiMedicAPIClient

# --- Vzorová FHIR data ---
SAMPLE_FHIR_PATIENT_WITH_ID = {
    "resourceType": "Patient",
    "id": "patient123",
    "name": [{"given": ["Pavel"], "family": "Novák"}],
    "gender": "male"
}

SAMPLE_FHIR_PATIENT_NO_ID = { # Pro testování POST scénáře
    "resourceType": "Patient",
    "name": [{"given": ["Jana"], "family": "Nová"}],
    "gender": "female"
}

SAMPLE_FHIR_OBSERVATION = {
    "resourceType": "Observation",
    "id": "obs789",
    "status": "final",
    "code": {"text": "Výška"},
    "valueQuantity": {"value": 175, "unit": "cm"}
}

SAMPLE_FHIR_BUNDLE = {
    "resourceType": "Bundle",
    "type": "transaction",
    "entry": [
        {
            "resource": SAMPLE_FHIR_PATIENT_WITH_ID,
            "request": {"method": "PUT", "url": f"Patient/{SAMPLE_FHIR_PATIENT_WITH_ID['id']}"}
        },
        {
            "resource": SAMPLE_FHIR_OBSERVATION,
            "request": {"method": "PUT", "url": f"Observation/{SAMPLE_FHIR_OBSERVATION['id']}"}
        }
    ]
}

SIMULATED_SUCCESS_MSG = "Operace byla úspěšně simulována."

# --- Testy pro Simulovaný Režim ---

def test_simulated_mode_send_fhir_resource(capsys):
    client = DigiMedicAPIClient(simulate=True)
    resource_to_send = SAMPLE_FHIR_PATIENT_WITH_ID.copy()

    response = client.send_fhir_resource(resource_to_send)

    assert response["status"] == "success"
    assert SIMULATED_SUCCESS_MSG in response["message"]
    assert response["resource_id"] == resource_to_send.get("id")
    assert response["resource_type"] == resource_to_send.get("resourceType")

    captured = capsys.readouterr()
    assert "[SIMULACE]" in captured.out
    assert f"Odesílání FHIR zdroje typu Patient s ID patient123" in captured.out
    assert json.dumps(resource_to_send, indent=2, ensure_ascii=False) in captured.out

def test_simulated_mode_send_fhir_bundle(capsys):
    client = DigiMedicAPIClient(simulate=True) # Výchozí je simulate=True
    bundle_to_send = SAMPLE_FHIR_BUNDLE.copy()

    response = client.send_fhir_bundle(bundle_to_send)

    assert response["status"] == "success"
    assert SIMULATED_SUCCESS_MSG in response["message"]
    assert response.get("bundle_id") == bundle_to_send.get("id", "nebylo zadáno") # Bundle nemusí mít ID

    captured = capsys.readouterr()
    assert "[SIMULACE]" in captured.out
    assert f"Odesílání FHIR Bundle (ID: {bundle_to_send.get('id', 'nebylo zadáno')})" in captured.out
    assert json.dumps(bundle_to_send, indent=2, ensure_ascii=False) in captured.out

# --- Testy pro Reálný Režim (s mockovanými requests) ---

@patch('backend.digimedic_api_client.requests')
def test_real_mode_send_resource_put_success(mock_requests):
    client = DigiMedicAPIClient(api_base_url="https://fakeapi.com", auth_token="fake_token", simulate=False)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": "patient123", "status": "updated"}
    mock_requests.put.return_value = mock_response

    resource_to_send = SAMPLE_FHIR_PATIENT_WITH_ID.copy()
    response = client.send_fhir_resource(resource_to_send)

    expected_url = f"https://fakeapi.com/Patient/{resource_to_send['id']}"
    mock_requests.put.assert_called_once_with(
        expected_url,
        json=resource_to_send,
        headers={"Authorization": "Bearer fake_token", "Content-Type": "application/fhir+json"}
    )
    assert response == {"id": "patient123", "status": "updated"}

@patch('backend.digimedic_api_client.requests')
def test_real_mode_send_resource_post_success(mock_requests):
    """Testuje odeslání nového resource (bez ID), očekává se POST a status 201."""
    client = DigiMedicAPIClient(api_base_url="https://fakeapi.com", auth_token="fake_token", simulate=False)

    mock_response = MagicMock()
    mock_response.status_code = 201 # Created
    mock_response.json.return_value = {"id": "newpatient456", "_versionId": "1"}
    mock_requests.post.return_value = mock_response

    resource_to_send = SAMPLE_FHIR_PATIENT_NO_ID.copy()
    response = client.send_fhir_resource(resource_to_send) # send_fhir_resource by mělo použít POST

    expected_url = f"https://fakeapi.com/Patient" # POST na typ zdroje
    mock_requests.post.assert_called_once_with(
        expected_url,
        json=resource_to_send,
        headers={"Authorization": "Bearer fake_token", "Content-Type": "application/fhir+json"}
    )
    assert response == {"id": "newpatient456", "_versionId": "1"}


@patch('backend.digimedic_api_client.requests')
def test_real_mode_send_bundle_success(mock_requests):
    client = DigiMedicAPIClient(api_base_url="https://fakeapi.com", auth_token="fake_token", simulate=False)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"resourceType": "Bundle", "type": "transaction-response", "entry": []}
    mock_requests.post.return_value = mock_response

    bundle_to_send = SAMPLE_FHIR_BUNDLE.copy()
    response = client.send_fhir_bundle(bundle_to_send)

    expected_url = "https://fakeapi.com/" # Bundle se posílá na base URL
    mock_requests.post.assert_called_once_with(
        expected_url,
        json=bundle_to_send,
        headers={"Authorization": "Bearer fake_token", "Content-Type": "application/fhir+json"}
    )
    assert response == {"resourceType": "Bundle", "type": "transaction-response", "entry": []}

@patch('backend.digimedic_api_client.requests')
def test_real_mode_send_resource_success_204_no_content(mock_requests):
    client = DigiMedicAPIClient(api_base_url="https://fakeapi.com", auth_token="fake_token", simulate=False)

    mock_response = MagicMock()
    mock_response.status_code = 204
    # .json() by nemělo být voláno, pokud je status 204
    # mock_response.json.side_effect = json.JSONDecodeError("msg", "doc", 0) # Simulace chyby, pokud by se volalo

    mock_requests.put.return_value = mock_response

    resource_to_send = SAMPLE_FHIR_PATIENT_WITH_ID.copy()
    response = client.send_fhir_resource(resource_to_send)

    assert response is None # Nebo nějaká standardizovaná odpověď pro 204
    mock_response.json.assert_not_called()


@patch('backend.digimedic_api_client.requests')
def test_real_mode_http_error_400_with_operation_outcome(mock_requests):
    client = DigiMedicAPIClient(api_base_url="https://fakeapi.com", auth_token="fake_token", simulate=False)
    operation_outcome = {
        "resourceType": "OperationOutcome",
        "issue": [{"severity": "error", "code": "processing", "diagnostics": "Chyba validace"}]
    }
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.json.return_value = operation_outcome
    mock_requests.put.return_value = mock_response

    response = client.send_fhir_resource(SAMPLE_FHIR_PATIENT_WITH_ID)
    assert response == operation_outcome

@patch('backend.digimedic_api_client.requests')
def test_real_mode_http_error_500_with_text_response(mock_requests):
    client = DigiMedicAPIClient(api_base_url="https://fakeapi.com", auth_token="fake_token", simulate=False)

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Interní chyba serveru."
    mock_response.json.side_effect = json.JSONDecodeError("msg", "doc", 0) # Nemůže parsovat JSON
    mock_requests.post.return_value = mock_response # Použijeme POST pro Bundle jako příklad

    response = client.send_fhir_bundle(SAMPLE_FHIR_BUNDLE)

    assert response["resourceType"] == "OperationOutcome"
    assert response["issue"][0]["severity"] == "error"
    assert "HTTP 500" in response["issue"][0]["diagnostics"]
    assert "Interní chyba serveru." in response["issue"][0]["diagnostics"]

@patch('backend.digimedic_api_client.requests')
def test_real_mode_requests_timeout(mock_requests):
    client = DigiMedicAPIClient(api_base_url="https://fakeapi.com", auth_token="fake_token", simulate=False)
    mock_requests.put.side_effect = requests.exceptions.Timeout("Časový limit vypršel")

    response = client.send_fhir_resource(SAMPLE_FHIR_PATIENT_WITH_ID)

    assert response["resourceType"] == "OperationOutcome"
    assert response["issue"][0]["severity"] == "error"
    assert "Časový limit" in response["issue"][0]["diagnostics"]
    assert "Timeout" in response["issue"][0]["diagnostics"]

@patch('backend.digimedic_api_client.requests')
def test_real_mode_requests_connection_error(mock_requests):
    client = DigiMedicAPIClient(api_base_url="https://fakeapi.com", auth_token="fake_token", simulate=False)
    mock_requests.post.side_effect = requests.exceptions.RequestException("Chyba připojení") # Obecná chyba

    response = client.send_fhir_bundle(SAMPLE_FHIR_BUNDLE)

    assert response["resourceType"] == "OperationOutcome"
    assert response["issue"][0]["severity"] == "error"
    assert "Chyba při komunikaci s API" in response["issue"][0]["diagnostics"]
    assert "Chyba připojení" in response["issue"][0]["diagnostics"]


# --- Testy pro Konfiguraci Klienta ---

def test_config_from_constructor_args():
    client = DigiMedicAPIClient(api_base_url="http://konstruktor.url", auth_token="konstruktor_token", simulate=False)
    assert client.base_url == "http://konstruktor.url"
    assert client.auth_token == "konstruktor_token"
    assert client.simulate is False

@patch.dict(os.environ, {
    "DIGIMEDIC_API_BASE_URL": "http://env.url",
    "DIGIMEDIC_API_TOKEN": "env_token"
})
def test_config_from_env_vars():
    # Musíme zajistit, že klient je inicializován *po* mockování env proměnných
    client = DigiMedicAPIClient(simulate=False)
    assert client.base_url == "http://env.url"
    assert client.auth_token == "env_token"

@patch.dict(os.environ, {
    "DIGIMEDIC_API_BASE_URL": "http://env.url",
    "DIGIMEDIC_API_TOKEN": "env_token"
})
def test_config_constructor_overrides_env():
    client = DigiMedicAPIClient(api_base_url="http://override.url", auth_token="override_token", simulate=False)
    assert client.base_url == "http://override.url"
    assert client.auth_token == "override_token"

@patch.dict(os.environ, clear=True) # Zajistíme, že env proměnné jsou prázdné
def test_config_real_mode_fallback_to_simulated_values_with_warning(capsys):
    # Odstranění proměnných, pokud by byly nastaveny globálně v testovacím prostředí
    if "DIGIMEDIC_API_BASE_URL" in os.environ:
        del os.environ["DIGIMEDIC_API_BASE_URL"]
    if "DIGIMEDIC_API_TOKEN" in os.environ:
        del os.environ["DIGIMEDIC_API_TOKEN"]

    client = DigiMedicAPIClient(simulate=False) # Žádné argumenty, žádné env proměnné

    # Očekáváme, že se použijí výchozí (simulované) hodnoty, protože jsme v reálném režimu, ale bez konfigurace
    # V implementaci DigiMedicAPIClient jsou výchozí hodnoty nastaveny na simulované/prázdné
    # a pokud je simulate=False a nejsou poskytnuty, mělo by dojít k varování.
    # Aktuální DigiMedicAPIClient má defaultní hodnoty pro base_url a auth_token
    # které jsou "https://simulated.digimedic.cz/fhir" a "SIMULATED_TOKEN"
    # Tyto se použijí, pokud nejsou přepsány.

    assert client.base_url == "https://simulated.digimedic.cz/fhir" # Nebo jaké jsou výchozí hodnoty
    assert client.auth_token == "SIMULATED_TOKEN"

    captured = capsys.readouterr()
    assert "VAROVÁNÍ: API Base URL není nakonfigurován" in captured.out
    assert "VAROVÁNÍ: API Auth Token není nakonfigurován" in captured.out
    assert "Klient DigiMedicAPIClient je v REÁLNÉM režimu, ale chybí konfigurace URL nebo tokenu." in captured.out

```
