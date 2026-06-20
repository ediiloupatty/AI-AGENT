# ============================================================================
#  install.ps1 — Pemasang LENGKAP Voca di Windows (1 perintah, pengalaman 1:1).
#
#    irm https://raw.githubusercontent.com/ediiloupatty/voice-coding-assistant/main/install.ps1 | iex
#
#  Dengan bar progres 1-100%:
#    • Binary inti (Rust) → perintah `voca`  (mode teks: NOL prasyarat)
#    • Fitur SUARA (Whisper + Piper + Silero). Python dipasang OTOMATIS bila
#      belum ada (winget → fallback installer resmi python.org, per-user, tanpa
#      admin). TIDAK butuh Git — source diambil via ZIP.
#    • Model suara id + en, lalu minta API key, lalu jalankan `voca` DI SINI
#      (tanpa membuka window baru).
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

# Cari interpreter Python yang valid (hindari stub Microsoft Store yang kosong).
function Find-Python {
  foreach ($c in @("python", "py")) {
    if (Get-Command $c -ErrorAction SilentlyContinue) {
      try { $v = (& $c --version) 2>&1 | Out-String } catch { $v = "" }
      if ($v -match "Python 3\.\d") { return $c }
    }
  }
  $f = Get-ChildItem "$env:LOCALAPPDATA\Programs\Python\Python3*\python.exe" -ErrorAction SilentlyContinue |
       Sort-Object FullName -Descending | Select-Object -First 1
  if ($f) { return $f.FullName }
  return $null
}

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

# ── 2) Suara (Python dipasang otomatis bila perlu; tanpa Git) ───────────────
$voice = $false
if ($env:VOCA_NO_VOICE -eq "1") {
  Step 18 "Melewati suara (VOCA_NO_VOICE=1)."
} else {
  try {
    $py = Find-Python
    if (-not $py) {
      Step 22 "Python belum ada — memasang otomatis (sekali, 1-2 menit)..."
      if (Get-Command winget -ErrorAction SilentlyContinue) {
        winget install -e --id Python.Python.3.12 --scope user --silent `
          --accept-package-agreements --accept-source-agreements *>$null
      } else {
        $pyinst = Join-Path $env:TEMP "python-setup.exe"
        curl.exe -fsSL "https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe" -o $pyinst
        Start-Process -FilePath $pyinst -ArgumentList "/quiet","InstallAllUsers=0","PrependPath=1","Include_pip=1" -Wait
      }
      $py = Find-Python
    }
    if (-not $py) { throw "Python tak bisa dipasang otomatis — pasang manual dari python.org lalu jalankan ulang." }

    Step 30 "Mengambil kode suara (ZIP, tanpa Git)..."
    New-Item -ItemType Directory -Force -Path $home_ | Out-Null
    $zip = Join-Path $env:TEMP "voca-src.zip"
    $ex  = Join-Path $env:TEMP "voca-src"
    if (Test-Path $ex) { Remove-Item -Recurse -Force $ex }
    curl.exe -fsSL "https://github.com/$repo/archive/refs/heads/main.zip" -o $zip
    Expand-Archive $zip -DestinationPath $ex -Force
    Copy-Item -Path (Join-Path $ex "voice-coding-assistant-main\*") -Destination $home_ -Recurse -Force

    $venv  = Join-Path $home_ ".venv"
    $pyexe = Join-Path $venv "Scripts\python.exe"
    Step 40 "Membuat virtualenv..."
    & $py -m venv $venv
    & $pyexe -m pip install --upgrade pip --quiet

    Step 55 "Memasang Whisper (dengar) + Piper (suara)..."
    & $pyexe -m pip install --quiet faster-whisper piper-tts sounddevice numpy python-dotenv

    Step 72 "Memasang VAD Silero (torch CPU, ~200MB)..."
    & $pyexe -m pip install --quiet torch torchaudio --index-url https://download.pytorch.org/whl/cpu
    & $pyexe -m pip install --quiet silero-vad

    Step 86 "Mengunduh model suara (id + en, ~120MB)..."
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

    [Environment]::SetEnvironmentVariable("VOCA_VOICE_PYTHON", $pyexe, "User")
    [Environment]::SetEnvironmentVariable("VOCA_VOICE_HOME",   $home_, "User")
    $env:VOCA_VOICE_PYTHON = $pyexe; $env:VOCA_VOICE_HOME = $home_
    $voice = $true
  } catch {
    Write-Host "  ! Setup suara gagal: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host "  ! Lanjut mode teks. Untuk coba lagi: jalankan ulang perintah install." -ForegroundColor Yellow
  }
}

# ── 3) API key (sekali; voca tak nanya lagi kalau diisi) ────────────────────
Step 95 "Hampir selesai — API key."
Write-Progress -Activity $ACT -Completed
Write-Host ""
Write-Host "===========================================" -ForegroundColor Green
Write-Host (" Voca terpasang" + $(if ($voice) { " + suara siap (hands-free)" } else { " (mode teks)" })) -ForegroundColor Green
Write-Host "===========================================" -ForegroundColor Green
Write-Host "Tempel API key Qwen / DashScope (daftar gratis: https://dashscope.aliyun.com)"
$key = Read-Host "API Key (sk-...)"
if ($key -and $key.Trim()) {
  [Environment]::SetEnvironmentVariable("DASHSCOPE_API_KEY", $key.Trim(), "User")
  $env:DASHSCOPE_API_KEY = $key.Trim()
  Note "API key tersimpan."
} else {
  Note "Dilewati — voca akan meminta API key saat pertama dijalankan."
}

# ── 4) Reload di tempat (tanpa window baru) ─────────────────────────────────
Write-Host ""
Write-Host "Ganti bahasa kapan saja: /lan id  atau  /lan en" -ForegroundColor DarkGray
$ans = Read-Host "Tekan R lalu Enter untuk jalankan 'voca' sekarang DI SINI, atau Enter untuk keluar"
if ($ans -match '^(r|R)') {
  & $dest    # jalan di terminal yang SAMA — bukan window baru
} else {
  Write-Host "Selesai. Ketik 'voca' kapan saja (terminal ini sudah siap)." -ForegroundColor Green
}
