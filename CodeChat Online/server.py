# server.py
import socket
import threading
import json
from PyQt5.QtCore import QObject, pyqtSignal

class NetworkManager(QObject):
    msg_received = pyqtSignal(dict)  # Emits decoded JSON dictionary
    status_update = pyqtSignal(str)  # Emits status strings for the UI

    def __init__(self):
        super().__init__()
        self.sock = None
        self.running = False
        self.is_host = False
        self.clients = []  # List of client sockets (Host only)

    def start_host(self, port=5555):
        """Starts the server logic."""
        self.is_host = True
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.bind(('0.0.0.0', port))
            self.sock.listen(5)
            self.running = True
            self.status_update.emit(f"Hosting on Port {port}...")
            threading.Thread(target=self._accept_clients, daemon=True).start()
            return True
        except Exception as e:
            self.status_update.emit(f"Error hosting: {e}")
            return False

    def connect_client(self, ip, port=5555):
        """Connects to a host."""
        self.is_host = False
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect((ip, port))
            self.running = True
            self.status_update.emit(f"Connected to {ip}:{port}")
            threading.Thread(target=self._receive_loop, args=(self.sock,), daemon=True).start()
            return True
        except Exception as e:
            self.status_update.emit(f"Connection failed: {e}")
            return False

    def _accept_clients(self):
        """Loop to accept new incoming connections (Host only)."""
        while self.running:
            try:
                client, addr = self.sock.accept()
                self.clients.append(client)
                self.status_update.emit(f"New Collaborator joined: {addr[0]}")
                threading.Thread(target=self._receive_loop, args=(client,), daemon=True).start()
            except:
                break

    def _receive_loop(self, connection):
        """Loop to listen for messages from a specific socket."""
        while self.running:
            try:
                # Basic length-prefixed framing or raw recv (Using raw 4096 for simplicity here)
                # For production, consider using a delimiter or fixed header for large payloads
                data = connection.recv(8192) 
                if not data:
                    break
                
                msg_str = data.decode('utf-8')
                try:
                    payload = json.loads(msg_str)
                    self.msg_received.emit(payload)
                except json.JSONDecodeError:
                    print("Received malformed JSON")
            except:
                break
        
        if self.is_host and connection in self.clients:
            self.clients.remove(connection)

    def send_payload(self, payload, target_client=None):
        """
        Sends a dictionary payload.
        If Host + target_client is None -> Broadcast to all.
        If Host + target_client is set -> Send to specific.
        If Client -> Send to Host.
        """
        try:
            data = json.dumps(payload).encode('utf-8')
            
            if self.is_host:
                if target_client:
                    target_client.send(data)
                else:
                    # Broadcast
                    for c in self.clients:
                        try:
                            c.send(data)
                        except:
                            self.clients.remove(c)
            else:
                # Client sending to Host
                if self.sock:
                    self.sock.send(data)
        except Exception as e:
            print(f"Send Error: {e}")