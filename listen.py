"""
listen.py — "Telinga" si agent (Speech-to-Text dengan faster-whisper).

Merekam suara dari mikrofon (mode push-to-talk: tekan ENTER untuk mulai,
ENTER lagi untuk berhenti), lalu mengubahnya jadi teks dengan model Whisper
yang berjalan lokal/offline.

Dependensi: faster-whisper, sounddevice (butuh PortAudio di sistem).
"""

import os

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

SAMPLE_RATE = 16000          # Whisper mengharapkan audio 16 kHz mono
# Ukuran model: tiny / base / small / medium / large-v3.
# "small" = keseimbangan bagus kecepatan vs akurasi untuk Bahasa Indonesia.
MODEL_SIZE = os.getenv("WHISPER_MODEL", "small")
LANG = os.getenv("WHISPER_LANG", "id")

_model = None


def _get_model() -> WhisperModel:
    """Muat model Whisper sekali saja (lazy, lalu di-cache)."""
    global _model
    if _model is None:
        print(f"   [memuat model Whisper '{MODEL_SIZE}' (sekali di awal)...]")
        _model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    return _model


def record_until_enter() -> np.ndarray | None:
    """Rekam dari mikrofon sampai user menekan ENTER. Return audio float32."""
    frames = []

    def callback(indata, frames_count, time_info, status):
        frames.append(indata.copy())

    input("\n🎤 Tekan ENTER untuk MULAI bicara...")
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1,
                        dtype="float32", callback=callback):
        input("🔴 Merekam... tekan ENTER lagi untuk BERHENTI.")

    if not frames:
        return None
    return np.concatenate(frames, axis=0).flatten()


def transcribe(audio) -> str:
    """Ubah audio (numpy array atau path file) jadi teks."""
    model = _get_model()
    segments, _info = model.transcribe(audio, language=LANG, beam_size=5)
    return " ".join(seg.text for seg in segments).strip()


def listen() -> str:
    """Rekam dari mic lalu kembalikan teks hasil transkripsi."""
    audio = record_until_enter()
    if audio is None or len(audio) == 0:
        return ""
    print("   [📝 mentranskripsi...]")
    return transcribe(audio)


if __name__ == "__main__":
    # Tes cepat: python listen.py  -> bicara, lihat teksnya
    teks = listen()
    print(f"\n📝 Kamu bilang: {teks!r}")
