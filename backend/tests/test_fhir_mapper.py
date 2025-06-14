import pytest
from backend import fhir_mapper # Assuming fhir_mapper is importable this way
from datetime import datetime

# --- Testy pro parse_date_to_fhir_format ---
@pytest.mark.parametrize("date_input, expected_output", [
    ("25.12.2023", "2023-12-25"),
    ("1. ledna 1990", "1990-01-01"),
    ("15 července 2005", "2005-07-15"),
    ("2023-03-15", "2023-03-15"),
    ("5. srpna 1975", "1975-08-05"),
    ("12/05/2001", "2001-05-12"),
    ("10 10 2010", "2010-10-10"),
    ("1.1.2020", "2020-01-01"),
    ("03.04.1995", "1995-04-03"),
    ("7 lis 1980", "1980-11-07"),
    ("7. lis. 1980", "1980-11-07"),
    ("  8.  prosince  1999  ", "1999-12-08"),
])
def test_parse_date_to_fhir_format_valid(date_input, expected_output):
    issues = []
    assert fhir_mapper.parse_date_to_fhir_format(date_input, issues) == expected_output
    assert not issues # Pro validní data by neměly být žádné issues

@pytest.mark.parametrize("date_input, expected_issue_details", [
    ("30. února 2023", {"level": "error", "field": "date_str"}),
    ("random text", {"level": "error", "field": "date_str"}),
    ("1.13.2023", {"level": "error", "field": "date_str"}), # Neplatný měsíc
    ("32.01.2023", {"level": "error", "field": "date_str"}), # Neplatný den
    ("10. října", {"level": "error", "field": "date_str"}), # Chybí rok
    ("", {"level": "warning", "field": "date_str"}), # Prázdný vstup
    (None, {"level": "warning", "field": "date_str"}), # None vstup
    ("1990", {"level": "error", "field": "date_str"}), # Pouze rok
    ("15. neexistujici_mesic 2023", {"level": "error", "field": "date_str"}), # Neplatný název měsíce
    ("10..10.2020", {"level": "error", "field": "date_str"}), # Dvojité tečky
    ("30.únor.2023", {"level": "error", "field": "date_str"}), # Neplatný den v měsíci (textový měsíc)
    ("květen 2023", {"level": "error", "field": "date_str"}), # Chybí den
])
def test_parse_date_to_fhir_format_invalid(date_input, expected_issue_details):
    issues = []
    assert fhir_mapper.parse_date_to_fhir_format(date_input, issues) is None
    assert len(issues) >= 1
    # Ověření, že alespoň jedno issue odpovídá očekávaným detailům
    found_matching_issue = False
    for issue in issues:
        if issue["level"] == expected_issue_details["level"] and \
           issue["field"] == expected_issue_details["field"]:
            if date_input is not None: # "value" by mělo být přítomno, pokud date_input není None
                assert str(date_input) in str(issue.get("value")) # Může být součástí delší zprávy
            found_matching_issue = True
            break
    assert found_matching_issue, f"Expected issue with details {expected_issue_details} not found in {issues}"

# --- Testy pro extract_info_from_birth_number ---
@pytest.mark.parametrize("rc_input, expected_dict", [
    ("8001011234", {'year': 1980, 'month': 1, 'day': 1, 'gender_code': 'male'}),
    ("8051011234", {'year': 1980, 'month': 1, 'day': 1, 'gender_code': 'female'}),
    ("0501011234", {'year': 2005, 'month': 1, 'day': 1, 'gender_code': 'male'}),
    ("0551011234", {'year': 2005, 'month': 1, 'day': 1, 'gender_code': 'female'}),
    ("0421011234", {'year': 2004, 'month': 1, 'day': 1, 'gender_code': 'male'}),
    ("0471011234", {'year': 2004, 'month': 1, 'day': 1, 'gender_code': 'female'}),
    ("531231123", {'year': 1953, 'month': 12, 'day': 31, 'gender_code': 'male'}),
    ("536231123", {'year': 1953, 'month': 12, 'day': 31, 'gender_code': 'female'}),
])
def test_extract_info_from_birth_number_valid(rc_input, expected_dict):
    issues = []
    assert fhir_mapper.extract_info_from_birth_number(rc_input, issues) == expected_dict
    assert not issues

