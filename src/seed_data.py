from __future__ import annotations

from collections.abc import Callable

import pandas as pd

from src.config import SAMPLE_DATA_PATH, ensure_project_dirs
from src.feature_engineering import build_text_for_model


SAMPLES_PER_CLASS = 2500

EMOJI_WRAPPERS = [
    ("", ""),
    ("😺🐳 ", " 🐻🐼"),
    ("✨ ", " ✨"),
    ("🔥 ", " 🙌"),
    ("💙 ", " 💙"),
    ("[", "]"),
    ("๑۞๑ ", " ๑۞๑"),
    ("<<< ", " >>>"),
]

CONFUSABLE_VARIANTS = {
    "a": ["ⓐ", "Ⓐ", "Δ", "𝔸", "ａ", "α", "а", "🅰"],
    "b": ["🅱", "๒", "Ⓑ", "ｂ", "в", "ƅ"],
    "c": ["ς", "Ⓒ", "ｃ", "с", "ƈ"],
    "d": ["ᗪ", "Ⓓ", "ｄ", "ԁ", "𝓭"],
    "e": ["ᵉ", "ⓔ", "Ｅ", "𝑒", "е", "ℯ"],
    "f": ["ⓕ", "ｆ", "𝒻"],
    "g": ["Ⓖ", "ɢ", "ｇ", "ց"],
    "h": ["Ħ", "Ⓗ", "ｈ", "һ", "𝓱"],
    "i": ["Ɨ", "Ⓘ", "Ｉ", "𝓲", "і", "ι"],
    "j": ["Ⓙ", "ｊ", "ј"],
    "k": ["к", "Ⓚ", "Ｋ", "𝓴"],
    "l": ["🅻", "ⓛ", "ｌ", "ⅼ", "𝓵"],
    "m": ["ⓜ", "Ｍ", "𝓶", "м"],
    "n": ["η", "几", "Ⓝ", "ｎ", "ո"],
    "o": ["ㄖ", "🅾", "ⓞ", "Ｏ", "ο", "о"],
    "p": ["ᵖ", "🅿", "Ⓟ", "ｐ", "р"],
    "q": ["ⓠ", "ｑ", "զ"],
    "r": ["Ř", "Ⓡ", "ｒ", "г", "𝓻"],
    "s": ["🆂", "ⓢ", "５", "ｓ", "ѕ"],
    "t": ["𝓽", "🆃", "７", "ｔ", "τ"],
    "u": ["ⓤ", "Ｕ", "υ", "ս"],
    "v": ["ᐯ", "Ⓥ", "ｖ", "ѵ"],
    "w": ["ⓦ", "Ｗ", "ԝ"],
    "x": ["χ", "Ⓧ", "ｘ", "х"],
    "y": ["𝐘", "Ⓨ", "ｙ", "у"],
    "z": ["Ⓩ", "ｚ", "ᴢ"],
    "0": ["⓪", "０", "⓿"],
    "1": ["①", "１", "❶"],
    "2": ["②", "２", "❷"],
    "3": ["③", "３", "❸"],
    "4": ["④", "４", "❹"],
    "5": ["⑤", "５", "❺"],
    "6": ["⑥", "６", "❻"],
    "7": ["➆", "⑦", "７", "❼"],
    "8": ["➇", "❽", "８", "⑧"],
    "9": ["⑨", "９", "❾"],
}

LEET_VARIANTS = {
    "a": ["4", "@"],
    "e": ["3"],
    "i": ["1", "!"],
    "o": ["0"],
    "s": ["5", "$"],
    "t": ["7"],
    "b": ["8"],
}

ZERO_WIDTH_CHARS = ["\u200b", "\u200c", "\u200d", "\u2060"]
SEPARATORS = [" ", ".", "-", "_", "·", "•", "|", "/", "\\", "~", ":"]
NOISE_TOKENS = ["!!", "...", "+++ ", " #info", " cek", " gas", " malam", " live"]

BENIGN_SENDERS = [
    "Budi",
    "Ayu",
    "Raka",
    "Nina",
    "ViewerBaik",
    "TemanLive",
    "KopiSore",
    "RuangChat",
    "Dina",
    "Fajar",
    "Lia",
    "Mira",
    "Doni",
    "Bagas",
    "Salsa",
    "NontonSantai",
    "PenontonSetia",
    "TimSupport",
    "AnakRank",
    "SahabatStream",
]

SPAM_SENDERS = [
    "TokoAyu",
    "PromoUser",
    "LapakMurah",
    "SubrekAku",
    "JualCepat",
    "KatalogHemat",
    "DiskonKita",
    "ProdukLokal",
    "AkunSecond",
    "KelasOnline",
]

