from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic import BaseModel # Ponecháno pro případné budoucí použití, aktuálně není potřeba
from typing import List, Dict, Any
import sys
import os
import shutil
import uuid # Pro generování unikátních názvů souborů

# Přidání cesty k 'backend' adresáři, aby bylo možné importovat z podmodulů
# Toto je relevantní, pokud spouštíme `uvicorn backend.main:app` z kořenového adresáře projektu.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from backend.fhir_mapper import map_text_to_fhir
    from backend.ai_models.text_extractor import extract_text_from_document
except ImportError as e:
    print(f"Import error: {e}. Trying relative imports.", file=sys.stderr)
    # Fallback pro případ, kdy je skript spuštěn jinak nebo sys.path není správně nastaven
    # např. python -m backend.main
    from .fhir_mapper import map_text_to_fhir
    from .ai_models.text_extractor import extract_text_from_document


app = FastAPI(
    title="AI-FHIR Komponenta Backend",
    description="API pro zpracování textových a obrázkových dokumentů a jejich mapování na FHIR zdroje.",
    version="0.2.0" # Navýšení verze
)

# Dočasný adresář pro nahrávání souborů
# Použijeme relativní cestu k adresáři backend, aby to bylo konzistentní
TEMP_UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "temp_uploads")
# Vytvoření adresáře již bylo provedeno v předchozím subtasku, ale exist_ok=True nevadí
os.makedirs(TEMP_UPLOAD_DIR, exist_ok=True)

@app.post("/api/process_document", response_model=List[Dict[str, Any]])
async def process_document_endpoint(file: UploadFile = File(...)):
    """
    Endpoint pro zpracování nahraného dokumentu (textového nebo obrázkového).
    Extrahovaný text je mapován na FHIR zdroje.
    """
    # Vytvoření unikátní cesty k dočasnému souboru
    file_extension = os.path.splitext(file.filename)[1]
    safe_filename = f"{uuid.uuid4()}{file_extension}"
    temp_file_path = os.path.join(TEMP_UPLOAD_DIR, safe_filename)

    try:
        # Uložení nahraného souboru na disk
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        extracted_text = None
        file_content_type = file.content_type
        print(f"DEBUG: Nahraný soubor: {file.filename}, Typ: {file_content_type}, Uložen do: {temp_file_path}")

        if file_content_type == "text/plain":
            with open(temp_file_path, "r", encoding="utf-8", errors="replace") as f:
                text_content = f.read()
            extracted_text = extract_text_from_document(text_content, input_type="text")
            print(f"DEBUG: Extrakce z textového souboru (prvních 100 znaků): '{extracted_text[:100]}...' ")
        elif file_content_type in ["image/png", "image/jpeg", "image/jpg"]:
            extracted_text = extract_text_from_document(temp_file_path, input_type="image_path")
            print(f"DEBUG: Extrakce z obrázku (OCR) (prvních 100 znaků): '{extracted_text[:100]}...' ")
        else:
            if os.path.exists(temp_file_path): # Smazat soubor pokud je nepodporovaný typ
                os.remove(temp_file_path)
            raise HTTPException(
                status_code=400,
                detail=f"Nepodporovaný typ souboru: {file_content_type}. Použijte .txt, .png, .jpg, .jpeg."
            )

        if extracted_text is None or not extracted_text.strip() or extracted_text.startswith("[CHYBA OCR]"):
            error_detail = "Nepodařilo se extrahovat relevantní text z dokumentu."
            if extracted_text and extracted_text.startswith("[CHYBA OCR]"):
                error_detail = extracted_text
            print(f"INFO: {error_detail} pro soubor {file.filename}")
            return []

        print(f"DEBUG: Text pro FHIR mapování (prvních 200 znaků): {extracted_text[:200]}")
        fhir_resources = map_text_to_fhir(extracted_text)
        if not fhir_resources:
             print(f"INFO: Funkce map_text_to_fhir vrátila prázdný seznam pro text z {file.filename}: {extracted_text[:100]}...")
        return fhir_resources

    except HTTPException:
        raise
    except Exception as e:
        import traceback
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

if __name__ == "__main__":
    import uvicorn
    print("Pro spuštění FastAPI serveru (z kořenového adresáře projektu):")
    print("uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000")
    print(f"Dočasné soubory budou ukládány do: {os.path.abspath(TEMP_UPLOAD_DIR)}")
