use std::io::{BufRead, BufReader, Write};
use std::process::{Child, ChildStdin, ChildStdout, Command, Stdio};

use serde_json::{json, Value};

pub struct VoiceBridge {
    child:  Child,
    stdin:  ChildStdin,
    stdout: BufReader<ChildStdout>,
}

impl VoiceBridge {
    /// Jalankan sidecar Python (`python3 -m voca.voice_server`) dan tunggu
    /// sampai siap. Mengembalikan `None` jika proses gagal start.
    pub fn start() -> Option<Self> {
        let py = std::env::var("VOCA_VOICE_PYTHON")
            .unwrap_or_else(|_| "python3".to_string());

        let mut cmd = Command::new(&py);
        cmd.args(["-m", "voca.voice_server"]);

        // Cari direktori yang mengandung paket `voca/` mulai dari CWD ke atas
        let home = std::env::var("VOCA_VOICE_HOME")
            .ok()
            .map(std::path::PathBuf::from)
            .or_else(|| find_voca_root(&std::env::current_dir().ok()?));

        if let Some(ref h) = home {
            cmd.current_dir(h).env("PYTHONPATH", h);
        }

        cmd.stdin(Stdio::piped())
           .stdout(Stdio::piped())
           .stderr(Stdio::inherit()); // tampilkan log sidecar di terminal

        let mut child = cmd.spawn().ok()?;
        let stdin      = child.stdin.take()?;
        let mut stdout = BufReader::new(child.stdout.take()?);

        // Tunggu baris `{"ready":true}`
        let mut line = String::new();
        match stdout.read_line(&mut line) {
            Ok(0) | Err(_) => { let _ = child.kill(); return None; }
            Ok(_) => {}
        }

        Some(VoiceBridge { child, stdin, stdout })
    }

    /// Ucapkan teks melalui TTS (blokir sampai selesai diputar).
    pub fn speak(&mut self, text: &str, lang: &str) {
        let _ = self.request(json!({ "cmd": "speak", "text": text, "lang": lang }));
    }

    /// Rekam mic hingga hening (VAD) → kembalikan transkrip. `""` jika gagal.
    pub fn listen(&mut self, lang: &str) -> String {
        match self.request(json!({ "cmd": "listen", "lang": lang })) {
            Some(v) => v
                .get("text")
                .and_then(|t| t.as_str())
                .unwrap_or("")
                .to_string(),
            None => String::new(),
        }
    }

    // ── Protokol JSON-per-baris ──────────────────────────────────────────────

    fn request(&mut self, req: Value) -> Option<Value> {
        self.stdin.write_all(req.to_string().as_bytes()).ok()?;
        self.stdin.write_all(b"\n").ok()?;
        self.stdin.flush().ok()?;

        let mut resp = String::new();
        match self.stdout.read_line(&mut resp) {
            Ok(0) | Err(_) => None,
            Ok(_)          => serde_json::from_str(resp.trim()).ok(),
        }
    }
}

impl Drop for VoiceBridge {
    fn drop(&mut self) {
        let _ = self.child.kill();
        let _ = self.child.wait();
    }
}

/// Naik hingga 5 level dari `start` mencari direktori yang punya `voca/__init__.py`.
fn find_voca_root(start: &std::path::Path) -> Option<std::path::PathBuf> {
    let mut dir = start.to_path_buf();
    for _ in 0..5 {
        if dir.join("voca").join("__init__.py").exists() {
            return Some(dir);
        }
        dir = dir.parent()?.to_path_buf();
    }
    None
}
