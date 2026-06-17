"""Tes untuk voca/voice.py — pemotongan kalimat & pembersihan teks (tanpa audio)."""

from voca import voice


def test_potong_kalimat_di_titik():
    head, sisa = voice._potong_kalimat("Halo dunia. sisa")
    assert head == "Halo dunia."
    assert sisa.strip() == "sisa"


def test_potong_kalimat_belum_lengkap():
    head, sisa = voice._potong_kalimat("masih ngetik")
    assert head is None
    assert sisa == "masih ngetik"


def test_bersihkan_teks_buang_markdown_kode_url_emoji():
    out = voice._bersihkan_teks("**tebal** `kode` lihat http://x.com 🎉 selesai")
    assert "*" not in out
    assert "`" not in out
    assert "http" not in out
    assert "🎉" not in out
    assert "tebal" in out and "selesai" in out


def test_eja_inggris_kata_umum():
    out = voice._eja_inggris("cek file dan commit lalu deploy")
    assert "fail" in out and "komit" in out and "diploi" in out
    assert "file" not in out


def test_eja_inggris_case_insensitive():
    assert voice._eja_inggris("ERROR di Function") == "eror di fangsyen"


def test_eja_inggris_tidak_sentuh_substring():
    # 'file' di dalam 'Profile'/'filename' tak boleh diganti (harus kata utuh)
    out = voice._eja_inggris("Profile dan filename")
    assert out == "Profile dan filename"
