from core.patient import Patient
from core.results import RCCKMResult
from renderers.clarifier_renderer import (
    build_clarifier_card_html,
    build_clarifier_items,
    get_missing_clarification_tests,
    render_clarifier_card,
    should_render_clarification_card,
)


def test_build_clarifier_items_marks_action_domain_recommendations():
    result = RCCKMResult(
        action_domains={
            "apob_testing": "Obtain ApoB to define atherogenic particle burden.",
            "lpa_testing": "Check Lp(a) once.",
            "cac_testing": "Coronary calcium reasonable for plaque clarification.",
            "uacr_testing": "Obtain UACR to complete kidney-risk assessment.",
            "hscrp_testing": "Consider hsCRP to clarify inflammatory biomarker context.",
            "fasting_lipids": "Repeat fasting lipid panel to confirm severe hypertriglyceridemia.",
        }
    )

    items = build_clarifier_items(result)

    assert all(item["status"] == "recommended" for item in items)
    assert items[0] == {
        "label": "ApoB",
        "status": "recommended",
        "reason": "LDL present but particle burden unmeasured",
        "priority": "High",
    }


def test_build_clarifier_items_uses_clarification_flags():
    result = RCCKMResult(
        clarification={
            "recommend_apob": True,
            "recommend_lpa": True,
            "recommend_cac": True,
            "recommend_uacr": True,
        }
    )

    items = build_clarifier_items(result)

    statuses = {item["label"]: item["status"] for item in items}
    assert statuses["ApoB"] == "recommended"
    assert statuses["Lp(a)"] == "recommended"
    assert statuses["CAC"] == "recommended"
    assert statuses["UACR"] == "recommended"
    assert statuses["hsCRP"] == "complete"
    assert statuses["Repeat fasting lipids"] == "complete"


def test_build_clarifier_card_html_contains_quick_read_recommended_list():
    result = RCCKMResult(
        action_domains={
            "lpa_testing": "Check Lp(a) once.",
        }
    )

    html = build_clarifier_card_html(result)

    assert "Additional information that may help clarify risk:" in html
    assert "risk clarification" not in html
    assert "clarifying data" not in html
    assert "already available" not in html.lower()
    assert "These items may improve confidence in the prevention plan." not in html
    assert "clarifier-tests" in html
    assert "Lp(a)" in html
    assert "Lp(a) measurement" not in html
    assert "recommended" not in html
    assert "Show completed clarifiers" not in html
    assert "complete" not in html
    assert "clarifier-row" not in html
    assert "clarifier-table-head" not in html
    assert "&lt;div" not in html


def test_hscrp_clarifier_uses_inflammatory_risk_context_copy():
    result = RCCKMResult(
        action_domains={
            "hscrp_testing": "Consider hsCRP if inflammatory risk context would change management.",
        }
    )

    html = build_clarifier_card_html(result)

    assert "hsCRP" in html
    assert "inflammatory risk context" not in html
    assert "inflammatory biomarker context" not in html


def test_measured_cac_does_not_render_as_missing_clarifier():
    patient = Patient(age=64, sex="female", cac=350)
    result = RCCKMResult(
        action_domains={
            "cac_testing": "Coronary calcium reasonable for plaque clarification.",
        }
    )

    html = build_clarifier_card_html(result, patient=patient)

    assert html == ""


def test_render_clarifier_card_uses_unsafe_markdown():
    class FakeStreamlit:
        def __init__(self):
            self.calls = []

        def markdown(self, value, unsafe_allow_html=False):
            self.calls.append((value, unsafe_allow_html))

    fake_st = FakeStreamlit()
    result = RCCKMResult(
        action_domains={
            "lpa_testing": "Check Lp(a) once.",
        }
    )

    render_clarifier_card(result, fake_st)

    assert len(fake_st.calls) == 1
    html, unsafe = fake_st.calls[0]
    assert unsafe is True
    assert "clarifier-card" in html
    assert "Additional information that may help clarify risk:" in html
    assert "Show completed clarifiers" not in html


def test_render_clarifier_card_skips_streamlit_when_no_missing_tests():
    class FakeStreamlit:
        def __init__(self):
            self.calls = []

        def markdown(self, value, unsafe_allow_html=False):
            self.calls.append((value, unsafe_allow_html))

    fake_st = FakeStreamlit()

    render_clarifier_card(RCCKMResult(), fake_st)

    assert fake_st.calls == []


def test_build_clarifier_card_html_hides_when_none_missing():
    html = build_clarifier_card_html(RCCKMResult())

    assert html == ""
    assert "Key clarifying data are available." not in html
    assert "No missing clarifiers flagged by the engine." not in html


def test_build_clarifier_card_html_uses_compact_ordered_test_list():
    result = RCCKMResult(
        clarification={
            "recommend_cac": True,
            "recommend_apob": True,
            "recommend_lpa": True,
            "recommend_uacr": True,
        }
    )

    html = build_clarifier_card_html(result)

    assert "Additional information that may help clarify risk:" in html
    assert "ApoB &bull; Lp(a) &bull; CAC &bull; UACR" in html
    assert "already available" not in html.lower()


def test_missing_clarification_helpers_drive_card_visibility():
    empty_result = RCCKMResult()
    missing_result = RCCKMResult(
        clarification={
            "recommend_cac": True,
            "recommend_apob": True,
            "recommend_lpa": True,
        }
    )

    assert get_missing_clarification_tests(None, empty_result) == []
    assert should_render_clarification_card([]) is False
    assert get_missing_clarification_tests(None, missing_result) == ["ApoB", "Lp(a)", "CAC"]
    assert should_render_clarification_card(["ApoB"]) is True


def test_clarifier_card_removes_legacy_wording_entirely():
    html = build_clarifier_card_html(
        RCCKMResult(clarification={"recommend_apob": True, "recommend_lpa": True})
    )

    forbidden = (
        "Data that could clarify risk",
        "improve confidence in the prevention plan",
        "Key clarifying data are available",
        "Already available:",
        "clarifying data",
        "Risk clarification",
        "Clarification complete",
    )
    for phrase in forbidden:
        assert phrase not in html
