"""
ui.py — Sistem desain & seluruh presentasi terminal Voca.

Semua hal yang berkaitan dengan TAMPILAN dikumpulkan di sini (warna, simbol,
banner, kolom input, bar status, spinner, prompt) supaya agent.py fokus ke
logika. Gaya: minimalis-modern, satu aksen (teal), garis tipis, banyak ruang.

Dua jalur render:
  - Rich (lewat `console`) untuk teks/markdown biasa — pakai nama style semantik.
  - ANSI mentah untuk drawing yang butuh kontrol kursor (kolom input full-width
    & bar status di scroll-region mode hands-free).
"""

import shutil
import sys
from pathlib import Path

# Modul baca-tombol berbeda per OS: termios/tty hanya ada di POSIX, msvcrt di Windows.
_IS_WINDOWS = sys.platform.startswith("win")
if _IS_WINDOWS:
    import msvcrt
else:
    import termios
    import tty

from rich.console import Console
from rich.prompt import Confirm
from rich.spinner import Spinner
from rich.text import Text
from rich.theme import Theme

from . import lang   # teks antarmuka ikut bahasa aktif (lang.t)

# ---------------------------------------------------------------------------
# Palet — ANSI mentah (untuk drawing scroll-region) + Rich Theme (untuk markup)
# ---------------------------------------------------------------------------
RESET = "\033[0m"
BOLD = "\033[1m"
NOBOLD = "\033[22m"
DIM = "\033[2m"

ACCENT = "\033[38;5;141m"     # Lavender / light purple - warna utama/brand
ACCENT_HI = "\033[38;5;51m"   # Neon cyan - warna judul & sorotan
MUTED = "\033[38;5;244m"      # Slate gray - teks sekunder/petunjuk
WARN = "\033[38;5;214m"       # Vibrant orange - proses/peringatan

# Kolom input abu-abu muda (TIDAK diubah — sesuai permintaan user).
BG_INPUT = "\033[48;5;254m"  # latar abu-abu muda
FG_INPUT = "\033[38;5;236m"  # teks gelap agar terbaca di atas abu-abu

# Style semantik untuk Rich. Pakai color(N) agar sama persis dgn ANSI 256 di atas.
THEME = Theme({
    "accent":        "color(141)",
    "accent.hi":     "color(51)",
    "muted":         "color(244)",
    "success":       "color(48)",
    "warn":          "color(214)",
    "error":         "color(197)",
    "rule.line":     "color(141)",
    "markdown.code": "bold color(51)",   # inline `code` — tanpa background gelap
})

console = Console(theme=THEME)

# ---------------------------------------------------------------------------
# Simbol (bukan emoji — aman dgn aturan no-emoji)
# ---------------------------------------------------------------------------
SIGIL = "◆"    # penanda brand Voca
PROMPT = "›"   # prompt input
TOOL = "▸"     # baris pemanggilan tool
RULE = "─"     # garis pemisah tipis
DOT = "·"      # pemisah antar-info
ASK = "?"      # tanda tanya konfirmasi
ERR = "✕"      # tanda error


# ---------------------------------------------------------------------------
# Util kecil
# ---------------------------------------------------------------------------
def _pendekkan(teks: str, maks: int) -> str:
    """Pangkas teks panjang dari depan, sisakan ekornya (mis. path)."""
    return teks if len(teks) <= maks else "…" + teks[-(maks - 1):]


def _colhome(path) -> str:
    """Ganti $HOME di awal path dengan '~' biar ringkas."""
    s = str(path)
    try:
        home = str(Path.home())
        if s.startswith(home):
            return "~" + s[len(home):]
    except Exception:
        pass
    return s


def _lebar() -> int:
    return shutil.get_terminal_size().columns


# ---------------------------------------------------------------------------
# Komponen statis (Rich)
# ---------------------------------------------------------------------------
def banner(model: str, workspace, mode: str, bahasa: str | None = None) -> None:
    """Banner pembuka minimalis: garis pemisah horizontal selebar penuh terminal."""
    W = _lebar()
    ws = _pendekkan(_colhome(workspace), W)
    garis = f"[accent]{RULE * W}[/]"

    logo = "[bold color(51)]V[/] [bold color(81)]O[/] [bold color(141)]C[/] [bold color(201)]A[/]"

    console.print()
    console.print(garis)
    console.print(f" {logo}  [muted]{lang.t('subtitle')}[/]")
    console.print(garis)

    # Info lines (label ikut bahasa aktif; bahasa opsional)
    info = [(lang.t("lbl_model"), model), (lang.t("lbl_lang"), bahasa),
            (lang.t("lbl_folder"), ws), (lang.t("lbl_mode"), mode)]
    for label, val in info:
        if val is None:
            continue
        console.print(f" [muted]{label:<8} :[/] {val}")

    console.print(garis)
    console.print()


