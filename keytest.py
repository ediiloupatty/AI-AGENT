#!/usr/bin/env python3
"""Diagnostik tombol: cek apakah terminal bisa baca tombol satu-per-satu.

Jalankan:  python keytest.py
Lalu tekan: ↑  ↓  ENTER  lalu  q (untuk keluar).
Tempelkan SELURUH output ke chat.
"""
import sys

print("== KEYTEST ==")
print("python      :", sys.version.split()[0])
print("stdin.isatty:", sys.stdin.isatty())
print("stdout.isatty:", sys.stdout.isatty())
print("platform    :", sys.platform)

try:
    import termios, tty, select
    print("termios/tty : OK (tersedia)")
except Exception as e:
    print("termios/tty : GAGAL ->", e)
    sys.exit(1)

if not sys.stdin.isatty():
    print("\n!! stdin BUKAN TTY — navigasi panah memang tidak akan bisa di sini.")
    print("   (Mungkin dijalankan lewat pipe / IDE / wrapper non-interaktif.)")
    sys.exit(2)

fd = sys.stdin.fileno()
old = termios.tcgetattr(fd)
print("\nTekan: ↑  ↓  ENTER  lalu  q untuk berhenti.\n")
try:
    tty.setcbreak(fd)
    n = 0
    while n < 12:
        ch = sys.stdin.read(1)
        seq = [ch]
        # kalau ESC, baca 2 byte lanjutan secara BLOCKING (panah = ESC [ A).
        # Menunggu byte berikutnya — andal walau terminal mengirimnya lambat.
        if ch == "\x1b":
            seq.append(sys.stdin.read(1))
            if seq[1] in ("[", "O"):
                seq.append(sys.stdin.read(1))
        raw = "".join(seq)
        label = {
            "\x1b[A": "UP ↑", "\x1b[B": "DOWN ↓",
            "\x1b[C": "RIGHT →", "\x1b[D": "LEFT ←",
            "\r": "ENTER", "\n": "ENTER", "\x1b": "ESC", "q": "q (keluar)",
        }.get(raw, "?")
        print(f"  baca: {raw!r:<12} -> {label}")
        n += 1
        if raw == "q":
            break
finally:
    termios.tcsetattr(fd, termios.TCSADRAIN, old)
    print("\n== selesai ==")
