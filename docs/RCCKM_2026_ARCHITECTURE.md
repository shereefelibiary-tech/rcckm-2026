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