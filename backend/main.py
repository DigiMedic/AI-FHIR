from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional # Added Optional
import sys
import os
import shutil
import uuid # Pro generování unikátních názvů souborů
import json # Pro logování quality_issues
import traceback # For detailed error logging in suggest_correction

# Přidání cesty k 'backend' adresáři, aby bylo možné importovat z podmodulů
# Toto je relevantní, pokud spouštíme `uvicorn backend.main:app` z kořenového adresáře projektu.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from backend.fhir_mapper import map_text_to_fhir, generate_fhir_id
    from backend.ai_models.text_extractor import extract_text_from_document
    from backend.digimedic_api_client import DigiMedicAPIClient
except ImportError as e:
    print(f"Import error: {e}. Trying relative imports.", file=sys.stderr)
    from .fhir_mapper import map_text_to_fhir, generate_fhir_id
    from .ai_models.text_extractor import extract_text_from_document
    from .digimedic_api_client import DigiMedicAPIClient


app = FastAPI(
    title="AI-FHIR Komponenta Backend",
    description="API pro zpracování textových a obrázkových dokumentů, jejich mapování na FHIR zdroje a přijímání návrhů na korekce.",
    version="0.2.1" # Navýšení verze pro novou funkcionalitu
)

# Dočasný adresář pro nahrávání souborů
TEMP_UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "temp_uploads")
os.makedirs(TEMP_UPLOAD_DIR, exist_ok=True)

# --- Pydantic modely ---

class ProcessingResult(BaseModel):
    fhir_resources: List[Dict[str, Any]]
    quality_issues: List[Dict[str, Any]]

class OriginalIssueDetail(BaseModel):
    level: Optional[str] = None
    message: Optional[str] = None
    field: Optional[str] = None
    value: Optional[str] = None # Frontend sends String(originalIssue.value) or null

