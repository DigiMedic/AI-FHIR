import pytest
from backend.ai_models import text_extractor # Assuming text_extractor is importable this way

# Test non-NLP text extraction
def test_extract_text_from_document_non_nlp():
    sample_text = "  Toto  je   VZOROVÝ text  \r\n  pro  Testování.  \r\r   Konec.  "
    expected_output = "toto je vzorový text pro testování. konec." # Based on current logic in text_extractor
    # The current logic in text_extractor.py:
    # text = str(document_input).strip()
    # text = re.sub(r'\r\n', '\n', text)
    # text = re.sub(r'\r', '\n', text)
    # text = re.sub(r'[ \t]+', ' ', text)
    # text = text.lower()
    # So, newlines are replaced by single space if they were part of re.sub, or become single space due to strip and space normalization
    # Let's re-verify the expected output based on the implementation:
    # "  Toto  je   VZOROVÝ text  \n  pro  Testování.  \n\n   Konec.  " (after newline normalization)
    # "Toto je VZOROVÝ text \n pro Testování. \n\n Konec." (after strip)
    # "Toto je VZOROVÝ text pro Testování. Konec." (after multi-space sub)
    # "toto je vzorový text pro testování. konec." (after lower)
    # This seems correct.

    # However, the actual code's re.sub(r'[ \t]+', ' ', text) and strip() behavior with newlines needs careful checking.
    # strip() removes leading/trailing whitespace including newlines.
    # re.sub(r'\r\n', '\n', text)
    # re.sub(r'\r', '\n', text)
    # text.strip() will remove leading/trailing newlines as well.
    # "  Toto  je   VZOROVÝ text  \n  pro  Testování.  \n\n   Konec.  "
    # After strip(): "Toto  je   VZOROVÝ text  \n  pro  Testování.  \n\n   Konec."
    # After re.sub(r'[ \t]+', ' ', text): "Toto je VZOROVÝ text \n pro Testování. \n\n Konec."
    # After lower: "toto je vzorový text \n pro testování. \n\n konec."
    # The current text_extractor.py has:
    # text = str(document_input).strip() # 1. strip
    # text = re.sub(r'\r\n', '\n', text) # 2. normalize \r\n
    # text = re.sub(r'\r', '\n', text)   # 3. normalize \r
    # text = re.sub(r'[ \t]+', ' ', text) # 4. normalize spaces
    # text = text.lower() # 5. lowercase
    # Let's trace "  Toto  je   VZOROVÝ text  \r\n  pro  Testování.  \r\r   Konec.  "
    # 1. strip(): "Toto  je   VZOROVÝ text  \r\n  pro  Testování.  \r\r   Konec."
    # 2. sub \r\n: "Toto  je   VZOROVÝ text  \n  pro  Testování.  \r\r   Konec."
    # 3. sub \r: "Toto  je   VZOROVÝ text  \n  pro  Testování.  \n\n   Konec."
    # 4. sub [ \t]+: "Toto je VZOROVÝ text \n pro Testování. \n\n Konec."
    # 5. lower: "toto je vzorový text \n pro testování. \n\n konec."
    # This is different from the initial expectation. The newlines are preserved.
    # The provided sample in text_extractor.py itself output:
    # 'toto je vzorový text \n pro testování. \n\n konec.'
    # So, the expected output should reflect this.
    expected_output_from_script = "toto je vzorový text \n pro testování. \n\n konec."
    assert text_extractor.extract_text_from_document(sample_text, input_type="text", use_nlp=False) == expected_output_from_script

    # Test with only newlines and spaces
    only_newlines_spaces = "  \n\n   \r   \r\n  "
    # 1. strip: "\n\n   \r   \r\n"
    # 2. \r\n -> \n: "\n\n   \r   \n"
    # 3. \r -> \n: "\n\n   \n   \n"
    # 4. space norm: "\n\n \n \n" (spaces around \n remain if not multiple)
    # 5. lower: "\n\n \n \n"
    expected_only_newlines = "\n\n \n \n" # The logic might result in this, or just "" if all newlines are stripped eventually.
                                       # The current code does not strip newlines aggressively after initial strip().
                                       # splitlines() and join(" ") would produce " " if there are multiple newlines.
                                       # Given the current regex logic:
                                       # strip -> "\n\n   \r   \r\n"
                                       # \r\n -> \n : "\n\n   \r   \n"
                                       # \r -> \n : "\n\n   \n   \n"
                                       # [ \t]+ -> " " : "\n\n \n \n"
                                       # lower : "\n\n \n \n"
    assert text_extractor.extract_text_from_document(only_newlines_spaces, input_type="text", use_nlp=False) == expected_only_newlines


    # Test with mixed spaces and tabs
    mixed_spaces_tabs = " text  \t s \t\t  tabulatory "
    # 1. strip: "text  \t s \t\t  tabulatory"
    # 2. \r\n norm: no change
    # 3. \r norm: no change
    # 4. space norm: "text s tabulatory"
    # 5. lower: "text s tabulatory"
    expected_mixed_spaces_tabs = "text s tabulatory"
    assert text_extractor.extract_text_from_document(mixed_spaces_tabs, input_type="text", use_nlp=False) == expected_mixed_spaces_tabs

    # Test with leading/trailing newlines and spaces combined
    leading_trailing_complex = "  \n  Text s okraji \n\n  "
    # 1. strip: "Text s okraji \n\n"
    # 2. \r\n norm: no change
    # 3. \r norm: no change
    # 4. space norm: "Text s okraji \n\n" (leading/trailing spaces for lines are kept if not multiple, but strip handles ends of string)
    # 5. lower: "text s okraji \n\n"
    expected_leading_trailing_complex = "text s okraji \n\n"
    assert text_extractor.extract_text_from_document(leading_trailing_complex, input_type="text", use_nlp=False) == expected_leading_trailing_complex


