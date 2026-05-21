from core.patient import Patient
from modules.rss.engine import build_rss_contributions, calculate_rss_total


def test_rss_cac_scoring():
    patient = Patient(age=60, sex="male", cac=350)
    contributions = build_rss_contributions(patient, None)

    assert any(c.label == "CAC plaque burden" and c.points == 30 and c.severity == "severe" for c in contributions)


def test_rss_apob_scoring():
    patient = Patient(age=60, sex="male", apob=110)
    contributions = build_rss_contributions(patient, None)

    assert any(c.label == "ApoB elevation" and c.points == 8 for c in contributions)


def test_rss_lpa_scoring():
    patient = Patient(age=60, sex="male", lp_a_value=260, lp_a_unit="nmol/L")
    contributions = build_rss_contributions(patient, None)

    assert any(c.label == "Elevated Lp(a)" and c.points == 12 for c in contributions)


def test_rss_hscrp_scoring():
    patient = Patient(age=60, sex="male", hscrp=5.2)
    contributions = build_rss_contributions(patient, None)

    assert any(c.label == "Inflammatory risk" and c.points == 7 for c in contributions)


def test_rss_egfr_scoring():
    patient = Patient(age=60, sex="male", egfr=35)
    contributions = build_rss_contributions(patient, None)

    assert any(c.label == "Reduced eGFR" and c.points == 8 for c in contributions)


def test_rss_uacr_scoring():
    patient = Patient(age=60, sex="male", uacr=320)
    contributions = build_rss_contributions(patient, None)

    assert any(c.label == "Albuminuria" and c.points == 10 for c in contributions)


def test_rss_triglycerides_scoring():
    patient = Patient(age=60, sex="male", triglycerides=520)
    contributions = build_rss_contributions(patient, None)

    assert any(c.label == "Hypertriglyceridemia" and c.points == 8 for c in contributions)


def test_rss_diabetes_scoring():
    patient = Patient(age=60, sex="male", diabetes=True)
    contributions = build_rss_contributions(patient, None)

    assert any(c.label == "Diabetes" and c.points == 8 for c in contributions)


def test_rss_smoking_scoring():
    patient = Patient(age=60, sex="male", smoker=True)
    contributions = build_rss_contributions(patient, None)

    assert any(c.label == "Smoking" and c.points == 8 for c in contributions)


def test_rss_total_score_calculation():
    patient = Patient(
        age=60,
        sex="male",
        cac=350,
        apob=140,
        lp_a_value=430,
        lp_a_unit="nmol/L",
        hscrp=5.5,
        egfr=35,
        uacr=320,
        triglycerides=520,
        diabetes=True,
        smoker=True,
    )
    contributions = build_rss_contributions(patient, None)
    total = calculate_rss_total(contributions)

    assert total == 30 + 12 + 15 + 7 + 8 + 10 + 8 + 8 + 8
