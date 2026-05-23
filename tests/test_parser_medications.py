from smartphrase_ingest.med_vocab import extract_medications_structured


def _first(result, normalized_name):
    matches = [
        med for med in result["medications_detected"]
        if med["normalized_name"] == normalized_name
    ]
    assert matches, f"{normalized_name} not detected"
    return matches[0]


def test_atorvastatin_80_active_is_high_intensity_statin():
    result = extract_medications_structured("Current medications: atorvastatin 80 mg daily.")

    assert result["lipidLowering"] is True
    assert result["statin"] is True
    assert result["statin_intensity"] == "high"
    assert _first(result, "atorvastatin")["active"] is True


def test_rosuvastatin_allergy_is_inactive():
    result = extract_medications_structured("Allergy to rosuvastatin.")

    med = _first(result, "rosuvastatin")
    assert med["active"] is False
    assert result["lipidLowering"] is None
    assert result["statin"] is None


def test_stopped_fenofibrate_is_inactive():
    result = extract_medications_structured("Stopped fenofibrate due to side effects.")

    med = _first(result, "fenofibrate")
    assert med["active"] is False
    assert result["lipidLowering"] is None


def test_cardiometabolic_medication_brands_set_flags():
    jardiance = extract_medications_structured("Jardiance 10 mg daily.")
    mounjaro = extract_medications_structured("Mounjaro weekly.")
    ozempic = extract_medications_structured("Ozempic 0.5 mg weekly.")
    losartan = extract_medications_structured("losartan 50 mg daily.")
    lisinopril = extract_medications_structured("lisinopril 20 mg daily.")
    synjardy = extract_medications_structured("Synjardy daily.")

    assert jardiance["sglt2"] is True
    assert mounjaro["glp1_gip"] is True
    assert ozempic["glp1_gip"] is True
    assert losartan["bpTreated"] is True
    assert losartan["ace_arb"] is True
    assert lisinopril["bpTreated"] is True
    assert lisinopril["ace_arb"] is True
    assert synjardy["sglt2"] is True
    assert synjardy["metformin"] is True