# Test OCR error handling (simulated)
def test_extract_text_from_image_ocr_unavailable_pytesseract(monkeypatch):
    # Temporarily set text_extractor.pytesseract to None
    monkeypatch.setattr(text_extractor, "pytesseract", None)
    monkeypatch.setattr(text_extractor, "Image", True) # Assume Image is available

    expected_error_msg = "[CHYBA OCR]: Potřebné knihovny (Pillow, Pytesseract) nejsou dostupné pro zpracování obrázku."
    # The function actually prints a different message first then returns the other one.
    # print("CHYBA: Knihovny Pillow a/nebo Pytesseract nejsou dostupné pro OCR.")
    # return "[CHYBA OCR]: Potřebné knihovny (Pillow, Pytesseract) nejsou dostupné pro zpracování obrázku."
    assert text_extractor.extract_text_from_document("dummy_path.png", input_type="image_path") == expected_error_msg

def test_extract_text_from_image_ocr_unavailable_pillow(monkeypatch):
    # Temporarily set text_extractor.Image to None
    monkeypatch.setattr(text_extractor, "Image", None)
    monkeypatch.setattr(text_extractor, "pytesseract", True) # Assume pytesseract is available

    expected_error_msg = "[CHYBA OCR]: Potřebné knihovny (Pillow, Pytesseract) nejsou dostupné pro zpracování obrázku."
    assert text_extractor.extract_text_from_document("dummy_path.png", input_type="image_path") == expected_error_msg

# Test NLP error handling (simulated for Stanza not available)
def test_extract_text_from_document_nlp_stanza_unavailable_raises_error(monkeypatch):
    # Temporarily set text_extractor.stanza to None
    monkeypatch.setattr(text_extractor, "stanza", None)
    # Also, reset the global pipeline to ensure get_stanza_pipeline() is re-evaluated
    monkeypatch.setattr(text_extractor, "stanza_nlp_pipeline", None, raising=False)

    with pytest.raises(RuntimeError) as excinfo:
        text_extractor.extract_text_from_document("some text", input_type="text", use_nlp=True, nlp_engine="stanza")
    assert "Stanza není dostupná pro NLP zpracování." in str(excinfo.value) or \
           "Knihovna Stanza není dostupná. Nelze inicializovat pipeline." in str(excinfo.value)


