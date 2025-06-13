# Návrh integrace NLP/ML modelu pro extrakci dat z lékařských zpráv

## 1. Současný přístup a jeho limitace

### 1.1. Současná extrakce pomocí regulárních výrazů (regexů)

Aktuální systém v `backend/fhir_mapper.py` využívá sadu předdefinovaných regulárních výrazů k identifikaci a extrakci specifických informací z textu lékařských zpráv. Každý regex je navržen tak, aby cílil na konkrétní datový prvek, jako je jméno pacienta, datum narození, rodné číslo, hodnoty vitálních funkcí (krevní tlak, pulz, teplota, výška, hmotnost) a text diagnózy.

Proces typicky zahrnuje:
1.  Definici regexu pro každý hledaný údaj (např. `REGEX_PATIENT_NAME`, `REGEX_BLOOD_PRESSURE`).
2.  Prohledání vstupního textu zprávy pomocí funkce `re.search()` s daným regexem.
3.  Pokud je nalezena shoda, extrakce relevantní skupiny (group) z výsledku shody.
4.  Následné čištění, normalizace (např. formátování data, převod desetinné čárky na tečku) a validace extrahovaných řetězců.
5.  Mapování extrahovaných a očištěných dat na FHIR struktury.

### 1.2. Limitace regexového přístupu

Přestože je regexový přístup relativně jednoduchý na implementaci pro dobře strukturované a předvídatelné texty, naráží na několik zásadních limitací, zejména v kontextu variability a komplexity lékařských zpráv:

*   **Křehkost vůči variabilitě textu:** Lékařské zprávy mohou být psány různými lékaři, na různých pracovištích a mohou mít velmi variabilní strukturu, formátování a terminologii. Regexy jsou často příliš rigidní a jakákoliv drobná odchylka od očekávaného vzoru (např. jiné klíčové slovo, změna pořadí, neobvyklá interpunkce) může vést k selhání extrakce.
    *   *Příklad:* Změna "Datum narození:" na "Narozena dne:" může vyžadovat úpravu regexu. Různé formáty zápisu vitálních funkcí nebo diagnóz jsou také problematické.
*   **Obtížná údržba a rozšiřování:** S rostoucím počtem regexů a zvyšující se komplexitou extrahovaných informací se systém stává obtížně udržitelným. Každá nová varianta textu nebo nový typ informace k extrakci vyžaduje psaní a ladění nového (nebo úpravu stávajícího) regexu, což je časově náročné a náchylné k chybám. Dlouhé a komplexní regexy jsou navíc špatně čitelné.
*   **Neschopnost zpracovat složitější kontext a nejednoznačnosti:** Regexy pracují primárně na úrovni shody vzorů a mají omezené schopnosti porozumět sémantickému kontextu. Nedokáží efektivně řešit:
    *   **Negace:** Např. "Pacient *nemá* horečku" vs. "Pacient *má* horečku". Regex může chybně extrahovat "horečku" v obou případech.
    *   **Podmíněné informace:** Např. "Pokud bude teplota nad 38°C, podejte lék X."
    *   **Přiřazení hodnot ke správným entitám v komplexních případech:** Např. extrakce hodnot pro více měření stejného typu v jedné větě.
    *   **Synonyma a parafráze:** Různé způsoby vyjádření téže informace.
*   **Omezená schopnost generalizace:** Regexy jsou obvykle přizpůsobeny specifickým vzorům viděným v datech, na kterých byly vyvinuty. Špatně generalizují na nové, neviděné formáty textu.
*   **Zpracování numerických hodnot a jednotek:** I když regexy mohou extrahovat čísla, správná interpretace (např. rozlišení desetinné čárky vs. tečky, asociace s korektní jednotkou) může být komplikovaná a vyžaduje další logiku.

## 2. Přínosy NLP/ML modelů

Nasazení modelů přirozeného jazyka (NLP) a strojového učení (ML) by mohlo přinést několik klíčových výhod oproti čistě regexovému přístupu:

*   **Vyšší robustnost a adaptabilita:** NLP/ML modely, zejména ty založené na neuronových sítích, se dokáží lépe vyrovnat s variabilitou v textu (různé formulace, synonymie, drobné překlepy). Po natrénování na dostatečně rozmanitých datech mohou správně extrahovat informace i z formátů, které nebyly explicitně definovány v pravidlech.
*   **Schopnost generalizace:** Modely se učí vzory a souvislosti z dat, což jim umožňuje generalizovat na nové, dříve neviděné případy lépe než regexy.
*   **Lepší zpracování kontextu:** Moderní NLP modely (např. Transformery) dokáží lépe porozumět kontextu, ve kterém se slova a fráze vyskytují. To může pomoci při řešení nejednoznačností, negací a přiřazování hodnot ke správným entitám.
*   **Potenciálně vyšší přesnost pro komplexní informace:** Pro složité entity nebo vztahy, kde by regexy byly příliš komplikované nebo nespolehlivé, mohou NLP/ML modely dosáhnout vyšší přesnosti.
*   **Snazší rozšiřitelnost o nové entity:** Přidání schopnosti extrahovat nový typ informace (novou entitu) může být v některých případech snazší pomocí dotrénování existujícího modelu na nových anotovaných datech, než psaním a laděním mnoha nových regexů.
*   **Redukce manuální práce při údržbě pravidel:** Počáteční investice do trénování modelu může snížit potřebu neustálých manuálních úprav regexů při každé nové variantě vstupního textu.

## 3. Typy NLP/ML modelů a technik vhodné pro daný úkol

Pro extrakci strukturovaných dat z lékařských zpráv by byly vhodné následující typy NLP/ML modelů a technik:

### 3.1. Rozpoznávání pojmenovaných entit (NER - Named Entity Recognition)
NER modely jsou trénovány k identifikaci a klasifikaci textových fragmentů do předdefinovaných kategorií (entit).
*   **Využití:** Identifikace jmen pacientů, lékařů, dat (datum narození, datum vyšetření), názvů diagnóz, léků, hodnot měření (např. "120/80", "37.5"), jednotek ("mmHg", "°C", "kg").
*   **Příklady entit:** `PATIENT_NAME`, `BIRTH_DATE`, `MEASUREMENT_VALUE`, `MEASUREMENT_UNIT`, `DIAGNOSIS_TEXT`, `MEDICATION_NAME`, `LOINC_CODE`.
*   **Modely:**
    *   Tradiční ML modely (CRF - Conditional Random Fields) často s ručně vytvořenými příznaky.
    *   Moderní neuronové sítě (BiLSTM-CRF, Transformery jako BERT, RoBERTa, ELECTRA) dosahují state-of-the-art výsledků.
*   **Knihovny:** spaCy (nabízí předtrénované modely a snadné trénování vlastních NER), Hugging Face Transformers (poskytuje přístup k široké škále předtrénovaných Transformer modelů, které lze dotrénovat pro NER).

### 3.2. Klasifikace textu
Modely pro klasifikaci textu přiřazují celému textu nebo jeho části předdefinovanou kategorii.
*   **Využití:**
    *   Určení typu lékařské zprávy (např. propouštěcí zpráva, ambulantní zpráva, laboratorní výsledky).
    *   Identifikace relevantních sekcí ve zprávě (např. "Anamnéza", "Objektivní nález", "Závěr", "Medikace"), což může pomoci zúžit prostor pro hledání specifických informací.
*   **Modely:** Naive Bayes, SVM, Logistická regrese, neuronové sítě (CNN, RNN, Transformery).
*   **Knihovny:** scikit-learn, spaCy, Hugging Face Transformers.

### 3.3. Relační extrakce (Relation Extraction - RE)
RE modely identifikují sémantické vztahy mezi entitami rozpoznanými NER.
*   **Využití:**
    *   Spojení hodnoty měření s její jednotkou a typem měření (např. ("120/80", "mmHg", "Krevní tlak")).
    *   Přiřazení diagnózy k pacientovi.
    *   Propojení léku s dávkováním.
*   **Modely:** Pravidlové systémy, modely založené na příznacích, neuronové sítě (využívající embeddingy entit a jejich kontextu).
*   **Poznámka:** RE může být náročnější na implementaci a vyžaduje kvalitní anotovaná data s relacemi. Někdy lze vztahy odvodit heuristicky po NER (např. nejbližší jednotka k číselné hodnotě).

### 3.4. Předtrénované modely a fine-tuning
Významným trendem v NLP je využití velkých jazykových modelů (LLM) předtrénovaných na obrovském množství textových dat (např. BERT, GPT). Tyto modely se naučily obecné jazykové reprezentace.
*   **Přínos:** Mohou být dotrénovány (fine-tuned) na menším množství specifických anotovaných dat (např. české lékařské zprávy) pro konkrétní úkol (NER, klasifikace) a často dosahují lepších výsledků než modely trénované od nuly pouze na malém datasetu.
*   **České modely:** Existují modely předtrénované specificky na českých datech (např. RobeCzech, Czert).
*   **Knihovny:** Hugging Face Transformers je de facto standardem pro práci s těmito modely.