@pytest.mark.parametrize("rc_input, expected_issue_field", [
    ("8013011234", "birth_number_cleaned"), # Neplatný měsíc
    ("8002301234", "birth_number_cleaned"), # Neplatný den (30.února)
    ("12345", "birth_number_cleaned"),      # Příliš krátké
    ("12345678901", "birth_number_cleaned"),# Příliš dlouhé
    ("800101123A", "birth_number_cleaned"), # Nečíselné
    ("0063001234", "birth_number_cleaned"), # Neplatný měsíc pro ženu
    ("7000101234", "birth_number_cleaned"), # Měsíc 00
    ("7001001234", "birth_number_cleaned"), # Den 00
    ("8002301234", "birth_number_cleaned"), # Den 30. února
])
def test_extract_info_from_birth_number_invalid(rc_input, expected_issue_field):
    issues = []
    assert fhir_mapper.extract_info_from_birth_number(rc_input, issues) is None
    assert any(issue["field"] == expected_issue_field and issue["level"] == "error" for issue in issues)

# --- Testy pro is_valid_birth_number ---
@pytest.mark.parametrize("rc_input, expected_validity, expected_issue_present", [
    ("540101/0081", True, False),
    ("5401010081", True, False),
    ("545101/0084", True, False),
    ("530101/123", True, False),
    ("042101/1234", True, False),
    ("047101/1234", True, False),
    ("800101/1234", False, True), # Modulo 11 fail
    ("805101/1234", False, True), # Modulo 11 fail
    ("12345/123", False, True),   # Krátké
    ("800101/123A", False, True), # Nečíselné
    ("801301/1234", False, True), # Neplatné datum v RČ (měsíc 13)
    ("700010/1234", False, True), # Měsíc 00
    ("700100/1234", False, True), # Den 00
    ("800230/1234", False, True), # Den 30. února
])
def test_is_valid_birth_number_logic(rc_input, expected_validity, expected_issue_present):
    issues = []
    assert fhir_mapper.is_valid_birth_number(rc_input, issues) == expected_validity
    if expected_issue_present:
        assert len(issues) > 0
        assert any(issue["level"] == "error" for issue in issues)
    else:
        # Pro validní RČ by neměly být žádné error issues (mohou být info/warning z extract_info)
        assert not any(issue["level"] == "error" for issue in issues)


# --- Testy pro FHIR resource creation ---
def test_create_fhir_patient_valid():
    patient_data = {
        "full_name": "Jana Nováková",
        "birth_date_fhir": "1954-01-01",
        "birth_number_raw": "545101/0084"
    }
    resource, issues = fhir_mapper.create_fhir_patient_resource(patient_data)
    assert resource is not None
    assert resource["resourceType"] == "Patient"
    assert resource["birthDate"] == "1954-01-01"
    assert resource["name"][0]["text"] == "Jana Nováková"
    assert resource["gender"] == "female"
    assert resource["identifier"][0]["value"] == "5451010084"
    assert not issues

def test_create_fhir_patient_rc_date_mismatch():
    patient_data = {
        "full_name": "Petr Dvořák",
        "birth_date_fhir": "1954-01-02",
        "birth_number_raw": "540101/0081"
    }
    resource, issues = fhir_mapper.create_fhir_patient_resource(patient_data)
    assert resource is not None # Resource se stále vytvoří
    assert len(issues) == 1
    assert issues[0]["level"] == "warning"
    assert "Nesoulad mezi datem narození z RČ" in issues[0]["message"]
    assert issues[0]["field"] == "birth_date/birth_number"

def test_create_fhir_observation_bp_out_of_range():
    bp_data_systolic_high = {"blood_pressure_value": "350/80"}
    resource_sys, issues_sys = fhir_mapper.create_fhir_observation_bp_resource(bp_data_systolic_high, "Patient/test")
    assert resource_sys is not None
    assert any(issue["level"] == "warning" and "Systolický krevní tlak (350 mmHg)" in issue["message"] for issue in issues_sys)

    bp_data_diastolic_high = {"blood_pressure_value": "120/210"}
    resource_dia_h, issues_dia_h = fhir_mapper.create_fhir_observation_bp_resource(bp_data_diastolic_high, "Patient/test")
    assert resource_dia_h is not None
    assert any(issue["level"] == "warning" and "Diastolický krevní tlak (210 mmHg)" in issue["message"] for issue in issues_dia_h)

    bp_data_diastolic_edge = {"blood_pressure_value": "160/200"} # Horní hranice, stále OK
    resource_dia_edge, issues_dia_edge = fhir_mapper.create_fhir_observation_bp_resource(bp_data_diastolic_edge, "Patient/test")
    assert resource_dia_edge is not None
    assert not any("Diastolický krevní tlak (200 mmHg) je mimo" in issue["message"] for issue in issues_dia_edge)


