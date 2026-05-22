import requests
import sys

QDRANT_URL = "http://localhost:6333"
COLLECTION_NAME = "km_knowledge"
VECTOR_SIZE = 1024
DISTANCE_METRIC = "Cosine"

def check_collection_exists():
    try:
        response = requests.get(f"{QDRANT_URL}/collections/{COLLECTION_NAME}")
        if response.status_code == 200:
            return True
        elif response.status_code == 404:
            return False
        else:
            print(f"Unexpected error checking collection: {response.status_code} - {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to Qdrant: {e}")
        return None

def create_collection():
    payload = {
        "vectors": {
            "size": VECTOR_SIZE,
            "distance": DISTANCE_METRIC
        }
    }
    try:
        response = requests.put(f"{QDRANT_URL}/collections/{COLLECTION_NAME}", json=payload)
        if response.status_code == 200:
            print(f"Collection '{COLLECTION_NAME}' created successfully.")
            return True
        else:
            print(f"Failed to create collection: {response.status_code} - {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to Qdrant: {e}")
        return False

def main():
    print(f"Checking if collection '{COLLECTION_NAME}' exists...")
    exists = check_collection_exists()

    if exists is True:
        print(f"Collection '{COLLECTION_NAME}' already exists. Exiting gracefully.")
        sys.exit(0)
    elif exists is False:
        print(f"Collection '{COLLECTION_NAME}' does not exist. Creating it...")
        if create_collection():
            print("Setup complete.")
            sys.exit(0)
        else:
            print("Setup failed.")
            sys.exit(1)
    else:
        print("Could not determine if collection exists due to connection error.")
        sys.exit(1)

if __name__ == "__main__":
    main()
