from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from qa_agent.expected_rules import derived_expectations


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "outputs"
EXPECTED_DIR = ROOT / "expected"


FIELD_MAP = {
    "age": "age",
    "sex": "sex",
    "ldl_c": "ldl_c",
    "apob": "apob",
    "a1c": "a1c",
    "egfr": "egfr",
    "uacr_mg_g": "uacr",
    "cac_score": "cac",
    "family_history_premature_ascvd": "family_history_premature_ascvd",
    "known_ascvd": "clinical_ascvd",
}


@dataclass
class Finding:
    status: str
    category: str
    severity: str
    key: str
    expected: Any
    actual: Any
    explanation: str


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _values_match(expected: Any, actual: Any) -> bool:
    if isinstance(expected, bool):
        return bool(actual) is expected
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        return math.isclose(float(actual), float(expected), rel_tol=0, abs_tol=0.01)
    if isinstance(expected, str):
        return str(actual or "").strip().lower() == expected.strip().lower()
    return actual == expected


def _finding(
    *,
    status: str,
    category: str,
    severity: str,
    key: str,
    expected: Any,
    actual: Any,
    explanation: str,
) -> Finding:
    return Finding(
        status=status,
        category=category,
        severity=severity,
        key=key,
        expected=expected,
        actual=actual,
        explanation=explanation,
    )


def _compare_field(expected: dict, parsed: dict, key: str) -> Finding | None:
    if key not in expected:
        return None
    actual_key = FIELD_MAP[key]
    actual = parsed.get(actual_key)
    if actual is None:
        return _finding(
            status="warn",
            category="parser",
            severity="medium",
            key=key,
            expected=expected[key],
            actual=actual,
            explanation=f"Parsed field `{actual_key}` was not available.",
        )
    passed = _values_match(expected[key], actual)
    return _finding(
        status="pass" if passed else "fail",
        category="parser",
        severity="high" if not passed else "low",
        key=key,
        expected=expected[key],
        actual=actual,
        explanation=(
            f"Parsed `{actual_key}` matched expected value."
            if passed
            else f"Parsed `{actual_key}` did not match expected value."
        ),
    )


def _compare_derived(expected: dict, parsed: dict, key: str) -> Finding | None:
    if key not in expected:
        return None
    derived = derived_expectations(parsed)
    actual = derived.get(key)
    passed = _values_match(expected[key], actual)
    return _finding(
        status="pass" if passed else "fail",
        category="derived_logic",
        severity="high" if not passed else "low",
        key=key,
        expected=expected[key],
        actual=actual,
        explanation=(
            f"Derived `{key}` matched expected value."
            if passed
            else f"Derived `{key}` did not match expected value."
        ),
    )


def _report_findings(actual: dict) -> list[Finding]:
    findings = []
    final_report_text = actual.get("final_report_text") or ""
    engine_output = actual.get("engine_output_json")
    findings.append(
        _finding(
            status="warn" if not final_report_text else "pass",
            category="report",
            severity="low",
            key="final_report_text",
            expected="available when interpretation has run",
            actual=bool(final_report_text),
            explanation=(
                "Final report text is not available because this QA run stops after Parse and apply."
                if not final_report_text
                else "Final report text is available."
            ),
        )
    )
    findings.append(
        _finding(
            status="warn" if engine_output is None else "pass",
            category="report",
            severity="low",
            key="engine_output_json",
            expected="available when interpretation has run",
            actual=engine_output is not None,
            explanation=(
                "Engine output is not available because this QA run stops after Parse and apply."
                if engine_output is None
                else "Engine output is available."
            ),
        )
    )
    return findings


