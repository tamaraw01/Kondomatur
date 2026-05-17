const app = document.querySelector("#app");
const DEFAULT_STREAMER_ID = "streamer_001";
const THEME_KEY = "kondomatur_theme";

function getTheme() {
  return localStorage.getItem(THEME_KEY) || "dark";
}

function applyTheme(theme = getTheme()) {
  document.documentElement.dataset.theme = theme;
}

function setTheme(theme) {
  localStorage.setItem(THEME_KEY, theme);
  applyTheme(theme);
}

applyTheme();

function apiBaseUrl() {
  return (localStorage.getItem("kondomatur_api_url") || "http://localhost:8000").replace(/\/$/, "");
}

function setApiBaseUrl(value) {
  localStorage.setItem("kondomatur_api_url", value.replace(/\/$/, ""));
}

function money(value) {
  return `IDR${Number(value || 0).toLocaleString("id-ID")}`;
}

function escapeHTML(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function publicNotice(kind, title, message) {
  return `
    <div class="public-notice ${kind}">
      <strong>${escapeHTML(title)}</strong>
      <span>${escapeHTML(message)}</span>
    </div>
  `;
}

async function api(path, options = {}) {
  const response = await fetch(`${apiBaseUrl()}${path}`, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Request gagal");
  return data;
}

function routeParts() {
  return window.location.pathname.split("/").filter(Boolean);
}

function copyText(value) {
  navigator.clipboard.writeText(value);
}

function layout(title, content, variant = "default") {
  const intro = variant === "console"
    ? `
      <section class="console-intro">
        <div>
          <p class="eyebrow">Streamer control room</p>
          <h1>${title}</h1>
        </div>
        <div class="api-card compact-api">
          <label>Backend API URL
            <input id="apiUrl" value="${apiBaseUrl()}" />
          </label>
        </div>
      </section>
    `
    : `
      <section class="hero">
        <div>
          <p class="eyebrow">Payment gateway sandbox</p>
          <h1>${title}</h1>
          <p class="copy">AI moderation, payment sandbox, dan overlay OBS dalam satu alur sederhana untuk demo streamer.</p>
        </div>
        <div class="api-card">
          <label>Backend API URL
            <input id="apiUrl" value="${apiBaseUrl()}" />
          </label>
          <span class="hint">Gunakan URL Render/Railway saat demo online.</span>
        </div>
      </section>
    `;
  app.innerHTML = `
    <header class="topbar">
      <a class="brand" href="/streamer">
        <span class="brand-mark">KT</span>
        <span>Kondomatur</span>
      </a>
      <div class="topbar-actions">
        <nav>
          <a href="/streamer">Panel</a>
          <a href="/donate/${DEFAULT_STREAMER_ID}">Donasi</a>
          <a href="/overlay/${DEFAULT_STREAMER_ID}">Overlay</a>
        </nav>
        <button class="theme-toggle" id="themeToggle" type="button" aria-label="Ganti tema">
          <span class="theme-toggle-icon"></span>
          <span id="themeToggleText">${getTheme() === "dark" ? "Dark" : "Light"}</span>
        </button>
      </div>
    </header>
    ${intro}
    ${content}
  `;
  document.querySelector("#apiUrl").addEventListener("change", (event) => {
    setApiBaseUrl(event.target.value);
    window.location.reload();
  });
  document.querySelector("#themeToggle").addEventListener("click", () => {
    const nextTheme = getTheme() === "dark" ? "light" : "dark";
    setTheme(nextTheme);
    document.querySelector("#themeToggleText").textContent = nextTheme === "dark" ? "Dark" : "Light";
  });
}

async function renderStreamer() {
  const settings = await api("/api/settings");
  const streamerId = settings.streamer_id || DEFAULT_STREAMER_ID;
  const logs = await api("/api/moderation/logs?limit=20");
  const currentMode = settings.filter_mode || "sensor";
  const donateLink = `${window.location.origin}/donate/${streamerId}`;
  const overlayLink = `${window.location.origin}/overlay/${streamerId}`;
  const total = logs.length;
  const safe = logs.filter((row) => row.action_label === "allow").length;
  const masked = logs.filter((row) => row.action_label === "mask").length;
  const blocked = logs.filter((row) => row.action_label === "block").length;
  const filtered = masked + blocked;
  const paid = logs.filter((row) => row.payment_status === "success").reduce((sum, row) => sum + Number(row.amount || 0), 0);

  layout(
    "Panel Streamer",
    `
    <section class="streamer-dashboard">
      <div class="kpi-grid">
        <article class="kpi-card kpi-revenue">
          <div class="pack-stripe"></div>
          <span>Total pendapatan</span>
          <strong>${money(paid).replace("IDR", "Rp ")}</strong>
        </article>
        <article class="kpi-card">
          <div class="pack-stripe hot"></div>
          <span>Donasi terfilter</span>
          <strong class="accent-hot">${filtered}</strong>
          <small>Event</small>
        </article>
        <article class="kpi-card mode-card">
          <div class="pack-stripe violet"></div>
          <span>Mode proteksi</span>
          <div class="segmented-mode" role="group" aria-label="Mode proteksi">
            <button class="mode-button ${currentMode === "sensor" ? "is-active" : ""}" data-mode="sensor" type="button">
              <span class="mode-dot"></span>
              Sensor
            </button>
            <button class="mode-button ${currentMode === "block" ? "is-active" : ""}" data-mode="block" type="button">
              <span class="mode-dot"></span>
              Blokir
            </button>
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
              <label>Link donasi<input id="donateLink" readonly value="${donateLink}" /></label>
              <button class="secondary" id="copyDonate">Copy</button>
            </div>
            <div class="premium-link-row">
              <label>Link overlay OBS<input id="overlayLink" readonly value="${overlayLink}" /></label>
              <button class="secondary" id="copyOverlay">Copy</button>
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
            <div><span>Total</span><strong>${total}</strong></div>
            <div><span>Aman</span><strong>${safe}</strong></div>
            <div><span>Sensor</span><strong>${masked}</strong></div>
            <div><span>Blokir</span><strong>${blocked}</strong></div>
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
                ${logs.length ? logs.map((row) => `
                  <tr>
                    <td>${escapeHTML(row.display_sender_name || row.sender_name_raw || "-")}</td>
                    <td>${money(row.amount)}</td>
                    <td><span class="badge">${escapeHTML(row.label_multiclass)}</span></td>
                    <td><span class="badge">${escapeHTML(row.action_label)}</span></td>
                    <td><span class="badge">${escapeHTML(row.payment_status)}</span></td>
                    <td><span class="badge">${Number(row.overlay_displayed) ? "visible" : "hidden"}</span></td>
                  </tr>
                `).join("") : `
                  <tr>
                    <td class="empty-cell" colspan="6">
                      <div class="empty-state">
                        <span class="empty-icon">i</span>
                        <p>Belum ada donasi yang masuk.</p>
                      </div>
                    </td>
                  </tr>
                `}
              </tbody>
            </table>
          </div>
        </div>
        <span class="version-mark">kt-v1.0.0-alpha</span>
      </section>
    </section>
    `,
    "console",
  );
  document.querySelector("#copyDonate").addEventListener("click", (event) => {
    copyText(donateLink);
    event.currentTarget.textContent = "Copied";
    setTimeout(() => { event.currentTarget.textContent = "Copy"; }, 1200);
  });
  document.querySelector("#copyOverlay").addEventListener("click", (event) => {
    copyText(overlayLink);
    event.currentTarget.textContent = "Copied";
    setTimeout(() => { event.currentTarget.textContent = "Copy"; }, 1200);
  });
  document.querySelectorAll(".mode-button").forEach((button) => {
    button.addEventListener("click", async () => {
      const mode = button.dataset.mode;
      await api("/api/settings/filter-mode", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ streamer_id: streamerId, filter_mode: mode }),
      });
      document.querySelectorAll(".mode-button").forEach((item) => item.classList.toggle("is-active", item.dataset.mode === mode));
    });
  });
}

