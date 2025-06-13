from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Any
import sys
import os

# Přidání cesty k 'backend' adresáři, aby bylo možné importovat fhir_mapper
# Toto je potřeba, pokud spouštíme main.py přímo z adresáře backendu,
# nebo pokud struktura projektu vyžaduje explicitní úpravu sys.path.
# Pro produkční nasazení (např. s Dockerem) by struktura importů mohla být jiná.
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from fhir_mapper import map_text_to_fhir
except ImportError:
    # Fallback pro případ, kdy je skript spuštěn tak, že 'backend' je již v PYTHONPATH
    # např. python -m backend.main
    from .fhir_mapper import map_text_to_fhir


app = FastAPI(
    title="AI-FHIR Komponenta Backend",
    description="API pro zpracování textu a jeho mapování na FHIR zdroje.",
    version="0.1.0"
)

class TextInput(BaseModel):
    text: str

@app.post("/api/process_text", response_model=List[Dict[str, Any]])
async def process_text_endpoint(input_data: TextInput):
    """
    Endpoint pro zpracování textu a jeho mapování na FHIR zdroje.
    Přijímá textový vstup a vrací seznam FHIR resources.
    """
    fhir_resources = map_text_to_fhir(input_data.text)
    return fhir_resources

# Příklad pro lokální spuštění s uvicorn, pokud je soubor spuštěn přímo
if __name__ == "__main__":
    import uvicorn
    # Uvicorn by měl být spuštěn s odkazem na aplikaci, např.:
    # uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
    # Tento blok je zde spíše pro informaci, přímé spouštění FastAPI z __main__ není typické pro produkci.
    print("Pro spuštění FastAPI serveru použijte příkaz jako:")
    print("uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000 --app-dir .")
    print("Ujistěte se, že jste v kořenovém adresáři projektu.")