def hint(teks: str) -> None:
    """Satu baris petunjuk redup di bawah banner."""
    console.print(f"[muted]{teks}[/]\n")


def info(teks: str) -> None:
    """Baris info redup (status ringan, mis. 'Sesi dilanjutkan')."""
    console.print(f"[muted]{teks}[/]")


def error(msg) -> None:
    """Baris error yang bersih: ✕ pesan."""
    console.print(f"\n[error]{ERR}[/] {msg}")


def selesai(teks: str = "sampai jumpa") -> None:
    """Baris penutup."""
    console.print(f"\n[muted]{SIGIL} {teks}[/]")


def header_jawaban() -> None:
    """Penanda di atas tiap jawaban asisten: '◆ Voca'."""
    console.print(f"\n[accent.hi]{SIGIL}[/] [bold accent.hi]Voca[/] [muted]· AI Assistant[/]")


def baris_tool(nama: str, ringkas: str) -> None:
    """Baris pemanggilan tool dengan ikon kilat modern."""
    sep = f" [muted]{DOT}[/] " if ringkas else ""
    console.print(f"  [accent.hi]⚡[/] [bold accent]{nama}[/]{sep}[muted]{ringkas}[/]")


def spinner_berpikir(teks: str = "berpikir…"):
    """Factory spinner 'sedang berpikir' (dipakai dgn rich.live.Live)."""
    return Spinner("dots", text=Text(teks, style="muted"), style="accent")


# ---------------------------------------------------------------------------
# Prompt & konfirmasi
# ---------------------------------------------------------------------------
def tanya_resume(giliran: int) -> bool:
    """Tanya user apakah mau lanjut dari sesi sebelumnya."""
    try:
        console.print()
        return Confirm.ask(
            f"[muted]Ada sesi sebelumnya ({giliran} giliran). Lanjutkan?[/]",
            default=False,
        )
    except (EOFError, KeyboardInterrupt):
        return False


def tanya_konfirmasi_suara(prompt: str) -> None:
    """Cetak pertanyaan konfirmasi (jawaban via suara ditangani pemanggil)."""
    console.print(f"\n[warn]{ASK}[/] {prompt}")


def konfirmasi_keyboard(prompt: str) -> bool:
    """Konfirmasi y/n via keyboard (handler default aksi yang mengubah sistem)."""
    try:
        console.print()
        return Confirm.ask(f"[warn]{ASK}[/] {prompt}", default=False)
    except (EOFError, KeyboardInterrupt):
        return False


# ---------------------------------------------------------------------------
# Kolom input abu-abu (ANSI mentah, full-width)
# ---------------------------------------------------------------------------
def _baris_input_grey(W: int) -> str:
    """Segmen ANSI: isi baris penuh abu-abu, balik ke awal, cetak prompt '›'."""
    return (
        f"{BG_INPUT}{FG_INPUT}{' ' * W}\r"     # latar abu-abu mentok kiri-kanan
        f"{BOLD}{ACCENT} {PROMPT} {NOBOLD}{FG_INPUT}"  # prompt aksen, lalu teks gelap
    )


def kotak_input(petunjuk: str = "") -> str:
    """Prompt input full-width: kolom abu-abu ujung-ke-ujung + padding atas/bawah."""
    W = _lebar()
    blank = f"{BG_INPUT}{' ' * W}{RESET}"
    try:
        console.print()
        if petunjuk:
            console.print(f"[muted]{petunjuk}[/]")
        print(blank, flush=True)                       # padding atas
        print(_baris_input_grey(W), end="", flush=True)
        teks = input()                                 # user mengetik di atas abu-abu
        print(blank, flush=True)                       # padding bawah
    except (EOFError, KeyboardInterrupt):
        print(RESET, end="", flush=True)
        raise
    print(RESET, end="", flush=True)                   # reset warna setelah Enter
    return teks.strip()


def pesan_user(teks: str) -> None:
    """Tampilkan ucapan/ketikan user dalam bar abu-abu full-width (echo)."""
    W = _lebar()
    blank = f"{BG_INPUT}{' ' * W}{RESET}"
    pad = " " * max(0, W - len(f" {PROMPT} {teks}"))
    print()
    print(blank, flush=True)                           # padding atas
    print(
        f"{BG_INPUT}{FG_INPUT}{BOLD}{ACCENT} {PROMPT} {NOBOLD}{FG_INPUT}{teks}{pad}{RESET}",
        flush=True,
    )
    print(blank, flush=True)                           # padding bawah


