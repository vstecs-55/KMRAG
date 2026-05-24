import os
import requests
import json
import uuid
import logging
from scripts.parsers import parse_pdf, parse_excel, parse_text, parse_word, ParserError

# Configuration
QDRANT_URL = "http://localhost:6333"
OLLAMA_URL = "http://localhost:11434"
COLLECTION_NAME = "km_knowledge"
MODEL_EMBED = "mxbai-embed-large"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Ingestor")

def get_embedding(text):
    res = requests.post(f"{OLLAMA_URL}/api/embeddings", json={"model": MODEL_EMBED, "prompt": text})
    res.raise_for_status()
    return res.json()["embedding"]

def ingest_file(file_path):
    ext = os.path.splitext(file_path)[1].lower()
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
            logger.warning(f"Unsupported extension: {ext}")
            return
            
        # Improved chunking: include filename and use smaller chunks
        chunk_size = 800
        overlap = 150
        
        chunks = []
        if len(content) <= chunk_size:
            chunks = [content]
        else:
            start = 0
            while start < len(content):
                end = start + chunk_size
                chunks.append(content[start:end])
                start += chunk_size - overlap
                
        points = []
        import time
        for i, chunk in enumerate(chunks):
            if not chunk.strip(): continue
            # Prepend filename to chunk text to help retrieval and LLM context
            filename = os.path.basename(file_path)
            rich_chunk = f"Source File: {filename}\nContent: {chunk}"
            vector = get_embedding(rich_chunk)
            point_id = str(uuid.uuid4())
            points.append({
                "id": point_id,
                "vector": vector,
                "payload": {
                    "text": rich_chunk,
                    "filename": filename,
                    "path": file_path,
                    "chunk_index": i,
                    "timestamp": time.time()
                }
            })
            
        # Upload in batches
        if points:
            res = requests.put(f"{QDRANT_URL}/collections/{COLLECTION_NAME}/points?wait=true", json={"points": points})
            res.raise_for_status()
            logger.info(f"Successfully ingested {len(points)} chunks from {file_path}")
            
    except Exception as e:
        logger.error(f"Error ingesting {file_path}: {e}")

def main():
    # 1. Reset collection
    logger.info("Resetting collection...")
    requests.delete(f"{QDRANT_URL}/collections/{COLLECTION_NAME}")
    res = requests.put(f"{QDRANT_URL}/collections/{COLLECTION_NAME}", json={
        "vectors": {"size": 1024, "distance": "Cosine"} # Unnamed vector
    })
    res.raise_for_status()
    logger.info("Collection reset and created successfully.")
    
    # 2. Walk through Database directory
    db_path = "Database"
    for root, dirs, files in os.walk(db_path):
        for file in files:
            file_path = os.path.join(root, file)
            ingest_file(file_path)

if __name__ == "__main__":
    main()
