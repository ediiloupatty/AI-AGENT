# ============================================================================
#  install.ps1 — Pemasang LENGKAP Voca di Windows (1 perintah, pengalaman 1:1).
#
#    irm https://raw.githubusercontent.com/ediiloupatty/voice-coding-assistant/main/install.ps1 | iex
#
#  Dengan bar progres 1-100%:
#    • Binary inti (Rust) → perintah `voca`  (mode teks: NOL prasyarat)
#    • Fitur SUARA (Whisper + Piper + Silero). TIDAK memasang apa pun ke sistem:
#      Python dikelola `uv` dan DIBUNGKUS di dalam folder project (%USERPROFILE%\.voca).
#      Hapus folder itu → mesin bersih total (tak ada Python/Git nyangkut di sistem).
#    • Urutan: binary → PILIH penyedia model + API key (di awal) → unduh suara
#      (id + en) yang berjalan tanpa menunggu kamu → 1 TAP untuk jalan (tanpa Enter).
#
#  Override: $env:VOCA_BASE_URL, $env:VOCA_INSTALL_DIR, $env:VOCA_HOME,
#            $env:VOCA_NO_VOICE=1 (lewati suara → mode teks saja).
# ============================================================================
$ErrorActionPreference = "Stop"
$ProgressPreference    = "Continue"

$repo  = "ediiloupatty/voice-coding-assistant"
$base  = if ($env:VOCA_BASE_URL)    { $env:VOCA_BASE_URL }    else { "https://github.com/$repo/releases/latest/download" }
$dir   = if ($env:VOCA_INSTALL_DIR) { $env:VOCA_INSTALL_DIR } else { Join-Path $env:LOCALAPPDATA "Voca" }
$home_ = if ($env:VOCA_HOME)        { $env:VOCA_HOME }        else { Join-Path $env:USERPROFILE ".voca" }
$dest  = Join-Path $dir "voca.exe"

$ACT = "Memasang Voca"
function Step($pct, $msg) { Write-Progress -Activity $ACT -Status $msg -PercentComplete $pct }
function Note($m) { Write-Host "  $m" -ForegroundColor DarkGray }

# ── 1) Binary inti (Rust) — mode teks, nol prasyarat ────────────────────────
Step 5 "Menyiapkan folder..."
New-Item -ItemType Directory -Force -Path $dir | Out-Null
Step 12 "Mengunduh binary inti (voca.exe)..."
curl.exe -fsSL "$base/voca-windows-x64.exe" -o $dest
if (-not (Test-Path $dest)) { Write-Progress -Activity $ACT -Completed; throw "Gagal mengunduh binary dari $base" }

Step 16 "Menambahkan ke PATH..."
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$dir*") { [Environment]::SetEnvironmentVariable("Path", "$userPath;$dir", "User") }
if (";$env:Path;" -notlike "*;$dir;*") { $env:Path = "$env:Path;$dir" }   # sesi ini juga → tak perlu window baru

