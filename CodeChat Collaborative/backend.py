import os
import ollama
import numpy as np
import pickle
import zipfile
import concurrent.futures
import requests
import json

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter, Language
    HAS_LANGCHAIN = True
except ImportError:
    HAS_LANGCHAIN = False

class CoreBrain:
    def __init__(self):
        self.chunks = []       
        self.embeddings = []   
        self.sources = []      
        self.local_history = [] 
        self.model = "llama3.1" 
        self.embed_file = "temp_vectors.npy"
        self.meta_file = "temp_metadata.pkl"

    def _read_file(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            if not content.strip(): return []
            
            if HAS_LANGCHAIN:
                ext = os.path.splitext(file_path)[1]
                lang_map = {'.py': Language.PYTHON, '.js': Language.JS, '.ts': Language.TS}
                lang = lang_map.get(ext, Language.PYTHON)
                splitter = RecursiveCharacterTextSplitter.from_language(
                    language=lang, chunk_size=1000, chunk_overlap=100
                )
                docs = splitter.create_documents([content])
                return [(d.page_content, file_path) for d in docs]
            
            return [(content, file_path)]
        except: return []

    def ingest_codebase(self, folder_path, callback_fn, append_mode=False):
        if not append_mode:
            self.chunks = []; self.embeddings = []; self.sources = []; self.local_history = []
            callback_fn("🧹 Memory wiped. Starting fresh...")
        
        files = []
        valid = {'.py', '.js', '.ts', '.c', '.cpp', '.java', '.md', '.txt', '.json', '.rs', '.go'}
        for r, d, f in os.walk(folder_path):
            if any(x in r for x in ['node_modules', '.git', 'venv', '__pycache__']): continue
            for file in f:
                if os.path.splitext(file)[1] in valid:
                    files.append(os.path.join(r, file))

        if not files: return "No new files found."
        
        callback_fn(f"📖 Reading {len(files)} files...")
        data = []
        with concurrent.futures.ThreadPoolExecutor() as ex:
            res = ex.map(self._read_file, files)
            for r in res: data.extend(r)
        
        return self._embed_data(data, callback_fn)

    def ingest_remote_data(self, file_data_list, callback_fn, append_mode=True):
        if not append_mode:
            self.chunks = []; self.embeddings = []; self.sources = []; self.local_history = []
            callback_fn("🧹 Server Brain Wiped (Single Mode Active)")
        return self._embed_data(file_data_list, callback_fn)

    def _embed_data(self, data_tuples, callback_fn):
        total = len(data_tuples)
        callback_fn(f"🧠 Embedding {total} chunks...")
        new_vecs = []
        
        for i, (chunk, path) in enumerate(data_tuples):
            try:
                self.chunks.append(chunk)
                self.sources.append(path)
                resp = ollama.embeddings(model=self.model, prompt=chunk)
                new_vecs.append(resp['embedding'])
                if i % 5 == 0: callback_fn(f"⚡ Processing: {int((i/total)*100)}%")
            except: pass
            
        if new_vecs:
            new_np = np.array(new_vecs)
            if len(self.embeddings) == 0:
                self.embeddings = new_np
            else:
                self.embeddings = np.concatenate((self.embeddings, new_np), axis=0)
        
        return f"Success: Indexed {total} chunks."

    def save_snapshot(self, filepath):
        try:
            if len(self.embeddings) == 0: return "Error: Brain is empty."
            np.save(self.embed_file, self.embeddings)
            with open(self.meta_file, 'wb') as f:
                pickle.dump({'chunks': self.chunks, 'sources': self.sources}, f)
            with zipfile.ZipFile(filepath, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.write(self.embed_file); zf.write(self.meta_file)
            if os.path.exists(self.embed_file): os.remove(self.embed_file)
            if os.path.exists(self.meta_file): os.remove(self.meta_file)
            return "Success"
        except Exception as e: return str(e)

    def load_snapshot(self, filepath):
        try:
            if not os.path.exists(filepath): return "File not found"
            self.chunks = []; self.sources = []; self.embeddings = []
            with zipfile.ZipFile(filepath, 'r') as zf: zf.extractall(".")
            self.embeddings = np.load(self.embed_file)
            with open(self.meta_file, 'rb') as f:
                d = pickle.load(f)
                self.chunks = d['chunks']; self.sources = d['sources']
            if os.path.exists(self.embed_file): os.remove(self.embed_file)
            if os.path.exists(self.meta_file): os.remove(self.meta_file)
            return "Success"
        except Exception as e: return str(e)

    def get_team_chat(self):
        try:
            res = requests.get("http://localhost:8000/team_activity", timeout=0.5)
            if res.status_code == 200: return res.json()['history']
            return []
        except: return []

    def get_connected_users(self):
        try:
            res = requests.get("http://localhost:8000/active_users", timeout=0.5)
            if res.status_code == 200: return res.json()['users']
            return []
        except: return []

    def ask_question(self, query, history=None, is_public=False):
        if not self.chunks or len(self.embeddings) == 0: 
            return "❌ Brain is empty. Please load code on Host and click Sync.", []

        active_history = history if history is not None else self.local_history

        try:
            q_vec = np.array(ollama.embeddings(model=self.model, prompt=query)['embedding'])
            sims = np.dot(self.embeddings, q_vec)
            top_idx = np.argsort(sims)[-5:][::-1]
            ctx = "\n\n".join([self.chunks[i] for i in top_idx])
            srcs = [self.sources[i] for i in top_idx]
        except Exception as e: return f"❌ Retrieval Error: {str(e)}", []

        system_msg = (
            "You are an expert Developer. "
            "Use the provided Context to answer the user's technical question. "
            f"\n\nContext:\n{ctx}"
        )

        msgs = [{'role': 'system', 'content': system_msg}]
        msgs.extend(active_history[-4:]) 
        msgs.append({'role': 'user', 'content': query})

        try:
            res = ollama.chat(
                model=self.model, 
                messages=msgs,
                options={'num_ctx': 4096},
                stream=False 
            )
            ans = res['message']['content']
            
            active_history.append({'role': 'user', 'content': query})
            active_history.append({'role': 'assistant', 'content': ans})
            
            if is_public:
                try: requests.post("http://localhost:8000/host_log", json={"query": query, "answer": ans}, timeout=0.5)
                except: pass
            
            return ans, srcs
        except Exception as e: return f"AI Error: {e}", []

class RemoteBrain:
    def __init__(self, url, token):
        self.url = url.rstrip('/')
        self.token = token
        self.chunks = [1] 

    def ask_question(self, query, history=None, is_public=False):
        try:
            headers = {"x-access-token": self.token}
            payload = {"text": query, "public": is_public}
            res = requests.post(f"{self.url}/query", json=payload, headers=headers, timeout=60)
            if res.status_code == 200:
                d = res.json()
                return d.get('answer', 'Error'), d.get('sources', [])
            return f"❌ Server Error: {res.text}", []
        except Exception as e: return f"❌ Connection Error: {e}", []

    def get_team_chat(self):
        try:
            headers = {"x-access-token": self.token}
            res = requests.get(f"{self.url}/team_activity", headers=headers, timeout=2)
            if res.status_code == 200: return res.json()['history']
            return []
        except: return []

    def get_connected_users(self):
        try:
            headers = {"x-access-token": self.token}
            res = requests.get(f"{self.url}/active_users", headers=headers, timeout=2)
            if res.status_code == 200: return res.json()['users']
            return []
        except: return []

    def ingest_codebase(self, folder_path, callback_fn, append_mode=True):
        callback_fn("📤 Scanning files...")
        files_data = []
        valid = {'.py', '.js', '.ts', '.c', '.cpp', '.java', '.md', '.txt', '.json', '.rs', '.go'}
        for r, d, f in os.walk(folder_path):
            if any(x in r for x in ['node_modules', '.git', 'venv']): continue
            for file in f:
                if os.path.splitext(file)[1] in valid:
                    try:
                        with open(os.path.join(r, file), 'r', encoding='utf-8', errors='ignore') as fo:
                            content = fo.read()
                        if content.strip():
                            files_data.append({"text": content, "source": f"RemoteUpload/{file}"})
                    except: pass
        
        if not files_data: return "No valid files found."
        
        total = len(files_data)
        batch_size = 5
        callback_fn(f"🚀 Uploading {total} files in batches...")
        headers = {"x-access-token": self.token}
        
        for i in range(0, total, batch_size):
            batch = files_data[i : i + batch_size]
            try:
                payload = {"chunks": batch, "append_mode": append_mode}
                res = requests.post(f"{self.url}/ingest", json=payload, headers=headers, timeout=30)
                if res.status_code != 200: return f"❌ Failed at file {i}: {res.text}"
                callback_fn(f"✅ Uploaded {min(i + batch_size, total)}/{total}")
            except Exception as e: return f"❌ Connection Lost: {e}"
            
        return "✅ All Files Uploaded Successfully"

    # --- NEW: Downloads brain from Server ---
    def save_snapshot(self, filepath):
        try:
            headers = {"x-access-token": self.token}
            res = requests.get(f"{self.url}/download_brain", headers=headers, stream=True, timeout=60)
            if res.status_code == 200:
                with open(filepath, 'wb') as f:
                    for chunk in res.iter_content(chunk_size=8192):
                        f.write(chunk)
                return "Success"
            else:
                return f"Server Error: {res.text}"
        except Exception as e:
            return f"Download Failed: {e}"

    # --- RESTRICTED: Collaborators cannot load local files into Remote Brain ---
    def load_snapshot(self, *args): 
        return "❌ Permission Denied: Only Host can load Brains."