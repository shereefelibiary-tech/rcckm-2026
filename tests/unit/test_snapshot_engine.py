from core.results import RCCKMResult
from core.enums import RiskLevel
from modules.snapshot.engine import build_snapshot_lines


def test_build_snapshot_lines_returns_concise_clinical_synthesis_in_order():
    result = RCCKMResult(
        risk_level=RiskLevel.HIGH,
        prevent_10y_ascvd=8.2,
        prevent_30y_ascvd=24.5,
        kdigo_stage="G3aA2",
        ckm_stage={"stage": 3, "drivers": ["CAC 350"]},
        rss_total=57,
        rss_category="High",
        top_drivers=[
            "CAC 350",
            "ApoB 110 mg/dL",
            "UACR 45 mg/g",
            "A1c 7.1%",
        ],
        clarification={
            "tier": 2,
            "summary": "Next useful clarifier(s): CAC.",
        },
        discordance_insight={
            "status": "uncertain",
            "headline": "High estimated risk with plaque unmeasured.",
        },
    )

    lines = build_snapshot_lines(result)

    assert lines == [
        "RCCKM level: HIGH",
        "CKM stage: Stage 3 — CAC 350",
        "PREVENT 10-year ASCVD risk: 8.2%",
        "PREVENT 30-year ASCVD risk: 24.5%",
        "Plaque: CAC 350",
        "Kidney: G3aA2",
        "Risk Signal Score: 57/100 (High)",
        "Top drivers: CAC 350; ApoB 110 mg/dL; UACR 45 mg/g; A1c 7.1%",
        "Clarification: Next useful clarifier(s): CAC.",
        "Discordance: High estimated risk with plaque unmeasured.",
    ]


def test_build_snapshot_lines_omits_low_tier_clarification_and_aligned_discordance():
    result = RCCKMResult(
        risk_level=RiskLevel.LOW,
        clarification={"tier": 1, "summary": "Measure Lp(a)."},
        discordance_insight={
            "status": "aligned",
            "headline": "No major PREVENT/plaque discordance detected.",
        },
    )

    lines = build_snapshot_lines(result)

    assert lines == ["RCCKM level: LOW"]
