use crossterm::event::{KeyCode, KeyEvent, KeyModifiers};
use tui_input::backend::crossterm::EventHandler;

use crate::app::{App, AppEvent, InputMode, MenuKind, MenuState};
use crate::llm::{Message, ToolCall};
use crate::{llm, provider, tools};

// ── Entry point ──────────────────────────────────────────────────────────────

pub fn handle_event(app: &mut App, event: AppEvent) {
    match event {
        AppEvent::Key(key)         => handle_key(app, key),
        AppEvent::Mouse(mouse)     => handle_mouse(app, mouse),
        AppEvent::Resize(_, _)     => {}

        AppEvent::Tick => {
            app.spinner_frame = app.spinner_frame.wrapping_add(1);
        }

        // ── LLM streaming ────────────────────────────────────────────────────
        AppEvent::LlmChunk(chunk) => {
            app.append_chunk(&chunk);
            if app.is_at_bottom { app.scroll_to_bottom(0); }
        }
        AppEvent::LlmComplete(text, tool_calls) => {
            handle_llm_complete(app, text, tool_calls);
        }
        AppEvent::LlmError(msg) => {
            app.finish_streaming();
            app.push_system(&format!("❌ {msg}"));
        }

        // ── Voice ────────────────────────────────────────────────────────────
        AppEvent::StartListening => {
            // Dipanggil setelah draw() menampilkan "mendengarkan..." di layar.
            // block_in_place: beri tahu Tokio bahwa kita akan blocking I/O
            // agar thread lain bisa dijadwalkan selama menunggu suara.
            if let Some(bridge) = app.bridge.as_mut() {
                let lang = app.voice.lang.clone();
                let tx   = app.tx.clone();
                let text = tokio::task::block_in_place(|| bridge.listen(&lang));
                let _ = tx.send(AppEvent::VoiceResult(text));
            } else {
                app.input_mode = InputMode::Normal;
            }
        }
        AppEvent::VoiceResult(text) => {
            app.input_mode = InputMode::Normal;
            app.voice_text_mode = false;
            if !text.is_empty() {
                process_user_input(app, &text);
            } else {
                app.push_system("🎤 tidak ada ucapan terdeteksi — coba lagi atau ketik pesan");
            }
        }
        AppEvent::VoiceSpeak(text) => {
            // Dipanggil SETELAH draw() — teks jawaban sudah tampil di layar
            // sebelum TTS mulai berbicara.
            if let Some(bridge) = app.bridge.as_mut() {
                let lang = app.voice.lang.clone();
                tokio::task::block_in_place(|| bridge.speak(&text, &lang));
            }
        }

        // ── Tools ─────────────────────────────────────────────────────────────
        AppEvent::ToolResult(id, result) => {
            app.llm_messages.push(Message::tool_result(&id, result));
            start_llm_turn(app);
        }
        AppEvent::ConfirmAnswer(yes) => {
            app.input_mode = InputMode::Normal;
            if !yes { app.push_system("(dibatalkan)"); }
        }
    }
}

// ── Keyboard ─────────────────────────────────────────────────────────────────

