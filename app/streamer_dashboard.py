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


st.set_page_config(page_title="KondomDonatur - Panel Streamer", page_icon="KD", layout="wide")
st.markdown(
    """
    <style>
    .block-container { padding-top: 2rem; max-width: 1180px; }
    [data-testid="stMetric"] {
        background: #f8fafc;
        border: 1px solid #d9e0ea;
        border-radius: 8px;
        padding: 14px;
    }
    div[data-testid="stAlert"] {
        border-radius: 8px;
    }
    .kd-card {
        border: 1px solid #d9e0ea;
        border-radius: 8px;
        padding: 16px;
        background: #ffffff;
    }
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
    selected_mode = st.radio(
        "Mode proteksi",
        ["sensor", "block"],
        index=["sensor", "block"].index(current_mode),
        horizontal=True,
    )
    if selected_mode != current_mode:
        settings = api_post(
            "/api/settings/filter-mode",
            {"streamer_id": streamer_id, "filter_mode": selected_mode},
        )
        st.success(f"Mode aktif: {settings['filter_mode']}")

with status_col:
    st.write("Status sistem")
    s1, s2, s3 = st.columns(3)
    s1.success("AI Moderation aktif")
    s2.success("Payment Sandbox aktif")
    s3.success("Overlay aktif")

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
