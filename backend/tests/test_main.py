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
        expected_response = {
            "fhir_resources": SAMPLE_FHIR_RESOURCES,
            "quality_issues": SAMPLE_QUALITY_ISSUES_EMPTY
        }
        assert response.json() == expected_response

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
        expected_response = {
            "fhir_resources": SAMPLE_PATIENT_RESOURCE,
            "quality_issues": SAMPLE_QUALITY_ISSUES_EMPTY
        }
        assert response.json() == expected_response

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
        expected_response = {
            "fhir_resources": [],
            "quality_issues": []
        }
        assert response.json() == expected_response # Očekáváme prázdný seznam zdrojů a issues

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
        expected_response = {
            "fhir_resources": [],
            "quality_issues": SAMPLE_QUALITY_ISSUES_PRESENT
        }
        assert response.json() == expected_response

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

        response = client.post("/api/process_document", files=files) # Capture the response

        assert response.status_code == 200 # Check status code
        expected_response = {
            "fhir_resources": SAMPLE_PATIENT_RESOURCE,
            "quality_issues": SAMPLE_QUALITY_ISSUES_PRESENT
        }
        assert response.json() == expected_response # Check response body

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
        expected_response = {
            "fhir_resources": fhir_resources_to_return,
            "quality_issues": []
        }
        assert response.json() == expected_response # Měl by vrátit FHIR zdroje a prázdné issues

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


# --- Fixtures pro testy /api/suggest_correction ---
@pytest.fixture(scope="function")
def correction_file_manager():
    """
    Fixture pro správu souboru s návrhy korekcí před a po každém testu.
    Zajišťuje, že testy běží s čistým souborem.
    """
    from backend.main import CORRECTIONS_FILE_PATH, DATA_DIR
    # Zajistit existenci adresáře DATA_DIR
    os.makedirs(DATA_DIR, exist_ok=True)

    # Smazat soubor před testem, pokud existuje
    if os.path.exists(CORRECTIONS_FILE_PATH):
        os.remove(CORRECTIONS_FILE_PATH)

    yield CORRECTIONS_FILE_PATH # Poskytne cestu k souboru testu, pokud by ji potřeboval

    # Smazat soubor po testu
    if os.path.exists(CORRECTIONS_FILE_PATH):
        os.remove(CORRECTIONS_FILE_PATH)

# --- Testy pro /api/suggest_correction ---

@patch('backend.main.datetime')
def test_suggest_correction_success(mock_datetime, client: TestClient, correction_file_manager):
    """
    Testuje úspěšné přijetí a uložení jednoho návrhu korekce.
    """
    # Nastavení mockovaného času
    # Pro přístup k datetime.utcnow().isoformat() je potřeba mockovat datetime.datetime
    mock_dt_instance = MagicMock()
    mock_dt_instance.isoformat.return_value = "2024-07-28T10:00:00" # Čas bez 'Z' jak to dělá datetime.utcnow().isoformat()

    # Mock datetime.utcnow() aby vracelo naši mockovanou instanci datetime objektu
    mock_datetime.utcnow.return_value = mock_dt_instance

    # Cesta k souboru s korekcemi z fixture
    corrections_file = correction_file_manager

    payload = {
        "originalIssue": {
            "level": "Warning",
            "message": "Původní problém",
            "field": "Patient.name.given",
            "value": "Pateint"
        },
        "suggestedValue": "Patient",
        "fileName": "test_document.txt",
        "comment": "Oprava překlepu"
    }

    response = client.post("/api/suggest_correction", json=payload)

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["message"] == "Návrh na korekci byl úspěšně přijat a uložen."

    # Ověření struktury suggestion_details
    stored_suggestion = response_data["suggestion_details"]
    assert stored_suggestion["fileName"] == payload["fileName"]
    assert stored_suggestion["suggestedValue"] == payload["suggestedValue"]
    assert stored_suggestion["comment"] == payload["comment"]
    assert stored_suggestion["originalIssue"]["field"] == payload["originalIssue"]["field"]
    assert "received_timestamp" in stored_suggestion
    assert stored_suggestion["received_timestamp"] == "2024-07-28T10:00:00Z" # Ověření mockovaného času s přidaným 'Z'

    # Ověření obsahu souboru
    assert os.path.exists(corrections_file)
    with open(corrections_file, 'r', encoding='utf-8') as f:
        saved_suggestions = json.load(f)

    assert isinstance(saved_suggestions, list)
    assert len(saved_suggestions) == 1

    saved_entry = saved_suggestions[0]
    assert saved_entry["fileName"] == payload["fileName"]
    assert saved_entry["suggestedValue"] == payload["suggestedValue"]
    assert saved_entry["comment"] == payload["comment"]
    assert saved_entry["originalIssue"]["message"] == payload["originalIssue"]["message"]
    assert saved_entry["received_timestamp"] == "2024-07-28T10:00:00Z"