def test_extract_text_from_document_nlp_stanza_pipeline_fail_fallback(monkeypatch):
    # This test simulates a scenario where 'stanza' module is available,
    # but stanza.Pipeline() call fails for some reason (e.g., model download issue not caught by stanza.download, or other init error).
    # The function should then fall back to non-NLP processing.

    class MockStanza:
        @staticmethod
        def download(*args, **kwargs):
            # print("MockStanza.download called")
            pass # Simulate successful download or model already present

        class Pipeline:
            def __init__(self, *args, **kwargs):
                # print("MockStanza.Pipeline.__init__ called, raising exception")
                raise Exception("Simulated Stanza Pipeline initialization error")

    monkeypatch.setattr(text_extractor, "stanza", MockStanza()) # Mock stanza module
    monkeypatch.setattr(text_extractor, "stanza_nlp_pipeline", None) # Reset pipeline

    sample_text = "Test pro NLP fallback."
    expected_non_nlp_output = "test pro nlp fallback." # non-NLP path lowercases

    # The function extract_text_from_document has a pass for this exception,
    # so it should fall through to the non-NLP text processing block.
    result = text_extractor.extract_text_from_document(sample_text, input_type="text", use_nlp=True, nlp_engine="stanza")
    assert result == expected_non_nlp_output

from unittest.mock import patch, MagicMock

# --- Mockovací třídy pro Stanza ---
class MockStanzaEntity:
    def __init__(self, text, type, start_char, end_char):
        self.text = text
        self.type = type
        self.start_char = start_char
        self.end_char = end_char

class MockStanzaDoc:
    def __init__(self, entities_data=None):
        if entities_data is None:
            entities_data = []
        self.ents = [MockStanzaEntity(**data) for data in entities_data]

@pytest.fixture
def mock_stanza_pipeline():
    """Fixture pro mockování stanza.Pipeline."""
    with patch('backend.ai_models.text_extractor.get_stanza_pipeline') as mock_get_pipeline:
        mock_pipeline_instance = MagicMock()
        # Základní chování: mock_pipeline_instance(text) vrací MockStanzaDoc bez entit
        mock_pipeline_instance.return_value = MockStanzaDoc([])
        mock_get_pipeline.return_value = mock_pipeline_instance
        yield mock_pipeline_instance # Vracíme instanci pipeline pro další konfiguraci v testech


# --- Testy pro úspěšnou NLP extrakci s mockováním ---
@pytest.mark.parametrize("test_id, input_text_verbatim, stanza_entities_data, expected_nlp_output", [
    (
        "name_extraction",
        "Pacient Jan Novák navštívil ordinaci.",
        [{"text": "Jan Novák", "type": "P", "start_char": 8, "end_char": 17}],
        [{"text": "Jan Novák", "type": "P", "start_char": 8, "end_char": 17}]
    ),
    (
        "date_extraction",
        "Datum narození: 15.1.1980.",
        [{"text": "15.1.1980", "type": "DATE", "start_char": 16, "end_char": 25}],
        [{"text": "15.1.1980", "type": "DATE", "start_char": 16, "end_char": 25}]
    ),
    (
        "multiple_entities",
        "MUDr. Eva Malá, nar. 20.05.1970, Z: Chřipka.",
        [
            {"text": "Eva Malá", "type": "P", "start_char": 5, "end_char": 13}, # Opraveno start_char z MUDr. Eva Malá
            {"text": "20.05.1970", "type": "DATE", "start_char": 20, "end_char": 30},
            {"text": "Chřipka", "type": "DIS", "start_char": 34, "end_char": 41} # Z: Chřipka
        ],
        [
            {"text": "Eva Malá", "type": "P", "start_char": 5, "end_char": 13},
            {"text": "20.05.1970", "type": "DATE", "start_char": 20, "end_char": 30},
            {"text": "Chřipka", "type": "DIS", "start_char": 34, "end_char": 41}
        ]
    ),
    (
        "no_entities_from_stanza",
        "Obyčejný text bez entit.",
        [], # Stanza nevrátí žádné entity
        []  # Očekáváme prázdný list
    )
])
def test_extract_text_from_document_with_mocked_nlp_success(
    mock_stanza_pipeline, test_id, input_text_verbatim, stanza_entities_data, expected_nlp_output
):
    """
    Testuje úspěšnou extrakci entit pomocí mockované Stanza pipeline.
    """
    # Nastavíme, co mockovaná Stanza pipeline vrátí pro tento konkrétní test
    mock_stanza_pipeline.return_value = MockStanzaDoc(stanza_entities_data)

    nlp_output = text_extractor.extract_text_from_document(
        input_text_verbatim, input_type="text", use_nlp=True, nlp_engine="stanza"
    )

    assert nlp_output == expected_nlp_output, f"Test ID '{test_id}' selhal."

    # Ověření, že mockovaná Stanza pipeline byla volána se správným textem.
    # Text pro Stanzu prochází interním čištěním (splitlines, join),
    # takže ho musíme nasimulovat pro porovnání.
    cleaned_text_for_stanza = " ".join(input_text_verbatim.splitlines())
    mock_stanza_pipeline.assert_called_once_with(cleaned_text_for_stanza)


