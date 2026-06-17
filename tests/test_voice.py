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