class CorrectionSuggestionPayload(BaseModel):
    originalIssue: OriginalIssueDetail
    suggestedValue: str
    fileName: Optional[str] = None

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
        print(f"DEBUG: Nahraný soubor: {file.filename}, Typ: {file_content_type}, Uložen do: {temp_file_path}")

        if file_content_type == "text/plain":
            with open(temp_file_path, "r", encoding="utf-8", errors="replace") as f:
                text_content = f.read()
            original_text_for_fhir = text_content
            extracted_data_for_fhir = extract_text_from_document(text_content, input_type="text", use_nlp=True)
            if isinstance(extracted_data_for_fhir, list):
                 print(f"DEBUG: Extrakce z textového souboru (NLP, {len(extracted_data_for_fhir)} entit): {str(extracted_data_for_fhir)[:200]}...")
            else:
                 print(f"DEBUG: Extrakce z textového souboru (pravděpodobně non-NLP fallback, prvních 100 znaků): '{str(extracted_data_for_fhir)[:100]}...' ")

        elif file_content_type in ["image/png", "image/jpeg", "image/jpg"]:
            ocr_extracted_text = extract_text_from_document(temp_file_path, input_type="image_path")
            extracted_data_for_fhir = ocr_extracted_text
            original_text_for_fhir = ocr_extracted_text
            print(f"DEBUG: Extrakce z obrázku (OCR) (prvních 100 znaků): '{ocr_extracted_text[:100]}...' ")
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
            print(f"INFO: Extrakce dat vrátila None pro soubor {file.filename}.")
        elif isinstance(extracted_data_for_fhir, str):
            if not extracted_data_for_fhir.strip() or extracted_data_for_fhir.startswith("[CHYBA OCR]"):
                error_detail = "Nepodařilo se extrahovat relevantní text z dokumentu."
                if extracted_data_for_fhir.startswith("[CHYBA OCR]"):
                    error_detail = extracted_data_for_fhir
                print(f"INFO: {error_detail} pro soubor {file.filename}")
                should_return_empty = True

        if should_return_empty:
            return ProcessingResult(fhir_resources=[], quality_issues=[])

        print(f"DEBUG: Data pro FHIR mapování (typ: {type(extracted_data_for_fhir)}): {str(extracted_data_for_fhir)[:200]}...")
        print(f"DEBUG: Original_text pro FHIR mapování (prvních 200 znaků): {original_text_for_fhir[:200]}...")

        mapping_output = map_text_to_fhir(extracted_data_for_fhir, original_text=original_text_for_fhir)
        fhir_resources = mapping_output.get("fhir_resources", [])
        quality_issues = mapping_output.get("quality_issues", [])

        if quality_issues:
            try:
                issues_json = json.dumps(quality_issues, indent=2, ensure_ascii=False)
                print(f"INFO [Main]: Quality issues reported from FHIR Mapper for {file.filename}:\n{issues_json}")
            except TypeError as json_err:
                print(f"CHYBA [Main]: Nelze serializovat quality_issues do JSON: {json_err}. Issues: {quality_issues}", file=sys.stderr)

        if not fhir_resources:
             print(f"INFO: Funkce map_text_to_fhir vrátila prázdný seznam FHIR resources pro data z {file.filename}.")
        else:
            try:
                api_client = DigiMedicAPIClient()
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
                        print(f"WARN: Skipping invalid resource in fhir_resources: {resource}", file=sys.stderr)

                if bundle_entries:
                    fhir_bundle = {
                        "resourceType": "Bundle",
                        "id": bundle_id,
                        "type": "transaction",
                        "entry": bundle_entries
                    }
                    print(f"DEBUG: Sending FHIR Bundle (ID: {bundle_id}) with {len(bundle_entries)} entries to DigiMedic API.")
                    api_response = api_client.send_fhir_bundle(fhir_bundle)
                    print(f"INFO: Response from DigiMedic API: {api_response}")
                else:
                    print("INFO: No valid resources to send in a FHIR bundle.")
            except Exception as api_ex:
                print(f"CHYBA: Nepodařilo se odeslat FHIR bundle přes DigiMedicAPIClient: {str(api_ex)}", file=sys.stderr)

        return ProcessingResult(fhir_resources=fhir_resources, quality_issues=quality_issues)

    except HTTPException:
        raise
    except Exception as e:
        print(f"CHYBA: Neočekávaná chyba při zpracování souboru {file.filename}: {str(e)}\n{traceback.format_exc()}", file=sys.stderr)
        raise HTTPException(status_code=500, detail="Interní chyba serveru při zpracování souboru.")
    finally:
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                print(f"DEBUG: Dočasný soubor {temp_file_path} smazán.")
            except OSError as e_remove:
                print(f"CHYBA: Nepodařilo se smazat dočasný soubor {temp_file_path}: {e_remove}", file=sys.stderr)
        if hasattr(file, 'file') and file.file and not file.file.closed:
            try:
                file.file.close()
                print(f"DEBUG: Soubor {file.filename} od klienta explicitně uzavřen.")
            except Exception as e_close:
                print(f"CHYBA: Nepodařilo se uzavřít soubor {file.filename} od klienta: {e_close}", file=sys.stderr)

@app.post("/api/suggest_correction")
async def suggest_correction_endpoint(payload: CorrectionSuggestionPayload):
    """
    Endpoint pro příjem návrhů na korekci problémů s kvalitou dat.
    Přijaté návrhy jsou aktuálně pouze logovány.
    """
    try:
        # Logování přijatého payloadu
        # Pro produkční nasazení by se mělo použít strukturované logování (např. modul logging)
        print(f"INFO [SuggestCorrection]: Přijat návrh na korekci pro soubor '{payload.fileName}'.")
        print(f"INFO [SuggestCorrection]: Původní problém: {payload.originalIssue.dict()}")
        print(f"INFO [SuggestCorrection]: Navrhovaná hodnota: '{payload.suggestedValue}'")

        # Zde by v budoucnu mohla být logika pro uložení návrhu do databáze,
        # upozornění administrátora, nebo automatické znovuzpracování.
        # Prozatím pouze logujeme.

        return {"message": "Návrh byl úspěšně přijat a zalogován."}
    except Exception as e:
        # Používáme traceback pro detailní logování chyby na serveru
        print(f"CHYBA [SuggestCorrection]: Neočekávaná chyba při zpracování návrhu na korekci: {str(e)}\n{traceback.format_exc()}", file=sys.stderr)
        # Vrátíme obecnou chybu klientovi. FastAPI se postará o HTTP 500.
        raise HTTPException(status_code=500, detail=f"Interní chyba serveru při zpracování návrhu: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    print("Pro spuštění FastAPI serveru (z kořenového adresáře projektu):")
    print("uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000")
    print(f"Dočasné soubory budou ukládány do: {os.path.abspath(TEMP_UPLOAD_DIR)}")
    print("Endpoint pro návrhy korekcí dostupný na: POST /api/suggest_correction")
