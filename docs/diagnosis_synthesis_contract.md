# Diagnosis Synthesis Contract

RCCKM diagnosis synthesis is clinical support first. It may surface ICD and HCC-aware metadata when the underlying diagnosis is clinically supported, but it must not promote speculative diagnoses or imply coding capture as a goal.

## Structured Metadata

Diagnosis candidates may carry this display metadata:

- `diagnosis`: clinician-readable diagnosis label.
- `icd10`: ICD-10-CM code or suggested code.
- `hcc_supported`: true only when the diagnosis and ICD mapping are clinically supported and CMS-HCC-relevant in RCCKM's current mapping.
- `hcc_label`: subtle label such as `HCC-supported`.
- `confidence`: source confidence, such as `data-supported` or `reported`.
- `source`: worksheet, parser, or clinician-reported evidence supporting the candidate.
- `review_status`: display workflow state, such as `review_suggested`.

## HCC / RAF Awareness

HCC visibility is intentionally subtle. Assessment Candidates may show an `HCC-supported` or similar professional badge for clinically supported HCC-relevant diagnoses.

Current supported examples include:

- Type 2 diabetes mellitus with diabetic chronic kidney disease, `E11.22`.
- CKD stage 3a or higher, including `N18.31`, `N18.32`, `N18.4`, and `N18.5`.

The EMR note may include a concise `HCC-supported` tag when it helps preserve clinically relevant diagnosis specificity.

## Guardrails

RCCKM must not:

- calculate RAF scores.
- show reimbursement estimates.
- use phrases such as capture opportunity.
- encourage unsupported diagnosis promotion.
- add HCC badges to ambiguous, missing, or weakly supported conditions.

Prediabetes, hypertriglyceridemia, ApoB burden, missing kidney data, and uncertain history do not receive HCC-supported badges by default.

## Review Workflow

Assessment Candidates remain reviewable. HCC-supported metadata is informational and does not replace clinician verification, coding policy review, or payer-specific documentation requirements.
