# RCCKM Browser QA Runner

Setup:

```bash
pip install playwright
playwright install chromium
python qa_agent/run_single_case.py
```

The runner opens `http://localhost:8501/?qa_mode=1` by default.
Override the target with:

```bash
set RCCKM_QA_URL=http://localhost:8501/?qa_mode=1
```

Generate synthetic QA patients:

```bash
python qa_agent/generate_cases.py --count 100
```

This writes paired patient JSON and Epic-style SmartPhrase text files to
`qa_agent/generated_cases/`.

Run batch validation over generated synthetic cases:

```bash
python qa_agent/run_batch_validation.py --count 100
```

The batch runner writes aggregate reports to `qa_agent/reports/` and saves
screenshots only for cases with findings.
