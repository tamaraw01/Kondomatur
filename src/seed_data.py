from __future__ import annotations

from itertools import cycle

import pandas as pd

from src.config import SAMPLE_DATA_PATH, ensure_project_dirs
from src.feature_engineering import build_text_for_model


SAMPLES_PER_CLASS = 300
EMOJI_WRAPPERS = [
    ("", ""),
    ("😺🐳 ", " 🐻🐼"),
    ("✨ ", " ✨"),
    ("[", "]"),
    ("๑۞๑ ", " ๑۞๑"),
]
CONFUSABLE_VARIANTS = {
    "a": ["ⓐ", "Ⓐ", "Δ", "𝔸", "ａ"],
    "b": ["🅱", "๒", "Ⓑ", "ｂ"],
    "c": ["ς", "Ⓒ", "ｃ"],
    "d": ["ᗪ", "Ⓓ", "ｄ"],
    "e": ["ᵉ", "ⓔ", "Ｅ", "𝑒"],
    "g": ["Ⓖ", "ɢ", "ｇ"],
    "h": ["Ħ", "Ⓗ", "ｈ"],
    "i": ["Ɨ", "Ⓘ", "Ｉ", "𝓲"],
    "j": ["Ⓙ", "ｊ"],
    "k": ["к", "Ⓚ", "Ｋ"],
    "l": ["🅻", "ⓛ", "ｌ"],
    "m": ["ⓜ", "Ｍ", "𝓶"],
    "n": ["η", "几", "Ⓝ", "ｎ"],
    "o": ["ㄖ", "🅾", "ⓞ", "Ｏ"],
    "p": ["ᵖ", "🅿", "Ⓟ", "ｐ"],
    "r": ["Ř", "Ⓡ", "ｒ"],
    "s": ["🆂", "ⓢ", "５", "ｓ"],
    "t": ["𝓽", "🆃", "７", "ｔ"],
    "u": ["ⓤ", "Ｕ"],
    "v": ["ᐯ", "Ⓥ"],
    "w": ["ⓦ", "Ｗ"],
    "x": ["χ", "Ⓧ"],
    "y": ["𝐘", "Ⓨ"],
    "z": ["Ⓩ", "ｚ"],
    "0": ["⓪", "０"],
    "1": ["①", "１"],
    "2": ["②", "２"],
    "3": ["③", "３"],
    "4": ["④", "４"],
    "5": ["⑤", "５"],
    "6": ["⑥", "６"],
    "7": ["➆", "⑦", "７"],
    "8": ["➇", "❽", "８"],
    "9": ["⑨", "９"],
}


BENIGN_MESSAGES = [
    "Semangat bang",
    "Semangat bang 😺🐳",
    "GG mainnya",
    "Sehat selalu",
    "Request lagu dong",
    "Lanjut bang seru banget",
    "Mantap gameplay-nya",
    "Terima kasih sudah live",
    "Bang jangan lupa makan",
    "Nice clutch tadi",
    "Support kecil dari aku",
]

SPAM_MESSAGES = [
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
]

SUSPICIOUS_MESSAGES = [
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
]

EXPLICIT_MESSAGES = [
    "slot gacor rtp 98%",
    "deposit sekarang bonus new member",
    "situs88 dot com gacor",
    "bola88 maxwin malam ini",
    "scatter hitam auto wd",
    "sl0t g4c0r rtp 98%",
    "m4xw1n malam ini",
    "s l o t g a c o r",
    "ｓｌｏｔ ｇａｃｏｒ",
    "gÃcÖr m4xw1n",
    "bocoran adm1n h4ri ini",
    "provider88 dot com bonus rtp 97%",
    "🅿🅾🅻🅰 🆃🅴🆁🅱🅰🅸🅺 🅷🅰🅽🆈🅰 🅳🅸 🅽🅴🆃888",
    "🆂🅻🅾🆃 🅶🅰🅲🅾🆁 🆁🆃🅿 98%",
    "🅱🅾🅲🅾🆁🅰🅽 🅰🅳🅼🅸🅽 🆅🅸🅿777",
    "p-o-l-a terbaik hanya di n-e-t888",
    "s.l.o.t g.a.c.o.r r.t.p 99%",
    "😺🐳 ᵖㄖｌⓐ tＥŘ๒ΔƗк ĦⒶ几𝐘𝔸 ᗪⒾ ηᵉ𝓽➇８❽ 🐻🐼",
    "ᵖㄖｌⓐ terbaik hanya di ηᵉ𝓽➇８❽",
    "vip777 bocoran admin hari ini",
    "play88 pola terbaik malam ini",
    "bet777 auto wd",
    "game88 bonus deposit",
]

