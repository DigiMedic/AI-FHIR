import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, ANY
import os
import shutil
import json # Pro testování quality issues logování

# Přidání cesty k 'backend' adresáři, pokud testy běží z jiné lokace
# a 'backend' není v PYTHONPATH. Pro pytest běžící z rootu by to nemělo být nutné.
# import sys
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.main import app, TEMP_UPLOAD_DIR

# --- Testovací data ---
SAMPLE_PATIENT_RESOURCE = [{"resourceType": "Patient", "id": "patient1", "name": [{"text": "Test Patient"}]}]
SAMPLE_OBSERVATION_RESOURCE = [{"resourceType": "Observation", "id": "obs1", "status": "final"}]
SAMPLE_FHIR_RESOURCES = SAMPLE_PATIENT_RESOURCE + SAMPLE_OBSERVATION_RESOURCE

SAMPLE_QUALITY_ISSUES_EMPTY = []
SAMPLE_QUALITY_ISSUES_PRESENT = [{"level": "warning", "message": "Test quality issue", "field": "some_field"}]

MOCK_EXTRACTED_TEXT_TXT = "Toto je extrahovaný text z textového dokumentu."
MOCK_EXTRACTED_TEXT_IMG = "Toto je extrahovaný text z obrázkového dokumentu (OCR)."
MOCK_EXTRACTED_TEXT_FAIL = "[CHYBA OCR] Nepodařilo se extrahovat text."

# --- Fixtures ---

@pytest.fixture(scope="module")
def client():
    """
    Fixture pro TestClient FastAPI aplikace.
    Zajistí vytvoření a smazání TEMP_UPLOAD_DIR.
    """
    # Vytvoření dočasného adresáře pro nahrávání, pokud neexistuje
    # Tento adresář je definován v backend.main
    os.makedirs(TEMP_UPLOAD_DIR, exist_ok=True)

    with TestClient(app) as c:
        yield c

    # Úklid dočasného adresáře po všech testech v modulu
    if os.path.exists(TEMP_UPLOAD_DIR):
        # print(f"DEBUG: Cleaning up TEMP_UPLOAD_DIR: {TEMP_UPLOAD_DIR}")
        shutil.rmtree(TEMP_UPLOAD_DIR)
    # else:
        # print(f"DEBUG: TEMP_UPLOAD_DIR not found for cleanup: {TEMP_UPLOAD_DIR}")


# --- Testovací funkce ---

def test_process_txt_document_success(client: TestClient):
    """
    Testuje úspěšné zpracování textového souboru (.txt).
    """
    with patch('backend.main.extract_text_from_document', return_value=MOCK_EXTRACTED_TEXT_TXT) as mock_extract, \
         patch('backend.main.map_text_to_fhir', return_value={"fhir_resources": SAMPLE_FHIR_RESOURCES, "quality_issues": SAMPLE_QUALITY_ISSUES_EMPTY}) as mock_map, \
         patch('backend.main.DigiMedicAPIClient') as MockApiClient:

        # Nastavení mocku pro instanci DigiMedicAPIClient a její metodu
        mock_api_instance = MockApiClient.return_value
        mock_api_instance.send_fhir_bundle.return_value = {"status": "success", "message": "Bundle sent successfully", "details": "Simulated success"}

        file_content = b"Obsah textoveho souboru pro test."
        files = {"file": ("test_document.txt", file_content, "text/plain")}

        response = client.post("/api/process_document", files=files)

        assert response.status_code == 200
        assert response.json() == SAMPLE_FHIR_RESOURCES

        mock_extract.assert_called_once_with(MOCK_EXTRACTED_TEXT_TXT, input_type="text", use_nlp=True)
        mock_map.assert_called_once_with(MOCK_EXTRACTED_TEXT_TXT, original_text=MOCK_EXTRACTED_TEXT_TXT)

        MockApiClient.assert_called_once() # Ověření, že klient byl inicializován
        mock_api_instance.send_fhir_bundle.assert_called_once() # Ověření, že bundle byl odeslán
        # Můžeme dále ověřit obsah bundle, pokud je to potřeba, např. ANY z unittest.mock