# ── 2) Penyedia model AI + API key (DI AWAL) ────────────────────────────────
# Diminta lebih dulu — sebelum unduhan suara yang lama — supaya kamu cukup
# menempel key sekali, lalu boleh tinggal: bagian berat berjalan tanpa nungguin.
# Bebas pilih provider; bisa diganti kapan saja di dalam app lewat /model.
Step 18 "Memilih penyedia model AI..."
Write-Progress -Activity $ACT -Completed   # jeda bar agar prompt rapi
Write-Host ""
Write-Host "Pilih penyedia model AI (bisa diganti kapan saja di app: /model):" -ForegroundColor Cyan
Write-Host "   [1] Qwen / DashScope   (default — https://dashscope.aliyun.com)"
Write-Host "   [2] OpenAI / ChatGPT   (https://platform.openai.com/api-keys)"
Write-Host "   [3] OpenRouter         (banyak model, ada gratis — https://openrouter.ai/keys)"
Write-Host "   [4] DeepSeek           (https://platform.deepseek.com)"
Write-Host "   [5] Google Gemini      (https://aistudio.google.com/apikey)"
Write-Host "   [6] Anthropic Claude   (https://console.anthropic.com)"
Write-Host "   [7] xAI Grok           (https://console.x.ai)"
Write-Host "   [8] Groq  (cepat)      (https://console.groq.com/keys)"
Write-Host "   [9] Mistral            (https://console.mistral.ai)"
Write-Host "  [10] Together AI        (https://api.together.xyz)"
Write-Host "  [11] Perplexity         (https://perplexity.ai/settings/api)"
Write-Host "  [12] Cerebras (cepat)   (https://cloud.cerebras.ai)"
Write-Host "  [13] Fireworks          (https://fireworks.ai)"
Write-Host "  [14] MiniMax  (coding)  (https://platform.minimax.io)"
Write-Host "  [15] Moonshot Kimi      (coding — https://platform.moonshot.ai)"
Write-Host "  [16] Zhipu GLM          (coding, murah — https://z.ai)"
Write-Host "  [17] SambaNova (cepat)  (https://cloud.sambanova.ai)"
Write-Host "  [18] NVIDIA NIM (gratis)(https://build.nvidia.com)"
Write-Host "  [19] GitHub Models(grts)(https://github.com/marketplace/models)"
Write-Host "  [20] Ollama   (LOKAL, gratis, tanpa key — https://ollama.com)"
Write-Host "  [21] LM Studio (LOKAL, gratis, tanpa key — https://lmstudio.ai)"
$sel = Read-Host "Nomor [Enter = 1]"
switch ($sel.Trim()) {
  "2"     { $provCode = "openai";     $keyVar = "OPENAI_API_KEY";     $provName = "OpenAI" }
  "3"     { $provCode = "openrouter"; $keyVar = "OPENROUTER_API_KEY"; $provName = "OpenRouter" }
  "4"     { $provCode = "deepseek";   $keyVar = "DEEPSEEK_API_KEY";   $provName = "DeepSeek" }
  "5"     { $provCode = "gemini";     $keyVar = "GEMINI_API_KEY";     $provName = "Gemini" }
  "6"     { $provCode = "claude";     $keyVar = "ANTHROPIC_API_KEY";  $provName = "Claude" }
  "7"     { $provCode = "grok";       $keyVar = "XAI_API_KEY";        $provName = "xAI Grok" }
  "8"     { $provCode = "groq";       $keyVar = "GROQ_API_KEY";       $provName = "Groq" }
  "9"     { $provCode = "mistral";    $keyVar = "MISTRAL_API_KEY";    $provName = "Mistral" }
  "10"    { $provCode = "together";   $keyVar = "TOGETHER_API_KEY";   $provName = "Together AI" }
  "11"    { $provCode = "perplexity"; $keyVar = "PERPLEXITY_API_KEY"; $provName = "Perplexity" }
  "12"    { $provCode = "cerebras";   $keyVar = "CEREBRAS_API_KEY";   $provName = "Cerebras" }
  "13"    { $provCode = "fireworks";  $keyVar = "FIREWORKS_API_KEY";  $provName = "Fireworks" }
  "14"    { $provCode = "minimax";    $keyVar = "MINIMAX_API_KEY";    $provName = "MiniMax" }
  "15"    { $provCode = "kimi";       $keyVar = "MOONSHOT_API_KEY";   $provName = "Moonshot Kimi" }
  "16"    { $provCode = "glm";        $keyVar = "ZAI_API_KEY";        $provName = "Zhipu GLM" }
  "17"    { $provCode = "sambanova";  $keyVar = "SAMBANOVA_API_KEY";  $provName = "SambaNova" }
  "18"    { $provCode = "nvidia";     $keyVar = "NVIDIA_API_KEY";     $provName = "NVIDIA NIM" }
  "19"    { $provCode = "github";     $keyVar = "GITHUB_MODELS_TOKEN"; $provName = "GitHub Models" }
  "20"    { $provCode = "ollama";     $keyVar = "OLLAMA_API_KEY";     $provName = "Ollama" }
  "21"    { $provCode = "lmstudio";   $keyVar = "LMSTUDIO_API_KEY";   $provName = "LM Studio" }
  default { $provCode = "qwen";       $keyVar = "DASHSCOPE_API_KEY";  $provName = "Qwen" }
}
# Pre-seed provider aktif (core baca VOCA_PROVIDER saat start → main.rs).
[Environment]::SetEnvironmentVariable("VOCA_PROVIDER", $provCode, "User")
$env:VOCA_PROVIDER = $provCode
if ($provCode -eq "ollama" -or $provCode -eq "lmstudio") {
  # Provider lokal: tak butuh API key — pastikan server lokalnya jalan.
  Note "$provName lokal — tanpa API key. Pastikan server '$provName' berjalan di mesin ini."
} else {
  Write-Host "Tempel API key $provName (kosongkan = diisi nanti saat pertama jalan)"
  $key = Read-Host "$provName API Key"
  if ($key -and $key.Trim()) {
    [Environment]::SetEnvironmentVariable($keyVar, $key.Trim(), "User")
    [Environment]::SetEnvironmentVariable($keyVar, $key.Trim(), "Process")
    Note "API key $provName tersimpan."
  } else {
    Note "Dilewati — voca akan meminta API key $provName saat pertama dijalankan."
  }
}

