"""RTL/Arabic display support for the Streamlit UI.

Streamlit renders left-to-right by default, which breaks Arabic/Darija text
ordering and spacing. inject_rtl() applies a display-only RTL stylesheet:
Arabic content flows right-to-left while inputs, code and URLs stay LTR.
No data or behavior changes.
"""
import streamlit as st

_RTL_CSS = """
<style>
html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"],
[data-testid="stMarkdownContainer"], [data-testid="stCaptionContainer"],
[data-testid="stSidebar"], [data-testid="stSidebarContent"],
p, h1, h2, h3, h4, h5, h6, li, label, summary, button, [role="radiogroup"] {
    direction: rtl !important;
    text-align: right !important;
}
input, textarea, pre, code, kbd, samp, [data-testid="stCodeBlock"] {
    direction: ltr !important;
    text-align: left !important;
}
</style>
"""


def inject_rtl() -> None:
    """Apply the RTL stylesheet. Call once after st.set_page_config."""
    st.markdown(_RTL_CSS, unsafe_allow_html=True)
