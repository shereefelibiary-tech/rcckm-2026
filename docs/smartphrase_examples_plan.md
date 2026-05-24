# SmartPhrase Examples Plan

The SmartPhrase example library should help clinicians understand what RCCKM can parse while reinforcing that parser output requires worksheet review.

All examples must be synthetic and de-identified.

## Safety Copy

Use this copy on the SmartPhrase examples page and near any copy/paste demo area:

These examples are synthetic and de-identified. Public demo users should not enter PHI unless HIPAA-compliant infrastructure is explicitly available. Parser output can be incomplete or incorrect during beta; clinicians must review and edit the worksheet before interpretation.

## Example Page Goals

Each example page should show:

- Source style.
- Synthetic paste text.
- Fields expected to parse.
- Fields that may remain missing.
- Safety notes.
- Link to try a de-identified demo.

Each page should avoid:

- Real patient data.
- Vendor screenshots that imply endorsement.
- Claims of flawless parsing.
- Hidden parser limitations.

## Planned Pages and Fixtures

### Epic

Planned URL:

- `/smartphrase-examples/epic`

Fixture:

- `tests/fixtures/ingest/epic_smartphrase_standard.txt`
- `tests/fixtures/ingest/epic_lab_results_table.txt`

Content focus:

- SmartPhrase-style risk review.
- Lab results table.
- Medication and family history lines.
- Explicit no/unknown boolean handling.

### Cerner

Planned URL:

- `/smartphrase-examples/cerner`

Fixture:

- `tests/fixtures/ingest/cerner_powerchart_summary.txt`
- `tests/fixtures/ingest/cerner_lab_flowsheet.txt`

Content focus:

- PowerChart summary style.
- Lipids, kidney markers, and diabetes values.
- CAC and smoking status.

### MEDITECH

Planned URL:

- `/smartphrase-examples/meditech`

Fixture:

- `tests/fixtures/ingest/meditech_expanse_summary.txt`

Content focus:

- Abbreviated lab and visit summary text.
- CAC, hsCRP, and clinical ASCVD negation.

### Athena

Planned URL:

- `/smartphrase-examples/athena`

Fixture:

- `tests/fixtures/ingest/athenahealth_visit_summary.txt`

Content focus:

- Visit summary paste.
- Medication vocabulary.
- Diabetes and CKM values.

### eClinicalWorks

Planned URL:

- `/smartphrase-examples/eclinicalworks`

Fixture:

- `tests/fixtures/ingest/eclinicalworks_progress_note.txt`

Content focus:

- Progress-note style paste.
- Nonfasting lipid context.
- Family history and conditions.

### NextGen

Planned URL:

- `/smartphrase-examples/nextgen`

Fixture:

- `tests/fixtures/ingest/nextgen_clinical_summary.txt`

Content focus:

- Clinical summary format.
- No clinical ASCVD line.
- CAC measured versus missing.

### Allscripts / Veradigm

Planned URL:

- `/smartphrase-examples/allscripts-veradigm`

Fixture:

- `tests/fixtures/ingest/allscripts_veradigm_summary.txt`

Content focus:

- Summary style with lab shorthand.
- Unknown and not documented examples.
- Medication active/inactive distinction.

### VA CPRS

Planned URL:

- `/smartphrase-examples/va-cprs`

Fixture:

- `tests/fixtures/ingest/va_cprs_note.txt`

Content focus:

- CPRS note-style text.
- Tobacco line.
- Family history.
- Prior MI/stroke/PAD negation.

### Labcorp

Planned URL:

- `/smartphrase-examples/labcorp`

Fixture:

- `tests/fixtures/ingest/labcorp_results_text.txt`

Content focus:

- Lab-result copy.
- Patient-reported clinical context.
- Missing medication information.

### Quest

Planned URL:

- `/smartphrase-examples/quest`

Fixture:

- `tests/fixtures/ingest/quest_results_text.txt`

Content focus:

- Lab-result copy.
- Diabetes, smoking, and family-history context.
- CAC if included outside lab data.

### Generic Portal Copy/Paste

Planned URL:

- `/smartphrase-examples/generic-portal`

Fixture:

- `tests/fixtures/ingest/generic_portal_lab_copy.txt`
- `tests/fixtures/ingest/messy_mixed_copy_paste.txt`
- `tests/fixtures/ingest/heavily_incomplete_unknowns.txt`

Content focus:

- Realistic messy paste text.
- Missing and unknown fields.
- Demonstrates that unknown does not become positive risk.
- Shows why worksheet review is mandatory.

## Example Content Template

```markdown
# Epic SmartPhrase Example

This synthetic example shows how RCCKM handles common Epic-style pasted text.

Safety note: Do not paste PHI into the public demo unless HIPAA-compliant infrastructure is explicitly available.

## Synthetic Paste Text

...

## Expected Parsed Fields

- Age
- Sex
- BP
- Lipids
- ApoB
- Lp(a)
- A1c
- eGFR
- UACR
- CAC
- Smoking
- Family history
- Medications

## Fields Requiring Review

- Clinical ASCVD status
- Medication activity and intolerance
- Family history relationship/event/age
- Unknown or not documented booleans

## What RCCKM Does Next

- Fills worksheet fields.
- Shows parse coverage.
- Requires clinician review.
- Generates report only after "Interpret reviewed worksheet."
```

## Fixture Governance

Rules:

- Every `.txt` example should have a matching `.expected.json`.
- Expected JSON should include normalized parsed fields only.
- Fixtures must contain no PHI.
- Fixtures should include positives, negatives, unknowns, and missing data.
- Unknown values should be expected as `null`, not `true`.

