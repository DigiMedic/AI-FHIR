import pytest
from backend import fhir_mapper # Assuming fhir_mapper is importable this way
from datetime import datetime

# --- Testy pro parse_date_to_fhir_format ---
@pytest.mark.parametrize("date_input, expected_output", [
    ("25.12.2023", "2023-12-25"),
    ("1. ledna 1990", "1990-01-01"),
    ("15 července 2005", "2005-07-15"), # červenec without genitive 'a'
    ("2023-03-15", "2023-03-15"),
    ("5. srpna 1975", "1975-08-05"),
    ("12/05/2001", "2001-05-12"),
    ("10 10 2010", "2010-10-10"),
    ("1.1.2020", "2020-01-01"),
    ("03.04.1995", "1995-04-03"),
    ("7 lis 1980", "1980-11-07"), # Zkratka měsíce
    ("7. lis. 1980", "1980-11-07"), # Zkratka měsíce s tečkou
    ("  8.  prosince  1999  ", "1999-12-08"), # Extra mezery
])
def test_parse_date_to_fhir_format_valid(date_input, expected_output):
    assert fhir_mapper.parse_date_to_fhir_format(date_input) == expected_output

@pytest.mark.parametrize("date_input", [
    "30. února 2023",
    "random text",
    "1.13.2023", # Neplatný měsíc
    "32.01.2023", # Neplatný den
    "10. října", # Chybí rok
    "", # Prázdný vstup
    None, # None vstup
    "1990", # Pouze rok
])
def test_parse_date_to_fhir_format_invalid(date_input):
    assert fhir_mapper.parse_date_to_fhir_format(date_input) is None

# --- Testy pro extract_info_from_birth_number ---
@pytest.mark.parametrize("rc_input, expected_dict", [
    ("8001011234", {'year': 1980, 'month': 1, 'day': 1, 'gender_code': 'male'}),
    ("8051011234", {'year': 1980, 'month': 1, 'day': 1, 'gender_code': 'female'}),
    ("0501011234", {'year': 2005, 'month': 1, 'day': 1, 'gender_code': 'male'}), # Předpoklad formátu do 2003
    ("0551011234", {'year': 2005, 'month': 1, 'day': 1, 'gender_code': 'female'}),# Předpoklad formátu do 2003
    ("0421011234", {'year': 2004, 'month': 1, 'day': 1, 'gender_code': 'male'}), # Formát po 2003 (měsíc +20)
    ("0471011234", {'year': 2004, 'month': 1, 'day': 1, 'gender_code': 'female'}),# Formát po 2003 (měsíc +70)
    ("531231123", {'year': 1953, 'month': 12, 'day': 31, 'gender_code': 'male'}), # 9místné
    ("536231123", {'year': 1953, 'month': 12, 'day': 31, 'gender_code': 'female'}), # 9místné
])
def test_extract_info_from_birth_number_valid(rc_input, expected_dict):
    assert fhir_mapper.extract_info_from_birth_number(rc_input) == expected_dict

@pytest.mark.parametrize("rc_input", [
    "8013011234", # Neplatný měsíc
    "8002301234", # Neplatný den (30.února)
    "12345",      # Příliš krátké
    "12345678901",# Příliš dlouhé
    "800101123A", # Nečíselné
    "0063001234", # Neplatný měsíc pro ženu (rok 2000, ale měsíc 63-50=13)
])
def test_extract_info_from_birth_number_invalid(rc_input):
    assert fhir_mapper.extract_info_from_birth_number(rc_input) is None

