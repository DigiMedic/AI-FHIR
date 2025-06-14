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
