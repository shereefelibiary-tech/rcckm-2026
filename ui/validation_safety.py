from html import escape

from ui.html import render_html
from ui.theme import component_theme_css


STATUS_ROWS = (
    ("Engine mode", "Deterministic"),
    ("Golden cases", "Active"),
    ("Never-cross invariants", "Active"),
    ("Output snapshots", "Active"),
    ("Clinical use", "Clinician review required"),
    ("PHI", "Do not enter PHI in public/demo use"),
)


def build_validation_safety_html() -> str:
    """Build the in-app Validation & Safety section as restrained HTML."""
    rows = "".join(
        "<div class='vs-row'>"
        f"<div class='vs-row-label'>{escape(label)}</div>"
        f"<div class='vs-row-value'>{escape(value)}</div>"
        "</div>"
        for label, value in STATUS_ROWS
    )
    return f"""
<style>
{component_theme_css()}
.vs-shell {{
    margin: 16px 0 22px;
    padding: 18px 20px 20px;
}}
.vs-kicker {{
    color: rgba(47, 95, 143, 0.88);
    font-size: 0.76rem;
    font-weight: 800;
    letter-spacing: 0.01em;
    margin-bottom: 4px;
}}
.vs-title {{
    color: var(--rc-text);
    font-family: var(--rc-font-body);
    font-size: 1.16rem;
    font-weight: 780;
    letter-spacing: 0;
    line-height: 1.15;
    margin-bottom: 7px;
}}
.vs-lede {{
    color: rgba(7, 26, 47, 0.70);
    font-size: 0.90rem;
    font-weight: 650;
    line-height: 1.42;
    max-width: 900px;
}}
.vs-grid {{
    display: grid;
    gap: 16px;
    grid-template-columns: minmax(0, 1.05fr) minmax(280px, 0.95fr);
    margin-top: 16px;
}}
.vs-panel {{
    border-top: 1px solid rgba(7, 26, 47, 0.10);
    padding-top: 12px;
}}
.vs-panel-title {{
    color: var(--rc-black);
    font-size: 0.88rem;
    font-weight: 850;
    margin-bottom: 7px;
}}
.vs-list {{
    color: rgba(7, 26, 47, 0.70);
    font-size: 0.84rem;
    font-weight: 620;
    line-height: 1.38;
    margin: 0;
    padding-left: 18px;
}}
.vs-list li {{
    margin: 4px 0;
}}
.vs-status {{
    border: 1px solid rgba(11,31,58,0.10);
    border-radius: 10px;
    background: rgba(255, 253, 248, 0.72);
    padding: 8px 10px;
}}
.vs-row {{
    align-items: baseline;
    border-top: 1px solid rgba(7, 26, 47, 0.07);
    display: grid;
    gap: 12px;
    grid-template-columns: minmax(125px, 0.72fr) minmax(0, 1fr);
    padding: 8px 2px;
}}
.vs-row:first-child {{
    border-top: 0;
}}
.vs-row-label {{
    color: rgba(7, 26, 47, 0.52);
    font-size: 0.75rem;
    font-weight: 760;
}}
.vs-row-value {{
    color: rgba(7, 26, 47, 0.78);
    font-size: 0.82rem;
    font-weight: 700;
    line-height: 1.22;
}}
.vs-posture {{
    color: rgba(7, 26, 47, 0.66);
    font-size: 0.84rem;
    font-weight: 620;
    line-height: 1.4;
    margin-top: 12px;
}}
@media (max-width: 760px) {{
    .vs-grid {{
        grid-template-columns: 1fr;
    }}
}}
</style>
<div class="rc-panel vs-shell">
  <div class="vs-kicker">Validation &amp; Safety</div>
  <div class="vs-title rc-card-title">Transparent validation for clinician review</div>
  <div class="vs-lede">
    RCCKM uses deterministic rule-based interpretation rather than hidden generative reasoning.
    Outputs are designed to be transparent, reproducible, and clinician-reviewable.
  </div>
  <div class="vs-grid">
    <div>
      <div class="vs-panel">
        <div class="vs-panel-title">Validation framework</div>
        <ul class="vs-list">
          <li>Golden cases test representative clinical scenarios across PREVENT risk, CKM staging, CAC/plaque status, ApoB/Lp(a), diabetes, kidney markers, hypertriglyceridemia, and ASCVD.</li>
          <li>Never-cross invariants protect against unsafe regressions, such as treating missing CAC as CAC 0 or allowing clinical ASCVD to be softened by CAC 0.</li>
          <li>Output contracts help prevent unintended wording drift in EMR notes and patient-facing roadmaps.</li>
        </ul>
      </div>
      <div class="vs-panel" style="margin-top: 14px;">
        <div class="vs-panel-title">Clinical safety posture</div>
        <ul class="vs-list">
          <li>RCCKM is clinical decision support.</li>
          <li>It does not replace medical judgment.</li>
          <li>Parsed values should be reviewed before interpretation.</li>
          <li>Public/demo use should not include patient-identifiable information.</li>
        </ul>
      </div>
    </div>
    <div>
      <div class="vs-status">
        {rows}
      </div>
      <div class="vs-posture">
        RCCKM is designed to standardize interpretation of cardiometabolic risk signals.
        It does not diagnose independently, prescribe automatically, or replace clinician judgment.
      </div>
    </div>
  </div>
</div>
""".strip()


def render_validation_safety(st_module) -> None:
    """Render the Validation & Safety section in Streamlit."""
    render_html(st_module, build_validation_safety_html())
