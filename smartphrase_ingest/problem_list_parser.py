from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


PROOF_DATA_DERIVED = "data_derived"
PROOF_EXPLICIT_STRUCTURED = "explicit_structured"
PROOF_ACTIVE_MEDICATION = "active_medication"
PROOF_PROBLEM_LIST = "problem_list"
PROOF_NARRATIVE = "narrative"
PROOF_UNKNOWN = "unknown"


@dataclass(frozen=True)
class ProblemListSignal:
    """One controlled diagnosis signal extracted from problem-list text."""

    field: str
    value: Any
    source_text: str
    confidence: float = 0.85
    review_required: bool = False
    proof_level: str = PROOF_PROBLEM_LIST
    reason: str = "problem list diagnosis"

    @property
    def source(self) -> str:
        return "problem_list"


def _first_match(block: str, patterns: tuple[str, ...], exclude: tuple[str, ...] = ()) -> str:
    for line in (block or "").splitlines():
        clean = line.strip(" -\t")
        if not clean:
            continue
        if any(re.search(pattern, clean, re.IGNORECASE) for pattern in exclude):
            continue
        if any(re.search(pattern, clean, re.IGNORECASE) for pattern in patterns):
            return clean
    return ""


def _add(signals: list[ProblemListSignal], field: str, evidence: str, **kwargs: Any) -> None:
    if evidence:
        signals.append(ProblemListSignal(field=field, value=True, source_text=evidence, **kwargs))


