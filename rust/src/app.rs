use tokio::sync::mpsc;
use tui_input::Input;

use crate::config::Limits;
use crate::llm::ToolCall;
use crate::provider::Provider;

pub const SYSTEM_PROMPT: &str = "\
Kamu Voca, asisten coding yang ringkas dan membantu. Kamu punya tool untuk \
melihat folder, mencari, membaca, menulis/mengedit file, dan menjalankan perintah. \
Pakai tool seperlunya. Jawab singkat dalam bahasa yang digunakan pengguna.";

// ─── Events ─────────────────────────────────────────────────────────────────

#[derive(Debug)]
#[allow(dead_code)]
pub enum AppEvent {
    Key(crossterm::event::KeyEvent),
    Mouse(crossterm::event::MouseEvent),
    Resize(u16, u16),
    Tick,

    // LLM streaming
    LlmChunk(String),
    LlmComplete(String, Vec<ToolCall>),
    LlmError(String),

    // Voice
    StartListening,
    VoiceResult(String),
    VoiceSpeak(String),

    // Tools
    ToolResult(String, String),
    ConfirmAnswer(bool),
}

// ─── Chat ───────────────────────────────────────────────────────────────────

#[derive(Clone, Debug)]
pub struct ChatBubble {
    pub role: BubbleRole,
    pub content: String,
}

#[derive(Clone, Debug, PartialEq)]
pub enum BubbleRole {
    System,
    User,
    Assistant,
    Tool,
}

// ─── Modes & Options ────────────────────────────────────────────────────────

#[derive(Clone, Debug, PartialEq)]
pub enum InputMode {
    Normal,
    Listening,
    Processing,
    Menu,
    #[allow(dead_code)]
    Confirming(String), // reserved: konfirmasi tool (belum dipakai di MVP auto-approve)
}

#[derive(Clone, Debug)]
pub struct VoiceOpts {
    pub speak: bool,
    pub listen: bool,
    pub lang: String,
}

#[derive(Clone, Debug)]
pub struct MenuState {
    pub title: String,
    pub items: Vec<String>,
    pub selected: usize,
    pub kind: MenuKind,
}

#[derive(Clone, Debug, PartialEq)]
pub enum MenuKind {
    Model,
    Language,
}

// ─── App State ──────────────────────────────────────────────────────────────

pub struct App {
    // Chat history
    pub messages: Vec<ChatBubble>,
    pub current_stream: String,
    pub is_streaming: bool,
    pub scroll_offset: u16,
    pub is_at_bottom: bool,
    pub total_lines: u16,

    // Input
    pub input: Input,
    pub input_mode: InputMode,
    pub menu: Option<MenuState>,

    // Config
    pub provider: Provider,
    pub voice: VoiceOpts,
    pub limits: Limits,

    // Animation
    pub spinner_frame: usize,
    pub spinner_msg: String,

    // Voice text override: true saat user tekan 't' di mic-mode untuk beralih ketik
    pub voice_text_mode: bool,

    // Runtime
    pub should_quit: bool,
    pub tx: mpsc::UnboundedSender<AppEvent>,
    pub llm_messages: Vec<crate::llm::Message>,
    pub tools_schema: serde_json::Value,
    pub bridge: Option<crate::voicebridge::VoiceBridge>,
    pub client: reqwest::Client,
}

impl App {
    pub fn new(
        provider: Provider,
        voice: VoiceOpts,
        limits: Limits,
        client: reqwest::Client,
        tx: mpsc::UnboundedSender<AppEvent>,
    ) -> Self {
        App {
            messages: Vec::new(),
            current_stream: String::new(),
            is_streaming: false,
            scroll_offset: 0,
            is_at_bottom: true,
            total_lines: 0,
            input: Input::default(),
            input_mode: InputMode::Normal,
            menu: None,
            provider,
            voice,
            limits,
            spinner_frame: 0,
            spinner_msg: String::new(),
            voice_text_mode: false,
            should_quit: false,
            tx,
            llm_messages: vec![crate::llm::Message::new("system", SYSTEM_PROMPT)],
            tools_schema: crate::tools::tools_schema(),
            bridge: None,
            client,
        }
    }

    // ── Scroll ──────────────────────────────────────────────────────────────

    pub fn scroll_up(&mut self, n: u16) {
        self.scroll_offset = self.scroll_offset.saturating_sub(n);
        self.is_at_bottom = false;
    }

    pub fn scroll_down(&mut self, n: u16, visible_h: u16) {
        let max = self.total_lines.saturating_sub(visible_h);
        self.scroll_offset = (self.scroll_offset + n).min(max);
        self.is_at_bottom = self.scroll_offset >= max;
    }

    pub fn scroll_to_bottom(&mut self, visible_h: u16) {
        self.scroll_offset = self.total_lines.saturating_sub(visible_h);
        self.is_at_bottom = true;
    }

    // ── Chat bubbles ─────────────────────────────────────────────────────────

    pub fn push_system(&mut self, msg: &str) {
        self.messages.push(ChatBubble { role: BubbleRole::System, content: msg.to_string() });
    }

    pub fn push_user(&mut self, msg: &str) {
        self.messages.push(ChatBubble { role: BubbleRole::User, content: msg.to_string() });
    }

    pub fn push_tool(&mut self, msg: &str) {
        self.messages.push(ChatBubble { role: BubbleRole::Tool, content: msg.to_string() });
    }

    // ── Streaming ────────────────────────────────────────────────────────────

    pub fn start_streaming(&mut self, msg: &str) {
        self.current_stream.clear();
        self.is_streaming = true;
        self.input_mode = InputMode::Processing;
        self.spinner_msg = msg.to_string();
        self.spinner_frame = 0;
    }

    pub fn append_chunk(&mut self, chunk: &str) {
        self.current_stream.push_str(chunk);
    }

    pub fn finish_streaming(&mut self) {
        if !self.current_stream.is_empty() {
            self.messages.push(ChatBubble {
                role: BubbleRole::Assistant,
                content: self.current_stream.clone(),
            });
        }
        self.current_stream.clear();
        self.is_streaming = false;
        self.input_mode = InputMode::Normal;
    }

    // ── Banner ───────────────────────────────────────────────────────────────

    pub fn push_banner(&mut self) {
        let cwd = std::env::current_dir()
            .map(|p| home_short(&p.to_string_lossy()))
            .unwrap_or_default();
        let mode = match (self.voice.listen, self.voice.speak) {
            (true, _)      => "suara (hands-free)",
            (false, true)  => "ketik + suara",
            _              => "ketik",
        };
        let msg = format!(
            "╭──────────────────────────────────────────────────\n\
             │ V O C A  ·  AI Coding Assistant\n\
             ├──────────────────────────────────────────────────\n\
             │ model  : {} · {}\n\
             │ bahasa : {}\n\
             │ folder : {}\n\
             │ mode   : {}\n\
             ╰──────────────────────────────────────────────────",
            self.provider.name, self.provider.model,
            self.voice.lang.to_uppercase(),
            cwd, mode,
        );
        self.push_system(&msg);
    }
}

fn home_short(path: &str) -> String {
    if let Some(home) = dirs::home_dir() {
        let h = home.to_string_lossy();
        if let Some(rest) = path.strip_prefix(h.as_ref()) {
            return format!("~{rest}");
        }
    }
    path.to_string()
}
