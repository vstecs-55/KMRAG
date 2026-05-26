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
CHECKPOINT_FILE = "ingest_checkpoint.json"
LOG_FILE = "ingest_slow.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("IngestorSlow")

def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, 'r') as f:
                return json.load(f)
        except: pass
    return {"ingested_files": []}

def save_checkpoint(ingested_files):
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump({"ingested_files": list(set(ingested_files))}, f)

def clean_text(text):
    if not text: return ""
    return "".join(c for c in text if c.isprintable() or c in "\n\t ")

def get_embedding(text):
    text = clean_text(text)
    if not text.strip(): return None
    for attempt in range(10):
        try:
            res = requests.post(f"{OLLAMA_URL}/api/embeddings", json={"model": MODEL_EMBED, "prompt": text}, timeout=180)
            res.raise_for_status()
            time.sleep(1) # Small cooldown
            return res.json()["embedding"]
        except Exception as e:
            logger.warning(f"Embedding attempt {attempt+1} failed: {e}")
            time.sleep(10 + (attempt * 5))
    return None

def ingest_file(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in ['.pdf', '.xlsx', '.xls', '.docx', '.txt', '.md']:
        return True
        
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
            return True
            
        if not content:
            return True

        raw_chunks = content.split("\n\n---CHUNK---\n\n")
        chunks = [c.strip() for c in raw_chunks if c.strip()]
                
        points = []
        filename = os.path.basename(file_path)
        for i, chunk in enumerate(chunks):
            text_to_embed = f"Source File: {filename}\nTechnical Data:\n{chunk}"
            vector = get_embedding(text_to_embed)
            
            # CRITICAL: If ANY chunk fails, return False to retry the whole file later
            if not vector: 
                logger.error(f"CHUNK FAILURE in {file_path} at index {i}. Aborting file.")
                return False
            
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
            
            if len(points) >= 5:
                requests.put(f"{QDRANT_URL}/collections/{COLLECTION_NAME}/points?wait=true", json={"points": points})
                points = []
                time.sleep(0.5)
            
        if points:
            requests.put(f"{QDRANT_URL}/collections/{COLLECTION_NAME}/points?wait=true", json={"points": points})
        
        return True
    except Exception as e:
        logger.error(f"Error ingesting {file_path}: {e}")
        return False

def main():
    checkpoint = load_checkpoint()
    ingested_files = checkpoint["ingested_files"]
    
    db_path = "Database"
    all_files = []
    for root, dirs, files in os.walk(db_path):
        if any(d.startswith('.') for d in root.split(os.sep)):
            continue
        for file in files:
            if file.startswith('.'): continue
            all_files.append(os.path.join(root, file))
            
    files_to_ingest = [f for f in all_files if f not in ingested_files]
    logger.info(f"Starting Slow Ingestion. {len(files_to_ingest)} files remaining.")
    
    for path in files_to_ingest:
        if ingest_file(path):
            ingested_files.append(path)
            save_checkpoint(ingested_files)
        else:
            # If file failed, don't add to checkpoint, so it will be retried next time
            logger.warning(f"File {path} failed ingestion and will be retried.")
            
        time.sleep(2)

if __name__ == "__main__":
    main()
