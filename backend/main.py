from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import shutil
import uuid
import json
import traceback
import logging
from datetime import datetime

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Importy z vlastních modulů
from backend.fhir_mapping import map_text_to_fhir, generate_fhir_id
from backend.ai_models.text_extractor import extract_text_from_document
from backend.digimedic_api_client import DigiMedicAPIClient

app = FastAPI(
    title="AI-FHIR Komponenta Backend",
    description="API pro zpracování textových a obrázkových dokumentů, jejich mapování na FHIR zdroje a přijímání návrhů na korekce.",
    version="0.2.3"
)

# Adresáře pro data
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CORRECTIONS_FILE_PATH = os.path.join(DATA_DIR, "correction_suggestions.json")
TEMP_UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "temp_uploads")
os.makedirs(TEMP_UPLOAD_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# --- Pydantic modely ---

class ProcessingResult(BaseModel):
    fhir_resources: List[Dict[str, Any]]
    quality_issues: List[Dict[str, Any]]
    digimedic_submission_status: Optional[str] = None

class OriginalIssueDetail(BaseModel):
    level: Optional[str] = None
    message: Optional[str] = None
    field: Optional[str] = None
    value: Optional[str] = None

class CorrectionSuggestionPayload(BaseModel):
    originalIssue: OriginalIssueDetail
    suggestedValue: Any
    fileName: str
    comment: Optional[str] = None

class StoredCorrectionSuggestion(CorrectionSuggestionPayload):
    received_timestamp: str

# --- API Endpoints ---

@app.post("/api/process_document", response_model=ProcessingResult)
async def process_document_endpoint(file: UploadFile = File(...)):
    """
    Endpoint pro zpracování nahraného dokumentu.
    """
    filename = file.filename if file.filename is not None else "unknown_file"
    file_extension = os.path.splitext(filename)[1]
    safe_filename = f"{uuid.uuid4()}{file_extension}"
    temp_file_path = os.path.join(TEMP_UPLOAD_DIR, safe_filename)

    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        extracted_data_for_fhir: Any = None
        original_text_for_fhir: str = ""
        file_content_type = file.content_type
        logger.debug(f"Nahraný soubor: {filename}, Typ: {file_content_type}, Uložen do: {temp_file_path}")

        if file_content_type == "text/plain":
            with open(temp_file_path, "r", encoding="utf-8", errors="replace") as f:
                text_content = f.read()
            original_text_for_fhir = text_content
            extracted_data_for_fhir = extract_text_from_document(text_content, input_type="text", use_nlp=True)
        elif file_content_type in ["image/png", "image/jpeg", "image/jpg"]:
            ocr_extracted_text = extract_text_from_document(temp_file_path, input_type="image_path")
            extracted_data_for_fhir = ocr_extracted_text
            original_text_for_fhir = ocr_extracted_text
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Nepodporovaný typ souboru: {file_content_type}. Použijte .txt, .png, .jpg, .jpeg."
            )

        if not extracted_data_for_fhir or (isinstance(extracted_data_for_fhir, str) and not extracted_data_for_fhir.strip()):
            logger.info(f"Z dokumentu {filename} nebyl extrahován žádný relevantní text.")
            return ProcessingResult(fhir_resources=[], quality_issues=[])

        mapping_output = map_text_to_fhir(extracted_data_for_fhir, original_text=original_text_for_fhir)
        fhir_resources = mapping_output.get("fhir_resources", [])
        quality_issues = mapping_output.get("quality_issues", [])

        digimedic_status_message: Optional[str] = None
        if not fhir_resources:
            digimedic_status_message = "Nebyly vytvořeny žádné FHIR zdroje, nic k odeslání na DigiMedic API."
        else:
            try:
                api_client = DigiMedicAPIClient()
                if api_client.simulate:
                    digimedic_status_message = "Odeslání na DigiMedic API je simulováno."

                bundle_entries = [{
                    "fullUrl": f"urn:uuid:{res['id']}",
                    "resource": res,
                    "request": {"method": "PUT", "url": f"{res['resourceType']}/{res['id']}"}
                } for res in fhir_resources if res and 'id' in res and 'resourceType' in res]

                if bundle_entries:
                    fhir_bundle = {
                        "resourceType": "Bundle",
                        "id": generate_fhir_id(),
                        "type": "transaction",
                        "entry": bundle_entries
                    }
                    api_response = api_client.send_fhir_bundle(fhir_bundle)
                    logger.info(f"Odpověď z DigiMedic API: {api_response}")
                    if isinstance(api_response, dict) and api_response.get("status") == "success":
                         digimedic_status_message = api_response.get("message", "Data úspěšně odeslána.")
                    else:
                         digimedic_status_message = f"Odeslání na DigiMedic API selhalo nebo vrátilo neočekávanou odpověď."
                else:
                    digimedic_status_message = "Nebyly nalezeny žádné validní FHIR zdroje k odeslání."

            except Exception as api_ex:
                logger.error(f"Chyba při odesílání FHIR bundle: {api_ex}", exc_info=True)
                digimedic_status_message = f"Chyba při odesílání dat na DigiMedic API: {api_ex}"

        return ProcessingResult(
            fhir_resources=fhir_resources,
            quality_issues=quality_issues,
            digimedic_submission_status=digimedic_status_message
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Neočekávaná chyba při zpracování souboru {filename}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Interní chyba serveru při zpracování souboru.")
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

@app.post("/api/suggest_correction")
async def suggest_correction_endpoint(payload: CorrectionSuggestionPayload):
    """
    Endpoint pro příjem návrhů na korekci dat.
    """
    logger.info(f"Přijat návrh na korekci: {payload.model_dump_json(indent=2)}")
    try:
        suggestion_to_store = StoredCorrectionSuggestion(
            **payload.model_dump(),
            received_timestamp=datetime.utcnow().isoformat() + "Z"
        )
        suggestions_list = []
        if os.path.exists(CORRECTIONS_FILE_PATH):
            with open(CORRECTIONS_FILE_PATH, "r", encoding="utf-8") as f:
                try:
                    suggestions_list = json.load(f)
                    if not isinstance(suggestions_list, list):
                        suggestions_list = []
                except json.JSONDecodeError:
                    suggestions_list = []
        
        suggestions_list.append(suggestion_to_store.model_dump())
        
        with open(CORRECTIONS_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(suggestions_list, f, indent=2, ensure_ascii=False)
            
        return {"message": "Návrh na korekci byl úspěšně přijat."}
    except Exception as e:
        logger.error(f"Chyba při ukládání návrhu na korekci: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Chyba serveru při ukládání návrhu.")

if __name__ == "__main__":
    import uvicorn
    logger.info("Pro spuštění FastAPI serveru (z kořenového adresáře projektu):")
    logger.info("uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000")
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
