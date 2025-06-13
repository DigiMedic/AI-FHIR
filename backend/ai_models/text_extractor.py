# backend/ai_models/text_extractor.py
import os
import re
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

def extract_text_from_document(document_input, input_type="text", lang='ces+eng') -> str:
    """
    Rozšířená funkce pro extrakci textu z dokumentu.
    Dokáže zpracovat přímý textový obsah nebo cestu k obrázkovému souboru pro OCR.

    Args:
        document_input (str): Obsah textového dokumentu jako řetězec,
                               nebo cesta k obrázkovému souboru.
        input_type (str): Typ vstupu, buď "text" pro přímý textový obsah,
                          nebo "image_path" pro cestu k obrázku.
        lang (str): Jazyk/jazyky pro Tesseract OCR (např. 'eng', 'ces', 'ces+eng').

    Returns:
        str: Extrahovaný text.
    """
    print(f"DEBUG: Volání funkce extract_text_from_document, input_type: {input_type}")

    if pytesseract is None or Image is None:
        return "[CHYBA OCR]: Potřebné knihovny (Pillow, Pytesseract) nejsou dostupné."

    if input_type == "text":
        if not isinstance(document_input, str):
            raise TypeError("Pro input_type='text' musí být vstupní dokument řetězec.")

        # Předzpracování textu
        text = document_input.strip() # Odstranění úvodních/koncových bílých znaků
        text = re.sub(r'\r\n', '\n', text) # Nahradí Windows konce řádků (CRLF) Unixovými (LF)
        text = re.sub(r'\r', '\n', text)   # Nahradí staré Mac konce řádků (CR) Unixovými (LF)
        text = re.sub(r'[ \t]+', ' ', text) # Nahradí vícenásobné mezery nebo tabulátory jednou mezerou
        text = text.lower() # Převod na malá písmena

        extracted_text = text
        processed_text = f"[TEXTOVÁ EXTRAKCE]:\n{extracted_text}"
        print(f"DEBUG: Výsledek textové extrakce: '{processed_text[:100]}...'")
        return processed_text

    elif input_type == "image_path":
        if not isinstance(document_input, str):
            raise TypeError("Pro input_type='image_path' musí být vstupní dokument cesta k souboru (řetězec).")

        if not os.path.exists(document_input):
            print(f"CHYBA: Soubor nenalezen na cestě: {document_input}")
            return f"[CHYBA OCR]: Soubor nenalezen: {document_input}"

        try:
            print(f"DEBUG: Pokus o OCR zpracování obrázku: {document_input}")
            text_from_image = pytesseract.image_to_string(Image.open(document_input), lang=lang)
            processed_text = f"[OCR EXTRAKCE ({lang})]:\n{text_from_image.strip()}"
            print(f"DEBUG: Výsledek OCR extrakce: '{processed_text[:100]}...'")
            return processed_text
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
    sample_text = "  Toto  je   VZOROVÝ text  \r\n  pro  Testování.  \r\r   Konec.  "
    print(f"Původní text:\n'{sample_text}'\n") # Přidány apostrofy pro jasné zobrazení mezer
    extracted_direct = extract_text_from_document(sample_text, input_type="text")
    print(f"Extrahovaný text (přímý vstup):\n{extracted_direct}\n")

    # Vytvoření testovacího obrázku pomocí ImageMagick
    test_image_path = "test_ocr_image.png"
    # Použijeme text v češtině a angličtině pro test obou jazykových modelů
    test_text_for_image = "Test OCR 123 ČESKY"
    # Příkaz pro vytvoření obrázku s textem
    # convert -size 300x50 xc:white -font Arial -pointsize 20 -fill black -gravity center -draw "text 0,0 'Test OCR 123 ČESKY'" test_ocr_image.png
    # Tento příkaz je složitější na správné escapování v subtasku, použijeme jednodušší
    os.system(f"convert -size 200x50 xc:lightblue -font DejaVu-Sans -pointsize 20 -fill black -gravity center -draw \"text 0,0 '{test_text_for_image}'\" {test_image_path}")

    if os.path.exists(test_image_path):
        print(f"Testovací obrázek '{test_image_path}' byl vytvořen.")
        print(f"Test OCR zpracování obrázku: {test_image_path}")
        # Test s češtinou a angličtinou
        extracted_ocr_cs_en = extract_text_from_document(test_image_path, input_type="image_path", lang='ces+eng')
        print(f"Výsledek OCR extrakce (ces+eng):\n{extracted_ocr_cs_en}\n")

        # Test pouze s angličtinou (pokud by český text nebyl rozpoznán)
        extracted_ocr_eng = extract_text_from_document(test_image_path, input_type="image_path", lang='eng')
        print(f"Výsledek OCR extrakce (eng):\n{extracted_ocr_eng}\n")

        # Test pouze s češtinou
        extracted_ocr_ces = extract_text_from_document(test_image_path, input_type="image_path", lang='ces')
        print(f"Výsledek OCR extrakce (ces):\n{extracted_ocr_ces}\n")

        os.remove(test_image_path) # Uklidíme po sobě
    else:
        print(f"CHYBA: Testovací obrázek '{test_image_path}' se nepodařilo vytvořit.")

    non_existent_image_path = "cesta/k/neexistujicimu/obrazku.png"
    print(f"Test s neexistujícím obrázkem: {non_existent_image_path}")
    extracted_non_existent = extract_text_from_document(non_existent_image_path, input_type="image_path")
    print(f"Výsledek pro neexistující obrázek:\n{extracted_non_existent}\n")
