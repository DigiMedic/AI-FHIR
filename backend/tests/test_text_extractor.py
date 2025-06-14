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
