from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from core.engine import evaluate_patient
from core.patient import Patient
from renderers.emr_renderer import render_emr_note
from renderers.patient_roadmap import render_patient_roadmap_text
from tests.helpers import assert_absent, assert_no_contradictory_phrases


ROOT = Path(__file__).resolve().parents[2]
GOLDEN_CASES_PATH = ROOT / "tests" / "golden_cases" / "golden_cases.json"
SNAPSHOT_ROOT = Path(__file__).resolve().parent
EMR_SNAPSHOT_DIR = SNAPSHOT_ROOT / "emr"
ROADMAP_SNAPSHOT_DIR = SNAPSHOT_ROOT / "patient_roadmap"

SELECTED_CASES = (
    "minimal_signal_cac_0",
    "level2_early_metabolic_risk",
    "level3_low_10y_high_lifetime_burden",
    "level3b_atherogenic_30y_ldl_apob",
    "level3b_albuminuria_borderline_prevent",
    "level3b_intermediate_prevent_uacr_missing",
    "cac_350",
    "clinical_ascvd",
    "clinical_ascvd_with_cac_0",
    "ldl_severe_hypercholesterolemia",
    "diabetes_plus_ckd_albuminuria",
    "tg_1000_very_severe",
)

FORBIDDEN_SNAPSHOT_PHRASES = (
    "<div",
    "</div>",
    "<span",
    "</span>",
    "phenotype",
    "inherited risk",
    "genetics",
    "dominant_action",
    "action_domains",
    "risk_continuum_sublevel",
    "Supporting actions:",
)


def _normalize(text: str) -> str:
    lines = str(text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    return "\n".join(line.rstrip() for line in lines).strip() + "\n"


def _load_selected_cases() -> list[dict]:
    cases = {
        case["name"]: case
        for case in json.loads(GOLDEN_CASES_PATH.read_text(encoding="utf-8"))
    }
    missing = [name for name in SELECTED_CASES if name not in cases]
    if missing:
        raise AssertionError(f"Snapshot case(s) missing from golden_cases.json: {missing}")
    return [cases[name] for name in SELECTED_CASES]


def _snapshot_path(kind: str, case_name: str) -> Path:
    if kind == "emr":
        return EMR_SNAPSHOT_DIR / f"{case_name}.txt"
    if kind == "patient_roadmap":
        return ROADMAP_SNAPSHOT_DIR / f"{case_name}.txt"
    raise ValueError(f"Unknown snapshot kind: {kind}")


def _assert_snapshot_safe(text: str) -> None:
    assert_absent(text, FORBIDDEN_SNAPSHOT_PHRASES)
    assert_no_contradictory_phrases(text)


def _assert_or_update_snapshot(path: Path, actual: str) -> None:
    actual = _normalize(actual)
    _assert_snapshot_safe(actual)
    if os.environ.get("UPDATE_SNAPSHOTS") == "1":
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(actual, encoding="utf-8", newline="\n")
        return

    assert path.exists(), (
        f"Missing snapshot: {path}. "
        "Run UPDATE_SNAPSHOTS=1 pytest tests/snapshots/test_output_snapshots.py to create it."
    )
    expected = _normalize(path.read_text(encoding="utf-8"))
    _assert_snapshot_safe(expected)
    assert actual == expected


@pytest.mark.parametrize("case", _load_selected_cases(), ids=lambda case: case["name"])
def test_emr_note_snapshots(case):
    patient = Patient(**case["patient"])
    result = evaluate_patient(patient)

    _assert_or_update_snapshot(
        _snapshot_path("emr", case["name"]),
        render_emr_note(patient, result),
    )


@pytest.mark.parametrize("case", _load_selected_cases(), ids=lambda case: case["name"])
def test_patient_roadmap_snapshots(case):
    patient = Patient(**case["patient"])
    result = evaluate_patient(patient)

    _assert_or_update_snapshot(
        _snapshot_path("patient_roadmap", case["name"]),
        render_patient_roadmap_text(patient, result),
    )
