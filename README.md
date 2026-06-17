# 🎙️ AI Coding Companion

AI yang bekerja bersamamu seperti rekan developer: kamu beri perintah, ia
menganalisis folder kerja, mengerjakan tugas, dan menarasikan progresnya
secara real-time. Memakai model **Qwen** (`qwen-plus`) via DashScope
internasional (endpoint OpenAI-compatible).

Dibangun bertahap:

- **Fase 1 (selesai)** — Otak agent berbasis teks: Qwen + tools (baca folder,
  baca/tulis file, jalankan command) dengan konfirmasi sebelum bertindak.
- **Fase 2 (selesai)** — Suara keluar (TTS / gTTS): agent menarasikan progres
  dengan suara. Lihat `voice.py`.
- **Fase 3 (selesai)** — Suara masuk (STT / faster-whisper): perintah lewat
  mikrofon. Lihat `listen.py`.
- **Fase 4** — Loop penuh hands-free: ngomong → kerja → lapor suara.

## Suara keluar / TTS (Fase 2)

Narasi agent dibacakan otomatis pakai **edge-tts** (suara Indonesia natural),
dengan fallback ke gTTS bila gagal. Butuh **ffmpeg** (`ffplay`) di sistem dan
koneksi internet.

- Matikan suara (mode teks saja): `VOICE_ENABLED=0 python agent.py`
- Ganti suara: `VOICE_NAME=id-ID-GadisNeural python agent.py` (wanita) /
  `id-ID-ArdiNeural` (pria, default)
- Tes suara saja: `python voice.py`
- Saat narasi suara terlalu panjang, tekan **Ctrl+C** sekali untuk melewatinya
  (agent tetap jalan).

## Suara masuk / STT (Fase 3)

Saat program berjalan, ketik `v` lalu ENTER untuk memberi perintah dengan suara
(push-to-talk: ENTER mulai bicara, ENTER lagi berhenti). Butuh **mikrofon** &
PortAudio. Model Whisper berjalan lokal/offline.

- Ganti ukuran model: `WHISPER_MODEL=base python agent.py`
  (pilihan: tiny / base / small / medium / large-v3 — makin besar makin akurat
  tapi makin berat. Default `small`.)
- Tes mic saja: `python listen.py`

## Cara menjalankan (Fase 1)

```bash
# 1. (disarankan) buat virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. install dependensi
pip install -r requirements.txt

# 3. siapkan API key
cp .env.example .env
#   lalu edit .env, isi DASHSCOPE_API_KEY (key Qwen Model Studio) kamu

# 4. jalankan
python agent.py
```

Lalu ketik perintah, misalnya:
- "Lihat ada file apa saja di folder ini"
- "Buatkan script python untuk menghitung bilangan prima"
- "Jalankan test-nya dan beri tahu hasilnya"

## Keamanan

- Semua operasi file dibatasi di dalam folder kerja.
- Menulis file & menjalankan command selalu minta konfirmasi `[y/N]` dulu.
