EMR_HEADER = "RISK CONTINUUM CKM"
EMR_LEVEL_LABEL = "Level"
EMR_PREVENT_LABEL = "PREVENT"
EMR_CKM_KIDNEY_PLAQUE_LABEL = "CKM/Kidney/Plaque"
EMR_CONTEXT_LABEL = "Context"

EMR_SECTION_ORDER = [
    "summary",
    "assessment",
    "recommendations",
]

EMR_SUMMARY_LABELS = {
    "level": EMR_LEVEL_LABEL,
    "prevent": EMR_PREVENT_LABEL,
    "ckm": EMR_CKM_KIDNEY_PLAQUE_LABEL,
    "context": EMR_CONTEXT_LABEL,
}

EMR_RECOMMENDATION_DOMAIN_ORDER = [
    "lipid_lowering",
    "plaque_cac",
    "kidney_protection",
    "blood_pressure",
    "glycemia_metabolic",
    "aspirin_antiplatelet",
    "data_to_clarify",
]

EMR_RECOMMENDATION_DOMAIN_LABELS = {
    "lipid_lowering": "Lipids",
    "plaque_cac": "Plaque",
    "kidney_protection": "Kidney",
    "blood_pressure": "BP",
    "glycemia_metabolic": "Glycemia",
    "aspirin_antiplatelet": "Aspirin",
    "data_to_clarify": "Clarify",
}

EMR_ASSESSMENT_TITLE = "Assessment:"
EMR_RECOMMENDATIONS_TITLE = "Recommendations:"

FORBIDDEN_EMR_FILLER_FRAGMENTS = (
    "may improve confidence",
    "as clinically indicated",
    "if appropriate",
    "when safe",
    "no repeat CAC needed",
    "Risk context:",
    "Risk:",
    "Level: Level",
    "Estimated population risk",
    "near-term",
    "longer-term trajectory",
    "prevention plan",
    "current decision-making",
    "existing rheumatoid arthritis; chronic inflammatory disease risk enhancer",
)
