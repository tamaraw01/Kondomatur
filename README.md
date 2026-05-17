# Kondomatur

Kondomatur adalah prototype AI-powered donation payment gateway untuk streamer. Sistem ini memoderasi nama pengirim dan pesan donasi sebelum payment sandbox dilanjutkan ke checkout dan overlay.

Sistem ini tidak melakukan integrasi pembayaran nyata dan tidak memakai data pribadi nyata. Semua data contoh bersifat sintetis untuk deteksi dan moderasi konten berbahaya.

## Fitur Utama

- Deteksi pesan donasi berdasarkan `sender_name_raw` dan `message_raw`.
- Normalisasi fancy Unicode, huruf hias seperti `🅿🅾🅻🅰`, ASCII folding, leetspeak, token yang dipisah spasi/simbol, URL tersamarkan, dan pola provider seperti `net888`.
- Emoji biasa seperti `😺🐳` tetap boleh tampil; yang dinaikkan risikonya adalah huruf/angka non-standar yang dipakai untuk menyamarkan teks.
- Klasifikasi: `benign`, `spam_non_judol`, `suspicious_judol`, `explicit_judol`.
- Action: `allow`, `review`, `mask`, `block`.
- Mode Sensor: jika pesan judol, payment sandbox tetap dibuat; setelah paid, overlay tampil dengan nama `someone` dan pesan sensor.
- Mode Blokir: jika pesan judol, payment intent tidak dibuat, `payment_status = rejected`, dan overlay tetap hidden.
- Baseline ML memakai TF-IDF char/word n-gram dan Logistic Regression.
- Fallback rule detector jika model belum dilatih.
- FastAPI backend, SQLite lokal, PostgreSQL/Supabase production, Streamlit lokal, dan frontend statis Vercel.
- UI demo memakai tema premium dengan mode `Dark`/`Light`, palet biru-cyan, dan aksen warna varian untuk memberi rasa platform publik yang matang.

## Arsitektur Singkat

- `api/main.py`: endpoint FastAPI dan penyimpanan hasil moderasi.
- `src/preprocessing.py`: normalisasi NFKC, ASCII fold, leetspeak, rekonstruksi token, skor obfuscation.
- `src/rule_detector.py`: fitur rule-based dan label awal.
- `src/model.py`: load/predict model scikit-learn dengan fallback rule.
- `src/risk_scoring.py`: skor risiko 0-100 dan level risiko.
- `src/decision_engine.py`: keputusan mode sensor atau blokir.
- `app/`: halaman Streamlit lokal untuk donor, Panel Streamer, dan overlay.
- `web/`: frontend statis Vercel dengan halaman `/streamer`, `/donate/{streamer_id}`, `/checkout/{payment_intent_id}`, dan `/overlay/{streamer_id}`.
- `scripts/`: migration, seed database, init lokal, dan training model.

## Install

```bash
cd Kondomatur
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows:

```bash
cd Kondomatur
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Inisialisasi Database

```bash
python scripts/init_db.py
```

Database lokal dibuat sebagai:

```text
donation_shield.db
```

Default streamer setting:

- `streamer_id`: `streamer_001`
- `streamer_name`: `Demo Streamer`
- `filter_mode`: `sensor`
- threshold review/mask/block: `35`, `60`, `80`

## Train Model

```bash
python scripts/train_model.py
```

Script ini akan membuat `data/sample/donation_sample.csv` jika belum ada, melatih baseline model, menampilkan `classification_report`, lalu menyimpan:

```text
models/judol_detector.pkl
```

Dataset sintetis dibuat seimbang untuk 4 kelas dengan 10.000 baris unik. Variasinya mencakup fancy Unicode, huruf hias, confusable lintas script, leetspeak, zero-width character, domain tersamarkan, angka hias, pemisah simbol, emoji wrapper yang aman, spam non-judol dengan URL legal/sintetis, dan pola provider placeholder seperti `net888`/`vip777`.

## Jalankan API

```bash
uvicorn api.main:app --reload --port 8000
```

API Docs:

```text
http://localhost:8000/docs
```

## Jalankan Donor Form Streamlit

```bash
streamlit run app/donor_form.py --server.port 8501
```

Buka:

```text
http://localhost:8501
```

Halaman ini tetap dipertahankan sebagai alat quick test lokal dan sudah memakai flow payment intent + checkout sandbox yang sama dengan `/donate/{streamer_id}`.

## Jalankan Panel Streamer

```bash
streamlit run app/streamer_dashboard.py --server.port 8502
```

Buka:

```text
http://localhost:8502
```

Panel Streamer hanya berisi:

- pilihan mode proteksi `sensor` atau `block`
- link donasi `/donate/{streamer_id}`
- link overlay OBS `/overlay/{streamer_id}`
- tombol copy link
- status sederhana: AI Moderation, Payment Sandbox, Overlay
- donasi terbaru dalam tabel sederhana
- metrik ringan: total donasi, aman, disensor, diblokir, nominal berhasil

## Jalankan Overlay

