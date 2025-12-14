import uvicorn
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
from backend import CoreBrain
import secrets
import os
import base64
from datetime import datetime

app = FastAPI(title="CodeChat Team Server")
brain = CoreBrain()

ACCESS_TOKENS = {} 
USER_SESSIONS = {} 
TEAM_HISTORY = []  
ACTIVE_USERS = {} 

class Query(BaseModel): 
    text: str
    public: bool = False 

class Invite(BaseModel): email: str; role: str 
class FileChunk(BaseModel): text: str; source: str
class IngestRequest(BaseModel): 
    chunks: List[FileChunk]
    append_mode: bool = True 

class SyncPayload(BaseModel): b64_data: str 
class HostLog(BaseModel): query: str; answer: str 

def get_user(x_access_token: str = Header(...)):
    if x_access_token not in ACCESS_TOKENS:
        raise HTTPException(status_code=401, detail="Invalid Token")
    ACTIVE_USERS[x_access_token] = datetime.now()
    return {"token": x_access_token, "info": ACCESS_TOKENS[x_access_token]}

@app.post("/generate_invite")
def create_invite(inv: Invite):
    token = secrets.token_hex(16)
    ACCESS_TOKENS[token] = {"email": inv.email, "role": inv.role}
    USER_SESSIONS[token] = [] 
    return {"status": "Invite generated", "token": token}

@app.post("/logout")
def logout_user(x_access_token: str = Header(...)):
    if x_access_token in ACTIVE_USERS:
        del ACTIVE_USERS[x_access_token]
    return {"status": "Logged out"}

@app.post("/sync_brain")
def sync_brain(payload: SyncPayload):
    print("⚡ HOST SYNC REQUEST RECEIVED")
    try:
        file_bytes = base64.b64decode(payload.b64_data)
        with open("server_brain.brain", "wb") as f: f.write(file_bytes)
        res = brain.load_snapshot("server_brain.brain")
        if "Success" in res:
            print(f"✅ BRAIN SYNCED: {len(brain.chunks)} chunks.")
            return {"status": "Server Brain Synced", "chunks": len(brain.chunks)}
        else:
            raise HTTPException(status_code=500, detail=f"Failed to load: {res}")
    except Exception as e:
        print(f"❌ SYNC ERROR: {e}")
        raise HTTPException(status_code=500, detail=f"Sync Error: {str(e)}")

# --- NEW: Allow Collaborators to Download Brain for 'Save Session' ---
@app.get("/download_brain")
def download_brain(user_data: dict = Depends(get_user)):
    # Create a fresh snapshot on server
    res = brain.save_snapshot("server_download.brain")
    if "Success" in res and os.path.exists("server_download.brain"):
        return FileResponse("server_download.brain", filename="codechat_brain.brain")
    raise HTTPException(status_code=500, detail="Could not generate brain snapshot")

@app.post("/query")
def query_brain(q: Query, user_data: dict = Depends(get_user)):
    token = user_data['token']
    email = user_data['info']['email']
    if len(brain.chunks) == 0:
        return {"answer": "⚠️ Server Brain is empty. Ask the Host to load code.", "sources": []}
    ans, srcs = brain.ask_question(q.text, history=USER_SESSIONS[token])
    if q.public:
        TEAM_HISTORY.append({"user": email, "query": q.text, "answer": ans})
        if len(TEAM_HISTORY) > 50: TEAM_HISTORY.pop(0) 
    return {"answer": ans, "sources": srcs}

@app.post("/ingest")
def ingest_remote(req: IngestRequest, user_data: dict = Depends(get_user)):
    print(f"📥 UPLOAD REQUEST from {user_data['info']['email']} | Mode: {'Append' if req.append_mode else 'Single'}")
    if user_data['info']['role'] != "collaborator":
        raise HTTPException(status_code=403, detail="Guests cannot upload code.")
    try:
        tuples = [(c.text, c.source) for c in req.chunks]
        brain.ingest_remote_data(tuples, lambda x: print(f"-> {x}"), append_mode=req.append_mode)
        brain.save_snapshot("server_brain.brain")
        return {"status": "Indexed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/host_log")
def log_host_activity(log: HostLog):
    TEAM_HISTORY.append({"user": "HOST (Admin)", "query": log.query, "answer": log.answer})
    if len(TEAM_HISTORY) > 50: TEAM_HISTORY.pop(0)
    return {"status": "logged"}

@app.get("/check_role")
def check_role(user_data: dict = Depends(get_user)):
    return {"role": user_data['info']['role']}

@app.get("/team_activity")
def get_team_activity(x_access_token: Optional[str] = Header(None)):
    if x_access_token and x_access_token in ACCESS_TOKENS:
        ACTIVE_USERS[x_access_token] = datetime.now()
    return {"history": TEAM_HISTORY}

@app.get("/active_users")
def get_active_users():
    now = datetime.now()
    active_list = []
    to_remove = []
    for token, last_seen in ACTIVE_USERS.items():
        if (now - last_seen).total_seconds() > 60: 
            to_remove.append(token)
        else:
            info = ACCESS_TOKENS.get(token, {"email": "Unknown", "role": "Unknown"})
            active_list.append({"email": info['email'], "role": info['role']})
    for t in to_remove:
        del ACTIVE_USERS[t]
    return {"users": active_list}

if __name__ == "__main__":
    print("\n" + "="*50)
    print("   🚀 SERVER STARTED: VERSION 14.0 (FINAL)      ")
    print("   ✅ ALL FEATURES & CONTEXT AWARE              ")
    print("="*50 + "\n")
    if os.path.exists("server_brain.brain"): 
        print("📂 Found saved brain, loading...")
        brain.load_snapshot("server_brain.brain")
    uvicorn.run(app, host="0.0.0.0", port=8000)