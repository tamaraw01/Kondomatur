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
    platform: str = Field(default="Kondomatur")
    message_raw: str = Field(default="")


class FilterModeRequest(BaseModel):
    streamer_id: str = DEFAULT_STREAMER_ID
    filter_mode: str = Field(pattern="^(sensor|block)$")


app = FastAPI(
    title="Kondomatur API",
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
        "app": "Kondomatur",
        "status": "ok",
        "message": "API siap menerima simulasi donasi.",
    }


@app.get("/health")
def health() -> dict[str, Any]:
    init_db()
    return {
        "status": "ok",
        "app": "Kondomatur",
        "environment": ENVIRONMENT,
        "model_available": MODEL_PATH.exists(),
    }


def _base_url() -> str:
    return ""


def _page(title: str, body: str, chrome: bool = True) -> HTMLResponse:
    chrome_html = """
        <header class="topbar">
          <a class="brand" href="/streamer">
            <span class="brand-mark">KT</span>
            <span>Kondomatur</span>
          </a>
          <div class="topbar-actions">
            <nav>
              <a href="/streamer">Panel</a>
              <a href="/donate/streamer_001">Donasi</a>
              <a href="/overlay/streamer_001">Overlay</a>
            </nav>
            <button class="theme-toggle" id="themeToggle" type="button">
              <span class="theme-toggle-icon"></span>
              <span id="themeToggleText">Dark</span>
            </button>
          </div>
        </header>
    """ if chrome else ""
    return HTMLResponse(
        f"""
        <!doctype html>
        <html lang="id">
        <head>
          <meta charset="utf-8" />
          <meta name="viewport" content="width=device-width, initial-scale=1" />
          <title>{title}</title>
          <style>
            :root {{
              color-scheme: dark;
              font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
              --bg: #06163f;
              --bg-2: #092a72;
              --surface: #071f56;
              --surface-2: #0a2b70;
              --surface-3: #0e3a8b;
              --line: rgba(194, 223, 255, 0.20);
              --line-strong: rgba(255, 255, 255, 0.32);
              --text: #f8fbff;
              --muted: #a7c1e8;
              --muted-2: #7fa1d4;
              --brand-blue: #0848c8;
              --brand-blue-2: #0d65ff;
              --cyan: #00d9ff;
              --mint: #00e7a6;
              --violet: #7357ff;
              --magenta: #ff2e83;
              --orange: #ff9a2e;
              --lime: #baff3d;
              --shadow: rgba(0, 8, 30, 0.36);
              --glow: rgba(0, 217, 255, 0.24);
            }}
            :root[data-theme="light"] {{
              color-scheme: light;
              --bg: #eef6ff;
              --bg-2: #dceeff;
              --surface: #ffffff;
              --surface-2: #edf5ff;
              --surface-3: #ddecff;
              --line: rgba(6, 22, 63, 0.14);
              --line-strong: rgba(6, 22, 63, 0.24);
              --text: #06163f;
              --muted: #536c98;
              --muted-2: #6c85ad;
              --brand-blue: #0855d8;
              --brand-blue-2: #0074ff;
              --cyan: #00a8e8;
              --mint: #00a878;
              --violet: #6652ff;
              --magenta: #e91e72;
              --orange: #e87510;
              --lime: #5cae00;
              --shadow: rgba(8, 49, 120, 0.15);
              --glow: rgba(0, 116, 255, 0.18);
            }}
            * {{ box-sizing: border-box; }}
            body {{
              min-height: 100vh;
              margin: 0;
              color: var(--text);
              background:
                linear-gradient(90deg, var(--cyan) 0 6px, transparent 6px),
                linear-gradient(135deg, color-mix(in srgb, var(--brand-blue) 74%, #001236), var(--bg) 44%, var(--bg-2));
            }}
            body::before {{
              content: "";
              position: fixed;
              inset: 0;
              z-index: -1;
              background:
                linear-gradient(115deg, transparent 0 18%, color-mix(in srgb, var(--cyan) 20%, transparent) 18% 22%, transparent 22% 100%),
                linear-gradient(64deg, transparent 0 58%, color-mix(in srgb, var(--magenta) 16%, transparent) 58% 62%, transparent 62% 100%),
                linear-gradient(180deg, color-mix(in srgb, var(--bg) 88%, transparent), var(--bg));
            }}
            main {{ width: min(1184px, calc(100% - 32px)); margin: 0 auto; padding: 26px 0 48px; }}
            .topbar {{ width: min(1184px, calc(100% - 32px)); margin: 0 auto; padding: 26px 0 8px; display: flex; justify-content: space-between; align-items: center; gap: 16px; }}
            .brand {{ display: inline-flex; align-items: center; gap: 11px; color: var(--text); font-weight: 950; text-decoration: none; }}
            .brand-mark {{ display: inline-grid; place-items: center; width: 40px; height: 32px; border: 1px solid var(--line-strong); border-radius: 999px; background: linear-gradient(135deg, #ffffff 0%, var(--cyan) 28%, var(--brand-blue-2) 72%, var(--violet) 100%); color: #fff; box-shadow: 0 18px 42px var(--glow); }}
            .topbar-actions {{ display: flex; align-items: center; gap: 10px; }}
            nav {{ display: flex; gap: 4px; padding: 5px; border: 1px solid var(--line); border-radius: 999px; background: color-mix(in srgb, var(--surface) 84%, transparent); box-shadow: 0 16px 38px var(--shadow); }}
            nav a {{ min-width: 78px; color: var(--muted); text-align: center; text-decoration: none; font-size: 13px; font-weight: 850; padding: 8px 12px; border-radius: 999px; }}
            nav a:hover {{ color: var(--text); background: color-mix(in srgb, var(--surface-3) 74%, transparent); }}
            .theme-toggle {{ min-width: 94px; display: inline-flex; justify-content: center; align-items: center; gap: 8px; border: 1px solid var(--line); border-radius: 999px; padding: 10px 12px; background: color-mix(in srgb, var(--surface) 86%, transparent); color: var(--text); box-shadow: 0 16px 38px var(--shadow); }}
            .theme-toggle-icon {{ width: 14px; height: 14px; border: 2px solid var(--cyan); border-radius: 999px; box-shadow: inset 5px 0 0 var(--cyan); }}
            .console-intro {{ display: grid; grid-template-columns: minmax(0, 1fr) minmax(280px, 420px); gap: 20px; align-items: end; margin-bottom: 24px; }}
            .console-intro h1 {{ margin: 0; font-size: 38px; line-height: 1.05; }}
            .panel, .api-card, .glass-panel, .kpi-card, .activity-panel {{
              position: relative;
              overflow: hidden;
              border: 1px solid var(--line);
              border-radius: 8px;
              background: linear-gradient(135deg, color-mix(in srgb, var(--surface) 96%, white 4%), var(--surface));
              box-shadow: 0 24px 70px var(--shadow);
            }}
            .panel::after, .api-card::after, .glass-panel::after, .kpi-card::after, .activity-panel::after {{ content: ""; position: absolute; inset: 0; pointer-events: none; background: linear-gradient(122deg, rgba(255,255,255,.18), transparent 28% 100%); opacity: .22; }}
            .panel, .api-card, .glass-panel {{ padding: 24px; }}
            .panel {{ margin-bottom: 18px; }}
            .compact-api {{ padding: 16px; }}
            .compact-api label {{ margin-bottom: 0; }}
            .eyebrow, .section-label {{ margin: 0 0 8px; color: var(--cyan); font-size: 12px; font-weight: 900; letter-spacing: 0; text-transform: uppercase; }}
            h1, h2, h3, p {{ margin-top: 0; }}
            h1 {{ font-size: 38px; }}
            h2 {{ margin-bottom: 12px; color: var(--text); font-size: 20px; }}
            .muted, .hint {{ color: var(--muted); }}
            label {{ display: grid; gap: 8px; margin-bottom: 12px; color: var(--text); font-size: 13px; font-weight: 850; }}
            input, textarea, select {{ width: 100%; border: 1px solid var(--line); border-radius: 8px; padding: 12px 13px; font: inherit; background: color-mix(in srgb, var(--surface-2) 82%, #000 18%); color: var(--text); }}
            :root[data-theme="light"] input, :root[data-theme="light"] textarea, :root[data-theme="light"] select {{ background: #fff; }}
            input:focus, textarea:focus, select:focus {{ outline: 3px solid color-mix(in srgb, var(--cyan) 24%, transparent); border-color: var(--cyan); }}
            button, .button {{ display: inline-flex; justify-content: center; align-items: center; border: 1px solid var(--line); border-radius: 8px; padding: 12px 15px; background: color-mix(in srgb, var(--surface-2) 86%, #000 14%); color: var(--text); font: inherit; font-weight: 900; text-decoration: none; cursor: pointer; }}
            button.secondary {{ align-self: end; border-color: var(--line); background: color-mix(in srgb, var(--surface-3) 82%, #000 18%); color: var(--text); }}
            .primary-button {{ width: 100%; border-color: var(--cyan); background: linear-gradient(135deg, var(--cyan), var(--brand-blue-2) 48%, var(--violet)); color: #fff; box-shadow: 0 16px 36px var(--glow); }}
            .streamer-dashboard {{ display: grid; gap: 30px; }}
            .kpi-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 24px; }}
            .kpi-card {{ min-height: 112px; display: grid; align-content: space-between; padding: 24px; }}
            .kpi-card span {{ color: var(--muted); font-size: 13px; font-weight: 900; text-transform: uppercase; }}
            .kpi-card strong {{ color: var(--cyan); font-size: 32px; line-height: 1; }}
            .kpi-card small {{ color: var(--muted-2); font-size: 14px; }}
            .accent-hot {{ color: var(--magenta) !important; }}
            .pack-stripe {{ position: absolute; inset: auto 0 0; height: 5px; background: linear-gradient(90deg, var(--cyan), var(--brand-blue-2), var(--lime)); }}
            .pack-stripe.hot {{ background: linear-gradient(90deg, var(--magenta), var(--orange)); }}
            .pack-stripe.violet {{ background: linear-gradient(90deg, var(--violet), var(--cyan)); }}
            .segmented-mode {{ display: grid; grid-template-columns: 1fr 1fr; gap: 6px; padding: 6px; border: 1px solid var(--line); border-radius: 8px; background: color-mix(in srgb, var(--bg) 80%, #000 20%); }}
            .mode-button {{ min-height: 38px; border: 0; border-radius: 6px; background: transparent; color: var(--muted); font-size: 12px; text-transform: uppercase; box-shadow: none; }}
            .mode-button.is-active {{ color: #fff; background: linear-gradient(135deg, var(--cyan), var(--brand-blue-2) 48%, var(--violet)); box-shadow: 0 12px 30px var(--glow), inset 0 1px 0 rgba(255,255,255,.26); }}
            .premium-grid {{ display: grid; grid-template-columns: minmax(0, 1.34fr) minmax(320px, .66fr); gap: 24px; }}
            .link-console, .status-console {{ display: grid; gap: 18px; }}
            .link-stack {{ display: grid; gap: 12px; }}
            .premium-link-row, .link-row {{ display: grid; grid-template-columns: 1fr auto; gap: 10px; align-items: end; }}
            .status-list, .status-row {{ display: flex; flex-wrap: wrap; gap: 9px; }}
            .status-chip, .pill, .live-pill, .badge {{ display: inline-flex; align-items: center; width: fit-content; border-radius: 999px; font-size: 12px; font-weight: 900; }}
            .status-chip, .pill {{ gap: 8px; padding: 9px 11px; border: 1px solid color-mix(in srgb, var(--mint) 28%, var(--line)); background: color-mix(in srgb, var(--mint) 12%, var(--surface)); color: var(--text); }}
            .status-chip i, .live-pill i {{ width: 8px; height: 8px; border-radius: 999px; background: var(--mint); box-shadow: 0 0 16px color-mix(in srgb, var(--mint) 72%, transparent); }}
            .mini-metrics, .metrics {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }}
            .mini-metrics div, .metric {{ min-height: 78px; display: grid; align-content: space-between; border: 1px solid var(--line); border-radius: 8px; padding: 14px; background: color-mix(in srgb, var(--surface-2) 86%, #000 14%); }}
            .mini-metrics span, .metric span {{ color: var(--muted); font-size: 12px; font-weight: 850; }}
            .mini-metrics strong, .metric strong {{ color: var(--text); font-size: 22px; }}
            .activity-panel {{ position: relative; overflow: hidden; }}
            .activity-header {{ min-height: 78px; display: flex; justify-content: space-between; align-items: center; gap: 18px; padding: 24px 32px; border-bottom: 1px solid var(--line); }}
            .activity-title {{ display: inline-flex; align-items: center; gap: 14px; }}
            .activity-title h2 {{ margin: 0; font-size: 20px; text-transform: uppercase; }}
            .chevron-mark {{ color: var(--cyan); font-size: 36px; line-height: 1; }}
            .live-pill {{ gap: 8px; padding: 8px 14px; border: 1px solid var(--line); background: color-mix(in srgb, var(--bg) 86%, #000 14%); color: var(--muted); text-transform: uppercase; }}
            .activity-body {{ min-height: 236px; padding: 0; }}
            .table-wrap {{ overflow-x: auto; }}
            table {{ width: 100%; min-width: 760px; border-collapse: collapse; }}
            th, td {{ border-bottom: 1px solid var(--line); padding: 15px 18px; text-align: left; font-size: 14px; }}
            th {{ background: color-mix(in srgb, var(--surface-2) 92%, #000 8%); color: var(--muted); font-size: 11px; text-transform: uppercase; }}
            td {{ color: var(--text); }}
            .badge {{ padding: 6px 9px; border: 1px solid color-mix(in srgb, var(--cyan) 24%, var(--line)); background: color-mix(in srgb, var(--cyan) 10%, var(--surface)); color: var(--text); }}
            .empty-cell {{ height: 236px; padding: 0; }}
            .empty-state {{ min-height: 236px; display: grid; place-items: center; align-content: center; gap: 18px; color: var(--muted); }}
            .empty-icon {{ display: inline-grid; place-items: center; width: 64px; height: 64px; border-radius: 999px; background: color-mix(in srgb, var(--surface-3) 70%, #000 30%); color: var(--cyan); font-size: 23px; font-weight: 900; }}
            .version-mark {{ position: absolute; right: 16px; bottom: 14px; color: var(--muted-2); font-size: 11px; }}
            pre {{ min-height: 120px; margin: 16px 0 0; overflow: auto; padding: 14px; border-radius: 8px; background: color-mix(in srgb, var(--bg) 88%, #000 12%); color: var(--text); white-space: pre-wrap; }}
            .checkout-card, .form-card {{ max-width: 760px; margin-inline: auto; }}
            .checkout-summary {{ display: grid; gap: 14px; margin: 18px 0; padding: 18px; border: 1px solid var(--line); border-radius: 8px; background: color-mix(in srgb, var(--surface-2) 86%, #000 14%); }}
            .checkout-summary strong {{ display: block; margin-top: 4px; color: var(--text); font-size: 22px; }}
            .summary-label {{ color: var(--muted); font-size: 12px; font-weight: 900; text-transform: uppercase; }}
            .summary-message {{ padding-top: 12px; border-top: 1px solid var(--line); }}
            .summary-message p {{ margin: 6px 0 0; color: var(--muted); }}
            .public-result {{ margin-top: 16px; }}
            .public-notice {{ display: grid; gap: 4px; padding: 14px 16px; border: 1px solid var(--line); border-radius: 8px; background: color-mix(in srgb, var(--surface-2) 86%, #000 14%); color: var(--muted); }}
            .public-notice strong {{ color: var(--text); }}
            .public-notice.success {{ border-color: color-mix(in srgb, var(--mint) 44%, var(--line)); background: color-mix(in srgb, var(--mint) 12%, var(--surface)); }}
            .public-notice.danger {{ border-color: color-mix(in srgb, var(--magenta) 48%, var(--line)); background: color-mix(in srgb, var(--magenta) 12%, var(--surface)); }}
            .overlay-card {{ width: min(760px, calc(100% - 32px)); margin: 48px auto; display: grid; gap: 8px; border: 1px solid var(--line); border-radius: 8px; padding: 32px; background: var(--surface); box-shadow: 0 24px 70px var(--shadow); }}
            .amount {{ color: var(--cyan); font-size: 32px; font-weight: 950; }}
            .message {{ color: var(--muted); font-size: 22px; }}
            @media (max-width: 980px) {{ .console-intro, .kpi-grid, .premium-grid, .mini-metrics, .metrics {{ grid-template-columns: 1fr; }} }}
            @media (max-width: 720px) {{ main, .topbar {{ width: min(100% - 20px, 1184px); }} .topbar, .topbar-actions, nav, .premium-link-row, .link-row, .activity-header {{ display: grid; grid-template-columns: 1fr; }} nav {{ border-radius: 8px; }} .theme-toggle {{ width: 100%; }} .activity-header {{ align-items: start; padding: 20px; }} }}
          </style>
          <script>
            const storedTheme = localStorage.getItem("kondomatur_theme") || "dark";
            document.documentElement.dataset.theme = storedTheme;
          </script>
        </head>
        <body>
          {chrome_html}
          {body}
          <script>
            const themeToggle = document.querySelector("#themeToggle");
            const themeText = document.querySelector("#themeToggleText");
            function syncThemeLabel() {{
              if (themeText) themeText.textContent = document.documentElement.dataset.theme === "dark" ? "Dark" : "Light";
            }}
            syncThemeLabel();
            if (themeToggle) {{
              themeToggle.addEventListener("click", () => {{
                const nextTheme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
                document.documentElement.dataset.theme = nextTheme;
                localStorage.setItem("kondomatur_theme", nextTheme);
                syncThemeLabel();
              }});
            }}
          </script>
        </body>
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
          <section class="console-intro">
            <div>
              <p class="eyebrow">Streamer control room</p>
              <h1>Panel Streamer</h1>
              <p class="muted">AI-powered donation payment gateway dengan moderasi otomatis, checkout sandbox, dan overlay OBS.</p>
            </div>
            <div class="api-card compact-api">
              <span class="section-label">Backend</span>
              <h2>Connected</h2>
              <p class="muted">FastAPI berjalan di origin ini.</p>
            </div>
          </section>

          <section class="streamer-dashboard">
            <div class="kpi-grid">
              <article class="kpi-card">
                <div class="pack-stripe"></div>
                <span>Total pendapatan</span>
                <strong id="totalRevenue">Rp 0</strong>
              </article>
              <article class="kpi-card">
                <div class="pack-stripe hot"></div>
                <span>Donasi terfilter</span>
                <strong id="filteredCount" class="accent-hot">0</strong>
                <small>Event</small>
              </article>
              <article class="kpi-card">
                <div class="pack-stripe violet"></div>
                <span>Mode proteksi</span>
                <div class="segmented-mode" role="group" aria-label="Mode proteksi">
                  <button class="mode-button {"is-active" if settings.get("filter_mode") == "sensor" else ""}" data-mode="sensor" type="button">Sensor</button>
                  <button class="mode-button {"is-active" if settings.get("filter_mode") == "block" else ""}" data-mode="block" type="button">Blokir</button>
                </div>
              </article>
            </div>

            <div class="premium-grid">
              <section class="glass-panel link-console">
                <div>
                  <span class="section-label">Distribution</span>
                  <h2>Link publik streamer</h2>
                </div>
                <div class="link-stack">
                  <div class="premium-link-row">
                    <label>Link donasi<input id="donateLink" readonly value="{donate_link}" /></label>
                    <button class="secondary" id="copyDonate" type="button">Copy</button>
                  </div>
                  <div class="premium-link-row">
                    <label>Link overlay OBS<input id="overlayLink" readonly value="{overlay_link}" /></label>
                    <button class="secondary" id="copyOverlay" type="button">Copy</button>
                  </div>
                </div>
              </section>

              <section class="glass-panel status-console">
                <span class="section-label">System status</span>
                <h2>Payment gateway aktif</h2>
                <div class="status-list">
                  <span class="status-chip"><i></i>AI Moderation aktif</span>
                  <span class="status-chip"><i></i>Payment Sandbox aktif</span>
                  <span class="status-chip"><i></i>Overlay aktif</span>
                </div>
                <div class="mini-metrics">
                  <div><span>Total</span><strong id="metricTotal">0</strong></div>
                  <div><span>Aman</span><strong id="metricSafe">0</strong></div>
                  <div><span>Sensor</span><strong id="metricMasked">0</strong></div>
                  <div><span>Blokir</span><strong id="metricBlocked">0</strong></div>
                </div>
              </section>
            </div>

            <section class="activity-panel">
              <header class="activity-header">
                <div class="activity-title">
                  <span class="chevron-mark">›</span>
                  <h2>Log aktivitas donasi</h2>
                </div>
                <span class="live-pill"><i></i>Live monitoring</span>
              </header>
              <div class="activity-body">
                <div class="table-wrap">
                  <table>
                    <thead><tr><th>Sender/display name</th><th>Amount</th><th>Label</th><th>Action</th><th>Payment</th><th>Overlay</th></tr></thead>
                    <tbody id="latestRows">
                      <tr>
                        <td class="empty-cell" colspan="6">
                          <div class="empty-state">
                            <span class="empty-icon">i</span>
                            <p>Memuat donasi terbaru...</p>
                          </div>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
              <span class="version-mark">kt-v1.0.0-alpha</span>
            </section>
          </section>
        </main>
        <script>
          const streamerId = {streamer_id!r};
          function escapeHtml(value) {{
            return String(value ?? "")
              .replaceAll("&", "&amp;")
              .replaceAll("<", "&lt;")
              .replaceAll(">", "&gt;")
              .replaceAll('"', "&quot;")
              .replaceAll("'", "&#039;");
          }}
          document.querySelectorAll('.mode-button').forEach((button) => {{
            button.addEventListener('click', async () => {{
              const mode = button.dataset.mode;
              await fetch('/api/settings/filter-mode', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ streamer_id: streamerId, filter_mode: mode }})
              }});
              document.querySelectorAll('.mode-button').forEach((item) => item.classList.toggle('is-active', item.dataset.mode === mode));
            }});
          }});
          function absolutePath(path) {{ return new URL(path, window.location.origin).toString(); }}
          document.querySelector('#donateLink').value = absolutePath('{donate_link}');
          document.querySelector('#overlayLink').value = absolutePath('{overlay_link}');
          function attachCopy(buttonId, inputId) {{
            const button = document.querySelector('#' + buttonId);
            button.addEventListener('click', async () => {{
              await navigator.clipboard.writeText(document.querySelector('#' + inputId).value);
              button.textContent = 'Copied';
              setTimeout(() => button.textContent = 'Copy', 1200);
            }});
          }}
          attachCopy('copyDonate', 'donateLink');
          attachCopy('copyOverlay', 'overlayLink');
          function fmtAmount(value) {{ return 'IDR' + Number(value || 0).toLocaleString('id-ID'); }}
          function fmtRupiah(value) {{ return fmtAmount(value).replace('IDR', 'Rp '); }}
          async function loadLatest() {{
            const res = await fetch('/api/moderation/logs?limit=20');
            const rows = await res.json();
            const total = rows.length;
            const safe = rows.filter(r => r.action_label === 'allow').length;
            const masked = rows.filter(r => r.action_label === 'mask').length;
            const blocked = rows.filter(r => r.action_label === 'block').length;
            const filtered = masked + blocked;
            const paid = rows.filter(r => r.payment_status === 'success').reduce((sum, r) => sum + Number(r.amount || 0), 0);
            document.querySelector('#totalRevenue').textContent = fmtRupiah(paid);
            document.querySelector('#filteredCount').textContent = filtered;
            document.querySelector('#metricTotal').textContent = total;
            document.querySelector('#metricSafe').textContent = safe;
            document.querySelector('#metricMasked').textContent = masked;
            document.querySelector('#metricBlocked').textContent = blocked;
            document.querySelector('#latestRows').innerHTML = rows.length ? rows.map(r => `
              <tr>
                <td>${{escapeHtml(r.display_sender_name || r.sender_name_raw || '-')}}</td>
                <td>${{fmtAmount(r.amount)}}</td>
                <td><span class="badge">${{escapeHtml(r.label_multiclass)}}</span></td>
                <td><span class="badge">${{escapeHtml(r.action_label)}}</span></td>
                <td><span class="badge">${{escapeHtml(r.payment_status)}}</span></td>
                <td><span class="badge">${{Number(r.overlay_displayed) ? 'visible' : 'hidden'}}</span></td>
              </tr>`).join('') : `
                <tr>
                  <td class="empty-cell" colspan="6">
                    <div class="empty-state">
                      <span class="empty-icon">i</span>
                      <p>Belum ada donasi yang masuk.</p>
                    </div>
                  </td>
                </tr>`;
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
              <button class="primary-button" type="submit">Lanjut ke Checkout</button>
            </form>
            <div id="result" class="public-result" aria-live="polite"></div>
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
            payload.platform = 'Kondomatur';
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
            result.innerHTML = '<div class="public-notice danger"><strong>Donasi gagal diproses</strong><span>' + (data.donor_message || 'Pesan terindikasi melanggar kebijakan sehingga pembayaran tidak dilanjutkan.') + '</span></div>';
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
            <button class="primary-button" id="payButton" {button_disabled}>Bayar Sandbox</button>
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
        chrome=False,
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
