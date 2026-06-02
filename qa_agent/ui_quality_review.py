from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from qa_agent.ui_quality_rules import (
    RuleHit,
    find_contradictions,
    find_duplicate_sections,
    find_filler_language,
    find_language_quality,
    find_report_structure,
    find_visual_smoke_issues,
)


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "outputs"


@dataclass(frozen=True)
class UIQualityFinding:
    status: str
    severity: str
    category: str
    finding: str
    evidence_excerpt: str
    suggested_fix_direction: str
    codex_ready: bool


def _load_text(path: Path | None) -> str:
    if not path or not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _status_from_severity(severity: str) -> str:
    return "fail" if severity == "high" else "warn"


def _from_hit(hit: RuleHit) -> UIQualityFinding:
    return UIQualityFinding(
        status=_status_from_severity(hit.severity),
        severity=hit.severity,
        category=hit.category,
        finding=hit.finding,
        evidence_excerpt=hit.evidence_excerpt,
        suggested_fix_direction=hit.suggested_fix_direction,
        codex_ready=hit.codex_ready,
    )


def _overall_status(findings: list[UIQualityFinding]) -> str:
    if any(item.status == "fail" for item in findings):
        return "FAIL"
    if any(item.status == "warn" for item in findings):
        return "WARN"
    return "PASS"


def review_payload(
    *,
    case_id: str,
    payload: dict[str, Any],
    page_text: str = "",
    screenshot_path: Path | None = None,
    require_screenshot: bool = False,
) -> dict[str, Any]:
    final_report_text = payload.get("final_report_text") or ""
    visible_text = payload.get("visible_ui_text") or ""
    full_page_text = page_text or visible_text
    combined_visible = f"{full_page_text}\n{final_report_text}"
    screenshot_exists: bool | None = None
    if screenshot_path is not None or require_screenshot:
        screenshot_exists = bool(screenshot_path and screenshot_path.exists() and screenshot_path.stat().st_size > 0)

    hits: list[RuleHit] = []
    hits.extend(find_filler_language(combined_visible))
    hits.extend(find_duplicate_sections(final_report_text))
    hits.extend(find_contradictions(payload, combined_visible))
    hits.extend(find_report_structure(final_report_text, payload))
    hits.extend(find_language_quality(combined_visible))
    hits.extend(
        find_visual_smoke_issues(
            page_text=full_page_text,
            final_report_text=final_report_text,
            screenshot_exists=screenshot_exists,
        )
    )
    findings = [_from_hit(hit) for hit in hits]
    return {
        "case_id": case_id,
        "status": _overall_status(findings),
        "finding_count": len(findings),
        "findings": [asdict(item) for item in findings],
    }


def review_case(
    case_id: str,
    *,
    actual_path: Path | None = None,
    page_text_path: Path | None = None,
    screenshot_path: Path | None = None,
    require_screenshot: bool = False,
) -> dict[str, Any]:
    actual = actual_path or OUTPUT_DIR / f"{case_id}_actual.json"
    payload = json.loads(actual.read_text(encoding="utf-8"))
    page_text = _load_text(page_text_path or OUTPUT_DIR / f"{case_id}_page.txt")
    return review_payload(
        case_id=case_id,
        payload=payload,
        page_text=page_text,
        screenshot_path=screenshot_path,
        require_screenshot=require_screenshot,
    )


def write_case_review(case_id: str, review: dict[str, Any], *, output_dir: Path = OUTPUT_DIR) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{case_id}_ui_quality.json"
    md_path = output_dir / f"{case_id}_ui_quality.md"
    json_path.write_text(json.dumps(review, indent=2, default=str), encoding="utf-8")

    lines = [
        f"# RCCKM UI Quality Review: {case_id}",
        "",
        f"Status: **{review['status']}**",
        "",
    ]
    if not review["findings"]:
        lines.append("No UI/report quality findings.")
    else:
        for index, item in enumerate(review["findings"], start=1):
            lines.extend(
                [
                    f"## {index}. {item['finding']} ({item['status']})",
                    "",
                    f"- Severity: {item['severity']}",
                    f"- Category: {item['category']}",
                    f"- Evidence: {item['evidence_excerpt']}",
                    f"- Suggested fix direction: {item['suggested_fix_direction']}",
                    f"- Codex ready: {item['codex_ready']}",
                    "",
                ]
            )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Review RCCKM visible UI/report quality for one QA case.")
    parser.add_argument("--case", required=True, dest="case_id")
    parser.add_argument("--actual-path", type=Path, default=None)
    parser.add_argument("--page-text-path", type=Path, default=None)
    parser.add_argument("--screenshot-path", type=Path, default=None)
    parser.add_argument("--require-screenshot", action="store_true")
    args = parser.parse_args(argv)

    review = review_case(
        args.case_id,
        actual_path=args.actual_path,
        page_text_path=args.page_text_path,
        screenshot_path=args.screenshot_path,
        require_screenshot=args.require_screenshot,
    )
    json_path, md_path = write_case_review(args.case_id, review)
    print(f"case_id: {args.case_id}")
    print(f"status: {review['status']}")
    print(f"findings: {review['finding_count']}")
    print(f"json: {json_path}")
    print(f"markdown: {md_path}")
    return 1 if review["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
