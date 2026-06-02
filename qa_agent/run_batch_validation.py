from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import sync_playwright
except ImportError as exc:
    raise SystemExit(
        "Playwright is required.\n"
        "Install with:\n"
        "  pip install playwright\n"
        "  playwright install chromium"
    ) from exc

from qa_agent.discrepancy_review import review_case, write_review
from qa_agent.generate_cases import generate_cases
from qa_agent.guideline_oracle import oracle_from_patient
from qa_agent.run_single_case import _click_button_if_present, _fill_main_textarea
from qa_agent.ui_quality_review import review_payload as review_ui_quality_payload
from qa_agent.ui_quality_review import write_case_review as write_ui_quality_case_review


ROOT = Path(__file__).resolve().parent
GENERATED_CASES_DIR = ROOT / "generated_cases"
OUTPUT_DIR = ROOT / "outputs"
REPORT_DIR = ROOT / "reports"
DEFAULT_URL = "http://localhost:8502/?qa_mode=1"


PARSER_FIELD_MAP = {
    "age": "age",
    "sex": "sex",
    "sbp": "sbp",
    "dbp": "dbp",
    "ldl_c": "ldl_c",
    "apob": "apob",
    "triglycerides": "triglycerides",
    "hdl": "hdl_c",
    "a1c": "a1c",
    "egfr": "egfr",
    "uacr": "uacr",
    "cac": "cac",
    "smoking": "current_smoker",
    "diabetes": "diabetes",
    "clinical_ascvd": "clinical_ascvd",
    "family_history_premature_ascvd": "family_history_premature_ascvd",
    "lp_a_value": "lp_a_value",
}


DOMAIN_CATEGORY = {
    "CKM stage": "CKM",
    "KDIGO stage": "KDIGO",
    "risk level": "risk level",
    "aspirin recommendation": "aspirin",
    "lipid recommendation": "lipids",
    "diagnosis signals": "diagnoses",
    "albuminuria category": "KDIGO",
}


@dataclass
class BatchFinding:
    case_id: str
    status: str
    category: str
    severity: str
    key: str
    expected: Any
    actual: Any
    explanation: str


def _load_manifest(case_dir: Path) -> list[dict[str, Any]]:
    manifest_path = case_dir / "manifest.json"
    if not manifest_path.exists():
        return []
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _ensure_cases(count: int, case_dir: Path) -> list[dict[str, Any]]:
    manifest = _load_manifest(case_dir)
    if len(manifest) < count:
        manifest = generate_cases(count=count, output_dir=case_dir)
    return manifest[:count]


def _normalize(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _numbers_match(expected: Any, actual: Any) -> bool:
    try:
        return abs(float(expected) - float(actual)) <= 0.05
    except (TypeError, ValueError):
        return False


def _values_match(expected: Any, actual: Any) -> bool:
    if expected is None:
        return actual in (None, "", "Not available")
    if isinstance(expected, bool):
        return bool(actual) is expected
    if isinstance(expected, (int, float)):
        return _numbers_match(expected, actual)
    return _normalize(expected) == _normalize(actual)


def _parser_severity(source_key: str) -> str:
    if source_key in {"age", "sex", "clinical_ascvd", "diabetes", "cac", "uacr"}:
        return "high"
    if source_key in {"ldl_c", "apob", "a1c", "egfr", "lp_a_value"}:
        return "medium"
    return "low"


def _compare_parser_fields(case_id: str, source_patient: dict[str, Any], parsed: dict[str, Any]) -> list[BatchFinding]:
    findings: list[BatchFinding] = []
    for source_key, parsed_key in PARSER_FIELD_MAP.items():
        expected = source_patient.get(source_key)
        if expected is None:
            continue
        actual = parsed.get(parsed_key)
        if _values_match(expected, actual):
            continue
        findings.append(
            BatchFinding(
                case_id=case_id,
                status="FAIL",
                category="parser",
                severity=_parser_severity(source_key),
                key=source_key,
                expected=expected,
                actual=actual,
                explanation=f"Parsed `{parsed_key}` did not match synthetic source `{source_key}`.",
            )
        )
    return findings


def _review_findings(case_id: str, review: dict[str, Any]) -> list[BatchFinding]:
    findings: list[BatchFinding] = []
    for item in review.get("discrepancies") or []:
        status = str(item.get("status", "WARN")).upper()
        category = DOMAIN_CATEGORY.get(item.get("domain"), "report rendering")
        severity = "high" if status == "FAIL" else "medium"
        if item.get("domain") == "diagnosis signals":
            severity = "low" if status == "WARN" else severity
        findings.append(
            BatchFinding(
                case_id=case_id,
                status=status,
                category=category,
                severity=severity,
                key=item.get("domain", "discrepancy"),
                expected=item.get("expected"),
                actual=item.get("actual"),
                explanation=item.get("rationale", ""),
            )
        )
    return findings


def _ui_findings(case_id: str, review: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"case_id": case_id, **item} for item in review.get("findings", [])]


