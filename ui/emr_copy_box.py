import html
import uuid

from ui.theme import component_theme_css


def render_emr_copy_box(
    st,
    text,
    title="Risk Continuum - EMR Note",
    height_px=520,
    button_label="Copy",
):
    components = getattr(getattr(st, "components", None), "v1", None)
    if components is None:
        import streamlit.components.v1 as components

    uid = uuid.uuid4().hex[:10]
    safe_text = html.escape(text or "")
    safe_title = html.escape(title or "Clinical Report")
    safe_button_label = html.escape(button_label or "Copy")
    textarea_height = max(240, height_px - 90)

    components.html(
        f"""
<style>
{component_theme_css()}
.emr-copy-panel {{
  border: 1px solid var(--rc-border);
  border-radius: var(--rc-radius);
  padding: 14px;
  background: var(--rc-surface);
  font-family: var(--rc-font-body);
}}
.emr-copy-head {{
  display:flex;
  justify-content:space-between;
  align-items:center;
  margin-bottom:10px;
}}
.emr-copy-title {{
  color: var(--rc-text);
  font-size: 0.88rem;
  font-weight: 850;
}}
.emr-copy-button {{
  border:1px solid rgba(11,31,58,0.18);
  background: var(--rc-surface);
  border-radius:999px;
  padding:6px 12px;
  font-weight:800;
  cursor:pointer;
  color: var(--rc-primary);
}}
.emr-copy-text {{
  width:100%;
  height:{textarea_height}px;
  border:1px solid rgba(11,31,58,0.12);
  border-radius:12px;
  padding:12px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
  font-size:12.5px;
  line-height:1.35;
  color:var(--rc-text);
  background:#fffefa;
  resize:none;
  box-sizing:border-box;
}}
.emr-copy-msg {{
  margin-top:10px;
  color:rgba(7,26,47,0.62);
  font-size:12px;
  min-height:16px;
}}
</style>
<div class="emr-copy-panel">
  <div class="emr-copy-head">
    <div class="emr-copy-title">{safe_title}</div>
    <button id="copyBtn_{uid}" class="emr-copy-button">{safe_button_label}</button>
  </div>

  <textarea id="noteText_{uid}" readonly class="emr-copy-text">{safe_text}</textarea>

  <div id="copiedMsg_{uid}" class="emr-copy-msg"></div>
</div>

<script>
(function() {{
  const btn = document.getElementById("copyBtn_{uid}");
  const ta = document.getElementById("noteText_{uid}");
  const msg = document.getElementById("copiedMsg_{uid}");

  async function doCopy() {{
    try {{
      await navigator.clipboard.writeText(ta.value);
      msg.textContent = "Copied to clipboard.";
      setTimeout(() => msg.textContent = "", 1500);
    }} catch (e) {{
      ta.focus();
      ta.select();
      const ok = document.execCommand("copy");
      msg.textContent = ok ? "Copied to clipboard." : "Copy unavailable - select all and copy manually.";
      setTimeout(() => msg.textContent = "", 2000);
    }}
  }}

  btn.addEventListener("click", doCopy);
}})();
</script>
        """,
        height=height_px,
    )
