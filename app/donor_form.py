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
        "bg": "#06163f",
        "surface": "#071f56",
        "surface_2": "#0a2b70",
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
        "surface_2": "#edf5ff",
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
            linear-gradient(135deg, {palette["bg"]}, {palette["surface_2"]});
        color: {palette["text"]};
    }}
    .block-container {{
        padding-top: 2rem;
    }}
    [data-testid="stForm"], div[data-testid="stAlert"] {{
        border-radius: 8px;
    }}
    h1, h2, h3, p, label, [data-testid="stMarkdownContainer"] {{
        color: {palette["text"]};
    }}
    .stButton > button, [data-testid="stFormSubmitButton"] button {{
        border-radius: 8px;
        border: 1px solid {palette["line"]};
        box-shadow: 0 14px 34px {palette["shadow"]};
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