def _overall_status(findings: list[BatchFinding]) -> str:
    if any(item.status == "FAIL" for item in findings):
        return "FAIL"
    if any(item.status == "WARN" for item in findings):
        return "WARN"
    return "PASS"


def _capture_case(page: Any, app_url: str, case_id: str, smartphrase: str, *, screenshot_path: Path | None) -> dict[str, Any]:
    page.goto(app_url, wait_until="domcontentloaded", timeout=60_000)
    page.wait_for_selector("textarea", timeout=60_000)
    _fill_main_textarea(page, smartphrase)

    if not _click_button_if_present(page, "Parse and apply", timeout_ms=10_000):
        raise RuntimeError("Could not find or click Parse and apply.")

    qa_export = page.locator('[data-testid="rcckm-qa-export"]')
    qa_export.wait_for(state="attached", timeout=60_000)

    if not _click_button_if_present(page, "Interpret risk", timeout_ms=20_000):
        raise RuntimeError("Could not find or click Interpret risk.")

    payload: dict[str, Any] = {}
    for _attempt in range(120):
        try:
            qa_export.wait_for(state="attached", timeout=10_000)
            raw_json = qa_export.text_content(timeout=10_000) or ""
            payload = json.loads(raw_json)
        except Exception:
            payload = {}
        if payload.get("final_report_text") and payload.get("engine_output_json"):
            break
        page.wait_for_timeout(500)
    else:
        raise RuntimeError(f"Timed out waiting for interpreted QA export for {case_id}.")

    if screenshot_path:
        page.screenshot(path=str(screenshot_path), full_page=True)
    return payload


def _capture_case_with_retry(
    browser: Any,
    app_url: str,
    case_id: str,
    smartphrase: str,
    *,
    attempts: int = 2,
) -> tuple[dict[str, Any], Any]:
    last_error: Exception | None = None
    page = None
    for attempt in range(1, attempts + 1):
        page = browser.new_page(viewport={"width": 1440, "height": 1400})
        try:
            payload = _capture_case(page, app_url, case_id, smartphrase, screenshot_path=None)
            return payload, page
        except Exception as exc:
            last_error = exc
            if attempt >= attempts:
                return {}, page
            page.close()
    raise RuntimeError(last_error or f"Could not capture case {case_id}.")


def _write_case_outputs(case_id: str, payload: dict[str, Any], page_text: str = "") -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"{case_id}_actual.json"
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    (OUTPUT_DIR / f"{case_id}_report.txt").write_text(
        payload.get("final_report_text") or "",
        encoding="utf-8",
    )
    (OUTPUT_DIR / f"{case_id}_page.txt").write_text(page_text, encoding="utf-8")
    return path


