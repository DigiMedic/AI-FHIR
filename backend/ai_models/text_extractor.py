# backend/ai_models/text_extractor.py
import os
import re
from typing import Union, List, Dict, Any # Přidáno pro typování

try:
    from PIL import Image
except ImportError:
    print("CHYBA: Knihovna Pillow není nainstalována. Spusťte 'pip install Pillow'.")
    Image = None

try:
    import pytesseract
except ImportError:
    print("CHYBA: Knihovna pytesseract není nainstalována. Spusťte 'pip install pytesseract'.")
    print("UPOZORNĚNÍ: Ujistěte se, že máte nainstalovaný Tesseract OCR engine v systému.")
    pytesseract = None

try:
    import stanza
except ImportError:
    print("CHYBA: Knihovna Stanza není nainstalována. Spusťte 'pip install stanza'.")
    stanza = None

stanza_nlp_pipeline = None

def get_stanza_pipeline():
    global stanza_nlp_pipeline
    if stanza is None:
        # Tato výjimka by měla být zachycena výše, ale pro jistotu
        raise ImportError("Knihovna Stanza není dostupná. Nelze inicializovat pipeline.")
    if stanza_nlp_pipeline is None:
        print("INFO: Inicializace Stanza pipeline pro cs (tokenize, ner)...")
        try:
            # V reálném nasazení by se model měl stahovat jen jednou nebo být součástí deploymentu.
            # Pro účely tohoto skriptu/modulu se pokusíme stáhnout, pokud není dostupný.
            # logging_level='WARN' potlačí většinu výpisů Stanza při stahování a načítání.
            stanza.download('cs', verbose=False, logging_level='WARN')
        except Exception as e:
            print(f"CHYBA: Nepodařilo se stáhnout Stanza model pro 'cs': {e}. Ujistěte se, že máte připojení k internetu nebo model již stažený.")
            # V případě selhání stahování by aplikace neměla pokračovat v pokusu o použití Stanza.
            raise RuntimeError(f"Selhání stahování/načítání Stanza modelu: {e}") from e

        # stanza.Pipeline vyvolá chybu, pokud model není nalezen, takže explicitní kontrola zde není nutná.
        stanza_nlp_pipeline = stanza.Pipeline('cs', processors='tokenize,ner', verbose=False, logging_level='WARN')
        print("INFO: Stanza pipeline inicializována.")
    return stanza_nlp_pipeline

