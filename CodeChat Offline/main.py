import sys
import os
import markdown
import pyttsx3
import speech_recognition as sr
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTextBrowser, QLineEdit, QPushButton, 
                             QFileDialog, QLabel, QFrame)
from PyQt6.QtCore import QThread, pyqtSignal, Qt

from backend import CoreBrain
from styles import PRO_STYLE, USER_BG, USER_BORDER, AI_BG, AI_BORDER, TEXT_WHITE, TEXT_GRAY

# --- WORKERS ---
class VoiceLoop(QThread):
    update_status = pyqtSignal(str)
    user_spoke = pyqtSignal(str)
    ai_replied = pyqtSignal(str, list)
    finished = pyqtSignal()
    def __init__(self, brain):
        super().__init__()
        self.brain = brain
        self.is_running = True
        self.recognizer = sr.Recognizer()
        self.engine = pyttsx3.init()
        try: self.engine.setProperty('rate', 160)
        except: pass
    def run(self):
        while self.is_running:
            try:
                self.update_status.emit("🎤 Listening...")
                with sr.Microphone() as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    audio = self.recognizer.listen(source, timeout=5)
                self.update_status.emit("Processing...")
                text = self.recognizer.recognize_google(audio)
                if not text: continue
                self.user_spoke.emit(text)
                if "goodbye" in text.lower():
                    self.stop()
                    break
                self.update_status.emit("Thinking...")
                ans, srcs = self.brain.ask_question(text)
                self.ai_replied.emit(ans, srcs)
                self.update_status.emit("🗣️ Speaking...")
                self.engine.say(ans)
                self.engine.runAndWait()
            except: pass
        self.finished.emit()
    def stop(self):
        self.is_running = False
        self.engine.stop()

class TaskWorker(QThread):
    msg_signal = pyqtSignal(str)
    result_signal = pyqtSignal(object)
    def __init__(self, brain, task, data=None, append_mode=False):
        super().__init__()
        self.brain = brain
        self.task = task
        self.data = data
        self.append_mode = append_mode

    def run(self):
        if self.task == "ingest": 
            res = self.brain.ingest_codebase(self.data, self.msg_signal.emit, self.append_mode)
        elif self.task == "save": res = self.brain.save_snapshot(self.data)
        elif self.task == "load": res = self.brain.load_snapshot(self.data)
        elif self.task == "query": 
            res = self.brain.ask_question(self.data)
            self.result_signal.emit(res)
            return
        self.result_signal.emit(res)