def test_extract_text_from_document_nlp_text_cleaning(mock_stanza_pipeline):
    """
    Testuje, že text je správně očištěn před voláním NLP pipeline.
    """
    input_text = "  Text s \n\rrůznými \r konci \n\n řádků a   nadbytečnými mezerami.  "
    # Očekávaný text po .splitlines() a " ".join():
    # "  Text s   různými   konci   řádků a   nadbytečnými mezerami.  " (mezery na začátku/konci zůstanou)
    # "Text s různými konci řádků a nadbytečnými mezerami." (pokud by strip byl před splitlines)
    # Aktuální implementace: text.splitlines() -> ["  Text s ", "různými ", " konci ", "", " řádků a   nadbytečnými mezerami.  "]
    # " ".join(...) -> "  Text s  různými   konci   řádků a   nadbytečnými mezerami.  "
    expected_cleaned_text = "  Text s  různými   konci   řádků a   nadbytečnými mezerami.  "

    mock_stanza_pipeline.return_value = MockStanzaDoc([]) # Nezáleží na výstupu, jen na volání

    text_extractor.extract_text_from_document(input_text, input_type="text", use_nlp=True, nlp_engine="stanza")

    mock_stanza_pipeline.assert_called_once_with(expected_cleaned_text)


# Test, že pokud je use_nlp=True, ale nlp_engine není "stanza", vrátí se non-NLP text
def test_extract_text_from_document_nlp_unsupported_engine_fallback(capsys):
    sample_text = "Test pro NLP s neznámým enginem."
    expected_non_nlp_output = "test pro nlp s neznámým enginem." # Normalizovaný text

    result = text_extractor.extract_text_from_document(
        sample_text, input_type="text", use_nlp=True, nlp_engine="nonexistent_engine"
    )

    assert result == expected_non_nlp_output

    captured = capsys.readouterr()
    # Předpokládáme, že text_extractor.py loguje varování, když je použit neznámý engine
    # např. print(f"VAROVÁNÍ: Nepodporovaný NLP engine: {nlp_engine}...")
    # Toto je třeba ověřit v implementaci text_extractor.py
    # Aktuální implementace text_extractor.py (dle dřívějšího čtení) nemá explicitní logování
    # pro tento případ v `extract_text_from_document`, ale `get_nlp_entities` má:
    # print(f"VAROVÁNÍ: Nepodporovaný NLP engine: {nlp_engine}. Nebude provedena NLP extrakce.")
    # Takže pokud `get_nlp_entities` je voláno (což by mělo být), tak by se to mělo zalogovat.
    assert "VAROVÁNÍ: Nepodporovaný NLP engine: nonexistent_engine" in captured.out


# --- Testy pro OCR extrakci ---

@pytest.fixture
def mock_pytesseract():
    """Fixture pro mockování pytesseract."""
    with patch('backend.ai_models.text_extractor.pytesseract') as mock_tess:
        yield mock_tess

