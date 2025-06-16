# Uživatelská příručka AI-FHIR Komponenty

## 1. Úvod

AI-FHIR komponenta je nástroj navržený pro automatickou extrakci informací z nestrukturovaných lékařských zpráv (textových souborů nebo obrázků) a jejich transformaci do standardizovaného formátu FHIR (Fast Healthcare Interoperability Resources). Cílem je usnadnit digitalizaci a interoperabilitu zdravotnických dat.

Tato příručka je určena pro koncové uživatele aplikace, kteří budou pracovat s frontendovým rozhraním pro nahrávání dokumentů a revizi extrahovaných dat.

## 2. Instalace a Nastavení

Podrobné instrukce pro instalaci a nastavení všech součástí systému (Frontend, Backend, Tesseract OCR, Stanza NLP model) naleznete v hlavním souboru [README.md](./README.md) v sekcích "Předpoklady" a "Instalace".

**Klíčové předpoklady shrnutí:**
*   Nainstalovaný Node.js (pro frontend)
*   Nainstalovaný Python 3.9+ (pro backend)
*   Funkční instalace Tesseract OCR (včetně českých jazykových dat `ces`)
*   Připojení k internetu pro stažení Stanza NLP modelu (při prvním spuštění backendu)

## 3. Použití Aplikace - Frontend

Frontendové rozhraní AI-FHIR komponenty je přístupné přes webový prohlížeč po spuštění frontendového serveru (typicky na adrese jako `http://localhost:3000`).

### 3.1 Nahrávání Dokumentů
*   V hlavní části aplikace naleznete sekci pro nahrání souboru.
*   Klikněte na tlačítko pro výběr souboru nebo přetáhněte soubor do vyznačené oblasti.
*   **Podporované formáty**:
    *   Textové soubory: `.txt` (očekáváno kódování UTF-8)
    *   Obrázkové soubory: `.png`, `.jpg`, `.jpeg` (pro OCR zpracování)
*   Po výběru souboru začne automaticky jeho zpracování backendem.

### 3.2 Zobrazení Výsledků Zpracování
Po dokončení zpracování se na stránce zobrazí několik sekcí:

*   **Informace o zpracování / Extrahovaný text**:
    *   U textových souborů zde uvidíte název souboru a prvních 100 znaků jeho obsahu.
    *   U obrázkových souborů zde bude potvrzení o zpracování a název souboru. Text extrahovaný pomocí OCR se přímo v této sekci nezobrazuje, ale je použit pro další FHIR mapování.
*   **Strukturovaná FHIR Data**:
    *   Tato sekce zobrazuje jednotlivé FHIR zdroje (např. Patient, Observation, Condition), které byly vytvořeny z extrahovaných dat. Každý zdroj je prezentován ve formě karty pro lepší čitelnost.
*   **Stav odeslání na DigiMedic API**:
    *   Informuje o tom, zda a jak byla vygenerovaná FHIR data (jako FHIR Bundle) odeslána na nakonfigurovaný DigiMedic FHIR server. Může zobrazovat úspěch, chybu, nebo informaci o simulovaném odeslání.
*   **Problémy s kvalitou dat (`quality_issues`)**:
    *   Zde jsou uvedeny jakékoli problémy, nejednoznačnosti nebo varování, která vznikla během procesu extrakce dat a jejich mapování na FHIR zdroje.
    *   Každý problém má úroveň (např. Error, Warning, Info), popis, pole, kterého se týká, a původní hodnotu.
    *   Problémy jsou barevně odlišeny pro snazší orientaci.

### 3.3 Navrhování Korekcí
*   Pokud u některého z problémů s kvalitou dat identifikujete chybu a víte správnou hodnotu, můžete navrhnout korekci.
*   Klikněte na tlačítko "Navrhnout korekci" (nebo podobné) u daného problému.
*   Otevře se formulář, kde můžete zadat opravenou hodnotu a případně přidat komentář.
*   Po odeslání je váš návrh zaznamenán na backendu pro budoucí revizi a případné zapracování. Stav odeslání návrhu se zobrazí.

## 4. Použití Aplikace - Backend API (pro pokročilé)

Pro pokročilé uživatele nebo vývojáře jsou k dispozici následující backendové endpointy (typicky na adrese jako `http://localhost:8000`):

*   **POST `/api/process_document`**:
    *   Přijímá nahraný soubor (multipart/form-data).
    *   Vrací JSON s FHIR zdroji, problémy s kvalitou a statusem odeslání na DigiMedic.
*   **POST `/api/suggest_correction`**:
    *   Přijímá JSON payload s návrhem korekce (viz Pydantic model `CorrectionSuggestionPayload` v `backend/main.py`).
    *   Ukládá návrh a vrací potvrzení.

## 5. Řešení Běžných Problémů (FAQ)

*   **OCR nefunguje / Nejsou extrahována data z obrázku**:
    *   Ověřte, že máte správně nainstalovaný Tesseract OCR a že je v systémové PATH (viz [README.md](./README.md)).
    *   Ujistěte se, že máte nainstalovaná česká (`ces`) a případně anglická (`eng`) jazyková data pro Tesseract.
    *   Kvalita skenovaného dokumentu může výrazně ovlivnit výsledek OCR.
*   **Chybné nebo neúplné informace ve FHIR zdrojích**:
    *   Zkontrolujte sekci "Problémy s kvalitou dat". Backend se snaží identifikovat nejasnosti.
    *   Pokud je to možné, navrhněte korekci.
    *   Kvalita vstupního textu (struktura, jednoznačnost) ovlivňuje přesnost AI extrakce.
*   **Chyba připojení k backendu z frontendu**:
    *   Ujistěte se, že backendový server běží (např. pomocí `uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000`).
    *   Zkontrolujte, zda je proměnná prostředí `REACT_APP_API_URL` ve frontendovém `.env` souboru správně nastavena na adresu běžícího backendu.

## 6. Tipy pro Kvalitní Vstupní Data

*   **Textové soubory (.txt)**: Používejte kódování UTF-8. Strukturovanější text s jasnými oddělovači (např. "Pacient:", "Dg.:") pomáhá AI modelům lépe identifikovat informace.
*   **Obrázkové soubory (.png, .jpg, .jpeg)**: Pro nejlepší výsledky OCR používejte kvalitní skeny s dostatečným rozlišením (alespoň 300 DPI), bez výrazného šumu, skvrn nebo zkreslení. Text by měl být co nejčitelnější.

## 7. Kontakt a Podpora

Pro technické dotazy nebo hlášení problémů se obraťte na kontakty uvedené v hlavním souboru [README.md](./README.md).
