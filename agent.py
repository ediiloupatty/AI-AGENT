"""
agent.py — "Otak" si AI coding companion (Fase 1: berbasis teks).

Memakai model Qwen via Alibaba Model Studio (endpoint OpenAI-compatible).

Alur kerja:
  1. User mengetik perintah.
  2. Qwen memikirkan langkah & memanggil tools (list_files, read_file,
     write_file, run_command) untuk menganalisis folder dan mengerjakan tugas.
  3. Setiap aksi yang mengubah sistem minta konfirmasi user.
  4. Model menarasikan apa yang sedang & sudah dilakukan secara real-time.

Nanti di fase berikutnya, narasi ini tinggal kita sambungkan ke TTS (gTTS),
dan input teks diganti dengan STT (whisper).
"""

import json
import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

from tools import TOOLS_SCHEMA, TOOL_FUNCTIONS, WORKSPACE
from voice import StreamSpeaker

# Baca .env dari folder proyek ini, bukan folder tempat 'kong' dipanggil,
# supaya API key tetap ketemu walau dijalankan dari direktori mana pun.
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

MODEL = "qwen-plus"
DEFAULT_BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"

SYSTEM_PROMPT = """Kamu adalah AI coding companion berbasis suara yang bekerja \
bersama developer, seperti rekan pair-programming yang aktif berkomunikasi.

Gaya kerja:
- Bicara dalam Bahasa Indonesia yang natural, ramah, dan ringkas.
- Sebelum bertindak, pahami dulu lingkungan kerja: gunakan list_files & read_file.
- Jelaskan langkah yang sedang kamu lakukan dan ALASANnya secara singkat,
  seolah sedang melaporkan progres ke rekan kerja secara real-time.
- Kerjakan tugas selangkah demi selangkah. Setelah selesai, simpulkan hasilnya.
- Kamu tidak perlu meminta izin di teks — sistem sudah otomatis meminta
  konfirmasi user saat kamu menulis file atau menjalankan command.

Narasimu nanti akan dibacakan dengan suara, jadi buat kalimat yang enak didengar."""


def hubungkan_tool(client, messages):
    """Loop satu giliran: panggil model, eksekusi tool, ulangi sampai selesai."""
    while True:
        stream = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS_SCHEMA,
            stream=True,
        )

        text_parts = []
        # Akumulasi tool call yang datang bertahap lewat stream (per index).
        tool_calls = {}
        # Speaker latar: mulai membacakan begitu frasa pertama siap, sambil
        # teks berikutnya masih mengalir (suara terasa langsung muncul).
        speaker = StreamSpeaker()

        print("\n🤖 ", end="", flush=True)
        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta

            if getattr(delta, "content", None):
                print(delta.content, end="", flush=True)
                text_parts.append(delta.content)
                speaker.feed(delta.content)

            for tc in (getattr(delta, "tool_calls", None) or []):
                slot = tool_calls.setdefault(tc.index, {"id": "", "name": "", "args": ""})
                if tc.id:
                    slot["id"] = tc.id
                if tc.function and tc.function.name:
                    slot["name"] = tc.function.name
                if tc.function and tc.function.arguments:
                    slot["args"] += tc.function.arguments
        print()

        # Tunggu sisa narasi selesai diucapkan sebelum lanjut (mis. jalankan tool).
        speaker.close()
        narasi = "".join(text_parts)

        # Susun pesan balasan asisten (teks + permintaan tool, jika ada).
        assistant_msg = {"role": "assistant", "content": narasi}
        if tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {"name": tc["name"], "arguments": tc["args"] or "{}"},
                }
                for tc in tool_calls.values()
            ]
        messages.append(assistant_msg)

        # Tidak ada tool yang diminta -> giliran ini selesai.
        if not tool_calls:
            return

        # Eksekusi setiap tool, kirim hasilnya kembali ke model.
        for tc in tool_calls.values():
            fungsi = TOOL_FUNCTIONS.get(tc["name"])
            try:
                args = json.loads(tc["args"]) if tc["args"] else {}
            except json.JSONDecodeError:
                args = {}
            print(f"\n   🔧 {tc['name']}({args})")

            if fungsi is None:
                hasil = f"Tool tidak dikenal: {tc['name']}"
            else:
                try:
                    hasil = fungsi(**args)
                except Exception as e:
                    hasil = f"Error menjalankan {tc['name']}: {e}"

            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": str(hasil),
            })
        # Lanjutkan loop: model lihat hasil tool lalu lanjut bekerja.


def main():
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        print("❌ DASHSCOPE_API_KEY belum diset. Salin .env.example ke .env dan isi key-mu.")
        sys.exit(1)

    client = OpenAI(
        api_key=api_key,
        base_url=os.getenv("QWEN_BASE_URL", DEFAULT_BASE_URL),
    )
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    print("=" * 60)
    print(f"🎙️  AI Coding Companion — model: {MODEL}")
    print(f"📂 Folder kerja: {WORKSPACE}")
    print("Ketik perintah, atau 'v' + ENTER untuk bicara. 'keluar' untuk berhenti.")
    print("=" * 60)

    while True:
        try:
            perintah = input("\n🧑 Kamu (ketik / 'v'=bicara): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSampai jumpa! 👋")
            break

        # Mode suara: rekam dari mic lalu transkripsi jadi perintah.
        if perintah.lower() in ("v", "suara", "voice"):
            try:
                from listen import listen
                perintah = listen()
            except Exception as e:
                print(f"   [⚠️  input suara gagal: {e}]")
                continue
            print(f"📝 (suara) Kamu: {perintah}")

        if not perintah:
            continue
        if perintah.lower() in ("keluar", "exit", "quit"):
            print("Sampai jumpa! 👋")
            break

        messages.append({"role": "user", "content": perintah})
        try:
            hubungkan_tool(client, messages)
        except Exception as e:
            print(f"\n❌ Terjadi error: {e}")


if __name__ == "__main__":
    main()