# --- Testy pro is_valid_birth_number ---
@pytest.mark.parametrize("rc_input, expected_validity", [
    # Valid RČs that SHOULD pass modulo 11 (format pre-2004)
    ("540101/0081", True),  # 1954-01-01, male, 5401010081 % 11 == 0
    ("5401010081", True),   # Same without slash
    ("545101/0084", True),  # 1954-01-01, female, 5451010084 % 11 == 0
    # Valid RČs where modulo 11 does not apply or is not the sole criteria
    ("530101/123", True),   # Valid 9-digit, 1953 (mod 11 not applicable for validity)
    ("042101/1234", True),  # Valid, male, 2004 (new format, mod 11 not applicable for validity)
    ("047101/1234", True),  # Valid, female, 2004 (new format, mod 11 not applicable for validity)
    # Invalid RČs due to modulo 11 (format pre-2004 where it applies)
    ("800101/1234", False), # 1980, 8001011234 % 11 != 0
    ("805101/1234", False), # 1980, 8051011234 % 11 != 0
    ("750320/1234", False), # 1975, 7503201234 % 11 != 0
    ("555101/9876", False), # 1955, 5551019876 % 11 != 0
    ("540101/1235", False), # Rok 1954, 5401011235 % 11 != 0
    # Other invalid RČs
    ("12345/123", False),   # Krátké
    ("800101/123A", False), # Nečíselné
    ("801301/1234", False), # Neplatné datum v RČ (měsíc)
])
def test_is_valid_birth_number_logic(rc_input, expected_validity):
    assert fhir_mapper.is_valid_birth_number(rc_input) == expected_validity

# --- Testy pro FHIR resource creation s capsys ---
def test_create_fhir_patient_valid():
    patient_data = {
        "full_name": "Jana Nováková",
        "birth_date_fhir": "1954-01-01", # Matches the valid RČ below
        "birth_number_raw": "545101/0084" # Valid RČ: 1954-01-01, female, 5451010084 % 11 == 0
    }
    resource = fhir_mapper.create_fhir_patient_resource(patient_data)
    assert resource is not None
    assert resource["resourceType"] == "Patient"
    assert resource["birthDate"] == "1954-01-01"
    assert resource["name"][0]["text"] == "Jana Nováková"
    assert resource["gender"] == "female"
    assert resource["identifier"][0]["value"] == "5451010084"

def test_create_fhir_patient_rc_date_mismatch(capsys):
    patient_data = {
        "full_name": "Petr Dvořák",
        "birth_date_fhir": "1954-01-02", # Different from RČ date
        "birth_number_raw": "540101/0081" # Valid RČ: 1954-01-01, male, 5401010081 % 11 == 0
    }
    fhir_mapper.create_fhir_patient_resource(patient_data)
    captured = capsys.readouterr()
    assert "VAROVÁNÍ [FHIR Mapper]: Nesoulad mezi datem narození z RČ (1.1.1954) a zadaným datem narození (1954-01-02)." in captured.out

def test_create_fhir_observation_bp_out_of_range(capsys):
        # Test systolic out of range
        bp_data_systolic_high = {"blood_pressure_value": "350/80"}
        fhir_mapper.create_fhir_observation_bp_resource(bp_data_systolic_high, "Patient/test-patient-id-sys")
        captured_systolic = capsys.readouterr()
        assert "VAROVÁNÍ [FHIR Mapper]: Hodnota Systolický krevní tlak (350 mmHg) je mimo očekávaný fyziologický rozsah (50-300 mmHg)." in captured_systolic.out

        # Test diastolic out of range (high)
        bp_data_diastolic_high = {"blood_pressure_value": "120/210"}
        fhir_mapper.create_fhir_observation_bp_resource(bp_data_diastolic_high, "Patient/test-patient-id-dia-high")
        captured_diastolic_high = capsys.readouterr()
        assert "VAROVÁNÍ [FHIR Mapper]: Hodnota Diastolický krevní tlak (210 mmHg) je mimo očekávaný fyziologický rozsah (30-200 mmHg)." in captured_diastolic_high.out

        # Test diastolic out of range (low)
        bp_data_diastolic_low = {"blood_pressure_value": "120/20"}
        fhir_mapper.create_fhir_observation_bp_resource(bp_data_diastolic_low, "Patient/test-patient-id-dia-low")
        captured_diastolic_low = capsys.readouterr()
        assert "VAROVÁNÍ [FHIR Mapper]: Hodnota Diastolický krevní tlak (20 mmHg) je mimo očekávaný fyziologický rozsah (30-200 mmHg)." in captured_diastolic_low.out

        # Test value 200 (should be IN range, no warning for 200 specifically)
        bp_data_diastolic_edge = {"blood_pressure_value": "160/200"}
        fhir_mapper.create_fhir_observation_bp_resource(bp_data_diastolic_edge, "Patient/test-patient-id-dia-edge")
        captured_diastolic_edge = capsys.readouterr()
        assert "VAROVÁNÍ [FHIR Mapper]: Hodnota Diastolický krevní tlak (200 mmHg) je mimo očekávaný fyziologický rozsah (30-200 mmHg)." not in captured_diastolic_edge.out


