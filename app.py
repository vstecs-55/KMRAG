import os
import requests
import sqlite3
import uuid
import logging
import subprocess
import asyncio
import json
from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any

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

# --- WebSocket Manager ---

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"New WebSocket connection. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        if not self.active_connections:
            return
        logger.info(f"Broadcasting stage: {message.get('stage')}")
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Broadcast error: {e}")

manager = ConnectionManager()

# --- Helper Functions ---

def get_history(user_id: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT role, content FROM history WHERE user_id = ? ORDER BY timestamp DESC LIMIT 3", (user_id,))
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

async def hybrid_search(query_text: str):
    search_query = query_text
    query_upper = query_text.upper()
    
    if "H200" in query_upper:
        search_query += " NVIDIA H200 HGX SXM5 8-GPU System"
    if any(x in query_upper for x in ["HDD", "SSD", "STORAGE", "BAYS", "ฮาร์ดดิสก์"]):
        search_query += " Storage Specification Drive Bays Capacity"
        
    await manager.broadcast({"stage": "retrieval_start", "query": search_query})
    vector = get_embedding(search_query)
    
    # Advanced Brand Filter
    conditions = []
    search_filter = None
    
    if any(x in query_upper for x in ["GIGABYTE", "GIGABYUT", "GIGA", "จิกะไบต์"]):
        conditions.append({"key": "filename", "match": {"text": "GIGABYTE"}})
    elif any(x in query_upper for x in ["SUPERMICRO", "SUPER", "ซุปเปอร์ไมโคร"]):
        search_filter = {
            "should": [
                {"key": "filename", "match": {"text": "Supermicro"}},
                {"key": "filename", "match": {"text": "sys-"}},
                {"key": "filename", "match": {"text": "as-"}}
            ]
        }
    elif any(x in query_upper for x in ["AMD", "EPYC", "RYZEN", "THREADRIPPER", "เอเอ็มดี"]):
        conditions.append({"key": "filename", "match": {"text": "AMD"}})
    elif any(x in query_upper for x in ["INTEL", "XEON", "อินเทล"]):
        conditions.append({"key": "filename", "match": {"text": "Intel"}})
    
    if not search_filter and conditions:
        search_filter = {"must": conditions}

    payload = {
        "vector": vector,
        "limit": 50,
        "with_payload": True
    }
    if search_filter:
        payload["filter"] = search_filter

    res = requests.post(f"{QDRANT_URL}/collections/{COLLECTION_NAME}/points/search", json=payload)
    res.raise_for_status()
    result = res.json().get("result", [])
    points = result if isinstance(result, list) else []
    
    def score_chunk(p):
        text = p.get("payload", {}).get("text", "").upper()
        fname = p.get("payload", {}).get("filename", "").upper()
        score = 0
        if "H200" in text: score += 1000
        if "HGX" in text: score += 2000
        if "8 X" in text or "8X" in text or "8 GPU" in text: score += 1500
        if "BAYS" in text or "SATA" in text or "NVME" in text: score += 800 # Boost for storage queries
        if "G593" in fname or "G593" in text: score += 2000
        if "G493" in fname or "G493" in text: score += 1200
        if "EPYC" in text or "9004" in text or "9005" in text: score += 1000
        if "XEON" in text or "W-3400" in text or "W-2400" in text: score += 1000
        return score

    points.sort(key=score_chunk, reverse=True)
    
    # Diversification: Ensure we get chunks from different files
    seen_files = set()
    diverse_points = []
    for p in points:
        fname = p.get("payload", {}).get("filename")
        if fname not in seen_files:
            diverse_points.append(p)
            seen_files.add(fname)
        if len(diverse_points) >= 12: break # Get 12 unique files
        
    # If we don't have enough unique files, fill with remaining points
    if len(diverse_points) < 12:
        for p in points:
            if p not in diverse_points:
                diverse_points.append(p)
            if len(diverse_points) >= 15: break

    await manager.broadcast({
        "stage": "retrieval_end", 
        "files": list(seen_files)
    })
    
    return diverse_points[:12]

async def call_llm(system_prompt: str, user_content: str, history: List[Dict[str, str]] = None):
    messages = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_content})
    
    payload = {
        "model": MODEL_GEN,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.1}
    }
    
    try:
        res = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=120)
        res.raise_for_status()
        return res.json()["message"]["content"]
    except Exception as e:
        logger.error(f"LLM Call failed: {e}")
        raise e