def _write_reports(
    results: list[dict[str, Any]],
    findings: list[BatchFinding],
    ui_findings: list[dict[str, Any]],
) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    counts = Counter(item["status"] for item in results)
    categories = Counter(item.category for item in findings)
    ui_categories = Counter(item["category"] for item in ui_findings)
    severities = Counter(item.severity for item in findings)
    ui_severities = Counter(item["severity"] for item in ui_findings)
    summary = {
        "total_cases": len(results),
        "pass": counts["PASS"],
        "warn": counts["WARN"],
        "fail": counts["FAIL"],
        "top_discrepancy_categories": dict(categories.most_common()),
        "severity_counts": dict(severities),
        "ui_quality": {
            "finding_count": len(ui_findings),
            "top_categories": dict(ui_categories.most_common()),
            "severity_counts": dict(ui_severities),
        },
        "cases": results,
        "findings": [asdict(item) for item in findings],
        "ui_findings": ui_findings,
    }
    (REPORT_DIR / "summary.json").write_text(
        json.dumps(summary, indent=2, default=str),
        encoding="utf-8",
    )

    lines = [
        "# RCCKM Batch Validation Summary",
        "",
        f"Total cases: {len(results)}",
        f"Pass: {counts['PASS']}",
        f"Warn: {counts['WARN']}",
        f"Fail: {counts['FAIL']}",
        "",
        "## Top Discrepancy Categories",
        "",
    ]
    if categories:
        for category, count in categories.most_common():
            lines.append(f"- {category}: {count}")
    else:
        lines.append("- None")
    lines.extend(["", "## Case Results", ""])
    for item in results:
        lines.append(f"- {item['case_id']}: {item['status']} ({item['phenotype']})")
    (REPORT_DIR / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    with (REPORT_DIR / "failures.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "case_id",
                "status",
                "category",
                "severity",
                "key",
                "expected",
                "actual",
                "explanation",
            ],
        )
        writer.writeheader()
        for item in findings:
            writer.writerow(
                {
                    "case_id": item.case_id,
                    "status": item.status,
                    "category": item.category,
                    "severity": item.severity,
                    "key": item.key,
                    "expected": json.dumps(item.expected, default=str),
                    "actual": json.dumps(item.actual, default=str),
                    "explanation": item.explanation,
                }
            )

    high = [item for item in findings if item.severity == "high"]
    high_lines = ["# High-Severity RCCKM Batch Findings", ""]
    if not high:
        high_lines.append("No high-severity findings.")
    else:
        for item in high:
            high_lines.extend(
                [
                    f"## {item.case_id}: {item.key}",
                    "",
                    f"- Status: {item.status}",
                    f"- Category: {item.category}",
                    f"- Expected: `{json.dumps(item.expected, default=str)}`",
                    f"- Actual: `{json.dumps(item.actual, default=str)}`",
                    f"- Explanation: {item.explanation}",
                    "",
                ]
            )
    (REPORT_DIR / "high_severity.md").write_text("\n".join(high_lines) + "\n", encoding="utf-8")

    ui_lines = [
        "# RCCKM UI Quality Summary",
        "",
        f"Total UI/report findings: {len(ui_findings)}",
        "",
        "## Categories",
        "",
    ]
    if ui_categories:
        for category, count in ui_categories.most_common():
            ui_lines.append(f"- {category}: {count}")
    else:
        ui_lines.append("- None")
    ui_lines.extend(["", "## Findings", ""])
    if not ui_findings:
        ui_lines.append("No UI/report quality findings.")
    else:
        for item in ui_findings:
            ui_lines.extend(
                [
                    f"### {item['case_id']}: {item['finding']}",
                    "",
                    f"- Status: {item['status']}",
                    f"- Severity: {item['severity']}",
                    f"- Category: {item['category']}",
                    f"- Evidence: {item['evidence_excerpt']}",
                    f"- Suggested fix direction: {item['suggested_fix_direction']}",
                    f"- Codex ready: {item['codex_ready']}",
                    "",
                ]
            )
    (REPORT_DIR / "ui_quality_summary.md").write_text("\n".join(ui_lines) + "\n", encoding="utf-8")


