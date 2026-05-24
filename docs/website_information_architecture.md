# RCCKM Website Information Architecture

The public website should feel clinician-grade, calm, and polished. It should explain RCCKM as a structured cardiometabolic prevention interpretation layer while making the beta status visible.

## Global Navigation

Primary nav:

- Home
- Try demo
- How it works
- PREVENT + RCCKM
- Level 2/3 radar zone
- SmartPhrase examples
- Validation
- Pricing

Footer nav:

- Privacy
- Terms
- Clinician-use disclaimer
- Beta safety disclaimer
- Contact / early access

Global safety note:

For clinician review only. Do not enter PHI into the public demo unless HIPAA-compliant infrastructure is explicitly available.

## 1. Home

Purpose:

Introduce RCCKM quickly and make the product category clear.

Primary message:

RCCKM is a structured cardiometabolic prevention interpretation layer for clinician review.

Hero content:

- Eyebrow: Cardiovascular - Kidney - Metabolic Prevention
- Title: Risk Continuum CKM
- Subtitle: Structured clinical interpretation for PREVENT, cardiometabolic risk burden, missing clarifiers, clinician plans, EMR notes, and patient roadmaps.

Key sections:

- Not just a calculator.
- What RCCKM produces.
- Level 2/3 radar-zone patients.
- Clinician review and beta safety language.
- CTA: Try de-identified demo.
- Secondary CTA: Request early access.

Must not imply:

- Autonomous treatment decisions.
- Diagnosis without clinician review.
- Safe PHI entry in the public demo.

## 2. Try Demo

Purpose:

Let users experience the flow with demo data or de-identified paste text.

Content:

- Public demo disclaimer.
- Demo patient examples.
- Paste EMR text workflow.
- Worksheet review.
- Interpret reviewed worksheet.
- Report sections.

Required safety copy:

- Use de-identified text only.
- Parser output must be reviewed in the worksheet.
- Public demo is not for PHI unless HIPAA-compliant infrastructure is active.
- Not for emergency or acute-care decisions.

Suggested demo modes:

- High CAC demo.
- Level 2B early-risk demo.
- Level 3B radar-zone demo.
- Clinical ASCVD dominance demo.
- Incomplete-data demo.

## 3. How It Works

Purpose:

Explain the workflow without overloading visitors.

Sections:

1. Paste or enter clinical data.
2. Review the worksheet.
3. Interpret with RCCKM.
4. Review report hierarchy.
5. Copy EMR note or patient roadmap.

Core concepts:

- Worksheet is the source of truth.
- PREVENT estimates population risk.
- RCCKM level synthesizes trajectory and clinical context.
- RSS shows cumulative risk burden.
- Clarifiers show missing data that would improve interpretation.

## 4. PREVENT + RCCKM

Purpose:

Explain how PREVENT is used and how RCCKM adds interpretation.

Content:

- PREVENT 10-year risk categories.
- PREVENT 30-year risk use in adults age 30-59.
- Atherosclerotic event risk versus cardiovascular event risk.
- PREVENT eligibility guardrails.
- Clinical ASCVD dominance: PREVENT is not used for treatment decisions in established ASCVD.
- RCCKM level is not the same as PREVENT category.

Example:

- PREVENT category: low 10-year risk.
- RCCKM level: Level 3A if 30-year risk trajectory is treatment-relevant.

## 5. Level 2/3 Radar Zone

Purpose:

Make the RCCKM differentiation memorable.

Core message:

Level 3 means not an event yet, but no longer ignorable.

Content:

- Level 1: minimal risk signal.
- Level 2A: early isolated risk signal.
- Level 2B: converging early risk signals.
- Level 3A: elevated long-term risk trajectory.
- Level 3B: actionable early CKM / atherogenic / kidney risk.
- Level 4: subclinical plaque present.
- Level 5: clinical ASCVD or very high plaque / secondary-prevention intensity.

Examples:

- Lp(a) plus reproductive markers with low 30-year risk: Level 2B.
- LDL-C 160-189 or 30-year risk >=10: Level 3A.
- Albuminuria plus metabolic/BP burden: Level 3B.
- CAC >0: plaque pathway.

## 6. SmartPhrase Examples

Purpose:

Show how common EMR paste formats map into the worksheet.

Pages or sections:

- Epic
- Cerner
- MEDITECH
- Athena
- eClinicalWorks
- NextGen
- Allscripts/Veradigm
- VA CPRS
- Labcorp
- Quest
- Generic portal copy/paste

Required disclaimer:

Examples are synthetic and de-identified. Actual parser output requires clinician review.

## 7. Validation / Guideline Alignment

Purpose:

Build trust without overstating certification.

Content:

- 2026 ACC/AHA dyslipidemia guideline coverage matrix.
- PREVENT category tests.
- Missing-vs-zero tests.
- Unknown/negation tests.
- Clinical ASCVD dominance tests.
- CAC tier and age-gating tests.
- Lp(a), ApoB, UACR, TG pathway tests.
- Golden clinical cases.
- Fuzz/permutation testing plan.

Suggested language:

RCCKM is under active clinical validation. The public beta exposes reviewable outputs and test-driven safety gates, but it is not a substitute for clinician judgment.

## 8. Pricing / Early Access

Purpose:

Collect demand without overcommitting before subscription readiness.

Content:

- Early access interest form.
- Individual clinician beta.
- Team / practice pilot.
- Health system validation conversation.

Potential pricing copy:

Pricing will be introduced after beta safety gates, privacy/terms, authentication, payments, and data-retention decisions are complete.

CTA:

- Request early access.
- Contact for clinical pilot.

## 9. Privacy / Terms / Clinician-Use Disclaimer

Purpose:

Make limits explicit.

Required topics:

- For clinician review only.
- Not medical advice for patients.
- Not a substitute for medical judgment.
- Not for emergency or acute-care use.
- Public demo no-PHI policy unless HIPAA-compliant infrastructure is active.
- Parser limitations.
- Output verification requirement.
- Data retention policy.
- Security posture.
- Terms of use.

## Public Shell File Structure

Suggested structure if using a frontend app:

```text
website/
  app/
    page.tsx
    try-demo/page.tsx
    how-it-works/page.tsx
    prevent-rcckm/page.tsx
    level-2-3-radar-zone/page.tsx
    smartphrase-examples/page.tsx
    validation/page.tsx
    pricing/page.tsx
    privacy/page.tsx
    terms/page.tsx
    clinician-use-disclaimer/page.tsx
  components/
    BetaDisclaimer.tsx
    PageHeader.tsx
    SafetyCallout.tsx
    SmartPhraseExampleCard.tsx
    ValidationMetric.tsx
    WaitlistForm.tsx
  content/
    smartphrases/
      epic.md
      cerner.md
      meditech.md
      athena.md
      eclinicalworks.md
      nextgen.md
      allscripts-veradigm.md
      va-cprs.md
      labcorp.md
      quest.md
      generic-portal.md
    disclaimers/
      beta-safety.md
      clinician-use.md
      no-phi-public-demo.md
  styles/
    tokens.css
    typography.css
    layout.css
```

Suggested route slugs:

- `/`
- `/try-demo`
- `/how-it-works`
- `/prevent-rcckm`
- `/level-2-3-radar-zone`
- `/smartphrase-examples`
- `/validation`
- `/pricing`
- `/privacy`
- `/terms`
- `/clinician-use-disclaimer`

