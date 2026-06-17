import os
import requests
import json
import uuid
import logging
import time
from dotenv import load_dotenv
from scripts.parsers import parse_pdf, parse_excel, parse_text, parse_word, parse_pptx, ParserError

load_dotenv()

# Configuration
QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
COLLECTION_NAME = os.environ.get("COLLECTION_NAME", "km_knowledge")
MODEL_EMBED = os.environ.get("MODEL_EMBED", "mxbai-embed-large")
CHECKPOINT_FILE = "ingest_checkpoint.json"
LOG_FILE = "ingest.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("Ingestor")

def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, 'r') as f:
                return json.load(f)
        except: pass
    return {"ingested_files": []}

def save_checkpoint(ingested_files):
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump({"ingested_files": ingested_files}, f)

def clean_text(text):
    if not text: return ""
    return "".join(c for c in text if c.isprintable() or c in "\n\t ")

def get_embedding(text):
    text = clean_text(text)
    if not text.strip(): return None
    # Very conservative retry logic
    for attempt in range(10):
        try:
            res = requests.post(f"{OLLAMA_URL}/api/embeddings", json={"model": MODEL_EMBED, "prompt": text}, timeout=180)
            res.raise_for_status()
            # Success, wait a bit before returning to let Ollama recover
            time.sleep(3) 
            return res.json()["embedding"]
        except Exception as e:
            logger.warning(f"Embedding attempt {attempt+1} failed: {e}")
            time.sleep(10 + (attempt * 5)) # Increasing delay
    logger.error("Skipping chunk after 10 failed embedding attempts.")
    return None

def ingest_file(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in ['.pdf', '.xlsx', '.xls', '.docx', '.pptx', '.txt', '.md']:
        return True
        
    logger.info(f"Ingesting: {file_path}")
    
    try:
        if ext == '.pdf':
            content = parse_pdf(file_path)
        elif ext in ['.xlsx', '.xls']:
            content = parse_excel(file_path)
        elif ext == '.docx':
            content = parse_word(file_path)
        elif ext == '.pptx':
            content = parse_pptx(file_path)
        elif ext in ['.txt', '.md']:
            content = parse_text(file_path)
        else:
            return True
            
        if not content:
            logger.warning(f"No content extracted from {file_path}")
            return True

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
            
            if len(points) >= 10: # Smaller batch
                res = requests.put(f"{QDRANT_URL}/collections/{COLLECTION_NAME}/points?wait=true", json={"points": points})
                res.raise_for_status()
                points = []
                logger.info(f"Ingested batch of 10 for {filename}")
            
        if points:
            res = requests.put(f"{QDRANT_URL}/collections/{COLLECTION_NAME}/points?wait=true", json={"points": points})
            res.raise_for_status()
        
        return True
    except Exception as e:
        logger.error(f"Error ingesting {file_path}: {e}")
        return False

def main():
    checkpoint = load_checkpoint()
    ingested_files = checkpoint["ingested_files"]
    
    try:
        res = requests.get(f"{QDRANT_URL}/collections/{COLLECTION_NAME}")
        if res.status_code != 200:
            logger.info("Creating collection...")
            res = requests.put(f"{QDRANT_URL}/collections/{COLLECTION_NAME}", json={
                "vectors": {"size": 1024, "distance": "Cosine"}
            })
            res.raise_for_status()
            ingested_files = []
    except:
        logger.info("Creating collection...")
        requests.put(f"{QDRANT_URL}/collections/{COLLECTION_NAME}", json={
            "vectors": {"size": 1024, "distance": "Cosine"}
        })
        ingested_files = []

    db_path = "Database"
    files_to_ingest = []
    for root, dirs, files in os.walk(db_path):
        if any(d.startswith('.') for d in root.split(os.sep)):
            continue
        for file in files:
            if file.startswith('.'): continue
            path = os.path.join(root, file)
            if path not in ingested_files:
                files_to_ingest.append(path)
                
    logger.info(f"Resuming ingestion. {len(files_to_ingest)} files remaining.")
    
    count = 0
    for path in files_to_ingest:
        success = ingest_file(path)
        if success:
            ingested_files.append(path)
            save_checkpoint(ingested_files)
            count += 1
            if count % 5 == 0:
                logger.info(f"Progress: {count}/{len(files_to_ingest)} files in this run.")
        
        time.sleep(5) # Cooldown between files

    logger.info("Ingestion session complete.")

if __name__ == "__main__":
    main()
