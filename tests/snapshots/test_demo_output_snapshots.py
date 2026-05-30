from __future__ import annotations

import os
from pathlib import Path

import pytest

from tools.demo_audit import audit_demo_cases, render_demo_output_snapshot
from ui.demo_case_gallery import DEMO_CASES


SNAPSHOT_ROOT = Path(__file__).resolve().parent / "demo_outputs"
UPDATE = os.environ.get("UPDATE_SNAPSHOTS") == "1"
FORBIDDEN = (
    "<div",
    "</div>",
    "<span",
    "</span>",
    "total cardiovascular risk",
    "cardiovascular event",
    "heart failure",
    "inflammatory residual risk",
    "dominant_action",
    "action_domains",
    "may improve confidence",
    "as clinically indicated",
    "if appropriate",
    "when safe",
    "reviewed as part of the prevention plan",
    "interpreted with the overall risk picture",
    "included in the prevention plan",
    "Coronary plaque: Coronary artery plaque",
    "Blood pressure: Blood pressure",
    "does not show an immediate action signal",
    "No immediate blood sugar action is shown",
    "risk-factor control",
    "management as appropriate",
    "incomplete",
    "deficiency",
    "deficient",
    "failed",
    "overdue",
    "should have",
    "missing ApoB",
    "missing CAC",
    "missing UACR",
    "to -",
)


def _normalize(text: str) -> str:
    return "\n".join(line.rstrip() for line in str(text).replace("\r\n", "\n").splitlines()).strip() + "\n"


def _snapshot_path(case_name: str) -> Path:
    return SNAPSHOT_ROOT / f"{case_name}.txt"


@pytest.mark.parametrize("label,case_name", DEMO_CASES, ids=[case for _label, case in DEMO_CASES])
def test_demo_output_snapshots(label, case_name):
    text = _normalize(render_demo_output_snapshot(case_name))
    lowered = text.lower()
    for phrase in FORBIDDEN:
        assert phrase.lower() not in lowered
    assert "10-year ASCVD risk" in text

    path = _snapshot_path(case_name)
    if UPDATE:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    assert path.exists(), f"Missing snapshot: {path}"
    assert text == _normalize(path.read_text(encoding="utf-8"))


def test_demo_audit_summary_snapshot():
    text = _normalize(audit_demo_cases().format_summary())
    assert "Errors: 0" in text
    assert "Demos needing rewrite: none" in text

    path = SNAPSHOT_ROOT / "audit_summary.txt"
    if UPDATE:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    assert path.exists(), f"Missing snapshot: {path}"
    assert text == _normalize(path.read_text(encoding="utf-8"))
