# RSS Scoring Contract

## Philosophy

RSS is an RCCKM interpretation layer. It is designed to make accumulated plaque, lipid, kidney, metabolic, inflammatory, behavioral, and risk-enhancing burden visible in one compact score and tower. It is not a PREVENT equation and does not replace guideline-based treatment logic.

## Hard Invariant

Displayed RSS score equals the sum of all displayed RSS contributor points.

Every contribution with points greater than 0 must:

- appear in the RSS contributor list
- appear as a segment in the RSS tower
- be included in the displayed RSS total

There are no hidden RSS points. Additional context may be shown only when it has 0 RSS points.

## Missing vs Zero

Missing values are not scored as normal and are not converted to zero.

- `None` means missing, not measured, or not entered.
- `0` means a true measured zero.
- UACR missing is not UACR 0.
- CAC missing or not performed is not CAC 0.
- Lp(a), ApoB, hsCRP, A1c, and kidney markers do not contribute points unless a measured value or explicit positive condition is present.

## Contributor Severity

Severity controls visual emphasis only. It does not control inclusion.

- `tiny`: 1-2 points
- `mild`: 3-4 points
- `moderate`: 5-7 points
- `major`: 8-29 points
- `very_high`: 30+ points

Tiny contributors are still displayed in the tower. If the segment is too small for readable text, the value remains available in the segment tooltip and in the contributor row.

## Current Point Contributors

### Plaque / CAC

- CAC 1-99: 10
- CAC 100-299: 20
- CAC 300-999: 30
- CAC >=1000: 40

CAC not performed or missing contributes 0 and may appear as a clarifier.

### ApoB

- ApoB 80-99 mg/dL: 4
- ApoB 100-129 mg/dL: 8
- ApoB >=130 mg/dL: 12

### Lp(a)

Nmoles/L:

- Lp(a) 75-124 nmol/L: 2
- Lp(a) 125-249 nmol/L: 8
- Lp(a) 250-429 nmol/L: 12
- Lp(a) >=430 nmol/L: 15

mg/dL:

- Lp(a) 30-49 mg/dL: 2
- Lp(a) 50-99 mg/dL: 8
- Lp(a) 100-179 mg/dL: 12
- Lp(a) >=180 mg/dL: 15

Lp(a) missing contributes 0 and may appear as a clarifier. Visible label is always `Lp(a)`.

### Glycemia

- A1c 5.7-6.4%: 2
- A1c >=6.5% when diabetes flag is absent: 8
- Diabetes present: 8

### Kidney

- eGFR 45-59: 5
- eGFR 30-44: 8
- eGFR 15-29: 12
- eGFR <15: 15
- UACR 30-299 mg/g: 6
- UACR >=300 mg/g: 10

UACR missing contributes 0 and may appear as a kidney-risk completion clarifier.

### Triglycerides

- TG 150-499 mg/dL: 4
- TG >=500 mg/dL: 8

### Inflammation / Conditions

- hsCRP 2-4.9 mg/L: 4
- hsCRP >=5 mg/L: 7
- RA: 2
- SLE: 2
- Psoriasis: 2
- IBD: 2
- HIV: 2
- Generic inflammatory disease, when no specific condition is present: 2

A single hsCRP elevation is not treated as a major driver.

### Sleep / Liver / Metabolic Enhancers

- OSA: 2
- MASLD: 2

### Family History

- Premature first-degree family history: 3

Premature thresholds:

- male first-degree relative event age <55
- female first-degree relative event age <65

Non-premature family history remains context only.

### Reproductive History

Documented reproductive risk markers contribute 2 points each and remain mild/contextual:

- Early menopause <45 years
- Premature menopause <40 years
- Preeclampsia
- Gestational hypertension
- Gestational diabetes
- Preterm delivery <37 weeks
- Small-for-gestational-age infant
- Recurrent spontaneous pregnancy loss
- PCOS / irregular menses
- Early menarche <10 years

These markers are not PREVENT inputs and do not independently mandate treatment. They can personalize primary-prevention risk discussion when lipid-lowering therapy is being considered.

### Smoking

- Current smoking: 8

## Context vs RSS

RSS contributors have positive points and stack in the tower.

Additional context is reserved for measured or documented information that does not currently add RSS points, such as non-premature family history or neutral measured values. Context rows must not show point values.

Missing clarifiers are important unmeasured items, such as missing Lp(a), UACR, ApoB, or CAC when clinically relevant.

## Level Taxonomy Interface

RSS is the cumulative risk-burden accumulator. It does not directly replace RCCKM level and it must not relabel PREVENT category as RCCKM level. The level classifier may use the presence of multiple RSS contributors as evidence of converging early risk signals, but the RSS tower/list contract remains separate:

- Every positive RSS contributor appears in the RSS total, tower, and contributor list.
- Missing values do not become zero.
- Small contributors can support Level 2B convergence when the pattern remains mild and non-treatment-forward.
- Level 3A/3B is the central early actionable trajectory zone. It requires a treatment-relevant trajectory or actionable biology such as elevated 30-year PREVENT risk, LDL-C 160-189, albuminuria, diabetes/CKD burden, severe hypercholesterolemia, Lp(a) plus family/reproductive/metabolic burden, or comparable guideline-supported action context.