def run_batch(*, count: int, app_url: str, case_dir: Path = GENERATED_CASES_DIR) -> dict[str, Any]:
    cases = _ensure_cases(count, case_dir)
    results: list[dict[str, Any]] = []
    all_findings: list[BatchFinding] = []
    all_ui_findings: list[dict[str, Any]] = []
    screenshots_dir = REPORT_DIR / "failure_screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            for case in cases:
                page = None
                case_id = case["case_id"]
                source_payload = json.loads(Path(case["patient_json"]).read_text(encoding="utf-8"))
                source_patient = source_payload.get("patient", source_payload)
                smartphrase = Path(case["smartphrase_text"]).read_text(encoding="utf-8")
                case_findings: list[BatchFinding] = []
                oracle: dict[str, Any] | None = None
                try:
                    payload, page = _capture_case_with_retry(browser, app_url, case_id, smartphrase)
                    if not payload:
                        raise RuntimeError(f"Could not capture interpreted QA export for {case_id}.")
                    page_text = page.locator("body").inner_text() if page is not None else ""
                    _write_case_outputs(case_id, payload, page_text=page_text)
                    parsed = payload.get("parsed_patient_json") or {}
                    oracle = oracle_from_patient(parsed)
                    case_findings.extend(_compare_parser_fields(case_id, source_patient, parsed))
                    review = review_case(case_id)
                    write_review(case_id, review)
                    case_findings.extend(_review_findings(case_id, review))
                    status = _overall_status(case_findings)
                    if status == "FAIL":
                        page.screenshot(path=str(screenshots_dir / f"{case_id}.png"), full_page=True)
                    ui_review = review_ui_quality_payload(
                        case_id=case_id,
                        payload=payload,
                        page_text=page_text,
                        screenshot_path=screenshots_dir / f"{case_id}.png" if status == "FAIL" else None,
                    )
                    write_ui_quality_case_review(case_id, ui_review)
                    all_ui_findings.extend(_ui_findings(case_id, ui_review))
                except (Exception, PlaywrightTimeoutError) as exc:
                    status = "FAIL"
                    case_findings.append(
                        BatchFinding(
                            case_id=case_id,
                            status="FAIL",
                            category="ui",
                            severity="high",
                            key="browser_run",
                            expected="successful QA export",
                            actual=str(exc),
                            explanation="Browser QA run did not complete.",
                        )
                    )
                    try:
                        if page is not None:
                            page.screenshot(path=str(screenshots_dir / f"{case_id}.png"), full_page=True)
                    except Exception:
                        pass
                    ui_review = {
                        "case_id": case_id,
                        "status": "FAIL",
                        "finding_count": 1,
                        "findings": [
                            {
                                "status": "fail",
                                "severity": "high",
                                "category": "visual",
                                "finding": "Browser QA run did not complete.",
                                "evidence_excerpt": str(exc),
                                "suggested_fix_direction": "Stabilize QA export capture before reviewing visible UI/report quality.",
                                "codex_ready": False,
                            }
                        ],
                    }
                    write_ui_quality_case_review(case_id, ui_review)
                    all_ui_findings.extend(_ui_findings(case_id, ui_review))
                all_findings.extend(case_findings)
                results.append(
                    {
                        "case_id": case_id,
                        "phenotype": case.get("phenotype"),
                        "status": status,
                        "oracle": oracle,
                        "finding_count": len(case_findings),
                    }
                )
                print(f"{case_id}: {status} ({len(case_findings)} findings)")
                if page is not None:
                    page.close()
        finally:
            browser.close()

    _write_reports(results, all_findings, all_ui_findings)
    counts = Counter(item["status"] for item in results)
    return {
        "total_cases": len(results),
        "pass": counts["PASS"],
        "warn": counts["WARN"],
        "fail": counts["FAIL"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run RCCKM batch QA validation over synthetic patients.")
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--case-dir", type=Path, default=GENERATED_CASES_DIR)
    parser.add_argument("--url", default=os.environ.get("RCCKM_QA_URL", DEFAULT_URL))
    args = parser.parse_args(argv)

    if args.count < 1:
        parser.error("--count must be at least 1")

    summary = run_batch(count=args.count, app_url=args.url, case_dir=args.case_dir)
    print("Batch validation complete")
    print(f"Total cases: {summary['total_cases']}")
    print(f"Pass: {summary['pass']}")
    print(f"Warn: {summary['warn']}")
    print(f"Fail: {summary['fail']}")
    print(f"Reports: {REPORT_DIR}")
    return 1 if summary["fail"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
