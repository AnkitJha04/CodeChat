import sys
import os
import markdown
import speech_recognition as sr
import requests
import json
import base64
import zipfile
import shutil
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTextBrowser, QLineEdit, QPushButton, 
                             QFileDialog, QLabel, QFrame, QInputDialog, QMessageBox, 
                             QDialog, QRadioButton, QTextEdit, QTabWidget, 
                             QListWidget)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QTimer
from backend import CoreBrain, RemoteBrain
from styles import PRO_STYLE, STATUS_LOCAL, STATUS_REMOTE, STATUS_GUEST, STATUS_COLLAB

TEXT_GRAY = "#888888"

class VoiceLoop(QThread):
    update_status = pyqtSignal(str); speech_recognized = pyqtSignal(str); 
    finished = pyqtSignal(); error_signal = pyqtSignal(str)
    
    def __init__(self):
        super().__init__(); self.is_running = True; self.paused = False
        self.recognizer = sr.Recognizer()
        
    def run(self):
        try:
            with sr.Microphone() as source: pass
        except Exception as e: self.error_signal.emit(f"Mic Error: {str(e)}"); return
        
        while self.is_running:
            if self.paused: self.msleep(200); continue 
            try:
                self.update_status.emit("🎤 Listening...")
                with sr.Microphone() as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    try: audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=10)
                    except sr.WaitTimeoutError: continue 
                
                if self.paused: continue 
                self.update_status.emit("Processing...")
                try: text = self.recognizer.recognize_google(audio)
                except sr.UnknownValueError: continue 
                if text: self.speech_recognized.emit(text)
            except Exception as e: print(f"Voice Error: {e}")
        self.finished.emit()

    def pause(self): self.paused = True
    def resume(self): self.paused = False
    def stop(self): self.is_running = False

class TaskWorker(QThread):
    msg_signal = pyqtSignal(str); result_signal = pyqtSignal(object)
    
    def __init__(self, brain, task, data=None, append_mode=False, extra=None, public_flag=False, history=None):
        super().__init__(); self.brain = brain; self.task = task; self.data = data; 
        self.append_mode = append_mode; self.extra = extra; self.public_flag = public_flag
        self.history = history 

    def run(self):
        res = "Error: Unknown Task Failure"
        try:
            if self.task == "ingest": 
                res = self.brain.ingest_codebase(self.data, self.msg_signal.emit, self.append_mode)
            elif self.task == "save_brain": 
                res = self.brain.save_snapshot(self.data)
            elif self.task == "load_brain": 
                res = self.brain.load_snapshot(self.data)
            elif self.task == "save_session":
                try:
                    temp_brain = "temp_session_brain.brain"
                    temp_chat = "temp_session_chat.json"
                    save_res = self.brain.save_snapshot(temp_brain)
                    if "Success" not in save_res: raise Exception(save_res)
                    with open(temp_chat, 'w', encoding='utf-8') as f:
                        json.dump(self.extra, f, indent=2)
                    with zipfile.ZipFile(self.data, 'w', zipfile.ZIP_DEFLATED) as zf:
                        zf.write(temp_brain); zf.write(temp_chat)
                    res = "Success"
                except Exception as e: res = f"Error saving session: {e}"
                finally:
                    if os.path.exists("temp_session_brain.brain"): os.remove("temp_session_brain.brain")
                    if os.path.exists("temp_session_chat.json"): os.remove("temp_session_chat.json")
            elif self.task == "load_session":
                try:
                    with zipfile.ZipFile(self.data, 'r') as zf: zf.extractall("temp_session_extract")
                    if os.path.exists("temp_session_extract/temp_session_brain.brain"):
                        load_res = self.brain.load_snapshot("temp_session_extract/temp_session_brain.brain")
                        if "Success" not in load_res: raise Exception(load_res)
                    chat_data = []
                    if os.path.exists("temp_session_extract/temp_session_chat.json"):
                        with open("temp_session_extract/temp_session_chat.json", 'r', encoding='utf-8') as f:
                            chat_data = json.load(f)
                    res = chat_data
                except Exception as e: res = f"Error loading session: {e}"
                finally:
                    if os.path.exists("temp_session_extract"): shutil.rmtree("temp_session_extract")
            elif self.task == "query": 
                res = self.brain.ask_question(self.data, history=self.history, is_public=self.public_flag)
            elif self.task == "sync_server":
                if not isinstance(self.brain, CoreBrain): res = "ERROR|Cannot sync from Remote Mode"
                else:
                    temp_file = "temp_sync.brain"; save_res = self.brain.save_snapshot(temp_file)
                    if "Success" not in save_res: res = f"ERROR|Save Failed: {save_res}"
                    else:
                        try:
                            with open(temp_file, "rb") as f: b64_data = base64.b64encode(f.read()).decode('utf-8')
                            resp = requests.post("http://localhost:8000/sync_brain", json={"b64_data": b64_data}, timeout=30)
                            if resp.status_code == 200: res = "SUCCESS|Synced"
                            else: res = f"ERROR|Server Reject: {resp.text}"
                        except Exception as e: res = f"ERROR|Upload Failed: {e}"
                        finally: 
                            if os.path.exists(temp_file): os.remove(temp_file)
            elif self.task == "invite":
                try:
                    resp = requests.post("http://localhost:8000/generate_invite", json={"email": self.data, "role": self.extra})
                    if resp.status_code == 200: res = f"SUCCESS|{resp.json()['token']}"
                    else: res = f"ERROR|{resp.text}"
                except: res = "ERROR|Server Offline"
            self.result_signal.emit(res)
        except Exception as e: self.result_signal.emit(f"CRITICAL ERROR: {str(e)}")

