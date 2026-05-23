import logging
import json
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any
import requests
from fastembed import SparseTextEmbedding
from qdrant_client import QdrantClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434/api"
QDRANT_URL = "http://localhost:6333"
COLLECTION_NAME = "km_knowledge"
EMBEDDING_MODEL = "mxbai-embed-large"
RERANK_MODEL = "llama3.3:70b"

# Initialize encoders
sparse_encoder = SparseTextEmbedding("prithivida/Splade_PP_en_v1")

def get_embedding(text: str) -> List[float]:
    response = requests.post(f"{OLLAMA_URL}/embeddings", json={
        "model": EMBEDDING_MODEL,
        "prompt": text
    })
    response.raise_for_status()
    return response.json()["embedding"]

def get_sparse_vector(text: str) -> Dict[str, List]:
    sparse_vec = list(sparse_encoder.embed([text]))[0]
    return {
        "indices": sparse_vec.indices.tolist(),
        "values": sparse_vec.values.tolist()
    }

def _dense_search(vector: List[float], limit: int) -> List[Dict[str, Any]]:
    payload = {
        "vector": { "name": "dense", "vector": vector },
        "limit": limit,
        "with_payload": True
    }
    response = requests.post(f"{QDRANT_URL}/collections/{COLLECTION_NAME}/points/search", json=payload)
    response.raise_for_status()
    return response.json().get("result", [])

def _sparse_search(sparse_vector: Dict[str, List], limit: int) -> List[Dict[str, Any]]:
    payload = {
        "vector": {
            "name": "sparse",
            "vector": {
                "indices": sparse_vector["indices"],
                "values": sparse_vector["values"]
            }
        },
        "limit": limit,
        "with_payload": True
    }
    response = requests.post(f"{QDRANT_URL}/collections/{COLLECTION_NAME}/points/search", json=payload)
    response.raise_for_status()
    return response.json().get("result", [])

def hybrid_search(query_text: str, limit: int = 10) -> List[Dict[str, Any]]:
    vector = get_embedding(query_text)
    sparse_vector = get_sparse_vector(query_text)

    with ThreadPoolExecutor() as executor:
        future_dense = executor.submit(_dense_search, vector, limit)
        future_sparse = executor.submit(_sparse_search, sparse_vector, limit)

        dense_results = future_dense.result()
        sparse_results = future_sparse.result()

    # Reciprocal Rank Fusion (RRF)
    k = 60
    scores = {}

    for rank, doc in enumerate(dense_results):
        doc_id = doc['id']
        scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank + 1)

    for rank, doc in enumerate(sparse_results):
        doc_id = doc['id']
        scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank + 1)

    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

    all_docs = {doc['id']: doc for doc in dense_results + sparse_results}
    return [all_docs[doc_id] for doc_id in sorted_ids[:limit]]

def rerank(query_text: str, documents: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
    if not documents:
        return []

    docs_text = ""
    for i, doc in enumerate(documents):
        content = doc.get("payload", {}).get("content", "No content")
        docs_text += f"ID: {doc['id']}\nContent: {content}\n---\n"

    prompt = f"""You are a precision reranker. I will provide you with retrieved documents and a user query.
Your task is to select the Top {top_k} most relevant documents and order them by relevance.
Return ONLY a JSON list of the document IDs in the new order.

Query: {query_text}

Documents:
{docs_text}

Response Format: ["id1", "id2", ...]"""

    response = requests.post(f"{OLLAMA_URL}/chat", json={
        "model": RERANK_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "format": "json"
    })
    response.raise_for_status()

    try:
        result_ids = json.loads(response.json()["message"]["content"])
        doc_map = {doc['id']: doc for doc in documents}
        return [doc_map[doc_id] for doc_id in result_ids if doc_id in doc_map]
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Reranking failed to produce valid JSON: {e}")
        return documents[:top_k]

def verify_query(query: str, description: str) -> None:
    logger.info(f"Testing {description}: '{query}'")

    try:
        logger.info("Performing hybrid search...")
        retrieved = hybrid_search(query)
        logger.info(f"Retrieved {len(retrieved)} documents.")
        for i, doc in enumerate(retrieved):
            logger.info(f" {i+1}. ID: {doc['id']} - {doc['payload'].get('content', '')[:100]}...")

        logger.info("Reranking results...")
        reranked = rerank(query, retrieved)
        logger.info(f"Top {len(reranked)} after reranking:")
        for i, doc in enumerate(reranked):
            logger.info(f" {i+1}. ID: {doc['id']} - {doc['payload'].get('content', '')[:100]}...")
    except Exception as e:
        logger.exception(f"Error verifying {description}: {e}")

if __name__ == "__main__":
    test_queries = [
        ("What is the power efficiency?", "Semantic Query"),
        ("EPYC 9004", "Keyword Query")
    ]

    for query, desc in test_queries:
        verify_query(query, desc)
