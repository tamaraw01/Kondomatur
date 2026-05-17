from datetime import datetime, timezone
from html import escape
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import text

from src.config import DEFAULT_STREAMER_ID, ENVIRONMENT, MODEL_PATH, get_cors_origins
from src.database import (
    db_connection,
    fetch_all,
    fetch_one,
    fetch_settings,
    init_db,
    insert_moderation_result,
    insert_processed_donation,
    insert_raw_donation,
    update_filter_mode,
    utc_now_iso,
)
from src.decision_engine import make_decision
from src.rule_detector import build_processed_record


class DonationRequest(BaseModel):
    sender_name_raw: str = Field(default="")
    sender_email_raw: str = Field(default="")
    amount: int = Field(default=0, ge=0)
    payment_method: str = Field(default="QRIS")
    platform: str = Field(default="Saweria")
    message_raw: str = Field(default="")
    streamer_filter_mode: str | None = Field(default=None, pattern="^(sensor|block)$")


class PaymentIntentRequest(BaseModel):
    streamer_id: str = DEFAULT_STREAMER_ID
    sender_name_raw: str = Field(default="")
    sender_email_raw: str = Field(default="")
    amount: int = Field(default=0, ge=0)
    payment_method: str = Field(default="QRIS")
    platform: str = Field(default="KondomDonatur")
    message_raw: str = Field(default="")


class FilterModeRequest(BaseModel):
    streamer_id: str = DEFAULT_STREAMER_ID
    filter_mode: str = Field(pattern="^(sensor|block)$")


app = FastAPI(
    title="KondomDonatur API",
    description="Simulasi moderasi donasi live streaming untuk deteksi promosi judol.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/")
def root() -> dict[str, Any]:
    init_db()
    return {
        "app": "KondomDonatur",
        "status": "ok",
        "message": "API siap menerima simulasi donasi.",
    }


@app.get("/health")
def health() -> dict[str, Any]:
    init_db()
    return {
        "status": "ok",
        "app": "KondomDonatur",
        "environment": ENVIRONMENT,
        "model_available": MODEL_PATH.exists(),
    }


def _base_url() -> str:
    return ""