class InviteDialog(QDialog):
    def __init__(self):
        super().__init__(); self.setWindowTitle("Invite Teammate"); self.resize(300, 150); self.setStyleSheet(PRO_STYLE)
        v = QVBoxLayout(self); self.email = QLineEdit(); self.email.setPlaceholderText("Enter Name")
        v.addWidget(QLabel("Name:")); v.addWidget(self.email); v.addWidget(QLabel("Role:"))
        self.r_guest = QRadioButton("Guest (Read Only)"); self.r_guest.setChecked(True)
        self.r_collab = QRadioButton("Collaborator (Can Upload)")
        v.addWidget(self.r_guest); v.addWidget(self.r_collab)
        btn = QPushButton("Generate Token & Sync"); btn.clicked.connect(self.accept); v.addWidget(btn)
    def get_data(self): return self.email.text(), "collaborator" if self.r_collab.isChecked() else "guest"

class TokenPopup(QDialog):
    def __init__(self, token):
        super().__init__(); self.setWindowTitle("Invite Generated"); self.resize(400, 300); self.setStyleSheet(PRO_STYLE)
        v = QVBoxLayout(self); lbl = QLabel("✅ Invite Created & Brain Synced!\n\nShare these 2 things:")
        lbl.setStyleSheet("color: #23a559; font-weight: bold; font-size: 14px;"); v.addWidget(lbl)
        v.addWidget(QLabel("1. The Server URL (Ngrok/Local IP):")); url_box = QLineEdit("https://postuterine-unfocused-dayle.ngrok-free.dev"); url_box.setReadOnly(True); v.addWidget(url_box)
        v.addWidget(QLabel("2. This Access Token:")); token_box = QTextEdit(token); token_box.setReadOnly(True); token_box.setStyleSheet("font-size: 13px; background-color: #111; padding: 10px;"); v.addWidget(token_box)
        ok = QPushButton("Close"); ok.clicked.connect(self.accept); v.addWidget(ok)

