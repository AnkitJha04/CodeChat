# styles.py

DARK_THEME = """
QMainWindow {
    background-color: #1e1e1e;
}

QWidget {
    font-family: 'Segoe UI', sans-serif;
    font-size: 14px;
    color: #e0e0e0;
}

/* Input Fields */
QLineEdit, QTextEdit {
    background-color: #2d2d2d;
    border: 1px solid #3d3d3d;
    border-radius: 6px;
    padding: 8px;
    color: #ffffff;
    selection-background-color: #007acc;
}
QLineEdit:focus, QTextEdit:focus {
    border: 1px solid #007acc;
}

/* Buttons */
QPushButton {
    background-color: #007acc;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #0062a3;
}
QPushButton:disabled {
    background-color: #4a4a4a;
    color: #8a8a8a;
}
QPushButton#secondary {
    background-color: #3a3a3a;
    border: 1px solid #555;
}
QPushButton#secondary:hover {
    background-color: #4a4a4a;
}

/* Chat Display */
QTextEdit#chat_display {
    background-color: #252526;
    border: none;
    line-height: 1.6;
}

/* Group Box */
QGroupBox {
    border: 1px solid #3d3d3d;
    border-radius: 6px;
    margin-top: 20px;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
}

/* ComboBox */
QComboBox {
    background-color: #2d2d2d;
    border: 1px solid #3d3d3d;
    border-radius: 6px;
    padding: 5px;
}
QComboBox::drop-down {
    border: none;
}
"""