async def process_query(user_id: str, query_text: str):
    logger.info(f"Processing: {query_text}")
    await manager.broadcast({"stage": "query_received", "text": query_text, "user": user_id})
    
    # Get history for this specific user
    history = get_history(user_id)
    
    context_docs = await hybrid_search(query_text)
    context_text = "\n".join([f"Source File: {d.get('payload',{}).get('filename')}\n{d.get('payload',{}).get('text')}" for d in context_docs])
    
    system_prompt = """คุณคือผู้เชี่ยวชาญด้านเทคนิค Server และชิปประมวลผล
    ภารกิจ: ค้นหาและระบุข้อมูลทางเทคนิค (CPU, GPU, Storage, HDD, RAM, PCIe, Memory Channels) จากข้อมูลที่ให้มาเท่านั้น
    - ระบุรุ่น (Model), จำนวนคอร์ (Cores), ความเร็ว (Clock Speed), และเทคโนโลยีเด่น
    - สังเกตข้อมูลจำนวน HDD/SSD ในส่วน 'Drive Bays' หรือ 'Storage'
    - ตอบให้ชัดเจน ระบุตัวเลขและหน่วยที่ถูกต้องตามเอกสาร
    - หากไม่พบข้อมูลในบริบท ให้แจ้งว่าไม่พบข้อมูล แต่พยายามสรุปข้อมูลที่มีประโยชน์ที่สุดจากไฟล์ที่ดึงมา"""
    
    user_content = f"CONTEXT DATA:\n{context_text}\n\nUSER QUESTION: {query_text}"
    
    await manager.broadcast({"stage": "llm_start"})
    final_answer = await call_llm(system_prompt, user_content, history=history)
    await manager.broadcast({"stage": "llm_end", "answer": final_answer})
    
    save_history(user_id, "user", query_text)
    save_history(user_id, "assistant", final_answer)
    return final_answer


# --- API Endpoints ---

@app.websocket("/ws/flow")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

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
    if event["type"] != "message" or event["message"]["type"] != "text":
        return {"status": "ok"}

    user_id = event["source"]["userId"]
    text = event["message"]["text"]
    
    async def run_and_reply():
        try:
            answer = await process_query(user_id, text)
            res = requests.post("https://api.line.me/v2/bot/message/push",
                          headers={"Authorization": f"Bearer {LINE_TOKEN}"},
                          json={"to": user_id, "messages": [{"type": "text", "text": answer}]})
            res.raise_for_status()
        except Exception as e:
            logger.error(f"Error in background task: {e}")
            try:
                requests.post("https://api.line.me/v2/bot/message/push",
                          headers={"Authorization": f"Bearer {LINE_TOKEN}"},
                          json={"to": user_id, "messages": [{"type": "text", "text": "ขออภัยครับ ระบบขัดข้องชั่วคราว"}]})
            except: pass

    asyncio.create_task(run_and_reply())
    return {"status": "ok"}

import psutil
import shutil

@app.get("/api/status")
async def get_status():
    status = {
        "api": "online",
        "ollama": "offline",
        "qdrant": "offline",
        "model": MODEL_GEN,
        "hardware": {
            "cpu": psutil.cpu_percent(),
            "ram": psutil.virtual_memory().percent,
            "hdd": psutil.disk_usage("/").percent,
            "gpu": 0
        }
    }
    
    # GPU Monitoring
    try:
        gpu_res = subprocess.check_output(["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"], encoding='utf-8')
        status["hardware"]["gpu"] = float(gpu_res.strip().split('\n')[0])
    except: pass

    try:
        res = requests.get(f"{OLLAMA_URL}/api/tags", timeout=2)
        if res.status_code == 200: status["ollama"] = "online"
    except: pass
    try:
        res = requests.get(f"{QDRANT_URL}/collections", timeout=2)
        if res.status_code == 200: status["qdrant"] = "online"
    except: pass
    return status

from ingest_optimized import run_ingestion
import threading

@app.post("/api/ingest")
async def trigger_ingest():
    def progress_callback(data):
        # We need an event loop to run the async broadcast from a thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(manager.broadcast(data))
        loop.close()

    def do_ingest():
        try:
            run_ingestion(progress_callback=progress_callback)
        except Exception as e:
            logger.error(f"Manual ingestion failed: {e}")
            # Since do_ingest runs in a thread, we use a separate loop to broadcast error
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(manager.broadcast({"stage": "system", "message": f"Ingestion Error: {str(e)}"}))
            loop.close()

    threading.Thread(target=do_ingest).start()
    return {"status": "ingestion_started"}

@app.post("/api/restart")
async def restart_system():
    await manager.broadcast({"stage": "system", "message": "System restart initiated."})
    def do_restart():
        import time
        time.sleep(1)
        subprocess.run(["sudo", "systemctl", "restart", "km-rag.service"], check=False)
    import threading
    threading.Thread(target=do_restart).start()
    return {"status": "restarting"}

@app.get("/api/debug/ws")
async def debug_ws():
    return {"active_connections": len(manager.active_connections)}

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
