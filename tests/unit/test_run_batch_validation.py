import json

from qa_agent import run_batch_validation


def test_compare_parser_fields_reports_mismatch():
    findings = run_batch_validation._compare_parser_fields(
        "synthetic_test",
        {"age": 55, "ldl_c": 142, "clinical_ascvd": False},
        {"age": 52, "ldl_c": 142, "clinical_ascvd": False},
    )

    assert len(findings) == 1
    assert findings[0].category == "parser"
    assert findings[0].severity == "high"
    assert findings[0].expected == 55
    assert findings[0].actual == 52


def test_write_reports_creates_required_batch_artifacts(tmp_path, monkeypatch):
    monkeypatch.setattr(run_batch_validation, "REPORT_DIR", tmp_path)
    finding = run_batch_validation.BatchFinding(
        case_id="synthetic_test",
        status="FAIL",
        category="CKM",
        severity="high",
        key="CKM stage",
        expected=3,
        actual=2,
        explanation="CKM stage did not match.",
    )

    run_batch_validation._write_reports(
        [{"case_id": "synthetic_test", "phenotype": "ckd_focused", "status": "FAIL"}],
        [finding],
        [
            {
                "case_id": "synthetic_test",
                "status": "warn",
                "severity": "medium",
                "category": "wording",
                "finding": "Filler phrase visible",
                "evidence_excerpt": "risk-factor control",
                "suggested_fix_direction": "Remove filler.",
                "codex_ready": True,
            }
        ],
    )

    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary["total_cases"] == 1
    assert summary["fail"] == 1
    assert (tmp_path / "summary.md").exists()
    assert (tmp_path / "failures.csv").exists()
    assert "CKM stage" in (tmp_path / "high_severity.md").read_text(encoding="utf-8")
    assert "Filler phrase visible" in (tmp_path / "ui_quality_summary.md").read_text(
        encoding="utf-8"
    )


def test_ui_findings_adds_case_id_to_case_review_items():
    review = {
        "findings": [
            {
                "status": "fail",
                "severity": "high",
                "category": "visual",
                "finding": "Browser QA run did not complete.",
                "evidence_excerpt": "timeout",
                "suggested_fix_direction": "Retry.",
                "codex_ready": False,
            }
        ]
    }

    findings = run_batch_validation._ui_findings("synthetic_test", review)

    assert findings[0]["case_id"] == "synthetic_test"
    assert findings[0]["category"] == "visual"