SUSPICIOUS_SENDERS = [
    "admininfo",
    "polaUpdate",
    "cuanMalam",
    "viewer88",
    "bocoranNow",
    "jamramai",
    "rtpinfo",
    "maxwinTips",
    "scatterNote",
    "depoInfo",
]

EXPLICIT_SENDERS = [
    "kantorbola88",
    "situs88info",
    "max88team",
    "slot88news",
    "provider88",
    "net888update",
    "vip777admin",
    "play88center",
    "bet777id",
    "game88official",
    "spin88hub",
    "jackpot88care",
]

BENIGN_BASES = [
    "Semangat bang",
    "GG mainnya",
    "Sehat selalu",
    "Request lagu dong",
    "Lanjut bang seru banget",
    "Mantap gameplay-nya",
    "Terima kasih sudah live",
    "Bang jangan lupa makan",
    "Nice clutch tadi",
    "Support kecil dari aku",
    "Keren banget tadi",
    "Aku suka vibes live ini",
    "Semoga rank naik",
    "Buat beli kopi",
    "Tetap semangat kuliahnya",
    "Terima kasih hiburannya",
    "Audio sudah enak",
    "Kamera sudah jelas",
    "Mainnya sabar banget",
    "Good luck match berikutnya",
    "Salam dari chat",
    "Kontennya rapi",
    "Jangan lupa istirahat",
    "Bantu sedikit ya",
    "Seru nonton bareng",
    "Mode santai dulu",
    "Terima kasih tutorialnya",
    "Akhirnya bisa nonton lagi",
    "Bang coba build baru",
    "Clip tadi lucu banget",
    "Semoga sehat selalu",
    "Lanjut sampai selesai",
    "Kualitas stream bagus",
    "Aku dukung terus",
]

BENIGN_CONTEXTS = [
    "",
    "buat support live hari ini",
    "dari penonton setia",
    "semoga harimu lancar",
    "jangan lupa minum air",
    "untuk beli snack",
    "match tadi seru",
    "request baca chat dong",
    "terima kasih sudah menemani",
    "semoga target tercapai",
    "aku nonton dari awal",
    "lanjut konten positif",
]

SPAM_BASES = [
    "Follow IG aku ya",
    "Subscribe channel aku",
    "Jual akun murah",
    "Promo skincare murah",
    "Cek toko aku",
    "Diskon produk hari ini",
    "Subrek channel baru aku",
    "Mampir ke lapak aku",
    "Promo produk lokal",
    "Cek link bio aku",
    "Open jasa edit video",
    "Jual voucher game murah",
    "Katalog baju baru turun",
    "Flash sale sepatu hari ini",
    "Cek kelas desain aku",
    "Paket belajar bahasa",
    "Mau barter akun game",
    "Preorder aksesoris hp",
    "Jasa top up legal",
    "Mampir marketplace aku",
]

SPAM_CONTEXTS = [
    "",
    "harga mulai 10 ribu",
    "stok terbatas",
    "link ada di bio",
    "promo weekend",
    "buat yang minat saja",
    "cek katalog terbaru",
    "garansi toko",
    "gratis ongkir wilayah tertentu",
    "pakai kode hemat",
]

SUSPICIOUS_BASES = [
    "jam gacor malam ini",
    "pola admin terbaru",
    "rtp tinggi",
    "gas sekarang",
    "bocoran admin hari ini",
    "cuan cepat malam ini",
    "info maxwin terbaru",
    "pola scatter katanya bagus",
    "admin kasih bocoran",
    "depo kecil bisa cuan",
    "pola terbaik malam ini",
    "info pola admin terbaru",
    "jam gacor paling ramai",
    "scatter mulai rapat",
    "wd lancar katanya",
    "bonus harian masih ada",
    "winrate naik malam ini",
    "pola spin pelan dulu",
    "admin kasih kode",
    "rtp live lagi tinggi",
    "bocoran pola hijau",
    "deposit receh dulu",
    "taruhan kecil katanya aman",
    "togel malam ini ramai",
    "casino live baru buka",
]

SUSPICIOUS_CONTEXTS = [
    "",
    "jangan telat",
    "cek sebelum penuh",
    "katanya aman",
    "buat info saja",
    "ramai di grup",
    "langsung gas",
    "malam ini saja",
    "kode admin turun",
    "pola sudah kebuka",
    "yang paham merapat",
    "jangan sebut merek",
]

