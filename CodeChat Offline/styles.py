# --- PALETTE ---
BG_WINDOW = "#090909"     # Deepest Black
BG_CHAT = "#000000"       # Pure Black for contrast
BG_INPUT = "#161616"      # Input Bar

# --- BUBBLES ---
USER_BG = "#005c4b"       # WhatsApp Green
USER_BORDER = "#007a63"
AI_BG = "#1f1f1f"         # Dark Card
AI_BORDER = "#333333"

# --- ACCENTS ---
ACCENT = "#5865F2"        # Blurple
SUCCESS = "#23a559"       # Green
WARNING = "#ffa500"       # Orange
ERROR = "#ff4444"         # Red

TEXT_WHITE = "#e9edef"
TEXT_GRAY = "#aebac1"

PRO_STYLE = f"""
QMainWindow {{ background-color: {BG_WINDOW}; }}

/* --- HEADER --- */
QFrame#Header {{
    background-color: {BG_INPUT}; 
    border-bottom: 1px solid #222;
}}
QLabel {{ font-family: 'Segoe UI', 'Helvetica Neue', sans-serif; }}

/* --- CHAT AREA --- */
QTextBrowser {{
    background-color: {BG_CHAT};
    border: none;
    selection-background-color: {ACCENT};
    padding: 20px;
}}

/* --- SCROLLBARS --- */
QScrollBar:vertical {{
    background: {BG_CHAT};
    width: 12px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: #333;
    min-height: 40px;
    border-radius: 6px;
    margin: 2px;
}}
QScrollBar::handle:vertical:hover {{ background: #555; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}

/* --- INPUT FIELD --- */
QLineEdit {{
    background-color: #202020;
    color: white;
    border: 1px solid #333;
    border-radius: 24px;
    padding: 12px 24px;
    font-size: 15px;
    selection-background-color: {ACCENT};
}}
QLineEdit:focus {{ 
    border: 1px solid {ACCENT}; 
    background-color: #262626;
}}
QLineEdit:disabled {{
    background-color: #1a1a1a;
    color: #555;
    border: 1px solid #222;
}}

/* --- BUTTONS --- */
QPushButton {{
    background-color: #262626;
    color: #ccc;
    border: 1px solid #333;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
    font-size: 13px;
}}
QPushButton:hover {{ 
    background-color: #333; 
    color: white; 
    border: 1px solid #555;
}}
QPushButton:pressed {{ background-color: #444; }}
QPushButton:disabled {{
    background-color: #1a1a1a;
    color: #444;
    border: 1px solid #222;
}}

/* --- SPECIAL BUTTONS --- */
QPushButton#VoiceBtn {{ border: 1px solid #555; }}
QPushButton#VoiceBtn:checked {{ 
    background-color: {ERROR}; 
    border: 1px solid #ff0000; 
    color: white;
}}
"""
# --- STYLESHEET FOR PRO THEME ---