## 4. Potenciální výzvy při implementaci NLP/ML

*   **Dostupnost a kvalita trénovacích dat:**
    *   Toto je největší výzva. Pro trénování (nebo i kvalitní fine-tuning) supervised ML modelů je potřeba dostatečné množství anotovaných lékařských zpráv. Anotace zahrnuje manuální označování entit a jejich typů, případně vztahů mezi nimi.
    *   **Citlivost dat (GDPR):** Lékařské zprávy obsahují vysoce citlivé osobní údaje. Je nutné zajistit striktní anonymizaci dat před jejich použitím pro trénování, nebo pracovat ve vysoce zabezpečeném prostředí s příslušnými oprávněními. Anonymizace sama o sobě může být náročná a může ovlivnit kvalitu dat.
    *   **Náročnost anotace:** Anotace je časově a finančně náročná, vyžaduje odborníky (lékaře nebo proškolené anotátory) pro zajištění kvality.
*   **Výpočetní náročnost:**
    *   **Trénování:** Trénování velkých NLP modelů (zejména Transformerů) může vyžadovat značné výpočetní zdroje (GPU, TPU) a čas.
    *   **Inference:** I když je inference (použití natrénovaného modelu) méně náročná než trénování, pro rozsáhlé nasazení může stále vyžadovat optimalizaci a dostatečné hardwarové prostředky, aby byla odezva systému rychlá.
*   **Interpretovatelnost výsledků ("Black Box"):**
    *   Některé pokročilé ML modely (např. hluboké neuronové sítě) mohou být vnímány jako "černé skříňky", kde je obtížné plně pochopit, proč model dospěl k určitému rozhodnutí. To může být problematické v medicínském kontextu, kde je důležitá důvěra a vysvětlitelnost.
    *   Techniky jako LIME nebo SHAP mohou pomoci s interpretací, ale je to stále aktivní oblast výzkumu.
*   **Integrace do stávajícího systému:**
    *   Je třeba navrhnout, jak bude NLP/ML model spolupracovat s existujícím `fhir_mapper.py`.
    *   **Hybridní přístup:** Model může extrahovat entity a `fhir_mapper.py` by se postaral o jejich validaci, převod na FHIR a případně o extrakci jednodušších, vysoce strukturovaných informací pomocí regexů, které fungují spolehlivě.
    *   **Nahrazení části regexů:** NLP model by mohl nahradit regexy pro složitější nebo variabilnější pole (např. text diagnózy, jméno pacienta), zatímco jednoduché a fixní vzory by mohly zůstat řešeny regexy.
*   **Jazyková specifika češtiny:** Čeština je flektivní jazyk s bohatou morfologií, což může představovat další výzvu pro NLP modely. Je důležité používat modely a nástroje, které jsou pro češtinu dobře uzpůsobeny (např. kvalitní tokenizace, lemmatizace).
*   **Udržování a re-trénování modelu:** Modely mohou postupem času degradovat (tzv. model drift), pokud se charakter vstupních dat změní. Je potřeba počítat s cyklem monitorování výkonu modelu a jeho případným přetrénováním na novějších datech.

## 5. Návrh postupu integrace (hrubý odhad pro Fázi 3)

Následující kroky představují hrubý odhad postupu implementace NLP/ML komponenty:

1.  **Sběr, analýza a příprava dat (pokud možno v rámci projektu):**
    *   Získání (nebo vytvoření reprezentativního vzorku) lékařských zpráv.
    *   Důkladná anonymizace dat v souladu s GDPR a etickými principy.
    *   Manuální anotace dat: Označení entit (jména, data, diagnózy, hodnoty, jednotky atd.) a případně vztahů. Vytvoření anotační příručky pro konzistenci.
    *   Rozdělení dat na trénovací, validační a testovací sadu.
    *   Pokud anotace není možná v plném rozsahu, zvážit alternativní přístupy (např. few-shot learning, využití slabě ohodnocených dat, transfer learning z obecnějších českých modelů).

2.  **Výběr vhodného NLP/ML modelu a knihovny:**
    *   Pro NER jako první volbu zvážit modely založené na Transformerech (např. BERT-based) z knihovny Hugging Face nebo modely v spaCy.
    *   Prozkoumat dostupnost českých předtrénovaných modelů (např. RobeCzech, Czert, modely dostupné v rámci projektu `ufal/robeczech-base` na Hugging Face).