# ── 3) Suara — Python terisolasi (uv), TANPA menyentuh sistem & tanpa git ────
$voice = $false
if ($env:VOCA_NO_VOICE -eq "1") {
  Step 24 "Melewati suara (VOCA_NO_VOICE=1)."
} else {
  try {
    New-Item -ItemType Directory -Force -Path $home_ | Out-Null

    # Source paket Python 'voca' via ZIP (tanpa git). File source ditimpa,
    # .venv/ & python/ & models/ yang sudah ada tetap dipertahankan.
    Step 26 "Mengambil kode suara (ZIP, tanpa git)..."
    $zip = Join-Path $env:TEMP "voca-src.zip"
    $ex  = Join-Path $env:TEMP "voca-src"
    if (Test-Path $ex) { Remove-Item -Recurse -Force $ex }
    curl.exe -fsSL "https://github.com/$repo/archive/refs/heads/main.zip" -o $zip
    Expand-Archive $zip -DestinationPath $ex -Force
    Copy-Item -Path (Join-Path $ex "voice-coding-assistant-main\*") -Destination $home_ -Recurse -Force

    # uv = pengelola Python portabel (1 exe, tanpa deps). Python yang diunduhnya
    # DIBUNGKUS di $home_\python — bukan instalasi sistem, tak muncul di PATH/registry.
    Step 36 "Mengunduh uv (pengelola Python portabel)..."
    $bin = Join-Path $home_ "bin"; New-Item -ItemType Directory -Force -Path $bin | Out-Null
    $uvzip = Join-Path $env:TEMP "uv.zip"
    curl.exe -fsSL "https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip" -o $uvzip
    Expand-Archive $uvzip -DestinationPath $bin -Force
    $uv = Join-Path $bin "uv.exe"

    $env:UV_PYTHON_INSTALL_DIR = Join-Path $home_ "python"   # Python ter-scope ke project
    $env:UV_CACHE_DIR          = Join-Path $home_ ".cache"   # cache pun di dalam project
    $venv   = Join-Path $home_ ".venv"
    $venvpy = Join-Path $venv  "Scripts\python.exe"

    Step 46 "Menyiapkan Python terisolasi + virtualenv..."
    & $uv venv $venv --python 3.12 --python-preference only-managed

    # VAD Silero kini lewat onnxruntime (model dibundel di source: voca\silero_vad.onnx),
    # jadi TAK perlu torch (~1GB) lagi → install jauh lebih kecil & cepat.
    Step 68 "Memasang Whisper + Piper + VAD (onnxruntime) + audio..."
    & $uv pip install --python $venvpy faster-whisper piper-tts onnxruntime sounddevice numpy python-dotenv

    Step 88 "Mengunduh model suara (id + en, ~120MB)..."
    $models = Join-Path $home_ "models"
    New-Item -ItemType Directory -Force -Path $models | Out-Null
    $PB = "https://huggingface.co/rhasspy/piper-voices/resolve/main"
    $files = @{
      "$PB/id/id_ID/news_tts/medium/id_ID-news_tts-medium.onnx"      = "id_ID-news_tts-medium.onnx"
      "$PB/id/id_ID/news_tts/medium/id_ID-news_tts-medium.onnx.json" = "id_ID-news_tts-medium.onnx.json"
      "$PB/en/en_US/amy/medium/en_US-amy-medium.onnx"                = "en_US-amy-medium.onnx"
      "$PB/en/en_US/amy/medium/en_US-amy-medium.onnx.json"           = "en_US-amy-medium.onnx.json"
    }
    foreach ($url in $files.Keys) { curl.exe -fsSL $url -o (Join-Path $models $files[$url]) }

    [Environment]::SetEnvironmentVariable("VOCA_VOICE_PYTHON", $venvpy, "User")
    [Environment]::SetEnvironmentVariable("VOCA_VOICE_HOME",   $home_,  "User")
    $env:VOCA_VOICE_PYTHON = $venvpy; $env:VOCA_VOICE_HOME = $home_
    $voice = $true
  } catch {
    Write-Host "  ! Setup suara gagal: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host "  ! Lanjut mode teks. Untuk coba lagi: jalankan ulang perintah install." -ForegroundColor Yellow
  }
}

# ── 4) Selesai + jalan (1 TAP, tanpa Enter) ─────────────────────────────────
Step 96 "Selesai."
Write-Progress -Activity $ACT -Completed
Write-Host ""
Write-Host "===========================================" -ForegroundColor Green
Write-Host (" Voca terpasang" + $(if ($voice) { " + suara siap (hands-free)" } else { " (mode teks)" })) -ForegroundColor Green
Write-Host "===========================================" -ForegroundColor Green
Write-Host "Ganti model kapan saja: /model    |    ganti bahasa: /lan id  /lan en" -ForegroundColor DarkGray
Write-Host ""
Write-Host "Tekan tombol apa saja untuk menjalankan 'voca' sekarang  (Q = keluar)..." -ForegroundColor Cyan
try {
  $k = [System.Console]::ReadKey($true)            # 1 tombol, TANPA Enter
  $quit = ($k.Key -eq 'Q' -or $k.Key -eq 'Escape')
} catch {
  # Host langka tanpa ReadKey → fallback yang butuh Enter.
  $quit = ((Read-Host "Enter = jalan, Q = keluar") -match '^[qQ]')
}
if ($quit) {
  Write-Host "Selesai. Ketik 'voca' kapan saja (terminal ini sudah siap)." -ForegroundColor Green
} else {
  & $dest    # jalan di terminal yang SAMA — bukan window baru
}
