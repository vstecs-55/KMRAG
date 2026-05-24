import os
import requests
import uuid
import logging
from scripts.parsers import parse_excel, semantic_chunking, parse_pdf, parse_word

logging.basicConfig(level=logging.INFO)
QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
COLLECTION_NAME = "km_knowledge"

def get_embedding(text):
    res = requests.post(f"{OLLAMA_URL}/api/embeddings", json={"model": "mxbai-embed-large", "prompt": text})
    res.raise_for_status()
    return res.json()["embedding"]

def upsert_qdrant(point_id, vector, text, metadata):
    # FIX: use named vector {"dense": vector}
    res = requests.put(f"{QDRANT_URL}/collections/{COLLECTION_NAME}/points", json={
        "points": [{"id": point_id, "vector": {"dense": vector}, "payload": {"text": text, **metadata}}]
    })
    res.raise_for_status()
    return res.json()

def run_test():
    db_path = "/home/admin/Documents/Projects/KM RAG/Database"
    for file in os.listdir(db_path):
        path = os.path.join(db_path, file)
        if not os.path.isfile(path): continue
        
        try:
            if file.endswith(".txt") or file.endswith(".md"):
                with open(path, 'r') as f: text = f.read()
            elif file.endswith(".csv") or file.endswith(".xlsx"):
                text = parse_excel(path)
            elif file.endswith(".pdf"):
                text = parse_pdf(path)
            else:
                continue
                
            chunks = semantic_chunking(text)
            for i, chunk in enumerate(chunks):
                vector = get_embedding(chunk)
                upsert_qdrant(str(uuid.uuid4()), vector, chunk, {"filename": file, "chunk": i})
                logging.info(f"Successfully upserted {file} chunk {i}")
        except Exception as e:
            logging.error(f"Failed to process {file}: {e}")

if __name__ == "__main__":
    run_test()