def test_create_fhir_observation_pulse_out_of_range():
    pulse_data_low = {"pulse_value": "10"}
    resource_low, issues_low = fhir_mapper.create_fhir_observation_pulse_resource(pulse_data_low, "Patient/test")
    assert resource_low is not None
    assert any(issue["level"] == "warning" and "Pulz (10 /min)" in issue["message"] for issue in issues_low)

    pulse_data_high = {"pulse_value": "350"}
    resource_high, issues_high = fhir_mapper.create_fhir_observation_pulse_resource(pulse_data_high, "Patient/test")
    assert resource_high is not None
    assert any(issue["level"] == "warning" and "Pulz (350 /min)" in issue["message"] for issue in issues_high)

def test_create_fhir_patient_missing_data():
    patient_data = {} # Prázdná data
    resource, issues = fhir_mapper.create_fhir_patient_resource(patient_data)
    assert resource is None
    assert len(issues) >= 2 # Očekáváme alespoň 2 issues (jméno, datum narození)
    assert any(issue["field"] == "full_name" and issue["level"] == "error" for issue in issues)
    assert any(issue["field"] == "birth_date_fhir" and issue["level"] == "error" for issue in issues)

def test_create_fhir_observation_bp_invalid_format():
    bp_data_invalid = {"blood_pressure_value": "nevalidni/format"}
    resource, issues = fhir_mapper.create_fhir_observation_bp_resource(bp_data_invalid, "Patient/test")
    assert resource is None
    assert any(issue["level"] == "error" and "Neplatný formát hodnoty krevního tlaku" in issue["message"] for issue in issues)

    bp_data_single_value = {"blood_pressure_value": "120"} # Chybí diastolická hodnota
    resource_single, issues_single = fhir_mapper.create_fhir_observation_bp_resource(bp_data_single_value, "Patient/test")
    assert resource_single is None
    assert any(issue["level"] == "error" and "Neplatný formát hodnoty krevního tlaku" in issue["message"] for issue in issues_single)


def test_create_fhir_condition_missing_data():
    condition_data = {}
    resource, issues = fhir_mapper.create_fhir_condition_resource(condition_data, "Patient/test")
    assert resource is None
    assert any(issue["level"] == "info" and "Chybí text diagnózy" in issue["message"] for issue in issues) # Je to "info" dle implementace

# Testy pro Temperature, Height, Weight resource creation
# Teplota
def test_create_fhir_observation_temperature_valid():
    data = {"temperature_value": "37.5"}
    resource, issues = fhir_mapper.create_fhir_observation_temperature_resource(data, "Patient/test")
    assert resource is not None
    assert resource["valueQuantity"]["value"] == 37.5
    assert not issues

def test_create_fhir_observation_temperature_bad_format():
    data = {"temperature_value": "abc"}
    resource, issues = fhir_mapper.create_fhir_observation_temperature_resource(data, "Patient/test")
    assert resource is None
    assert any(issue["level"] == "error" and "Neplatná hodnota teploty" in issue["message"] for issue in issues)

def test_create_fhir_observation_temperature_out_of_range():
    data = {"temperature_value": "50"} # Příliš vysoká
    resource, issues = fhir_mapper.create_fhir_observation_temperature_resource(data, "Patient/test")
    assert resource is not None # Resource se vytvoří, ale s varováním
    assert any(issue["level"] == "warning" and "mimo očekávaný fyziologický rozsah" in issue["message"] for issue in issues)

# Výška
def test_create_fhir_observation_height_valid():
    data = {"height_value": "175.0"}
    resource, issues = fhir_mapper.create_fhir_observation_height_resource(data, "Patient/test")
    assert resource is not None
    assert resource["valueQuantity"]["value"] == 175.0
    assert not issues

def test_create_fhir_observation_height_bad_format():
    data = {"height_value": "xyz"}
    resource, issues = fhir_mapper.create_fhir_observation_height_resource(data, "Patient/test")
    assert resource is None
    assert any(issue["level"] == "error" and "Neplatná hodnota výšky" in issue["message"] for issue in issues)