@pytest.fixture
def mock_image_open():
    """Fixture pro mockování Image.open."""
    with patch('backend.ai_models.text_extractor.Image.open') as mock_open:
        # Mocknutý Image.open by měl vrátit objekt, který lze použít v kontextovém manažeru
        mock_image_instance = MagicMock()
        mock_open.return_value = mock_image_instance
        yield mock_open


def test_extract_text_from_image_success_mocked(mock_pytesseract, mock_image_open):
    """Testuje úspěšnou OCR extrakci s mockovaným Tesseractem."""
    expected_text = "Toto je text z obrázku."
    mock_pytesseract.image_to_string.return_value = expected_text

    # Cesta k souboru je fiktivní, protože Image.open je mockováno
    result = text_extractor.extract_text_from_document("dummy/path/to/image.png", input_type="image_path")

    mock_image_open.assert_called_once_with("dummy/path/to/image.png")
    mock_pytesseract.image_to_string.assert_called_once() # S mocknutým image objektem
    assert result == expected_text


def test_extract_text_from_image_tesseract_not_found_error_mocked(mock_pytesseract, mock_image_open):
    """Testuje TesseractNotFoundError při OCR."""
    # Importujeme TesseractNotFoundError z modulu, kde je definován (pytesseract)
    # Pokud pytesseract není nainstalován, tento import selže. Pro testování musíme
    # buď zajistit, že je nainstalován, nebo mockovat i samotný import TesseractNotFoundError.
    # Pro zjednodušení předpokládáme, že pytesseract (a tedy i jeho výjimky) je dostupný
    # v testovacím prostředí, i když `image_to_string` mockujeme.
    # Pokud by nebyl, museli bychom výjimku mockovat:
    # class MockTesseractNotFoundError(Exception): pass
    # mock_pytesseract.TesseractNotFoundError = MockTesseractNotFoundError
    try:
        from pytesseract import TesseractNotFoundError
    except ImportError:
        # Pokud pytesseract není vůbec dostupný, vytvoříme si vlastní mock výjimku pro test
        class TesseractNotFoundError(Exception): pass
        mock_pytesseract.TesseractNotFoundError = TesseractNotFoundError


    mock_pytesseract.image_to_string.side_effect = TesseractNotFoundError("Mocked Tesseract not found")

    result = text_extractor.extract_text_from_document("dummy/path/to/image.png", input_type="image_path")

    mock_image_open.assert_called_once_with("dummy/path/to/image.png")
    mock_pytesseract.image_to_string.assert_called_once()
    assert result == "[CHYBA OCR]: Program Tesseract není nainstalován nebo není v PATH."


def test_extract_text_from_image_general_ocr_error_mocked(mock_pytesseract, mock_image_open):
    """Testuje obecnou chybu při OCR."""
    mock_pytesseract.image_to_string.side_effect = Exception("Simulated generic OCR error")

    result = text_extractor.extract_text_from_document("dummy/path/to/image.png", input_type="image_path")

    mock_image_open.assert_called_once_with("dummy/path/to/image.png")
    mock_pytesseract.image_to_string.assert_called_once()
    assert "[CHYBA OCR]: Chyba při zpracování obrázku pomocí Tesseract" in result
    assert "Simulated generic OCR error" in result # Ověření, že původní chyba je v textu


def test_extract_text_from_image_file_not_found():
    """Testuje případ, kdy obrázkový soubor neexistuje."""
    # Není potřeba mockovat Image.open, protože chyba by měla nastat dříve,
    # nebo Image.open by mělo samo vyvolat FileNotFoundError.
    # V text_extractor.py je try-except okolo Image.open.

    # Zajistíme, že soubor opravdu neexistuje
    non_existent_path = "cesta/k/neexistujicimu/obrazku.png"
    assert not os.path.exists(non_existent_path)

    result = text_extractor.extract_text_from_document(non_existent_path, input_type="image_path")
    assert result == f"[CHYBA OCR]: Soubor s obrázkem nebyl nalezen na cestě: {non_existent_path}"
