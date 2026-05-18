import sys
import os
from pathlib import Path

import requests
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

EXAMPLES = {
    "Donasi normal": {
        "sender_name_raw": "Budi",
        "sender_email_raw": "budi@example.com",
        "amount": 25000,
        "payment_method": "QRIS",
        "platform": "Saweria",
        "message_raw": "Semangat bang, lanjut mainnya!",
    },
    "Spam non-judol": {
        "sender_name_raw": "TokoAyu",
        "sender_email_raw": "ayu@example.com",
        "amount": 15000,
        "payment_method": "QRIS",
        "platform": "Saweria",
        "message_raw": "Follow IG aku ya, cek toko aku juga",
    },
    "Judol suspicious": {
        "sender_name_raw": "admininfo",
        "sender_email_raw": "info@example.com",
        "amount": 50000,
        "payment_method": "QRIS",
        "platform": "Saweria",
        "message_raw": "jam gacor malam ini, pola admin terbaru",
    },
    "Judol explicit": {
        "sender_name_raw": "kantorbola88",
        "sender_email_raw": "promo@example.com",
        "amount": 100000,
        "payment_method": "QRIS",
        "platform": "Saweria",
        "message_raw": "RTP tinggi malam ini, gas sekarang!",
    },
    "Judol fancy Unicode": {
        "sender_name_raw": "๑۞๑ ϰꍏ♫☂⊙☈♭ꍏ↳↳88 ๑۞๑",
        "sender_email_raw": "demo@example.com",
        "amount": 88000,
        "payment_method": "QRIS",
        "platform": "Saweria",
        "message_raw": "ｓｌｏｔ ｇａｃｏｒ rtp 98%",
    },
}


def apply_example(example_name: str) -> None:
    for key, value in EXAMPLES[example_name].items():
        st.session_state[key] = value


