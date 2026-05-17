import os
import time

import requests
import streamlit as st


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(page_title="Kondomatur - Overlay", page_icon="KT", layout="centered")
theme_mode = st.sidebar.radio("Tema tampilan", ["Dark", "Light"], horizontal=True)
palette = (
    {
        "bg": "#06163f",
        "surface": "#071f56",
        "text": "#f8fbff",
        "muted": "#a7c1e8",
        "line": "rgba(194, 223, 255, 0.20)",
        "cyan": "#00d9ff",
        "shadow": "rgba(0, 8, 30, 0.36)",
    }
    if theme_mode == "Dark"
    else {
        "bg": "#eef6ff",
        "surface": "#ffffff",
        "text": "#06163f",
        "muted": "#536c98",
        "line": "rgba(6, 22, 63, 0.14)",
        "cyan": "#0074ff",
        "shadow": "rgba(8, 49, 120, 0.15)",
    }
)

st.markdown(
    f"""
    <style>
    .stApp {{
        background:
            linear-gradient(90deg, {palette["cyan"]} 0 6px, transparent 6px),
            linear-gradient(135deg, {palette["bg"]}, {palette["surface"]});
        color: {palette["text"]};
    }}
    .block-container {{ padding-top: 2rem; max-width: 780px; }}
    .overlay-card {{
        border: 1px solid {palette["line"]};
        border-radius: 8px;
        padding: 28px;
        background: {palette["surface"]};
        box-shadow: 0 20px 55px {palette["shadow"]};
    }}
    .amount {{ font-size: 32px; font-weight: 800; color: {palette["cyan"]}; }}
    .message {{ font-size: 24px; margin-top: 14px; color: {palette["muted"]}; }}
    h1, h2, h3, p, label, [data-testid="stMarkdownContainer"] {{
        color: {palette["text"]};
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

top = st.columns([1, 1])
top[0].title("Overlay Donasi")
auto_refresh = top[1].toggle("Auto refresh", value=False)

if auto_refresh:
    time.sleep(3)
    st.rerun()

if st.button("Refresh"):
    st.rerun()

try:
    response = requests.get(f"{API_BASE_URL}/api/overlay", timeout=10)
    response.raise_for_status()
    donations = response.json()
except requests.RequestException as exc:
    st.error("API belum berjalan. Jalankan: uvicorn api.main:app --reload --port 8000")
    st.code(str(exc))
    st.stop()

if not donations:
    st.info("Belum ada donasi yang tampil di overlay.")
    st.stop()

latest = donations[0]
amount = f"IDR{int(latest['amount']):,}".replace(",", ".")
sender = latest["display_sender_name"]
message = latest["display_message"]

st.markdown(
    f"""
    <div class="overlay-card">
        <div class="amount">{amount} dari {sender}</div>
        <div class="message">{message}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.expander("Riwayat overlay terbaru"):
    for donation in donations[1:]:
        amount_item = f"IDR{int(donation['amount']):,}".replace(",", ".")
        st.write(f"{amount_item} dari {donation['display_sender_name']}: {donation['display_message']}")
