"""Run one RCCKM browser QA case against the Streamlit app.

Setup:
    pip install playwright
    playwright install chromium
    python qa_agent/run_single_case.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

try:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import sync_playwright
except ImportError as exc:
    raise SystemExit(
        "Playwright is required.\n"
        "Install with:\n"
        "  pip install playwright\n"
        "  playwright install chromium"
    ) from exc


ROOT = Path(__file__).resolve().parent
CASE_ID = "golden_001"
CASE_PATH = ROOT / "cases" / "golden_001_uacr_apob_cac0.txt"
OUTPUT_DIR = ROOT / "outputs"
DEFAULT_URL = "http://localhost:8501/?qa_mode=1"


def _click_button_if_present(page: Any, label: str, *, timeout_ms: int = 2500) -> bool:
    button = page.get_by_role("button", name=label, exact=True)
    try:
        if button.count() != 1:
            return False
        button.click(timeout=timeout_ms)
        return True
    except PlaywrightTimeoutError:
        return False


def _fill_main_textarea(page: Any, text: str) -> None:
    textarea = page.get_by_label("Paste EMR text", exact=True)
    if textarea.count() != 1:
        textarea = page.locator("textarea").first()
    textarea.fill(text)


def _summary_value(parsed: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in parsed and parsed[key] is not None:
            return parsed[key]
    return None


def _print_summary(payload: dict[str, Any], export_found: bool) -> None:
    parsed = payload.get("parsed_patient_json") or {}
    report_text = payload.get("final_report_text") or ""
    fields = {
        "age": _summary_value(parsed, "age"),
        "sex": _summary_value(parsed, "sex"),
        "ldl_c": _summary_value(parsed, "ldl_c", "ldl"),
        "apob": _summary_value(parsed, "apob"),
        "uacr": _summary_value(parsed, "uacr"),
        "cac": _summary_value(parsed, "cac"),
    }
    populated = ", ".join(
        f"{key}={value}" for key, value in fields.items() if value is not None
    )
    print(f"case_id: {CASE_ID}")
    print(f"qa_export_found: {export_found}")
    print(f"parsed_fields: {populated or 'none'}")
    print(f"report_text_length: {len(report_text)}")


def run() -> int:
    app_url = os.environ.get("RCCKM_QA_URL", DEFAULT_URL)
    smartphrase = CASE_PATH.read_text(encoding="utf-8")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    actual_json_path = OUTPUT_DIR / f"{CASE_ID}_actual.json"
    page_text_path = OUTPUT_DIR / f"{CASE_ID}_page.txt"
    screenshot_path = OUTPUT_DIR / f"{CASE_ID}_screenshot.png"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1400})
        export_found = False
        try:
            page.goto(app_url, wait_until="domcontentloaded", timeout=60_000)
            page.wait_for_selector("textarea", timeout=60_000)
            _fill_main_textarea(page, smartphrase)

            _click_button_if_present(page, "Parse and apply", timeout_ms=10_000)
            page.wait_for_timeout(800)

            if not _click_button_if_present(page, "Interpret risk", timeout_ms=20_000):
                raise RuntimeError("Could not find or click Interpret risk.")

            qa_export = page.locator('[data-testid="rcckm-qa-export"]')
            qa_export.wait_for(state="attached", timeout=60_000)
            export_found = True

            raw_json = qa_export.text_content(timeout=10_000) or ""
            payload = json.loads(raw_json)

            actual_json_path.write_text(
                json.dumps(payload, indent=2, default=str),
                encoding="utf-8",
            )
            page_text_path.write_text(page.locator("body").inner_text(), encoding="utf-8")
            page.screenshot(path=str(screenshot_path), full_page=True)
            _print_summary(payload, export_found)
            return 0
        except Exception as exc:
            print(f"case_id: {CASE_ID}")
            print(f"qa_export_found: {export_found}")
            print(f"error: {exc}")
            raise
        finally:
            if not export_found:
                page_text_path.write_text(page.locator("body").inner_text(), encoding="utf-8")
                page.screenshot(path=str(screenshot_path), full_page=True)
            browser.close()


if __name__ == "__main__":
    sys.exit(run())
