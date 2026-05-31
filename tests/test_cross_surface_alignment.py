from __future__ import annotations

import pytest

from core.engine import evaluate_patient
from modules.actions.scaffold import (
    ACTION_PANEL_DOMAIN_ORDER,
    build_domain_actions,
    render_domain_actions_for_surface,
)
from rcckm.governance import audit_cross_surface_alignment
from renderers.emr_renderer import render_emr_note
from renderers.patient_roadmap import render_patient_roadmap_text
from ui.demo_case_gallery import DEMO_CASES, build_demo_patient


REQUIRED_DOMAIN_ORDER = [
    "lipid_lowering",
    "plaque_cac",
    "kidney_protection",
    "blood_pressure",
    "glycemia_metabolic",
    "aspirin_antiplatelet",
]


def _surface_bundle(case_name: str):
    patient = build_demo_patient(case_name)
    result = evaluate_patient(patient)
    domains = build_domain_actions(patient, result)
    action_text = "\n".join(render_domain_actions_for_surface(domains, surface="action_card"))
    emr_text = render_emr_note(patient, result)
    patient_text = render_patient_roadmap_text(patient, result)
    return domains, action_text, emr_text, patient_text


@pytest.mark.parametrize("label,case_name", DEMO_CASES, ids=[name for _label, name in DEMO_CASES])
def test_all_demo_surfaces_share_structured_domain_actions(label, case_name):
    domains, action_text, emr_text, patient_text = _surface_bundle(case_name)
    domain_ids = [domain.domain_id for domain in domains]

    assert [domain_id for domain_id in domain_ids if domain_id in REQUIRED_DOMAIN_ORDER] == REQUIRED_DOMAIN_ORDER
    assert all(domain_id in ACTION_PANEL_DOMAIN_ORDER for domain_id in domain_ids)
    assert all(domain.action_card_line for domain in domains), label
    assert all(
        domain.patient_line
        or (domain.domain_id == "data_to_clarify" and not domain.detail_lines)
        for domain in domains
    ), label
    assert all(
        domain.emr_line
        or (domain.domain_id == "data_to_clarify" and not domain.detail_lines)
        for domain in domains
    ), label
    assert action_text.strip(), label
    assert emr_text.strip(), label
    assert patient_text.strip(), label
    findings = audit_cross_surface_alignment(action_text, emr_text, patient_text)
    assert findings == [], f"{label}: {[finding.message for finding in findings]}"


@pytest.mark.parametrize(
    "case_name,action_terms,emr_terms,patient_terms",
    [
        (
            "high_apob_discordance",
            ("Discuss moderate-intensity statin", "ApoB 125; target <90"),
            ("Discuss moderate-intensity statin", "ApoB <90"),
            ("cholesterol",),
        ),
        (
            "south_asian_ancestry_context",
            ("Discuss moderate-intensity statin", "ApoB 108; target <90"),
            ("Discuss moderate-intensity statin", "South Asian ancestry"),
            ("cholesterol",),
        ),
        (
            "rheumatoid_arthritis_risk_enhancer",
            ("Inflammatory risk enhancer", "RA is a risk enhancer"),
            ("Context: RA", "No lipid-lowering medication indicated"),
            ("rheumatoid arthritis",),
        ),
        (
            "ckd_albuminuria",
            ("Discuss moderate-intensity statin", "Monitor albuminuria"),
            ("Discuss moderate-intensity statin", "UACR"),
            ("kidney",),
        ),
        (
            "cac_300_high_plaque_burden",
            ("High-intensity therapy indicated", "CAC 350"),
            ("High-intensity lipid-lowering therapy indicated", "CAC 350."),
            ("very high burden",),
        ),
        (
            "severe_secondary_prevention",
            ("Secondary-prevention lipid therapy", "Antiplatelet therapy"),
            ("Secondary-prevention lipid-lowering therapy", "Secondary-prevention antiplatelet therapy"),
            ("known cardiovascular disease",),
        ),
        (
            "cac_zero_ambiguity_resolution",
            ("CAC 0", "Discuss moderate-intensity statin"),
            ("CAC 0", "Moderate-intensity statin"),
            ("CAC 0",),
        ),
        (
            "healthy_low_risk_prevention",
            ("No lipid-lowering medication indicated",),
            ("No lipid-lowering medication indicated", "No kidney action"),
            ("cholesterol",),
        ),
    ],
)
def test_representative_demo_domain_semantics_match_across_surfaces(
    case_name,
    action_terms,
    emr_terms,
    patient_terms,
):
    _domains, action_text, emr_text, patient_text = _surface_bundle(case_name)

    for term in action_terms:
        assert term.lower() in action_text.lower(), term
    for term in emr_terms:
        assert term.lower() in emr_text.lower(), term
    for term in patient_terms:
        assert term.lower() in patient_text.lower(), term


def test_cross_surface_alignment_governance_reports_domain_specific_mismatches():
    findings = audit_cross_surface_alignment(
        action_card_text=(
            "Lipid lowering: No lipid-lowering medication indicated.\n"
            "Plaque: Very high burden (CAC 350).\n"
            "Kidney protection: No kidney action.\n"
            "Aspirin / antiplatelet: Not indicated."
        ),
        emr_text=(
            "Recommendations:\n"
            "- High-intensity lipid-lowering therapy indicated.\n"
            "- CAC not performed.\n"
            "- Add SGLT2 inhibitor now.\n"
            "- Start aspirin therapy."
        ),
        patient_text="",
    )

    messages = " ".join(finding.message.lower() for finding in findings)
    assert "lipid" in messages
    assert "cac" in messages
    assert "kidney" in messages
    assert "aspirin" in messages


def test_emr_and_roadmap_domain_order_tracks_action_domain_order():
    patient = build_demo_patient("cac_300_high_plaque_burden")
    result = evaluate_patient(patient)
    domain_ids = [domain.domain_id for domain in build_domain_actions(patient, result)]

    assert [domain_id for domain_id in domain_ids if domain_id in REQUIRED_DOMAIN_ORDER] == REQUIRED_DOMAIN_ORDER

    emr_text = render_emr_note(patient, result).lower()
    emr_recommendations = emr_text.split("recommendations:", 1)[-1]
    roadmap_text = render_patient_roadmap_text(patient, result).lower()
    roadmap_next_steps = roadmap_text.split("step 4", 1)[-1]

    emr_terms = ("lipids:", "plaque:", "kidney:", "bp:", "glycemia:", "aspirin:")
    roadmap_terms = ("cholesterol:", "coronary plaque:", "kidneys:", "blood pressure:", "blood sugar:", "aspirin:")

    emr_positions = [emr_recommendations.index(term) for term in emr_terms]
    roadmap_positions = [roadmap_next_steps.index(term) for term in roadmap_terms]

    assert emr_positions == sorted(emr_positions)
    assert roadmap_positions == sorted(roadmap_positions)
