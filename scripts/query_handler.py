import os
import requests
import sqlite3
import uuid
import logging

# Configuration
QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
COLLECTION_NAME = "km_//_knowledge" # Adjusted based on actual collection
DB_PATH = "chat_history.db"
MODEL_GEN = "llama3.3:70b"
MODEL_EMBED = "mxbai-embed-large"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("QueryHandler")

def get_history(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT role, content FROM history WHERE user_id = ? ORDER BY timestamp DESC LIMIT 5", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

def save_history(user_id, role, content):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO history (user_id, role, content) VALUES (?, ?, ?)", (user_id, role, content))
    conn.commit()
    conn.close()

def call_llm(system_prompt, messages, format_json=False):
    payload = {
        "model": MODEL_GEN,
        "messages": [{"role": "system", "content": system_prompt}] + messages,
        "stream": False
    }
    if format_json:
        payload["format"] = "json"
    
    res = requests.post(f"{OLLAMA_URL}/api/chat", json=payload)
    res.raise_for_status()
    return res.json()["message"]["content"]

def get_embedding(text):
    res = requests.post(f"{OLLAMA_URL}/api/embeddings", json={"model": MODEL_EMBED, "prompt": text})
    res.raise_for_status()
    return res.json()["embedding"]

def hybrid_search(query_text):
    # Simplified for logic verification
    vector = get_embedding(query_text)
    res = requests.put(f"{QDRANT_URL}/collections/km_knowledge/points/search", json={
        "vector": {"dense": vector},
        "limit": 10,
        "with_payload": True
    })
    res.raise_for_status()
    return res.json()["result"]

def process_query(user_id, query_text):
    # 1. History
    history = get_history(user_id)
    
    # 2. Intent Routing
    router_prompt = "คุณคือผู้เชี่ยวชาญในการวิเคราะห์เจตนา... (Full prompt from spec)"
    messages = history + [{"role": "user", "content": query_text}]
    intent_res = call_llm(router_prompt, messages, format_json=True)
    # (Assume intent_res is parsed to intent_type)
    
    # 3. Hybrid Retrieval
    context_docs = hybrid_search(query_text)
    
    # 4. Generation
    gen_prompt = "คุณคือที่ปรึกษาผู้เชี่ยวชาญ... (Full prompt from spec)"
    context_text = "\n".join([d["payload"]["text"] for d in context_docs])
    gen_messages = [{"role": "user", "content": f"Context: {context_text}\n\nQuery: {query_text}"}]
    draft = call_llm(gen_prompt, gen_messages)
    
    # 5. Refinement
    refine_prompt = "คุณคือผู้ตรวจสอบคุณภาพคำตอบ... (Full prompt from spec)"
    refine_messages = [{"role": "user", "content": f"Context: {context_text}\n\nDraft: {draft}"}]
    final_answer = call_llm(refine_prompt, refine_messages)
    
    # 6. Save & Return
    save_history(user_id, "user", query_text)
    save_history(user_id, "assistant", final_answer)
    
    return final_answer

if __name__ == "__main__":
    # Test run
    try:
        print(process_query("test_user", "ราคา EPYC 9004 เท่าไหร่?"))
    except Exception as e:
        print(f"Error: {e}")
