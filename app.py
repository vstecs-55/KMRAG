import os
import requests
import sqlite3
import uuid
import logging
import subprocess
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional

# Configuration
QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
COLLECTION_NAME = "km_knowledge"
DB_PATH = "chat_history.db"
LINE_TOKEN = "hg2DPV5v0z7cyJyuJsBkEBk/j+wNoUnrSLPOTRHL4TzWrqChXDZ1u6VRkzUtRCmEpEnR47gSrNoTurwwWwKit/fffi6PPnNY8WF6HVK1vLFkb9jPu6B+Wv7oHnAwJw48XhwXJy0ymBAzSRhAGwbxPgdB04t89/1O/w1cDnyilFU="
MODEL_GEN = "llama3.2-vision:11b"
MODEL_EMBED = "mxbai-embed-large"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KM-RAG-API")

app = FastAPI()

# --- Helper Functions ---

def get_history(user_id: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT role, content FROM history WHERE user_id = ? ORDER BY timestamp DESC LIMIT 5", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

def save_history(user_id: str, role: str, content: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO history (user_id, role, content) VALUES (?, ?, ?)", (user_id, role, content))
    conn.commit()
    conn.close()

def get_embedding(text: str):
    res = requests.post(f"{OLLAMA_URL}/api/embeddings", json={"model": MODEL_EMBED, "prompt": text})
    res.raise_for_status()
    return res.json()["embedding"]

def hybrid_search(query_text: str):
    search_query = query_text
    if "H200" in query_text.upper():
        search_query += " NVIDIA H200 GPU SXM5 HGX PCIe"
        
    vector = get_embedding(search_query)
    
    # Dynamic Brand Filter
    conditions = []
    if "GIGABYTE" in query_text.upper():
        conditions.append({"key": "filename", "match": {"text": "GIGABYTE"}})
    elif "SUPERMICRO" in query_text.upper():
        # Supermicro files often start with sys- or as-
        search_filter = {
            "should": [
                {"key": "filename", "match": {"text": "Supermicro"}},
                {"key": "filename", "match": {"text": "sys-"}},
                {"key": "filename", "match": {"text": "as-"}}
            ]
        }
    
    if not conditions and "search_filter" not in locals():
        search_filter = None
    elif conditions:
        search_filter = {"must": conditions}

    payload = {
        "vector": vector,
        "limit": 50,
        "with_payload": True
    }
    if search_filter:
        payload["filter"] = search_filter

    res = requests.post(f"{QDRANT_URL}/collections/{COLLECTION_NAME}/points/query", json=payload)
    res.raise_for_status()
    result = res.json().get("result", {})
    points = result.get("points", []) if isinstance(result, dict) else []
    
    # Re-ranking logic
    def score_chunk(p):
        text = p.get("payload", {}).get("text", "").upper()
        fname = p.get("payload", {}).get("filename", "").upper()
        score = 0
        if "H200" in text: score += 1000
        if "NVIDIA" in text: score += 200
        
        # Priority models
        for model in ["G494", "G294", "G593", "AS-2115", "SYS-221"]:
            if model in fname or model in text: score += 500
            
        return score

    points.sort(key=score_chunk, reverse=True)
    return points[:6]

def call_llm(system_prompt: str, user_content: str):
    payload = {
        "model": MODEL_GEN,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        "stream": False,
        "options": {"num_ctx": 4096, "temperature": 0.1}
    }
    
    try:
        res = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=300)
        res.raise_for_status()
        return res.json()["message"]["content"]
    except Exception as e:
        logger.error(f"LLM Call failed: {e}")
        raise e

def process_query(user_id: str, query_text: str):
    logger.info(f"Processing: {query_text}")
    
    context_docs = hybrid_search(query_text)
    context_text = "\n".join([f"File: {d.get('payload',{}).get('filename')}\nContent: {d.get('payload',{}).get('text')}" for d in context_docs])
    
    system_prompt = """คุณคือผู้เชี่ยวชาญด้าน Technical Support สำหรับ Server
    ภารกิจ: ค้นหาข้อมูลรุ่น Server (จากชื่อไฟล์หรือเนื้อหา) ที่รองรับ NVIDIA H200 GPU
    
    กฎการตอบ:
    1. ตรวจสอบ Context ให้ละเอียด (รวมถึงบรรทัด 'File: ...' และ 'Source File: ...')
    2. ลิสต์รุ่นที่รองรับ NVIDIA H200 มาให้ครบถ้วน
    3. ถ้าหาไม่เจอจริงๆ ให้บอกว่าไม่พบข้อมูล
    4. ตอบเป็นภาษาไทยที่สุภาพและเป็นมืออาชีพ"""
    
    user_content = f"บริบทข้อมูลประกอบด้วยหลายไฟล์ดังนี้:\n{context_text}\n\nคำถาม: {query_text}"
    
    final_answer = call_llm(system_prompt, user_content)
    
    save_history(user_id, "user", query_text)
    save_history(user_id, "assistant", final_answer)
    return final_answer# --- API Endpoints ---

@app.get("/")
async def read_root():
    return FileResponse("dashboard.html")

@app.post("/webhook")
@app.post("/line/webhook")
async def line_webhook(request: Request):
    body = await request.json()
    if not body.get("events"):
        return {"status": "no events"}
    
    event = body["events"][0]
    if not event or event.get("type") != "message" or event.get("message", {}).get("type") != "text":
        return {"status": "ignored"}
    
    user_id = event["source"]["userId"]
    text = event["message"]["text"]
    
    try:
        answer = process_query(user_id, text)
        res = requests.post("https://api.line.me/v2/bot/message/push",
                      headers={"Authorization": f"Bearer {LINE_TOKEN}"},
                      json={"to": user_id, "messages": [{"type": "text", "text": answer}]})
        logger.info(f"LINE API Response: {res.status_code} - {res.text}")
        res.raise_for_status()
    except Exception as e:
        logger.error(f"Error processing query or sending to LINE: {e}")
        try:
            res_err = requests.post("https://api.line.me/v2/bot/message/push",
                          headers={"Authorization": f"Bearer {LINE_TOKEN}"},
                          json={"to": user_id, "messages": [{"type": "text", "text": "ขออภัยครับ ระบบขัดข้องชั่วคราว"}]})
            logger.info(f"LINE API Error Response: {res_err.status_code} - {res_err.text}")
        except: pass
        
    return {"status": "ok"}

@app.get("/health")
async def health():
    # Check dependencies
    services = {}
    try:
        requests.get(f"{OLLAMA_URL}/api/tags", timeout=2)
        services["ollama"] = "online"
    except: services["ollama"] = "offline"
    
    try:
        requests.get(f"{QDRANT_URL}/healthz", timeout=2)
        services["qdrant"] = "online"
    except: services["qdrant"] = "offline"
    
    return {"status": "healthy" if all(v == "online" for v in services.values()) else "degraded", "services": services}

@app.post("/system/restart")
async def restart_system():
    # Use sudo to restart docker containers
    subprocess.run(["sudo", "-S", "docker", "restart", "qdrant"], input="SunnyHills888\n", text=True)
    # n8n is usually a process, might need to be restarted via systemctl or pkill/start
    # For now, just restart Qdrant as a demo of the functionality
    return {"status": "restart_triggered", "detail": "Qdrant restarted"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
