# ============================================================================
#  uninstall.ps1 — Hapus Voca dari Windows (BERSIH TOTAL).
#
#    irm https://raw.githubusercontent.com/ediiloupatty/voice-coding-assistant/main/uninstall.ps1 | iex
#
#  Menghapus: binary, sidecar suara (uv+Python+venv+model), config (API key &
#  daftar folder tepercaya), entri PATH, dan env var user. Tak menyisakan jejak.
#  Override path lewat: $env:VOCA_INSTALL_DIR, $env:VOCA_HOME.
# ============================================================================
$ErrorActionPreference = "Stop"

$dir   = if ($env:VOCA_INSTALL_DIR) { $env:VOCA_INSTALL_DIR } else { Join-Path $env:LOCALAPPDATA "Voca" }
$home_ = if ($env:VOCA_HOME)        { $env:VOCA_HOME }        else { Join-Path $env:USERPROFILE ".voca" }
$cfg   = Join-Path $env:APPDATA "voca"

Write-Host "Akan menghapus Voca:" -ForegroundColor Yellow
Write-Host "  - Binary : $dir"
Write-Host "  - Suara  : $home_  (uv, Python, venv, model)"
Write-Host "  - Config : $cfg  (API key & folder tepercaya)"
Write-Host "  - Entri PATH user + env var (VOCA_VOICE_PYTHON, VOCA_VOICE_HOME, DASHSCOPE_API_KEY)"
$ans = Read-Host "Lanjut hapus SEMUA? (y/N)"
if ($ans -notmatch '^(y|Y)') { Write-Host "Dibatalkan."; return }

foreach ($p in @($dir, $home_, $cfg)) {
  if (Test-Path $p) {
    try { Remove-Item -Recurse -Force $p; Write-Host "  dihapus: $p" -ForegroundColor Green }
    catch { Write-Host "  ! gagal hapus $p ($($_.Exception.Message)) — tutup 'voca' dulu lalu ulangi." -ForegroundColor Yellow }
  }
}

# Cabut folder binary dari PATH user (case-insensitive, abaikan slash akhir).
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath) {
  $keep = $userPath -split ';' | Where-Object { $_ -and ($_.TrimEnd('\') -ine $dir.TrimEnd('\')) }
  [Environment]::SetEnvironmentVariable("Path", ($keep -join ';'), "User")
}
# Hapus env var user.
foreach ($v in @("VOCA_VOICE_PYTHON", "VOCA_VOICE_HOME", "DASHSCOPE_API_KEY")) {
  [Environment]::SetEnvironmentVariable($v, $null, "User")
}

Write-Host ""
Write-Host "Voca terhapus bersih. Buka terminal BARU agar PATH/env ter-refresh." -ForegroundColor Green