# ---------------------------------------------------------------------------
# Bar status bawah (mode hands-free, di dalam scroll-region)
# ---------------------------------------------------------------------------
# mode -> (warna_label, label, hint)
_BAR = {
    "dengerin":    (ACCENT,    "● SUARA",    f"bicara / ketik  {DOT}  /model  {DOT}  /lan  {DOT}  ^C keluar"),
    "transkripsi": (WARN,      "⏳ PROSES",   "memproses suara…"),
    "berpikir":    (ACCENT_HI, "🧠 BERPIKIR", "menyusun jawaban…"),
}


def status_bar(H: int, W: int, mode: str = "dengerin", bahasa: str = "") -> None:
    """Gambar bar status 3-baris paling bawah dengan lencana status ala web.

    mode: 'dengerin' (siap menerima) | 'transkripsi' | 'berpikir'.
    bahasa: kode bahasa aktif (mis. 'EN'/'ID') -> tampil di pojok kanan bawah.
    """
    warna, label, teks_hint = _BAR.get(mode, _BAR["dengerin"])

    # Reset warna dulu, lalu bersihkan dari H-2 ke bawah.
    print(f"{RESET}\033[{H-2};1H\033[J", end="", flush=True)
    # H-2: garis pemisah tipis (aksen redup).
    print(f"{DIM}{ACCENT}{RULE * (W - 1)}{RESET}", end="", flush=True)

    def _badge_bahasa():
        """Lencana bahasa aktif, rata kanan di baris H."""
        if not bahasa:
            return
        teks = f" lang: {bahasa} "
        col = max(1, W - len(teks))
        print(f"{RESET}\033[{H};{col}H{DIM}{ACCENT}{teks}{RESET}", end="", flush=True)

    if mode == "dengerin":
        # H-1: kolom input abu-abu (tempat user mengetik).
        print(f"\033[{H-1};1H{_baris_input_grey(W)}", end="", flush=True)
        # H: label mode + petunjuk.
        print(
            f"{RESET}\033[{H};1H {warna}{BOLD}{label}{RESET}  {MUTED}{teks_hint}{RESET}",
            end="", flush=True,
        )
        _badge_bahasa()
        # Aktifkan kembali abu-abu & taruh kursor di awal area ketik (kolom 4).
        print(f"\033[{H-1};4H{BG_INPUT}{FG_INPUT}", end="", flush=True)
    else:
        # Status (transkripsi/berpikir): tanpa kolom abu-abu.
        print(
            f"\033[{H-1};1H {warna}{BOLD}{PROMPT}{RESET}  {MUTED}{teks_hint}{RESET}",
            end="", flush=True,
        )
        print(f"\033[{H};1H {warna}{BOLD}{label}{RESET}", end="", flush=True)
        _badge_bahasa()
        print(f"\033[{H-1};4H", end="", flush=True)


# ---------------------------------------------------------------------------
# Layar terpisah (alternate screen buffer)
# ---------------------------------------------------------------------------
def _aktifkan_vt_windows() -> None:
    """Aktifkan pemrosesan escape-ANSI (VT) di konsol Windows lama (conhost).

    Windows Terminal modern sudah mendukung VT secara default, tapi conhost lama
    butuh ENABLE_VIRTUAL_TERMINAL_PROCESSING agar `\\033[...]` tak tampil mentah.
    Aman & no-op di mana pun selain Windows.
    """
    if not _IS_WINDOWS:
        return
    try:
        import ctypes
        k = ctypes.windll.kernel32
        k.SetConsoleMode(k.GetStdHandle(-11), 7)   # 7 = VT|PROCESSED|WRAP_AT_EOL
    except Exception:
        pass


def buka_layar() -> None:
    """Masuk ke 'layar baru' (alternate screen) seperti vim/htop/less.

    Isi terminal sebelumnya disembunyikan selama Voca jalan, lalu dikembalikan
    utuh saat Voca ditutup.

    - ?1049h : aktifkan alternate screen.
    - ?1007l : matikan 'alternate scroll' — supaya scroll mouse TIDAK dikirim
      sebagai tombol panah (kalau aktif, muncul ^[[A / ^[[B di kolom input).
    """
    _aktifkan_vt_windows()
    print("\033[?1049h\033[?1007l\033[2J\033[H", end="", flush=True)


