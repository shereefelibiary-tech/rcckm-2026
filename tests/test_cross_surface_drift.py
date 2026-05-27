from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from core.engine import evaluate_patient
from core.patient import Patient
from modules.actions.scaffold import build_domain_actions, render_domain_actions_for_surface
from rcckm.governance import audit_cross_surface_alignment, extract_domain_signals
from renderers.emr_renderer import render_emr_note
from renderers.patient_roadmap import render_patient_roadmap_text
from ui.demo_case_gallery import DEMO_CASES, build_demo_patient
from ui.report_layout import _build_targets_html


ROOT = Path(__file__).resolve().parents[1]
GOLDEN_CASES_PATH = ROOT / "tests" / "golden_cases" / "golden_cases.json"


DEMO_DRIVER_TERMS = {
    "high_apob_discordance": ("ApoB", "particle burden"),
    "south_asian_ancestry_context": ("South Asian",),
    "rheumatoid_arthritis_risk_enhancer": ("RA", "rheumatoid arthritis"),
    "ckd_albuminuria": ("albuminuria", "UACR"),
    "ckd_g3a_a2": ("CKD", "albuminuria"),
    "cac_300_high_plaque_burden": ("CAC 350", "plaque burden"),
    "cac_100_high_plaque_burden": ("CAC", "plaque"),
    "cac_1_99_plaque_present": ("CAC", "plaque"),
    "cac_zero_ambiguity_resolution": ("CAC 0",),
    "incidental_cac_on_ct": ("Incidental", "CAC"),
    "breast_arterial_calcification_demo": ("Breast arterial calcification",),
    "severe_secondary_prevention": ("secondary prevention", "ASCVD"),
}


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", str(text or ""))


def _surface_bundle(patient: Patient) -> dict[str, str]:
    result = evaluate_patient(patient)
    domains = build_domain_actions(patient, result)
    return {
        "action": "\n".join(render_domain_actions_for_surface(domains, surface="action_card")),
        "emr": render_emr_note(patient, result),
        "roadmap": render_patient_roadmap_text(patient, result),
        "targets": _strip_html(_build_targets_html(result, patient)),
        "demo": "",
    }


def _render_demo_bundle(case_name: str) -> dict[str, str]:
    patient = build_demo_patient(case_name)
    surfaces = _surface_bundle(patient)
    label = next((label for label, name in DEMO_CASES if name == case_name), case_name)
    surfaces["demo"] = "\n".join(
        [
            f"DEMO: {label}",
            f"CASE: {case_name}",
            "EMR:",
            surfaces["emr"],
            "PATIENT ROADMAP:",
            surfaces["roadmap"],
            "ACTIONS:",
            surfaces["action"],
            "TARGETS:",
            surfaces["targets"],
        ]
    )
    return surfaces


def _load_golden_cases() -> list[tuple[str, Patient]]:
    raw_cases = json.loads(GOLDEN_CASES_PATH.read_text(encoding="utf-8"))
    return [(case["name"], Patient(**case["patient"])) for case in raw_cases]


def _assert_no_surface_drift(case_name: str, surfaces: dict[str, str], patient: Patient) -> None:
    action = surfaces["action"]
    emr = surfaces["emr"]
    roadmap = surfaces["roadmap"]
    targets = surfaces["targets"]
    demo = surfaces.get("demo", "")
    all_text = "\n".join(surfaces.values())
    action_signals = extract_domain_signals(action)
    emr_signals = extract_domain_signals(emr)
    roadmap_signals = extract_domain_signals(roadmap)
    target_signals = extract_domain_signals(targets)
    all_signals = extract_domain_signals(all_text)

    findings = audit_cross_surface_alignment(action, emr, "\n".join([roadmap, targets, demo]))
    assert findings == [], f"{case_name}: {[finding.message for finding in findings]}"

    if action_signals["lipid_intensify"]:
        assert (
            emr_signals["lipid_intensify"] or "lipid-lowering therapy" in emr.lower()
        ), f"Drift detected: Action card says lipid intensification but EMR lacks lipid intensification. Case: {case_name}"
    if emr_signals["statin_moderate"] or emr_signals["statin_high"] or emr_signals["lipid_intensify"]:
        assert not action_signals["lipid_no_escalation"], (
            f"Drift detected: EMR recommends lipid therapy but Action says no lipid escalation. Case: {case_name}"
        )
    if getattr(patient, "cac", None) is not None:
        for surface_name, text in surfaces.items():
            assert "cac not performed" not in text.lower(), (
                f"Drift detected: CAC is measured but {surface_name} says CAC not performed. Case: {case_name}"
            )
    if action_signals["cac_measured"]:
        assert not emr_signals["cac_recommend_obtain"], (
            f"Drift detected: Action says CAC already measured but EMR recommends obtaining CAC. Case: {case_name}"
        )
        assert not roadmap_signals["cac_recommend_obtain"], (
            f"Drift detected: Action says CAC already measured but roadmap recommends obtaining CAC. Case: {case_name}"
        )
    if action_signals["kidney_albuminuria"]:
        assert emr_signals["kidney_albuminuria"], (
            f"Drift detected: Action card mentions albuminuria but EMR lacks UACR/albuminuria context. Case: {case_name}"
        )
    if action_signals["aspirin_negative"] and (emr_signals["aspirin_positive"] or roadmap_signals["aspirin_positive"]):
        assert action_signals["aspirin_positive"] or all_signals["secondary_prevention"], (
            f"Drift detected: aspirin negative and positive recommendations conflict. Case: {case_name}"
        )
    if getattr(patient, "clinical_ascvd", False):
        forbidden = "prevention worth discussing"
        assert forbidden not in all_text.lower(), (
            f"Drift detected: clinical ASCVD case uses primary-prevention de-risking language. Case: {case_name}"
        )
    if getattr(patient, "cac", None) and not getattr(patient, "clinical_ascvd", False):
        assert "secondary-prevention" not in all_text.lower(), (
            f"Drift detected: CAC-only primary prevention case calls itself secondary prevention. Case: {case_name}"
        )
    assert target_signals or targets.strip(), f"Targets surface did not render or produce extractable text. Case: {case_name}"


@pytest.mark.parametrize("label,case_name", DEMO_CASES, ids=[name for _label, name in DEMO_CASES])
def test_demo_cases_have_no_cross_surface_drift(label: str, case_name: str):
    patient = build_demo_patient(case_name)
    surfaces = _render_demo_bundle(case_name)
    _assert_no_surface_drift(case_name, surfaces, patient)

    combined = "\n".join(surfaces.values()).lower()
    for term in DEMO_DRIVER_TERMS.get(case_name, ()):
        assert term.lower() in combined, (
            f"Demo driver missing from risk context/recommendations: {term}. Case: {case_name}"
        )


@pytest.mark.parametrize("case_name,patient", _load_golden_cases(), ids=[name for name, _patient in _load_golden_cases()])
def test_golden_cases_have_no_cross_surface_drift(case_name: str, patient: Patient):
    surfaces = _surface_bundle(patient)
    _assert_no_surface_drift(case_name, surfaces, patient)


def test_extract_domain_signals_detects_core_surface_semantics():
    signals = extract_domain_signals(
        "Lipid lowering: Intensify lipid-lowering. CAC 350 already measured. "
        "Kidney protection: Monitor albuminuria; UACR 45. "
        "Aspirin / antiplatelet: Not routine for primary prevention."
    )

    assert signals["lipid_intensify"]
    assert signals["cac_measured"]
    assert signals["kidney_albuminuria"]
    assert signals["aspirin_negative"]
