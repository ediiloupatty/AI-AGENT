"""
provider.py — Sumber kebenaran "provider LLM aktif" (Qwen / OpenAI).

Qwen tetap default; OpenAI hanya opsi tambahan. Keduanya dipakai lewat SDK
`openai` (format chat-completions sama), jadi pindah provider = ganti
(api_key, base_url, model). Bisa di-toggle saat jalan: ketik 'openai'/'gpt'
atau 'qwen'.

Modul ini hanya bergantung pada `config` (hindari impor siklik).
"""

import re

from . import config

_PROVIDERS = {
    "qwen": {
        "name": "Qwen",
        "api_key": config.QWEN_API_KEY,
        "base_url": config.QWEN_BASE_URL,
        "model": config.QWEN_MODEL,
        "headers": {},
        "cmd": {"qwen", "kwen", "kuen", "ke qwen"},
    },
    "openai": {
        "name": "OpenAI",
        "api_key": config.OPENAI_API_KEY,
        "base_url": config.OPENAI_BASE_URL,
        "model": config.OPENAI_MODEL,
        "headers": {},
        "cmd": {"openai", "open ai", "gpt", "chatgpt", "ke openai"},
    },
    "openrouter": {
        "name": "OpenRouter",
        "api_key": config.OPENROUTER_API_KEY,
        "base_url": config.OPENROUTER_BASE_URL,
        "model": config.OPENROUTER_MODEL,
        # Header opsional OpenRouter (untuk atribusi/ranking; tidak wajib).
        "headers": {
            "HTTP-Referer": "https://github.com/ediiloupatty/voice-coding-assistant",
            "X-OpenRouter-Title": "Voca",
        },
        # Body tambahan: aktifkan reasoning (model berpikir dulu).
        "extra_body": (
            {"reasoning": {"enabled": True}} if config.OPENROUTER_REASONING else {}
        ),
        "cmd": {"openrouter", "open router", "router", "ke openrouter"},
    },
    "deepseek": {
        "name": "DeepSeek",
        "api_key": config.DEEPSEEK_API_KEY,
        "base_url": config.DEEPSEEK_BASE_URL,
        "model": config.DEEPSEEK_MODEL,
        "headers": {},
        # Mode thinking DeepSeek (berpikir dulu, usaha reasoning tinggi).
        "extra_body": (
            {"thinking": {"type": "enabled"}, "reasoning_effort": "high"}
            if config.DEEPSEEK_THINKING else {}
        ),
        "cmd": {"deepseek", "deep seek", "dipsik", "ke deepseek"},
    },
}

# Provider aktif (default dari config; jatuh ke 'qwen' kalau tak dikenal).
CURRENT = config.VOCA_PROVIDER if config.VOCA_PROVIDER in _PROVIDERS else "qwen"


def set(prov: str) -> bool:
    """Ganti provider aktif. Return True kalau kode dikenal."""
    global CURRENT
    if prov in _PROVIDERS:
        CURRENT = prov
        return True
    return False


def code() -> str:
    """Kode provider aktif ('qwen' / 'openai')."""
    return CURRENT


def _cur() -> dict:
    return _PROVIDERS[CURRENT]


def name() -> str:
    """Nama provider aktif."""
    return _cur()["name"]


def name_of(prov: str) -> str:
    """Nama provider tertentu."""
    return _PROVIDERS[prov]["name"]


def api_key() -> str | None:
    return _cur()["api_key"]


def base_url() -> str:
    return _cur()["base_url"]


def model() -> str:
    return _cur()["model"]


def headers() -> dict:
    """Header HTTP tambahan untuk provider aktif (mis. atribusi OpenRouter)."""
    return _cur().get("headers", {})


def extra_body() -> dict:
    """Field body tambahan untuk provider aktif (mis. reasoning OpenRouter)."""
    return _cur().get("extra_body", {})


def has_key(prov: str) -> bool:
    """True kalau provider tertentu sudah punya API key."""
    return bool(_PROVIDERS.get(prov, {}).get("api_key"))


def detect_command(teks: str) -> str | None:
    """Deteksi perintah ganti provider dari ucapan/ketikan pendek.

    Return kode provider kalau teks jelas perintah ganti provider, else None.
    Dibatasi ucapan pendek (<=3 kata) agar tak salah memicu di tengah kalimat.
    """
    bersih = re.sub(r"[^\w\s]", "", teks.lower()).strip()
    if not bersih or len(bersih.split()) > 3:
        return None
    for kode, data in _PROVIDERS.items():
        if bersih in data["cmd"]:
            return kode
    return None
