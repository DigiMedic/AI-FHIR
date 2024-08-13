# AI-FHIR - Platforma pro strukturování dat ve zdravotnictví

![AIHDS Logo](https://i.ibb.co/3Y2P8t8/DALL-E-2024-07-14-14-18-27-A-clean-and-minimalistic-pixel-art-hero-image-for-the-AIHDS-platform-inte.webp)

## Úvod

**AIHDS** je projekt zaměřený na automatické strukturování nestrukturovaných zdravotních dat (např. skenované dokumenty) do standardizovaného formátu dle FHIR. Cílem je zajistit bezpečné a interoperabilní sdílení těchto dat s existujícími systémy EHR a národními portály.

## 1. Cíl projektu
Vytvoření komponenty, která strukturovně převádí nestrukturovaná zdravotní data do formátu FHIR a EHDS, a uchovává je na serveru pro interoperabilní sdílení.

## 2. Použité technologie

- **AI Modely**:
  - **Claude 3.4**: Model pro pokročilé zpracování přirozeného jazyka.
  - **GPT-4.0**: Model pro generování textu a zpracování nestrukturovaných dat.
- **OCR (Optical Character Recognition)**:
  - **Tesseract**: Open-source knihovna pro převod obrázků na text.
  - **[Tesseract OCR](https://github.com/tesseract-ocr/tesseract)**
- **Databáze**:
  - **HAPI FHIR Server**: Implementace FHIR pro správu a uchovávání zdravotních dat.
  - **[HAPI FHIR Server](https://hapifhir.io/)**
- **UI Framework**:
  - **React**: Front-end knihovna pro vytvoření interaktivního uživatelského rozhraní.
  - **[React Documentation](https://reactjs.org/docs/getting-started.html)**
- **Backend Platforma**:
  - **DigiMedic FHIR Backend**: Platforma pro bezpečné uchovávání a správu zdravotních dat.

## 3. Technologické specifikace

### a) Zpracování nestrukturovaných dat
- **OCR (Optical Character Recognition)**: Použití OCR nástrojů, jako je Tesseract, pro převod naskenovaných dokumentů na text.
  - **[Tesseract OCR](https://github.com/tesseract-ocr/tesseract)**
- **Předzpracování textu**: Čistění a strukturování textu z OCR. To zahrnuje odstranění chyb a rozdělení dat na logické jednotky (např. jméno pacienta, diagnóza).
  - **[Text Preprocessing Techniques](https://towardsdatascience.com/text-preprocessing-for-machine-learning-6217d71c6a5b)**

### b) Strukturování dat podle FHIR
- **FHIR Mappings**: Definování pravidel a mapování pro transformaci nestrukturovaných dat do strukturované formy kompatibilní s FHIR.
  - **[FHIR Specification](https://build.fhir.org/)**
- **Validace dat**: Validace strukturovaných dat podle FHIR specifikací.
  - **[FHIR Validation](https://www.hl7.org/fhir/validation.html)**

### c) Datové úložiště a interoperabilita
- **Databáze**: Použití HAPI FHIR Serveru pro práci s FHIR daty.
  - **[HAPI FHIR Server](https://hapifhir.io/)**
- **Interoperabilita**: Navrhnout API pro sdílení dat podle FHIR, kompatibilní s národními a evropskými specifikacemi.
  - **[FHIR API Specification](https://www.hl7.org/fhir/http.html)**

### d) Uživatelské rozhraní (UI)
- **React Komponenta**: UI bude implementováno jako React komponenta, kterou vizuálně přizpůsobíme podle potřeb projektu.
  - **[React Documentation](https://reactjs.org/docs/getting-started.html)**

## 4. Typy modelů a jejich použití

### a) Model pro zpracování textu (NLP)
- **Úkol**: Extrakce a strukturování klíčových informací z nestrukturovaného textu.
- **Modely**: GPT-4.0, Claude 3.4.
- **Použití**: Generování textu, odpovídání na dotazy, extrakce informací.

### b) Model pro klasifikaci
- **Úkol**: Klasifikace textových dat do specifických FHIR kategorií.
- **Modely**: Finetuning BERT nebo RoBERTa na specifické úkoly klasifikace.
- **Použití**: Kategorizace dat jako jsou diagnózy, léky, testy.

### c) Model pro rozpoznávání entit
- **Úkol**: Identifikace a extrakce entit jako jsou jména pacientů, data, diagnózy.
- **Modely**: Fine-tuning NER (Named Entity Recognition) modelů.
- **Použití**: Extrakce klíčových entit z textu a jejich přiřazení k odpovídajícím FHIR prvkům.

## 5. Příprava tréninkových dat

### a) Shromažďování dat
- **Zdroje dat**: Zdravotní dokumentace, lékařské zprávy, skenované dokumenty.
- **Formáty**: Textové soubory, PDF, obrázky.

### b) Anotace dat
- **Nástroje**: Labelbox, Prodigy.
- **Popis**: Ruční anotace dat pro trénink, zahrnující označení klíčových prvků a struktur.

### c) Příprava a čištění dat
- **Metody**: Odstranění šumu, normalizace textu, korekce OCR chyb.
- **Nástroje**: Open-source knihovny pro zpracování textu a obrázků.

## 6. Trénink modelů

### a) Výběr architektury
- **Pro NLP**: Transformer-based modely jako GPT-4.0 a Claude 3.4.
- **Pro klasifikaci**: BERT, RoBERTa.
- **Pro NER**: Fine-tuned NER modely.

### b) Metodika trénování
- **Rozdělení dat**: Tréninková data (80%), validační data (10%), testovací data (10%).
- **Parametry trénování**: Epochy, learning rate, batch size přizpůsobené na základě experimentů.

### c) Vyhodnocení výkonu
- **Metody**: Precision, Recall, F1 Score, Accuracy.
- **Nástroje**: Scikit-learn, TensorBoard.

## 7. Validace a Testování

### a) Validace modelu
- **Techniky**: Cross-validation, hyperparameter tuning.
- **Nástroje**: Optuna, Hyperopt.

### b) Testování modelu
- **Scénáře**: Testování na reálných a syntetických datech.
- **Metody**: A/B testing, user feedback.

## 8. Integrace a nasazení

### a) Integrace do systému
- **API**: RESTful API pro integraci s FHIR serverem.
- **Nástroje**: Docker, Kubernetes pro nasazení.

### b) Monitorování a údržba
- **Monitoring**: Sledování výkonu modelů v reálném čase.
- **Nástroje**: Prometheus, Grafana.

## 9. Dokumentace

### a) Dokumentace pro modely
- **Nástroje**: Docosaurus pro dokumentaci modelů a API.
  - **[Docosaurus Documentation](https://docosaurus.com/)**

### b) Školení a příručky
- **Materiály**: Uživatelské příručky, tréninkové materiály pro interní uživatele.
  - **[User Documentation](https://www.readthedocs.org/)**

## 10. Referenční materiály a odkazy

- **[GPT-4.0](https://openai.com/research/gpt-4)**
- **[FHIR Specification](https://build.fhir.org/)**
- **[NCEZ Seznam Zkratek](https://ncez.mzcr.cz/cs/seznam-zkratek/seznam-zkratek)**
- **[NCEZ Národní Kontaktni Místo](https://ncez.mzcr.cz/cs/narodni-kontaktni-misto-elektronickeho-zdravotnictvi/narodni-kontaktni-misto-pro-elektronicke)**
- **[NIXZD Dokumenty](https://www.nixzd.cz/dokumenty)**
- **[IHE Czech](https://www.ihe-czech.cz/)**
- **[GDPR Compliance](https://gdpr.eu/)**
- **[EHDS Specification](https://ec.europa.eu/health/ehealth/ehds_en)**
- **[Ethical AI Guidelines](https://www.acm.org/code-of-ethics)**
- **[Security Best Practices](https://www.nist.gov/topics/cybersecurity)**


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
