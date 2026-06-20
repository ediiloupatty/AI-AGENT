# ============================================================================
#  install-voice.ps1 — Pasang SIDECAR SUARA Voca di Windows (STT + TTS + VAD).
#
#  Binary inti (perintah `voca`) sudah dipasang oleh install.ps1 / install.bat
#  (mode teks). Script ini menambah kemampuan NGOMONG: Whisper (dengar) +
#  Piper (suara) + Silero VAD, lalu menyetel env var agar `voca` menemukannya.
#
#  Pakai (PowerShell):
#    irm https://raw.githubusercontent.com/ediiloupatty/voice-coding-assistant/main/install-voice.ps1 | iex
#
#  Prasyarat: Python 3.10+ dan Git terpasang di PATH.
#  Override: VOCA_HOME (folder sidecar, default %USERPROFILE%\.voca).
#  Unduhan: ~300MB (torch CPU + model Whisper saat pertama jalan + model Piper).
# ============================================================================
$ErrorActionPreference = "Stop"

$REPO     = "ediiloupatty/voice-coding-assistant"
$VOCA_HOME = if ($env:VOCA_HOME) { $env:VOCA_HOME } else { Join-Path $env:USERPROFILE ".voca" }
$VENV     = Join-Path $VOCA_HOME ".venv"
$PYEXE    = Join-Path $VENV "Scripts\python.exe"
$MODELS   = Join-Path $VOCA_HOME "models"

function Say  ($m) { Write-Host $m -ForegroundColor Cyan }
function Ok   ($m) { Write-Host $m -ForegroundColor Green }
function Warn ($m) { Write-Host "! $m" -ForegroundColor Yellow }
function Die  ($m) { Write-Host "x $m" -ForegroundColor Red; exit 1 }

Write-Host "==========================================="
Write-Host "  Memasang sidecar suara Voca (ngomong)"
Write-Host "==========================================="

# --- 1) Prasyarat: Python + Git -------------------------------------------
$py = $null
foreach ($c in @("python", "py")) {
  if (Get-Command $c -ErrorAction SilentlyContinue) { $py = $c; break }
}
if (-not $py) { Die "Python tak ditemukan. Pasang Python 3.10+ dari https://python.org lalu ulangi." }
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Die "Git tak ditemukan. Pasang Git dari https://git-scm.com lalu ulangi." }

# --- 2) Ambil kode (paket Python 'voca') ----------------------------------
if (Test-Path (Join-Path $VOCA_HOME ".git")) {
  Say "Memperbarui kode di $VOCA_HOME ..."
  git -C $VOCA_HOME fetch --depth 1 origin main
  git -C $VOCA_HOME reset --hard origin/main   # selalu samakan dgn remote (riwayat bisa di-rewrite)
} else {
  Say "Mengunduh kode ke $VOCA_HOME ..."
  if (Test-Path $VOCA_HOME) { Remove-Item -Recurse -Force $VOCA_HOME }
  git clone --depth 1 "https://github.com/$REPO.git" $VOCA_HOME
}

# --- 3) Virtualenv + dependensi -------------------------------------------
Say "Menyiapkan virtualenv (bisa beberapa menit)..."
& $py -m venv $VENV
& $PYEXE -m pip install --upgrade pip --quiet
Say "  Memasang Whisper (STT) + Piper (TTS) + audio..."
& $PYEXE -m pip install --quiet faster-whisper piper-tts sounddevice numpy python-dotenv
Say "  Memasang VAD Silero (torch CPU, ~200MB)..."
& $PYEXE -m pip install --quiet torch torchaudio --index-url https://download.pytorch.org/whl/cpu
& $PYEXE -m pip install --quiet silero-vad

# --- 4) Model suara Piper (id + en) ---------------------------------------
Say "Mengunduh model suara Piper (~120MB)..."
New-Item -ItemType Directory -Force -Path $MODELS | Out-Null
$PB = "https://huggingface.co/rhasspy/piper-voices/resolve/main"
$files = @{
  "$PB/id/id_ID/news_tts/medium/id_ID-news_tts-medium.onnx"      = "id_ID-news_tts-medium.onnx"
  "$PB/id/id_ID/news_tts/medium/id_ID-news_tts-medium.onnx.json" = "id_ID-news_tts-medium.onnx.json"
  "$PB/en/en_US/amy/medium/en_US-amy-medium.onnx"                = "en_US-amy-medium.onnx"
  "$PB/en/en_US/amy/medium/en_US-amy-medium.onnx.json"           = "en_US-amy-medium.onnx.json"
}
foreach ($url in $files.Keys) {
  $dest = Join-Path $MODELS $files[$url]
  curl.exe -fsSL $url -o $dest
}

# --- 5) Setel env var agar `voca` menemukan sidecar -----------------------
[Environment]::SetEnvironmentVariable("VOCA_VOICE_PYTHON", $PYEXE,     "User")
[Environment]::SetEnvironmentVariable("VOCA_VOICE_HOME",   $VOCA_HOME, "User")

Write-Host ""
Ok "==========================================="
Ok " Sidecar suara siap di $VOCA_HOME"
Ok "==========================================="
Write-Host "  Tutup PowerShell ini, buka terminal BARU, lalu jalankan:  voca"
Write-Host "  (kini hands-free: tinggal ngomong, tekan t untuk ketik)"
Write-Host "  Ganti bahasa suara: /lan id  atau  /lan en"
Warn "Opsional: pasang ffmpeg agar pitch-shift suara aktif (tanpa itu suara tetap jalan)."