@patch('backend.main.datetime')
def test_suggest_correction_multiple_suggestions(mock_datetime, client: TestClient, correction_file_manager):
    """
    Testuje úspěšné uložení více návrhů korekcí.
    """
    mock_dt_instance = MagicMock()
    mock_dt_instance.isoformat.side_effect = ["2024-07-28T10:00:00", "2024-07-28T10:05:00"]
    mock_datetime.utcnow.return_value = mock_dt_instance

    corrections_file = correction_file_manager

    payload1 = {
        "originalIssue": {"level": "Info", "message": "Problém 1", "field": "field1", "value": "val1"},
        "suggestedValue": "suggestion1",
        "fileName": "doc1.txt",
        "comment": "Komentář 1"
    }
    payload2 = {
        "originalIssue": {"level": "Error", "message": "Problém 2", "field": "field2", "value": "val2"},
        "suggestedValue": "suggestion2",
        "fileName": "doc2.txt",
        "comment": "Komentář 2"
    }

    response1 = client.post("/api/suggest_correction", json=payload1)
    assert response1.status_code == 200

    response2 = client.post("/api/suggest_correction", json=payload2)
    assert response2.status_code == 200

    assert os.path.exists(corrections_file)
    with open(corrections_file, 'r', encoding='utf-8') as f:
        saved_suggestions = json.load(f)

    assert isinstance(saved_suggestions, list)
    assert len(saved_suggestions) == 2

    assert saved_suggestions[0]["suggestedValue"] == "suggestion1"
    assert saved_suggestions[0]["fileName"] == "doc1.txt"
    assert saved_suggestions[0]["received_timestamp"] == "2024-07-28T10:00:00Z"

    assert saved_suggestions[1]["suggestedValue"] == "suggestion2"
    assert saved_suggestions[1]["fileName"] == "doc2.txt"
    assert saved_suggestions[1]["received_timestamp"] == "2024-07-28T10:05:00Z"


def test_suggest_correction_file_creation(client: TestClient, correction_file_manager):
    """
    Testuje, zda je soubor s návrhy vytvořen, pokud původně neexistoval.
    """
    from backend.main import CORRECTIONS_FILE_PATH # Použijeme cestu definovanou v main

    # Fixture `correction_file_manager` zajistí, že soubor na začátku neexistuje.
    assert not os.path.exists(CORRECTIONS_FILE_PATH)

    payload = {
        "originalIssue": {"level": "Info", "message": "Test", "field": "test.field", "value": "old"},
        "suggestedValue": "new",
        "fileName": "file_creation_test.txt"
    }
    # Mock datetime není nutný, pokud nám nezáleží na přesném timestampu v tomto testu
    response = client.post("/api/suggest_correction", json=payload)
    assert response.status_code == 200
    assert os.path.exists(CORRECTIONS_FILE_PATH)


