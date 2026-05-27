# Clinical Logic Overview

RCCKM organizes cardiometabolic prevention data into a stable clinical story:
where the patient falls, what diagnoses are supported, what targets apply, and
what actions follow.

## Core Inputs

High-impact inputs include age, sex, blood pressure, lipids, ApoB, Lp(a), A1c,
eGFR, UACR, smoking, diabetes, clinical ASCVD, CAC/plaque status, family
history, and selected risk enhancers.

## Interpretation Layers

- PREVENT-era risk: 10-year and 30-year ASCVD context.
- CKM stage: cardiometabolic and kidney stage context.
- Plaque/CAC: structural plaque status when measured.
- RSS: cumulative visible burden from lipid, metabolic, kidney, plaque,
  behavioral, and risk-enhancer contributors.
- Data-derived diagnoses: coding support from structured findings.
- Domain actions: lipid, plaque, kidney, BP, glycemia, aspirin, and data
  clarifiers.

## Guardrails

- CAC-only plaque is not treated as clinical ASCVD.
- Clinical ASCVD uses secondary-prevention logic.
- Missing CAC is unmeasured, not CAC 0.
- eGFR and UACR drive kidney staging; creatinine alone does not stage CKD.
- Family history is risk context, not a diagnosis candidate.
- Action, EMR, patient roadmap, and demo output render from shared domain
  action structures to reduce drift.