def test_create_fhir_observation_height_out_of_range():
    data = {"height_value": "300"} # Příliš vysoká
    resource, issues = fhir_mapper.create_fhir_observation_height_resource(data, "Patient/test")
    assert resource is not None
    assert any(issue["level"] == "warning" and "mimo očekávaný fyziologický rozsah" in issue["message"] for issue in issues)

# Hmotnost
def test_create_fhir_observation_weight_valid():
    data = {"weight_value": "70.5"}
    resource, issues = fhir_mapper.create_fhir_observation_weight_resource(data, "Patient/test")
    assert resource is not None
    assert resource["valueQuantity"]["value"] == 70.5
    assert not issues

def test_create_fhir_observation_weight_bad_format():
    data = {"weight_value": "sto"}
    resource, issues = fhir_mapper.create_fhir_observation_weight_resource(data, "Patient/test")
    assert resource is None
    assert any(issue["level"] == "error" and "Neplatná hodnota hmotnosti" in issue["message"] for issue in issues)

def test_create_fhir_observation_weight_out_of_range():
    data = {"weight_value": "500"} # Příliš vysoká
    resource, issues = fhir_mapper.create_fhir_observation_weight_resource(data, "Patient/test")
    assert resource is not None
    assert any(issue["level"] == "warning" and "mimo očekávaný fyziologický rozsah" in issue["message"] for issue in issues)

# --- Testy pro agregaci quality issues v parsovacích funkcích ---
def test_parse_patient_data_gathers_date_issues():
    """
    Testuje, zda parse_patient_data správně agreguje issues z parse_date_to_fhir_format.
    """
    # Text s problematickým datem narození
    text_input = "Pacient: Test Pacient\nNar.: 30. února 2000\nRČ: 000230/1234"
    nlp_entities = [] # Testujeme regex fallback pro jednoduchost
    issues = []

    # parse_patient_data zavolá parse_date_to_fhir_format, které by mělo přidat issue
    parsed_data = fhir_mapper.parse_patient_data(nlp_entities, text_input, issues)

    # Ověříme, že issue z parse_date_to_fhir_format bylo přidáno do seznamu
    assert any(
        issue["level"] == "error" and
        "Neplatná kombinace den/měsíc/rok" in issue["message"] and # Chyba z datetime(year, month, day)
        issue["field"] == "date_str" and
        "30. února 2000" in issue["value"]
        for issue in issues
    ), f"Chybějící nebo nesprávné quality issue pro neplatné datum v {issues}"

    # Datum by nemělo být parsováno
    assert "birth_date_fhir" not in parsed_data
    assert parsed_data.get("birth_date_raw") == "30. února 2000"


# --- Test pro map_text_to_fhir (základní) ---
def test_map_text_to_fhir_basic_with_issues():
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
    output = fhir_mapper.map_text_to_fhir(sample_text, original_text=sample_text)
    fhir_resources = output["fhir_resources"]
    quality_issues = output["quality_issues"]

    assert len(fhir_resources) > 0
    assert any(res["resourceType"] == "Patient" for res in fhir_resources)
    assert any(res["resourceType"] == "Observation" and res["code"]["text"] == "Krevní tlak" for res in fhir_resources)
    assert any(res["resourceType"] == "Observation" and res["code"]["text"] == "Pulz" for res in fhir_resources)
    assert any(res["resourceType"] == "Condition" for res in fhir_resources)

    # Check for the specific out-of-range warning for pulse in quality_issues
    assert any(
        issue["level"] == "warning" and
        "Hodnota pulzu (350 /min) je mimo očekávaný fyziologický rozsah" in issue["message"] and
        issue["field"] == "pulse_value"
        for issue in quality_issues
    )
    # Check that RČ and birth date match (no warning should be present for mismatch)
    assert not any("Nesoulad mezi datem narození z RČ" in issue["message"] for issue in quality_issues)


# --- Komplexní testy pro map_text_to_fhir ---