def test_process_png_document_success(client: TestClient):
    """
    Testuje úspěšné zpracování obrázkového souboru (.png).
    """
    with patch('backend.main.extract_text_from_document', return_value=MOCK_EXTRACTED_TEXT_IMG) as mock_extract, \
         patch('backend.main.map_text_to_fhir', return_value={"fhir_resources": SAMPLE_PATIENT_RESOURCE, "quality_issues": SAMPLE_QUALITY_ISSUES_EMPTY}) as mock_map, \
         patch('backend.main.DigiMedicAPIClient') as MockApiClient:

        mock_api_instance = MockApiClient.return_value
        mock_api_instance.send_fhir_bundle.return_value = {"status": "success", "message": "Bundle sent"}

        # Vytvoření jednoduchého falešného PNG souboru (obsah nemusí být validní PNG)
        file_content = b"fake png content"
        files = {"file": ("test_image.png", file_content, "image/png")}

        response = client.post("/api/process_document", files=files)

        assert response.status_code == 200
        assert response.json() == SAMPLE_PATIENT_RESOURCE

        # Ověření, že extract_text_from_document bylo voláno s cestou k souboru a správným typem
        # ANY se použije pro temp_file_path, protože jeho přesný název neznáme
        mock_extract.assert_called_once_with(ANY, input_type="image_path")
        # Ověříme, že ANY je string (cesta k souboru)
        assert isinstance(mock_extract.call_args[0][0], str)

        mock_map.assert_called_once_with(MOCK_EXTRACTED_TEXT_IMG, original_text=MOCK_EXTRACTED_TEXT_IMG)
        MockApiClient.assert_called_once()
        mock_api_instance.send_fhir_bundle.assert_called_once()


def test_unsupported_file_type(client: TestClient):
    """
    Testuje nahrání nepodporovaného typu souboru.
    """
    file_content = b"some binary data"
    files = {"file": ("archive.zip", file_content, "application/zip")}

    response = client.post("/api/process_document", files=files)

    assert response.status_code == 400
    assert "Nepodporovaný typ souboru: application/zip" in response.json().get("detail", "")


def test_text_extraction_failure_ocr(client: TestClient):
    """
    Testuje případ, kdy extrakce textu (např. OCR) selže.
    """
    with patch('backend.main.extract_text_from_document', return_value=MOCK_EXTRACTED_TEXT_FAIL) as mock_extract, \
         patch('backend.main.map_text_to_fhir') as mock_map, \
         patch('backend.main.DigiMedicAPIClient.send_fhir_bundle') as mock_send_bundle:

        file_content = b"fake image data that will cause OCR error"
        files = {"file": ("ocr_fail_image.jpg", file_content, "image/jpeg")}

        response = client.post("/api/process_document", files=files)

        assert response.status_code == 200 # Endpoint by měl stále vrátit 200
        assert response.json() == [] # Očekáváme prázdný seznam, protože extrakce selhala

        mock_extract.assert_called_once_with(ANY, input_type="image_path")
        # map_text_to_fhir by nemělo být voláno, pokud extrakce vrátí chybu signalizující prázdný výstup
        # Aktuální implementace main.py: pokud je extracted_data_for_fhir "[CHYBA OCR]", vrátí []
        # a map_text_to_fhir se nevolá.
        mock_map.assert_not_called()
        mock_send_bundle.assert_not_called()


def test_map_text_to_fhir_returns_no_resources(client: TestClient):
    """
    Testuje případ, kdy map_text_to_fhir nevrátí žádné FHIR zdroje, ale může vrátit quality issues.
    """
    with patch('backend.main.extract_text_from_document', return_value=MOCK_EXTRACTED_TEXT_TXT) as mock_extract, \
         patch('backend.main.map_text_to_fhir', return_value={"fhir_resources": [], "quality_issues": SAMPLE_QUALITY_ISSUES_PRESENT}) as mock_map, \
         patch('backend.main.DigiMedicAPIClient.send_fhir_bundle') as mock_send_bundle:

        file_content = b"Text, ktery nevede k zadnym FHIR zdrojum."
        files = {"file": ("no_fhir.txt", file_content, "text/plain")}

        response = client.post("/api/process_document", files=files)

        assert response.status_code == 200
        assert response.json() == [] # Odpověď endpointu by měla být prázdný seznam zdrojů

        mock_extract.assert_called_once()
        mock_map.assert_called_once()
        mock_send_bundle.assert_not_called() # Neměly by se odesílat žádné zdroje


def test_process_document_with_quality_issues_logging(client: TestClient, capsys):
    """
    Testuje, zda jsou quality_issues správně zalogovány.
    """
    with patch('backend.main.extract_text_from_document', return_value=MOCK_EXTRACTED_TEXT_TXT) as mock_extract, \
         patch('backend.main.map_text_to_fhir', return_value={"fhir_resources": SAMPLE_PATIENT_RESOURCE, "quality_issues": SAMPLE_QUALITY_ISSUES_PRESENT}) as mock_map, \
         patch('backend.main.DigiMedicAPIClient') as MockApiClient:

        mock_api_instance = MockApiClient.return_value
        mock_api_instance.send_fhir_bundle.return_value = {"status": "success"}

        file_content = b"Text s quality issues."
        files = {"file": ("issues.txt", file_content, "text/plain")}

        client.post("/api/process_document", files=files)

        captured = capsys.readouterr()
        assert "INFO [Main]: Quality issues reported" in captured.out
        # Ověření, že JSON výpis obsahuje klíčové části našich mockovaných issues
        assert '"level": "warning"' in captured.out
        assert '"message": "Test quality issue"' in captured.out
        assert '"field": "some_field"' in captured.out