def _page(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(
        f"""
        <!doctype html>
        <html lang="id">
        <head>
          <meta charset="utf-8" />
          <meta name="viewport" content="width=device-width, initial-scale=1" />
          <title>{title}</title>
          <style>
            :root {{ font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: #172033; background: #f4f7fb; }}
            body {{ margin: 0; }}
            body::before {{ content: ""; position: fixed; inset: 0 0 auto; height: 260px; background: linear-gradient(135deg, #0f766e 0%, #184e77 58%, #25324a 100%); z-index: -1; }}
            main {{ width: min(1080px, calc(100% - 32px)); margin: 0 auto; padding: 32px 0; }}
            .panel {{ background: rgba(255,255,255,.98); border: 1px solid #d9e0ea; border-radius: 8px; padding: 22px; margin-bottom: 16px; box-shadow: 0 14px 34px rgba(23,32,51,.08); }}
            .grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }}
            .metrics {{ display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 10px; }}
            .metric {{ border: 1px solid #d9e0ea; border-radius: 8px; padding: 14px; background: #f8fafc; }}
            .metric strong {{ font-size: 22px; }}
            h1, h2, p {{ margin-top: 0; }}
            h1 {{ font-size: 34px; }}
            h2 {{ font-size: 18px; }}
            label {{ display: grid; gap: 6px; margin-bottom: 12px; font-weight: 700; }}
            input, textarea, select {{ width: 100%; border: 1px solid #c8d1df; border-radius: 6px; padding: 10px 11px; font: inherit; box-sizing: border-box; }}
            button, .button {{ display: inline-flex; justify-content: center; align-items: center; border: 1px solid #0f766e; border-radius: 6px; padding: 10px 12px; background: #0f766e; color: white; font-weight: 800; text-decoration: none; cursor: pointer; }}
            button.secondary {{ background: #f8fafc; color: #172033; border-color: #b9c4d3; }}
            .status-row {{ display: flex; flex-wrap: wrap; gap: 8px; }}
            .pill {{ border-radius: 999px; padding: 7px 10px; background: #dcfce7; color: #166534; font-weight: 800; font-size: 13px; }}
            .muted {{ color: #5f6b7a; }}
            .link-row {{ display: grid; grid-template-columns: 1fr auto; gap: 8px; align-items: end; }}
            .section-label {{ color: #0f766e; font-size: 12px; font-weight: 900; text-transform: uppercase; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ border-bottom: 1px solid #e5eaf1; padding: 10px; text-align: left; font-size: 14px; }}
            th {{ background: #f8fafc; }}
            pre {{ background: #111827; color: #e5edf7; border-radius: 6px; padding: 12px; overflow: auto; }}
            .checkout-card {{ max-width: 720px; margin-inline: auto; }}
            .checkout-summary {{ display: grid; gap: 14px; margin: 18px 0; padding: 18px; border: 1px solid #d9e0ea; border-radius: 8px; background: #f8fafc; }}
            .checkout-summary strong {{ display: block; margin-top: 4px; color: #172033; font-size: 22px; }}
            .summary-label {{ color: #657184; font-size: 12px; font-weight: 900; text-transform: uppercase; }}
            .summary-message {{ padding-top: 12px; border-top: 1px solid #e5eaf1; }}
            .summary-message p {{ margin: 6px 0 0; color: #344054; }}
            .public-result {{ margin-top: 16px; }}
            .public-notice {{ display: grid; gap: 4px; padding: 14px 16px; border: 1px solid #bfdbfe; border-radius: 8px; background: #eff6ff; color: #1d4ed8; }}
            .public-notice strong {{ color: #1e3a8a; }}
            .public-notice.success {{ border-color: #86efac; background: #f0fdf4; color: #166534; }}
            .public-notice.success strong {{ color: #14532d; }}
            .public-notice.danger {{ border-color: #fecaca; background: #fff1f2; color: #9f1239; }}
            .public-notice.danger strong {{ color: #881337; }}
            .overlay-card {{ border: 1px solid #d7dde8; border-radius: 8px; padding: 28px; background: #fff; box-shadow: 0 12px 30px rgba(23, 37, 84, .12); }}
            .amount {{ font-size: 32px; font-weight: 900; }}
            .message {{ font-size: 24px; margin-top: 12px; color: #374151; }}
            @media (max-width: 760px) {{ .grid, .metrics, .link-row {{ grid-template-columns: 1fr; }} }}
          </style>
        </head>
        <body>{body}</body>
        </html>
        """
    )


def _fetch_checkout_public_detail(payment_intent_id: str) -> dict[str, Any]:
    with db_connection() as conn:
        detail = fetch_one(
            conn,
            """
            SELECT dr.amount, dr.sender_name_raw, dr.message_raw, mr.payment_status
            FROM donations_raw dr
            JOIN moderation_results mr ON mr.donation_id = dr.donation_id
            WHERE dr.donation_id = :payment_intent_id
            """,
            {"payment_intent_id": payment_intent_id},
        )
    if not detail:
        raise HTTPException(status_code=404, detail="payment_intent_id tidak ditemukan")
    return {
        "amount": detail.get("amount") or 0,
        "sender_name": detail.get("sender_name_raw") or "-",
        "message": detail.get("message_raw") or "-",
        "payment_status": detail.get("payment_status") or "pending",
    }


@app.get("/streamer", response_class=HTMLResponse)
def streamer_panel() -> HTMLResponse:
    settings = fetch_settings()
    streamer_id = settings.get("streamer_id", DEFAULT_STREAMER_ID)
    donate_link = f"/donate/{streamer_id}"
    overlay_link = f"/overlay/{streamer_id}"
    return _page(
        "Panel Streamer",
        f"""
        <main>
          <section class="panel">
            <h1>Panel Streamer</h1>
            <p class="muted">Prototype AI-powered donation payment gateway. Pilih mode proteksi, salin link donasi, lalu pasang overlay di OBS.</p>
            <div class="grid">
              <label>Mode proteksi
                <select id="mode">
                  <option value="sensor" {"selected" if settings.get("filter_mode") == "sensor" else ""}>Mode Sensor</option>
                  <option value="block" {"selected" if settings.get("filter_mode") == "block" else ""}>Mode Blokir</option>
                </select>
              </label>
              <div>
                <p class="muted">Status sistem</p>
                <div class="status-row">
                  <span class="pill">AI Moderation aktif</span>
                  <span class="pill">Payment Sandbox aktif</span>
                  <span class="pill">Overlay aktif</span>
                </div>
              </div>
            </div>
          </section>

          <section class="panel grid">
            <div class="link-row">
              <label>Link donasi<input id="donateLink" readonly value="{donate_link}" /></label>
              <button class="secondary" onclick="copyValue('donateLink')">Copy</button>
            </div>
            <div class="link-row">
              <label>Link overlay OBS<input id="overlayLink" readonly value="{overlay_link}" /></label>
              <button class="secondary" onclick="copyValue('overlayLink')">Copy</button>
            </div>
          </section>

          <section class="panel">
            <div class="metrics" id="metrics"></div>
          </section>

          <section class="panel">
            <h2>Donasi terbaru</h2>
            <table>
              <thead><tr><th>Sender/display name</th><th>Amount</th><th>Label</th><th>Action</th><th>Payment</th><th>Overlay</th></tr></thead>
              <tbody id="latestRows"><tr><td colspan="6">Memuat...</td></tr></tbody>
            </table>
          </section>
        </main>
        <script>
          const streamerId = {streamer_id!r};
          const modeEl = document.querySelector('#mode');
          modeEl.addEventListener('change', async () => {{
            await fetch('/api/settings/filter-mode', {{
              method: 'POST',
              headers: {{ 'Content-Type': 'application/json' }},
              body: JSON.stringify({{ streamer_id: streamerId, filter_mode: modeEl.value }})
            }});
          }});
          function absolutePath(path) {{ return new URL(path, window.location.origin).toString(); }}
          document.querySelector('#donateLink').value = absolutePath('{donate_link}');
          document.querySelector('#overlayLink').value = absolutePath('{overlay_link}');
          async function copyValue(id) {{ await navigator.clipboard.writeText(document.querySelector('#' + id).value); }}
          function fmtAmount(value) {{ return 'IDR' + Number(value || 0).toLocaleString('id-ID'); }}
          async function loadLatest() {{
            const res = await fetch('/api/moderation/logs?limit=20');
            const rows = await res.json();
            const total = rows.length;
            const safe = rows.filter(r => r.action_label === 'allow').length;
            const masked = rows.filter(r => r.action_label === 'mask').length;
            const blocked = rows.filter(r => r.action_label === 'block').length;
            const paid = rows.filter(r => r.payment_status === 'success').reduce((sum, r) => sum + Number(r.amount || 0), 0);
            document.querySelector('#metrics').innerHTML = [
              ['Total donasi', total], ['Total aman', safe], ['Total disensor', masked], ['Total diblokir', blocked], ['Nominal berhasil', fmtAmount(paid)]
            ].map(([k,v]) => `<div class="metric"><strong>${{v}}</strong><br><span class="muted">${{k}}</span></div>`).join('');
            document.querySelector('#latestRows').innerHTML = rows.length ? rows.map(r => `
              <tr>
                <td>${{r.display_sender_name || r.sender_name_raw || '-'}}</td>
                <td>${{fmtAmount(r.amount)}}</td>
                <td>${{r.label_multiclass}}</td>
                <td>${{r.action_label}}</td>
                <td>${{r.payment_status}}</td>
                <td>${{Number(r.overlay_displayed) ? 'visible' : 'hidden'}}</td>
              </tr>`).join('') : '<tr><td colspan="6">Belum ada donasi.</td></tr>';
          }}
          loadLatest();
        </script>
        """,
    )


@app.get("/donate/{streamer_id}", response_class=HTMLResponse)
def donate_page(streamer_id: str) -> HTMLResponse:
    return _page(
        "Kirim Donasi",
        f"""
        <main>
          <section class="panel">
            <h1>Kirim Donasi</h1>
            <p class="muted">Payment sandbox untuk streamer <strong>{streamer_id}</strong>.</p>
            <form id="donateForm">
              <input type="hidden" name="streamer_id" value="{streamer_id}" />
              <label>Nama pengirim<input name="sender_name_raw" value="Budi" required /></label>
              <label>Email<input name="sender_email_raw" value="budi@example.com" /></label>
              <label>Nominal<input name="amount" type="number" min="0" value="25000" /></label>
              <label>Pesan<textarea name="message_raw" rows="4">Semangat bang, lanjut mainnya!</textarea></label>
              <button type="submit">Lanjut ke Checkout</button>
            </form>
            <pre id="result"></pre>
          </section>
        </main>
        <script>
          const form = document.querySelector('#donateForm');
          const result = document.querySelector('#result');
          form.addEventListener('submit', async (event) => {{
            event.preventDefault();
            const payload = Object.fromEntries(new FormData(form).entries());
            payload.amount = Number(payload.amount || 0);
            payload.payment_method = 'QRIS';
            payload.platform = 'KondomDonatur';
            const res = await fetch('/api/payment-intents', {{
              method: 'POST',
              headers: {{ 'Content-Type': 'application/json' }},
              body: JSON.stringify(payload)
            }});
            const data = await res.json();
            if (data.checkout_url) {{
              window.location.href = data.checkout_url;
              return;
            }}
            result.textContent = data.donor_message || JSON.stringify(data, null, 2);
          }});
        </script>
        """,
    )


@app.get("/checkout/{payment_intent_id}", response_class=HTMLResponse)
def checkout_page(payment_intent_id: str) -> HTMLResponse:
    detail = _fetch_checkout_public_detail(payment_intent_id)
    amount = f"IDR{int(detail.get('amount') or 0):,}".replace(",", ".")
    sender_name = escape(detail.get("sender_name") or "-")
    message = escape(detail.get("message") or "-")
    payment_status = detail.get("payment_status")
    initial_notice = """
            <div class="public-notice">
              <strong>Siap diproses</strong>
              <span>Klik tombol bayar untuk menyelesaikan checkout sandbox.</span>
            </div>
    """
    button_disabled = ""
    if payment_status == "success":
        button_disabled = "disabled"
        initial_notice = """
            <div class="public-notice success">
              <strong>Pembayaran sudah berhasil</strong>
              <span>Terima kasih, donasimu sudah diproses untuk streamer.</span>
            </div>
        """
    elif payment_status == "rejected":
        button_disabled = "disabled"
        initial_notice = """
            <div class="public-notice danger">
              <strong>Donasi gagal diproses</strong>
              <span>Pesan terindikasi melanggar kebijakan sehingga pembayaran tidak dilanjutkan.</span>
            </div>
        """
    return _page(
        "Checkout Sandbox",
        f"""
        <main>
          <section class="panel checkout-card">
            <h1>Checkout Sandbox</h1>
            <p class="muted">Selesaikan pembayaran simulasi untuk mengirim donasi ke streamer.</p>
            <div class="checkout-summary">
              <div>
                <span class="summary-label">Nominal</span>
                <strong>{amount}</strong>
              </div>
              <div>
                <span class="summary-label">Pengirim</span>
                <strong>{sender_name}</strong>
              </div>
              <div class="summary-message">
                <span class="summary-label">Pesan</span>
                <p>{message}</p>
              </div>
            </div>
            <button id="payButton" {button_disabled}>Bayar Sandbox</button>
            <div id="result" class="public-result" aria-live="polite">{initial_notice}</div>
          </section>
        </main>
        <script>
          document.querySelector('#payButton').addEventListener('click', async () => {{
            const button = document.querySelector('#payButton');
            const result = document.querySelector('#result');
            button.disabled = true;
            button.textContent = 'Memproses...';
            result.innerHTML = '<div class="public-notice"><strong>Memproses pembayaran</strong><span>Mohon tunggu sebentar.</span></div>';
            const res = await fetch('/api/checkout/{payment_intent_id}/pay', {{ method: 'POST' }});
            const data = await res.json();
            if (data.payment_status === 'success') {{
              result.innerHTML = '<div class="public-notice success"><strong>Pembayaran berhasil</strong><span>Terima kasih, donasimu sudah diproses untuk streamer.</span></div>';
            }} else {{
              result.innerHTML = '<div class="public-notice danger"><strong>Donasi gagal diproses</strong><span>' + (data.message || 'Pesan terindikasi melanggar kebijakan sehingga pembayaran tidak dilanjutkan.') + '</span></div>';
              button.disabled = false;
            }}
            button.textContent = 'Bayar Sandbox';
          }});
        </script>
        """,
    )


@app.get("/overlay/{streamer_id}", response_class=HTMLResponse)
def obs_overlay_page(streamer_id: str) -> HTMLResponse:
    return _page(
        "Overlay OBS",
        f"""
        <main>
          <section class="overlay-card" id="overlayCard">
            <div class="amount">Menunggu donasi...</div>
            <div class="message">Streamer: {streamer_id}</div>
          </section>
        </main>
        <script>
          function fmtAmount(value) {{ return 'IDR' + Number(value || 0).toLocaleString('id-ID'); }}
          async function loadOverlay() {{
            const res = await fetch('/api/overlay/{streamer_id}');
            const rows = await res.json();
            const latest = rows[0];
            if (!latest) return;
            document.querySelector('#overlayCard').innerHTML = `
              <div class="amount">${{fmtAmount(latest.amount)}} dari ${{latest.display_sender_name}}</div>
              <div class="message">${{latest.display_message}}</div>
            `;
          }}
          loadOverlay();
          setInterval(loadOverlay, 3000);
        </script>
        """,
    )


@app.post("/api/donations")
def create_donation(payload: DonationRequest) -> dict[str, Any]:
    init_db()
    settings = fetch_settings()
    filter_mode = payload.streamer_filter_mode or settings.get("filter_mode", "sensor")
    now = utc_now_iso()
    timestamp = datetime.now(timezone.utc).isoformat()

    decision_input = payload.model_dump()
    decision = make_decision(decision_input, filter_mode)
    donation_id = decision["donation_id"]

    raw_row = {
        "donation_id": donation_id,
        "timestamp": timestamp,
        "platform": payload.platform,
        "sender_name_raw": payload.sender_name_raw,
        "sender_email_raw": payload.sender_email_raw,
        "amount": payload.amount,
        "payment_method": payload.payment_method,
        "message_raw": payload.message_raw,
        "streamer_filter_mode": filter_mode,
        "created_at": now,
    }
    processed_row = build_processed_record(
        donation_id,
        payload.sender_name_raw,
        payload.message_raw,
        payload.sender_email_raw,
    )
    moderation_row = {
        "donation_id": donation_id,
        "label_binary": decision["label_binary"],
        "label_multiclass": decision["label_multiclass"],
        "risk_score": decision["risk_score"],
        "confidence": decision["confidence"],
        "action_label": decision["action_label"],
        "moderation_status": decision["moderation_status"],
        "payment_status": decision["payment_status"],
        "overlay_displayed": int(decision["overlay_displayed"]),
        "display_sender_name": decision["display_sender_name"],
        "display_message": decision["display_message"],
        "explanation": decision["explanation"],
        "created_at": now,
    }

    with db_connection() as conn:
        insert_raw_donation(conn, raw_row)
        insert_processed_donation(conn, processed_row)
        insert_moderation_result(conn, moderation_row)

    return decision


def _save_moderated_donation(payload: PaymentIntentRequest, filter_mode: str, payment_pending: bool) -> dict[str, Any]:
    now = utc_now_iso()
    decision_input = payload.model_dump()
    decision = make_decision(decision_input, filter_mode)
    donation_id = decision["donation_id"]

    raw_row = {
        "donation_id": donation_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "platform": payload.platform,
        "sender_name_raw": payload.sender_name_raw,
        "sender_email_raw": payload.sender_email_raw,
        "amount": payload.amount,
        "payment_method": payload.payment_method,
        "message_raw": payload.message_raw,
        "streamer_filter_mode": filter_mode,
        "created_at": now,
    }
    processed_row = build_processed_record(
        donation_id,
        payload.sender_name_raw,
        payload.message_raw,
        payload.sender_email_raw,
    )

    payment_status = decision["payment_status"]
    overlay_displayed = int(decision["overlay_displayed"])
    if payment_pending and payment_status == "success":
        payment_status = "pending"
        overlay_displayed = 0

    moderation_row = {
        "donation_id": donation_id,
        "label_binary": decision["label_binary"],
        "label_multiclass": decision["label_multiclass"],
        "risk_score": decision["risk_score"],
        "confidence": decision["confidence"],
        "action_label": decision["action_label"],
        "moderation_status": decision["moderation_status"],
        "payment_status": payment_status,
        "overlay_displayed": overlay_displayed,
        "display_sender_name": decision["display_sender_name"],
        "display_message": decision["display_message"],
        "explanation": decision["explanation"],
        "created_at": now,
    }
    with db_connection() as conn:
        insert_raw_donation(conn, raw_row)
        insert_processed_donation(conn, processed_row)
        insert_moderation_result(conn, moderation_row)

    return {**decision, "donation_id": donation_id, "payment_status": payment_status, "overlay_displayed": bool(overlay_displayed)}


@app.post("/api/payment-intents")
def create_payment_intent(payload: PaymentIntentRequest) -> dict[str, Any]:
    init_db()
    settings = fetch_settings(payload.streamer_id)
    filter_mode = settings.get("filter_mode", "sensor")
    decision = _save_moderated_donation(payload, filter_mode, payment_pending=True)

    if filter_mode == "block" and decision["label_binary"]:
        with db_connection() as conn:
            conn.execute(
                text(
                    """
                    UPDATE moderation_results
                    SET action_label = :action_label,
                        moderation_status = :moderation_status,
                        payment_status = :payment_status,
                        overlay_displayed = :overlay_displayed,
                        display_sender_name = :display_sender_name,
                        display_message = :display_message
                    WHERE donation_id = :donation_id
                    """
                ),
                {
                    "action_label": "block",
                    "moderation_status": "blocked",
                    "payment_status": "rejected",
                    "overlay_displayed": 0,
                    "display_sender_name": "",
                    "display_message": "",
                    "donation_id": decision["donation_id"],
                },
            )
        decision = {
            **decision,
            "action_label": "block",
            "moderation_status": "blocked",
            "payment_status": "rejected",
            "overlay_displayed": False,
            "display_sender_name": "",
            "display_message": "",
            "donor_message": "Donasi gagal diproses karena pesan terindikasi melanggar kebijakan.",
        }

    if decision["payment_status"] == "rejected":
        return {
            **decision,
            "payment_intent_created": False,
            "payment_intent_id": None,
            "checkout_url": None,
            "overlay_status": "hidden",
        }

    payment_intent_id = decision["donation_id"]
    return {
        **decision,
        "payment_intent_created": True,
        "payment_intent_id": payment_intent_id,
        "checkout_url": f"/checkout/{payment_intent_id}",
        "overlay_status": "hidden",
    }


@app.get("/api/checkout/{payment_intent_id}")
def checkout_public_detail(payment_intent_id: str) -> dict[str, Any]:
    init_db()
    return _fetch_checkout_public_detail(payment_intent_id)


@app.post("/api/checkout/{payment_intent_id}/pay")
def pay_payment_intent(payment_intent_id: str) -> dict[str, Any]:
    init_db()
    with db_connection() as conn:
        row = fetch_one(
            conn,
            "SELECT * FROM moderation_results WHERE donation_id = :payment_intent_id",
            {"payment_intent_id": payment_intent_id},
        )
        if row is None:
            raise HTTPException(status_code=404, detail="payment_intent_id tidak ditemukan")
        if row["payment_status"] == "rejected":
            return {
                "payment_intent_id": payment_intent_id,
                "payment_status": "rejected",
                "overlay_status": "hidden",
                "message": "Donasi gagal diproses karena pesan terindikasi melanggar kebijakan.",
            }
        conn.execute(
            text(
                """
                UPDATE moderation_results
                SET payment_status = :payment_status,
                    overlay_displayed = :overlay_displayed
                WHERE donation_id = :payment_intent_id
                """
            ),
            {"payment_status": "success", "overlay_displayed": 1, "payment_intent_id": payment_intent_id},
        )
    return {
        "payment_intent_id": payment_intent_id,
        "payment_status": "success",
        "overlay_status": "visible",
        "message": "Pembayaran sandbox berhasil.",
    }


@app.get("/api/overlay")
def overlay_donations(limit: int = 10) -> list[dict[str, Any]]:
    init_db()
    with db_connection() as conn:
        return fetch_all(
            conn,
            """
            SELECT
                mr.donation_id,
                dr.amount,
                mr.display_sender_name,
                mr.display_message,
                mr.created_at
            FROM moderation_results mr
            JOIN donations_raw dr ON dr.donation_id = mr.donation_id
            WHERE mr.overlay_displayed = 1
            ORDER BY mr.created_at DESC
            LIMIT :limit
            """,
            {"limit": limit},
        )


@app.get("/api/overlay/{streamer_id}")
def streamer_overlay_donations(streamer_id: str, limit: int = 10) -> list[dict[str, Any]]:
    return overlay_donations(limit=limit)


@app.get("/api/moderation/logs")
def moderation_logs(limit: int = 200) -> list[dict[str, Any]]:
    init_db()
    with db_connection() as conn:
        return fetch_all(
            conn,
            """
            SELECT
                dr.donation_id,
                dr.timestamp,
                dr.platform,
                dr.sender_name_raw,
                dr.sender_email_raw,
                dr.amount,
                dr.payment_method,
                dr.message_raw,
                dr.streamer_filter_mode,
                dp.message_deobfuscated,
                dp.sender_name_deobfuscated,
                mr.label_binary,
                mr.label_multiclass,
                mr.risk_score,
                mr.confidence,
                mr.action_label,
                mr.moderation_status,
                mr.payment_status,
                mr.overlay_displayed,
                mr.display_sender_name,
                mr.display_message,
                mr.explanation,
                mr.created_at
            FROM moderation_results mr
            JOIN donations_raw dr ON dr.donation_id = mr.donation_id
            LEFT JOIN donations_processed dp ON dp.donation_id = mr.donation_id
            ORDER BY mr.created_at DESC
            LIMIT :limit
            """,
            {"limit": limit},
        )


@app.get("/api/moderation/{donation_id}")
def moderation_detail(donation_id: str) -> dict[str, Any]:
    init_db()
    with db_connection() as conn:
        raw = fetch_one(
            conn,
            "SELECT * FROM donations_raw WHERE donation_id = :donation_id",
            {"donation_id": donation_id},
        )
        processed = fetch_one(
            conn,
            "SELECT * FROM donations_processed WHERE donation_id = :donation_id",
            {"donation_id": donation_id},
        )
        result = fetch_one(
            conn,
            "SELECT * FROM moderation_results WHERE donation_id = :donation_id",
            {"donation_id": donation_id},
        )
    if raw is None:
        raise HTTPException(status_code=404, detail="donation_id tidak ditemukan")
    return {"raw": raw, "processed": processed, "moderation_result": result}


@app.post("/api/settings/filter-mode")
def set_filter_mode(payload: FilterModeRequest) -> dict[str, Any]:
    try:
        return update_filter_mode(payload.streamer_id, payload.filter_mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/settings")
def settings() -> dict[str, Any]:
    return fetch_settings()
