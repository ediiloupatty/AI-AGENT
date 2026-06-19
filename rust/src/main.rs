mod agent;
mod app;
mod config;
mod llm;
mod provider;
mod tools;
mod ui;
mod voicebridge;

use anyhow::Result;
use crossterm::event::{Event as CrosstermEvent, EventStream};
use futures_util::StreamExt;
use ratatui::crossterm::event::{DisableMouseCapture, EnableMouseCapture};
use ratatui::crossterm::execute;
use std::env;
use std::panic;
use tokio::sync::mpsc;
use tokio::time::{interval, Duration, MissedTickBehavior};

use crate::app::{App, AppEvent};
use crate::voicebridge::VoiceBridge;

#[tokio::main]
async fn main() -> Result<()> {
    // Pulihkan terminal saat panic agar tidak corrupt
    let original_hook = panic::take_hook();
    panic::set_hook(Box::new(move |info| {
        let _ = ratatui::restore();
        let _ = execute!(std::io::stdout(), DisableMouseCapture);
        original_hook(info);
    }));

    // Flag versi
    let args: Vec<String> = env::args().collect();
    if args.get(1).map_or(false, |a| matches!(a.as_str(), "--version" | "-v")) {
        println!("Voca v{}", env!("CARGO_PKG_VERSION"));
        return Ok(());
    }

    // Muat .env + config user (~/.config/voca/config.json)
    config::load();

    // ── Parse CLI ────────────────────────────────────────────────────────────
    let mut voice_listen = true;
    let mut voice_speak  = true;
    let mut voice_lang   = "id".to_string();
    let mut initial_text: Option<String> = None;

    let mut i = 1usize;
    while i < args.len() {
        match args[i].as_str() {
            "--no-voice" | "--text-only" => { voice_listen = false; voice_speak = false; }
            "--voice"  => { voice_listen = true; voice_speak = true; }
            "--listen" => voice_listen = true,
            "--speak" | "--say" => voice_speak = true,
            "--lang" if i + 1 < args.len() => { voice_lang = args[i + 1].clone(); i += 1; }
            "-t" | "--text" if i + 1 < args.len() => { initial_text = Some(args[i + 1].clone()); i += 1; }
            _ => {}
        }
        i += 1;
    }

    // ── Provider LLM ─────────────────────────────────────────────────────────
    let code = env::var("VOCA_MODEL")
        .or_else(|_| env::var("VOCA_PROVIDER"))
        .unwrap_or_else(|_| "qwen".to_string());

    let mut prov = provider::by_code(&code)
        .unwrap_or_else(|| provider::all().into_iter().next().unwrap());
    prov.api_key = Some(config::ensure_api_key(prov.code, prov.name)?);

    let limits = config::Limits::from_env();
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(60))
        .build()?;

    // ── Channel & State ──────────────────────────────────────────────────────
    let (tx, mut rx) = mpsc::unbounded_channel::<AppEvent>();

    let bridge = if voice_listen || voice_speak { VoiceBridge::start() } else { None };

    let voice_opts = app::VoiceOpts { listen: voice_listen, speak: voice_speak, lang: voice_lang };
    let mut app = App::new(prov, voice_opts, limits, client, tx.clone());
    app.bridge = bridge;

    // Banner, lalu status sidecar
    app.push_banner();
    if app.bridge.is_none() && (app.voice.listen || app.voice.speak) {
        app.push_system(
            "⌨  Sidecar suara tidak tersedia — lanjut mode teks.\n\
             ·  Jalankan dulu: python3 -m voca.voice_server"
        );
        app.voice.listen = false;
        app.voice.speak  = false;
    } else if app.bridge.is_some() {
        app.push_system("◉ Sidecar suara siap. Tekan Enter kosong untuk mulai bicara.");
    }

    // Pesan awal dari argumen -t
    if let Some(text) = initial_text {
        let _ = tx.send(AppEvent::VoiceResult(text));
    }

    // ── TUI ──────────────────────────────────────────────────────────────────
    let mut terminal = ratatui::init();
    let _ = execute!(std::io::stdout(), EnableMouseCapture);

    // Tick setiap 80 ms untuk animasi spinner; lewati tick yang terlewat
    let mut tick_interval = interval(Duration::from_millis(80));
    tick_interval.set_missed_tick_behavior(MissedTickBehavior::Skip);

    let mut crossterm_events = EventStream::new();

    loop {
        if app.should_quit { break; }

        terminal.draw(|f| ui::draw(f, &mut app))?;

        tokio::select! {
            biased;

            // Prioritas: event dari LLM/voice tasks (LlmChunk, VoiceResult, …)
            Some(event) = rx.recv() => {
                agent::handle_event(&mut app, event);
            }

            // Keyboard/mouse diproses langsung (tanpa round-trip lewat tx)
            Some(Ok(event)) = crossterm_events.next() => {
                match event {
                    CrosstermEvent::Key(k) => {
                        agent::handle_event(&mut app, AppEvent::Key(k));
                    }
                    CrosstermEvent::Mouse(m) => {
                        agent::handle_event(&mut app, AppEvent::Mouse(m));
                    }
                    CrosstermEvent::Resize(w, h) => {
                        agent::handle_event(&mut app, AppEvent::Resize(w, h));
                    }
                    _ => {}
                }
            }

            // Tick animasi (prioritas terendah)
            _ = tick_interval.tick() => {
                agent::handle_event(&mut app, AppEvent::Tick);
            }
        }
    }

    // ── Cleanup ──────────────────────────────────────────────────────────────
    let _ = execute!(std::io::stdout(), DisableMouseCapture);
    ratatui::restore();

    Ok(())
}
