# Risk Continuum CKM

Risk Continuum CKM (RCCKM) is a clinician-facing cardiometabolic prevention interpretation engine. It turns fragmented prevention data into a structured risk picture, data-derived diagnoses, targets, a domain-based Action panel, an EMR-ready note, and a patient-facing roadmap.

Current version: `0.1.0-beta`.

## What RCCKM Is

RCCKM integrates:

- PREVENT-era 10-year and 30-year ASCVD risk interpretation.
- CKM staging and kidney context from eGFR and UACR.
- ApoB, Lp(a), LDL-C, triglycerides, and target interpretation.
- CAC/plaque status, including CAC 0, measured CAC burden, and clinical ASCVD context.
- RSS contributors that make cumulative risk burden visible.
- Data-derived diagnosis and coding support.
- SmartPhrase-style extraction from de-identified clinical text.

The goal is to reduce clinician cognitive load by making prevention status, diagnosis support, targets, and next actions easier to review.

## What RCCKM Is Not

- Not a medical device cleared for clinical deployment.
- Not a substitute for clinician judgment.
- Not a replacement for guideline review, shared decision-making, contraindication checks, or local policy.
- Not intended for entry of patient-identifiable information in public demos or public repositories.

## Beta Status

RCCKM is in active beta. Outputs are intended for review, validation, and product/clinical feedback. Clinical logic and output language may change before any production use.

## Clinical Disclaimer

This software is for clinician decision-support review and educational/prototype use only. It does not diagnose, treat, or independently recommend care. A qualified clinician must verify all inputs, outputs, diagnosis/coding support, medication recommendations, contraindications, and patient-specific context.

## Privacy

Do not paste PHI or patient-identifiable data into public demos, issues, examples, screenshots, or test fixtures. Repository examples are synthetic.

## Local Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Testing

```bash
python -m pytest -q
python tools/run_validation.py
```

CI runs golden cases, never-cross invariants, governance/drift tests, snapshot contracts, and the layered validation runner.

## Render Deployment

`render.yaml` points to the root `requirements.txt`.

- Language: Python 3
- Build Command: `pip install -r requirements.txt`
- Start Command: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
- Runtime target: see `runtime.txt`

## Documentation

- [Clinical Logic Overview](docs/clinical_logic_overview.md)
- [RSS Methodology](docs/rss_methodology.md)
- [PREVENT and CKM Notes](docs/prevent_and_ckm_notes.md)
- [Diagnosis Workflow](docs/diagnosis_workflow.md)
- [Security and Privacy Notes](docs/security_privacy_notes.md)
- [Documentation Index](docs/README.md)

## Examples

Synthetic examples are in [examples](examples/). They are not real patient data.

## License / IP

All rights reserved. Source code is publicly viewable for evaluation only. No license is granted for reuse, redistribution, modification, clinical deployment, or commercial use without written permission.
