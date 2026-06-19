use ratatui::prelude::*;
use ratatui::widgets::{
    Block, Borders, Clear, Paragraph, Scrollbar, ScrollbarOrientation, ScrollbarState, Wrap,
};

use crate::app::{App, BubbleRole, InputMode, MenuState};

// ── Palet warna (light theme — sesuai tts/src/App.css) ──────────────────────
//
// Gradient web (atas→bawah): #d2f3ec → #e1f6f1 → #edf8f5 → #f4f7fb
//
const ACCENT:     Color = Color::Rgb(13,  148, 136); // #0d9488 web --accent
const MUTED:      Color = Color::Rgb(91,  101, 115); // #5b6573 web --muted
const TOOL_C:     Color = Color::Rgb(37,  99,  235); // #2563eb web blue
const WARNING:    Color = Color::Rgb(234, 88,  12);
const ERROR_C:    Color = Color::Rgb(220, 38,  38);
const BORDER:     Color = Color::Rgb(167, 215, 209); // teal muted
const HEADER_BG:  Color = Color::Rgb(210, 243, 236); // #d2f3ec
const STATUS_BG:  Color = Color::Rgb(237, 248, 245); // #edf8f5
const INPUT_BG:   Color = Color::Rgb(255, 255, 255);
const CHAT_BG:    Color = Color::Rgb(244, 247, 251); // #f4f7fb web --page
const TEXT_FG:    Color = Color::Rgb(15,  23,  42);  // #0f172a web --ink
const POPUP_BG:   Color = Color::Rgb(15,  23,  42);  // dark navy untuk menu overlay
const POPUP_SEL:  Color = Color::Rgb(13,  148, 136); // teal untuk selected item
const POPUP_DIM:  Color = Color::Rgb(100, 120, 150); // abu-abu terang pada bg gelap

const SPINNER_FRAMES: [char; 10] = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'];

fn spin(idx: usize) -> char {
    SPINNER_FRAMES[idx % SPINNER_FRAMES.len()]
}

// ── Layout ───────────────────────────────────────────────────────────────────
//
// ┌────────────────────────────────────────────┐  Length(2)   Header
// ├────────────────────────────────────────────┤  Fill(1)     Chat
// ├────────────────────────────────────────────┤  Length(1)   Status bar
// ├────────────────────────────────────────────┤  Length(3)   Input area
// └────────────────────────────────────────────┘

pub fn draw(frame: &mut Frame, app: &mut App) {
    let chunks = Layout::vertical([
        Constraint::Length(2),
        Constraint::Fill(1),
        Constraint::Length(1),
        Constraint::Length(3),
    ])
    .split(frame.area());

    render_header(frame, app, chunks[0]);
    render_chat(frame, app, chunks[1]);
    render_status(frame, app, chunks[2]);
    render_input(frame, app, chunks[3]);

    if let Some(ref menu) = app.menu {
        render_menu(frame, menu, frame.area());
    }
}

// ── Header ───────────────────────────────────────────────────────────────────

fn render_header(frame: &mut Frame, app: &App, area: Rect) {
    let [title_row, sep_row] = Layout::vertical([
        Constraint::Length(1),
        Constraint::Length(1),
    ])
    .areas(area);

    let (badge_text, badge_bg) = if app.voice.listen {
        (" ◉ SUARA ", ACCENT)
    } else {
        (" ⌨  KETIK ", MUTED)
    };
    let lang_str = format!(" {} ", app.voice.lang.to_uppercase());

    let left_len = "  ◈ VOCA  ·  AI Coding Assistant".chars().count() as u16;
    let right_len = (badge_text.chars().count() + lang_str.chars().count()) as u16;
    let pad = area.width.saturating_sub(left_len + right_len) as usize;

    let title = Line::from(vec![
        Span::styled("  ◈ ", Style::default().fg(ACCENT).bold()),
        Span::styled("VOCA", Style::default().fg(ACCENT).bold()),
        Span::styled("  ·  AI Coding Assistant", Style::default().fg(MUTED)),
        Span::raw(" ".repeat(pad)),
        Span::styled(badge_text, Style::default().fg(Color::White).bg(badge_bg).bold()),
        Span::styled(lang_str,   Style::default().fg(ACCENT).bold().bg(HEADER_BG)),
    ]);

    frame.render_widget(
        Paragraph::new(title).style(Style::default().bg(HEADER_BG)),
        title_row,
    );
    frame.render_widget(
        Paragraph::new(Line::from(Span::styled(
            "─".repeat(area.width as usize),
            Style::default().fg(ACCENT),
        )))
        .style(Style::default().bg(HEADER_BG)),
        sep_row,
    );
}