fn handle_key(app: &mut App, key: KeyEvent) {
    // Global: Ctrl-C keluar
    if key.code == KeyCode::Char('c') && key.modifiers.contains(KeyModifiers::CONTROL) {
        app.should_quit = true;
        return;
    }
    // Global: scroll
    match key.code {
        KeyCode::PageUp   => { app.scroll_up(10); return; }
        KeyCode::PageDown => { app.scroll_down(10, 0); return; }
        KeyCode::End      => { app.scroll_to_bottom(0); return; }
        _ => {}
    }

    match &app.input_mode.clone() {
        InputMode::Normal => {
            let in_mic_mode = app.voice.listen
                && !app.voice_text_mode
                && app.input.value().is_empty()
                && app.bridge.is_some();

            match key.code {
                KeyCode::Enter => {
                    let text = app.input.value().to_string();
                    app.input.reset();
                    if !text.is_empty() {
                        app.voice_text_mode = false;
                        process_user_input(app, &text);
                    } else if in_mic_mode {
                        app.input_mode = InputMode::Listening;
                        let _ = app.tx.send(AppEvent::StartListening);
                    }
                }

                // 't' di mic-mode: beralih ke text input tanpa menambah 't' ke buffer
                KeyCode::Char('t') | KeyCode::Char('T') if in_mic_mode => {
                    app.voice_text_mode = true;
                }

                // Esc di voice text-mode: kembali ke mic indicator
                KeyCode::Esc if app.voice_text_mode => {
                    app.voice_text_mode = false;
                    app.input.reset();
                }

                _ => {
                    if in_mic_mode {
                        app.voice_text_mode = true;
                    }
                    app.input.handle_event(&crossterm::event::Event::Key(key));
                }
            }
        }

        InputMode::Menu => {
            if let Some(mut menu) = app.menu.take() {
                let n = menu.items.len();
                match key.code {
                    KeyCode::Up   | KeyCode::Char('k') => {
                        menu.selected = (menu.selected + n - 1) % n;
                        app.menu = Some(menu);
                    }
                    KeyCode::Down | KeyCode::Char('j') => {
                        menu.selected = (menu.selected + 1) % n;
                        app.menu = Some(menu);
                    }
                    KeyCode::Enter => {
                        app.input_mode = InputMode::Normal;
                        match menu.kind {
                            MenuKind::Model => {
                                let all = provider::all();
                                apply_provider(all[menu.selected].code, app);
                            }
                            MenuKind::Language => {
                                let langs = ["id", "en"];
                                apply_language(langs[menu.selected], app);
                            }
                        }
                    }
                    KeyCode::Esc | KeyCode::Char('q') => {
                        app.input_mode = InputMode::Normal;
                        app.push_system("(dibatalkan)");
                    }
                    _ => { app.menu = Some(menu); }
                }
            }
        }

        InputMode::Confirming(_) => match key.code {
            KeyCode::Char('y') | KeyCode::Char('Y') => {
                let _ = app.tx.send(AppEvent::ConfirmAnswer(true));
            }
            KeyCode::Enter | KeyCode::Char('n') | KeyCode::Char('N') | KeyCode::Esc => {
                let _ = app.tx.send(AppEvent::ConfirmAnswer(false));
            }
            _ => {}
        },

        InputMode::Processing | InputMode::Listening => {
            // Abaikan input saat sedang proses / mendengarkan
        }
    }
}

fn handle_mouse(app: &mut App, mouse: crossterm::event::MouseEvent) {
    use crossterm::event::MouseEventKind;
    match mouse.kind {
        MouseEventKind::ScrollUp   => app.scroll_up(3),
        MouseEventKind::ScrollDown => app.scroll_down(3, 0),
        _ => {}
    }
}

// ── User input → LLM ─────────────────────────────────────────────────────────

fn process_user_input(app: &mut App, teks: &str) {
    let teks = teks.trim();
    if teks.is_empty() { return; }

    // Slash commands
    match teks {
        "/exit" | "/quit" => { app.should_quit = true; return; }
        "/help" => {
            app.push_system("Perintah: /model [nama]  ·  /lan [id|en]  ·  /exit");
            return;
        }
        _ => {}
    }
    if let Some(arg) = teks.strip_prefix("/model") {
        switch_model(app, arg.trim());
        return;
    }
    if let Some(arg) = teks.strip_prefix("/lan") {
        switch_lang(app, arg.trim_start_matches('g').trim());
        return;
    }

    // Quick shortcuts (ganti model/bahasa dengan kata natural)
    if let Some((kind, val)) = detect_quick_command(teks) {
        match kind {
            "model" => { switch_model(app, val); return; }
            _       => { switch_lang(app, val); return; }
        }
    }

    // Pesan biasa → kirim ke LLM
    app.push_user(teks);
    app.llm_messages.push(Message::new("user", teks));
    start_llm_turn(app);
}

fn start_llm_turn(app: &mut App) {
    app.start_streaming("memikirkan...");
    let tx     = app.tx.clone();
    let client = app.client.clone();
    let prov   = app.provider.clone();
    let limits = app.limits.clone();
    let msgs   = app.llm_messages.clone();
    let tools  = app.tools_schema.clone();

    tokio::spawn(async move {
        llm::stream_to_channel(client, prov, limits, msgs, tools, tx).await;
    });
}

