import os
import ollama
import numpy as np
import pickle
import zipfile
import concurrent.futures

class CoreBrain:
    def __init__(self):
        self.chunks = []       
        self.embeddings = []   
        self.sources = []      
        self.chat_history = [] 
        self.model = "llama3.1"
        self.embed_file = "temp_vectors.npy"
        self.meta_file = "temp_metadata.pkl"

    def _read_file(self, file_path):
        """Read a single file and split into chunks"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            if not content.strip(): return []
            
            # Intelligent splitting
            raw = content.split('\n\n')
            chunks = []
            current_chunk = ""
            for r in raw:
                if len(current_chunk) + len(r) < 1000:
                    current_chunk += r + "\n\n"
                else:
                    chunks.append(current_chunk)
                    current_chunk = r + "\n\n"
            if current_chunk: chunks.append(current_chunk)
            
            return [(c, file_path) for c in chunks if len(c) > 50]
        except: return []

    def ingest_codebase(self, folder_path, callback_fn, append_mode=False):
        """
        Scans and indexes code. Supports Append Mode to add to existing memory.
        """
        # 1. Manage Memory State
        if not append_mode:
            self.chunks = []
            self.embeddings = []
            self.sources = []
            self.chat_history = [] 
            existing_sources = set()
            callback_fn("🧹 Memory cleared. Starting fresh scan...")
        else:
            existing_sources = set(self.sources)
            callback_fn(f"🔗 Appending to existing {len(self.sources)} files...")
        
        # 2. Recursive Scan
        files_to_process = []
        allowed_ext = {'.py', '.js', '.ts', '.c', '.cpp', '.java', '.md', '.txt', '.html', '.css', '.json', '.rs', '.go'}
        
        for root, dirs, files in os.walk(folder_path):
            if any(x in root for x in ['node_modules', '.git', 'venv', '__pycache__', 'build', 'dist', 'target']):
                continue
            for f in files:
                if os.path.splitext(f)[1] in allowed_ext:
                    full_path = os.path.join(root, f)
                    if full_path not in existing_sources:
                        files_to_process.append(full_path)

        if not files_to_process: return "No new valid files found."

        # 3. Parallel Read
        callback_fn(f"📖 Reading {len(files_to_process)} new files...")
        all_data = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = executor.map(self._read_file, files_to_process)
            for res in results: all_data.extend(res)

        # 4. Embed
        total = len(all_data)
        callback_fn(f"🧠 Embedding {total} new chunks...")
        
        new_embeds = []
        for i, (chunk, path) in enumerate(all_data):
            try:
                self.chunks.append(chunk)
                self.sources.append(path)
                
                response = ollama.embeddings(model=self.model, prompt=chunk)
                new_embeds.append(response['embedding'])

                if i % 10 == 0:
                    prog = int((i / total) * 100)
                    callback_fn(f"⚡ Processing: {prog}%")
            except: pass

        if new_embeds:
            new_embeds_np = np.array(new_embeds)
            if len(self.embeddings) > 0:
                self.embeddings = np.concatenate((self.embeddings, new_embeds_np), axis=0)
            else:
                self.embeddings = new_embeds_np

        return f"Success: Added {len(files_to_process)} files."

    def save_snapshot(self, filepath):
        try:
            np.save(self.embed_file, self.embeddings)
            with open(self.meta_file, 'wb') as f:
                pickle.dump({'chunks': self.chunks, 'sources': self.sources, 'history': self.chat_history}, f)
            with zipfile.ZipFile(filepath, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.write(self.embed_file)
                zf.write(self.meta_file)
            return "Success"
        except Exception as e: return str(e)

    def load_snapshot(self, filepath):
        try:
            with zipfile.ZipFile(filepath, 'r') as zf: zf.extractall(".")
            self.embeddings = np.load(self.embed_file)
            with open(self.meta_file, 'rb') as f:
                data = pickle.load(f)
                self.chunks = data['chunks']
                self.sources = data['sources']
                self.chat_history = data.get('history', [])
            return f"Success: Loaded {len(self.chunks)} chunks."
        except Exception as e: return str(e)

    def ask_question(self, query):
        if not self.chunks: return "Please load a codebase first.", []

        query_vec = np.array(ollama.embeddings(model=self.model, prompt=query)['embedding'])
        similarities = np.dot(self.embeddings, query_vec)
        top_indices = np.argsort(similarities)[-5:][::-1]

        relevant_chunks = [self.chunks[i] for i in top_indices]
        relevant_sources = [self.sources[i] for i in top_indices]
        
        context_text = "\n\n".join(relevant_chunks)
        
        messages = [{'role': 'system', 'content': f"You are an expert Developer. Answer using ONLY this context:\n{context_text}"}]
        messages.extend(self.chat_history[-4:]) 
        messages.append({'role': 'user', 'content': query})

        try:
            response = ollama.chat(model=self.model, messages=messages)
            ans = response['message']['content']
            self.chat_history.append({'role': 'user', 'content': query})
            self.chat_history.append({'role': 'assistant', 'content': ans})
            return ans, relevant_sources
        except Exception as e: return f"Error: {str(e)}", []