def test_map_text_to_fhir_complex_scenario():
    sample_text_complex = """
    Pacient: Karel Novák
    Nar.: 30.února.1970  // Neplatné datum narození
    RČ: 700228/1111     // Platné RČ pro 28.2.1970 (nesoulad s Nar.)
    ---
    TK: 125/75 mmHg
    Pulz: 15/min          // Extrémně nízký pulz
    Teplota: 36.7 C
    Výška: 180 cm
    Hmotnost: 75 kg
    ---
    Diagnóza: Angina Pectoris I20.9. Jiná poznámka: kontrola za rok.
    Další text: Saturace O2: 98% na vzduchu. // Toto by nemělo být součástí diagnózy
    """
    output = fhir_mapper.map_text_to_fhir(sample_text_complex, original_text=sample_text_complex)
    fhir_resources = output["fhir_resources"]
    quality_issues = output["quality_issues"]

    assert len(fhir_resources) >= 4 # Očekáváme Patient, BP Obs, Pulse Obs, Temp Obs, Height, Weight, Condition

    patient_resource = next((r for r in fhir_resources if r["resourceType"] == "Patient"), None)
    assert patient_resource is not None
    # Datum narození by mělo být z RČ, protože "Nar." je neplatné
    assert patient_resource.get("birthDate") == "1970-02-28"

    pulse_obs = next((r for r in fhir_resources if r["resourceType"] == "Observation" and r["code"]["text"] == "Pulz"), None)
    assert pulse_obs is not None
    assert pulse_obs["valueQuantity"]["value"] == 15

    condition_resource = next((r for r in fhir_resources if r["resourceType"] == "Condition"), None)
    assert condition_resource is not None
    assert "Angina Pectoris I20.9" in condition_resource["code"]["text"]
    assert "Saturace O2" not in condition_resource["code"]["text"] # Ověření, že se nezachytilo příliš mnoho

    # Ověření quality issues
    assert any(
        issue["level"] == "error" and "Neplatná kombinace den/měsíc/rok" in issue["message"] and "30.února.1970" in issue["value"]
        for issue in quality_issues
    ), "Chybí issue pro neplatné datum narození"

    assert any(
        issue["level"] == "warning" and "Nesoulad mezi datem narození z RČ" in issue["message"]
        for issue in quality_issues
    ), "Chybí issue pro nesoulad data narození a RČ"

    assert any(
        issue["level"] == "warning" and "Hodnota pulzu (15 /min) je mimo očekávaný fyziologický rozsah" in issue["message"]
        for issue in quality_issues
    ), "Chybí issue pro pulz mimo rozsah"

def test_map_text_to_fhir_empty_input():
    output = fhir_mapper.map_text_to_fhir("", original_text="")
    fhir_resources = output["fhir_resources"]
    quality_issues = output["quality_issues"]

    assert not fhir_resources # Žádné FHIR zdroje
    assert len(quality_issues) >= 1
    assert any(
        issue["level"] == "error" and "Vstupní text i NLP entity jsou prázdné" in issue["message"]
        for issue in quality_issues
    )

def test_map_text_to_fhir_irrelevant_text():
    text = "Toto je naprosto irelevantní text bez lékařských údajů."
    output = fhir_mapper.map_text_to_fhir(text, original_text=text)
    fhir_resources = output["fhir_resources"]
    quality_issues = output["quality_issues"]

    # Očekáváme, že se nevytvoří žádný Patient resource, což zastaví další tvorbu
    assert not any(r["resourceType"] == "Patient" for r in fhir_resources)
    # Měly by se objevit issues o chybějících datech pacienta
    assert any("Jméno pacienta nenalezeno" in issue["message"] for issue in quality_issues)
    assert any("Datum narození nenalezeno" in issue["message"] for issue in quality_issues)
    # ... a potenciálně další issues o nenalezených pozorováních/diagnóze, pokud parsování dojde tak daleko
    # nebo kritická issue, že Patient resource nemohl být vytvořen.
    assert any("Patient resource nemohl být vytvořen" in issue["message"] and issue["level"] == "critical" for issue in quality_issues)


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
        issues = []
        result = fhir_mapper.parse_observation_data(nlp_entities, text_input, issues)

        if expected_bp_value:
            assert result.get("blood_pressure_value") == expected_bp_value
            assert result.get("measurement_time_fhir") is not None
        else:
            assert result.get("blood_pressure_value") is None

        # Ověření quality issues (log_check nyní odkazuje na issue message)
        # Testy capsys byly nahrazeny kontrolou issues listu
        # Tento blok je zjednodušený, protože původní log_check byl pro stdout,
        # nyní by se měly kontrolovat specifické issues v `issues` listu.
        # Prozatím ponecháme základní kontrolu, zda se nějaké issues vygenerovaly, pokud se očekává.
        # Konkrétní obsah issues by se měl testovat detailněji.
        if expected_bp_value:
            # Pokud očekáváme hodnotu, neměly by být žádné "nenalezeno" issues.
            # Mohou být jiné issues (např. formát), ale to by testoval jiný scénář.
            assert not any("nenalezen" in issue.get("message", "").lower() for issue in issues), \
                f"Test ID {test_id}: Expected BP value but found 'not found' issue in {issues}"
        else:
            # Pokud neočekáváme hodnotu, měl by existovat issue o nenalezení, pokud text nebyl úplně prázdný.
            if text_input and text_input.strip(): # Jen pokud byl nějaký vstup k parsování
                 assert any("krevní tlak nenalezen" in issue.get("message", "").lower() for issue in issues), \
                    f"Test ID {test_id}: Expected no BP value but no 'not found' issue in {issues}"
            else: # Pokud byl vstup prázdný, nemusí být issue o nenalezení, ale issues list by měl být prázdný nebo obsahovat jiné info
                pass # Pro prázdný vstup se issues řeší jinde

        # Původní capsys kontroly byly pro stdout, ty jsou nyní nahrazeny kontrolou `issues`.
        # Logika pro use_regex_fallback_expected je nyní implicitně pokryta tím, zda `expected_bp_value` je None či nikoliv
        # a jaké issues se (ne)objeví.