st.set_page_config(page_title="Kondomatur - Donor Form", page_icon="KT", layout="centered")
theme_mode = st.sidebar.radio("Tema tampilan", ["Dark", "Light"], horizontal=True)
palette = (
    {
        "bg": "#0b1018",
        "surface": "#111827",
        "surface_2": "#1d2939",
        "surface_3": "#253247",
        "text": "#f8fbff",
        "muted": "#aebacc",
        "line": "rgba(203, 213, 225, 0.16)",
        "cyan": "#22d3ee",
        "mint": "#34d399",
        "orange": "#f59e0b",
        "shadow": "rgba(0, 0, 0, 0.36)",
    }
    if theme_mode == "Dark"
    else {
        "bg": "#f5f7fb",
        "surface": "#ffffff",
        "surface_2": "#eef3f9",
        "surface_3": "#dce7f3",
        "text": "#111827",
        "muted": "#5d6b7d",
        "line": "rgba(15, 23, 42, 0.12)",
        "cyan": "#0891b2",
        "mint": "#059669",
        "orange": "#d97706",
        "shadow": "rgba(15, 23, 42, 0.12)",
    }
)
st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700;800;900&display=swap');

    html, body, [class*="css"] {{
        font-family: "Plus Jakarta Sans", ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}

    html, body, #root {{
        background: {palette["bg"]} !important;
    }}

    .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    section.main {{
        background:
            radial-gradient(circle at 8% 10%, color-mix(in srgb, {palette["cyan"]} 24%, transparent), transparent 30rem),
            radial-gradient(circle at 94% 2%, color-mix(in srgb, {palette["orange"]} 14%, transparent), transparent 26rem),
            linear-gradient(135deg, {palette["bg"]}, {palette["surface_2"]}) !important;
        color: {palette["text"]};
    }}

    .stApp::before {{
        content: "";
        position: fixed;
        inset: 0;
        pointer-events: none;
        background:
            linear-gradient(color-mix(in srgb, {palette["line"]} 44%, transparent) 1px, transparent 1px),
            linear-gradient(90deg, color-mix(in srgb, {palette["line"]} 44%, transparent) 1px, transparent 1px);
        background-size: 54px 54px;
        opacity: 0.28;
        mask-image: linear-gradient(180deg, black, transparent 76%);
    }}

    .stApp::after {{
        content: "";
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        height: 60px;
        z-index: 999999;
        pointer-events: none;
        background: linear-gradient(135deg, {palette["bg"]}, {palette["surface"]});
        border-top: 3px solid {palette["cyan"]};
    }}

    header,
    .stAppHeader,
    header[data-testid="stHeader"],
    [data-testid="stHeader"] {{
        height: 0;
        min-height: 0;
        background: transparent !important;
        visibility: hidden;
    }}

    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    #MainMenu {{
        visibility: hidden;
    }}

    .block-container {{
        max-width: 860px;
        padding-top: 3rem;
        padding-bottom: 4rem;
    }}

    [data-testid="stSidebar"] {{
        background: {palette["surface"]};
        border-right: 1px solid {palette["line"]};
    }}

    [data-testid="stSidebar"] > div {{
        padding-top: 3rem;
    }}

    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {{
        color: {palette["text"]};
    }}

    [data-testid="stForm"], div[data-testid="stAlert"] {{
        border-radius: 8px;
    }}

    [data-testid="stForm"] {{
        border: 1px solid {palette["line"]};
        background: linear-gradient(135deg, color-mix(in srgb, {palette["surface"]} 94%, white 6%), {palette["surface"]});
        box-shadow: 0 24px 70px {palette["shadow"]};
        padding: 1.25rem;
    }}

    h1, h2, h3, p, label, [data-testid="stMarkdownContainer"] {{
        color: {palette["text"]};
    }}

    h1 {{
        font-weight: 900;
        letter-spacing: 0;
        font-size: clamp(2.4rem, 5vw, 3.5rem);
    }}

    .stCaptionContainer,
    [data-testid="stCaptionContainer"],
    p {{
        color: {palette["muted"]};
    }}

    .stButton > button, [data-testid="stFormSubmitButton"] button {{
        border-radius: 8px;
        border: 1px solid {palette["line"]};
        background: color-mix(in srgb, {palette["surface"]} 88%, black 12%);
        color: {palette["text"]};
        box-shadow: 0 14px 34px {palette["shadow"]};
        font-weight: 800;
        min-height: 2.75rem;
        transition: transform 160ms ease, border-color 160ms ease, background 160ms ease;
    }}

    .stButton > button:hover, [data-testid="stFormSubmitButton"] button:hover {{
        border-color: {palette["cyan"]};
        background: {palette["surface_3"]};
        color: {palette["text"]};
        transform: translateY(-1px);
    }}

    [data-testid="stFormSubmitButton"] button {{
        border-color: {palette["cyan"]};
        background: linear-gradient(135deg, {palette["cyan"]}, {palette["mint"]});
        color: #06111f;
        box-shadow: 0 16px 40px color-mix(in srgb, {palette["cyan"]} 22%, transparent);
    }}

    .stTextInput input,
    .stNumberInput input,
    .stTextArea textarea,
    .stSelectbox [data-baseweb="select"] > div {{
        border: 1px solid {palette["line"]};
        border-radius: 8px;
        background: color-mix(in srgb, {palette["surface_2"]} 88%, black 12%);
        color: {palette["text"]};
    }}

    [data-testid="stNumberInput"] button {{
        border-color: {palette["line"]};
        background: {palette["surface_2"]} !important;
        color: {palette["text"]} !important;
    }}

    .stTextInput input:focus,
    .stNumberInput input:focus,
    .stTextArea textarea:focus {{
        border-color: {palette["cyan"]};
        box-shadow: 0 0 0 3px color-mix(in srgb, {palette["cyan"]} 20%, transparent);
    }}

    [data-testid="stRadio"] label {{
        color: {palette["text"]};
        font-weight: 700;
    }}

    div[data-testid="stAlert"] {{
        border: 1px solid {palette["line"]};
        background: color-mix(in srgb, {palette["surface"]} 90%, transparent);
    }}

    pre, code {{
        border-radius: 8px;
    }}

    @media (max-width: 640px) {{
        .block-container {{
            padding-inline: 1rem;
            padding-top: 2rem;
        }}

        [data-testid="column"] {{
            width: 100% !important;
            flex: 1 1 100% !important;
        }}
    }}
    </style>
    """,
    unsafe_allow_html=True,
)
st.title("Kondomatur")
st.caption("Simulasi form donasi dan checkout sandbox untuk demo moderasi pesan live streaming.")

cols = st.columns(5)
for index, name in enumerate(EXAMPLES):
    if cols[index].button(name, use_container_width=True):
        apply_example(name)

with st.form("donation_form"):
    streamer_id = st.text_input("Streamer ID", value="streamer_001")
    sender_name_raw = st.text_input("Nama pengirim", key="sender_name_raw", value=st.session_state.get("sender_name_raw", "Budi"))
    sender_email_raw = st.text_input("Email pengirim", key="sender_email_raw", value=st.session_state.get("sender_email_raw", "budi@example.com"))
    amount = st.number_input("Nominal donasi", min_value=0, step=5000, key="amount", value=int(st.session_state.get("amount", 25000)))
    payment_method = st.selectbox("Metode pembayaran", ["QRIS", "Virtual Account", "E-Wallet", "Transfer Bank"], key="payment_method")
    platform = st.selectbox("Platform", ["Saweria", "Trakteer", "YouTube Live", "TikTok Live", "Twitch"], key="platform")
    message_raw = st.text_area("Pesan donasi", key="message_raw", value=st.session_state.get("message_raw", "Semangat bang"))
    streamer_filter_mode = st.radio("Mode perlindungan", ["sensor", "block"], horizontal=True, key="streamer_filter_mode")
    submitted = st.form_submit_button("Kirim Donasi", use_container_width=True)

if submitted:
    st.session_state.pop("pending_payment_intent_id", None)
    payload = {
        "streamer_id": streamer_id,
        "sender_name_raw": sender_name_raw,
        "sender_email_raw": sender_email_raw,
        "amount": int(amount),
        "payment_method": payment_method,
        "platform": platform,
        "message_raw": message_raw,
    }
    try:
        requests.post(
            f"{API_BASE_URL}/api/settings/filter-mode",
            json={"streamer_id": streamer_id, "filter_mode": streamer_filter_mode},
            timeout=10,
        ).raise_for_status()
        response = requests.post(f"{API_BASE_URL}/api/payment-intents", json=payload, timeout=10)
        response.raise_for_status()
        result = response.json()
        if result.get("payment_intent_created"):
            st.success("Payment intent sandbox berhasil dibuat. Lanjutkan pembayaran untuk menampilkan overlay.")
            st.session_state["pending_payment_intent_id"] = result["payment_intent_id"]
            st.code(f"{API_BASE_URL}{result['checkout_url']}")
        elif result["payment_status"] == "rejected":
            st.error("Donasi gagal diproses karena pesan terindikasi melanggar kebijakan.")
        else:
            st.warning("Donasi menunggu review.")

        st.subheader("Detail Demo")
        st.json(
            {
                "payment_intent_created": result.get("payment_intent_created"),
                "payment_intent_id": result.get("payment_intent_id"),
                "label_multiclass": result["label_multiclass"],
                "risk_score": result["risk_score"],
                "risk_level": result.get("risk_level"),
                "action_label": result["action_label"],
                "payment_status": result["payment_status"],
                "moderation_status": result["moderation_status"],
                "overlay_displayed": result["overlay_displayed"],
                "display_sender_name": result["display_sender_name"],
                "display_message": result["display_message"],
                "explanation": result["explanation"],
            }
        )
    except requests.RequestException as exc:
        st.error(f"Gagal menghubungi API di {API_BASE_URL}. Jalankan uvicorn terlebih dahulu.")
        st.code(str(exc))

pending_payment_intent_id = st.session_state.get("pending_payment_intent_id")
if pending_payment_intent_id:
    st.divider()
    st.subheader("Checkout Sandbox")
    if st.button("Bayar Sandbox", use_container_width=True):
        try:
            response = requests.post(
                f"{API_BASE_URL}/api/checkout/{pending_payment_intent_id}/pay",
                timeout=10,
            )
            response.raise_for_status()
            result = response.json()
            st.success("Pembayaran sandbox berhasil.")
            st.json(result)
            st.session_state.pop("pending_payment_intent_id", None)
        except requests.RequestException as exc:
            st.error("Gagal menyelesaikan checkout sandbox.")
            st.code(str(exc))
