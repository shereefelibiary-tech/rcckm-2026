from core.results import RCCKMResult
from renderers.clarifier_renderer import (
    build_clarifier_card_html,
    build_clarifier_items,
    render_clarifier_card,
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

    assert "Data that could clarify risk" in html
    assert "These items may improve confidence in the prevention plan." in html
    assert "clarifier-list" in html
    assert "Lp(a)" in html
    assert "Lp(a) measurement" in html
    assert "Already available:" in html
    assert "recommended" not in html
    assert "Show completed clarifiers" not in html
    assert "complete" not in html
    assert "clarifier-row" not in html
    assert "clarifier-table-head" not in html
    assert "&lt;div" not in html


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
    assert "Data that could clarify risk" in html
    assert "Show completed clarifiers" not in html


def test_build_clarifier_card_html_uses_concise_available_state_when_none_missing():
    html = build_clarifier_card_html(RCCKMResult())

    assert "Data that could clarify risk" in html
    assert "Key clarifying data are available." in html
    assert "No missing clarifiers flagged by the engine." not in html
