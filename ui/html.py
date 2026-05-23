def render_html(*args):
    """Render trusted app-owned HTML through Streamlit's unsafe HTML path.

    Supports both render_html(html) and render_html(st, html) so older call sites
    can migrate gradually without leaking renderer markup as visible text.
    """
    if len(args) == 1:
        import streamlit as st_module

        html = args[0]
    elif len(args) == 2:
        st_module, html = args
    else:
        raise TypeError("render_html expects html or (st_module, html)")

    if not html or not isinstance(html, str):
        return

    if bool(getattr(st_module, "session_state", {}).get("show_raw_renderer_html", False)):
        with st_module.expander("Raw renderer HTML", expanded=False):
            st_module.code(html, language="html")

    st_module.markdown(html, unsafe_allow_html=True)


def render_component_html(st_module, html, *, height=420, scrolling=False):
    """Render a complete self-styled HTML component in an iframe.

    Use this for larger custom UI modules that include their own CSS. This avoids
    Streamlit Markdown treating HTML as text in some browser/session states.
    """
    if not html or not isinstance(html, str):
        return

    if bool(getattr(st_module, "session_state", {}).get("show_raw_renderer_html", False)):
        with st_module.expander("Raw renderer HTML", expanded=False):
            st_module.code(html, language="html")

    st_module.components.v1.html(html, height=height, scrolling=scrolling)