// ── Chat ─────────────────────────────────────────────────────────────────────

fn render_chat(frame: &mut Frame, app: &mut App, area: Rect) {
    let inner_w = area.width.saturating_sub(2) as usize;
    let mut lines: Vec<Line> = Vec::new();

    for bubble in &app.messages {
        if !lines.is_empty() { lines.push(Line::raw("")); }

        match bubble.role {
            BubbleRole::System => {
                let style = if bubble.content.starts_with("❌") {
                    Style::default().fg(ERROR_C)
                } else if bubble.content.starts_with("⚠") {
                    Style::default().fg(WARNING)
                } else {
                    Style::default().fg(MUTED).italic()
                };
                for raw in bubble.content.lines() {
                    lines.push(Line::from(vec![
                        Span::raw("  "),
                        Span::styled(raw.to_string(), style),
                    ]));
                }
            }

            BubbleRole::User => {
                lines.push(Line::from(vec![
                    Span::styled("  ╭─ ", Style::default().fg(ACCENT)),
                    Span::styled("ANDA", Style::default().fg(ACCENT).bold()),
                ]));
                for raw in bubble.content.lines() {
                    lines.push(Line::from(vec![
                        Span::styled("  │ ", Style::default().fg(ACCENT)),
                        Span::styled(raw.to_string(), Style::default().fg(TEXT_FG)),
                    ]));
                }
            }

            BubbleRole::Assistant => {
                lines.push(Line::from(vec![
                    Span::styled("  ╭─ ", Style::default().fg(ACCENT)),
                    Span::styled("VOCA", Style::default().fg(ACCENT).bold()),
                ]));
                for raw in bubble.content.lines() {
                    lines.push(Line::from(vec![
                        Span::styled("  │ ", Style::default().fg(ACCENT)),
                        Span::styled(raw.to_string(), Style::default().fg(TEXT_FG)),
                    ]));
                }
            }

            BubbleRole::Tool => {
                for raw in bubble.content.lines() {
                    lines.push(Line::from(vec![
                        Span::styled("  ◆ ", Style::default().fg(TOOL_C)),
                        Span::styled(raw.to_string(), Style::default().fg(TOOL_C).dim()),
                    ]));
                }
            }
        }
    }

    // Streaming: jawaban LLM yang sedang masuk
    if app.is_streaming {
        if !lines.is_empty() { lines.push(Line::raw("")); }
        lines.push(Line::from(vec![
            Span::styled("  ╭─ ", Style::default().fg(ACCENT)),
            Span::styled("VOCA", Style::default().fg(ACCENT).bold()),
        ]));

        if app.current_stream.is_empty() {
            let sp = spin(app.spinner_frame);
            let msg = if app.spinner_msg.is_empty() { "memikirkan..." } else { &app.spinner_msg };
            lines.push(Line::from(vec![
                Span::styled("  │ ", Style::default().fg(ACCENT)),
                Span::styled(format!("{sp} "), Style::default().fg(ACCENT)),
                Span::styled(msg.to_string(), Style::default().fg(MUTED).italic()),
            ]));
        } else {
            for raw in app.current_stream.lines() {
                lines.push(Line::from(vec![
                    Span::styled("  │ ", Style::default().fg(ACCENT)),
                    Span::styled(raw.to_string(), Style::default().fg(TEXT_FG)),
                ]));
            }
            // Kursor animasi streaming
            lines.push(Line::from(vec![
                Span::styled("  │ ", Style::default().fg(ACCENT)),
                Span::styled(spin(app.spinner_frame).to_string(), Style::default().fg(ACCENT)),
            ]));
        }
    }

    // Hitung baris setelah wrapping untuk scrollbar
    let total = compute_wrapped_lines(&lines, inner_w);
    app.total_lines = total as u16;

    let visible_h = area.height;
    if app.is_at_bottom {
        app.scroll_offset = (app.total_lines).saturating_sub(visible_h);
    }

    frame.render_widget(
        Paragraph::new(Text::from(lines))
            .style(Style::default().bg(CHAT_BG).fg(TEXT_FG))
            .wrap(Wrap { trim: false })
            .scroll((app.scroll_offset, 0)),
        area,
    );

    // Scrollbar vertikal
    let content_len = app.total_lines as usize;
    let viewport    = visible_h as usize;
    if content_len > viewport {
        let mut state = ScrollbarState::new(content_len.saturating_sub(viewport))
            .position(app.scroll_offset as usize);
        frame.render_stateful_widget(
            Scrollbar::new(ScrollbarOrientation::VerticalRight)
                .begin_symbol(Some("▲"))
                .end_symbol(Some("▼"))
                .track_symbol(Some("│"))
                .thumb_symbol("█"),
            area,
            &mut state,
        );
    }
}