def extract_text_from_document(document_input, input_type="text", lang='ces+eng', use_nlp: bool = False, nlp_engine: str = "stanza") -> Union[str, List[Dict[str, Any]]]:
    """
    Rozšířená funkce pro extrakci textu z dokumentu.
    Dokáže zpracovat přímý textový obsah, cestu k obrázkovému souboru pro OCR,
    nebo provést NLP extrakci entit z textu.

    Args:
        document_input (str): Obsah textového dokumentu jako řetězec,
                               nebo cesta k obrázkovému souboru.
        input_type (str): Typ vstupu, buď "text" pro přímý textový obsah,
                          nebo "image_path" pro cestu k obrázku.
        lang (str): Jazyk/jazyky pro Tesseract OCR (např. 'eng', 'ces', 'ces+eng').
        use_nlp (bool): Pokud True a input_type je "text", provede se NLP extrakce entit.
        nlp_engine (str): Specifikuje NLP engine, který se má použít (aktuálně podporován "stanza").

    Returns:
        Union[str, List[Dict[str, Any]]]: Extrahovaný text jako řetězec (pokud use_nlp=False),
                                          nebo seznam entit (pokud use_nlp=True a úspěšně).
                                          V případě chyby OCR vrací chybový řetězec.
    """
    print(f"DEBUG: Volání funkce extract_text_from_document, input_type: {input_type}, use_nlp: {use_nlp}, nlp_engine: {nlp_engine}")

    if input_type == "text" and use_nlp:
        if nlp_engine == "stanza":
            if stanza is None:
                print("CHYBA: Knihovna Stanza není dostupná, NLP extrakce se neprovede.")
                raise RuntimeError("Stanza není dostupná pro NLP zpracování.")
            try:
                nlp = get_stanza_pipeline()

                text_for_nlp = str(document_input).strip()
                text_for_nlp = re.sub(r'\r\n', '\n', text_for_nlp)
                text_for_nlp = re.sub(r'\r', '\n', text_for_nlp)
                # Vícenásobné mezery prozatím ponecháme, Stanza by si s nimi měla poradit.
                # text_for_nlp = re.sub(r'[ \t]+', ' ', text_for_nlp)

                print(f"DEBUG: Text pro Stanza NLP (prvních 100 znaků): '{text_for_nlp[:100]}...'")
                doc = nlp(text_for_nlp)
                entities = []
                for ent in doc.ents:
                    entities.append({
                        "text": ent.text,
                        "type": ent.type,
                        "start_char": ent.start_char,
                        "end_char": ent.end_char
                    })
                print(f"DEBUG: Stanza NLP extrahovala {len(entities)} entit.")
                return entities
            except Exception as e:
                print(f"CHYBA: Selhání při NLP zpracování (Stanza): {e}")
                # Pokud NLP selže, necháme propadnout k standardní (non-NLP) extrakci textu níže.
                # Je důležité, aby tato 'pass' větev skutečně umožnila pokračování kódu
                # k dalšímu bloku 'if input_type == "text":' (non-NLP).
                pass
        else:
            print(f"VAROVÁNÍ: Nepodporovaný NLP engine: {nlp_engine}. NLP extrakce se neprovede.")
            # Necháme propadnout k standardní (non-NLP) extrakci textu níže

    # Standardní extrakce textu (pokud use_nlp=False nebo pokud NLP selhalo a propadlo sem)
    # nebo OCR extrakce

    if input_type == "text":
        # Tato větev se nyní vykoná, pokud use_nlp == False,
        # NEBO pokud use_nlp == True, ale NLP zpracování výše selhalo a propadlo sem.
        if not isinstance(document_input, str):
            # Tato kontrola by měla být provedena i před NLP blokem, pokud je relevantní
            # Ale pro jednoduchost ji necháváme zde, protože NLP blok také pracuje s document_input jako stringem.
            raise TypeError("Pro input_type='text' musí být vstupní dokument řetězec.")

        text = str(document_input).strip()
        text = re.sub(r'\r\n', '\n', text)
        text = re.sub(r'\r', '\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        text = text.lower() # Převod na malá písmena pro non-NLP cestu

        extracted_text = text
        print(f"DEBUG: Výsledek textové extrakce (non-NLP, prvních 100 znaků): '{extracted_text[:100]}...'")
        return extracted_text

    elif input_type == "image_path":
        if pytesseract is None or Image is None:
            # Tato kontrola je kritická pro image_path
            print("CHYBA: Knihovny Pillow a/nebo Pytesseract nejsou dostupné pro OCR.")
            return "[CHYBA OCR]: Potřebné knihovny (Pillow, Pytesseract) nejsou dostupné pro zpracování obrázku."

        if not isinstance(document_input, str):
            raise TypeError("Pro input_type='image_path' musí být vstupní dokument cesta k souboru (řetězec).")

        if not os.path.exists(document_input):
            print(f"CHYBA: Soubor nenalezen na cestě: {document_input}")
            return f"[CHYBA OCR]: Soubor nenalezen: {document_input}"

        try:
            print(f"DEBUG: Pokus o OCR zpracování obrázku: {document_input}")
            # Poznámka: Původní kód vracel formátovaný string s "[OCR EXTRAKCE...]",
            # ale pro konzistenci s textovou extrakcí (non-NLP) by měl vracet jen čistý text.
            # Pokud je potřeba zachovat prefix, mělo by to být řešeno konzistentně.
            # Prozatím vracíme čistý text.
            text_from_image = pytesseract.image_to_string(Image.open(document_input), lang=lang)
            extracted_text = text_from_image.strip()
            print(f"DEBUG: Výsledek OCR extrakce (prvních 100 znaků): '{extracted_text[:100]}...'")
            return extracted_text # Vrací čistý text
        except pytesseract.TesseractNotFoundError:
            print("CHYBA: Tesseract OCR engine nebyl nalezen v systémové PATH.")
            print("Ujistěte se, že je Tesseract nainstalován a dostupný.")
            return "[CHYBA OCR]: Tesseract OCR engine nenalezen. Kontaktujte administrátora."
        except Exception as e:
            print(f"CHYBA: Neočekávaná chyba při OCR zpracování souboru {document_input}: {e}")
            return f"[CHYBA OCR]: Nepodařilo se zpracovat obrázek ({e})."
    else:
        raise ValueError(f"Neznámý input_type: {input_type}. Použijte 'text' nebo 'image_path'.")

if __name__ == '__main__':
    # Test non-NLP textové extrakce
    sample_text = "  Toto  je   VZOROVÝ text  \r\n  pro  Testování.  \r\r   Konec.  "
    print(f"Původní text:\n'{sample_text}'\n")
    extracted_direct_non_nlp = extract_text_from_document(sample_text, input_type="text", use_nlp=False)
    print(f"Extrahovaný text (přímý vstup, non-NLP):\n'{extracted_direct_non_nlp}'\n")

    # Test OCR (pokud jsou dostupné knihovny a ImageMagick)
    test_image_path = "test_ocr_image.png"
    test_text_for_image = "Test OCR 123 ČESKY"

    if Image is not None and pytesseract is not None:
        # Pokus o vytvoření testovacího obrázku
        # Tento příkaz může selhat, pokud 'convert' (ImageMagick) není nainstalován.
        # V takovém případě se OCR testy přeskočí nebo selžou kontrolovaně.
        try:
            # Jednoduchý textový obrázek bez externích závislostí na fontu, pokud je to možné
            # Použití `os.system` je platformně závislé a může být bezpečnostní riziko.
            # Pro robustní testování by bylo lepší generovat obrázek přímo s Pillow.
            os.system(f"convert -size 200x50 xc:lightblue -pointsize 20 -fill black -gravity center -draw \"text 0,0 '{test_text_for_image}'\" {test_image_path} > /dev/null 2>&1")
            if not os.path.exists(test_image_path): # Kontrola, zda byl obrázek skutečně vytvořen
                 print(f"VAROVÁNÍ: Zdá se, že příkaz 'convert' selhal nebo obrázek nebyl vytvořen na cestě: {test_image_path}. OCR testy obrázku mohou selhat nebo být přeskočeny.")
        except Exception as e:
            print(f"CHYBA: Nepodařilo se spustit příkaz 'convert' pro vytvoření testovacího obrázku: {e}. OCR testy obrázku budou přeskočeny.")
            # Zajistíme, aby test_image_path neexistoval, pokud selhalo vytvoření
            if os.path.exists(test_image_path): os.remove(test_image_path)


        if os.path.exists(test_image_path):
            print(f"Testovací obrázek '{test_image_path}' byl (pravděpodobně) vytvořen.")
            print(f"--- Test OCR Extrakce ({test_image_path}) ---")
            extracted_ocr_cs_en = extract_text_from_document(test_image_path, input_type="image_path", lang='ces+eng')
            print(f"Výsledek OCR (ces+eng):\n'{extracted_ocr_cs_en}'\n")
            os.remove(test_image_path) # Uklidíme po sobě
        else:
            print(f"INFO: Testovací obrázek '{test_image_path}' se nepodařilo vytvořit (pravděpodobně chybí ImageMagick 'convert'). OCR testy obrázku se přeskočí.")
    else:
        print("INFO: Knihovny Pillow a/nebo Pytesseract nejsou dostupné. OCR testy se přeskočí.")

    # Test s neexistujícím obrázkem
    print("--- Test s neexistujícím obrázkem ---")
    non_existent_image_path = "cesta/k/neexistujicimu/obrazku.png"
    extracted_non_existent = extract_text_from_document(non_existent_image_path, input_type="image_path")
    print(f"Výsledek pro neexistující obrázek:\n'{extracted_non_existent}'\n")

    # Test Stanza NLP Extrakce (pokud je Stanza dostupná)
    if stanza:
        print("\n--- Test Stanza NLP Extrakce ---")
        sample_nlp_text = "Pacientka Jana Nováková, narozená 15. května 1980 v Praze, si stěžuje na bolest hlavy. Bydliště: Dlouhá 12, Praha 1. RČ: 805515/1234. Navštívila Nemocnici Na Homolce."
        print(f"Vstupní text pro NLP:\n'{sample_nlp_text}'\n")
        try:
            nlp_entities = extract_text_from_document(sample_nlp_text, input_type="text", use_nlp=True, nlp_engine="stanza")
            if isinstance(nlp_entities, list):
                print("Extrahované entity (NLP):")
                for entity in nlp_entities:
                    print(f"- Text: '{entity['text']}', Typ: {entity['type']}, Start: {entity['start_char']}, End: {entity['end_char']}")
            else:
                # Pokud NLP selhalo a propadlo to k non-NLP extrakci, typ bude str
                print(f"NLP extrakce nevrátila seznam entit, ale: {type(nlp_entities)}. Obsah: '{nlp_entities}'")
        except RuntimeError as e: # Zachytáváme RuntimeError z get_stanza_pipeline nebo z kontroly Stanza
             print(f"CHYBA při testování NLP extrakce (RuntimeError): {e}")
        except Exception as e:
            print(f"CHYBA při testování NLP extrakce (jiná chyba): {e}")

        # Test NLP s chybou (např. pokud by se Stanza nepodařilo inicializovat a kód by propadl)
        # Tento test je spíše koncepční, protože get_stanza_pipeline() by mělo vyvolat chybu dříve
        print("\n--- Test Stanza NLP Extrakce (očekávané propadnutí k non-NLP) ---")
        # Simulace, že stanza je None po importu, ale předtím, než by to get_stanza_pipeline chytilo
        # Toto je těžké čistě otestovat bez modifikace globální proměnné stanza
        # Místo toho můžeme testovat, co se stane, pokud NLP engine není podporován
        unsupported_nlp_text = "Test s nepodporovaným NLP enginem."
        print(f"Vstupní text pro nepodporovaný NLP: '{unsupported_nlp_text}'")
        result_unsupported_nlp = extract_text_from_document(unsupported_nlp_text, input_type="text", use_nlp=True, nlp_engine="nepodporovany_engine")
        print(f"Výsledek pro nepodporovaný NLP engine (očekává se non-NLP text): '{result_unsupported_nlp}' (Typ: {type(result_unsupported_nlp)})")

    else:
        print("\nINFO: Knihovna Stanza není dostupná, NLP testy se přeskočí.")

    # Test, kdy textový vstup pro NLP je prázdný
    if stanza:
        print("\n--- Test Stanza NLP Extrakce (prázdný vstup) ---")
        empty_text = "   "
        print(f"Vstupní text pro NLP (prázdný): '{empty_text}'")
        try:
            nlp_empty_entities = extract_text_from_document(empty_text, input_type="text", use_nlp=True, nlp_engine="stanza")
            if isinstance(nlp_empty_entities, list):
                print(f"Extrahované entity z prázdného textu (očekává se prázdný seznam): {nlp_empty_entities}")
            else:
                print(f"NLP extrakce z prázdného textu nevrátila seznam, ale: {type(nlp_empty_entities)}")
        except Exception as e:
            print(f"CHYBA při testování NLP s prázdným vstupem: {e}")

```
