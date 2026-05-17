const app = document.querySelector("#app");
const DEFAULT_STREAMER_ID = "streamer_001";

function apiBaseUrl() {
  return (localStorage.getItem("kondomdonatur_api_url") || "http://localhost:8000").replace(/\/$/, "");
}

function setApiBaseUrl(value) {
  localStorage.setItem("kondomdonatur_api_url", value.replace(/\/$/, ""));
}

function money(value) {
  return `IDR${Number(value || 0).toLocaleString("id-ID")}`;
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

function layout(title, content) {
  app.innerHTML = `
    <header class="topbar">
      <a class="brand" href="/streamer">
        <span class="brand-mark">KD</span>
        <span>KondomDonatur</span>
      </a>
      <nav>
        <a href="/streamer">Panel</a>
        <a href="/donate/${DEFAULT_STREAMER_ID}">Donasi</a>
        <a href="/overlay/${DEFAULT_STREAMER_ID}">Overlay</a>
      </nav>
    </header>
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
    ${content}
  `;
  document.querySelector("#apiUrl").addEventListener("change", (event) => {
    setApiBaseUrl(event.target.value);
    window.location.reload();
  });
}

async function renderStreamer() {
  layout(
    "Panel Streamer",
    `
    <section class="panel control-panel">
      <div>
        <span class="section-label">Proteksi live</span>
        <h2>Mode moderasi</h2>
        <p class="muted">Sensor menjaga donasi tetap masuk dan menyamarkan overlay. Blokir menolak payment intent ketika judol terdeteksi.</p>
      </div>
      <label>Mode proteksi
        <select id="mode">
          <option value="sensor">Mode Sensor</option>
          <option value="block">Mode Blokir</option>
        </select>
      </label>
    </section>
    <section class="panel">
      <div>
        <span class="section-label">Kesiapan sistem</span>
        <h2>Status operasional</h2>
        <div class="status-row">
          <span class="pill">AI Moderation aktif</span>
          <span class="pill">Payment Sandbox aktif</span>
          <span class="pill">Overlay aktif</span>
        </div>
      </div>
    </section>
    <section class="panel link-panel">
      <div class="link-row">
        <label>Link donasi<input id="donateLink" readonly /></label>
        <button class="secondary" id="copyDonate">Copy</button>
      </div>
      <div class="link-row">
        <label>Link overlay OBS<input id="overlayLink" readonly /></label>
        <button class="secondary" id="copyOverlay">Copy</button>
      </div>
    </section>
    <section class="panel">
      <span class="section-label">Ringkasan</span>
      <div class="metrics" id="metrics"></div>
    </section>
    <section class="panel">
      <span class="section-label">Monitoring</span>
      <h2>Donasi terbaru</h2>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Sender/display name</th><th>Amount</th><th>Label</th><th>Action</th><th>Payment</th><th>Overlay</th></tr></thead>
          <tbody id="latestRows"><tr><td colspan="6">Memuat...</td></tr></tbody>
        </table>
      </div>
    </section>
    `,
  );

  const settings = await api("/api/settings");
  const streamerId = settings.streamer_id || DEFAULT_STREAMER_ID;
  const donateLink = `${window.location.origin}/donate/${streamerId}`;
  const overlayLink = `${window.location.origin}/overlay/${streamerId}`;
  document.querySelector("#mode").value = settings.filter_mode || "sensor";
  document.querySelector("#donateLink").value = donateLink;
  document.querySelector("#overlayLink").value = overlayLink;
  document.querySelector("#copyDonate").addEventListener("click", () => copyText(donateLink));
  document.querySelector("#copyOverlay").addEventListener("click", () => copyText(overlayLink));
  document.querySelector("#mode").addEventListener("change", async (event) => {
    await api("/api/settings/filter-mode", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ streamer_id: streamerId, filter_mode: event.target.value }),
    });
  });

  const logs = await api("/api/moderation/logs?limit=20");
  const total = logs.length;
  const safe = logs.filter((row) => row.action_label === "allow").length;
  const masked = logs.filter((row) => row.action_label === "mask").length;
  const blocked = logs.filter((row) => row.action_label === "block").length;
  const paid = logs.filter((row) => row.payment_status === "success").reduce((sum, row) => sum + Number(row.amount || 0), 0);
  document.querySelector("#metrics").innerHTML = [
    ["Total donasi", total],
    ["Total aman", safe],
    ["Total disensor", masked],
    ["Total diblokir", blocked],
    ["Nominal berhasil", money(paid)],
  ].map(([label, value]) => `<div class="metric"><span>${label}</span><strong>${value}</strong></div>`).join("");
  document.querySelector("#latestRows").innerHTML = logs.length
    ? logs.map((row) => `
      <tr>
        <td>${row.display_sender_name || row.sender_name_raw || "-"}</td>
        <td>${money(row.amount)}</td>
        <td><span class="badge">${row.label_multiclass}</span></td>
        <td><span class="badge">${row.action_label}</span></td>
        <td><span class="badge">${row.payment_status}</span></td>
        <td><span class="badge">${Number(row.overlay_displayed) ? "visible" : "hidden"}</span></td>
      </tr>
    `).join("")
    : `<tr><td colspan="6">Belum ada donasi.</td></tr>`;
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
      <pre id="result"></pre>
    </section>
    `,
  );
  document.querySelector("#donateForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(event.currentTarget).entries());
    payload.amount = Number(payload.amount || 0);
    payload.payment_method = "QRIS";
    payload.platform = "KondomDonatur";
    const data = await api("/api/payment-intents", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (data.checkout_url) {
      window.location.href = data.checkout_url;
      return;
    }
    document.querySelector("#result").textContent = data.donor_message || JSON.stringify(data, null, 2);
  });
}

async function renderCheckout(paymentIntentId) {
  layout(
    "Checkout Sandbox",
    `
    <section class="panel checkout-card">
      <span class="section-label">Payment sandbox</span>
      <p>Payment intent: <strong>${paymentIntentId}</strong></p>
      <button class="primary" id="payButton">Bayar Sekarang</button>
      <pre id="result">Klik bayar untuk menyelesaikan payment sandbox.</pre>
    </section>
    `,
  );
  document.querySelector("#payButton").addEventListener("click", async () => {
    const data = await api(`/api/checkout/${paymentIntentId}/pay`, { method: "POST" });
    document.querySelector("#result").textContent = JSON.stringify(data, null, 2);
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
