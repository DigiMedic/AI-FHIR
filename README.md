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
1. **Podpora více formátů**: Zpracování textových dokumentů, PDF a naskenovaných obrázků.
2. **AI-poháněná extrakce**: Přesná extrakce dat pomocí NLP a ML modelů.
3. **FHIR mapování**: Automatická konverze dat do FHIR zdrojů.
4. **Integrace s DigiMedic**: Napojení na DigiMedic backend pro správu strukturovaných dat.
5. **Uživatelské rozhraní**: Jednoduché rozhraní pro nahrávání dokumentů a vizualizaci výsledků.

### Technologický stack
- **Frontend**: React.js s použitím shadcn/ui
- **AI modely**: GPT-4.0, vlastní NLP modely
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
- [ ] **Integrace NLP modelu pro extrakci entit:**
    - [ ] Výběr a testování předtrénovaného NLP modelu (např. pro češtinu ze spaCy/Hugging Face).
    - [ ] Návrh a implementace hybridního přístupu (kombinace NLP a stávajících regexů).
    - [ ] Případné dotrénování (fine-tuning) modelu na specifických datech (pokud budou dostupná).
- [ ] **Pokročilá validace a návrh korekce dat:**
    - [ ] Rozšíření validace extrahovaných dat (např. RČ vs datum narození, fyziologické rozsahy).
    - [ ] Návrh mechanismu pro označování a případnou manuální korekci sporných dat v UI.
- [ ] **Vylepšení UI/UX:**
    - [ ] Zapracování zpětné vazby od uživatelů (pokud bude k dispozici).
    - [ ] Zlepšení vizualizace komplexnějších FHIR zdrojů nebo chybových stavů.
- [ ] **Formalizace testování a výkonnostní optimalizace:**
    - [ ] Zavedení jednotkových a integračních testů pomocí testovacího frameworku (např. pytest pro backend, Jest/RTL pro frontend).
    - [ ] Profilování a optimalizace kritických částí aplikace (OCR, FHIR mapování).

### Fáze 4: Testování a finalizace (Měsíc 7)
- [ ] Komplexní testování komponenty
- [ ] Integrace s produkčním prostředím DigiMedic (propojení frontendu s reálným backendem a API)
- [ ] Tvorba uživatelské dokumentace
- [ ] Příprava na nasazení
## Začínáme

### Předpoklady
- Node.js (v14 nebo novější)
- Přístup k DigiMedic Backend API

### Instalace
1. Naklonujte repozitář:
   ```
   git clone https://github.com/vase-org/ai-fhir-komponenta.git
   ```
2. Nainstalujte závislosti:
   ```
   cd ai-fhir-komponenta
   npm install
   ```
3. Nastavte proměnné prostředí:
   ```
   cp .env.example .env
   # Upravte .env s vašimi specifickými konfiguracemi, včetně přístupových údajů k DigiMedic API
   ```
4. Spusťte vývojový server:
   ```
   npm run dev
   ```

### Spuštění testů
```
npm run test
```

## Přispívání
Vítáme příspěvky do vývoje AI-FHIR komponenty. Přečtěte si prosím náš soubor [CONTRIBUTING.md](CONTRIBUTING.md) pro podrobnosti o procesu pro podávání pull requestů.

## Licence
Tento projekt je licencován pod MIT licencí - viz soubor [LICENSE.md](LICENSE.md) pro detaily.

## Kontakt
Pro technické dotazy ohledně komponenty kontaktujte:
- Vedoucí vývoje: [Jméno] - email@example.com
- Technická podpora: podpora@ai-fhir-komponenta.cz

## Poděkování
- Děkujeme týmu DigiMedic za poskytnutí robustní backendové infrastruktury a API.
- FHIR® je registrovaná ochranná známka HL7 a je používána s povolením HL7.
