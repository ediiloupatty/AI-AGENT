"""
voice.py — "Mulut" si agent (Text-to-Speech).

Mesin utama: edge-tts (suara Indonesia natural, streaming, cepat).
Fallback otomatis: gTTS (kalau edge-tts gagal, mis. saat offline/error).

Sebelum dibacakan, teks dibersihkan dulu dari emoji, markdown, blok kode, dan
URL supaya yang terdengar hanya kalimat yang natural.

Dependensi sistem: ffplay (bagian dari ffmpeg) untuk memutar mp3.
"""

import asyncio
import os
import queue
import re
import subprocess
import tempfile
import threading

# Set VOICE_ENABLED=0 di environment untuk mematikan suara (mode teks saja).
VOICE_ENABLED = os.getenv("VOICE_ENABLED", "1") != "0"
# Suara edge-tts. Pilihan ID: id-ID-ArdiNeural (pria), id-ID-GadisNeural (wanita).
VOICE_NAME = os.getenv("VOICE_NAME", "id-ID-ArdiNeural")
# Bahasa untuk fallback gTTS.
LANG = os.getenv("VOICE_LANG", "id")


def _bersihkan_teks(teks: str) -> str:
    """Buang elemen yang tidak enak dibacakan: kode, emoji, markdown, URL."""
    teks = re.sub(r"```.*?```", " ", teks, flags=re.DOTALL)   # blok kode
    teks = re.sub(r"`[^`]*`", " ", teks)                       # inline code
    teks = re.sub(r"https?://\S+", " ", teks)                  # URL
    teks = re.sub(r"[#*_>`]", " ", teks)                       # penanda markdown
    teks = re.sub(r"^\s*[-•]\s*", "", teks, flags=re.MULTILINE)
    teks = re.sub(                                             # emoji & simbol
        r"[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF←-⇿⌀-⏿]",
        " ", teks,
    )
    teks = re.sub(r"\s+", " ", teks).strip()                  # rapikan spasi
    return teks


def _edge_stream_play(teks: str) -> None:
    """Putar suara edge-tts SAMBIL generate (streaming).

    Audio dialirkan ke ffplay potongan demi potongan, jadi suara mulai
    terdengar begitu chunk pertama jadi — tidak menunggu seluruh audio selesai.
    """
    import edge_tts

    player = subprocess.Popen(
        ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", "-i", "pipe:0"],
        stdin=subprocess.PIPE,
    )

    async def _run():
        communicate = edge_tts.Communicate(teks, VOICE_NAME)
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                player.stdin.write(chunk["data"])

    try:
        asyncio.run(_run())
    finally:
        if player.stdin:
            player.stdin.close()
        player.wait()


def _gtts_save(teks: str, path: str) -> None:
    """Fallback: generate suara dengan gTTS."""
    from gtts import gTTS

    gTTS(text=teks, lang=LANG).save(path)


def speak(teks: str) -> None:
    """Bacakan teks dengan suara. Aman: tidak menghentikan agent kalau gagal."""
    if not VOICE_ENABLED:
        return
    bersih = _bersihkan_teks(teks)
    if not bersih:
        return

    path = None
    try:
        # Utama: edge-tts streaming (suara mulai cepat, tanpa file sementara).
        try:
            _edge_stream_play(bersih)
            return
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"   [edge-tts gagal ({e}), pakai gTTS...]")

        # Fallback: gTTS -> simpan file -> putar.
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            path = f.name
        _gtts_save(bersih, path)
        subprocess.run(
            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", path],
            check=False,
        )
    except KeyboardInterrupt:
        # Tekan Ctrl+C saat bicara = lewati suara, JANGAN matikan agent.
        print("\n   [⏭️  narasi suara dilewati]")
    except Exception as e:
        # Suara cuma "kulit" — kalau gagal, agent tetap lanjut bekerja.
        print(f"   [⚠️  TTS gagal, lanjut tanpa suara: {e}]")
    finally:
        if path:
            try:
                os.remove(path)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Speaker latar: bicara SAMBIL teks mengalir, dipotong per frasa pendek.
# ---------------------------------------------------------------------------
# Karakter yang menandai akhir sebuah potongan ucapan (tanda baca / baris baru).
_FLUSH_CHARS = set(".,!?;:\n")
# Kalau belum ketemu tanda baca tapi sudah sepanjang ini, paksa potong di spasi
# terdekat — supaya frasa panjang tanpa koma tetap mulai dibacakan cepat.
_MAX_CHUNK = 32


def _potong_siap_ucap(buf: str):
    """Ambil potongan yang siap diucapkan dari buffer; sisanya dikembalikan.

    Return (potongan_atau_None, sisa_buffer).
    """
    # Prioritas 1: potong di tanda baca pertama yang muncul.
    for i, ch in enumerate(buf):
        if ch in _FLUSH_CHARS:
            return buf[: i + 1], buf[i + 1:]
    # Prioritas 2: kalau sudah kepanjangan, potong di spasi terakhir.
    if len(buf) >= _MAX_CHUNK and " " in buf:
        idx = buf.rfind(" ")
        return buf[:idx], buf[idx + 1:]
    return None, buf


class StreamSpeaker:
    """Menerima teks bertahap (saat streaming) dan membacakannya per frasa.

    Pemakaian:
        sp = StreamSpeaker()
        sp.feed("Oke, ")        # otomatis mulai bicara begitu ada frasa siap
        sp.feed("saya cek...")
        sp.close()              # tunggu sampai semua selesai diucapkan
    """

    def __init__(self):
        self.enabled = VOICE_ENABLED
        if not self.enabled:
            return
        self._buf = ""
        self._q: "queue.Queue[str | None]" = queue.Queue()
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def _worker(self):
        while True:
            potongan = self._q.get()
            if potongan is None:
                return
            try:
                _edge_stream_play(potongan)
            except Exception:
                pass  # frasa gagal diucapkan -> lewati, jangan ganggu kerja agent

    def _enqueue(self, teks: str):
        bersih = _bersihkan_teks(teks)
        if bersih:
            self._q.put(bersih)

    def feed(self, teks: str):
        """Suapkan potongan teks baru dari stream."""
        if not self.enabled:
            return
        self._buf += teks
        while True:
            potongan, self._buf = _potong_siap_ucap(self._buf)
            if potongan is None:
                break
            self._enqueue(potongan)

    def close(self):
        """Ucapkan sisa buffer lalu tunggu antrean suara selesai."""
        if not self.enabled:
            return
        if self._buf.strip():
            self._enqueue(self._buf)
        self._buf = ""
        self._q.put(None)
        self._thread.join()


if __name__ == "__main__":
    # Tes cepat: python voice.py
    speak("Halo! Saya AI coding companion kamu. Suara saya sudah aktif dan terdengar lebih natural sekarang.")
