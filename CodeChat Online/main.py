# main.py
import sys
import json
import threading
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTextEdit, QLineEdit, QPushButton, 
                             QLabel, QFileDialog, QComboBox, QCheckBox, 
                             QGroupBox, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSlot

import styles
from server import NetworkManager

# Try importing Backend; if fails, user can only be Guest
try:
    from backend import RAGBackend
    HAS_BACKEND = True
except ImportError:
    HAS_BACKEND = False

class CollaborationApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Talk to Your Code - Team Edition")
        self.resize(1000, 750)
        self.setStyleSheet(styles.DARK_THEME)

        self.network = NetworkManager()
        self.rag_engine = None
        self.username = "User"
        self.chat_history = []

        # Connect Network Signals
        self.network.msg_received.connect(self.on_network_message)
        self.network.status_update.connect(self.update_status_bar)

        self.setup_ui()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- Top Section: Connection ---
        conn_group = QGroupBox("Setup")
        conn_layout = QHBoxLayout()

        self.role_combo = QComboBox()
        self.role_combo.addItems(["Host (Server)", "Collaborator (Guest)"])
        self.role_combo.currentIndexChanged.connect(self.toggle_role_ui)

        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("Host IP Address (e.g. 192.168.1.5)")
        
        self.port_input = QLineEdit("5555")
        self.port_input.setFixedWidth(60)

        self.connect_btn = QPushButton("Start / Connect")
        self.connect_btn.clicked.connect(self.handle_connection)

        self.load_code_btn = QPushButton("Load Codebase")
        self.load_code_btn.setObjectName("secondary")
        self.load_code_btn.clicked.connect(self.select_codebase)

        conn_layout.addWidget(QLabel("Role:"))
        conn_layout.addWidget(self.role_combo)
        conn_layout.addWidget(self.ip_input)
        conn_layout.addWidget(self.port_input)
        conn_layout.addWidget(self.connect_btn)
        conn_layout.addWidget(self.load_code_btn)
        conn_group.setLayout(conn_layout)
        main_layout.addWidget(conn_group)

        # --- Middle Section: Chat ---
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        main_layout.addWidget(self.chat_display)

        # --- Bottom Section: Input ---
        input_layout = QHBoxLayout()
        
        self.msg_input = QLineEdit()
        self.msg_input.setPlaceholderText("Ask a question...")
        self.msg_input.returnPressed.connect(self.send_message)
        
        self.public_chk = QCheckBox("Share Chat")
        self.public_chk.setChecked(True)
        self.public_chk.setToolTip("If unchecked, only the Host sees this.")

        send_btn = QPushButton("Send")
        send_btn.clicked.connect(self.send_message)

        input_layout.addWidget(self.msg_input)
        input_layout.addWidget(self.public_chk)
        input_layout.addWidget(send_btn)
        main_layout.addLayout(input_layout)

        # --- Footer: Save/Load ---
        footer_layout = QHBoxLayout()
        save_btn = QPushButton("Save History")
        save_btn.setObjectName("secondary")
        save_btn.clicked.connect(self.save_history)
        
        load_btn = QPushButton("Load History")
        load_btn.setObjectName("secondary")
        load_btn.clicked.connect(self.load_history)

        self.status_lbl = QLabel("Ready")
        self.status_lbl.setStyleSheet("color: #888;")

        footer_layout.addWidget(save_btn)
        footer_layout.addWidget(load_btn)
        footer_layout.addStretch()
        footer_layout.addWidget(self.status_lbl)
        main_layout.addLayout(footer_layout)

        self.toggle_role_ui()

    def toggle_role_ui(self):
        role = self.role_combo.currentText()
        if "Host" in role:
            self.ip_input.setEnabled(False)
            self.ip_input.setText("Localhost")
            self.connect_btn.setText("Start Server")
            self.load_code_btn.setVisible(True)
            self.username = "Host"
        else:
            self.ip_input.setEnabled(True)
            self.ip_input.setText("")
            self.connect_btn.setText("Connect")
            self.load_code_btn.setVisible(False)
            self.username = "Guest"

    def update_status_bar(self, msg):
        self.status_lbl.setText(msg)

    def append_chat(self, sender, text, is_private=False):
        """Updates the chat window with HTML formatting."""
        color = "#00aaff" if sender == "Host" or sender == "System" else "#ffaa00"
        if sender == "Me": color = "#00aaff"
        
        style = ""
        badge = ""
        if is_private:
            style = "background-color: #2d2d2d; padding: 5px; border-radius: 5px;"
            badge = " <span style='color: #ff5555; font-size: 10px;'>[PRIVATE]</span>"

        html = f"<div style='margin-bottom: 8px; {style}'><b style='color:{color};'>{sender}</b>{badge}: {text}</div>"
        self.chat_display.append(html)
        self.chat_history.append({"sender": sender, "text": text, "private": is_private})

    # --- Actions ---

    def handle_connection(self):
        port = int(self.port_input.text())
        role = self.role_combo.currentText()

        if "Host" in role:
            if not HAS_BACKEND:
                QMessageBox.critical(self, "Error", "Backend libraries (LangChain/Ollama) not found.\nYou can only run as Guest.")
                return

            self.rag_engine = RAGBackend() # Initialize AI
            if self.network.start_host(port):
                self.connect_btn.setDisabled(True)
                self.role_combo.setDisabled(True)
        else:
            ip = self.ip_input.text()
            if self.network.connect_client(ip, port):
                self.connect_btn.setDisabled(True)
                self.role_combo.setDisabled(True)

    def select_codebase(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Codebase Folder")
        if folder and self.rag_engine:
            self.update_status_bar(f"Indexing {folder}...")
            # Run ingestion in thread
            threading.Thread(target=self._ingest_worker, args=(folder,), daemon=True).start()

    def _ingest_worker(self, folder):
        success, msg = self.rag_engine.ingest_codebase(folder)
        # Use QMetaObject or signal to update UI from thread, but emit via network helper is easier here
        # Creating a self-signal is best practice, but for brevity we use the network signal wrapper
        self.network.status_update.emit(msg)

    # --- Messaging Logic ---

    def send_message(self):
        text = self.msg_input.text().strip()
        if not text: return

        self.msg_input.clear()
        is_public = self.public_chk.isChecked()

        # Display locally
        self.append_chat("Me", text, is_private=not is_public)

        payload = {
            "type": "query",
            "sender": self.username,
            "text": text,
            "public": is_public
        }

        if "Host" in self.role_combo.currentText():
            # Host processing their own query
            self.process_host_query(payload)
        else:
            # Guest sending to Host
            self.network.send_payload(payload)

    @pyqtSlot(dict)
    def on_network_message(self, payload):
        """Handle incoming JSON payload."""
        msg_type = payload.get("type")
        sender = payload.get("sender")
        text = payload.get("text")
        is_public = payload.get("public", True)

        # Check Privacy: If private and I am not the sender AND not the target (Host is implied target)
        # However, for simplicity, Host broadcasts all, clients filter.
        target_user = payload.get("target_user") 
        if not is_public and target_user and target_user != self.username and self.username != "Host":
            return # Ignore private messages meant for others

        if msg_type == "query":
            # Only Host cares about "query" type
            if "Host" in self.role_combo.currentText():
                self.append_chat(sender, text, is_private=not is_public)
                self.process_host_query(payload)
        
        elif msg_type == "chat":
            # A public message from someone else
            if sender != self.username:
                self.append_chat(sender, text)

        elif msg_type == "response":
            # AI Response
            self.append_chat("System", text, is_private=not is_public)

    def process_host_query(self, payload):
        """Host logic: Run RAG and reply."""
        # 1. Broadcast the question if public (so others see "Guest asked X")
        if payload["public"] and payload["sender"] != "Host":
            chat_payload = {"type": "chat", "sender": payload["sender"], "text": payload["text"]}
            self.network.send_payload(chat_payload)

        # 2. Run AI in thread
        threading.Thread(target=self._rag_worker, args=(payload,), daemon=True).start()

    def _rag_worker(self, payload):
        if not self.rag_engine: return

        answer = self.rag_engine.query(payload["text"])
        
        response_payload = {
            "type": "response",
            "sender": "System",
            "text": answer,
            "public": payload["public"],
            "target_user": payload["sender"]
        }

        # Send to network (Host will broadcast)
        self.network.send_payload(response_payload)
        
        # Manually trigger local UI update for Host (since Host socket doesn't loopback receive)
        self.network.msg_received.emit(response_payload)

    # --- Persistence ---

    def save_history(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Chat", "", "JSON Files (*.json)")
        if path:
            with open(path, 'w') as f:
                json.dump(self.chat_history, f, indent=4)
            self.update_status_bar("Chat saved.")

    def load_history(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Chat", "", "JSON Files (*.json)")
        if path:
            try:
                with open(path, 'r') as f:
                    history = json.load(f)
                    self.chat_display.clear()
                    self.chat_history = []
                    for h in history:
                        self.append_chat(h['sender'], h['text'], h.get('private', False))
                self.update_status_bar("Chat loaded.")
            except Exception as e:
                QMessageBox.critical(self, "Error", "Invalid file.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CollaborationApp()
    window.show()
    sys.exit(app.exec_())