# --- MAIN UI ---
class CoreApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.brain = CoreBrain()
        self.voice_thread = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("CodeChat Pro - MultiWorkspace")
        self.resize(1300, 950)
        self.setStyleSheet(PRO_STYLE)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)

        # --- 1. HEADER ---
        header = QFrame()
        header.setFixedHeight(80)
        header.setStyleSheet("background-color: #1e1e1e; border-bottom: 1px solid #333;")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(30, 0, 30, 0)
        h_layout.setSpacing(15)
        
        logo_lbl = QLabel("⚡")
        logo_lbl.setStyleSheet("font-size: 28px; color: #ffeb3b;")
        title_lbl = QLabel("CodeChat")
        title_lbl.setStyleSheet("font-size: 22px; font-weight: 800; color: white;")
        
        self.status_pill = QLabel(" Waiting ")
        self.status_pill.setFixedHeight(28)
        self.status_pill.setStyleSheet("background-color: #555; color: #ccc; border-radius: 14px; padding: 0 12px; font-weight: bold; font-size: 12px;")
        
        h_layout.addWidget(logo_lbl)
        h_layout.addWidget(title_lbl)
        h_layout.addSpacing(10)
        h_layout.addWidget(self.status_pill)
        h_layout.addStretch()
        
        # Mode Toggle
        self.btn_mode = QPushButton("⚡ Single Mode")
        self.btn_mode.setCheckable(True)
        self.btn_mode.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_mode.clicked.connect(self.toggle_mode)
        self.btn_mode.setStyleSheet("""
            QPushButton { background-color: #2b2b2b; color: #aaa; border: 1px solid #444; }
            QPushButton:checked { background-color: #7b1fa2; color: white; border: 1px solid #9c27b0; }
        """)
        h_layout.addWidget(self.btn_mode)

        # Buttons
        self.btn_new = QPushButton("📂 New Project")
        self.btn_new.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_new.clicked.connect(self.do_ingest)
        
        self.btn_load = QPushButton("📂 Load")
        self.btn_load.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_load.clicked.connect(self.do_load)

        self.btn_save = QPushButton("💾 Save")
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.clicked.connect(self.do_save)
        
        self.btn_call = QPushButton("📞 Voice Mode")
        self.btn_call.setCheckable(True)
        self.btn_call.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_call.clicked.connect(self.toggle_voice)
        
        h_layout.addWidget(self.btn_new)
        h_layout.addWidget(self.btn_load)
        h_layout.addWidget(self.btn_save)
        h_layout.addWidget(self.btn_call)
        
        layout.addWidget(header)

        # --- 2. CHAT ---
        self.chat_area = QTextBrowser()
        self.chat_area.setOpenExternalLinks(True)
        layout.addWidget(self.chat_area)

        # --- 3. INPUT ---
        input_frame = QFrame()
        input_frame.setFixedHeight(110)
        input_frame.setStyleSheet("background-color: #161616; border-top: 1px solid #222;")
        i_layout = QHBoxLayout(input_frame)
        i_layout.setContentsMargins(30, 20, 30, 20)
        i_layout.setSpacing(15)
        
        self.inp = QLineEdit()
        self.inp.setPlaceholderText("Please load a project first...")
        self.inp.returnPressed.connect(self.ask_text)
        
        self.btn_send = QPushButton("➤")
        self.btn_send.setFixedSize(55, 50)
        self.btn_send.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_send.clicked.connect(self.ask_text)
        self.btn_send.setStyleSheet("background-color: #5865F2; color: white; border-radius: 25px; font-size: 22px; border: none; padding-bottom: 4px;")
        
        i_layout.addWidget(self.inp)
        i_layout.addWidget(self.btn_send)
        layout.addWidget(input_frame)

        self.lock_ui()

    # --- UI LOGIC ---
    def toggle_mode(self):
        if self.btn_mode.isChecked(): self.btn_mode.setText("🔗 Append Mode")
        else: self.btn_mode.setText("⚡ Single Mode")

    def lock_ui(self):
        self.btn_save.setEnabled(False)
        self.btn_call.setEnabled(False)
        self.inp.setEnabled(False)
        self.btn_send.setEnabled(False)
        self.inp.setPlaceholderText("⚠ Please load a project first...")
        self.btn_save.setStyleSheet("color: #555; border: 1px solid #333;")
        self.btn_call.setStyleSheet("color: #555; border: 1px solid #333;")

    def unlock_ui(self):
        self.btn_save.setEnabled(True)
        self.btn_call.setEnabled(True)
        self.inp.setEnabled(True)
        self.btn_send.setEnabled(True)
        self.inp.setPlaceholderText("Ask your codebase...")
        self.inp.setFocus()
        self.btn_save.setStyleSheet("")
        self.btn_call.setStyleSheet("")
        self.set_state(" Ready ", "#23a559")

    def add_msg(self, text, msg_type="user", srcs=None):
        align = "left"
        row_html = ""
        gap = "20"
        
        if msg_type == "user":
            align = "right"
            bg_color = USER_BG
            border = USER_BORDER
            avatar = "👤"
            avatar_bg = "#00a884"
            title = "You"
            radius = "18px 0 18px 18px"
            row_html = f"""
                <td valign="top">
                    <div style="background-color:{bg_color}; border:1px solid {border}; color:{TEXT_WHITE}; padding:16px 20px; border-radius:{radius}; font-size:15px; min-width:100px; max-width:800px; box-shadow: 0 4px 8px rgba(0,0,0,0.2);">
                        <div style="font-weight:bold; font-size:11px; color:#aebac1; margin-bottom:6px;">{title}</div>
                        {text}
                    </div>
                </td>
                <td width="{gap}"></td>
                <td valign="top" width="50">
                    <div style="background-color:{avatar_bg}; width:44px; height:44px; border-radius:22px; text-align:center; font-size:24px; line-height:44px; color:white; border: 2px solid #161616;">{avatar}</div>
                </td>
            """
        elif msg_type == "ai":
            align = "left"
            bg_color = AI_BG
            border = AI_BORDER
            avatar = "🤖"
            avatar_bg = "#5865F2"
            title = "Assistant"
            radius = "0 18px 18px 18px"
            content = markdown.markdown(text, extensions=['fenced_code', 'codehilite'], extension_configs={'codehilite': {'noclasses': True, 'pygments_style': 'monokai'}})
            if srcs:
                files = list(set([os.path.basename(s) for s in srcs]))
                content += f"<div style='margin-top:12px; padding-top:12px; border-top:1px solid #444; font-size:11px; color:{TEXT_GRAY};'>📚 <b>Source:</b> {', '.join(files)}</div>"
            row_html = f"""
                <td valign="top" width="50">
                    <div style="background-color:{avatar_bg}; width:44px; height:44px; border-radius:22px; text-align:center; font-size:24px; line-height:44px; color:white; border: 2px solid #161616;">{avatar}</div>
                </td>
                <td width="{gap}"></td>
                <td valign="top">
                    <div style="background-color:{bg_color}; border:1px solid {border}; color:{TEXT_WHITE}; padding:16px 20px; border-radius:{radius}; font-size:15px; min-width:100px; box-shadow: 0 4px 8px rgba(0,0,0,0.2);">
                        {content}
                    </div>
                </td>
            """
        elif msg_type == "voice":
            align = "right"
            bg_color = "#7b1fa2"
            border = "#9c27b0"
            avatar = "📞"
            avatar_bg = "#9c27b0"
            radius = "18px 0 18px 18px"
            row_html = f"""
                <td valign="top">
                    <div style="background-color:{bg_color}; border:1px solid {border}; color:white; padding:16px 20px; border-radius:{radius}; font-size:15px; box-shadow: 0 4px 8px rgba(0,0,0,0.2);">
                        <div style="font-weight:bold; font-size:11px; color:#e1bee7; margin-bottom:5px;">Voice Input</div>
                        {text}
                    </div>
                </td>
                <td width="{gap}"></td>
                <td valign="top" width="50">
                    <div style="background-color:{avatar_bg}; width:44px; height:44px; border-radius:22px; text-align:center; font-size:24px; line-height:44px; color:white; border: 2px solid #161616;">{avatar}</div>
                </td>
            """

        html = f"""
        <table width="100%" border="0" cellpadding="0" cellspacing="0" style="margin-bottom: 25px;">
            <tr><td align="{align}"><table border="0" cellpadding="0" cellspacing="0"><tr>{row_html}</tr></table></td></tr>
        </table>
        """
        self.chat_area.append(html)
        sb = self.chat_area.verticalScrollBar()
        sb.setValue(sb.maximum())

    # --- ACTIONS ---
    def set_state(self, txt, color):
        self.status_pill.setText(txt)
        self.status_pill.setStyleSheet(f"background-color: {color}; color: white; border-radius: 14px; padding: 0 12px; font-weight: bold; font-size: 12px;")
        QApplication.processEvents()

    def update_voice_state(self, status_text):
        if "Listening" in status_text: self.set_state(status_text, "#e53935")
        elif "Processing" in status_text: self.set_state(status_text, "#5865F2")
        elif "Speaking" in status_text: self.set_state(status_text, "#23a559")
        else: self.set_state(status_text, "#555")

    def do_ingest(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Code")
        if folder:
            is_append = self.btn_mode.isChecked()
            if not is_append: self.chat_area.clear()
            self.set_state("Indexing...", "#ff9800")
            self.worker = TaskWorker(self.brain, "ingest", folder, append_mode=is_append)
            self.worker.msg_signal.connect(lambda s: self.status_pill.setText(s))
            self.worker.result_signal.connect(lambda s: self.finish(s))
            self.worker.start()

    def do_save(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save", "", "Brain (*.brain)")
        if path:
            self.set_state("Saving...", "#ff9800")
            self.worker = TaskWorker(self.brain, "save", path)
            self.worker.result_signal.connect(self.finish)
            self.worker.start()

    def do_load(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load", "", "Brain (*.brain)")
        if path:
            self.set_state("Loading...", "#ff9800")
            self.worker = TaskWorker(self.brain, "load", path)
            self.worker.result_signal.connect(self.finish)
            self.worker.start()

    def finish(self, res):
        if "Success" in res or "Loaded" in res:
            self.unlock_ui()
            self.add_msg(f"✅ {res}", "ai")
        else:
            self.add_msg(f"❌ Error: {res}", "ai")
            self.set_state(" Error ", "#ff4444")

    def ask_text(self):
        txt = self.inp.text().strip()
        if not txt: return
        self.add_msg(txt, "user")
        self.inp.clear()
        self.set_state("Thinking...", "#5865F2")
        self.worker = TaskWorker(self.brain, "query", txt)
        self.worker.result_signal.connect(lambda r: self.add_msg(r[0], "ai", r[1]))
        self.worker.start()

    def toggle_voice(self):
        if self.btn_call.isChecked():
            if not self.brain.chunks:
                self.btn_call.setChecked(False)
                return
            self.voice_thread = VoiceLoop(self.brain)
            self.voice_thread.update_status.connect(self.update_voice_state)
            self.voice_thread.user_spoke.connect(lambda t: self.add_msg(t, "voice"))
            self.voice_thread.ai_replied.connect(lambda a, s: self.add_msg(a, "ai", s))
            self.voice_thread.finished.connect(lambda: self.set_state(" Ready ", "#23a559"))
            self.voice_thread.start()
        else:
            if self.voice_thread: self.voice_thread.stop()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CoreApp()
    window.show()
    sys.exit(app.exec())