import requests
import sys
import os
import logging
from typing import Optional

# Configuration
QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = os.environ.get("QDRANT_COLLECTION_NAME", "km_knowledge")
VECTOR_SIZE = int(os.environ.get("QDRANT_VECTOR_SIZE", "1024"))
DISTANCE_METRIC = os.environ.get("QDRANT_DISTANCE_METRIC", "Cosine")

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def check_collection_exists() -> Optional[bool]:
    try:
        response = requests.get(f"{QDRANT_URL}/collections/{COLLECTION_NAME}", timeout=5)
        if response.status_code == 200:
            return True
        elif response.status_code == 404:
            return False
        else:
            logger.error(f"Unexpected error checking collection: {response.status_code} - {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error connecting to Qdrant: {e}")
        return None

def create_collection() -> bool:
    payload = {
        "vectors": {
            "size": VECTOR_SIZE,
            "distance": DISTANCE_METRIC
        }
    }
    try:
        response = requests.put(f"{QDRANT_URL}/collections/{COLLECTION_NAME}", json=payload, timeout=5)
        if response.status_code == 200:
            logger.info(f"Collection '{COLLECTION_NAME}' created successfully.")
            return True
        else:
            logger.error(f"Failed to create collection: {response.status_code} - {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Error connecting to Qdrant: {e}")
        return False

def main() -> None:
    logger.info(f"Checking if collection '{COLLECTION_NAME}' exists...")
    exists = check_collection_exists()

    if exists is True:
        logger.info(f"Collection '{COLLECTION_NAME}' already exists. Exiting gracefully.")
        sys.exit(0)
    elif exists is False:
        logger.info(f"Collection '{COLLECTION_NAME}' does not exist. Creating it...")
        if create_collection():
            logger.info("Setup complete.")
            sys.exit(0)
        else:
            logger.error("Setup failed.")
            sys.exit(1)
    else:
        logger.error("Could not determine if collection exists due to connection error.")
        sys.exit(1)

if __name__ == "__main__":
    main()
