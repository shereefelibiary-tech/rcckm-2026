# Risk Continuum CKM

Risk Continuum CKM is a clinician-facing cardiometabolic prevention interpretation engine that transforms fragmented risk data into a structured prevention trajectory, clinician action plan, EMR-ready note, and patient-facing roadmap.

## What it does

RCCKM integrates PREVENT 10-year and 30-year risk, CKM staging, ApoB/Lp(a)/triglyceride interpretation, CAC/plaque status, kidney-risk markers, RSS burden visualization, diagnosis support, and SmartPhrase-style data ingestion.

The goal is to identify patients whose cardiometabolic trajectory is becoming clinically meaningful before overt ASCVD or advanced disease develops.

## Core concepts

- **PREVENT**: population-level 10-year and 30-year cardiovascular risk estimation.
- **RCCKM levels**: an interpretation framework that separates near-term event risk from long-term trajectory and biologic burden.
- **RSS**: a cumulative risk-burden visualization where contributing signals are explicitly shown.
- **CKM / KDIGO**: cardiometabolic and kidney-risk context, including eGFR and UACR.
- **CAC / plaque**: structural plaque status when available, with missing CAC treated as unmeasured rather than zero.
- **EMR note**: concise clinician-facing documentation output.
- **Patient roadmap**: patient-facing prevention explanation and next steps.
- **SmartPhrase parsing**: structured extraction from de-identified EMR-style text.

## Status

Active beta. Outputs require clinician review.

## Safety

This software is intended for clinician decision support and educational/prototype use. It is not a substitute for medical judgment. Public/demo use should not include patient-identifiable information.

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

- Language: Python 3
- Build Command: `pip install -r requirements.txt`
- Start Command: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
- Runtime: `python-3.12.7`