fn handle_llm_complete(app: &mut App, narasi: String, tool_calls: Vec<ToolCall>) {
    // finish_streaming() push bubble VOCA → draw() menampilkannya
    app.finish_streaming();
    app.llm_messages.push(Message::assistant(narasi.clone(), tool_calls.clone()));

    // Jadwalkan TTS setelah draw() berikutnya:
    // urutan event → LlmComplete (finish_streaming+push) → draw() tampilkan teks
    // → VoiceSpeak → bridge.speak() blok selama TTS
    if app.voice.speak && app.bridge.is_some() && !narasi.is_empty() {
        let _ = app.tx.send(AppEvent::VoiceSpeak(narasi.clone()));
    }

    if tool_calls.is_empty() {
        trim_history(&mut app.llm_messages, app.limits.max_history);
        return;
    }

    // Eksekusi semua tool, kumpulkan hasil, lalu lanjut iterasi LLM
    for tc in &tool_calls {
        let summary = tools::summarize_args(&tc.function.arguments);
        app.push_tool(&format!("◆ {} {}", tc.function.name, summary));
        let result = tools::dispatch(&tc.function.name, &tc.function.arguments);
        app.llm_messages.push(Message::tool_result(&tc.id, result));
    }
    start_llm_turn(app);
}

// ── Slash command helpers ─────────────────────────────────────────────────────

fn switch_model(app: &mut App, arg: &str) {
    if arg.is_empty() {
        let all = provider::all();
        let cur = all.iter().position(|p| p.code == app.provider.code).unwrap_or(0);
        let items = all.iter().map(|p| {
            let dot  = if p.api_key.is_some() { "●" } else { "○" };
            let flag = if p.code == app.provider.code { " ←" } else { "" };
            format!("{:<11} {}  {dot}{flag}", p.code, p.model)
        }).collect();
        app.menu = Some(MenuState { title: "PILIH MODEL".into(), items, selected: cur, kind: MenuKind::Model });
        app.input_mode = InputMode::Menu;
    } else {
        apply_provider(arg, app);
    }
}

fn apply_provider(code: &str, app: &mut App) {
    match provider::by_code(code) {
        Some(mut p) => match crate::config::ensure_api_key(p.code, p.name) {
            Ok(k) => {
                p.api_key = Some(k);
                app.push_system(&format!("✓ model: {} ({})", p.name, p.model));
                app.provider = p;
            }
            Err(e) => app.push_system(&format!("❌ {e}")),
        },
        None => app.push_system("❌ provider tidak dikenal (qwen / openai / openrouter / deepseek)"),
    }
}

fn switch_lang(app: &mut App, arg: &str) {
    const LANGS: [(&str, &str); 2] = [("id", "Indonesia"), ("en", "English")];
    if arg == "id" || arg == "en" {
        apply_language(arg, app);
    } else if arg.is_empty() {
        let cur   = LANGS.iter().position(|(c, _)| *c == app.voice.lang).unwrap_or(0);
        let items = LANGS.iter().map(|(c, name)| {
            let flag = if *c == app.voice.lang { " ←" } else { "" };
            format!("{name}{flag}")
        }).collect();
        app.menu = Some(MenuState { title: "PILIH BAHASA".into(), items, selected: cur, kind: MenuKind::Language });
        app.input_mode = InputMode::Menu;
    } else {
        let new = if app.voice.lang == "id" { "en" } else { "id" };
        apply_language(new, app);
    }
}

fn apply_language(lang: &str, app: &mut App) {
    app.voice.lang = lang.to_string();
    app.push_system(&format!("✓ bahasa: {}", lang.to_uppercase()));
}

fn trim_history(messages: &mut Vec<Message>, max: usize) {
    // messages[0] = system prompt, jangan dihapus
    while messages.len().saturating_sub(1) > max {
        messages.remove(1);
        // Jaga agar setelah remove[1] selanjutnya adalah pesan user
        while messages.len() > 1 && messages[1].role != "user" {
            messages.remove(1);
        }
    }
}

fn detect_quick_command(teks: &str) -> Option<(&'static str, &'static str)> {
    let t: String = teks
        .to_lowercase()
        .chars()
        .filter(|c| c.is_alphanumeric() || c.is_whitespace())
        .collect();
    let t = t.trim();
    if t.is_empty() || t.split_whitespace().count() > 3 { return None; }
    match t {
        "qwen" | "kuen" | "kwen"                       => Some(("model", "qwen")),
        "openai" | "open ai" | "gpt" | "chatgpt"       => Some(("model", "openai")),
        "openrouter" | "open router" | "router"         => Some(("model", "openrouter")),
        "deepseek" | "deep seek" | "dipsik"             => Some(("model", "deepseek")),
        "english" | "bahasa inggris" | "inggris"        => Some(("lan", "en")),
        "indonesia" | "bahasa indonesia"                => Some(("lan", "id")),
        _ => None,
    }
}
