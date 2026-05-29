"""Shared EMR label aliases for deterministic smartphrase extraction."""

A1C_ALIASES = (
    "a1c",
    "a1c:",
    "hemoglobin a1c",
    "hgba1c",
    "hba1c",
)

UACR_ALIASES = (
    "uacr",
    "urine acr",
    "albumin/creatinine ratio",
    "albumin creatinine ratio",
    "alb/cr ratio",
    "alb/cr",
    "albcreat",
    "microalbumin/creatinine ratio",
)

CAC_ALIASES = (
    "cac",
    "coronary artery calcium",
    "coronary calcium score",
    "ct calcium score",
)

ANCESTRY_ALIASES = {
    "south asian": "south_asian",
    "indian": "south_asian",
    "pakistani": "south_asian",
    "bangladeshi": "south_asian",
    "filipino": "filipino",
}

INFLAMMATORY_DISEASE_ALIASES = {
    "rheumatoid arthritis": "ra",
    "ra": "ra",
    "sle": "sle",
    "systemic lupus": "sle",
    "psoriasis": "psoriasis",
    "ibd": "ibd",
    "crohn": "ibd",
    "ulcerative colitis": "ibd",
}

OSA_ALIASES = (
    "osa",
    "obstructive sleep apnea",
    "sleep apnea",
    "cpap",
    "bipap",
)

MASLD_ALIASES = (
    "masld",
    "nafld",
    "fatty liver",
    "hepatic steatosis",
    "steatotic liver disease",
)

HSCRP_ALIASES = (
    "hscrp",
    "hs-crp",
    "high sensitivity crp",
    "high-sensitivity crp",
    "c-reactive protein, high sensitivity",
    "crp high sensitivity",
    "crphs",
)