class CoreApp(QMainWindow):
    def __init__(self):
        super().__init__(); self.brain = CoreBrain(); self.voice_thread = None; self.chat_history_log = [] 
        self.init_ui(); self.team_timer = QTimer(); self.team_timer.timeout.connect(self.poll_updates)
        self.team_timer.start(2000) 

    def init_ui(self):
        self.setWindowTitle("CodeChat Pro - Team Edition"); self.resize(1100, 700)
        self.setStyleSheet(PRO_STYLE)
        main_widget = QWidget(); self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget); main_layout.setContentsMargins(0,0,0,0); main_layout.setSpacing(0)

        sidebar = QFrame(); sidebar.setFixedWidth(220); sidebar.setObjectName("Sidebar")
        sb_layout = QVBoxLayout(sidebar); sb_layout.setContentsMargins(15, 20, 15, 20); sb_layout.setSpacing(10)
        logo = QLabel("⚡ CodeChat"); logo.setStyleSheet("color: white; font-size: 20px; font-weight: bold; margin-bottom: 10px;")
        sb_layout.addWidget(logo)
        sb_layout.addWidget(QLabel("PROJECT"))
        self.btn_new = QPushButton("📂 New Project"); self.btn_new.clicked.connect(self.do_ingest); sb_layout.addWidget(self.btn_new)
        self.btn_mode = QPushButton("⚡ Single Mode"); self.btn_mode.setCheckable(True); self.btn_mode.clicked.connect(self.toggle_mode)
        self.btn_mode.setStyleSheet("color: #aaa; font-style: italic; border: 1px dashed #444;") 
        sb_layout.addWidget(self.btn_mode)
        
        self.btn_load_brain = QPushButton("🧠 Load Brain"); self.btn_load_brain.clicked.connect(self.do_load_brain); sb_layout.addWidget(self.btn_load_brain)
        self.btn_save_brain = QPushButton("💾 Save Brain"); self.btn_save_brain.clicked.connect(self.do_save_brain); self.btn_save_brain.setEnabled(False); sb_layout.addWidget(self.btn_save_brain)
        
        sb_layout.addSpacing(10); sb_layout.addWidget(QLabel("CHAT + CONTEXT"))
        self.btn_save_chat = QPushButton("💾 Save Session"); self.btn_save_chat.clicked.connect(self.do_save_chat); sb_layout.addWidget(self.btn_save_chat)
        self.btn_load_chat = QPushButton("📂 Load Session"); self.btn_load_chat.clicked.connect(self.do_load_chat); sb_layout.addWidget(self.btn_load_chat)
        
        sb_layout.addSpacing(10); sb_layout.addWidget(QLabel("TEAM"))
        self.btn_sync = QPushButton("🔄 Sync Server"); self.btn_sync.clicked.connect(self.do_sync); sb_layout.addWidget(self.btn_sync)
        self.btn_invite = QPushButton("📧 Invite"); self.btn_invite.clicked.connect(self.send_invite); sb_layout.addWidget(self.btn_invite)
        self.btn_join = QPushButton("🌐 Join Team"); self.btn_join.setCheckable(True); self.btn_join.clicked.connect(self.toggle_join); sb_layout.addWidget(self.btn_join)
        sb_layout.addSpacing(10); sb_layout.addWidget(QLabel("TOOLS"))
        self.btn_voice = QPushButton("📞 Voice Mode"); self.btn_voice.setCheckable(True); self.btn_voice.clicked.connect(self.toggle_voice); sb_layout.addWidget(self.btn_voice)
        sb_layout.addStretch()
        self.lbl_activity = QLabel("Ready"); self.lbl_activity.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_activity.setStyleSheet("color: #5865F2; font-size: 13px; font-weight: bold; margin-bottom: 5px;")
        sb_layout.addWidget(self.lbl_activity)
        self.user_badge = QLabel(" Local Host "); self.user_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.user_badge.setStyleSheet(f"background-color: {STATUS_LOCAL}; color: white; border-radius: 4px; padding: 5px; font-weight: bold;")
        sb_layout.addWidget(self.user_badge)
        main_layout.addWidget(sidebar)

        center_frame = QFrame(); center_layout = QVBoxLayout(center_frame); center_layout.setContentsMargins(0,0,0,0)
        self.tabs = QTabWidget()
        self.chat = QTextBrowser(); self.chat.setOpenExternalLinks(True)
        self.team_view = QTextBrowser(); self.team_view.setOpenExternalLinks(True)
        self.tabs.addTab(self.chat, "💬 My Session (Private)")
        self.tabs.addTab(self.team_view, "👥 Team Stream (Public)")
        center_layout.addWidget(self.tabs)

        inp_frame = QFrame(); inp_frame.setFixedHeight(70); inp_frame.setStyleSheet("background-color: #161616; border-top: 1px solid #222;")
        i_layout = QHBoxLayout(inp_frame); i_layout.setContentsMargins(15,10,15,10)
        self.inp = QLineEdit(); self.inp.setPlaceholderText("Ask a question..."); self.inp.returnPressed.connect(self.ask_text)
        self.btn_send = QPushButton("➤"); self.btn_send.setFixedSize(40, 40); self.btn_send.clicked.connect(self.ask_text); self.btn_send.setStyleSheet("border-radius: 20px; font-size: 18px;")
        i_layout.addWidget(self.inp); i_layout.addWidget(self.btn_send)
        center_layout.addWidget(inp_frame)
        main_layout.addWidget(center_frame)

        self.user_panel = QFrame(); self.user_panel.setFixedWidth(180); self.user_panel.setStyleSheet("background-color: #111; border-left: 1px solid #222;")
        u_layout = QVBoxLayout(self.user_panel); u_layout.setContentsMargins(10, 20, 10, 20)
        u_layout.addWidget(QLabel("🟢 ACTIVE USERS"))
        self.user_list = QListWidget(); self.user_list.setStyleSheet("background: transparent; border: none; font-size: 12px; color: #aaa;")
        u_layout.addWidget(self.user_list)
        main_layout.addWidget(self.user_panel)
        self.lock_ui()

    def set_status(self, text): self.lbl_activity.setText(text)
    def lock_ui(self): self.inp.setEnabled(False); self.btn_send.setEnabled(False); self.inp.setPlaceholderText("Load project to start...")
    def unlock_ui(self): self.inp.setEnabled(True); self.btn_send.setEnabled(True); self.inp.setPlaceholderText("Ask a question...")
    
    def toggle_mode(self):
        if self.btn_mode.isChecked():
            self.btn_mode.setText("🔗 Append Mode")
            self.btn_mode.setStyleSheet("color: #F59E0B; font-weight: bold; border: 1px solid #F59E0B;")
        else:
            self.btn_mode.setText("⚡ Single Mode")
            self.btn_mode.setStyleSheet("color: #aaa; font-style: italic; border: 1px dashed #444;")

    def poll_updates(self):
        history = self.brain.get_team_chat()
        if history:
            html = ""
            for h in history:
                color = "#5865F2" if "HOST" in h['user'] else "#F59E0B"
                html += f"""
                <div style="margin-bottom: 15px; padding: 10px; background-color: #0f0f0f; border-radius: 8px; border: 1px solid #222;">
                    <div style="color:{color}; font-size: 10px; font-weight: bold; margin-bottom: 5px;">👤 {h['user']}</div>
                    <div style="background-color: #1a1a1a; padding: 8px; border-radius: 6px; margin-bottom: 5px; border-left: 2px solid {color};">
                        <span style="color: #ccc; font-weight: bold;">Q:</span> <span style="color: #fff; white-space: pre-wrap;">{h['query']}</span>
                    </div>
                    <div style="background-color: #111; padding: 8px; border-radius: 6px; color: #aaa; font-size: 12px; white-space: pre-wrap;">
                        <span style="color: #5865F2; font-weight: bold;">AI:</span> {h['answer']}
                    </div>
                </div>
                """
            if self.team_view.toHtml() != html:
                sb = self.team_view.verticalScrollBar()
                was_at_bottom = sb.value() >= (sb.maximum() - 20)
                old_val = sb.value()
                self.team_view.setHtml(html)
                if was_at_bottom: sb.setValue(sb.maximum())
                else: sb.setValue(old_val)
        
        if hasattr(self.brain, 'get_connected_users'):
            users = self.brain.get_connected_users()
            self.user_list.clear(); self.user_list.addItem("👤 Host (Admin)")
            for u in users: self.user_list.addItem(f"🟠 {u['email']}" if u['role']=='collaborator' else f"⚪ {u['email']}")

    def ask_text(self):
        t = self.inp.text().strip(); 
        if not t: return
        self.handle_question(t)

    def handle_question(self, text):
        is_public = (self.tabs.currentIndex() == 1)
        self.inp.clear(); self.set_status("🤔 Thinking...")
        if self.voice_thread and self.voice_thread.isRunning(): self.voice_thread.pause()
        if not is_public: self.add_msg(text, "user")
        
        formatted_history = []
        for msg in self.chat_history_log[-6:]: 
            role = 'user' if msg['type'] == 'user' else 'assistant'
            formatted_history.append({'role': role, 'content': msg['content']})

        self.worker = TaskWorker(self.brain, "query", text, public_flag=is_public, history=formatted_history)
        self.worker.result_signal.connect(lambda r: self.finish_query(r, is_public))
        self.worker.start()

    def finish_query(self, result, is_public):
        if isinstance(result, str):
            ans = result; srcs = []
        elif isinstance(result, tuple) and len(result) == 2:
            ans, srcs = result
        else:
            ans = "Error: Invalid response format"; srcs = []

        self.set_status("Ready")
        if not isinstance(ans, str): ans = str(ans)
        if not is_public: self.add_msg(ans, "ai", srcs)
        if self.voice_thread and self.voice_thread.isRunning(): self.voice_thread.resume()

    def toggle_voice(self):
        if self.btn_voice.isChecked():
            self.voice_thread = VoiceLoop()
            self.voice_thread.update_status.connect(lambda s: self.set_status(s))
            self.voice_thread.speech_recognized.connect(self.handle_question)
            self.voice_thread.start()
        else: self.voice_thread.stop(); self.set_status("Ready")

    def do_ingest(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Code")
        if folder:
            is_append = self.btn_mode.isChecked() or isinstance(self.brain, RemoteBrain)
            if not is_append: self.chat.clear(); self.chat_history_log = []
            self.set_status("Indexing...")
            self.worker = TaskWorker(self.brain, "ingest", folder, is_append)
            self.worker.msg_signal.connect(lambda s: self.set_status(s))
            self.worker.result_signal.connect(self.finish_ingest); self.worker.start()

    def finish_ingest(self, res):
        if "Success" in res or "Indexed" in res: 
            self.set_status("Ready"); self.unlock_ui(); self.add_msg(f"✅ {res}", "ai")
            if not isinstance(self.brain, RemoteBrain): self.btn_save_brain.setEnabled(True)
        else: self.add_msg(f"❌ {res}", "ai"); self.set_status("Error")

    def do_sync(self): self.set_status("Syncing..."); self.worker = TaskWorker(self.brain, "sync_server"); self.worker.result_signal.connect(self.finish_sync); self.worker.start()
    def finish_sync(self, res): 
        if "SUCCESS" in res: self.set_status("Synced"); QMessageBox.information(self, "Sync", "✅ Server Updated.")
        else: self.set_status("Error"); QMessageBox.warning(self, "Sync Error", res)

    def send_invite(self):
        dlg = InviteDialog()
        if dlg.exec():
            email, role = dlg.get_data()
            if email: self.set_status("Syncing..."); self.sync_worker = TaskWorker(self.brain, "sync_server"); self.sync_worker.result_signal.connect(lambda res: self.process_invite_chain(res, email, role)); self.sync_worker.start()

    def process_invite_chain(self, sync_result, email, role):
        if "SUCCESS" not in sync_result: QMessageBox.warning(self, "Sync Failed", f"Could not sync.\n{sync_result}"); self.set_status("Error"); return
        self.set_status("Inviting..."); self.worker = TaskWorker(self.brain, "invite", email, extra=role); self.worker.result_signal.connect(self.show_invite_popup); self.worker.start()

    def show_invite_popup(self, result_str):
        self.set_status("Ready"); 
        if result_str.startswith("SUCCESS|"): TokenPopup(result_str.split("|")[1]).exec()
        else: QMessageBox.critical(self, "Error", result_str)

    def toggle_join(self):
        if self.btn_join.isChecked():
            url, ok1 = QInputDialog.getText(self, "Join Team", "Host URL:"); token, ok2 = QInputDialog.getText(self, "Auth", "Token:")
            if ok1 and ok2:
                try:
                    role_data = requests.get(f"{url}/check_role", headers={"x-access-token": token}, timeout=5).json()
                    self.brain = RemoteBrain(url, token); role = role_data['role']
                    
                    # --- COLLABORATOR UI LOCKS ---
                    # 1. Mode is locked to APPEND (Checked) to protect Host's data
                    self.btn_mode.setChecked(True)
                    self.btn_mode.setEnabled(False) 
                    self.btn_mode.setStyleSheet("color: #555; border: 1px solid #333;")

                    # 2. LOAD is disabled, SAVE is enabled (Brain & Session)
                    self.btn_load_session = getattr(self, 'btn_load_chat', None) # Alias fix if needed
                    self.btn_save_chat.setEnabled(True)
                    self.btn_load_chat.setEnabled(False) 
                    self.btn_save_brain.setEnabled(True)
                    self.btn_load_brain.setEnabled(False)

                    if role == "collaborator": 
                        self.user_badge.setText(" Remote (Collab) "); self.user_badge.setStyleSheet(f"background-color: {STATUS_COLLAB}; color: black; border-radius: 4px; padding: 5px; font-weight:bold;"); self.btn_new.setEnabled(True) 
                    else: 
                        self.user_badge.setText(" Remote (Guest) "); self.user_badge.setStyleSheet(f"background-color: {STATUS_GUEST}; color: white; border-radius: 4px; padding: 5px; font-weight:bold;"); self.btn_new.setEnabled(False) 
                    self.btn_join.setText("❌ Leave Team"); self.btn_invite.setEnabled(False); self.btn_sync.setEnabled(False)
                    self.unlock_ui(); self.add_msg(f"Connected as {role.title()}.", "ai")
                except Exception as e: self.add_msg(f"❌ Connection Failed: {e}", "ai"); self.btn_join.setChecked(False)
            else: self.btn_join.setChecked(False)
        else:
            try: requests.post(f"{self.brain.url}/logout", headers={"x-access-token": self.brain.token}, timeout=2)
            except: pass
            
            # --- RESTORE HOST UI ---
            self.brain = CoreBrain(); self.user_badge.setText(" Local Host "); self.user_badge.setStyleSheet(f"background-color: {STATUS_LOCAL}; color: white; border-radius: 4px; padding: 5px;")
            self.btn_mode.setEnabled(True); self.btn_mode.setStyleSheet("color: #aaa; font-style: italic; border: 1px dashed #444;")
            
            # Re-enable all Load/Save buttons for Host
            self.btn_save_chat.setEnabled(True)
            self.btn_load_chat.setEnabled(True)
            self.btn_save_brain.setEnabled(True)
            self.btn_load_brain.setEnabled(True)

            self.btn_join.setText("🌐 Join Team"); self.btn_invite.setEnabled(True); self.btn_sync.setEnabled(True); self.btn_new.setEnabled(True); self.lock_ui() 

    def closeEvent(self, event):
        if hasattr(self, 'brain') and isinstance(self.brain, RemoteBrain):
            try: requests.post(f"{self.brain.url}/logout", headers={"x-access-token": self.brain.token}, timeout=1)
            except: pass
        if self.voice_thread: self.voice_thread.stop()
        event.accept()

    def add_msg(self, text, type="user", srcs=None):
        self.chat_history_log.append({"type": type, "content": text, "srcs": srcs})
        align = "right" if type=="user" else "left"; bg = "#005c4b" if type=="user" else "#1f1f1f"
        content = text
        if type=="ai": content = markdown.markdown(text, extensions=['fenced_code', 'codehilite'], extension_configs={'codehilite': {'noclasses': True, 'pygments_style': 'monokai'}}); 
        if srcs: content += f"<br><hr style='border:0; border-top:1px solid #444'><small style='color:{TEXT_GRAY}'>Ref: {len(srcs)} sources</small>"
        html = f"""<table width="100%" cellpadding="5"><tr><td align="{align}"><div style="background-color:{bg}; color:#e9edef; padding:15px; border-radius:15px; max-width:600px;">{content}</div></td></tr></table>"""
        self.chat.append(html); self.chat.verticalScrollBar().setValue(self.chat.verticalScrollBar().maximum())

    def do_save_chat(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Session", f"session_{datetime.now().strftime('%Y%m%d_%H%M')}.ccsession", "CodeChat Session (*.ccsession)")
        if path:
            self.set_status("Saving Session...")
            self.worker = TaskWorker(self.brain, "save_session", path, extra=self.chat_history_log)
            self.worker.result_signal.connect(lambda res: self.set_status("Session Saved" if res=="Success" else f"Error: {res}"))
            self.worker.start()

    def do_load_chat(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Session", "", "CodeChat Session (*.ccsession)")
        if path:
            self.set_status("Loading Session...")
            self.worker = TaskWorker(self.brain, "load_session", path)
            self.worker.result_signal.connect(self.finish_load_session)
            self.worker.start()

    def finish_load_session(self, res):
        if isinstance(res, list):
            self.chat.clear()
            self.chat_history_log = []
            for msg in res: self.add_msg(msg['content'], msg['type'], msg.get('srcs'))
            self.set_status("Session Loaded"); self.unlock_ui(); self.btn_save_brain.setEnabled(True)
        else:
            self.set_status("Error"); QMessageBox.critical(self, "Load Failed", str(res))

    def do_save_brain(self): 
        path, _ = QFileDialog.getSaveFileName(self, "Save Brain", "", "Brain (*.brain)")
        if path:
            self.set_status("Saving Brain...")
            self.worker = TaskWorker(self.brain, "save_brain", path)
            self.worker.result_signal.connect(lambda res: self.set_status("Brain Saved" if res=="Success" else f"Error: {res}"))
            self.worker.start()

    def do_load_brain(self): 
        path, _ = QFileDialog.getOpenFileName(self, "Load Brain", "", "Brain (*.brain)")
        if path:
            self.set_status("Loading Brain...")
            self.worker = TaskWorker(self.brain, "load_brain", path)
            self.worker.result_signal.connect(lambda res: self.set_status("Brain Loaded" if res=="Success" else f"Error: {res}"))
            self.worker.start()

if __name__ == "__main__": app = QApplication(sys.argv); window = CoreApp(); window.show(); sys.exit(app.exec())