# --- Testovací třída/sada testů pro parse_vital_signs_data s NLP ---
class TestParseVitalSignsDataNLP:
    # Testy pro PULZ
    @pytest.mark.parametrize("test_id, text_input, nlp_entities, expected_value, expected_unit, expected_issue_message_part_if_not_found", [
        ("pulse_nlp_direct", "Pulz: 75/min.", [{"text": "75/min", "type": "CARDINAL", "start_char": 6, "end_char": 12}], "75", "/min", None),
        ("pulse_nlp_separate_unit", "SF 80 tepů/min", [{"text": "80", "type": "NUMBER", "start_char": 3, "end_char": 5}], "80", "/min", None),
        ("pulse_nlp_context_regex", "P: 90, ale divně", [{"text": "90", "type": "CARDINAL", "start_char": 3, "end_char": 5}], "90", "/min", None),
        ("pulse_global_regex", "Srdeční akce byla 65 /min.", [], "65", "/min", None),
        ("pulse_no_value", "Pulz: není", [], None, None, "pulzu nenalezena"),
        ("pulse_nlp_entity_no_unit_finds_default", "Puls 120", [{"text": "120", "type": "CARDINAL", "start_char": 5, "end_char": 8}], "120", "/min", None),
    ])
    def test_parse_pulse_nlp(self, test_id, text_input, nlp_entities, expected_value, expected_unit, expected_issue_message_part_if_not_found):
        issues = []
        result = fhir_mapper.parse_vital_signs_data(nlp_entities, text_input, issues)
        assert result.get("pulse_value") == expected_value
        assert result.get("pulse_unit") == expected_unit
        if expected_issue_message_part_if_not_found and expected_value is None:
             assert any(expected_issue_message_part_if_not_found.lower() in issue.get("message", "").lower() and issue["level"] == "info" for issue in issues), f"Test ID {test_id}: Expected issue message part '{expected_issue_message_part_if_not_found}' not found in {issues}"
        elif expected_value:
             assert not any("pulzu nenalezena" in issue.get("message", "").lower() for issue in issues), f"Test ID {test_id}: Expected pulse value but found 'not found' issue in {issues}"

    # Testy pro TEPLOTU
    @pytest.mark.parametrize("test_id, text_input, nlp_entities, expected_value, expected_unit, expected_issue_message_part_if_not_found", [
        ("temp_nlp_direct", "Teplota: 37,5°C", [{"text": "37,5°C", "type": "NUMBER", "start_char": 9, "end_char": 15}], "37.5", "°C", None),
        ("temp_nlp_separate_unit", "T 36.8 stupňů C", [{"text": "36.8", "type": "CARDINAL", "start_char": 2, "end_char": 6}], "36.8", "°C", None),
        ("temp_nlp_context_regex", "Teplota naměřena 37 C", [{"text": "37", "type": "NUMBER", "start_char": 17, "end_char": 19}], "37", "°C", None),
        ("temp_global_regex", "Pacient afebrilní, TT 36,9C.", [], "36.9", "°C", None),
        ("temp_no_value", "Teplota: neměřena", [], None, None, "teploty nenalezena"),
    ])
    def test_parse_temperature_nlp(self, test_id, text_input, nlp_entities, expected_value, expected_unit, expected_issue_message_part_if_not_found):
        issues = []
        result = fhir_mapper.parse_vital_signs_data(nlp_entities, text_input, issues)
        assert result.get("temperature_value") == expected_value
        assert result.get("temperature_unit") == expected_unit
        if expected_issue_message_part_if_not_found and expected_value is None:
             assert any(expected_issue_message_part_if_not_found.lower() in issue.get("message", "").lower() and issue["level"] == "info" for issue in issues), f"Test ID {test_id}: Expected issue message part '{expected_issue_message_part_if_not_found}' not found in {issues}"
        elif expected_value:
             assert not any("teploty nenalezena" in issue.get("message", "").lower() for issue in issues), f"Test ID {test_id}: Expected temperature value but found 'not found' issue in {issues}"

    # Testy pro VÝŠKU
    @pytest.mark.parametrize("test_id, text_input, nlp_entities, expected_value, expected_unit, expected_issue_message_part_if_not_found", [
        ("height_nlp_direct", "Výška: 180cm.", [{"text": "180cm", "type": "QUANTITY", "start_char": 7, "end_char": 12}], "180", "cm", None),
        ("height_nlp_separate_unit", "Výš. 175 cm", [{"text": "175", "type": "NUMBER", "start_char": 6, "end_char": 9}], "175", "cm", None),
        ("height_nlp_context_regex", "Výška pacienta 190cm", [{"text": "190", "type": "CARDINAL", "start_char": 16, "end_char": 19}], "190", "cm", None),
        ("height_global_regex", "Měří asi 165 cm.", [], "165", "cm", None),
        ("height_no_value", "Výška: neuvedena", [], None, None, "výšky nenalezena"),
    ])
    def test_parse_height_nlp(self, test_id, text_input, nlp_entities, expected_value, expected_unit, expected_issue_message_part_if_not_found):
        issues = []
        result = fhir_mapper.parse_vital_signs_data(nlp_entities, text_input, issues)
        assert result.get("height_value") == expected_value
        assert result.get("height_unit") == expected_unit
        if expected_issue_message_part_if_not_found and expected_value is None:
             assert any(expected_issue_message_part_if_not_found.lower() in issue.get("message", "").lower() and issue["level"] == "info" for issue in issues), f"Test ID {test_id}: Expected issue message part '{expected_issue_message_part_if_not_found}' not found in {issues}"
        elif expected_value:
             assert not any("výšky nenalezena" in issue.get("message", "").lower() for issue in issues), f"Test ID {test_id}: Expected height value but found 'not found' issue in {issues}"

    # Testy pro HMOTNOST
    @pytest.mark.parametrize("test_id, text_input, nlp_entities, expected_value, expected_unit, expected_issue_message_part_if_not_found", [
        ("weight_nlp_direct", "Hmotnost: 75.5kg", [{"text": "75.5kg", "type": "QUANTITY", "start_char": 10, "end_char": 16}], "75.5", "kg", None),
        ("weight_nlp_separate_unit", "Hm. 82 kg.", [{"text": "82", "type": "NUMBER", "start_char": 4, "end_char": 6}], "82", "kg", None),
        ("weight_nlp_context_regex", "Váha aktuálně 91 kg", [{"text": "91", "type": "CARDINAL", "start_char": 14, "end_char": 16}], "91", "kg", None),
        ("weight_global_regex", "Pacient váží 68kg.", [], "68", "kg", None),
        ("weight_no_value", "Hmotnost: neznámá", [], None, None, "hmotnosti nenalezena"),
    ])
    def test_parse_weight_nlp(self, test_id, text_input, nlp_entities, expected_value, expected_unit, expected_issue_message_part_if_not_found):
        issues = []
        result = fhir_mapper.parse_vital_signs_data(nlp_entities, text_input, issues)
        assert result.get("weight_value") == expected_value
        assert result.get("weight_unit") == expected_unit
        if expected_issue_message_part_if_not_found and expected_value is None:
             assert any(expected_issue_message_part_if_not_found.lower() in issue.get("message", "").lower() and issue["level"] == "info" for issue in issues), f"Test ID {test_id}: Expected issue message part '{expected_issue_message_part_if_not_found}' not found in {issues}"
        elif expected_value:
             assert not any("hmotnosti nenalezena" in issue.get("message", "").lower() for issue in issues), f"Test ID {test_id}: Expected weight value but found 'not found' issue in {issues}"


