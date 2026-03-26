⚡ CodeChat - Team Edition
CodeChat is a standalone, privacy-focused RAG (Retrieval-Augmented Generation) tool designed for secure team collaboration. Unlike cloud-based AI editors, CodeChat runs 100% locally using Ollama (Llama 3.1), allowing you to turn your codebase into a queryable "Second Brain" without sending sensitive code to the cloud.

📖 Project Genesis & Architecture
The Problem
Modern development teams want to leverage AI to understand and navigate large codebases, but existing cloud-based solutions (like GitHub Copilot or ChatGPT) require sending proprietary, sensitive source code to third-party servers. Furthermore, running local AI on every team member's machine is hardware-intensive and creates fragmented knowledge silos.

The Approach
The goal was to build a secure, localized Client-Server architecture. By centralizing the heavy lifting (embedding generation and LLM inference) on a single powerful "Host" machine using Ollama and FastAPI, the rest of the team can connect via a lightweight PyQt6 desktop client. This ensures zero data leakage while democratizing access to the codebase's "Second Brain."

Iterations
Iteration 1 (Core Local RAG): Developed a single-user desktop application capable of indexing a local folder and querying it using Ollama and a custom NumPy vector store.

Iteration 2 (Memory & State): Introduced the "Smart Memory" feature, allowing users to save and load compiled vector indices ("Brains") and chat histories to eliminate redundant processing time.

Iteration 3 (Team Connectivity): Transitioned to a FastAPI backend, enabling secure network connections and real-time collaboration without requiring clients to download the source files.

Iteration 4 (Access Control & Voice): Implemented Role-Based Security (Host, Collaborator, Guest) to protect the integrity of the Host's data, and added hands-free Voice Mode.

Key Design Choices
100% Local Inference: Opted for Ollama (Llama 3.1) over external APIs to guarantee absolute privacy and zero subscription costs.

Custom Vector Store over Heavy DBs: Chose a lightweight, custom NumPy implementation for vector embeddings rather than requiring users to set up complex databases like Pinecone or Milvus.

Decoupled Architecture: Separated the AI backend (FastAPI) from the frontend GUI (PyQt6). This ensures the client remains fast and responsive, even when the Host is processing heavy embeddings.

Smart Scrolling "Team Stream": Designed the UI to lock the scroll position when reading history, preventing new collaborative messages from interrupting the user's reading flow.

Daily Time Commitment
During active development, this project required an average commitment of [Insert Number, e.g., 2-3 hours] per day, split between backend API structuring, UI/UX design in PyQt, and refining the local RAG prompt engineering.

🚀 Key Features
👥 Real-Time Collaboration: Instantly share your codebase's knowledge. A Host indexes the code, and Collaborators/Guests can query it remotely without downloading the source files.

🔒 100% Local & Private: Powered by Ollama. No API keys, no subscriptions, and no data leaks.

🧠 Smart Memory: Save and Load "Brains" (vector indices) or full "Sessions" (Brain + Chat History) to resume work anytime.

🛡️ Role-Based Security:

Host: Full control (Index/Wipe/Save/Load).

Collaborator: Can append new files to the knowledge base but cannot overwrite/wipe the Host's data.

Guest: Read-only access to query the knowledge base.

🎤 Voice Mode: Hands-free coding assistance with speech-to-text.

📜 Smart Scrolling: The "Team Stream" locks your scroll position when reading history, so new messages don't interrupt you.

🛠️ Tech Stack
GUI: Python (PyQt6)

Server: FastAPI, Uvicorn

AI Backend: Ollama (Llama 3.1)

Vector Store: Local vector embeddings (custom NumPy implementation)

Audio/Speech: SpeechRecognition, PyAudio

📦 Installation
Prerequisites
Python 3.10+ installed.

Ollama installed and running. Download Ollama

Setup
Clone this repository:

Bash
git clone https://github.com/yourusername/codechat-team.git 
cd codechat-team
Install required Python libraries:

Bash
pip install PyQt6 ollama numpy requests fastapi uvicorn speechrecognition markdown pyaudio
(Note: On Windows, if pyaudio fails, you may need to install it via a .whl file or use pipwin install pyaudio.)

Pull the Llama 3.1 model:

Bash
ollama pull llama3.1
📖 How to Use
Option A: Single User (Offline Mode)
Run the application:

Bash
python main.py
Click 📂 New Project to select a folder containing your code.

Start chatting with your codebase in the "My Session" tab.

Use 💾 Save Session to back up your progress.

Option B: Team Mode (Host & Clients)
1. Start the Host (Server)
The person with the powerful GPU/RAM should act as the Host.

Open a terminal and run the server:

Bash
python server.py
Open another terminal and run the client:

Bash
python main.py
In the client app, click 🔄 Sync Server.

Click 📧 Invite to generate tokens for your team:

Guest Token: For read-only users.

Collaborator Token: For users who can add code.

2. Join as a Teammate

Run the client on your machine:

Bash
python main.py
Click 🌐 Join Team.

Enter the Host's URL (e.g., http://192.168.1.5:8000 or a Ngrok URL) and your Token.

Start querying the codebase immediately!

📂 File Structure
main.py: The frontend GUI application (PyQt6).

server.py: The FastAPI server that manages the "Central Brain" and user sessions.

backend.py: Handles AI logic (Ollama), embedding generation, and vector storage.

styles.py: CSS stylesheets for the dark mode UI.

🤝 Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.