def tutup_layar() -> None:
    """Keluar dari alternate screen: reset warna & scroll-region, pulihkan
    alternate scroll, lalu kembali ke layar terminal semula."""
    print("\033[0m\033[r\033[?1007h\033[?1049l", end="", flush=True)


def _baca_tombol() -> str:
    """Baca satu tombol dari keyboard tanpa ENTER. Lintas-OS.

    Windows: pakai msvcrt (panah datang sbg prefix \\x00/\\xe0 + kode).
    POSIX  : terminal HARUS sudah cbreak (lihat pilih_model). Sekuens panah
             (ESC '[' 'A') dibaca BLOCKING — di sebagian terminal byte-nya tiba
             dengan jeda tak menentu, jadi menunggu byte berikutnya jauh lebih
             andal daripada timeout. ESC murni tak dipakai utk batal → pakai 'q'.
    """
    if _IS_WINDOWS:
        ch = msvcrt.getwch()
        if ch in ('\x00', '\xe0'):     # prefix tombol khusus (panah, F-keys, dll)
            ch2 = msvcrt.getwch()
            return {'H': 'up', 'P': 'down', 'M': 'right', 'K': 'left'}.get(ch2, 'ignore')
        if ch in ('\r', '\n'):
            return 'enter'
        if ch == '\x03':               # Ctrl+C
            raise KeyboardInterrupt()
        if ch == '\x1b':
            return 'esc'
        return ch.lower()

    ch = sys.stdin.read(1)
    if ch == '\x1b':              # awal sekuens (panah dsb) — tunggu lanjutannya
        ch2 = sys.stdin.read(1)   # blocking: tahan berapa pun lambatnya byte tiba
        if ch2 in ('[', 'O'):
            ch3 = sys.stdin.read(1)
            return {'A': 'up', 'B': 'down', 'C': 'right', 'D': 'left'}.get(ch3, 'ignore')
        return 'ignore'
    if ch in ('\r', '\n'):
        return 'enter'
    if ch == '\x03':  # Ctrl+C
        raise KeyboardInterrupt()
    return ch.lower()


def _potong(s: str, n: int) -> str:
    """Potong string ke n kolom, sisipkan … bila kepanjangan."""
    return s if len(s) <= n else s[: max(0, n - 1)] + "…"


def _menu_interaktif(judul: str, jumlah: int, baris_fn, indeks_aktif: int = 0,
                     W: int = 58) -> int | None:
    """Menu panah ↑/↓ generik (dipakai pilih_model & pilih_bahasa).

    `baris_fn(i, aktif)` -> string MARKUP isi baris ke-i (DI DALAM │…│), sudah
    selebar W-2 kolom terlihat. Return indeks terpilih, atau None bila batal (q).

    Memakai Rich `Live` (full-frame redraw, pola TUI Ink di Claude/Gemini CLI) +
    `_baca_tombol` lintas-OS. Scroll-region mode hands-free dilepas sementara
    supaya Live bebas menggambar ulang.
    """
    from rich.live import Live
    from rich.console import Group

    if not _IS_WINDOWS:
        try:
            termios.tcflush(sys.stdin.fileno(), termios.TCIFLUSH)
        except Exception:
            pass

    indeks = indeks_aktif

    def _frame() -> "Group":
        garis = RULE * (W - len(judul) - 5)   # ╭─ {judul} …╮  -> total W kolom
        rows = [Text.from_markup(f"[accent]╭─[/][accent.hi] {judul} [/][accent]{garis}╮[/]")]
        for i in range(jumlah):
            rows.append(Text.from_markup(f"[accent]│[/]{baris_fn(i, i == indeks)}[accent]│[/]"))
        rows.append(Text.from_markup(f"[accent]╰{RULE * (W - 2)}╯[/]"))
        rows.append(Text.from_markup("[muted] ↑/↓ pindah  ·  ENTER pilih  ·  q batal[/]"))
        return Group(*rows)

    # POSIX: simpan setelan terminal & masuk cbreak (sekali) selama menu.
    # Windows: msvcrt.getwch() sudah membaca tombol tanpa echo, tak perlu setup.
    fd = None if _IS_WINDOWS else sys.stdin.fileno()
    setelan_lama = None if _IS_WINDOWS else termios.tcgetattr(fd)
    # Lepas scroll-region (hands-free) tanpa kehilangan posisi kursor (DECSC/DECRC).
    print("\0337\033[r\0338", end="", flush=True)
    try:
        if not _IS_WINDOWS:
            tty.setcbreak(fd)   # cbreak (anti-echo ^[[A), Ctrl+C tetap aktif
        with Live(_frame(), console=console, auto_refresh=False,
                  transient=True, screen=False) as live:
            while True:
                tombol = _baca_tombol()
                if tombol == 'up':
                    indeks = (indeks - 1) % jumlah
                    live.update(_frame(), refresh=True)
                elif tombol == 'down':
                    indeks = (indeks + 1) % jumlah
                    live.update(_frame(), refresh=True)
                elif tombol == 'enter':
                    return indeks
                elif tombol == 'q':
                    return None
    finally:
        if not _IS_WINDOWS:
            termios.tcsetattr(fd, termios.TCSADRAIN, setelan_lama)