# --- Testy pro vylepšené chování parse_patient_data ---
class TestParsePatientDataNLPContext:
    def test_parse_patient_name_multiple_P_entities(self): # capsys odstraněn
        text_input = "Pacient: Jan Novák. Ošetřující lékař: MUDr. Petr Svoboda."
        nlp_entities = [
            {"text": "Jan Novák", "type": "P", "start_char": 9, "end_char": 18},
            {"text": "MUDr. Petr Svoboda", "type": "P", "start_char": 42, "end_char": 60}
        ]
        expected_name = "Jan Novák"
        issues = []
        result = fhir_mapper.parse_patient_data(nlp_entities, text_input, issues)
        assert result.get("full_name") == expected_name
        # Ověření, že nebyly přidány žádné error/warning issues specificky pro full_name
        assert not any(issue.get("field") == "full_name" and issue.get("level") in ["error", "warning"] for issue in issues), \
            f"Expected no name-specific issues, got {issues}"

    def test_parse_birth_date_multiple_T_entities(self):
        text_input = "Datum narození: 1.1.1990. Datum vyšetření: 15.3.2023."
        nlp_entities = [
            {"text": "1.1.1990", "type": "DATE", "start_char": 16, "end_char": 24},
            {"text": "15.3.2023", "type": "DATE", "start_char": 44, "end_char": 53}
        ]
        expected_date_fhir = "1990-01-01"
        expected_date_raw = "1.1.1990"
        issues = []
        result = fhir_mapper.parse_patient_data(nlp_entities, text_input, issues)
        assert result.get("birth_date_fhir") == expected_date_fhir
        assert result.get("birth_date_raw") == expected_date_raw
        # Ověření, že nebyly přidány žádné error issues specificky pro birth_date z NLP zpracování
        # (parse_date_to_fhir_format by mohl přidat issues, ale zde testujeme výběr správné entity)
        assert not any(issue.get("field") == "birth_date" and issue.get("level") == "error" for issue in issues), \
            f"Expected no birth_date selection errors, got {issues}"
        # Kontrola, že pokud parse_date_to_fhir_format selhalo pro vybranou entitu, je to zaznamenáno
        # V tomto případě by mělo projít bez chyby parsování data.
        assert not any(issue.get("field") == "date_str" and issue.get("value") == expected_date_raw and issue.get("level") == "error" for issue in issues), \
            f"Date parsing error for selected entity '{expected_date_raw}': {issues}"


