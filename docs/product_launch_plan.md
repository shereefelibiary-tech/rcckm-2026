# RCCKM Public Launch Plan

RCCKM is launching publicly as a prevention interpretation layer while the clinical engine remains in beta. The public shell should make the product understandable, credible, and testable without implying autonomous clinical decision-making.

## Positioning

Core statement:

RCCKM is a structured cardiometabolic prevention interpretation layer for clinician review.

RCCKM is not just a calculator. It combines population risk estimation, risk-burden accumulation, missing-data completion cues, clinician-facing action structure, EMR-ready documentation, and patient-facing roadmap output.

Primary product capabilities:

- Calculates PREVENT when required inputs are available.
- Shows 10-year and 30-year atherosclerotic and cardiovascular event risk.
- Separates PREVENT category from RCCKM level.
- Uses RSS to accumulate visible risk-burden contributors.
- Identifies Level 2 and Level 3 radar-zone patients who may otherwise look "low risk."
- Highlights missing clarifiers such as UACR, ApoB, Lp(a), CAC, hsCRP, and PREVENT inputs.
- Generates a clinician plan, EMR note, and patient roadmap.

Beta positioning:

- The clinical engine is in beta.
- Outputs require clinician verification.
- The parser is under active validation and may miss or misclassify pasted data.
- The public demo must avoid PHI unless HIPAA-compliant infrastructure is in place.
- RCCKM is not for emergency or acute-care decision-making.

## Launch Phases

### Phase 0 - Private Clinical Beta

Audience:

- Internal reviewers.
- Selected preventive cardiology, lipidology, nephrology, endocrine, and primary care clinicians.

Goals:

- Validate level taxonomy.
- Validate parser safety.
- Stress-test incomplete data, unknowns, negations, missing-vs-zero behavior, and clinical ASCVD dominance.
- Build initial clinician trust.

Exit criteria:

- Parser validation suite passing.
- Missing-vs-zero tests passing.
- Unknown/negation tests passing.
- 50 golden cases passing.
- 1,000+ fuzz cases passing.
- Public demo safety disclaimer completed.

### Phase 1 - Public Shell and Demo

Audience:

- Clinicians evaluating RCCKM.
- Health system innovation teams.
- Researchers and guideline-oriented reviewers.

Goals:

- Explain RCCKM clearly.
- Provide a de-identified demo workflow.
- Show representative SmartPhrase formats.
- Show validation posture and guideline alignment.
- Collect early access interest.

Public constraints:

- No PHI entry unless HIPAA-compliant deployment is explicitly available.
- Demo output must include beta disclaimer.
- Pricing can be early-access oriented rather than fully commercial.

### Phase 2 - Early Access Subscription

Audience:

- Individual clinicians and small clinical teams.
- Early institutional pilots.

Goals:

- Test authentication, billing, onboarding, support, audit, and data retention decisions.
- Establish feedback loops for parser and recommendation safety.
- Offer controlled use with clear beta terms.

Launch gates:

- Terms, privacy, and clinician-use disclaimer complete.
- Authentication and payments tested.
- No-PHI or HIPAA posture documented.
- Audit logs and retention policy documented.

### Phase 3 - Production Clinical Workflow

Audience:

- Clinical practices and organizations.
- Health-system deployment partners.

Goals:

- Move from demo-first to workflow integration.
- Consider HIPAA-compliant data handling.
- Add organization-level controls, audit logs, parser QA, and export workflows.

## Public Messaging Pillars

### 1. Prevention Interpretation Layer

RCCKM sits above raw risk equations. It organizes PREVENT, RSS, CKM/KDIGO context, missing clarifiers, targets, action, EMR text, and patient-facing language into one reviewable workflow.

### 2. Level 2/3 Radar Zone

RCCKM focuses on patients who may not have clinical ASCVD or measured plaque but have early cardiometabolic trajectory:

- Level 2A: early isolated risk signal.
- Level 2B: converging early risk signals.
- Level 3A: elevated long-term risk trajectory.
- Level 3B: actionable early CKM / atherogenic / kidney risk.

### 3. Missing Data Is a Safety Signal

RCCKM treats missing data as missing, not normal. UACR, ApoB, Lp(a), CAC, diabetes status, smoking status, and BP treatment status are shown as completion gaps when clinically relevant.

### 4. Clinician Review First

RCCKM does not replace medical judgment. The worksheet is the source of truth after parsing, and clinicians review outputs before use.

## Launch Assets

Required pages:

- Home
- Try demo
- How it works
- PREVENT + RCCKM
- Level 2/3 radar zone
- SmartPhrase examples
- Validation / guideline alignment
- Pricing / early access
- Privacy / terms / clinician-use disclaimer

Required support docs:

- `docs/website_information_architecture.md`
- `docs/smartphrase_examples_plan.md`
- `docs/subscription_launch_checklist.md`
- `docs/beta_safety_disclaimer.md`

## Success Metrics

Product comprehension:

- Clinicians can explain how RCCKM differs from a calculator.
- Clinicians understand PREVENT category versus RCCKM level.
- Clinicians understand that parser output must be reviewed.

Safety:

- No public copy implies autonomous diagnosis or treatment.
- No public demo invites PHI entry without compliance infrastructure.
- Unknown, missing, and not documented examples are represented safely.

Engagement:

- Demo starts.
- Early access signups.
- SmartPhrase example views.
- Validation page views.
- Contact requests from clinicians or organizations.