def pilih_model(opsi: list[dict], indeks_aktif: int = 0) -> int | None:
    """Menu interaktif pilih provider/model (↑/↓). Return indeks atau None."""
    W = _lebar()                   # selebar penuh terminal
    INNER = W - 2
    NAMA_W = 18                     # kolom nama (cukup utk "OpenRouter (aktif)")
    MODEL_MAX = 18                  # nama model dipotong … kalau kepanjangan

    # Pra-render tiap baris + padding (dari panjang TERLIHAT) supaya '│' sejajar.
    statis = []
    for opt in opsi:
        status = "[success]● Siap[/]" if opt["configured"] else "[error]○ Belum diset[/]"
        status_raw = "● Siap" if opt["configured"] else "○ Belum diset"
        nama = opt["name"] + (" (aktif)" if opt["is_current"] else "")
        nama_field = f"{_potong(nama, NAMA_W):<{NAMA_W}}"
        model_field = f"({_potong(opt['model'], MODEL_MAX)})"
        pad = max(1, INNER - 3 - NAMA_W - 1 - len(model_field) - len(status_raw))
        statis.append((nama_field, model_field, status, " " * pad))

    def baris(i, aktif):
        nf, mf, st, pad = statis[i]
        if aktif:
            isi = f" [bold accent.hi]❯ {nf}[/] [muted]{mf}[/]"
        else:
            isi = f"   {nf} [muted]{mf}[/]"
        return f"{isi}{pad}{st}"

    return _menu_interaktif("PILIH PROVIDER", len(opsi), baris, indeks_aktif, W)


def pilih_bahasa(opsi: list[dict], indeks_aktif: int = 0) -> int | None:
    """Menu interaktif pilih bahasa (↑/↓). opsi: [{code,name,is_current}].

    Return indeks atau None bila batal.
    """
    W = _lebar()                   # selebar penuh terminal
    FIELD = W - 2 - 3              # sisa kolom setelah prefix " ❯ " / "   "

    statis = []
    for o in opsi:
        nama = o["name"] + (" (aktif)" if o["is_current"] else "")
        statis.append(f"{_potong(nama, FIELD):<{FIELD}}")

    def baris(i, aktif):
        nf = statis[i]
        return f" [bold accent.hi]❯ {nf}[/]" if aktif else f"   {nf}"

    return _menu_interaktif("PILIH BAHASA", len(opsi), baris, indeks_aktif, W)


if __name__ == "__main__":
    # Tes MENU saja (tanpa app/alt-screen): python -m voca.ui menu
    if len(sys.argv) > 1 and sys.argv[1] == "menu":
        demo = [
            {"name": "Qwen", "model": "qwen-max", "configured": True, "is_current": True},
            {"name": "OpenAI", "model": "gpt-4o", "configured": True, "is_current": False},
            {"name": "OpenRouter", "model": "openai/gpt-oss-120b:free", "configured": True, "is_current": False},
            {"name": "DeepSeek", "model": "deepseek-v4-flash", "configured": False, "is_current": False},
        ]
        pilih = pilih_model(demo, indeks_aktif=0)
        console.print(f"\nDipilih indeks: {pilih}"
                      + (f" → {demo[pilih]['name']}" if pilih is not None else " (batal)"))
        sys.exit(0)

    # Smoke test visual (tanpa API): python -m voca.ui
    buka_layar()
    try:
        banner("qwen-plus", Path.home() / "edi/project/pribadi/tts", "hands-free")
        hint(f"ngomong langsung  {DOT}  ENTER ketik  {DOT}  'berhenti' keluar")
        pesan_user("kamu siapa sih?")
        header_jawaban()
        console.print("Saya Voca, asisten coding berbasis suara.")
        baris_tool("read_file", "path=agent.py")
        baris_tool("run_command", "cmd=pytest -q")
        console.input("\n[muted]ENTER untuk keluar demo…[/]")
    finally:
        tutup_layar()
