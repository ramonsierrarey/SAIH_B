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

st.set_page_config(
    page_title="SAIH_B",
    page_icon=str(ROOT / "static" / "icon-512.png"),
    layout="wide",
)

st.html(
    """<script>
    (() => {
      for (const rel of ["manifest", "apple-touch-icon"]) {
        document.head.querySelectorAll(`link[rel="${rel}"]`).forEach((link) => link.remove());
      }
      const links = [
        ["manifest", "app/static/manifest.webmanifest"],
        ["apple-touch-icon", "app/static/apple-touch-icon.png"],
      ];
      for (const [rel, href] of links) {
        const link = document.createElement("link");
        link.rel = rel;
        link.href = href;
        document.head.append(link);
      }
      const metadata = [
        ["application-name", "SAIH_B"],
        ["apple-mobile-web-app-title", "SAIH_B"],
        ["apple-mobile-web-app-capable", "yes"],
        ["theme-color", "#142533"],
      ];
      for (const [name, content] of metadata) {
        let meta = document.head.querySelector(`meta[name="${name}"]`);
        if (!meta) {
          meta = document.createElement("meta");
          meta.name = name;
          document.head.append(meta);
        }
        meta.content = content;
      }
    })();
    </script>""",
    unsafe_allow_javascript=True,
)


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
