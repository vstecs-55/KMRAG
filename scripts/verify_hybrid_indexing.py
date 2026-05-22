import requests
import os
import sys
import datetime
import json
import logging
from typing import List, Dict, Any, Optional, Union

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Configuration from environment variables
QDRANT_URL: str = os.environ.get("QDRANT_URL", "http://localhost:6333")
OLLAMA_URL: str = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/embeddings")
COLLECTION_NAME: str = os.environ.get("QDRANT_COLLECTION_NAME", "km_knowledge")
MODEL_NAME: str = os.environ.get("MODEL_NAME", "mxbai-embed-large")

def get_dense_embedding(text: str) -> Optional[List[float]]:
    """
    Retrieves dense embedding from Ollama.
    """
    logger.info(f"Getting dense embedding for: {text[:50]}...")
    payload = {"model": MODEL_NAME, "prompt": text}
    try:
        res = requests.post(OLLAMA_URL, json=payload, timeout=10)
        if res.status_code == 200:
            return res.json().get("embedding")
        else:
            logger.error(f"Error getting embedding: {res.text}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error while getting dense embedding: {e}")
        return None

def get_sparse_embedding(text: str) -> Dict[str, List[Union[int, float]]]:
    """
    MOCK IMPLEMENTATION: Generates a mock sparse embedding for connectivity verification.
    This does not represent actual BM25/SPLADE embeddings.
    """
    logger.info(f"Generating mock sparse embedding for: {text[:50]}...")
    words = text.lower().split()
    sparse_vec = {}
    for i, word in enumerate(words):
        idx = abs(hash(word)) % 100000
        sparse_vec[idx] = 1.0
    return {"indices": list(sparse_vec.keys()), "values": list(sparse_vec.values())}

def push_to_qdrant(point_id: int, dense_vec: List[float], sparse_vec: Dict[str, List[Union[int, float]]], payload: Dict[str, Any]) -> bool:
    """
    Pushes a point with hybrid vectors to Qdrant.
    """
    logger.info(f"Pushing point {point_id} to Qdrant...")
    data = {
        "points": [
            {
                "id": point_id,
                "vector": {
                    "dense": dense_vec,
                    "sparse": sparse_vec
                },
                "payload": payload
            }
        ]
    }
    try:
        res = requests.put(f"{QDRANT_URL}/collections/{COLLECTION_NAME}/points", json=data, timeout=10)
        if res.status_code == 200:
            logger.info("Point pushed successfully.")
            return True
        else:
            logger.error(f"Error pushing point: {res.text}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error while pushing point: {e}")
        return False

def verify_retrieval_dense(query_text: str) -> bool:
    """
    Verifies retrieval using dense vectors.
    """
    logger.info(f"Verifying retrieval (Dense) for: {query_text}")
    dense_vec = get_dense_embedding(query_text)
    if dense_vec is None:
        return False

    search_payload = {
        "vector": {
            "name": "dense",
            "vector": dense_vec
        },
        "limit": 1,
        "with_payload": True
    }
    try:
        res = requests.post(f"{QDRANT_URL}/collections/{COLLECTION_NAME}/points/search", json=search_payload, timeout=10)
        if res.status_code == 200:
            resp = res.json()
            results = resp.get("result", [])
            logger.info(f"Results: {json.dumps(results, indent=2)}")
            if len(results) > 0:
                p = results[0]
                logger.info(f"Match found: {p['payload']['text']} (Score: {p['score']})")
                return True
            return False
        else:
            logger.error(f"Error searching: {res.text}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error while searching (dense): {e}")
        return False

def verify_retrieval_sparse(query_text: str) -> bool:
    """
    Verifies retrieval using sparse vectors.
    """
    logger.info(f"Verifying retrieval (Sparse) for: {query_text}")
    sparse_vec = get_sparse_embedding(query_text)

    search_payload = {
        "vector": {
            "name": "sparse",
            "vector": sparse_vec
        },
        "limit": 1,
        "with_payload": True
    }
    try:
        res = requests.post(f"{QDRANT_URL}/collections/{COLLECTION_NAME}/points/search", json=search_payload, timeout=10)
        if res.status_code == 200:
            resp = res.json()
            results = resp.get("result", [])
            logger.info(f"Results: {json.dumps(results, indent=2)}")
            if len(results) > 0:
                p = results[0]
                logger.info(f"Match found: {p['payload']['text']} (Score: {p['score']})")
                return True
            return False
        else:
            logger.error(f"Error searching: {res.text}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error while searching (sparse): {e}")
        return False

if __name__ == "__main__":
    test_text = "The AMD EPYC 9004 Series (Genoa) provides high performance for data centers."
    payload = {
        "text": test_text,
        "filename": "amd_specs.pdf",
        "page_number": 1,
        "source_type": "pdf",
        "timestamp": datetime.datetime.now().isoformat()
    }

    dense = get_dense_embedding(test_text)
    sparse = get_sparse_embedding(test_text)

    if dense and sparse:
        if push_to_qdrant(1, dense, sparse, payload):
            dense_ok = verify_retrieval_dense("Where is the EPYC 9004?")
            sparse_ok = verify_retrieval_sparse("Where is the EPYC 9004?")
            if dense_ok and sparse_ok:
                logger.info("SUCCESS: Hybrid indexing (Dense + Sparse) verified.")
                sys.exit(0)

    logger.error("FAILURE: Hybrid indexing verification failed.")
    sys.exit(1)
