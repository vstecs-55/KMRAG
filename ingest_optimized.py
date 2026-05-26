import os
import requests
import json
import uuid
import logging
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from tqdm import tqdm
from scripts.parsers import parse_pdf, parse_excel, parse_text, parse_word, ParserError

# Configuration
QDRANT_URL = "http://localhost:6333"
OLLAMA_URL = "http://localhost:11434"
COLLECTION_NAME = "km_knowledge"
MODEL_EMBED = "mxbai-embed-large"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("IngestorFast")

def get_embedding(text):
    """Gets embedding from Ollama with retry logic."""
    for attempt in range(5):
        try:
            res = requests.post(
                f"{OLLAMA_URL}/api/embeddings", 
                json={"model": MODEL_EMBED, "prompt": text}, 
                timeout=120
            )
            res.raise_for_status()
            return res.json()["embedding"]
        except Exception as e:
            if attempt == 4:
                logger.error(f"Failed to get embedding after 5 attempts: {e}")
                return None
            time.sleep(2 ** attempt) # Exponential backoff
    return None

def process_single_file(file_path):
    """Parses a file and returns its chunks. (To be run in ProcessPool)"""
    ext = os.path.splitext(file_path)[1].lower()
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
            return None
            
        # The parsers already return chunks joined by "---CHUNK---"
        raw_chunks = content.split("\n\n---CHUNK---\n\n")
        
        # Further clean and filter empty chunks
        chunks = [c.strip() for c in raw_chunks if c.strip()]
        return {"file_path": file_path, "chunks": chunks}
    except Exception as e:
        # logger.error(f"Error parsing {file_path}: {e}")
        return {"file_path": file_path, "error": str(e)}

def run_ingestion(progress_callback=None):
    db_path = "Database"
    
    files_to_ingest = []
    for root, dirs, files in os.walk(db_path):
        # Skip hidden directories
        if any(d.startswith('.') for d in root.split(os.sep)):
            continue
        for file in files:
            # Skip hidden files
            if file.startswith('.'):
                continue
            files_to_ingest.append(os.path.join(root, file))
                
    logger.info(f"Found {len(files_to_ingest)} files for ingestion.")
    if progress_callback: progress_callback({"stage": "ingest_start", "total_files": len(files_to_ingest)})

    # 1. Reset Collection
    logger.info("Resetting collection...")
    requests.delete(f"{QDRANT_URL}/collections/{COLLECTION_NAME}")
    res = requests.put(f"{QDRANT_URL}/collections/{COLLECTION_NAME}", json={
        "vectors": {"size": 1024, "distance": "Cosine"}
    })
    res.raise_for_status()

    # 2. Parallel Parsing
    logger.info("Starting parallel parsing...")
    all_file_data = []
    with ProcessPoolExecutor(max_workers=os.cpu_count() or 4) as executor:
        futures = {executor.submit(process_single_file, fp): fp for fp in files_to_ingest}
        parsed_count = 0
        for future in tqdm(as_completed(futures), total=len(futures), desc="Parsing Files"):
            result = future.result()
            if result and "chunks" in result:
                all_file_data.append(result)
            parsed_count += 1
            if progress_callback and parsed_count % 50 == 0:
                progress_callback({"stage": "ingest_parsing", "current": parsed_count, "total": len(files_to_ingest)})

    # 3. Parallel Embedding & Ingestion
    logger.info("Starting parallel embedding and ingestion...")
    
    points_batch = []
    batch_size = 100
    
    def handle_chunk(file_path, chunk, index):
        filename = os.path.basename(file_path)
        text_to_embed = f"Source File: {filename}\nTechnical Data:\n{chunk}"
        vector = get_embedding(text_to_embed)
        if vector:
            return {
                "id": str(uuid.uuid4()),
                "vector": vector,
                "payload": {
                    "text": text_to_embed,
                    "filename": filename,
                    "path": file_path,
                    "chunk_index": index
                }
            }
        return None

    # We use a ThreadPool for Ollama calls as they are I/O bound (waiting for GPU/Ollama)
    with ThreadPoolExecutor(max_workers=1) as executor:
        chunk_futures = []
        for file_data in all_file_data:
            for i, chunk in enumerate(file_data["chunks"]):
                chunk_futures.append(executor.submit(handle_chunk, file_data["file_path"], chunk, i))
        
        total_chunks = len(chunk_futures)
        ingested_chunks = 0
        for future in tqdm(as_completed(chunk_futures), total=len(chunk_futures), desc="Ingesting Chunks"):
            point = future.result()
            if point:
                points_batch.append(point)
            
            # Small delay for Ollama stability
            time.sleep(0.05)
            
            ingested_chunks += 1
            if len(points_batch) >= batch_size:
                requests.put(f"{QDRANT_URL}/collections/{COLLECTION_NAME}/points?wait=true", json={"points": points_batch})
                points_batch = []
                if progress_callback:
                    progress_callback({"stage": "ingest_embedding", "current": ingested_chunks, "total": total_chunks})

    # Final batch
    if points_batch:
        requests.put(f"{QDRANT_URL}/collections/{COLLECTION_NAME}/points?wait=true", json={"points": points_batch})

    logger.info("Ingestion complete!")
    if progress_callback: progress_callback({"stage": "ingest_complete", "total_chunks": ingested_chunks})

if __name__ == "__main__":
    run_ingestion()
