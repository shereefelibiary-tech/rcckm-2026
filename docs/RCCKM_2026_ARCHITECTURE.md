# RCCKM 2026 Architecture

## Purpose

RCCKM 2026 is a PREVENT-era cardiometabolic risk interpretation engine.

It is designed to translate modern dyslipidemia, plaque, cardio-kidney-metabolic, and treatment-target guidance into deterministic clinical outputs.

## Core principle

PREVENT estimates risk. RCCKM interprets state.

## Primary architecture

RCCKM 2026 will use:

1. PREVENT risk estimation
2. Lipid and atherogenic burden assessment
3. Plaque and CAC reclassification
4. CKM phenotype interpretation
5. Treatment target generation
6. Decision stability scoring
7. EMR-ready recommendation output

## Design rules

- No PCE-centered logic.
- PREVENT is the primary risk equation layer.
- PREVENT estimates population event risk; it does not establish plaque unless CAC or another plaque measure is present.
- CAC is a reclassification layer, not just a tie-breaker.
- LDL-C and non-HDL-C targets are first-class outputs.
- ApoB is used for burden clarification and discordance detection.
- Lp(a) is treated as a lifetime risk-enhancing marker.
- Missing key data should reduce decision stability.
- The engine should produce one dominant clinical action.
- The engine should remain deterministic and testable.

## Initial module map

- prevent
- lipids
- plaque
- ckm
- kidney
- metabolic
- targets
- stability
- recommendations
- emr

## Roadmap

### PREVENT Expansion

- Add PREVENT 30-year ASCVD risk support.
- Add a 10-year PREVENT risk threshold around 5% for intermediate decision support.
- Add a young adult / long-horizon pathway using age 30-59 and 30-year PREVENT risk.
- Preserve the rule that PREVENT high risk can increase urgency and treatment intensity, but does not imply plaque unless CAC or another plaque measure is present.

### Lp(a)

- Add once-in-lifetime Lp(a) testing logic for all adults.
- Treat missing Lp(a) as a data-completion opportunity, especially when risk is borderline, intermediate, premature family history is present, or plaque/risk discordance is suspected.

### Lipid Targets

- Add LDL-C target tiers:
  - <100 mg/dL for lower-intensity primary prevention contexts.
  - <70 mg/dL for high-risk primary prevention or significant subclinical plaque contexts.
  - <55 mg/dL for established ASCVD / secondary prevention intensity.
- Preserve ApoB and non-HDL-C as parallel target outputs where supported.

### Treatment Guardrails

- Add explicit warning logic: do not recommend supplements as a lipid-lowering strategy.
- Favor evidence-based lipid-lowering therapies and lifestyle guidance over supplement-based LDL-C lowering recommendations.
