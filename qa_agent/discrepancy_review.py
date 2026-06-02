from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from qa_agent.guideline_oracle import oracle_from_patient


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "outputs"
DISCREPANCY_DIR = ROOT / "discrepancies"


@dataclass
class Discrepancy:
    status: str
    domain: str
    expected: Any
    actual: Any
    rationale: str
    clinical_significance: str
    suspected_source: str


def _load_actual(case_id: str) -> dict:
    return json.loads((OUTPUT_DIR / f"{case_id}_actual.json").read_text(encoding="utf-8"))


def _text_contains(text: str, expected: str | None) -> bool:
    return bool(expected and expected.lower() in (text or "").lower())


def _nested_get(source: dict | None, *keys: str) -> Any:
    current: Any = source or {}
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _normalize(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _status_for_mismatch(*, expected: Any, actual: Any, domain: str) -> str:
    if _normalize(expected) == _normalize(actual):
        return "PASS"
    if actual in (None, "", [], {}):
        return "WARN"
    if domain in {"diagnosis signals", "lipid recommendation"}:
        return "WARN"
    return "FAIL"


def _append_discrepancy(
    findings: list[Discrepancy],
    *,
    domain: str,
    expected: Any,
    actual: Any,
    rationale: str,
    clinical_significance: str,
    suspected_source: str,
) -> None:
    status = _status_for_mismatch(expected=expected, actual=actual, domain=domain)
    if status == "PASS":
        return
    findings.append(
        Discrepancy(
            status=status,
            domain=domain,
            expected=expected,
            actual=actual,
            rationale=rationale,
            clinical_significance=clinical_significance,
            suspected_source=suspected_source,
        )
    )


def _diagnosis_names(actual: dict) -> set[str]:
    names = set()
    for item in actual.get("diagnoses") or []:
        if isinstance(item, dict):
            name = item.get("name") or item.get("diagnosis")
            if name:
                names.add(str(name).lower())
    return names


def review_case(case_id: str) -> dict:
    actual = _load_actual(case_id)
    parsed = actual.get("parsed_patient_json") or {}
    oracle = oracle_from_patient(parsed)
    report_text = actual.get("final_report_text") or ""
    recommendations_text = actual.get("recommendations_text") or ""
    combined_text = f"{report_text}\n{recommendations_text}"
    findings: list[Discrepancy] = []

    _append_discrepancy(
        findings,
        domain="CKM stage",
        expected=oracle["ckm_stage"],
        actual=_nested_get(actual.get("ckm_stage"), "stage"),
        rationale="Oracle stages CKM from objective plaque, kidney, glycemia, and metabolic inputs.",
        clinical_significance="CKM stage changes the summary frame and may alter kidney/metabolic emphasis.",
        suspected_source="CKM staging export or interpretation layer",
    )
    _append_discrepancy(
        findings,
        domain="KDIGO stage",
        expected=oracle["kdigo_stage"],
        actual=oracle["kdigo_stage"] if _text_contains(combined_text, oracle["kdigo_stage"]) else None,
        rationale="Oracle derives KDIGO from current eGFR and UACR.",
        clinical_significance="KDIGO mismatch can misrepresent kidney risk and albuminuria severity.",
        suspected_source="KDIGO summary/report rendering",
    )
    _append_discrepancy(
        findings,
        domain="risk level",
        expected=oracle["risk_level"],
        actual=_nested_get(actual.get("risk_level"), "level"),
        rationale="Oracle assigns level from clinical ASCVD, CAC, CKM, and actionable risk burden.",
        clinical_significance="Risk level mismatch can alter clinical posture and documentation.",
        suspected_source="Risk continuum classification/export",
    )
    _append_discrepancy(
        findings,
        domain="aspirin recommendation",
        expected=oracle["aspirin_action"],
        actual=oracle["aspirin_action"] if _text_contains(combined_text, oracle["aspirin_action"]) else None,
        rationale="Oracle applies the aspirin framework from ASCVD, CAC, age, and bleeding-risk context.",
        clinical_significance="Aspirin mismatch may cause overuse or underuse of antiplatelet therapy.",
        suspected_source="ActionDomainReadout aspirin renderer or aspirin action selection",
    )
    _append_discrepancy(
        findings,
        domain="lipid recommendation",
        expected=oracle["lipid_action"],
        actual=oracle["lipid_action"] if _text_contains(combined_text, oracle["lipid_action"]) else combined_text,
        rationale="Oracle applies ApoB-first lipid logic with LDL-C, ApoB, CAC, ASCVD, and kidney/risk-enhancer context.",
        clinical_significance="Lipid mismatch may change whether therapy is started, continued, or intensified.",
        suspected_source="Lipid action wording or treatment-posture selection",
    )
    _append_discrepancy(
        findings,
        domain="albuminuria category",
        expected=oracle["albuminuria_category"],
        actual=oracle["albuminuria_category"] if _text_contains(combined_text, oracle["albuminuria_category"]) else None,
        rationale="Oracle maps UACR <30 to A1, 30-299 to A2, and >=300 to A3.",
        clinical_significance="Albuminuria category affects kidney risk language and CKM/KDIGO interpretation.",
        suspected_source="KDIGO/report rendering or UACR propagation",
    )

    actual_diagnoses = _diagnosis_names(actual)
    missing_diagnoses = [
        diagnosis
        for diagnosis in oracle["diagnoses"]
        if not any(diagnosis.lower() in actual_name for actual_name in actual_diagnoses)
    ]
    if missing_diagnoses:
        findings.append(
            Discrepancy(
                status="WARN",
                domain="diagnosis signals",
                expected=oracle["diagnoses"],
                actual=sorted(actual_diagnoses),
                rationale="Oracle diagnosis signals are objective findings expected from current parsed data.",
                clinical_significance="Diagnosis signal mismatch may affect display, coding review, or documentation completeness.",
                suspected_source="Diagnosis synthesis or diagnosis export",
            )
        )

    status = "FAIL" if any(item.status == "FAIL" for item in findings) else "PASS"
    if status == "PASS" and any(item.status == "WARN" for item in findings):
        status = "WARN"
    return {
        "case_id": case_id,
        "status": status,
        "oracle": oracle,
        "discrepancies": [asdict(item) for item in findings],
    }


def write_review(case_id: str, review: dict) -> Path:
    DISCREPANCY_DIR.mkdir(parents=True, exist_ok=True)
    path = DISCREPANCY_DIR / f"{case_id}_review.md"
    lines = [
        f"# RCCKM Discrepancy Review: {case_id}",
        "",
        f"Status: **{review['status']}**",
        "",
    ]
    if not review["discrepancies"]:
        lines.append("No discrepancies found.")
    else:
        for index, item in enumerate(review["discrepancies"], start=1):
            lines.extend(
                [
                    f"## {index}. {item['domain']} ({item['status']})",
                    "",
                    f"- Expected: `{json.dumps(item['expected'], default=str)}`",
                    f"- Actual: `{json.dumps(item['actual'], default=str)}`",
                    f"- Rationale: {item['rationale']}",
                    f"- Clinical significance: {item['clinical_significance']}",
                    f"- Suspected source: {item['suspected_source']}",
                    "",
                ]
            )
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Review RCCKM output against guideline oracle.")
    parser.add_argument("--case", required=True, dest="case_id")
    args = parser.parse_args(argv)
    review = review_case(args.case_id)
    path = write_review(args.case_id, review)
    print(f"case_id: {args.case_id}")
    print(f"status: {review['status']}")
    print(f"discrepancies: {len(review['discrepancies'])}")
    print(f"review: {path}")
    return 1 if review["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
