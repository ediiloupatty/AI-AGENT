"""
lang.py — Sumber kebenaran "bahasa aktif" Voca (Indonesia / English).

Satu tempat menyimpan bahasa yang sedang dipakai beserta semua setelan turunannya
(kode STT Whisper, kode/​model TTS, instruksi bahasa untuk LLM, kata pemicu ganti
bahasa). Modul lain (voice, listen, agent) cukup membaca getter di sini, sehingga
ganti bahasa saat runtime otomatis berlaku di STT, TTS, dan jawaban AI.

Catatan: modul ini HANYA bergantung pada `config` agar tidak ada impor siklik.
"""

import re

from . import config

# Tabel setelan per bahasa.
_LANGS = {
    "id": {
        "name": "Bahasa Indonesia",
        "whisper": "id",                  # kode bahasa Whisper (STT)
        "gtts": "id",                     # kode bahasa gTTS (TTS online)
        "piper": config.PIPER_MODEL,      # model Piper lokal (TTS offline)
        "phonetic": config.SPEAK_PHONETIC,  # eja kata Inggris (hanya untuk suara ID)
        "directive": "Selalu balas dalam Bahasa Indonesia yang natural dan santai.",
        "switched": "Oke, sekarang pakai Bahasa Indonesia.",
        "cmd": {"indonesia", "indo", "id", "bahasa indonesia", "bahasa", "ke indonesia"},
    },
    "en": {
        "name": "English",
        "whisper": "en",
        "gtts": "en",
        "piper": config.PIPER_MODEL_EN,   # opsional; kalau tak ada -> gTTS
        "phonetic": False,                # jangan eja-fonetik saat bahasa English
        "directive": ("IMPORTANT: From now on, respond ONLY in English, regardless of "
                      "the language used in the instructions above. Keep the same casual, "
                      "concise style."),
        "switched": "Okay, switching to English.",
        "cmd": {"english", "en", "inggris", "bahasa inggris", "ke english", "to english"},
    },
}

# Bahasa aktif saat ini (default dari config; jatuh ke 'en' kalau tak dikenal).
CURRENT = config.VOCA_LANG if config.VOCA_LANG in _LANGS else "en"


def set(code: str) -> bool:
    """Ganti bahasa aktif. Return True kalau berhasil (kode dikenal)."""
    global CURRENT
    if code in _LANGS:
        CURRENT = code
        return True
    return False


def code() -> str:
    """Kode bahasa aktif ('id' / 'en')."""
    return CURRENT


def daftar() -> list[dict]:
    """Daftar bahasa untuk menu pilih: [{code, name, is_current}]."""
    return [
        {"code": k, "name": v["name"], "is_current": k == CURRENT}
        for k, v in _LANGS.items()
    ]