function renderDonate(streamerId = DEFAULT_STREAMER_ID) {
  layout(
    "Kirim Donasi",
    `
    <section class="panel form-card">
      <span class="section-label">Donasi penonton</span>
      <form id="donateForm">
        <input type="hidden" name="streamer_id" value="${streamerId}" />
        <label>Nama pengirim<input name="sender_name_raw" value="Budi" required /></label>
        <label>Email<input name="sender_email_raw" value="budi@example.com" /></label>
        <label>Nominal<input name="amount" type="number" value="25000" min="0" /></label>
        <label>Pesan<textarea name="message_raw" rows="4">Semangat bang, lanjut mainnya!</textarea></label>
        <button class="primary" type="submit">Lanjut ke Checkout</button>
      </form>
      <div id="result" class="public-result" aria-live="polite"></div>
    </section>
    `,
  );
  document.querySelector("#donateForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(event.currentTarget).entries());
    payload.amount = Number(payload.amount || 0);
    payload.payment_method = "QRIS";
    payload.platform = "Kondomatur";
    const data = await api("/api/payment-intents", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (data.checkout_url) {
      window.location.href = data.checkout_url;
      return;
    }
    document.querySelector("#result").innerHTML = publicNotice(
      "danger",
      "Donasi gagal diproses",
      data.donor_message || "Pesan terindikasi melanggar kebijakan sehingga pembayaran tidak dilanjutkan.",
    );
  });
}

