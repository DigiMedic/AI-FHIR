from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional # Added Optional
import os
import shutil
import uuid # Pro generování unikátních názvů souborů
import json # Pro logování quality_issues
import traceback # For detailed error logging in suggest_correction
import logging # Added logging
from datetime import datetime # Pro časové razítko

# Configure basic logging
# This should be done once, preferably at the application entry point.
# If this file is the main entry point (e.g. when run with uvicorn backend.main:app), this is a suitable place.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Přidání cesty k 'backend' adresáři, aby bylo možné importovat z podmodulů
# Toto je relevantní, pokud spouštíme `uvicorn backend.main:app` z kořenového adresáře projektu.
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# Removed sys import, path manipulation might need review based on project structure and execution

try:
    # Updated to import from the new fhir_mapping package
    from backend.fhir_mapping import map_text_to_fhir, generate_fhir_id
    from backend.ai_models.text_extractor import extract_text_from_document
    from backend.digimedic_api_client import DigiMedicAPIClient
except ImportError as e:
    logger.error(f"Import error during initial backend imports: {e}. Trying relative imports for main module context.", exc_info=True)
    # Relative imports for when main.py is run as a module within backend, or for tests
    from .fhir_mapping import map_text_to_fhir, generate_fhir_id
    from .ai_models.text_extractor import extract_text_from_document
    from .digimedic_api_client import DigiMedicAPIClient


app = FastAPI(
    title="AI-FHIR Komponenta Backend",
    description="API pro zpracování textových a obrázkových dokumentů, jejich mapování na FHIR zdroje a přijímání návrhů na korekce.",
    version="0.2.2" # Navýšení verze pro ukládání korekcí
)

# Adresář pro ukládání dat, jako jsou návrhy korekcí
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CORRECTIONS_FILE_PATH = os.path.join(DATA_DIR, "correction_suggestions.json")

# Dočasný adresář pro nahrávání souborů
TEMP_UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "temp_uploads")
os.makedirs(TEMP_UPLOAD_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True) # Zajistíme existenci adresáře pro data

# --- Pydantic modely ---

class ProcessingResult(BaseModel):
    fhir_resources: List[Dict[str, Any]]
    quality_issues: List[Dict[str, Any]]
    digimedic_submission_status: Optional[str] = None # Nové pole pro status odeslání

class OriginalIssueDetail(BaseModel):
    level: Optional[str] = None
    message: Optional[str] = None
    field: Optional[str] = None
    value: Optional[str] = None # Frontend sends String(originalIssue.value) or null

class CorrectionSuggestionPayload(BaseModel): # Data přicházející od klienta
    originalIssue: OriginalIssueDetail # Detail původního problému
    suggestedValue: Any # Návrh uživatele (může být string, číslo, atd.)
    fileName: str # Název souboru, ke kterému se návrh vztahuje (původně Optional, nyní povinné)
    # document_id: Optional[str] = None # Pokud bychom chtěli explicitní ID dokumentu
    # issue_id: Optional[str] = None # Pokud by issue mělo unikátní ID nezávislé na struktuře
    # path_to_value: Optional[str] = None # Pokud by originalIssue.field nebylo dostatečné
    comment: Optional[str] = None # Volitelný komentář uživatele

class StoredCorrectionSuggestion(CorrectionSuggestionPayload): # Data ukládaná na serveru
    received_timestamp: str # ISO formát časového razítka

# --- API Endpoints ---

