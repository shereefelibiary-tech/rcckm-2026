# Security and Privacy Notes

RCCKM is designed to be used with de-identified or synthetic data during public
review.

## Public Repository Rules

- Do not commit PHI, patient names, MRNs, phone numbers, addresses, dates of
  birth, screenshots with patient data, or real clinical notes.
- Do not commit API keys, passwords, tokens, private URLs, or Streamlit secrets.
- Use synthetic examples only.

## Current Repository Audit

The readiness pass searched the working tree for common credential and PHI
patterns, including API keys, tokens, passwords, private key markers, MRN/SSN
markers, emails, phone-like strings, and common patient identifiers.

Findings:

- No live credentials or private key material were found in the working tree.
- No examples or screenshots containing real patient data were found.
- The only identifier-like fixtures are synthetic detector tests using reserved
  example values.
- Commit history was checked for common secret markers where practical; no live
  credential pattern was identified.

## Local Secret Handling

`.gitignore` excludes `.env`, `.env.*`, `.streamlit/secrets.toml`, local
`secrets.toml`, and common private key/certificate file extensions.