fn compute_wrapped_lines(lines: &[Line], width: usize) -> usize {
    if width == 0 { return lines.len(); }
    lines.iter().map(|line| {
        let chars: usize = line.spans.iter().map(|s| s.content.chars().count()).sum();
        if chars == 0 { 1 } else { (chars + width - 1) / width }
    }).sum()
}

// ── Status bar ───────────────────────────────────────────────────────────────

fn render_status(frame: &mut Frame, app: &App, area: Rect) {
    let model_str = format!(" {} · {} ", app.provider.name, app.provider.model);

    let (icon, mode_str, mode_style) = if app.voice.listen {
        ("◉", " SUARA ", Style::default().fg(ACCENT).bg(STATUS_BG).bold())
    } else {
        ("⌨", " KETIK ", Style::default().fg(MUTED).bg(STATUS_BG))
    };

    let hint = if app.voice.listen {
        " Enter bicara  ·  /model  ·  /lan  ·  /exit "
    } else {
        " /model  ·  /lan  ·  /exit "
    };

    let bar = Line::from(vec![
        Span::styled(model_str,              Style::default().fg(MUTED).bg(STATUS_BG)),
        Span::styled("│",                    Style::default().fg(BORDER).bg(STATUS_BG)),
        Span::styled(format!(" {icon}"),     mode_style),
        Span::styled(mode_str,               mode_style),
        Span::styled("│",                    Style::default().fg(BORDER).bg(STATUS_BG)),
        Span::styled(hint,                   Style::default().fg(MUTED).bg(STATUS_BG)),
        Span::styled(" ".repeat(area.width as usize), Style::default().bg(STATUS_BG)),
    ]);

    frame.render_widget(
        Paragraph::new(bar).style(Style::default().bg(STATUS_BG)),
        area,
    );
}

// ── Input area ───────────────────────────────────────────────────────────────