GAME_TERMS = ["slot", "scatter", "casino", "togel", "spin", "jackpot", "bet", "taruhan"]
PROVIDER_PLACEHOLDERS = [
    "provider88",
    "situs88",
    "bola88",
    "slot88",
    "max88",
    "win88",
    "jackpot88",
    "spin88",
    "net888",
    "vip777",
    "play88",
    "game88",
    "bet777",
]
DOMAIN_FORMS = [
    "{provider}.com",
    "{provider}.net",
    "www.{provider}.com",
    "{provider} dot com",
    "{provider} dot net",
    "{provider} [dot] com",
    "{provider} (dot) com",
    "{provider} d0t com",
    "{provider} titik com",
    "{provider}-official dot com",
]
PROMO_TERMS = [
    "gacor",
    "maxwin",
    "auto wd",
    "bonus new member",
    "deposit sekarang",
    "depo receh",
    "withdraw cepat",
    "bocoran admin",
    "pola terbaik",
    "rtp tinggi",
    "winrate tinggi",
]
PERCENT_CLAIMS = ["rtp 88%", "rtp 92%", "rtp 95", "rtp 97%", "rtp 98%", "winrate 90%", "menang 99%"]
PAYMENT_TERMS = ["deposit qris", "depo ewallet", "wd cepat", "saldo masuk", "bonus deposit"]
EXPLICIT_TEMPLATES = [
    "{game} {promo} {percent}",
    "{provider} {domain} {promo}",
    "{game} {promo} {payment}",
    "{domain} {game} {percent}",
    "{promo} hanya di {provider}",
    "{payment} {provider} {percent}",
    "admin {provider} kasih {promo}",
    "{game} {provider} {promo} malam ini",
    "link {domain} {payment}",
    "bocoran {game} {provider} {percent}",
]


def _pick(items: list[str], index: int, step: int = 1) -> str:
    return items[(index * step) % len(items)]


def fullwidth_text(text: str) -> str:
    output = []
    for char in text:
        if char == " ":
            output.append(char)
        elif 33 <= ord(char) <= 126:
            output.append(chr(ord(char) + 0xFEE0))
        else:
            output.append(char)
    return "".join(output)


def separator_text(text: str, separator: str) -> str:
    words = []
    for word in text.split():
        clean = word.strip(".,!?:;")
        if len(clean) >= 3 and clean.isascii() and clean.replace("%", "").replace("-", "").isalnum():
            words.append(separator.join(word))
        else:
            words.append(word)
    return " ".join(words)


def confusable_text(text: str, offset: int = 0) -> str:
    output = []
    for index, char in enumerate(text):
        variants = CONFUSABLE_VARIANTS.get(char.lower())
        if not variants:
            output.append(char)
            continue
        output.append(variants[(index + offset) % len(variants)])
    return "".join(output)


def leet_text(text: str, offset: int = 0) -> str:
    output = []
    for index, char in enumerate(text):
        variants = LEET_VARIANTS.get(char.lower())
        if variants and (index + offset) % 2 == 0:
            output.append(variants[(index + offset) % len(variants)])
        else:
            output.append(char)
    return "".join(output)


def zero_width_text(text: str, offset: int = 0) -> str:
    chars = []
    zw = ZERO_WIDTH_CHARS[offset % len(ZERO_WIDTH_CHARS)]
    for index, char in enumerate(text):
        chars.append(char)
        if char.isalnum() and (index + offset) % 3 == 0:
            chars.append(zw)
    return "".join(chars)


def mixed_case_text(text: str, offset: int = 0) -> str:
    return "".join(char.upper() if char.isalpha() and (index + offset) % 2 == 0 else char for index, char in enumerate(text))


def compact_text(text: str) -> str:
    return text.replace(" ", "")


def noisy_text(text: str, offset: int = 0) -> str:
    token = NOISE_TOKENS[offset % len(NOISE_TOKENS)]
    if offset % 2 == 0:
        return f"{text}{token}"
    return f"{token.strip()} {text}"


def wrap_message(text: str, index: int) -> str:
    prefix, suffix = EMOJI_WRAPPERS[index % len(EMOJI_WRAPPERS)]
    return f"{prefix}{text}{suffix}"


OBFUSCATORS: list[Callable[[str, int], str]] = [
    lambda text, index: text,
    lambda text, index: fullwidth_text(text),
    lambda text, index: separator_text(text, SEPARATORS[index % len(SEPARATORS)]),
    lambda text, index: confusable_text(text, index),
    lambda text, index: leet_text(text, index),
    lambda text, index: zero_width_text(text, index),
    lambda text, index: mixed_case_text(text, index),
    lambda text, index: compact_text(text),
    lambda text, index: noisy_text(text, index),
    lambda text, index: wrap_message(confusable_text(text, index), index),
    lambda text, index: wrap_message(separator_text(text, SEPARATORS[index % len(SEPARATORS)]), index),
    lambda text, index: zero_width_text(leet_text(text, index), index),
    lambda text, index: confusable_text(leet_text(text, index), index),
]