SENDER_NAMES = [
    "Budi",
    "Ayu",
    "Raka",
    "Nina",
    "DemoUser",
    "kantorbola88",
    "situs88info",
    "viewer_setia",
    "PromoAkun",
    "max88team",
]


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
        if len(word) >= 3 and word.isascii() and word.replace("%", "").isalnum():
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
        if char.isupper() and char.lower() not in {"x"}:
            replacement = variants[(index + offset) % len(variants)]
        else:
            replacement = variants[(index + offset) % len(variants)]
        output.append(replacement)
    return "".join(output)


def symbol_noise_text(text: str, offset: int = 0) -> str:
    separators = ["·", "•", "_", "~", "|"]
    separator = separators[offset % len(separators)]
    return separator_text(text, separator)


def wrap_message(text: str, index: int) -> str:
    prefix, suffix = EMOJI_WRAPPERS[index % len(EMOJI_WRAPPERS)]
    return f"{prefix}{text}{suffix}"


def mutate_message(label: str, message: str, index: int) -> str:
    if label == "benign":
        variants = [
            message,
            wrap_message(message, index),
            message.upper() if index % 7 == 0 else message,
            f"{message}!!" if index % 5 == 0 else message,
        ]
        return variants[index % len(variants)]

    if label == "spam_non_judol":
        variants = [
            message,
            fullwidth_text(message) if index % 5 == 0 else message,
            wrap_message(message, index) if index % 4 == 0 else message,
        ]
        return variants[index % len(variants)]

    variants = [
        message,
        fullwidth_text(message),
        separator_text(message, " "),
        separator_text(message, "."),
        separator_text(message, "-"),
        symbol_noise_text(message, index),
        confusable_text(message, index),
        wrap_message(confusable_text(message, index), index),
        wrap_message(symbol_noise_text(message, index), index),
    ]
    return variants[index % len(variants)]


def generate_sample_dataset(force: bool = False) -> pd.DataFrame:
    ensure_project_dirs()
    if SAMPLE_DATA_PATH.exists() and not force:
        return pd.read_csv(SAMPLE_DATA_PATH)

    rows = []
    groups = [
        ("benign", BENIGN_MESSAGES),
        ("spam_non_judol", SPAM_MESSAGES),
        ("suspicious_judol", SUSPICIOUS_MESSAGES),
        ("explicit_judol", EXPLICIT_MESSAGES),
    ]
    sender_cycle = cycle(SENDER_NAMES)

    for label, messages in groups:
        for index in range(SAMPLES_PER_CLASS):
            message = mutate_message(label, messages[index % len(messages)], index)
            sender = next(sender_cycle)
            if label == "benign":
                sender = ["Budi", "Ayu", "Raka", "Nina", "ViewerBaik"][index % 5]
            elif label == "spam_non_judol":
                sender = ["TokoAyu", "PromoUser", "LapakMurah", "SubrekAku", "JualCepat"][index % 5]
            elif label == "suspicious_judol":
                sender = ["admininfo", "polaUpdate", "cuanMalam", "viewer88", "bocoranNow"][index % 5]
            else:
                sender = ["kantorbola88", "situs88info", "max88team", "slot88news", "provider88"][index % 5]

            rows.append(
                {
                    "donation_id": f"sample_{label}_{index:03d}",
                    "sender_name_raw": sender,
                    "sender_email_raw": f"user{index}@example.com",
                    "amount": 10000 + (index % 10) * 5000,
                    "payment_method": "QRIS",
                    "platform": "Saweria",
                    "message_raw": message,
                    "label_multiclass": label,
                    "text_for_model": build_text_for_model(sender, message),
                }
            )

    df = pd.DataFrame(rows)
    df.to_csv(SAMPLE_DATA_PATH, index=False)
    return df


if __name__ == "__main__":
    data = generate_sample_dataset(force=True)
    print(f"Generated {len(data)} rows at {SAMPLE_DATA_PATH}")