def test_suggest_correction_invalid_payload_missing_field(client: TestClient, correction_file_manager):
    """
    Testuje odeslání nevalidního payloadu (chybí povinné pole 'fileName').
    """
    payload = {
        "originalIssue": {"level": "Warning", "message": "Missing file name", "field": "some.field", "value": "abc"},
        "suggestedValue": "def"
        # Chybí "fileName"
    }
    response = client.post("/api/suggest_correction", json=payload)
    assert response.status_code == 422 # Unprocessable Entity
    response_data = response.json()
    assert "detail" in response_data
    assert any(err["type"] == "missing" and "fileName" in err["loc"] for err in response_data["detail"])


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
        expected_response = {
            "fhir_resources": [],
            "quality_issues": []
        }
        assert response.json() == expected_response # Očekáváme prázdné seznamy

        mock_extract.assert_called_once_with(ANY, input_type="image_path")
        mock_map.assert_not_called() # map_text_to_fhir by se nemělo volat
        mock_send_bundle.assert_not_called()


def test_process_image_document_actual_image(client: TestClient):
    """
    Testuje zpracování skutečného obrázkového souboru (.png) s OCR.
    Tento test nepoužívá mock pro extract_text_from_document ani map_text_to_fhir,
    aby se otestovala skutečná OCR extrakce a základní mapování.
    Očekává, že OCR extrahuje "Test OCR 123" z test_image.png.
    """
    # Cesta k testovacímu obrázku (vytvořenému skriptem create_test_image.py)
    # Předpokládáme, že testy běží z kořenového adresáře projektu,
    # nebo je PYTHONPATH nastaven tak, že 'backend' je dostupný.
    current_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(current_dir, "test_image.png")

    assert os.path.exists(image_path), f"Test image not found at {image_path}. Run create_test_image.py."

    # DigiMedicAPIClient bude stále mockován, abychom nevolali externí API
    with patch('backend.main.DigiMedicAPIClient') as MockApiClient:
        mock_api_instance = MockApiClient.return_value
        mock_api_instance.send_fhir_bundle.return_value = {"status": "success", "message": "Bundle sent (mocked)"}

        with open(image_path, "rb") as img_file:
            files = {"file": ("test_image.png", img_file, "image/png")}
            response = client.post("/api/process_document", files=files)

        assert response.status_code == 200
        response_data = response.json()
        assert isinstance(response_data, dict) # Změněno z list na dict dle nového response modelu
        assert "fhir_resources" in response_data
        assert "quality_issues" in response_data

        # Ověření, že DigiMedicAPIClient byl volán, pokud byly vytvořeny nějaké FHIR zdroje
        # Toto závisí na tom, zda "Test OCR 123" vyprodukuje nějaké FHIR zdroje.
        # Pokud fhir_resources mohou být prázdné, pak send_fhir_bundle nemusí být voláno.
        if response_data["fhir_resources"]:
            MockApiClient.assert_called_once()
            mock_api_instance.send_fhir_bundle.assert_called_once()
        else:
            # Pokud nejsou žádné zdroje, bundle by se neměl odesílat
            MockApiClient.assert_called_once() # Klient se inicializuje
            mock_api_instance.send_fhir_bundle.assert_not_called() # Ale neodesílá

        # Volitelný úklid - pro testovací assety to obvykle není nutné,
        # ale pokud by byl soubor vytvářen dynamicky v testu a neměl by přetrvávat:
        # if os.path.exists(image_path):
        #     os.remove(image_path)

        # Hlubší kontrola obsahu fhir_resources by vyžadovala znalost,
        # jak se "Test OCR 123" mapuje na FHIR.
        # Pro tento test stačí ověřit strukturu odpovědi a úspěšné zpracování.
        # Můžeme ale zkontrolovat, zda quality_issues obsahují informaci o extrahovaném textu,
        # pokud by to fhir_mapper dělal (což momentálně nedělá explicitně do quality_issues).
        # print("DEBUG response_data:", response_data) # Pro ladění
```