def benign_message(index: int) -> str:
    base = _pick(BENIGN_BASES, index, 7)
    context = _pick(BENIGN_CONTEXTS, index, 5)
    message = f"{base} {context}".strip()
    if index % 6 == 0:
        message = wrap_message(message, index)
    if index % 11 == 0:
        message = f"{message}!"
    if index % 17 == 0:
        message = f"{message} #{100 + (index % 900)}"
    return message


def spam_message(index: int) -> str:
    base = _pick(SPAM_BASES, index, 5)
    context = _pick(SPAM_CONTEXTS, index, 7)
    message = f"{base} {context}".strip()
    if index % 9 == 0:
        message = f"{message} https://contoh-toko{index % 37}.id"
    if index % 13 == 0:
        message = fullwidth_text(message)
    if index % 19 == 0:
        message = wrap_message(message, index)
    return message


def suspicious_message(index: int) -> str:
    base = _pick(SUSPICIOUS_BASES, index, 11)
    context = _pick(SUSPICIOUS_CONTEXTS, index, 7)
    message = f"{base} {context}".strip()
    obfuscator = OBFUSCATORS[index % len(OBFUSCATORS)]
    return obfuscator(message, index)


def explicit_message(index: int) -> str:
    provider = _pick(PROVIDER_PLACEHOLDERS, index, 7)
    domain = _pick(DOMAIN_FORMS, index, 5).format(provider=provider)
    template = _pick(EXPLICIT_TEMPLATES, index, 3)
    message = template.format(
        game=_pick(GAME_TERMS, index, 11),
        provider=provider,
        domain=domain,
        promo=_pick(PROMO_TERMS, index, 13),
        percent=_pick(PERCENT_CLAIMS, index, 17),
        payment=_pick(PAYMENT_TERMS, index, 19),
    )
    obfuscator = OBFUSCATORS[index % len(OBFUSCATORS)]
    return obfuscator(message, index)


def sender_for_label(label: str, index: int) -> str:
    if label == "benign":
        return _pick(BENIGN_SENDERS, index, 3)
    if label == "spam_non_judol":
        return _pick(SPAM_SENDERS, index, 5)
    if label == "suspicious_judol":
        sender = _pick(SUSPICIOUS_SENDERS, index, 7)
        if index % 4 == 0:
            return confusable_text(sender, index)
        if index % 9 == 0:
            return leet_text(sender, index)
        return sender
    sender = _pick(EXPLICIT_SENDERS, index, 11)
    if index % 3 == 0:
        return confusable_text(sender, index)
    if index % 5 == 0:
        return separator_text(sender, SEPARATORS[index % len(SEPARATORS)])
    if index % 7 == 0:
        return leet_text(sender, index)
    return sender


def message_for_label(label: str, index: int) -> str:
    if label == "benign":
        return benign_message(index)
    if label == "spam_non_judol":
        return spam_message(index)
    if label == "suspicious_judol":
        return suspicious_message(index)
    return explicit_message(index)


def generate_rows_for_label(label: str, count: int) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    seen: set[tuple[str, str, str]] = set()
    index = 0
    while len(rows) < count:
        sender = sender_for_label(label, index)
        message = message_for_label(label, index)
        key = (label, sender, message)
        index += 1
        if key in seen:
            continue
        seen.add(key)
        row_number = len(rows)
        rows.append(
            {
                "donation_id": f"sample_{label}_{row_number:04d}",
                "sender_name_raw": sender,
                "sender_email_raw": f"user{row_number:04d}@example.com",
                "amount": 10000 + (row_number % 25) * 2500,
                "payment_method": _pick(["QRIS", "E-Wallet", "Virtual Account", "Transfer"], row_number),
                "platform": _pick(["Saweria", "Trakteer", "Kondomatur", "DemoPay"], row_number, 3),
                "message_raw": message,
                "label_multiclass": label,
                "text_for_model": build_text_for_model(sender, message),
            }
        )
    return rows


def generate_sample_dataset(force: bool = False) -> pd.DataFrame:
    ensure_project_dirs()
    if SAMPLE_DATA_PATH.exists() and not force:
        return pd.read_csv(SAMPLE_DATA_PATH)

    rows: list[dict[str, object]] = []
    for label in ["benign", "spam_non_judol", "suspicious_judol", "explicit_judol"]:
        rows.extend(generate_rows_for_label(label, SAMPLES_PER_CLASS))

    df = pd.DataFrame(rows)
    duplicate_count = int(df.duplicated(subset=["sender_name_raw", "message_raw", "label_multiclass"]).sum())
    if duplicate_count:
        raise RuntimeError(f"Synthetic dataset contains {duplicate_count} duplicate sender/message/label rows")
    df.to_csv(SAMPLE_DATA_PATH, index=False)
    return df


if __name__ == "__main__":
    data = generate_sample_dataset(force=True)
    print(f"Generated {len(data)} unique rows at {SAMPLE_DATA_PATH}")
