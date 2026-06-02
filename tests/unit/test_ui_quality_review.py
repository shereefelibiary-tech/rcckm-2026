import json

from qa_agent.ui_quality_review import review_payload, write_case_review


def _payload(**overrides):
    payload = {
        "parsed_patient_json": {
            "cac": 0,
            "clinical_ascvd": False,
            "a1c": 5.6,
            "egfr": 72,
            "uacr": 8,
        },
        "final_report_text": (
            "Objective:\nVitals and labs reviewed.\n\n"
            "Assessment:\n- No diagnosis candidates generated.\n\n"
            "Recommendations:\n1. Aspirin: Not indicated."
        ),
        "visible_ui_text": "RISK CONTINUUM CKM\nRecommendations\nAspirin: Not indicated.",
    }
    payload.update(overrides)
    return payload


def test_ui_quality_review_passes_clean_report():
    review = review_payload(case_id="clean", payload=_payload(), page_text="Clean visible page")

    assert review["status"] == "PASS"
    assert review["findings"] == []


def test_ui_quality_review_flags_filler_and_contradiction():
    review = review_payload(
        case_id="bad",
        payload=_payload(
            final_report_text=(
                "Assessment:\nCoronary plaque: Present (CAC 0).\n\n"
                "Recommendations:\nAspirin: Not indicated. Start aspirin. "
                "Consider optimizing risk factors."
            )
        ),
        page_text="Consider optimizing risk factors.",
    )

    assert review["status"] == "FAIL"
    categories = {item["category"] for item in review["findings"]}
    assert {"wording", "contradiction"} <= categories


def test_ui_quality_review_does_not_treat_no_known_ascvd_as_secondary_prevention():
    review = review_payload(
        case_id="ascvd_context",
        payload=_payload(
            final_report_text=(
                "Assessment:\nNo known clinical ASCVD.\n\n"
                "Recommendations:\n1. Aspirin: Not indicated."
            )
        ),
        page_text="No known clinical ASCVD.",
    )

    assert not any(
        item["category"] == "contradiction" and "ASCVD" in item["finding"]
        for item in review["findings"]
    )


def test_write_case_review_outputs_json_and_markdown(tmp_path):
    review = review_payload(
        case_id="bad",
        payload=_payload(final_report_text="Assessment:\n\nRecommendations:\nAI-generated."),
        page_text="AI-generated.",
    )

    json_path, md_path = write_case_review("bad", review, output_dir=tmp_path)

    assert json.loads(json_path.read_text(encoding="utf-8"))["case_id"] == "bad"
    assert "AI-generated" in md_path.read_text(encoding="utf-8")