```bash
streamlit run app/overlay.py --server.port 8503
```

Buka:

```text
http://localhost:8503
```

## Frontend Web Statis untuk Vercel

Selain Streamlit lokal, tersedia frontend demo statis di folder `web/`. Frontend ini bisa dideploy ke Vercel dengan Root Directory `web`.

Halaman frontend minimal:

- `/streamer`
- `/donate/{streamer_id}`
- `/checkout/{payment_intent_id}`
- `/overlay/{streamer_id}`

Di `/streamer`, isi field `Backend API URL` dengan URL backend Render/Railway.

Detail deployment ada di [DEPLOYMENT.md](DEPLOYMENT.md).

## Endpoint API

- `GET /`: status aplikasi.
- `GET /health`: health check deployment.
- `GET /streamer`: Panel Streamer minimal.
- `GET /donate/{streamer_id}`: halaman donasi penonton.
- `GET /checkout/{payment_intent_id}`: checkout payment sandbox.
- `GET /overlay/{streamer_id}`: overlay OBS.
- `POST /api/payment-intents`: buat payment intent sandbox setelah moderasi AI.
- `POST /api/checkout/{payment_intent_id}/pay`: tandai payment sandbox sebagai paid dan tampilkan overlay jika eligible.
- `POST /api/donations`: kirim donasi, proses moderasi, simpan raw/processed/result.
- `GET /api/overlay`: donasi terbaru yang boleh tampil di overlay.
- `GET /api/moderation/logs`: log moderasi terbaru.
- `GET /api/moderation/{donation_id}`: detail raw, processed, dan result.
- `POST /api/settings/filter-mode`: update mode `sensor` atau `block`.
- `GET /api/settings`: ambil streamer settings.

Contoh request:

```json
{
  "sender_name_raw": "Budi",
  "sender_email_raw": "budi@gmail.com",
  "amount": 25000,
  "payment_method": "QRIS",
  "platform": "Saweria",
  "message_raw": "Semangat bang",
  "streamer_filter_mode": "sensor"
}
```

## Skenario Demo

1. Donasi normal

   - Nama: `Budi`
   - Pesan: `Semangat bang, lanjut mainnya!`
   - Mode: `sensor` atau `block`
   - Expected: payment intent dibuat, checkout sandbox bisa dibayar, overlay tampil normal setelah paid.

2. Judol Mode Sensor

   - Nama: `kantorbola88`
   - Pesan: `RTP tinggi malam ini, gas sekarang!`
   - Mode: `sensor`
   - Expected: payment intent tetap dibuat, sebelum paid overlay hidden, setelah paid overlay muncul dengan `someone` dan pesan sensor.

3. Judol Mode Blokir

   - Nama: `kantorbola88`
   - Pesan: `RTP tinggi malam ini, gas sekarang!`
   - Mode: `block`
   - Expected: payment intent tidak dibuat, `payment_status = rejected`, overlay tidak muncul.

4. Fancy Unicode

   - Nama: `๑۞๑ ϰꍏ♫☂⊙☈♭ꍏ↳↳88 ๑۞๑`
   - Pesan: `ｓｌｏｔ ｇａｃｏｒ rtp 98%`
   - Expected: terdeteksi suspicious/explicit setelah normalisasi; pada Mode Sensor overlay tampil tersensor setelah paid.

5. Huruf hias provider

   - Nama: `viewer`
   - Pesan: `🅿🅾🅻🅰 🆃🅴🆁🅱🅰🅸🅺 🅷🅰🅽🆈🅰 🅳🅸 🅽🅴🆃888`
   - Expected: dinormalisasi menjadi `pola terbaik hanya di net888` dan terdeteksi `explicit_judol`.

6. Emoji + huruf hias campuran

   - Nama: `viewer`
   - Pesan: `😺🐳 ᵖㄖｌⓐ tＥŘ๒ΔƗк ĦⒶ几𝐘𝔸 ᗪⒾ ηᵉ𝓽➇８❽ 🐻🐼`
   - Expected: emoji tidak menjadi masalah, tetapi huruf/angka hias dinormalisasi menjadi `pola terbaik hanya di net888` dan terdeteksi `explicit_judol`.

## Testing

```bash
pytest
```

Test minimal mencakup preprocessing, rule detector, dan decision engine untuk mode Sensor/Blokir.

## Urutan Demo Lokal

Jalankan dari root project `Kondomatur`:

```bash
python scripts/init_db.py
python scripts/migrate.py
python scripts/seed_db.py
python scripts/train_model.py
uvicorn api.main:app --reload --port 8000
streamlit run app/donor_form.py --server.port 8501
streamlit run app/streamer_dashboard.py --server.port 8502
streamlit run app/overlay.py --server.port 8503
```

Setelah API berjalan, flow produk utama juga bisa dibuka langsung dari backend:

- Panel Streamer: `http://localhost:8000/streamer`
- Link donasi contoh: `http://localhost:8000/donate/streamer_001`
- Overlay OBS contoh: `http://localhost:8000/overlay/streamer_001`
