from smartphrase_ingest.med_vocab import extract_medications_structured
from ui.ingest_panel import parse_ingest_report, parse_ingest_text


def _first_med(result, normalized_name):
    matches = [
        med
        for med in result["medications_detected"]
        if med["normalized_name"] == normalized_name
    ]
    assert matches, f"{normalized_name} not detected"
    return matches[0]


def test_active_atorvastatin_high_intensity_sets_lipid_lowering():
    result = extract_medications_structured("Current medications: atorvastatin 40 mg daily.")

    med = _first_med(result, "atorvastatin")
    assert med["active"] is True
    assert med["dose"] == "40 mg"
    assert med["frequency"].lower() == "daily"
    assert result["lipidLowering"] is True
    assert result["statin"] is True
    assert result["statin_intensity"] == "high"


def test_rosuvastatin_10_nightly_is_moderate_intensity():
    result = extract_medications_structured("Meds: rosuvastatin 10 mg nightly.")

    assert result["statin"] is True
    assert result["statin_intensity"] == "moderate"


def test_stopped_statin_is_detected_but_not_counted_active():
    result = extract_medications_structured("Stopped atorvastatin 40 mg due to muscle aches.")

    med = _first_med(result, "atorvastatin")
    assert med["active"] is False
    assert result["lipidLowering"] is None
    assert result["statin"] is None


def test_active_moderate_statin_ezetimibe_with_prior_high_intensity_intolerance():
    result = extract_medications_structured(
        "Current medications: pravastatin 40 mg daily, ezetimibe 10 mg daily. "
        "Prior atorvastatin intolerance. Prior rosuvastatin intolerance."
    )
    active_pravastatin = _first_med(result, "pravastatin")
    active_ezetimibe = _first_med(result, "ezetimibe")
    inactive_atorvastatin = _first_med(result, "atorvastatin")
    inactive_rosuvastatin = _first_med(result, "rosuvastatin")

    assert active_pravastatin["active"] is True
    assert active_ezetimibe["active"] is True
    assert inactive_atorvastatin["active"] is False
    assert inactive_rosuvastatin["active"] is False
    assert result["lipidLowering"] is True
    assert result["statin"] is True
    assert result["ezetimibe"] is True
    assert result["statin_intensity"] == "moderate"
    assert result["statin_intolerance"] is True


def test_statin_allergy_is_not_active_lipid_lowering():
    parsed = parse_ingest_text("Allergy to simvastatin. LDL-C 135.")

    assert parsed["lipid_lowering"] is False


def test_pcsk9_and_ezetimibe_are_lipid_lowering():
    repatha = extract_medications_structured("Repatha every 2 weeks.")
    zetia = extract_medications_structured("Zetia 10 mg daily.")

    assert repatha["pcsk9"] is True
    assert repatha["lipidLowering"] is True
    assert _first_med(repatha, "evolocumab")["frequency"].lower() == "every 2 weeks"
    assert zetia["ezetimibe"] is True
    assert zetia["lipidLowering"] is True


def test_sglt2_and_glp1_brand_names_are_detected():
    jardiance = extract_medications_structured("Jardiance 10 mg daily.")
    farxiga = extract_medications_structured("Farxiga 10 mg daily.")
    mounjaro = extract_medications_structured("Mounjaro weekly.")
    ozempic = extract_medications_structured("Ozempic 0.5 mg weekly.")

    assert jardiance["sglt2"] is True
    assert farxiga["sglt2"] is True
    assert mounjaro["glp1_gip"] is True
    assert ozempic["glp1_gip"] is True


def test_bp_and_ace_arb_medications_are_detected():
    losartan = extract_medications_structured("losartan 50 mg daily")
    lisinopril = extract_medications_structured("lisinopril 20 mg daily")
    hctz = extract_medications_structured("HCTZ 25 mg daily")

    assert losartan["bpTreated"] is True
    assert losartan["ace_arb"] is True
    assert lisinopril["bpTreated"] is True
    assert lisinopril["ace_arb"] is True
    assert hctz["bpTreated"] is True


def test_combination_products_set_component_flags():
    synjardy = extract_medications_structured("Synjardy daily.")
    entresto = extract_medications_structured("Entresto 49/51 mg BID.")

    assert synjardy["sglt2"] is True
    assert synjardy["metformin"] is True
    assert entresto["bpTreated"] is True
    assert entresto["ace_arb"] is True
    assert _first_med(entresto, "sacubitril/valsartan")["class"] == "arni"


def test_parser_includes_structured_med_output_and_warnings():
    report = parse_ingest_report(
        "Meds: Jardiance 10 mg daily, losartan 50 mg daily. Stopped atorvastatin."
    )
    parsed = report["parsed"]

    assert parsed["sglt2"] is True
    assert parsed["bp_treated"] is True
    assert parsed["ace_arb"] is True
    assert "medications_detected" in report["raw"]["extracted"]
    assert any("atorvastatin" in warning.lower() for warning in report["warnings"])
