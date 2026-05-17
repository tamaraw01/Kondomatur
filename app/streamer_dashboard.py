import os

import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


def api_get(path: str):
    response = requests.get(f"{API_BASE_URL}{path}", timeout=10)
    response.raise_for_status()
    return response.json()


def api_post(path: str, payload: dict):
    response = requests.post(f"{API_BASE_URL}{path}", json=payload, timeout=10)
    response.raise_for_status()
    return response.json()


st.set_page_config(page_title="Kondomatur - Panel Streamer", page_icon="KT", layout="wide")
theme_mode = st.sidebar.radio("Tema tampilan", ["Dark", "Light"], horizontal=True)
if theme_mode == "Dark":
    palette = {
        "bg": "#06163f",
        "surface": "#071f56",
        "surface_2": "#0a2b70",
        "text": "#f8fbff",
        "muted": "#a7c1e8",
        "line": "rgba(194, 223, 255, 0.20)",
        "cyan": "#00d9ff",
        "mint": "#00e7a6",
        "shadow": "rgba(0, 8, 30, 0.36)",
    }
else:
    palette = {
        "bg": "#eef6ff",
        "surface": "#ffffff",
        "surface_2": "#edf5ff",
        "text": "#06163f",
        "muted": "#536c98",
        "line": "rgba(6, 22, 63, 0.14)",
        "cyan": "#0074ff",
        "mint": "#00a878",
        "shadow": "rgba(8, 49, 120, 0.15)",
    }

st.markdown(
    f"""
    <style>
    .stApp {{
        background:
            linear-gradient(90deg, {palette["cyan"]} 0 6px, transparent 6px),
            linear-gradient(135deg, {palette["bg"]}, {palette["surface_2"]});
        color: {palette["text"]};
    }}
    .block-container { padding-top: 2rem; max-width: 1180px; }
    [data-testid="stMetric"] {{
        background: {palette["surface"]};
        border: 1px solid {palette["line"]};
        border-radius: 8px;
        padding: 16px;
        box-shadow: 0 20px 55px {palette["shadow"]};
    }}
    div[data-testid="stAlert"] {{
        border-radius: 8px;
    }}
    .kd-card {{
        border: 1px solid {palette["line"]};
        border-radius: 8px;
        padding: 20px;
        background: {palette["surface"]};
        box-shadow: 0 20px 55px {palette["shadow"]};
    }}
    .premium-title {{
        color: {palette["cyan"]};
        font-size: 12px;
        font-weight: 900;
        text-transform: uppercase;
    }}
    .status-chip {{
        display: inline-block;
        margin: 0 8px 8px 0;
        padding: 9px 12px;
        border: 1px solid {palette["line"]};
        border-radius: 999px;
        background: {palette["surface_2"]};
        color: {palette["text"]};
        font-weight: 800;
        font-size: 13px;
    }}
    h1, h2, h3, p, label, [data-testid="stMarkdownContainer"] {{
        color: {palette["text"]};
    }}
    </style>
    """,
    unsafe_allow_html=True,
)
st.title("Panel Streamer")
st.caption("AI-powered donation payment gateway prototype untuk streamer.")

try:
    settings = api_get("/api/settings")
except requests.RequestException as exc:
    st.error("API belum berjalan. Jalankan: uvicorn api.main:app --reload --port 8000")
    st.code(str(exc))
    st.stop()

streamer_id = settings.get("streamer_id", "streamer_001")
current_mode = settings.get("filter_mode", "sensor")

mode_col, status_col = st.columns([1, 2])
with mode_col:
    st.markdown('<div class="premium-title">Mode proteksi</div>', unsafe_allow_html=True)
    sensor_col, block_col = st.columns(2)
    with sensor_col:
        if st.button("Sensor", type="primary" if current_mode == "sensor" else "secondary", use_container_width=True):
            if current_mode != "sensor":
                api_post("/api/settings/filter-mode", {"streamer_id": streamer_id, "filter_mode": "sensor"})
                st.rerun()
    with block_col:
        if st.button("Blokir", type="primary" if current_mode == "block" else "secondary", use_container_width=True):
            if current_mode != "block":
                api_post("/api/settings/filter-mode", {"streamer_id": streamer_id, "filter_mode": "block"})
                st.rerun()

with status_col:
    st.markdown('<div class="premium-title">Status sistem</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <span class="status-chip">AI Moderation aktif</span>
        <span class="status-chip">Payment Sandbox aktif</span>
        <span class="status-chip">Overlay aktif</span>
        """,
        unsafe_allow_html=True,
    )

donate_link = f"{API_BASE_URL}/donate/{streamer_id}"
overlay_link = f"{API_BASE_URL}/overlay/{streamer_id}"


def copyable_link(label: str, value: str) -> None:
    st.text_input(label, value)
    escaped_value = value.replace("'", "\\'")
    components.html(
        f"""
        <button
          style="border:1px solid #0f766e;border-radius:6px;padding:9px 12px;background:#0f766e;color:white;font-weight:700;cursor:pointer;"
          onclick="navigator.clipboard.writeText('{escaped_value}')"
        >
          Copy link
        </button>
        """,
        height=44,
    )


link_col_1, link_col_2 = st.columns(2)
with link_col_1:
    copyable_link("Link donasi", donate_link)
with link_col_2:
    copyable_link("Link overlay OBS", overlay_link)

try:
    logs = api_get("/api/moderation/logs?limit=20")
except requests.RequestException as exc:
    st.error("Gagal mengambil donasi terbaru.")
    st.code(str(exc))
    st.stop()

df = pd.DataFrame(logs)

if df.empty:
    st.info("Belum ada donasi. Bagikan link donasi untuk mulai demo.")
    st.stop()

total = len(df)
total_safe = int((df["action_label"] == "allow").sum())
total_masked = int((df["action_label"] == "mask").sum())
total_blocked = int((df["action_label"] == "block").sum())
total_success_amount = int(df.loc[df["payment_status"] == "success", "amount"].sum())

metric_cols = st.columns(5)
metric_cols[0].metric("Total donasi", total)
metric_cols[1].metric("Total aman", total_safe)
metric_cols[2].metric("Total disensor", total_masked)
metric_cols[3].metric("Total diblokir", total_blocked)
metric_cols[4].metric("Nominal berhasil", f"IDR{total_success_amount:,}".replace(",", "."))

table = df.copy()
table["sender/display name"] = table["display_sender_name"].fillna("").where(
    table["display_sender_name"].fillna("") != "",
    table["sender_name_raw"],
)
table["overlay_status"] = table["overlay_displayed"].apply(lambda value: "visible" if int(value) else "hidden")

st.subheader("Donasi terbaru")
st.dataframe(
    table[
        [
            "sender/display name",
            "amount",
            "label_multiclass",
            "action_label",
            "payment_status",
            "overlay_status",
        ]
    ].rename(
        columns={
            "label_multiclass": "label",
            "action_label": "action",
        }
    ),
    use_container_width=True,
    hide_index=True,
)