def test_create_fhir_observation_pulse_out_of_range(capsys):
    pulse_data = {"pulse_value": "10"} # Příliš nízký pulz
    fhir_mapper.create_fhir_observation_pulse_resource(pulse_data, "Patient/test-patient-id")
    captured = capsys.readouterr()
    assert "VAROVÁNÍ [FHIR Mapper]: Hodnota Pulz (10 /min) je mimo očekávaný fyziologický rozsah (20-300 /min)." in captured.out

    pulse_data_high = {"pulse_value": "350"} # Příliš vysoký pulz
    fhir_mapper.create_fhir_observation_pulse_resource(pulse_data_high, "Patient/test-patient-id")
    captured_high = capsys.readouterr()
    assert "VAROVÁNÍ [FHIR Mapper]: Hodnota Pulz (350 /min) je mimo očekávaný fyziologický rozsah (20-300 /min)." in captured_high.out

# --- Test pro map_text_to_fhir (základní) ---
def test_map_text_to_fhir_basic_with_validation_capture(capsys):
    sample_text = """
    Pacient: Testovací Pacient
    Nar.: 10.10.1990
    RČ: 901010/1234
    ---
    TK: 120/80 mmHg
    Pulz: 350/min  // Out of range pulse
    Teplota: 36.5 C
    ---
    Diagnóza: Testovací diagnóza.
    """
    # Using original_text=sample_text for the non-NLP path or when NLP entities are not provided
    fhir_resources = fhir_mapper.map_text_to_fhir(sample_text, original_text=sample_text)

    assert len(fhir_resources) > 0 # Očekáváme nějaké zdroje

    patient_found = any(res["resourceType"] == "Patient" for res in fhir_resources)
    assert patient_found

    bp_observation_found = any(
        res["resourceType"] == "Observation" and
        res["code"]["text"] == "Krevní tlak" for res in fhir_resources
    )
    assert bp_observation_found

    pulse_observation_found = any(
        res["resourceType"] == "Observation" and
        res["code"]["text"] == "Pulz" for res in fhir_resources
    )
    assert pulse_observation_found

    condition_found = any(res["resourceType"] == "Condition" for res in fhir_resources)
    assert condition_found

    captured = capsys.readouterr()
    # Check for the specific out-of-range warning for pulse
    assert "VAROVÁNÍ [FHIR Mapper]: Hodnota Pulz (350 /min) je mimo očekávaný fyziologický rozsah (20-300 /min)." in captured.out
    # Check that RČ and birth date match (no warning should be present for mismatch)
    assert "Nesoulad mezi datem narození z RČ" not in captured.out


