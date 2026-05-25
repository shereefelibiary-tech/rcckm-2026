import html
import json
import re

from ui.html import render_html
from ui.theme import component_theme_css


_HTML_TAG_RE = re.compile(r"</?(?:div|span|style|script|table|tr|td|p|br|html|body)\b[^>]*>", re.IGNORECASE)


def normalize_export_text(text: str | None) -> str:
    """Normalize plain-text report output for copy, print, and download."""
    value = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    value = "\n".join(line.rstrip() for line in value.split("\n")).strip()
    return f"{value}\n" if value else ""


def contains_html_tags(text: str | None) -> bool:
    """Return whether report text contains app-renderer HTML tags."""
    return bool(_HTML_TAG_RE.search(str(text or "")))


def _copy_print_component_html(emr_text: str, roadmap_text: str) -> str:
    emr_json = json.dumps(emr_text)
    roadmap_json = json.dumps(roadmap_text)
    printable_roadmap = html.escape(roadmap_text)
    return f"""
<style>
{component_theme_css()}
.export-copy-grid {{
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}}
.export-button {{
  border: 1px solid rgba(11,31,58,0.16);
  background: rgba(255,253,248,0.94);
  border-radius: 999px;
  color: var(--rc-primary);
  cursor: pointer;
  font-family: var(--rc-font-body);
  font-size: 0.82rem;
  font-weight: 850;
  padding: 8px 12px;
}}
.export-button:hover {{
  background: rgba(47,95,143,0.055);
}}
.export-message {{
  color: rgba(7,26,47,0.58);
  font-family: var(--rc-font-body);
  font-size: 0.74rem;
  font-weight: 650;
  line-height: 1.25;
  min-height: 18px;
  margin-top: 8px;
}}
.print-roadmap-document {{
  display: none;
}}
@media (max-width: 680px) {{
  .export-copy-grid {{
    grid-template-columns: 1fr;
  }}
}}
@media print {{
  body * {{
    visibility: hidden !important;
  }}
  .print-roadmap-document, .print-roadmap-document * {{
    visibility: visible !important;
  }}
  .print-roadmap-document {{
    background: #ffffff !important;
    color: #111111 !important;
    display: block !important;
    font-family: Georgia, 'Times New Roman', serif !important;
    font-size: 11pt !important;
    left: 0 !important;
    line-height: 1.42 !important;
    padding: 0.6in !important;
    position: absolute !important;
    top: 0 !important;
    white-space: pre-wrap !important;
    width: 100% !important;
  }}
}}
</style>
<div class="export-copy-grid">
  <button class="export-button" id="copyEmr">Copy EMR note</button>
  <button class="export-button" id="copyRoadmap">Copy patient roadmap</button>
  <button class="export-button" id="printRoadmap">Print patient roadmap</button>
</div>
<div class="export-message" id="exportMessage"></div>
<pre class="print-roadmap-document" id="printRoadmapDocument">RCCKM / Risk Continuum CKM

{printable_roadmap}

Clinician review required. Public/demo use should not include patient-identifiable information.</pre>
<script>
(function() {{
  const emrText = {emr_json};
  const roadmapText = {roadmap_json};
  const msg = document.getElementById("exportMessage");

  function setMessage(text) {{
    msg.textContent = text;
    setTimeout(function() {{ msg.textContent = ""; }}, 1800);
  }}

  async function copyText(text, label) {{
    try {{
      await navigator.clipboard.writeText(text);
      setMessage(label + " copied.");
    }} catch (error) {{
      const textarea = document.createElement("textarea");
      textarea.value = text;
      textarea.setAttribute("readonly", "");
      textarea.style.position = "fixed";
      textarea.style.left = "-9999px";
      document.body.appendChild(textarea);
      textarea.focus();
      textarea.select();
      const ok = document.execCommand("copy");
      document.body.removeChild(textarea);
      setMessage(ok ? label + " copied." : "Copy failed - select the text manually.");
    }}
  }}

  function printRoadmap() {{
    const printWindow = window.open("", "_blank", "noopener,noreferrer");
    if (!printWindow) {{
      window.print();
      return;
    }}
    printWindow.document.write(`<!doctype html>
<html>
<head>
<title>RCCKM patient roadmap</title>
<style>
  body {{
    background: #ffffff;
    color: #111111;
    font-family: Georgia, "Times New Roman", serif;
    font-size: 11pt;
    line-height: 1.42;
    margin: 0;
    padding: 0.6in;
  }}
  h1 {{
    font-family: Arial, sans-serif;
    font-size: 17pt;
    margin: 0 0 16px;
  }}
  pre {{
    font-family: Georgia, "Times New Roman", serif;
    white-space: pre-wrap;
  }}
  .disclaimer {{
    border-top: 1px solid #d7d7d7;
    color: #444444;
    font-family: Arial, sans-serif;
    font-size: 9pt;
    margin-top: 20px;
    padding-top: 8px;
  }}
</style>
</head>
<body>
<h1>RCCKM / Risk Continuum CKM</h1>
<pre></pre>
<div class="disclaimer">Clinician review required. Public/demo use should not include patient-identifiable information.</div>
</body>
</html>`);
    printWindow.document.querySelector("pre").textContent = roadmapText;
    printWindow.document.close();
    printWindow.focus();
    printWindow.print();
  }}

  document.getElementById("copyEmr").addEventListener("click", function() {{
    copyText(emrText, "EMR note");
  }});
  document.getElementById("copyRoadmap").addEventListener("click", function() {{
    copyText(roadmapText, "Patient roadmap");
  }});
  document.getElementById("printRoadmap").addEventListener("click", printRoadmap);
}})();
</script>
""".strip()