def test_digimedic_api_client_sends_bundle_failure(client: TestClient, capsys):
    """
    Testuje případ, kdy odeslání FHIR bundle přes DigiMedicAPIClient selže.
    Endpoint by měl stále vrátit FHIR zdroje a zalogovat chybu.
    """
    fhir_resources_to_return = SAMPLE_FHIR_RESOURCES

    with patch('backend.main.extract_text_from_document', return_value=MOCK_EXTRACTED_TEXT_TXT) as mock_extract, \
         patch('backend.main.map_text_to_fhir', return_value={"fhir_resources": fhir_resources_to_return, "quality_issues": []}) as mock_map, \
         patch('backend.main.DigiMedicAPIClient') as MockApiClient:

        mock_api_instance = MockApiClient.return_value
        mock_api_instance.send_fhir_bundle.side_effect = Exception("Simulated API Connection Error")

        file_content = b"Text pro API chybu."
        files = {"file": ("api_error.txt", file_content, "text/plain")}

        response = client.post("/api/process_document", files=files)

        assert response.status_code == 200 # Endpoint by neměl spadnout
        assert response.json() == fhir_resources_to_return # Měl by vrátit FHIR zdroje

        mock_extract.assert_called_once()
        mock_map.assert_called_once()
        MockApiClient.assert_called_once()
        mock_api_instance.send_fhir_bundle.assert_called_once()

        captured = capsys.readouterr()
        # Ověření, že chyba z API klienta byla zalogována do stderr (dle implementace v main.py)
        # V main.py je to: print(f"CHYBA: Nepodařilo se odeslat FHIR bundle ...", file=sys.stderr)
        # Nicméně capsys zachytává stdout. Pokud by to šlo do sys.stderr, museli bychom to testovat jinak
        # nebo upravit logování v main.py na standardní `logging` modul.
        # Prozatím budeme kontrolovat stdout, kam print směřuje defaultně v testech, pokud není specifikováno jinak.
        # V main.py je print(..., file=sys.stderr), takže capsys.out to nezachytí.
        # Pro jednoduchost tento assert vynecháme, nebo bychom museli mockovat sys.stderr.
        # Místo toho se spoléháme na to, že kód proběhl a vrátil správná data.
        # Pokud by bylo kritické, bylo by potřeba mockovat `sys.stderr` nebo použít `logging` a zachytávat logy.
        assert "CHYBA: Nepodařilo se odeslat FHIR bundle přes DigiMedicAPIClient: Simulated API Connection Error" in captured.err or \
               "CHYBA: Nepodařilo se odeslat FHIR bundle přes DigiMedicAPIClient: Simulated API Connection Error" in captured.out
        # Poznámka: pytest může přesměrovat stderr na stdout, proto kontrola obou.
        # V reálném běhu by to šlo do stderr.

# TODO: Zvážit test pro případ, kdy DigiMedicAPIClient() selže při inicializaci.
# TODO: Zvážit test pro případ, kdy extrakce textu vrátí None (ne chybový string)
# TODO: Zvážit test pro případ, kdy soubor nelze uložit na disk (oprávnění, plný disk) - těžší na čisté mockování

# Dodatečný test pro None z extract_text_from_document
def test_text_extraction_returns_none(client: TestClient):
    """
    Testuje případ, kdy extrakce textu vrátí None.
    """
    with patch('backend.main.extract_text_from_document', return_value=None) as mock_extract, \
         patch('backend.main.map_text_to_fhir') as mock_map, \
         patch('backend.main.DigiMedicAPIClient.send_fhir_bundle') as mock_send_bundle:

        file_content = b"fake image data that will cause None return"
        files = {"file": ("none_extract.jpg", file_content, "image/jpeg")}

        response = client.post("/api/process_document", files=files)

        assert response.status_code == 200
        assert response.json() == [] # Očekáváme prázdný seznam

        mock_extract.assert_called_once_with(ANY, input_type="image_path")
        mock_map.assert_not_called() # map_text_to_fhir by se nemělo volat
        mock_send_bundle.assert_not_called()

```
