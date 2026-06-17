"""Tes untuk voca/tools.py — operasi file, edit, search, diff (tanpa jaringan)."""

import pytest

from voca import config, tools


@pytest.fixture
def ws(tmp_path, monkeypatch):
    """Folder kerja sementara + konfirmasi auto-ya + diff senyap."""
    monkeypatch.setattr(tools, "WORKSPACE", tmp_path)
    monkeypatch.setattr(config, "SHOW_DIFF", False)
    tools.set_confirm_handler(lambda prompt: True)
    return tmp_path


# --- keamanan path ----------------------------------------------------------
def test_resolve_safe_blokir_traversal(ws):
    with pytest.raises(ValueError):
        tools._resolve_safe("../rahasia")


def test_resolve_safe_izinkan_di_dalam(ws):
    assert str(tools._resolve_safe("sub/x.txt")).startswith(str(ws))


# --- read / write -----------------------------------------------------------
def test_read_file_tidak_ada(ws):
    assert "tidak ditemukan" in tools.read_file("nope.txt")


def test_write_lalu_read(ws):
    assert "Berhasil" in tools.write_file("a.txt", "halo\ndunia\n")
    assert tools.read_file("a.txt") == "halo\ndunia\n"


def test_read_rentang_baris(ws):
    tools.write_file("b.txt", "satu\ndua\ntiga\n")
    out = tools.read_file("b.txt", 2, 3)
    assert "2: dua" in out and "3: tiga" in out and "satu" not in out


def test_read_dipotong(ws, monkeypatch):
    monkeypatch.setattr(config, "MAX_READ_CHARS", 10)
    tools.write_file("c.txt", "x" * 50)
    assert "dipotong" in tools.read_file("c.txt")


# --- edit_file --------------------------------------------------------------
def test_edit_sukses(ws):
    tools.write_file("d.py", "a=1\nb=2\n")
    assert "Berhasil mengedit" in tools.edit_file("d.py", "b=2", "b=3")
    assert tools.read_file("d.py") == "a=1\nb=3\n"


def test_edit_tidak_unik(ws):
    tools.write_file("e.py", "x\nx\n")
    assert "tidak unik" in tools.edit_file("e.py", "x", "y")


def test_edit_teks_tak_ada(ws):
    tools.write_file("f.py", "abc\n")
    assert "tak ditemukan" in tools.edit_file("f.py", "zzz", "y")


def test_edit_file_belum_ada(ws):
    assert "write_file" in tools.edit_file("ghost.py", "a", "b")


# --- search & list ----------------------------------------------------------
def test_search_python(ws):
    (ws / "g.py").write_text("def login():\n    pass\n")
    out = tools._search_python("login", ws)
    assert "g.py" in out and "login" in out


def test_list_files(ws):
    (ws / "h.txt").write_text("x")
    assert "h.txt" in tools.list_files(".")


# --- diff -------------------------------------------------------------------
def test_diff_hitung_tambah_hapus(ws):
    tambah, hapus = tools._tampilkan_diff("x", "a\nb\n", "a\nc\n")
    assert tambah == 1 and hapus == 1