def extract_problem_list_signals(block: str) -> list[ProblemListSignal]:
    """Return review-safe structured signals from a diagnosis/problem-list block."""
    signals: list[ProblemListSignal] = []

    ascvd = _first_match(
        block,
        (
            r"\bcoronary\s+artery\s+disease\b",
            r"\bCAD\b",
            r"\bmyocardial\s+infarction\b",
            r"\bMI\b",
            r"\bNSTEMI\b",
            r"\bSTEMI\b",
            r"\bPCI\b",
            r"\bCABG\b",
            r"\bcoronary\s+stent\b",
            r"\bischemic\s+stroke\b",
            r"\blacunar\s+infarction\b",
            r"\bTIA\b",
            r"\bPAD\b",
            r"\bperipheral\s+arter(?:y|ial)\s+disease\b",
        ),
        (
            r"\bfamily\s+history\b",
            r"\bsubarachnoid\s+hemorrhage\b",
            r"\bSAH\b",
            r"\baneurysm\b",
            r"\bRBBB\b",
            r"\batrial\s+flutter\b",
            r"\bpacemaker\b",
        ),
    )
    if ascvd:
        signals.append(
            ProblemListSignal(
                field="clinical_ascvd_review",
                value=True,
                source_text=ascvd,
                confidence=0.75,
                review_required=True,
                reason="Clinical ASCVD found in problem list; confirm.",
            )
        )

    hemorrhagic = _first_match(
        block,
        (
            r"\bsubarachnoid\s+hemorrhage\b",
            r"\bSAH\b",
            r"\bruptured\b[^\n]*\baneurysm\b",
            r"\baneurysm\b",
        ),
    )
    if hemorrhagic:
        signals.append(
            ProblemListSignal(
                field="cerebrovascular_review",
                value=True,
                source_text=hemorrhagic,
                confidence=0.7,
                review_required=True,
                reason="Prior cerebrovascular event; determine ischemic vs hemorrhagic history.",
            )
        )

    sleep_review = _first_match(
        block,
        (
            r"\bsuspected\s+sleep\s+apnea\b",
            r"\bpossible\s+(?:OSA|obstructive\s+sleep\s+apnea|sleep\s+apnea)\b",
            r"\brule\s+out\s+(?:OSA|obstructive\s+sleep\s+apnea|sleep\s+apnea)\b",
            r"\bsnoring\b",
            r"\bhypersomnia\b",
            r"\bnon[-\s]?restorative\s+sleep\b",
        ),
    )
    if sleep_review:
        signals.append(
            ProblemListSignal(
                field="sleep_apnea_review",
                value=True,
                source_text=sleep_review,
                confidence=0.7,
                review_required=True,
                reason="Possible sleep apnea.",
            )
        )
    else:
        _add(
            signals,
            "osa",
            _first_match(
                block,
                (
                    r"\bOSA\b",
                    r"\bobstructive\s+sleep\s+apnea\b",
                    r"\bcomplex\s+sleep\s+apnea\b",
                    r"\bsleep\s+apnea\b",
                ),
                (r"\bsuspected\b", r"\bpossible\b", r"\brule\s+out\b"),
            ),
        )

    _add(
        signals,
        "diabetes",
        _first_match(
            block,
            (
                r"\btype\s+2\s+diabetes\s+mellitus\b",
                r"\bT2DM\b",
                r"\bDM2\b",
                r"\bdiabetes\s+mellitus\b",
                r"\bdiabetic\s+(?:nephropathy|CKD|kidney\s+disease)\b",
                r"\bdiabetes\s+with\s+(?:hyperglycemia|circulatory\s+complication)\b",
                r"\bE11(?:\.|$)",
            ),
        ),
    )
    _add(
        signals,
        "masld",
        _first_match(
            block,
            (
                r"\bMASLD\b",
                r"\bNAFLD\b",
                r"\bfatty\s+liver\b",
                r"\bhepatic\s+steatosis\b",
                r"\bsteatosis\s+of\s+liver\b",
            ),
        ),
    )
    _add(
        signals,
        "ckd",
        _first_match(
            block,
            (
                r"\bchronic\s+kidney\s+disease\b",
                r"\bCKD(?:\s+stage\s+[2345][ab]?)?\b",
                r"\bdiabetic\s+nephropathy\b",
                r"\balbuminuria\b",
                r"\bproteinuria\b",
                r"\bmicroalbuminuria\b",
            ),
        ),
    )

    for field, patterns in (
        ("rheumatoid_arthritis", (r"\brheumatoid\s+arthritis\b", r"\bseropositive\s+rheumatoid\s+arthritis\b")),
        ("psoriasis", (r"\bpsoriasis\b", r"\bpsoriatic\s+arthritis\b")),
        ("sle", (r"\bSLE\b", r"\blupus\b", r"\bsystemic\s+lupus\b")),
        ("ibd", (r"\binflammatory\s+bowel\s+disease\b", r"\bCrohn'?s\b", r"\bulcerative\s+colitis\b", r"\bIBD\b")),
    ):
        _add(signals, field, _first_match(block, patterns))

    inflammatory_review = _first_match(
        block,
        (
            r"\bpolyarthritis\b",
            r"\bpositive\s+rheumatoid\s+factor\b",
            r"\bpositive\s+RF\b",
            r"\bRF\s+positive\b",
            r"\barthralgia\b",
            r"\belevated\s+inflammatory\s+markers\b",
        ),
        (
            r"\brheumatoid\s+arthritis\b",
            r"\bpsoriatic\s+arthritis\b",
        ),
    )
    if inflammatory_review:
        signals.append(
            ProblemListSignal(
                field="inflammatory_arthritis_review",
                value=True,
                source_text=inflammatory_review,
                confidence=0.65,
                review_required=True,
                reason="Inflammatory arthritis review.",
            )
        )

    family_detail = _first_match(
        block,
        (
            r"\b(?:father|mother|brother|sister|sibling)\b[^\n]{0,40}\b(?:MI|myocardial\s+infarction|heart\s+attack|stroke|CABG|PCI)\b[^\n]{0,30}\bage\s+\d{1,3}\b",
            r"\b(?:father|mother|brother|sister|sibling)\b[^\n]{0,40}\b(?:MI|myocardial\s+infarction|heart\s+attack|stroke|CABG|PCI)\b[^\n]{0,30}\bat\s+\d{1,3}\b",
        ),
    )
    if family_detail:
        signals.append(
            ProblemListSignal(
                field="family_history_detail",
                value=True,
                source_text=family_detail,
                confidence=0.9,
                review_required=False,
                reason="family history detail",
            )
        )
    else:
        premature = _first_match(
            block,
            (
                r"\bfamily\s+history\s+of\s+premature\s+(?:CAD|coronary\s+artery\s+disease|ASCVD|MI|ischemic\s+heart\s+disease)\b",
                r"\bpremature\s+family\s+history\s+of\s+(?:CAD|coronary\s+artery\s+disease|ASCVD|MI|ischemic\s+heart\s+disease)\b",
            ),
        )
        if premature:
            signals.append(
                ProblemListSignal(
                    field="family_history_premature_review",
                    value=True,
                    source_text=premature,
                    confidence=0.75,
                    review_required=True,
                    reason="Family history of premature ASCVD; confirm relationship and age.",
                )
            )
        generic_family = _first_match(
            block,
            (
                r"\bfamily\s+history\s+of\s+(?:CAD|coronary\s+artery\s+disease|ischemic\s+heart\s+disease|MI|ASCVD)\b",
            ),
        )
        if generic_family:
            signals.append(
                ProblemListSignal(
                    field="family_history_review",
                    value=True,
                    source_text=generic_family,
                    confidence=0.65,
                    review_required=True,
                    reason="Family history of CAD; premature status not specified.",
                )
            )

    _add(signals, "suspected_fh_hefh", _first_match(block, (r"\bfamilial\s+hypercholesterolemia\b", r"\bsuspected\s+FH\b", r"\bHeFH\b")))
    for field, patterns in (
        ("pcos_or_irregular_menses", (r"\bPCOS\b", r"\bpolycystic\s+ovary\b")),
        ("gestational_diabetes", (r"\bgestational\s+diabetes\b", r"\bGDM\b")),
        ("preeclampsia", (r"\bpreeclampsia\b", r"\bpre[-\s]?eclampsia\b")),
        ("gestational_hypertension", (r"\bgestational\s+hypertension\b",)),
        ("premature_menopause", (r"\bpremature\s+menopause\b", r"\bearly\s+menopause\b")),
        ("preterm_delivery", (r"\bpreterm\s+delivery\b",)),
        ("recurrent_pregnancy_loss", (r"\brecurrent\s+pregnancy\s+loss\b",)),
        ("small_for_gestational_age", (r"\bsmall\s+for\s+gestational\s+age\b",)),
    ):
        _add(signals, field, _first_match(block, patterns))

    active_cancer = _first_match(block, (r"\bactive\s+cancer\b", r"\bcurrent\s+cancer\b", r"\bundergoing\s+(?:chemo|radiation|immunotherapy)\b"))
    _add(signals, "active_cancer", active_cancer)

    return signals