def _nested_get(source: dict | None, *keys: str) -> Any:
    current: Any = source or {}
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _interpretation_findings(expected: dict, actual: dict) -> list[Finding]:
    findings: list[Finding] = []
    report_text = actual.get("final_report_text") or ""
    recommendations_text = actual.get("recommendations_text") or ""
    combined_text = f"{report_text}\n{recommendations_text}"

    if "ckm_stage" in expected:
        actual_stage = _nested_get(actual.get("ckm_stage"), "stage")
        passed = _values_match(expected["ckm_stage"], actual_stage)
        findings.append(
            _finding(
                status="pass" if passed else "fail",
                category="report",
                severity="high" if not passed else "low",
                key="ckm_stage",
                expected=expected["ckm_stage"],
                actual=actual_stage,
                explanation=(
                    "CKM stage matched expected interpretation."
                    if passed
                    else "CKM stage did not match expected interpretation."
                ),
            )
        )
    if "risk_level" in expected:
        actual_level = _nested_get(actual.get("risk_level"), "level")
        passed = _values_match(expected["risk_level"], actual_level)
        findings.append(
            _finding(
                status="pass" if passed else "fail",
                category="report",
                severity="high" if not passed else "low",
                key="risk_level",
                expected=expected["risk_level"],
                actual=actual_level,
                explanation=(
                    "Risk level matched expected interpretation."
                    if passed
                    else "Risk level did not match expected interpretation."
                ),
            )
        )
    if "kdigo_stage" in expected:
        passed = expected["kdigo_stage"].lower() in combined_text.lower()
        findings.append(
            _finding(
                status="pass" if passed else "fail",
                category="report",
                severity="medium" if not passed else "low",
                key="kdigo_stage",
                expected=expected["kdigo_stage"],
                actual=combined_text if passed else None,
                explanation=(
                    "Report text includes expected KDIGO stage."
                    if passed
                    else "Report text does not include expected KDIGO stage."
                ),
            )
        )
    if "aspirin_recommendation" in expected:
        passed = expected["aspirin_recommendation"].lower() in combined_text.lower()
        findings.append(
            _finding(
                status="pass" if passed else "fail",
                category="report",
                severity="high" if not passed else "low",
                key="aspirin_recommendation",
                expected=expected["aspirin_recommendation"],
                actual=combined_text if passed else None,
                explanation=(
                    "Aspirin recommendation matched expected wording signal."
                    if passed
                    else "Aspirin recommendation did not match expected wording signal."
                ),
            )
        )
    if "lipid_recommendation_contains" in expected:
        passed = expected["lipid_recommendation_contains"].lower() in combined_text.lower()
        findings.append(
            _finding(
                status="pass" if passed else "fail",
                category="report",
                severity="high" if not passed else "low",
                key="lipid_recommendation_contains",
                expected=expected["lipid_recommendation_contains"],
                actual=combined_text if passed else None,
                explanation=(
                    "Lipid recommendation matched expected wording signal."
                    if passed
                    else "Lipid recommendation did not match expected wording signal."
                ),
            )
        )
    diagnoses = actual.get("diagnoses") or []
    findings.append(
        _finding(
            status="pass" if diagnoses else "warn",
            category="report",
            severity="low",
            key="diagnoses",
            expected="diagnosis candidates available",
            actual=bool(diagnoses),
            explanation=(
                "Diagnosis candidates are available in QA export."
                if diagnoses
                else "Diagnosis candidates were not available in QA export."
            ),
        )
    )
    return findings


def _ui_findings(actual: dict) -> list[Finding]:
    text = actual.get("visible_ui_text") or ""
    has_visible_text = bool(text.strip())
    return [
        _finding(
            status="pass" if has_visible_text else "warn",
            category="ui",
            severity="low",
            key="visible_ui_text",
            expected="visible UI summary text available",
            actual=has_visible_text,
            explanation=(
                "Visible UI summary text is available."
                if has_visible_text
                else "Visible UI summary text was not available."
            ),
        )
    ]


def compare_case(case_id: str) -> dict:
    actual_path = OUTPUT_DIR / f"{case_id}_actual.json"
    expected_path = EXPECTED_DIR / f"{case_id}_expected.json"
    actual = _load_json(actual_path)
    expected = _load_json(expected_path)
    parsed = actual.get("parsed_patient_json") or {}

    findings: list[Finding] = []
    for key in FIELD_MAP:
        finding = _compare_field(expected, parsed, key)
        if finding:
            findings.append(finding)
    for key in (
        "albuminuria_category",
        "diabetes_range",
        "prediabetes_range",
        "aspirin_primary_prevention_indicated",
        "lipid_therapy_reasonable",
    ):
        finding = _compare_derived(expected, parsed, key)
        if finding:
            findings.append(finding)
    findings.extend(_report_findings(actual))
    findings.extend(_interpretation_findings(expected, actual))
    findings.extend(_ui_findings(actual))

    status = "FAIL" if any(item.status == "fail" for item in findings) else "PASS"
    if status == "PASS" and any(item.status == "warn" for item in findings):
        status = "WARN"
    return {
        "case_id": case_id,
        "status": status,
        "counts": {
            "pass": sum(1 for item in findings if item.status == "pass"),
            "warn": sum(1 for item in findings if item.status == "warn"),
            "fail": sum(1 for item in findings if item.status == "fail"),
        },
        "findings": [asdict(item) for item in findings],
    }


def write_reports(case_id: str, comparison: dict) -> tuple[Path, Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUTPUT_DIR / f"{case_id}_comparison.json"
    md_path = OUTPUT_DIR / f"{case_id}_comparison.md"
    json_path.write_text(json.dumps(comparison, indent=2, default=str), encoding="utf-8")

    lines = [
        f"# RCCKM QA Comparison: {case_id}",
        "",
        f"Status: **{comparison['status']}**",
        "",
        "| Status | Category | Severity | Key | Expected | Actual | Explanation |",
        "|---|---|---|---|---|---|---|",
    ]
    for item in comparison["findings"]:
        lines.append(
            "| {status} | {category} | {severity} | `{key}` | {expected} | {actual} | {explanation} |".format(
                status=item["status"],
                category=item["category"],
                severity=item["severity"],
                key=item["key"],
                expected=json.dumps(item["expected"], default=str),
                actual=json.dumps(item["actual"], default=str),
                explanation=str(item["explanation"]).replace("|", "\\|"),
            )
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare RCCKM QA output to expected rules.")
    parser.add_argument("--case", required=True, dest="case_id")
    args = parser.parse_args(argv)

    comparison = compare_case(args.case_id)
    json_path, md_path = write_reports(args.case_id, comparison)
    print(f"case_id: {args.case_id}")
    print(f"status: {comparison['status']}")
    print(f"counts: {comparison['counts']}")
    print(f"json: {json_path}")
    print(f"markdown: {md_path}")
    return 1 if comparison["status"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
