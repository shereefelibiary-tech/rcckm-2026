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

