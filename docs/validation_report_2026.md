# RCCKM 2026 Validation Report

## Status

Validation status: Active beta validation framework.

Current validation date: May 25, 2026.

## Scope

This validation suite covers deterministic clinical interpretation behavior, report wording contracts, and output safety checks for RCCKM 2026. It is designed to catch unintended drift in clinical classification, report wording, diagnosis synthesis, and patient-facing output.

## Golden Cases

Golden cases exercise locked clinical archetypes and boundary-tolerant scenarios across the RCCKM interpretation layer. Covered domains include:

- PREVENT low, borderline, intermediate, and high categories.
- CAC and plaque states, including CAC 0, CAC positive, severe plaque burden, CAC >=1000, and plaque unmeasured.
- ApoB, LDL-C, non-HDL-C, and discordant atherogenic burden patterns.
- Lp(a) thresholds and reporting language.
- Diabetes, prediabetes, and glycemic trajectory.
- CKD, eGFR, UACR, albuminuria, and KDIGO staging.
- Hypertriglyceridemia, including severe and very severe triglyceride pathways.
- Clinical ASCVD and secondary-prevention dominance.
- RCCKM Level 1-5 taxonomy, including Level 2A, 2B, 3A, and 3B.

Golden case assertions support both global phrase checks and section-specific assertions for EMR notes, patient roadmaps, action text, and diagnosis text.

## Never-Cross Invariants

The invariant suite protects clinical rules that should not drift across refactors or wording changes. Current categories include:

- Plaque and CAC safety, including missing CAC versus measured CAC 0.
- Clinical ASCVD override behavior.
- LDL-C >=190 and suspected FH/severe hypercholesterolemia guardrails.
- Severe hypertriglyceridemia and pancreatitis-risk pathways.
- Kidney staging and missing-versus-zero UACR behavior.
- PREVENT category thresholds.
- Diagnosis gating for diabetes, albuminuria, CKD, and plaque diagnoses.
- Forbidden language and contradictory phrase checks.

## Snapshot Contracts

Selected EMR notes and patient roadmap outputs are snapshot-locked as plain text files under:

- `tests/snapshots/emr/`
- `tests/snapshots/patient_roadmap/`

Snapshots are intentionally ordinary `.txt` files so reviewers can inspect diffs directly. Default test behavior compares rendered output to the checked-in contract. Snapshot updates require explicit opt-in:

```bash
UPDATE_SNAPSHOTS=1 pytest tests/snapshots/test_output_snapshots.py
```

Snapshot tests also enforce safety checks for raw HTML fragments, forbidden wording, internal implementation field names, and contradictory phrase pairs.

## CI

GitHub Actions runs validation on push and pull request. The workflow executes:

- `pytest tests/golden_cases`
- `pytest tests/invariants`
- `pytest tests/snapshots`
- `python tools/run_validation.py`

The layered validation runner also includes parser fixture regression, boundary tests, invariant tests, snapshot contracts, parser safety tests, and a reproducible fuzz sample.

## Known Limitations

- This is not prospective outcomes validation.
- It does not replace clinician judgment.
- It depends on accurate worksheet data entry or verified parsed data.
- Parser output must be reviewed before interpretation.
- Public or demo use should not include PHI unless appropriate HIPAA-compliant infrastructure and policy are in place.

## Clinical Safety Posture

RCCKM is a clinician-facing cardiometabolic prevention interpretation layer. Outputs require clinician review and are not a substitute for medical judgment. The validation framework is designed to reduce unsafe regressions, make output drift visible, and keep clinical interpretation behavior inspectable during active beta development.