fn render_input(frame: &mut Frame, app: &App, area: Rect) {
    let border_color = match &app.input_mode {
        InputMode::Confirming(_) => WARNING,
        _                        => ACCENT,
    };

    let block = Block::default()
        .borders(Borders::TOP)
        .border_style(Style::default().fg(border_color))
        .style(Style::default().bg(INPUT_BG).fg(TEXT_FG));

    let inner = block.inner(area);

    match &app.input_mode {
        InputMode::Normal => {
            let in_mic_mode = app.voice.listen
                && !app.voice_text_mode
                && app.input.value().is_empty()
                && app.bridge.is_some();

            if in_mic_mode {
                // Tampilkan mic indicator — tanpa cursor
                let display = Line::from(vec![
                    Span::styled("  ◉ ", Style::default().fg(ACCENT).bold()),
                    Span::styled("Enter = bicara", Style::default().fg(ACCENT)),
                    Span::styled("    ·    ", Style::default().fg(MUTED)),
                    Span::styled("t", Style::default().fg(TEXT_FG).bold()),
                    Span::styled(" = ketik teks", Style::default().fg(MUTED)),
                ]);
                frame.render_widget(Paragraph::new(display).block(block), area);
            } else {
                let value = app.input.value();
                let placeholder = if app.voice_text_mode {
                    "ketik pesan… (Esc = kembali mic)"
                } else {
                    "ketik pesan atau /help…"
                };
                let display = if value.is_empty() {
                    Line::from(vec![
                        Span::styled("  › ", Style::default().fg(ACCENT).bold()),
                        Span::styled(placeholder, Style::default().fg(MUTED).italic()),
                    ])
                } else {
                    Line::from(vec![
                        Span::styled("  › ", Style::default().fg(ACCENT).bold()),
                        Span::styled(value.to_string(), Style::default().fg(TEXT_FG)),
                    ])
                };
                frame.render_widget(Paragraph::new(display).block(block), area);
                // Posisi kursor: 4 karakter "  › " + visual cursor
                let cursor_x = area.x + 4 + app.input.visual_cursor() as u16;
                frame.set_cursor_position(Position::new(cursor_x, inner.y));
            }
        }

        InputMode::Listening => {
            let sp = spin(app.spinner_frame);
            frame.render_widget(
                Paragraph::new(Line::from(vec![
                    Span::raw("  "),
                    Span::styled(format!("{sp} "), Style::default().fg(ACCENT).bold()),
                    Span::styled("mendengarkan suara Anda…", Style::default().fg(ACCENT).italic()),
                ]))
                .block(block),
                area,
            );
        }

        InputMode::Processing => {
            let sp  = spin(app.spinner_frame);
            let msg = if app.spinner_msg.is_empty() { "memikirkan…" } else { &app.spinner_msg };
            frame.render_widget(
                Paragraph::new(Line::from(vec![
                    Span::raw("  "),
                    Span::styled(format!("{sp} "), Style::default().fg(MUTED)),
                    Span::styled(msg.to_string(), Style::default().fg(MUTED).italic()),
                ]))
                .block(block),
                area,
            );
        }

        InputMode::Confirming(prompt) => {
            frame.render_widget(
                Paragraph::new(Line::from(vec![
                    Span::styled("  ⚠  ", Style::default().fg(WARNING).bold()),
                    Span::styled(prompt.clone(), Style::default().fg(TEXT_FG)),
                    Span::styled("  [y/N] ", Style::default().fg(WARNING).bold()),
                ]))
                .block(block),
                area,
            );
        }

        InputMode::Menu => {
            frame.render_widget(
                Paragraph::new(Line::from(Span::styled(
                    "  ↑/↓ pilih  ·  Enter konfirmasi  ·  q batal",
                    Style::default().fg(MUTED).italic(),
                )))
                .block(block),
                area,
            );
        }
    }
}

// ── Menu overlay ─────────────────────────────────────────────────────────────

fn render_menu(frame: &mut Frame, menu: &MenuState, area: Rect) {
    let max_item_w  = menu.items.iter().map(|s| s.chars().count()).max().unwrap_or(10) as u16;
    let content_w   = max_item_w.max(menu.title.chars().count() as u16).max(28);
    let popup_w     = (content_w + 6).min(area.width);
    let popup_h     = (menu.items.len() as u16 + 4).min(area.height);
    let popup_area  = centered_rect(popup_w, popup_h, area);

    frame.render_widget(Clear, popup_area);

    let mut lines: Vec<Line> = Vec::new();
    for (i, item) in menu.items.iter().enumerate() {
        if i == menu.selected {
            lines.push(Line::from(vec![
                Span::styled(" ❯ ", Style::default().fg(POPUP_SEL).bold()),
                Span::styled(item.clone(), Style::default().fg(Color::White).bold()),
            ]));
        } else {
            lines.push(Line::from(vec![
                Span::styled("   ", Style::default()),
                Span::styled(item.clone(), Style::default().fg(POPUP_DIM)),
            ]));
        }
    }
    lines.push(Line::raw(""));
    lines.push(Line::from(Span::styled(
        " ↑/↓ pilih  ·  Enter ok  ·  q batal",
        Style::default().fg(POPUP_DIM).italic(),
    )));

    let block = Block::default()
        .title(Line::from(vec![
            Span::raw(" "),
            Span::styled(menu.title.clone(), Style::default().fg(POPUP_SEL).bold()),
            Span::raw(" "),
        ]))
        .borders(Borders::ALL)
        .border_type(ratatui::widgets::BorderType::Rounded)
        .border_style(Style::default().fg(POPUP_SEL))
        .style(Style::default().bg(POPUP_BG));

    frame.render_widget(
        Paragraph::new(Text::from(lines))
            .block(block)
            .wrap(Wrap { trim: false }),
        popup_area,
    );
}

fn centered_rect(width: u16, height: u16, area: Rect) -> Rect {
    let x = area.x + area.width.saturating_sub(width) / 2;
    let y = area.y + area.height.saturating_sub(height) / 2;
    Rect::new(x, y, width.min(area.width), height.min(area.height))
}
