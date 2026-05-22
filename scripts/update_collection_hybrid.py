import requests
import os
import sys
import logging
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Configuration from environment variables
QDRANT_URL: str = os.environ.get("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME: str = os.environ.get("QDRANT_COLLECTION_NAME", "km_knowledge")

def delete_collection() -> bool:
    """
    Deletes the specified Qdrant collection.
    """
    logger.info(f"Deleting collection {COLLECTION_NAME}...")
    try:
        res = requests.delete(f"{QDRANT_URL}/collections/{COLLECTION_NAME}", timeout=10)
        return res.status_code == 200
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error while deleting collection: {e}")
        return False

def create_hybrid_collection() -> bool:
    """
    Creates a hybrid collection in Qdrant with both dense and sparse vectors.
    """
    logger.info(f"Creating hybrid collection {COLLECTION_NAME}...")
    payload = {
        "vectors": {
            "dense": {
                "size": 1024,
                "distance": "Cosine"
            }
        },
        "sparse_vectors": {
            "sparse": {}
        }
    }
    try:
        res = requests.put(f"{QDRANT_URL}/collections/{COLLECTION_NAME}", json=payload, timeout=10)
        if res.status_code == 200:
            logger.info("Hybrid collection created successfully.")
            return True
        else:
            logger.error(f"Failed to create collection: {res.text}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error while creating collection: {e}")
        return False

if __name__ == "__main__":
    delete_collection()
    if create_hybrid_collection():
        sys.exit(0)
    else:
        sys.exit(1)