def render_export_print_section(st, *, emr_text: str, roadmap_text: str) -> None:
    """Render compact copy, print, and download controls for report text."""
    clean_emr = normalize_export_text(emr_text)
    clean_roadmap = normalize_export_text(roadmap_text)
    render_html(
        st,
        f"""
<style>
{component_theme_css()}
.export-panel {{
  margin: 16px 0 18px;
  padding: 15px 17px 16px;
}}
.export-title {{
  color: var(--rc-black);
  font-family: var(--rc-font-body);
  font-size: 1.0rem;
  font-weight: 850;
  letter-spacing: 0;
  line-height: 1.15;
}}
.export-helper {{
  color: rgba(7,26,47,0.64);
  font-size: 0.84rem;
  font-weight: 620;
  line-height: 1.35;
  margin-top: 4px;
}}
.export-note {{
  border-top: 1px solid rgba(7,26,47,0.08);
  color: rgba(7,26,47,0.54);
  font-size: 0.74rem;
  font-weight: 650;
  line-height: 1.3;
  margin-top: 10px;
  padding-top: 9px;
}}
</style>
<div class="rc-panel export-panel">
  <div class="export-title">Export / Print</div>
  <div class="export-helper">Copy the EMR note for clinical documentation or print the patient roadmap for patient counseling.</div>
</div>
""",
    )
    st.components.v1.html(
        _copy_print_component_html(clean_emr, clean_roadmap),
        height=100,
        scrolling=False,
    )
    cols = st.columns(2)
    with cols[0]:
        st.download_button(
            "Download EMR note (.txt)",
            data=clean_emr,
            file_name="rcckm_emr_note.txt",
            mime="text/plain",
        )
    with cols[1]:
        st.download_button(
            "Download patient roadmap (.txt)",
            data=clean_roadmap,
            file_name="rcckm_patient_roadmap.txt",
            mime="text/plain",
        )
    render_html(
        st,
        """
<div class="export-note">
  Review all copied or printed output before use. Public/demo use should not include patient-identifiable information.
</div>
""",
    )
