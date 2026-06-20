# install.ps1 — pemasang Voca core (Rust) di Windows:
#   irm https://raw.githubusercontent.com/ediiloupatty/voice-coding-assistant/main/install.ps1 | iex
#
# Override: $env:VOCA_BASE_URL (sumber binary), $env:VOCA_INSTALL_DIR (folder).
# Catatan: mode suara (ngomong) butuh sidecar Python. Pasang dengan:
#   irm https://raw.githubusercontent.com/ediiloupatty/voice-coding-assistant/main/install-voice.ps1 | iex
$ErrorActionPreference = "Stop"

$repo = "ediiloupatty/voice-coding-assistant"
$base = if ($env:VOCA_BASE_URL) { $env:VOCA_BASE_URL }
        else { "https://github.com/$repo/releases/latest/download" }
$dir  = if ($env:VOCA_INSTALL_DIR) { $env:VOCA_INSTALL_DIR }
        else { Join-Path $env:LOCALAPPDATA "Voca" }

$asset = "voca-windows-x64.exe"
$dest  = Join-Path $dir "voca.exe"

New-Item -ItemType Directory -Force -Path $dir | Out-Null
Write-Host "Mengunduh Voca core ($asset)..."
Invoke-WebRequest "$base/$asset" -OutFile $dest

$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$dir*") {
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$dir", "User")
    Write-Host "PATH user diperbarui. Buka terminal BARU agar 'voca' aktif."
}

Write-Host "Selesai. Jalankan: voca"
Write-Host "  (API key diminta otomatis saat pertama dijalankan)"
Write-Host "  Mau ngomong (mode suara)? Jalankan:"
Write-Host "    irm https://raw.githubusercontent.com/$repo/main/install-voice.ps1 | iex"
