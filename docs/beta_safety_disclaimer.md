# RCCKM Beta Safety Disclaimer

Use this language in the public demo, footer, onboarding flow, and any early access agreement.

## Short Disclaimer

RCCKM is a beta clinical interpretation tool for clinician review. It is not a substitute for medical judgment, medical advice, diagnosis, or treatment. Do not enter PHI into the public demo unless HIPAA-compliant infrastructure is explicitly available.

## Public Demo Disclaimer

RCCKM is currently in beta.

The public demo is intended for de-identified test data and clinician evaluation only. Do not enter protected health information or patient-identifiable information into the public demo unless a HIPAA-compliant deployment is explicitly available and covered by the appropriate agreements.

RCCKM outputs require clinician verification. The parser may miss, misread, or misclassify pasted text during beta. The worksheet should be reviewed and edited before interpretation, and the generated report should be checked before use in clinical documentation or patient communication.

RCCKM is not intended for emergency, urgent, or acute-care decision-making.

## Clinician-Use Disclaimer

RCCKM is a structured cardiometabolic prevention interpretation layer. It can organize available information, estimate PREVENT risk when inputs are complete, accumulate RSS contributors, highlight missing clarifiers, and draft clinician-facing and patient-facing text.

RCCKM does not replace clinician judgment. Clinicians remain responsible for verifying source data, clinical context, guideline applicability, diagnosis and coding decisions, medication decisions, contraindications, patient preferences, and follow-up.

## Parser Disclaimer

The RCCKM parser is under active validation. It may:

- Miss relevant data.
- Parse the wrong value.
- Misclassify medication status.
- Misread negated or unknown conditions.
- Fail to detect stale or conflicting information.
- Require manual worksheet correction.

The worksheet is the final source of truth before interpretation.

## Missing Data Disclaimer

RCCKM treats missing data as missing, not normal. A blank or unavailable field may limit PREVENT calculation, CKM/KDIGO staging, RSS interpretation, and recommendations.

Examples of important missing clarifiers include:

- UACR for kidney-risk completion.
- ApoB for particle burden.
- Lp(a) once-in-lifetime measurement.
- CAC when age eligible and treatment decision or intensity remains uncertain.
- Diabetes status, smoking status, BP treatment status, and PREVENT-required inputs.

## Patient-Facing Disclaimer

This roadmap supports clinician review and shared decision-making. It does not replace medical advice. Patients should review the roadmap with their clinician before making medication, testing, or lifestyle decisions.

## Not For Emergency Use

RCCKM is not designed for emergency symptoms, acute chest pain, stroke symptoms, hypertensive emergencies, acute kidney injury, severe hyperglycemia, or other urgent clinical situations. Use appropriate emergency and acute-care workflows.

## Suggested UI Placement

Public demo top banner:

For clinician review only. Use de-identified test data. Do not enter PHI into the public demo unless HIPAA-compliant infrastructure is in place.

Before interpretation:

Parser output fills the worksheet. Review and edit values before interpretation. Outputs are beta and require clinician verification.

Report footer:

RCCKM beta output for clinician review. Not a substitute for clinical judgment. Not for emergency or acute-care use.

Patient roadmap footer:

This roadmap supports clinician review and shared decision-making. It does not replace medical advice.

