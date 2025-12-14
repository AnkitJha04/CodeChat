# backend.py
import os
import glob
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.llms import Ollama
from langchain_community.chains import RetrievalQA

class RAGBackend:
    def __init__(self, model_name="llama3"):
        self.model_name = model_name
        self.qa_chain = None
        self.vector_db = None
        
        print(f"Initializing RAG Backend with {model_name}...")
        self.embeddings = OllamaEmbeddings(model=model_name)
        self.llm = Ollama(model=model_name)

    def ingest_codebase(self, directory_path):
        """Reads code files, splits them, and builds the Vector DB."""
        if not os.path.exists(directory_path):
            return False, "Directory does not exist."

        try:
            # 1. Gather Files (Add more extensions if needed)
            extensions = ["*.py", "*.js", "*.html", "*.css", "*.cpp", "*.h", "*.java", "*.txt", "*.md"]
            files = []
            for ext in extensions:
                files.extend(glob.glob(os.path.join(directory_path, "**", ext), recursive=True))
            
            if not files:
                return False, "No code files found."

            # 2. Load Content
            documents = []
            for f in files:
                try:
                    loader = TextLoader(f, encoding='utf-8')
                    documents.extend(loader.load())
                except Exception:
                    continue # Skip binary or weirdly encoded files

            # 3. Split Text
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            texts = text_splitter.split_documents(documents)

            if not texts:
                return False, "No valid text found in files."

            # 4. Create Vector DB (In-memory for session)
            # We recreate it every time a new folder is loaded to keep it fresh
            self.vector_db = Chroma.from_documents(
                documents=texts, 
                embedding=self.embeddings
            )

            # 5. Build Chain
            retriever = self.vector_db.as_retriever(search_kwargs={"k": 3})
            self.qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=retriever,
                return_source_documents=True
            )

            return True, f"Success: Indexed {len(files)} files."

        except Exception as e:
            return False, f"Ingestion Error: {str(e)}"

    def query(self, user_query):
        """Queries the RAG chain."""
        if not self.qa_chain:
            return "System: No codebase loaded. Please ask the Host to load a folder."
        
        try:
            response = self.qa_chain.invoke(user_query)
            answer = response['result']
            
            # Extract sources
            sources = []
            if 'source_documents' in response:
                for doc in response['source_documents']:
                    if 'source' in doc.metadata:
                        sources.append(os.path.basename(doc.metadata['source']))
            
            # Remove duplicates
            sources = list(set(sources))
            
            if sources:
                answer += f"\n\n--- Source Files: {', '.join(sources)} ---"
            
            return answer
        except Exception as e:
            return f"AI Error: {str(e)}"