3.  **Experimenty s předtrénovanými modely (Zero-shot/Few-shot):**
    *   Otestovat vybrané předtrénované modely na malém vzorku anotovaných (nebo i neanotovaných) dat, aby se zjistila jejich výchozí schopnost extrahovat relevantní entity pro češtinu a medicínský kontext.

4.  **Dotrénování (Fine-tuning) modelu:**
    *   Pokud jsou k dispozici anotovaná data, dotrénovat vybraný předtrénovaný model na specifický úkol extrakce entit z českých lékařských zpráv.
    *   Experimentovat s hyperparametry trénování a architekturou modelu.

5.  **Návrh API pro NLP/ML model:**
    *   Definovat jasné rozhraní, jak bude model přijímat vstupní text (jednu zprávu nebo dávku zpráv).
    *   Definovat formát výstupu modelu (např. JSON seznam extrahovaných entit s jejich typy, hodnotami, pozicemi v textu a případně skóre spolehlivosti).

6.  **Integrace výstupu modelu do `fhir_mapper.py` (Hybridní přístup):**
    *   Upravit `fhir_mapper.py` tak, aby mohl volat NLP/ML model přes jeho API.
    *   Výstup z modelu (extrahované entity) použít jako vstup pro další zpracování v `fhir_mapper.py`.
    *   `fhir_mapper.py` by mohl:
        *   Validovat entity extrahované modelem (např. formát data, rozsah hodnot).
        *   Převádět entity na FHIR struktury (podobně jako to dělá nyní s výstupy z regexů).
        *   Ponechat regexy pro velmi jednoduché a spolehlivé případy, nebo jako fallback.
        *   Řešit logiku propojování entit (např. hodnota + jednotka), pokud to model neposkytuje přímo.

7.  **Testování a evaluace:**
    *   Důkladně otestovat nový systém na testovací sadě anotovaných dat.
    *   Použít standardní metriky pro NER (precision, recall, F1-skóre) pro jednotlivé typy entit.
    *   Porovnat výkon hybridního systému s původním čistě regexovým přístupem.
    *   Iterativně vylepšovat model a integraci na základě výsledků testování.

## 6. Doporučení

Integrace NLP/ML modelu má velký potenciál výrazně zlepšit robustnost a přesnost extrakce dat z lékařských zpráv, zejména s ohledem na jejich variabilitu. Hlavní výzvou je dostupnost kvalitních anotovaných trénovacích dat pro český medicínský kontext.

**Doporučení:**

*   **Zahájit s hybridním přístupem:** Začít s integrací NLP/ML modelu pro extrakci nejsložitějších a nejvariabilnějších entit (např. text diagnózy, jména, složitější popisné hodnoty), kde regexy nejvíce selhávají. Jednodušší a vysoce strukturované informace (např. explicitně označené rodné číslo ve fixním formátu) mohou být prozatím ponechány na regexech, pokud fungují spolehlivě.
*   **Využít předtrénované české modely:** Zaměřit se na využití a dotrénování existujících českých Transformer modelů (např. z rodiny RobeCzech, Czert), což může snížit potřebu obrovského množství anotovaných dat od nuly. Knihovna Hugging Face Transformers by měla být primární volbou. spaCy je také silný kandidát pro jednodušší nasazení a trénování.
*   **Iterativní vývoj a sběr dat:** Pokud je to možné, postupně sbírat a anotovat data. I menší, ale kvalitní datasety mohou být pro dotrénování užitečné. Zvážit aktivní učení nebo bootstrapping techniky pro efektivnější anotaci.
*   **Zaměřit se na NER jako první krok:** Rozpoznávání pojmenovaných entit je základním stavebním kamenem. Relační extrakce může být přidána později jako vylepšení.
*   **Realistická očekávání:** I s NLP/ML modely nebude dosaženo 100% přesnosti. Je důležité mít mechanismy pro validaci a případnou manuální korekci.

**Krátkodobě (v rámci Fáze 3, pokud to čas a zdroje dovolí):**
1.  Provést průzkum a experimenty s dostupnými českými předtrénovanými NER modely na vzorku zpráv (i bez anotací, jen pro kvalitativní posouzení).
2.  Pokud by se podařilo získat a (alespoň částečně) anotovat malý dataset, zkusit dotrénovat jeden vybraný model pro klíčové entity (např. jméno, datum, diagnóza, výška, váha).
3.  Navrhnout základní API modelu a zvážit, jak by jeho výstup mohl být integrován do `parse_patient_data` a `parse_vital_signs_data` jako alternativa nebo doplněk k regexům.

Dlouhodobě je přechod na robustnější NLP/ML řešení pro tento typ úlohy velmi žádoucí a přinese významné zkvalitnění systému.