@app.post("/api/process_document", response_model=ProcessingResult)
async def process_document_endpoint(file: UploadFile = File(...)):
    """
    Endpoint pro zpracování nahraného dokumentu (textového nebo obrázkového).
    Extrahovaný text je mapován na FHIR zdroje.
    """
    file_extension = os.path.splitext(file.filename)[1]
    safe_filename = f"{uuid.uuid4()}{file_extension}"
    temp_file_path = os.path.join(TEMP_UPLOAD_DIR, safe_filename)

    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        extracted_data_for_fhir: Any = None
        original_text_for_fhir: str = ""

        file_content_type = file.content_type
        logger.debug(f"Nahraný soubor: {file.filename}, Typ: {file_content_type}, Uložen do: {temp_file_path}")

        if file_content_type == "text/plain":
            with open(temp_file_path, "r", encoding="utf-8", errors="replace") as f:
                text_content = f.read()
            original_text_for_fhir = text_content
            extracted_data_for_fhir = extract_text_from_document(text_content, input_type="text", use_nlp=True)
            if isinstance(extracted_data_for_fhir, list):
                 logger.debug(f"Extrakce z textového souboru (NLP, {len(extracted_data_for_fhir)} entit): {str(extracted_data_for_fhir)[:200]}...")
            else:
                 logger.debug(f"Extrakce z textového souboru (pravděpodobně non-NLP fallback, prvních 100 znaků): '{str(extracted_data_for_fhir)[:100]}...' ")

        elif file_content_type in ["image/png", "image/jpeg", "image/jpg"]:
            ocr_extracted_text = extract_text_from_document(temp_file_path, input_type="image_path")
            extracted_data_for_fhir = ocr_extracted_text
            original_text_for_fhir = ocr_extracted_text
            logger.debug(f"Extrakce z obrázku (OCR) (prvních 100 znaků): '{ocr_extracted_text[:100]}...' ")
        else:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            raise HTTPException(
                status_code=400,
                detail=f"Nepodporovaný typ souboru: {file_content_type}. Použijte .txt, .png, .jpg, .jpeg."
            )

        should_return_empty = False
        if extracted_data_for_fhir is None:
            should_return_empty = True
            logger.info(f"Extrakce dat vrátila None pro soubor {file.filename}.")
        elif isinstance(extracted_data_for_fhir, str):
            if not extracted_data_for_fhir.strip() or extracted_data_for_fhir.startswith("[CHYBA OCR]"):
                error_detail = "Nepodařilo se extrahovat relevantní text z dokumentu."
                if extracted_data_for_fhir.startswith("[CHYBA OCR]"):
                    error_detail = extracted_data_for_fhir
                logger.info(f"{error_detail} pro soubor {file.filename}")
                should_return_empty = True

        if should_return_empty:
            return ProcessingResult(fhir_resources=[], quality_issues=[])

        logger.debug(f"Data pro FHIR mapování (typ: {type(extracted_data_for_fhir)}): {str(extracted_data_for_fhir)[:200]}...")
        logger.debug(f"Original_text pro FHIR mapování (prvních 200 znaků): {original_text_for_fhir[:200]}...")

        mapping_output = map_text_to_fhir(extracted_data_for_fhir, original_text=original_text_for_fhir)
        fhir_resources = mapping_output.get("fhir_resources", [])
        quality_issues = mapping_output.get("quality_issues", [])

        if quality_issues:
            try:
                # Log quality issues: using logger.info for each issue or a single log for all.
                # For now, logging the whole JSON blob, adjust if too verbose or needs specific formatting.
                issues_json_str = json.dumps(quality_issues, indent=2, ensure_ascii=False)
                logger.info(f"Quality issues reported from FHIR Mapper for {file.filename}:\n{issues_json_str}")
            except TypeError as json_err:
                logger.error(f"Nelze serializovat quality_issues do JSON: {json_err}. Issues: {quality_issues}", exc_info=True)


        digimedic_status_message: Optional[str] = None # Inicializace zde

        if not fhir_resources:
             logger.info(f"Funkce map_text_to_fhir vrátila prázdný seznam FHIR resources pro data z {file.filename}.")
             digimedic_status_message = "Nebyly vytvořeny žádné FHIR zdroje, nic k odeslání na DigiMedic API."
        else:
            try:
                api_client = DigiMedicAPIClient()
                if api_client.simulate:
                    digimedic_status_message = "Odeslání na DigiMedic API je simulováno (klient je v simulačním režimu)."

                bundle_id = generate_fhir_id()
                bundle_entries = []
                for resource in fhir_resources:
                    if resource and 'resourceType' in resource and 'id' in resource:
                        entry = {
                            "fullUrl": f"urn:uuid:{resource['id']}",
                            "resource": resource,
                            "request": {
                                "method": "PUT",
                                "url": f"{resource['resourceType']}/{resource['id']}"
                            }
                        }
                        bundle_entries.append(entry)
                    else:
                        logger.warning(f"Skipping invalid resource in fhir_resources: {resource}")

                if bundle_entries:
                    fhir_bundle = {
                        "resourceType": "Bundle",
                        "id": bundle_id,
                        "type": "transaction",
                        "entry": bundle_entries
                    }
                    logger.debug(f"Sending FHIR Bundle (ID: {bundle_id}) with {len(bundle_entries)} entries to DigiMedic API.")
                    api_response = api_client.send_fhir_bundle(fhir_bundle) # api_response je dict
                    logger.info(f"Response from DigiMedic API: {json.dumps(api_response, indent=2, ensure_ascii=False)}")

                    # Nastavení status message na základě odpovědi z DigiMedicAPIClient
                    # Předpokládáme, že DigiMedicAPIClient vrací 'status' a 'message' nebo 'issue'
                    if isinstance(api_response, dict):
                        if api_response.get("status") == "success":
                            digimedic_status_message = api_response.get("message", "FHIR data byla úspěšně odeslána na DigiMedic server.")
                        elif api_response.get("resourceType") == "OperationOutcome" and api_response.get("issue"):
                            first_issue = api_response["issue"][0]
                            diagnostics = first_issue.get("diagnostics", "Nespecifikovaná chyba z DigiMedic API.")
                            severity = first_issue.get("severity", "error")
                            digimedic_status_message = f"Odeslání na DigiMedic API: {severity} - {diagnostics}"
                        else:
                            digimedic_status_message = f"Odeslání na DigiMedic API vrátilo neočekávanou odpověď: {str(api_response)[:200]}..."
                    else:
                         digimedic_status_message = f"Odeslání na DigiMedic API vrátilo neočekávaný typ odpovědi."

                else:
                    logger.info("No valid resources to send in a FHIR bundle.")
                    if not digimedic_status_message: # Pokud již není nastavena zpráva o simulaci
                        digimedic_status_message = "Nebyly nalezeny žádné validní FHIR zdroje k odeslání na DigiMedic API."

            except Exception as api_ex:
                logger.error(f"Nepodařilo se odeslat FHIR bundle přes DigiMedicAPIClient: {str(api_ex)}", exc_info=True)
                if not digimedic_status_message: # Pokud již není nastavena zpráva o simulaci
                    digimedic_status_message = f"Chyba při odesílání FHIR bundle na DigiMedic API: {str(api_ex)}"

        return ProcessingResult(
            fhir_resources=fhir_resources,
            quality_issues=quality_issues,
            digimedic_submission_status=digimedic_status_message
        )
                # digimedic_status_message zde již bude nastaven, nebo bude None, pokud se k odeslání ani nedostalo
                if not digimedic_status_message: # Pokud ještě nebyla nastavena zpráva
                    digimedic_status_message = f"Interní chyba serveru před pokusem o odeslání na DigiMedic API: {str(api_ex)}"


        return ProcessingResult(
            fhir_resources=fhir_resources,
            quality_issues=quality_issues,
            digimedic_submission_status=digimedic_status_message
        )

    except HTTPException: # Re-raise HTTPException to let FastAPI handle it
        raise
    except Exception as e:
        logger.error(f"Neočekávaná chyba při zpracování souboru {file.filename}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Interní chyba serveru při zpracování souboru.")
    finally:
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                logger.debug(f"Dočasný soubor {temp_file_path} smazán.")
            except OSError as e_remove:
                logger.error(f"Nepodařilo se smazat dočasný soubor {temp_file_path}: {e_remove}", exc_info=True)
        if hasattr(file, 'file') and file.file and not file.file.closed:
            try:
                file.file.close()
                logger.debug(f"Soubor {file.filename} od klienta explicitně uzavřen.")
            except Exception as e_close:
                logger.error(f"Nepodařilo se uzavřít soubor {file.filename} od klienta: {e_close}", exc_info=True)

