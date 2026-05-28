# CodeChat – Team Edition

> **Private AI Workspace for Engineering Teams**
> A fully local, collaborative RAG-based platform that lets teams query, understand, and navigate large codebases using local LLMs — without sending proprietary code to the cloud.

---

## 🚀 Overview

CodeChat – Team Edition is a privacy-first AI collaboration platform designed for development teams that want the power of AI-assisted code understanding **without sacrificing source-code privacy**.

Unlike cloud-based coding assistants, CodeChat runs entirely on local infrastructure using **Ollama + Llama 3.1**, enabling teams to transform their repositories into a searchable, queryable **“AI Second Brain.”**

The platform follows a **Client–Server architecture**, where a centralized Host machine performs:

* embedding generation,
* vector indexing,
* and LLM inference,

while lightweight clients connect securely over the network.

---

# ✨ Key Features
## 🔒 100% Local & Private
* No cloud APIs
* No code leakage
* No subscriptions
* Fully self-hosted

Powered entirely by:
* Ollama
* Local vector embeddings
* FastAPI backend

---

## 👥 Collaborative Team Workspace

Multiple users can connect to a shared AI knowledge base without downloading the original source code.

### Roles:

| Role         | Permissions      |
| ------------ | ---------------- |
| Host         | Full control     |
| Collaborator | Can append files |
| Guest        | Read-only access |

---

## 🧠 Smart Memory System

Save and restore:

* vector indices (“Brains”)
* chat sessions
* project states

Avoid re-indexing large repositories repeatedly.

---

## ⚡ Query Your Entire Codebase

Ask natural-language questions like:

```bash
Where is JWT authentication implemented?
```

```bash
Explain the database architecture.
```

```bash
Which files handle websocket communication?
```

```bash
How does the FastAPI backend communicate with the client?
```

---

## 🎤 Voice Mode

Hands-free AI interaction using:

* SpeechRecognition
* PyAudio

---

## 📜 Smart Team Stream

Collaborative chat system with intelligent scrolling behavior:

* preserves reading position,
* prevents interruptions from new messages.

---

# 🏗️ Architecture

                ┌────────────────────┐
                │    Client Apps     │
                │  (PyQt6 Desktop)   │
                └─────────┬──────────┘
                          │
                          │ HTTP/WebSocket
                          ▼
                ┌────────────────────┐
                │   FastAPI Server   │
                │  Central AI Brain  │
                └─────────┬──────────┘
                          │
         ┌────────────────┼────────────────┐
         ▼                ▼                ▼
 ┌────────────┐   ┌──────────────┐   ┌─────────────┐
 │  Ollama    │   │ Vector Store │   │ Chat Memory │
 │ Llama 3.1  │   │   (NumPy)    │   │ Sessions    │
 └────────────┘   └──────────────┘   └─────────────┘

# 🛠️ Tech Stack

| Component    | Technology                  |
| ------------ | --------------------------- |
| GUI          | PyQt6                       |
| Backend      | FastAPI + Uvicorn           |
| AI Runtime   | Ollama                      |
| LLM          | Llama 3.1                   |
| Vector Store | Custom NumPy embeddings     |
| Networking   | Requests / HTTP             |
| Speech       | SpeechRecognition + PyAudio |


# 📦 Installation
## Prerequisites

* Python 3.10+
* Ollama installed and running

Download Ollama:
[https://ollama.com](https://ollama.com)

---

## Clone Repository
bash
git clone https://github.com/yourusername/codechat-team.git
cd codechat-team

---

## Install Dependencies
bash
pip install -r requirements.txt
Or manually:
bash
pip install PyQt6 ollama numpy requests fastapi uvicorn speechrecognition markdown pyaudio

---

## Pull Llama 3.1
bash
ollama pull llama3.1

---

# 🚀 Running CodeChat

# Option A — Offline Single User Mode

Start the application:

```bash
python main.py
```

### Features:

* Local repository indexing
* AI code querying
* Session memory
* Offline operation

---

# Option B — Team Collaboration Mode

## Start Host Server

```bash
python server.py
```

---

## Launch Client

```bash
python main.py
```

---

## Connect Team Members

1. Click **🌐 Join Team**
2. Enter:

   * Host URL
   * Access Token
3. Start querying instantly

---

# 📂 Project Structure

```text
codechat-team/
│
├── main.py          # PyQt6 frontend client
├── server.py        # FastAPI backend server
├── backend.py       # AI + vector logic
├── styles.py        # UI styling
├── requirements.txt
└── README.md
```

---

# 🎯 Why CodeChat Exists

Modern engineering teams increasingly rely on AI to:

* understand large codebases,
* accelerate onboarding,
* debug systems,
* and improve productivity.

But existing cloud-based AI tools require uploading proprietary code to third-party servers.

CodeChat solves this by enabling:
✅ fully local inference
✅ collaborative querying
✅ secure code understanding
✅ centralized AI infrastructure

without exposing sensitive source code.

---

# 🔥 Core Design Principles

## Local-First AI

All inference happens locally using Ollama.

---

## Lightweight Infrastructure

Uses a custom NumPy vector system instead of requiring:

* Pinecone
* Milvus
* external vector databases

---

## Decoupled Architecture

Frontend and backend are separated for:

* scalability
* responsiveness
* modularity

---

## Privacy By Design

No external APIs.
No telemetry.
No cloud dependency.

---

# 🧪 Current Status

> ⚠️ **Developer Preview / Beta Release**

CodeChat is currently under active development.

Planned improvements include:
* advanced repo indexing
* semantic memory optimization
* multi-model support
* plugin ecosystem
* enterprise authentication
* containerized deployment
* distributed inference

# 🤝 Contributing

Pull requests are welcome.

For major changes:

1. Open an issue
2. Discuss proposed changes
3. Submit PR

---

# 📌 Roadmap

## v0.1 Beta
* Local RAG
* Team collaboration
* Smart memory
* Voice mode
---
## v0.2
* Multi-repository support
* Advanced chunking
* Semantic search optimization
* Better onboarding
---
## v0.3
* Web dashboard
* Docker deployment
* Team analytics
* Plugin architecture
---

# 🌟 Vision
CodeChat aims to become:
> **The private AI operating system for engineering teams.**
A fully local collaborative intelligence layer for:

* software teams,
* robotics companies,
* AI startups,
* research labs,
* and secure engineering environments.

# ⭐ Support The Project
If you found this interesting:

* Star the repository
* Share feedback
* Open issues
* Contribute improvements

---

# 👨‍💻 Author :- Ankit Jha

AI • Embedded Systems • Robotics • Computer Vision
Building intelligent systems at the intersection of:
* AI
* automation
* robotics
* and real-world engineering.