# --- Testy pro extract_value_and_unit_from_nlp_entity_text ---
@pytest.mark.parametrize("entity_text, surrounding_text, unit_regex_map, default_unit, expected_value, expected_unit", [
    ("75", "/min", {"/min": r"/min|tepů/min"}, None, "75", "/min"),
    ("36,5", "°C", {"°C": r"°C|C"}, None, "36.5", "°C"),
    ("180", "cm", {"cm": r"cm"}, None, "180", "cm"),
    ("Hmotnost 85.2", "kg", {"kg": r"kg"}, None, "85.2", "kg"), # Hodnota na konci entity
    ("cca 90", " kg", {"kg": r"kg"}, None, "90", "kg"), # Jednotka v surrounding_text
    ("Váha: 70.5", "", {"kg": r"kg"}, "kg", "70.5", "kg"), # Default unit
    ("40", " tepů za minutu", {"/min": r"tepů/min|/min"}, None, "40", "/min"), # Složitější jednotka
    ("Pulz je 60", "", {"/min": r"/min"}, "/min", "60", "/min"), # Jednotka chybí, použije se default
    ("Teplota 37", " stupňů Celsia", {"°C": r"stupňů Celsia|°C"}, None, "37", "°C"),
    # Případy, kdy jednotka je součástí entity_text
    ("72/min", "", {"/min": r"/min|tepů/min"}, None, "72", "/min"),
    ("38.2°C", " další text", {"°C": r"°C|C"}, None, "38.2", "°C"),
    ("175cm", " a něco", {"cm": r"cm"}, None, "175", "cm"),
    ("100kg", "", {"kg": r"kg"}, None, "100", "kg"),
    # Neúspěšné extrakce
    ("žádné číslo", "jednotka", {"jednotka": r"jednotka"}, None, None, None),
    ("100", "neznámá jednotka", {"kg": r"kg"}, None, "100", None), # Hodnota ano, jednotka ne
    ("100", "neznámá jednotka", {"kg": r"kg"}, "kg", "100", "kg"), # Hodnota ano, jednotka ne, ale je default
    # Složitější regexy pro jednotky
    ("Puls 55 tepů/minutu", " ", {"/min": r"tep[uů](/min|/minutu)|bpm"}, "/min", "55", "/min"),
    ("Váha pacienta: 82 kg.", "", {"kg": r"kg"}, None, "82", "kg"),
])
def test_extract_value_and_unit_from_nlp_entity_text(
    entity_text, surrounding_text, unit_regex_map, default_unit, expected_value, expected_unit
):
    value, unit = fhir_mapper.extract_value_and_unit_from_nlp_entity_text(
        entity_text, surrounding_text, unit_regex_map, default_unit
    )
    assert value == expected_value
    assert unit == expected_unit

# --- Testovací třída/sada testů pro parse_observation_data (krevní tlak) s NLP ---
class TestParseObservationDataNLP:
    @pytest.mark.parametrize("test_id, text_input, nlp_entities, expected_bp_value, use_regex_fallback_expected", [
        (
            "nlp_ok_exact",
            "TK 130/80 mmHg",
            [
                {"text": "130", "type": "CARDINAL", "start_char": 3, "end_char": 6},
                {"text": "80", "type": "CARDINAL", "start_char": 7, "end_char": 9}
            ],
            "130/80",
            False
        ),
        (
            "nlp_ok_krevni_tlak",
            "Krevní tlak: 140 / 90 mmHg",
            [
                {"text": "140", "type": "NUMBER", "start_char": 13, "end_char": 16},
                {"text": "90", "type": "NUMBER", "start_char": 19, "end_char": 21}
            ],
            "140/90",
            False
        ),
        (
            "nlp_one_entity_fallback_regex", # NLP najde jen jedno číslo, měl by následovat regex fallback
            "TK 150 a nějaký další text 150/95 mmHg", # Globální regex najde 150/95
            [
                {"text": "150", "type": "CARDINAL", "start_char": 3, "end_char": 6}
                # Chybí druhá entita pro diastolický tlak blízko TK
            ],
            "150/95", # Očekáváme hodnotu z regexu
            True
        ),
        (
            "nlp_entities_far_fallback_regex", # NLP entity jsou příliš daleko od klíčového slova
            "TK je v normě. Později naměřeno 120/70.",
            [
                {"text": "120", "type": "CARDINAL", "start_char": 30, "end_char": 33},
                {"text": "70", "type": "CARDINAL", "start_char": 34, "end_char": 36}
            ],
            "120/70", # Očekáváme hodnotu z regexu, protože NLP entity nejsou v okně za "TK"
            True
        ),
        (
            "no_nlp_entities_fallback_regex",
            "Tlak krve: 160/100",
            [], # Žádné NLP entity
            "160/100",
            True
        ),
         (
            "nlp_values_with_text_inside",
            "TK: cca 125 / skoro 75 mmHg",
            [
                {"text": "cca 125", "type": "NUMBER", "start_char": 8, "end_char": 15}, # "TK: cca " je 8 znaků
                {"text": "skoro 75", "type": "NUMBER", "start_char": 18, "end_char": 26}
            ],
            "125/75",
            False
        ),
    ])
    def test_parse_blood_pressure_nlp_and_fallback(self, test_id, text_input, nlp_entities, expected_bp_value, use_regex_fallback_expected, capsys):
        # Přidáme nlp_entities do text_input pro úplnost, i když je mockujeme
        # Je důležité, aby start_char a end_char odpovídaly text_input

        result = fhir_mapper.parse_observation_data(nlp_entities, text_input)

        if expected_bp_value:
            assert result.get("blood_pressure_value") == expected_bp_value
            assert result.get("measurement_time_fhir") is not None
        else:
            assert result.get("blood_pressure_value") is None

        captured = capsys.readouterr()
        if use_regex_fallback_expected:
            assert "Nalezen krevní tlak (Regex fallback)" in captured.out or \
                   "Krevní tlak nenalezen ani pomocí NLP, ani pomocí Regex" in captured.out
        else:
            assert "Nalezen krevní tlak (NLP)" in captured.out
            assert "Nalezen krevní tlak (Regex fallback)" not in captured.out


