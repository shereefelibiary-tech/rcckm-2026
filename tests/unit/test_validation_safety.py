from ui.validation_safety import build_validation_safety_html


def test_validation_safety_section_contains_clinician_facing_status_rows():
    html = build_validation_safety_html()

    assert "Validation &amp; Safety" in html
    assert "Deterministic" in html
    assert "Golden cases" in html
    assert "Never-cross invariants" in html
    assert "Output snapshots" in html
    assert "Clinician review recommended" in html
    assert "Do not enter PHI in public/demo use" in html


def test_validation_safety_section_explains_scope_without_overclaiming():
    html = build_validation_safety_html()

    assert "deterministic rule-based interpretation" in html
    assert "does not diagnose independently" in html
    assert "prescribe automatically" in html
    assert "replace clinician judgment" in html
    assert "clinical decision support" in html
    assert "patient-identifiable information" in html
    assert "hidden generative reasoning" in html
    assert "guaranteed" not in html.lower()
    assert "certified" not in html.lower()
