# Diagnosis Workflow

RCCKM creates data-derived diagnosis candidates from structured clinical
findings, then separates them into accepted and needs-review groups for display
and documentation.

## Source of Candidates

Diagnosis candidates are generated from objective data such as diabetes status,
A1c, eGFR, UACR, CAC, LDL-C, ApoB, triglycerides, Lp(a), and clinical ASCVD
context.

Family history and risk enhancers are handled as context signals unless a
specific diagnosis rule exists.

## Normalization

`core/diagnosis_workflow.py` normalizes candidate rows, status, ICD-10 codes,
HCC metadata, review state, and evidence fields.

## Suppression Rules

Composite diagnoses are displayed ahead of lower-yield fragments. Examples:

- Type 2 diabetes with CKD can suppress standalone diabetes.
- Staged CKD can suppress generic CKD.
- Severe subclinical coronary atherosclerosis can suppress the lower-yield
  subclinical coronary atherosclerosis row.

Suppression is display-level. It does not change the underlying engine
thresholds.

## Code Export

Confirmed code export includes accepted diagnoses only. Suppressed or
review-needed diagnoses are not exported as confirmed codes.