# --- Testovací třída/sada testů pro parse_vital_signs_data s NLP ---
class TestParseVitalSignsDataNLP:
    # Testy pro PULZ
    @pytest.mark.parametrize("test_id, text_input, nlp_entities, expected_value, expected_unit, log_check", [
        ("pulse_nlp_direct", "Pulz: 75/min.", [{"text": "75/min", "type": "CARDINAL", "start_char": 6, "end_char": 12}], "75", "/min", "Nalezen Pulz (NLP)"),
        ("pulse_nlp_separate_unit", "SF 80 tepů/min", [{"text": "80", "type": "NUMBER", "start_char": 3, "end_char": 5}], "80", "/min", "Nalezen Pulz (NLP)"),
        ("pulse_nlp_context_regex", "P: 90, ale divně", [{"text": "90", "type": "CARDINAL", "start_char": 3, "end_char": 5}], "90", "/min", "Nalezen Pulz (Kontextový Regex fallback)"), # Předpoklad: '/min' není v okolí pro NLP, ale regex to chytí
        ("pulse_global_regex", "Srdeční akce byla 65 /min.", [], "65", "/min", "Nalezen Pulz (Globální Regex fallback)"),
        ("pulse_no_value", "Pulz: není", [], None, None, "Pulz nenalezen"),
        ("pulse_nlp_entity_no_unit_finds_default", "Puls 120", [{"text": "120", "type": "CARDINAL", "start_char": 5, "end_char": 8}], "120", "/min", "Nalezen Pulz (NLP)"), # default /min
    ])
    def test_parse_pulse_nlp(self, test_id, text_input, nlp_entities, expected_value, expected_unit, log_check, capsys):
        result = fhir_mapper.parse_vital_signs_data(nlp_entities, text_input)
        assert result.get("pulse_value") == expected_value
        assert result.get("pulse_unit") == expected_unit
        if log_check:
            captured = capsys.readouterr()
            assert log_check in captured.out

    # Testy pro TEPLOTU
    @pytest.mark.parametrize("test_id, text_input, nlp_entities, expected_value, expected_unit, log_check", [
        ("temp_nlp_direct", "Teplota: 37,5°C", [{"text": "37,5°C", "type": "NUMBER", "start_char": 9, "end_char": 15}], "37.5", "°C", "Nalezena Teplota (NLP)"),
        ("temp_nlp_separate_unit", "T 36.8 stupňů C", [{"text": "36.8", "type": "CARDINAL", "start_char": 2, "end_char": 6}], "36.8", "°C", "Nalezena Teplota (NLP)"),
        ("temp_nlp_context_regex", "Teplota naměřena 37 C", [{"text": "37", "type": "NUMBER", "start_char": 17, "end_char": 19}], "37", "°C", "Nalezena Teplota (Kontextový Regex fallback)"),
        ("temp_global_regex", "Pacient afebrilní, TT 36,9C.", [], "36.9", "°C", "Nalezena Teplota (Globální Regex fallback)"),
        ("temp_no_value", "Teplota: neměřena", [], None, None, "Teplota nenalezena"),
    ])
    def test_parse_temperature_nlp(self, test_id, text_input, nlp_entities, expected_value, expected_unit, log_check, capsys):
        result = fhir_mapper.parse_vital_signs_data(nlp_entities, text_input)
        assert result.get("temperature_value") == expected_value
        assert result.get("temperature_unit") == expected_unit
        if log_check:
            captured = capsys.readouterr()
            assert log_check in captured.out

    # Testy pro VÝŠKU
    @pytest.mark.parametrize("test_id, text_input, nlp_entities, expected_value, expected_unit, log_check", [
        ("height_nlp_direct", "Výška: 180cm.", [{"text": "180cm", "type": "QUANTITY", "start_char": 7, "end_char": 12}], "180", "cm", "Nalezena Výška (NLP)"),
        ("height_nlp_separate_unit", "Výš. 175 cm", [{"text": "175", "type": "NUMBER", "start_char": 6, "end_char": 9}], "175", "cm", "Nalezena Výška (NLP)"),
        ("height_nlp_context_regex", "Výška pacienta 190cm", [{"text": "190", "type": "CARDINAL", "start_char": 16, "end_char": 19}], "190", "cm", "Nalezena Výška (Kontextový Regex fallback)"), # NLP entita je jen "190", "cm" je hned za ní
        ("height_global_regex", "Měří asi 165 cm.", [], "165", "cm", "Nalezena Výška (Globální Regex fallback)"),
        ("height_no_value", "Výška: neuvedena", [], None, None, "Výška nenalezena"),
    ])
    def test_parse_height_nlp(self, test_id, text_input, nlp_entities, expected_value, expected_unit, log_check, capsys):
        result = fhir_mapper.parse_vital_signs_data(nlp_entities, text_input)
        assert result.get("height_value") == expected_value
        assert result.get("height_unit") == expected_unit
        if log_check:
            captured = capsys.readouterr()
            assert log_check in captured.out

    # Testy pro HMOTNOST
    @pytest.mark.parametrize("test_id, text_input, nlp_entities, expected_value, expected_unit, log_check", [
        ("weight_nlp_direct", "Hmotnost: 75.5kg", [{"text": "75.5kg", "type": "QUANTITY", "start_char": 10, "end_char": 16}], "75.5", "kg", "Nalezena Hmotnost (NLP)"),
        ("weight_nlp_separate_unit", "Hm. 82 kg.", [{"text": "82", "type": "NUMBER", "start_char": 4, "end_char": 6}], "82", "kg", "Nalezena Hmotnost (NLP)"),
        ("weight_nlp_context_regex", "Váha aktuálně 91 kg", [{"text": "91", "type": "CARDINAL", "start_char": 14, "end_char": 16}], "91", "kg", "Nalezena Hmotnost (Kontextový Regex fallback)"),
        ("weight_global_regex", "Pacient váží 68kg.", [], "68", "kg", "Nalezena Hmotnost (Globální Regex fallback)"),
        ("weight_no_value", "Hmotnost: neznámá", [], None, None, "Hmotnost nenalezena"),
    ])
    def test_parse_weight_nlp(self, test_id, text_input, nlp_entities, expected_value, expected_unit, log_check, capsys):
        result = fhir_mapper.parse_vital_signs_data(nlp_entities, text_input)
        assert result.get("weight_value") == expected_value
        assert result.get("weight_unit") == expected_unit
        if log_check:
            captured = capsys.readouterr()
            assert log_check in captured.out