@app.post("/api/suggest_correction")
async def suggest_correction_endpoint(payload: CorrectionSuggestionPayload):
    """
    Endpoint pro příjem návrhů na korekci problémů s kvalitou dat.
    Přijaté návrhy jsou logovány a ukládány do souboru.
    """
    logger.info(f"Přijat požadavek na /api/suggest_correction s payloadom: {payload.model_dump_json(indent=2)}")

    try:
        # Vytvoření adresáře pro data, pokud neexistuje (mělo by být již vytvořeno při startu)
        os.makedirs(DATA_DIR, exist_ok=True)

        # Vytvoření záznamu pro uložení
        suggestion_to_store = StoredCorrectionSuggestion(
            **payload.model_dump(),
            received_timestamp=datetime.utcnow().isoformat() + "Z" # ISO formát s UTC označením
        )

        suggestions_list = []
        if os.path.exists(CORRECTIONS_FILE_PATH):
            try:
                with open(CORRECTIONS_FILE_PATH, "r", encoding="utf-8") as f:
                    content = f.read()
                    if content: # Soubor není prázdný
                        suggestions_list = json.loads(content)
                        if not isinstance(suggestions_list, list):
                            logger.warning(f"Obsah souboru {CORRECTIONS_FILE_PATH} není seznam. Inicializuji nový seznam.")
                            suggestions_list = []
            except json.JSONDecodeError:
                logger.error(f"Chyba při parsování JSONu z {CORRECTIONS_FILE_PATH}. Soubor bude přepsán.", exc_info=True)
                suggestions_list = [] # Přepíšeme soubor, pokud je poškozený
            except Exception as e:
                logger.error(f"Neočekávaná chyba při čtení {CORRECTIONS_FILE_PATH}: {e}", exc_info=True)
                # V případě jiné chyby čtení raději nebudeme pokračovat s přepsáním
                raise HTTPException(status_code=500, detail="Chyba serveru při čtení databáze návrhů.")

        suggestions_list.append(suggestion_to_store.model_dump())

        try:
            with open(CORRECTIONS_FILE_PATH, "w", encoding="utf-8") as f:
                json.dump(suggestions_list, f, indent=2, ensure_ascii=False)
            logger.info(f"Návrh korekce úspěšně uložen do {CORRECTIONS_FILE_PATH}.")
        except Exception as e:
            logger.error(f"Chyba při zápisu návrhu korekce do {CORRECTIONS_FILE_PATH}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Chyba serveru při ukládání návrhu.")

        return {
            "message": "Návrh na korekci byl úspěšně přijat a uložen.",
            "suggestion_details": suggestion_to_store.model_dump()
        }
    except HTTPException: # Pokud je HTTPException vyvolána explicitně výše
        raise
    except Exception as e:
        logger.error(f"Neočekávaná chyba v endpointu /api/suggest_correction: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Interní chyba serveru při zpracování návrhu: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    # Logger is already configured at the top of the file.
    # The uvicorn logger can be configured separately if needed, e.g.
    # logging.getLogger("uvicorn.access").setLevel(logging.DEBUG)
    # logging.getLogger("uvicorn.error").setLevel(logging.INFO)

    logger.info("Pro spuštění FastAPI serveru (z kořenového adresáře projektu):")
    logger.info("uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000")
    logger.info(f"Dočasné soubory budou ukládány do: {os.path.abspath(TEMP_UPLOAD_DIR)}")
    logger.info("Endpoint pro návrhy korekcí dostupný na: POST /api/suggest_correction")

    uvicorn.run(app, host="0.0.0.0", port=8000)
