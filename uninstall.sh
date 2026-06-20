#!/usr/bin/env bash
#
# uninstall.sh — Hapus Voca dari Linux/macOS (BERSIH TOTAL).
#
#   curl -fsSL https://raw.githubusercontent.com/ediiloupatty/voice-coding-assistant/main/uninstall.sh | bash
#
# Menghapus: binary, sidecar suara (uv+Python+venv+model), config (API key &
# folder tepercaya), cache/log, dan baris export di shell rc.
# Override path: VOCA_INSTALL_DIR, VOCA_HOME.
set -euo pipefail

BIN_DIR="${VOCA_INSTALL_DIR:-$HOME/.local/bin}"
VOCA_HOME="${VOCA_HOME:-$HOME/.voca}"
CFG="${XDG_CONFIG_HOME:-$HOME/.config}/voca"
CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/voca"

say()  { printf '\033[1;36m%s\033[0m\n' "$*"; }
ok()   { printf '\033[1;32m%s\033[0m\n' "$*"; }

say "Akan menghapus Voca:"
echo "  - Binary : $BIN_DIR/voca"
echo "  - Suara  : $VOCA_HOME  (uv, Python, venv, model)"
echo "  - Config : $CFG   (API key & folder tepercaya)"
echo "  - Cache  : $CACHE"
echo "  - Baris export VOCA_VOICE_PYTHON / VOCA_VOICE_HOME di shell rc"
printf "Lanjut hapus SEMUA? (y/N) "
read -r ans </dev/tty || ans=""
case "$ans" in y|Y) ;; *) echo "Dibatalkan."; exit 0 ;; esac

rm -f  "$BIN_DIR/voca"
rm -rf "$VOCA_HOME" "$CFG" "$CACHE"

# Buang baris export yang ditambahkan installer dari shell rc (backup .voca-bak).
for f in "$HOME/.zshrc" "$HOME/.bashrc" "$HOME/.profile"; do
  [ -f "$f" ] || continue
  if grep -qE 'VOCA_VOICE_PYTHON|VOCA_VOICE_HOME' "$f"; then
    sed -i.voca-bak '/VOCA_VOICE_PYTHON/d; /VOCA_VOICE_HOME/d' "$f"
  fi
done

ok "Voca terhapus bersih. Buka terminal baru (atau 'source' shell rc) agar env ter-refresh."
echo "  (Catatan: baris PATH '\$HOME/.local/bin' tidak dihapus karena lazim dipakai tool lain.)"