# --- Testy pro vylepšené chování parse_patient_data ---
class TestParsePatientDataNLPContext:
    def test_parse_patient_name_multiple_P_entities(self, capsys):
        text_input = "Pacient: Jan Novák. Ošetřující lékař: MUDr. Petr Svoboda."
        # Lékař je také typu 'P', ale dále od klíčového slova "Pacient:"
        nlp_entities = [
            {"text": "Jan Novák", "type": "P", "start_char": 9, "end_char": 18}, # Pacient
            {"text": "MUDr. Petr Svoboda", "type": "P", "start_char": 42, "end_char": 60} # Lékař
        ]
        expected_name = "Jan Novák"

        result = fhir_mapper.parse_patient_data(nlp_entities, text_input)
        assert result.get("full_name") == expected_name
        captured = capsys.readouterr()
        assert f"Vybrána entita 'P' '{expected_name}' na základě blízkosti ke klíčovému slovu." in captured.out

    def test_parse_birth_date_multiple_T_entities(self, capsys):
        text_input = "Datum narození: 1.1.1990. Datum vyšetření: 15.3.2023."
        nlp_entities = [
            {"text": "1.1.1990", "type": "DATE", "start_char": 16, "end_char": 24}, # Datum narození
            {"text": "15.3.2023", "type": "DATE", "start_char": 44, "end_char": 53}  # Datum vyšetření
        ]
        expected_date_fhir = "1990-01-01"
        expected_date_raw = "1.1.1990"

        result = fhir_mapper.parse_patient_data(nlp_entities, text_input)
        assert result.get("birth_date_fhir") == expected_date_fhir
        assert result.get("birth_date_raw") == expected_date_raw
        captured = capsys.readouterr()
        assert f"Vybrána NLP entita data narození '{expected_date_raw}'" in captured.out
        assert f"Nalezeno datum narození (NLP): {expected_date_raw} -> {expected_date_fhir}" in captured.out

