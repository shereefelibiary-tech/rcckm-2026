# Risk Continuum CKM

**A structured clinical interpretation layer for cardiovascular, kidney, and metabolic risk.**

Built by a practicing internist. Aligned to PREVENT-era and AHA 2026 guidelines. Designed for the pace of a real clinical day.

---

## What it does

RCCKM is a clinician-facing cardiometabolic prevention interpretation engine that transforms fragmented risk data into a structured prevention trajectory, clinician action plan, EMR-ready note, and patient-facing roadmap.

The goal is to identify patients whose cardiometabolic trajectory is becoming clinically meaningful — including patients whose risk is present but scattered, and patients who do not look high-risk on the surface.

RCCKM integrates:
- PREVENT 10-year and 30-year cardiovascular risk estimation
- CKM syndrome staging and KDIGO CKD classification
- ApoB / Lp(a) / triglyceride interpretation
- CAC and plaque status (missing CAC treated as unmeasured, not zero)
- Kidney-risk markers (eGFR, UACR)
- Risk Signal Score (RSS) burden visualization
- Diagnosis normalization and staging support
- SmartPhrase-style EHR data ingestion
- Missingness detection — absent data is flagged, not silently omitted

---

## Clinical framework

### Risk Continuum — five-level staging

Every patient is placed on a five-level continuum from minimal signal to very high risk:

| Level | Description |
|---|---|
| 1 | Minimal risk signal |
| 2 | Emerging risk signals — monitor and address upstream |
| 3 | Actionable biologic risk — the inflection point for intervention |
| 4 | Subclinical atherosclerosis confirmed — treat aggressively |
| 5 | Established ASCVD / very high risk — maximum intensity required |

Sublevel designations (e.g. 3A, 3B) provide additional granularity based on the combination of risk signals present.

### Core concepts

- **PREVENT** — population-level 10-year and 30-year cardiovascular risk estimation, replacing Pooled Cohort Equations
- **RCCKM levels** — an interpretation framework that separates near-term event risk from long-term trajectory and biologic burden
- **RSS** — a cumulative risk-burden score where contributing signals are explicitly shown by domain
- **CKM / KDIGO** — cardiometabolic and kidney-risk staging, including eGFR and UACR integration
- **CAC / plaque** — structural plaque status when available; unmeasured CAC surfaces a recommendation rather than assuming zero
- **EMR note** — concise clinician-facing documentation with ICD-10 codes, targets, and recommendations
- **Patient roadmap** — plain-language prevention explanation, current goals, and numbered next steps
- **SmartPhrase parsing** — structured extraction from de-identified EMR-style text input

---

## Output

Four structured outputs from a single patient encounter:

**Clinical interpretation** — Risk Continuum level, RSS score, PREVENT 10 and 30-year risk, CKM and KDIGO staging, marker-level signal assessment, missingness flags, and confidence rating.

**Targets and action** — Guideline-aligned lipid targets (LDL-C, non-HDL-C, ApoB), blood pressure targets, numbered clinical action steps, aspirin guidance, and CAC recommendation when treatment decision remains uncertain.

**EMR-ready note** — Structured clinical note ready to paste into Epic, Cerner, Athena, or any EMR note field. Includes ICD-10 codes for confirmed diagnoses, treatment targets, and recommendations.

**Patient roadmap** — Plain-language patient-facing handout. Risk explained as natural frequencies. Drivers named clearly. Current goals shown alongside current values. Numbered next steps.

---

## Architecture

```
rcckm-2026/
├── app.py                    # Streamlit application entry point
├── diagnosis_workflow.py     # Diagnosis normalization and staging pipeline
├── core/                     # Risk level engine and staging logic
├── modules/
│   └── prevent/              # PREVENT equation implementation
├── renderers/                # Output rendering (EMR note, patient roadmap, RSS)
├── smartphrase_ingest/       # EHR smartphrase parsing pipeline
├── ui/                       # Worksheet, ingest panel, report layout, theme
├── tools/                    # Utility scripts
├── tests/                    # Test suite
├── docs/                     # Clinical documentation
└── examples/                 # Example patient cases
```

### Key design decisions

**Deterministic engine.** Every output is reproducible and auditable. Given the same inputs, RCCKM produces the same outputs every time. No generative AI in the clinical logic layer — only published coefficients, guideline-based staging rules, and transparent scoring.

**Worksheet-first architecture.** The smartphrase ingest parses EHR output into a structured worksheet. The clinician reviews and confirms before interpretation runs. The engine never acts on unreviewed data.

**Dirty-state tracking.** Worksheet changes are detected via hash comparison. If the worksheet is modified after interpretation, the report is marked stale and the clinician is prompted to re-interpret.

**Composite diagnosis handling.** The diagnosis pipeline normalizes, prioritizes, and suppresses diagnoses appropriately — for example, a confirmed diabetic CKD diagnosis suppresses redundant standalone diabetes and albuminuria fragments to prevent double-counting in staging logic.

**Missingness as a signal.** When clinical data is absent, RCCKM flags it explicitly and indicates what it would change about the risk picture. Incomplete data produces a visible gap, not a silent calculation.

---

## Guideline alignment

| Framework | Source |
|---|---|
| PREVENT equations | Khan et al., Circulation 2024; AHA 2026 Dyslipidemia Guideline |
| CKM syndrome staging | Ndumele et al., JACC 2023 |
| KDIGO CKD classification | KDIGO 2024 CKD Guidelines |
| Lipid targets and risk categories | Blumenthal et al., ACC/AHA 2026 Guideline on the Management of Blood Cholesterol |
| Risk-enhancing factors | AHA 2026 Dyslipidemia Guideline, Table 13 |

---

## Running locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Render deployment

- Language: Python 3
- Root Directory: blank
- Build Command: `pip install -r requirements.txt`
- Start Command: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
- Runtime: `python-3.12.7`

---

## Status

Active beta. Engine is in clinical use by the author in a primary care practice. External validation is in progress. All outputs require clinician review before use in patient care.

---

## Safety

This software is intended for clinician decision support and educational use. It is not a substitute for medical judgment. Not FDA cleared as a medical device. Public and demo use should not include patient-identifiable information. Patient data entered into the tool is not stored or transmitted.

---

## Author

Built by a practicing internal medicine physician. The clinical problem this tool addresses — the high-risk patient who does not look high-risk on the surface — is one encountered in real practice, every day.

---

## License

To be determined. Contact the repository owner for collaboration or licensing inquiries.