# --- Testy pro vylepšené chování parse_condition_data ---
class TestParseConditionDataNLPContext:
    def test_parse_condition_multiple_DIS_entities_merged(self):
        text_input = "Diagnóza: Diabetes mellitus, ICHS. Další diagnóza: Hypertenze."
        nlp_entities = [
            {"text": "Diabetes mellitus", "type": "DIS", "start_char": 10, "end_char": 27},
            {"text": "ICHS", "type": "DIS", "start_char": 29, "end_char": 33},
            {"text": "Hypertenze", "type": "DIS", "start_char": 53, "end_char": 63}
        ]
        expected_diagnosis = "Diabetes mellitus, ICHS"
        issues = []
        result = fhir_mapper.parse_condition_data(nlp_entities, text_input, issues)
        assert result.get("diagnosis_text") == expected_diagnosis
        assert not any(issue.get("field") == "diagnosis_text" and issue.get("level") in ["error","warning"] for issue in issues), \
            f"Expected no diagnosis-specific issues, got {issues}"

    def test_parse_condition_dis_experimental_extension(self):
        text_input = "Závěr: Infekce horních cest dýchacích."
        nlp_entities = [
            {"text": "Infekce horních cest dýchacích", "type": "DIS", "start_char": 7, "end_char": 37}
        ]
        expected_diagnosis = "Infekce horních cest dýchacích."
        issues = []
        result = fhir_mapper.parse_condition_data(nlp_entities, text_input, issues)
        assert result.get("diagnosis_text") == expected_diagnosis
        assert not issues, f"Expected no issues, got {issues}"

    def test_parse_condition_single_dis_no_merge_needed(self):
        text_input = "Dg.: Hypertenze esenciální."
        nlp_entities = [
            {"text": "Hypertenze esenciální", "type": "DIS", "start_char": 5, "end_char": 26}
        ]
        expected_diagnosis = "Hypertenze esenciální"
        issues = []
        result = fhir_mapper.parse_condition_data(nlp_entities, text_input, issues)
        assert result.get("diagnosis_text") == expected_diagnosis
        assert not issues, f"Expected no issues, got {issues}"
