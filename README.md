# AI-FHIR Komponenta

![AIHDS Logo](https://i.ibb.co/3Y2P8t8/DALL-E-2024-07-14-14-18-27-A-clean-and-minimalistic-pixel-art-hero-image-for-the-AIHDS-platform-inte.webp)

## Přehled projektu

### Úvod
AI-FHIR komponenta je specializovaný nástroj pro automatické strukturování nestrukturovaných zdravotních dat do standardizovaného formátu **FHIR** (Fast Healthcare Interoperability Resources). Tato komponenta slouží jako most mezi uživatelem a **DigiMedic** backendem, optimalizuje proces převodu a ukládání zdravotních dat.

### Problém
Zdravotnická zařízení často čelí výzvám při práci s nestrukturovanými daty, která je obtížné integrovat do moderních zdravotních informačních systémů. Manuální strukturování dat je nejen časově náročné, ale i náchylné k chybám.

### Řešení
**AI-FHIR** komponenta poskytuje:
- **Automatickou extrakci**: Relevantní informace jsou automaticky extrahovány z různých typů dokumentů.
- **Převod do FHIR formátu**: Extrahovaná data jsou automaticky konvertována do FHIR-kompatibilních zdrojů.
- **Seamless integraci**: Přímé napojení na DigiMedic backend pro ukládání a správu dat.
- **Uživatelsky přívětivé rozhraní**: Intuitivní prostředí pro nahrávání dokumentů a kontrolu výsledků.

### Klíčové funkce
1. **Podpora více formátů**: Zpracování textových dokumentů (.txt) a naskenovaných obrázků (formáty .png, .jpg, .jpeg). Podpora PDF je plánována do budoucna.
2. **AI-poháněná extrakce**: Přesná extrakce dat pomocí hybridního přístupu: primárně využívá model Stanza (`cs_cnec`) pro rozpoznávání pojmenovaných entit (NER) jako jsou jména pacientů, data, diagnózy (např. typ 'DIS'), a také pro identifikaci číselných hodnot a potenciálních jednotek u vitálních funkcí (krevní tlak, pulz, teplota, výška, hmotnost). Pro případy, kdy NLP extrakce není jednoznačná, nebo pro specifické, vysoce strukturované vzory, se jako fallback a doplňkový mechanismus používají pokročilé regulární výrazy. Tento hybridní model umožňuje robustnější a přesnější zpracování široké škály formátů lékařských zpráv.
3. **FHIR mapování**: Automatická konverze dat do FHIR zdrojů.
4. **Pokročilá validace dat**: Integrované kontroly pro zajištění konzistence a správnosti dat, včetně porovnání údajů z rodného čísla s datem narození, kontroly fyziologických rozsahů pro měřené hodnoty a ověření časové platnosti záznamů.
5. **Integrace s DigiMedic**: Napojení na DigiMedic backend pro správu strukturovaných dat.
6. **Uživatelské rozhraní**: Jednoduché rozhraní pro nahrávání dokumentů a vizualizaci výsledků.
7.  **Automatické odesílání na DigiMedic FHIR Server**: Po úspěšné extrakci a transformaci dat na FHIR zdroje komponenta automaticky sestaví FHIR Bundle a odešle jej na nakonfigurovaný DigiMedic FHIR server. Tato funkce pracuje ve výchozím simulovaném režimu. Pro odesílání na reálný server je nutné nastavit proměnné prostředí `DIGIMEDIC_API_BASE_URL` a `DIGIMEDIC_API_TOKEN`.
8.  **Detailní záznamy o kvalitě zpracování**: Během procesu extrakce a mapování systém interně sbírá podrobné informace o možných problémech nebo nestandardních hodnotách (tzv. "quality issues"). Tyto záznamy jsou logovány na serveru a poskytují cennou zpětnou vazbu pro monitorování a budoucí vylepšení, včetně podpory pro uživatelské rozhraní při revizi dat.
9.  **Návrhy na korekci dat**: Uživatelské rozhraní umožňuje u každého identifikovaného problému s kvalitou dat ("quality issue") navrhnout korekci. Tyto návrhy jsou odesílány na backendový endpoint (`/api/suggest_correction`) pro zaznamenání a budoucí zpracování.

### Technologický stack
- **Frontend**: React.js
- **AI modely**: Pro rozpoznávání pojmenovaných entit (NER) je využíván model `cs_cnec` z knihovny Stanza, který identifikuje klíčové informace včetně jmen, dat, diagnóz a číselných hodnot. Tyto NLP entity jsou dále zpracovávány v kombinaci s kontextovou analýzou a pokročilými regulárními výrazy (jako fallback nebo pro zpřesnění) pro extrakci strukturovaných údajů, zejména vitálních funkcí.
- **NER model**: Stanza (knihovna od Stanford NLP Group, model `cs_cnec` pro češtinu)
- **OCR**: Tesseract
- **Backend**: DigiMedic FHIR Backend API

---

## Diagramy

### Architektura AI-FHIR Komponenty
![Architektura AI-FHIR Komponenty](https://github.com/DigiMedic/AI-FHIR/blob/a7d991a0c7bbe8fd5f25427b4064ce71512fb1e4/Al-FHIR%20Komponenta%20Architecture.svg)

Tento diagram ukazuje architekturu AI-FHIR komponenty, včetně klíčových součástí a jejich propojení.

### Tok Zpracování AI-FHIR Komponenty
![Tok Zpracování AI-FHIR Komponenty](https://github.com/DigiMedic/AI-FHIR/blob/a7d991a0c7bbe8fd5f25427b4064ce71512fb1e4/AI-FHIR%20Komponenta%20Flowchart.svg)

Tento diagram zobrazuje tok zpracování dat v rámci AI-FHIR komponenty, od nahrání dokumentu po jeho uložení do FHIR formátu.

---
---
  ## 10. Referenční materiály a odkazy

- **[GPT-4.0](https://openai.com/research/gpt-4)**
- **[FHIR-cz specifikace a prifily](https://build.fhir.org/ig/ncez-cz/cz-core/index.html)**
- **[NCEZ Seznam Zkratek](https://ncez.mzcr.cz/cs/seznam-zkratek/seznam-zkratek)**
- **[NCEZ Národní Kontaktni Místo](https://ncez.mzcr.cz/cs/narodni-kontaktni-misto-elektronickeho-zdravotnictvi/narodni-kontaktni-misto-pro-elektronicke)**
- **[NIXZD Dokumenty](https://www.nixzd.cz/dokumenty)**
- **[IHE Czech](https://www.ihe-czech.cz/)**
- **[GDPR Compliance](https://gdpr.eu/)**
- **[EHDS Specification](https://ec.europa.eu/health/ehealth/ehds_en)**
- **[Ethical AI Guidelines](https://www.acm.org/code-of-ethics)**
- **[Security Best Practices](https://www.nist.gov/topics/cybersecurity)**
---

## Roadmapa

### Fáze 1: Základy (Měsíce 1-2)
- [x] Analýza požadavků a specifikace komponenty
- [x] Návrh architektury komponenty
- [x] Vývoj základního AI modelu pro extrakci textu (placeholder implementován)
- [x] Vytvoření základního uživatelského rozhraní pro nahrávání dokumentů (React UI pro nahrávání a zobrazení textu)

### Fáze 2: Vývoj klíčových funkcí (Měsíce 3-4)
- [x] Implementace OCR pro zpracování naskenovaných dokumentů (backendová část s Tesseract, frontendová simulace)
- [x] Vývoj logiky pro mapování extrahovaných dat na FHIR zdroje (Python mapper pro Patient [včetně RČ], Observation [krevní tlak, pulz, teplota, výška, váha] a Condition [diagnóza])
- [x] Integrace s DigiMedic Backend API (simulovaný Python klient)
- [x] Rozšíření UI o vizualizaci strukturovaných dat (Patient, Observation - TK, pulz, teplota, výška, váha, Condition).

### Fáze 3: Vylepšení a optimalizace (Měsíce 5-6)
- [x] **Integrace NLP modelu pro extrakci entit:**
    - [x] Výběr a testování předtrénovaného NLP modelu (vybrán `stanfordnlp/stanza-cs` s modelem `cs_cnec`, licence Apache 2.0).
    - [x] Návrh hybridního přístupu (kombinace NLP Stanza a regexů) a jeho implementace pro klíčové entity (jméno pacienta, datum narození, diagnózy) i pro vitální funkce (krevní tlak, pulz, teplota, výška, hmotnost). NLP je nyní primárním zdrojem pro tyto entity, s regexy jako fallbackem a pro kontextovou validaci.
    - [ ] Případné dotrénování (fine-tuning) modelu na specifických datech (pokud budou dostupná).
- [x] **Pokročilá validace a návrh korekce dat:**
    - [x] Implementace pokročilé validace extrahovaných dat (RČ vs datum narození, pohlaví z RČ, fyziologické rozsahy, základní časová konzistence).
    - [x] Backend generuje strukturované "quality issues". Implementována základní UI funkcionalita ve frontendu pro navrhování korekcí k těmto issues; návrhy jsou logovány na backendu. Plnohodnotné zpracování korekcí (např. jejich aplikace na data, uživatelské rozhraní pro revizi a schvalování korekcí) a integrace do UI pro revizi dat jsou dalšími kroky.
- [ ] **Vylepšení UI/UX:**
    - [ ] Zapracování zpětné vazby od uživatelů (pokud bude k dispozici).
    - [~] Zlepšení vizualizace komplexnějších FHIR zdrojů nebo chybových stavů. (Backend poskytuje strukturované 'quality issues', frontend nyní tyto problémy zobrazuje přehledněji. Refaktoring `App.js` na menší komponenty může dále přispět k lepší vizualizaci a údržbě).
- [x]/[~] **Formalizace testování, výkonnostní optimalizace a refaktoring:**
    - [x] Implementována a rozšířena sada jednotkových a integračních testů pro backend (endpointy, logika extrakce a mapování, API klient) pomocí pytest.
    - [~] Provedeno základní profilování kritických částí aplikace (NLP extrakce, FHIR mapování) a identifikace potenciálních oblastí pro optimalizaci. Výkon je prozatím považován za akceptovatelný pro typické vstupy.
    - [ ] Refaktoring backendového souboru `fhir_mapper.py` pro lepší čitelnost, modularitu a údržbu.
    - [ ] Přechod z `print` na standardní `logging` modul v celém backendu pro konzistentní a konfigurovatelné logování.
    - [ ] Refaktoring frontendového souboru `App.js` na menší, lépe spravovatelné a znovupoužitelné komponenty.
    - [ ] Zvážit úpravu URL backendu v testech (aktuálně pravděpodobně napevno).

### Fáze 4: Testování a finalizace (Měsíc 7)
- [~] Komplexní testování komponenty: Doplnit testy pro backend endpoint `/api/suggest_correction` a odpovídající frontendovou funkcionalitu. (Základní frontendové a specifické backendové testy již přidány).
- [x] Implementován reálný DigiMedic API klient v backendu s možností konfigurace přes proměnné prostředí a automatickým odesíláním FHIR Bundlů z hlavního zpracovávacího endpointu. Propojení s frontendem pro řízení tohoto procesu a plná integrace s produkčním API je dalším krokem.
- [ ] Tvorba uživatelské dokumentace.
- [ ] Příprava na nasazení.
- [ ] Aktualizace `README.md`: Doplnění informací o doporučené verzi Pythonu pro backend, zpřesnění instalace backendových závislostí a detailnější instrukce pro instalaci a konfiguraci Tesseract OCR.
## Začínáme

### Předpoklady
- Node.js (verze 14 nebo novější).
- **Python:** Doporučena verze Python 3.9+ (např. 3.9, 3.10, 3.11). Některé závislosti mohou vyžadovat novější verze.
- Přístup k DigiMedic Backend API (pro reálný provoz, jinak běží v simulovaném režimu).
- **Tesseract OCR Engine:**
    - Musí být nainstalovaný v systému pro zpracování obrázkových dokumentů.
    - Oficiální instalační příručka: [Tesseract OCR Installation](https://tesseract-ocr.github.io/tessdoc/Installation.html).
    - Ujistěte se, že máte nainstalovaná jazyková data minimálně pro češtinu (`ces`) a případně angličtinu (`eng`), pokud budete zpracovávat dokumenty v těchto jazycích. Další jazyky dle potřeby.
    - Například na systémech Debian/Ubuntu se jazyková data často instalují pomocí balíčku jako `tesseract-ocr-ces`. Ověřte si název balíčku pro vaši distribuci.
    - Aplikace očekává, že Tesseract je v systémové PATH. Pokud tomu tak není, může být potřeba upravit cestu k `tesseract_cmd` v souboru `backend/ai_models/text_extractor.py` (aktuálně se však spoléhá na PATH).
- **Stanza NLP Model:** Při prvním spuštění komponenty, která využívá NLP model Stanza, může dojít k automatickému stažení jazykového modelu pro češtinu (pokud již není přítomen v systému v defaultním umístění Stanza modelů, typicky `~/stanza_resources`). Toto stažení vyžaduje připojení k internetu.

### Instalace

1.  **Naklonujte repozitář:**
    ```bash
    git clone https://github.com/vase-org/ai-fhir-komponenta.git
    cd ai-fhir-komponenta
    ```

2.  **Nastavení a instalace backendových závislostí:**
    Doporučuje se vytvořit a aktivovat virtuální prostředí pro Python.
    ```bash
    # Vytvoření virtuálního prostředí (např. v kořenovém adresáři projektu)
    python -m venv venv
    ```
    Aktivace virtuálního prostředí:
    -   Windows: `venv\Scripts\activate`
    -   Linux/macOS: `source venv/bin/activate`

    Nainstalujte požadované Python knihovny:
    ```bash
    pip install -r backend/requirements.txt
    ```

3.  **Instalace frontendových závislostí:**
    ```bash
    cd frontend
    npm install
    cd ..
    ```
    (Předpokládá, že se vrátíte do kořenového adresáře projektu, pokud je to relevantní pro další kroky.)

4.  **Nastavte proměnné prostředí:**
    Proměnné prostředí se konfigurují pomocí `.env` souborů. Vytvořte je zkopírováním a úpravou `.env.example` souborů:

    *   **Pro backend (FastAPI/Uvicorn):**
        -   Zkopírujte `backend/.env.example` do `backend/.env`.
        -   Upravte `backend/.env`: Pro reálný (nesimulovaný) režim DigiMedic API klienta nastavte proměnné `DIGIMEDIC_API_BASE_URL` a `DIGIMEDIC_API_TOKEN`. Pokud tyto proměnné nejsou nastaveny nebo soubor `.env` neexistuje, DigiMedicAPIClient poběží v simulovaném režimu.

    *   **Pro frontend (React):**
        -   Zkopírujte `frontend/.env.example` do `frontend/.env`.
        -   Upravte `frontend/.env`: Klíčová proměnná je `REACT_APP_API_URL`, která určuje adresu backendového API (např. `http://localhost:8000`). Proměnné v tomto souboru musí začínat prefixem `REACT_APP_`.

5.  **Spusťte vývojový server:**
   `Spuštění vývojových serverů:`
   *   `Pro backend (z kořenového adresáře projektu): uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000`
   *   `Pro frontend (z adresáře \`frontend\`): npm start`

### Spuštění testů
```
# Spuštění backendových testů (z kořenového adresáře projektu):
pip install pytest # Pokud ještě není nainstalován
pytest backend/tests

# Spuštění frontendových testů (z adresáře `frontend`):
npm test
# Poznámka k frontendovým testům:
# Sada základních testů pro frontendovou komponentu App byla implementována v `frontend/src/App.test.js`.
# V některých omezených (např. sandboxed CI) prostředích může spuštění `npm test` selhat kvůli environmentálním omezením (např. timeout).
# Doporučuje se proto spouštět frontendové testy v lokálním vývojovém prostředí pro ověření jejich funkčnosti.
```

## Přispívání
Vítáme příspěvky do vývoje AI-FHIR komponenty.

## Licence
Tento projekt je licencován pod MIT licencí.

## Kontakt
Pro technické dotazy ohledně komponenty kontaktujte:
- Vedoucí vývoje: [Jméno] - email@example.com
- Technická podpora: podpora@ai-fhir-komponenta.cz

## Poděkování
- Děkujeme týmu DigiMedic za poskytnutí robustní backendové infrastruktury a API.
- FHIR® je registrovaná ochranná známka HL7 a je používána s povolením HL7.
