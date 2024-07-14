# AIHDS - Platforma pro strukturování dat ve zdravotnictví

![AIHDS Logo]([https://via.placeholder.com/150x150.png?text=AIHDS+Logo](https://i.ibb.co/3Y2P8t8/DALL-E-2024-07-14-14-18-27-A-clean-and-minimalistic-pixel-art-hero-image-for-the-AIHDS-platform-inte.webp))

## Úvod

**AIHDS** (Artificial Intelligence Health Data Structuring) je projekt zaměřený na vytvoření aplikace/nástroje pro digitalizaci zdravotní dokumentace a převedení jejího obsahu do správné struktury a formátu podle aktuálních mezinárodních standardů pro zdravotnická data. Toho bude dosaženo pomocí AI modulu s využitím technologie OpenAI a možností OCR (Optical Character Recognition). Konkrétně se bude jednat o nástroj pro lékaře a zdravotnické pracovníky v České republice. Cílem projektu je zlepšit péči o pacienty, zefektivnit procesy a zvýšit kvalitu zdravotnických dat.

## Cíle projektu

- [x] Vytvořit aplikaci pro převod nestrukturovaných zdravotnických dat (text, obraz) do strukturované elektronické podoby
- [x] Implementovat modul umělé inteligence pro analýzu a extrakci informací s využitím modulu GPT-4 Vision bez nutnosti trénování vlastních modelů
- [x] Zajistit, aby výstupní data byla ve formátech splňujících standardy EHDS (European Health Data Space) a FHIR (Fast Healthcare Interoperability Resources) pro interoperabilitu
- [x] Vytvořit jednoduché a intuitivní uživatelské rozhraní

## Použité technologie

- **Umělá inteligence:** OpenAI, GPT-4 Vision
- **Databáze:** [doplnit]
- **Standardy:** FHIR, HL7, DICOM, SNOMED CT, ICD-10, CCDA
- **Backend:** [doplnit]
- **Frontend:** [doplnit]
- **UIX:** [Shadcn UI](https://github.com/shadcn-ui/ui)

## Funkce aplikace

- Nahrávání vstupních souborů různých formátů
- Volba typu dokumentu
- Analýza obsahu pomocí AI
- Extrakce strukturovaných informací
- Uložení do databáze
- Možnost exportu do CSV, JSON, PDF dle standardů
- Jednoduchá vizualizace a procházení výsledků

## Bezpečnost

- Autorizace uživatelů
- Anonymizace citlivých údajů
- Auditní záznamy
- Šifrování komunikace i uložených dat
