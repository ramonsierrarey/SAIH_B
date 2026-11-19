from pathlib import Path

import streamlit as st

import monitor


ROOT = Path(__file__).resolve().parent
html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
html = '<div class="burguillo">' + html.split("<body>", 1)[1].split("</body>", 1)[0] + "</div>"
css = (ROOT / "static" / "style.css").read_text(encoding="utf-8")
css = css.replace(":root", ":host").replace("body{margin:0}", ".burguillo{margin:0}")
js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")

dashboard_component = st.components.v2.component(
    "burguillo_dashboard",
    html=html,
    css=css,
    js=js,
)

st.set_page_config(page_title="El Burguillo · Observatorio del agua", layout="wide")


def refresh_manual():
    ok, message = monitor.refresh(manual=True)
    st.session_state["refresh_message"] = "" if ok else message


@st.fragment(run_every="60s")
def dashboard():
    monitor.refresh()
    dashboard_component(
        key="dashboard",
        data={
            "snapshot": monitor.get_data(),
            "message": st.session_state.pop("refresh_message", ""),
        },
        on_refresh_change=refresh_manual,
        width="stretch",
    )


dashboard()