# --- Testy pro vylepšené chování parse_condition_data ---
class TestParseConditionDataNLPContext:
    def test_parse_condition_multiple_DIS_entities_merged(self, capsys):
        text_input = "Diagnóza: Diabetes mellitus, ICHS. Další diagnóza: Hypertenze."
        # NLP entity pro "Diabetes mellitus" a "ICHS" jsou blízko a měly by se spojit
        nlp_entities = [
            {"text": "Diabetes mellitus", "type": "DIS", "start_char": 10, "end_char": 27},
            {"text": "ICHS", "type": "DIS", "start_char": 29, "end_char": 33}, # Navazuje po ", "
            {"text": "Hypertenze", "type": "DIS", "start_char": 53, "end_char": 63} # Dále
        ]
        expected_diagnosis = "Diabetes mellitus, ICHS"

        result = fhir_mapper.parse_condition_data(nlp_entities, text_input)
        assert result.get("diagnosis_text") == expected_diagnosis
        captured = capsys.readouterr()
        assert "Spojuji DIS entitu 'Diabetes mellitus' s 'ICHS'" in captured.out
        assert f"Nalezena diagnóza (NLP, spojené/rozšířené DIS): '{expected_diagnosis}'" in captured.out

    def test_parse_condition_dis_experimental_extension(self, capsys):
        text_input = "Závěr: Infekce horních cest dýchacích." # Tečka je součástí
        nlp_entities = [
            # NLP entita končí před tečkou
            {"text": "Infekce horních cest dýchacích", "type": "DIS", "start_char": 7, "end_char": 37}
        ]
        # Očekáváme, že experimentální rozšíření přidá tečku
        expected_diagnosis = "Infekce horních cest dýchacích."

        result = fhir_mapper.parse_condition_data(nlp_entities, text_input)
        assert result.get("diagnosis_text") == expected_diagnosis
        captured = capsys.readouterr()
        assert f"Experimentální rozšíření textu diagnózy na: '{expected_diagnosis}'" in captured.out

    def test_parse_condition_single_dis_no_merge_needed(self, capsys):
        text_input = "Dg.: Hypertenze esenciální."
        nlp_entities = [
            {"text": "Hypertenze esenciální", "type": "DIS", "start_char": 5, "end_char": 26}
        ]
        expected_diagnosis = "Hypertenze esenciální" # Tečka je odstraněna finálním čištěním

        result = fhir_mapper.parse_condition_data(nlp_entities, text_input)
        assert result.get("diagnosis_text") == expected_diagnosis
        captured = capsys.readouterr()
        # Očekáváme log pro jednu DIS entitu, ne pro spojování
        assert "Nalezena diagnóza (NLP, jedna DIS entita)" in captured.out
        assert "Spojuji DIS entitu" not in captured.out
