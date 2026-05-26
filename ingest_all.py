import os
import requests
import json
import uuid
import logging
import time
from scripts.parsers import parse_pdf, parse_excel, parse_text, parse_word, ParserError

# Configuration
QDRANT_URL = "http://localhost:6333"
OLLAMA_URL = "http://localhost:11434"
COLLECTION_NAME = "km_knowledge"
MODEL_EMBED = "mxbai-embed-large"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Ingestor")

def clean_text(text):
    return "".join(c for c in text if c.isprintable() or c in "\n\t ")

def get_embedding(text):
    text = clean_text(text)
    for attempt in range(5):
        try:
            res = requests.post(f"{OLLAMA_URL}/api/embeddings", json={"model": MODEL_EMBED, "prompt": text}, timeout=90)
            res.raise_for_status()
            return res.json()["embedding"]
        except Exception as e:
            logger.warning(f"Embedding attempt {attempt+1} failed: {e}")
            time.sleep(3)
    return None

def ingest_file(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in ['.pdf', '.xlsx', '.xls', '.docx', '.txt', '.md']:
        return
        
    logger.info(f"Ingesting: {file_path}")
    
    try:
        if ext == '.pdf':
            content = parse_pdf(file_path)
        elif ext in ['.xlsx', '.xls']:
            content = parse_excel(file_path)
        elif ext == '.docx':
            content = parse_word(file_path)
        elif ext in ['.txt', '.md']:
            content = parse_text(file_path)
        else:
            return
            
        raw_chunks = content.split("\n\n---CHUNK---\n\n")
        chunks = [c.strip() for c in raw_chunks if c.strip()]
                
        points = []
        filename = os.path.basename(file_path)
        for i, chunk in enumerate(chunks):
            text_to_embed = f"Source File: {filename}\nTechnical Data:\n{chunk}"
            
            vector = get_embedding(text_to_embed)
            if not vector: continue
            
            points.append({
                "id": str(uuid.uuid4()),
                "vector": vector,
                "payload": {
                    "text": text_to_embed,
                    "filename": filename,
                    "path": file_path,
                    "chunk_index": i
                }
            })
            
            if len(points) >= 20:
                res = requests.put(f"{QDRANT_URL}/collections/{COLLECTION_NAME}/points?wait=true", json={"points": points})
                res.raise_for_status()
                points = []
            
        if points:
            res = requests.put(f"{QDRANT_URL}/collections/{COLLECTION_NAME}/points?wait=true", json={"points": points})
            res.raise_for_status()
            
    except Exception as e:
        logger.error(f"Error ingesting {file_path}: {e}")

def main():
    logger.info("Resetting collection...")
    requests.delete(f"{QDRANT_URL}/collections/{COLLECTION_NAME}")
    res = requests.put(f"{QDRANT_URL}/collections/{COLLECTION_NAME}", json={
        "vectors": {"size": 1024, "distance": "Cosine"}
    })
    res.raise_for_status()
    
    db_path = "Database"
    
    files_to_ingest = []
    for root, dirs, files in os.walk(db_path):
        # Skip hidden directories
        if any(d.startswith('.') for d in root.split(os.sep)):
            continue
        for file in files:
            if file.startswith('.'): continue
            files_to_ingest.append(os.path.join(root, file))
                
    logger.info(f"Starting ingestion for {len(files_to_ingest)} files...")
    for path in files_to_ingest:
        ingest_file(path)

if __name__ == "__main__":
    main()