async function renderCheckout(paymentIntentId) {
  layout(
    "Checkout Sandbox",
    `
    <section class="panel checkout-card">
      <span class="section-label">Payment sandbox</span>
      <h2>Ringkasan Donasi</h2>
      <div id="checkoutSummary" class="checkout-summary">
        <span class="skeleton-line"></span>
        <span class="skeleton-line short"></span>
      </div>
      <button class="primary" id="payButton">Bayar Sandbox</button>
      <div id="result" class="public-result" aria-live="polite">
        ${publicNotice("info", "Siap diproses", "Klik tombol bayar untuk menyelesaikan checkout sandbox.")}
      </div>
    </section>
    `,
  );
  const payButton = document.querySelector("#payButton");
  const resultEl = document.querySelector("#result");
  const summaryEl = document.querySelector("#checkoutSummary");

  try {
    const detail = await api(`/api/checkout/${paymentIntentId}`);
    summaryEl.innerHTML = `
      <div>
        <span class="summary-label">Nominal</span>
        <strong>${money(detail.amount)}</strong>
      </div>
      <div>
        <span class="summary-label">Pengirim</span>
        <strong>${escapeHTML(detail.sender_name || "-")}</strong>
      </div>
      <div class="summary-message">
        <span class="summary-label">Pesan</span>
        <p>${escapeHTML(detail.message || "-")}</p>
      </div>
    `;
    if (detail.payment_status === "success") {
      payButton.disabled = true;
      resultEl.innerHTML = publicNotice(
        "success",
        "Pembayaran sudah berhasil",
        "Terima kasih, donasimu sudah diproses untuk streamer.",
      );
    }
    if (detail.payment_status === "rejected") {
      payButton.disabled = true;
      resultEl.innerHTML = publicNotice(
        "danger",
        "Donasi gagal diproses",
        "Pesan terindikasi melanggar kebijakan sehingga pembayaran tidak dilanjutkan.",
      );
    }
  } catch (error) {
    payButton.disabled = true;
    resultEl.innerHTML = publicNotice("danger", "Checkout tidak ditemukan", error.message);
  }

  payButton.addEventListener("click", async () => {
    payButton.disabled = true;
    payButton.textContent = "Memproses...";
    resultEl.innerHTML = publicNotice("info", "Memproses pembayaran", "Mohon tunggu sebentar.");
    try {
      const data = await api(`/api/checkout/${paymentIntentId}/pay`, { method: "POST" });
      if (data.payment_status === "success") {
        resultEl.innerHTML = publicNotice(
          "success",
          "Pembayaran berhasil",
          "Terima kasih, donasimu sudah diproses untuk streamer.",
        );
      } else {
        resultEl.innerHTML = publicNotice(
          "danger",
          "Donasi gagal diproses",
          data.message || "Pesan terindikasi melanggar kebijakan sehingga pembayaran tidak dilanjutkan.",
        );
      }
    } catch (error) {
      payButton.disabled = false;
      resultEl.innerHTML = publicNotice("danger", "Pembayaran belum berhasil", error.message);
    } finally {
      payButton.textContent = "Bayar Sandbox";
    }
  });
}

async function renderOverlay(streamerId = DEFAULT_STREAMER_ID) {
  app.innerHTML = `
    <section class="overlay-card" id="overlayCard">
      <div class="amount">Menunggu donasi...</div>
      <div class="message">Streamer: ${streamerId}</div>
    </section>
  `;
  async function refresh() {
    const rows = await api(`/api/overlay/${streamerId}`);
    const latest = rows[0];
    if (!latest) return;
    document.querySelector("#overlayCard").innerHTML = `
      <div class="amount">${money(latest.amount)} dari ${latest.display_sender_name}</div>
      <div class="message">${latest.display_message}</div>
    `;
  }
  refresh();
  setInterval(refresh, 3000);
}

async function main() {
  try {
    const [page, id] = routeParts();
    if (!page || page === "streamer") return renderStreamer();
    if (page === "donate") return renderDonate(id || DEFAULT_STREAMER_ID);
    if (page === "checkout") return renderCheckout(id);
    if (page === "overlay") return renderOverlay(id || DEFAULT_STREAMER_ID);
    return renderStreamer();
  } catch (error) {
    app.innerHTML = `<section class="panel"><h1>Terjadi error</h1><pre>${error.message}</pre></section>`;
  }
}

main();