# ---------------------------------------------------------------------------
# i18n teks ANTARMUKA (chrome) — ikut bahasa aktif. Pakai lewat t("kunci").
# ---------------------------------------------------------------------------
_UI = {
    "en": {
        "subtitle": "· voice coding companion",
        "lbl_model": "model", "lbl_lang": "language", "lbl_folder": "folder", "lbl_mode": "mode",
        "mode_text": "text", "mode_voice": "hands-free (voice)",
        "hint_text": "'v' speak  ·  /model  ·  /lan  ·  'exit' quit",
        "bar_listen_label": "● VOICE",
        "bar_listen_hint": "speak / type  ·  /model  ·  /lan  ·  ^C quit",
        "bar_trans_label": "⏳ WORKING", "bar_trans_hint": "processing speech…",
        "bar_think_label": "🧠 THINKING", "bar_think_hint": "composing answer…",
        "menu_model_title": "SELECT MODEL", "menu_lang_title": "SELECT LANGUAGE",
        "menu_hint": "↑/↓ move  ·  ENTER select  ·  q cancel",
        "tag_active": "(active)", "st_ready": "● Ready", "st_unset": "○ Not set",
        "resume_q": "Found a previous session ({n} turns). Resume?",
        "resumed": "Session resumed.",
        "bye": "see you",
        "stopped_prompt": "⏹ stopped — back to prompt",
        "stopped_listen": "⏹ stopped — back to listening",
        "now_using": "Now using {name} ({model}).",
        "already_lang": "Already using {name}.",
        "key_missing": "API key for {name} is not set in .env.",
        "greet": "Hi, I'm ready to help. Talk to me, or type if you prefer.",
        "bye_voice": "Alright, see you!",
        "confirm_yes": "Okay, proceeding.", "confirm_no": "Alright, cancelled.",
    },
    "id": {
        "subtitle": "· asisten coding suara",
        "lbl_model": "model", "lbl_lang": "bahasa", "lbl_folder": "folder", "lbl_mode": "mode",
        "mode_text": "teks", "mode_voice": "hands-free (suara)",
        "hint_text": "'v' bicara  ·  /model  ·  /lan  ·  'keluar' berhenti",
        "bar_listen_label": "● SUARA",
        "bar_listen_hint": "bicara / ketik  ·  /model  ·  /lan  ·  ^C keluar",
        "bar_trans_label": "⏳ PROSES", "bar_trans_hint": "memproses suara…",
        "bar_think_label": "🧠 BERPIKIR", "bar_think_hint": "menyusun jawaban…",
        "menu_model_title": "PILIH PROVIDER", "menu_lang_title": "PILIH BAHASA",
        "menu_hint": "↑/↓ pindah  ·  ENTER pilih  ·  q batal",
        "tag_active": "(aktif)", "st_ready": "● Siap", "st_unset": "○ Belum diset",
        "resume_q": "Ada sesi sebelumnya ({n} giliran). Lanjutkan?",
        "resumed": "Sesi dilanjutkan.",
        "bye": "sampai jumpa",
        "stopped_prompt": "⏹ dihentikan — kembali ke prompt",
        "stopped_listen": "⏹ dihentikan — kembali mendengarkan",
        "now_using": "Sekarang pakai {name} ({model}).",
        "already_lang": "Sudah pakai {name}.",
        "key_missing": "API key untuk {name} belum diset di .env.",
        "greet": "Halo, saya siap membantu. Silakan bicara, atau ketik kalau mau.",
        "bye_voice": "Baik, sampai jumpa!",
        "confirm_yes": "Oke, saya lanjutkan.", "confirm_no": "Baik, saya batalkan.",
    },
}


def t(key: str, **kw) -> str:
    """Ambil teks UI untuk bahasa aktif (fallback ke English lalu ke key mentah)."""
    s = _UI.get(CURRENT, {}).get(key) or _UI["en"].get(key, key)
    return s.format(**kw) if kw else s


def _cur() -> dict:
    return _LANGS[CURRENT]


def whisper() -> str:
    """Kode bahasa untuk Whisper (STT)."""
    return _cur()["whisper"]


def gtts() -> str:
    """Kode bahasa untuk gTTS (TTS online)."""
    return _cur()["gtts"]


def piper_model() -> str:
    """Path model Piper untuk bahasa aktif (mungkin file-nya tidak ada)."""
    return _cur()["piper"]


def phonetic() -> bool:
    """Apakah eja-fonetik kata Inggris dipakai (hanya untuk suara Indonesia)."""
    return _cur()["phonetic"]


def name() -> str:
    """Nama bahasa aktif yang enak dibaca."""
    return _cur()["name"]


def directive() -> str:
    """Instruksi bahasa untuk disisipkan ke system prompt LLM."""
    return _cur()["directive"]


def switched_msg() -> str:
    """Kalimat konfirmasi setelah ganti bahasa (diucapkan & dicetak)."""
    return _cur()["switched"]


def detect_command(teks: str) -> str | None:
    """Deteksi perintah ganti bahasa dari ucapan/ketikan pendek.

    Return kode bahasa ('id'/'en') kalau teks jelas-jelas perintah ganti bahasa,
    selain itu None. Dibatasi ucapan pendek (<=3 kata) supaya kata 'english' di
    tengah kalimat biasa tidak salah memicu.
    """
    bersih = re.sub(r"[^\w\s]", "", teks.lower()).strip()
    if not bersih or len(bersih.split()) > 3:
        return None
    for kode, data in _LANGS.items():
        if bersih in data["cmd"]:
            return kode
    return None
