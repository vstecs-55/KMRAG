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
    
    # Define brands and their identifiers
    brands = {
        "GIGABYTE": ["GIGABYTE", "GIGABYUT", "GIGA", "จิกะไบต์"],
        "SUPERMICRO": ["SUPERMICRO", "SUPER", "ซุปเปอร์ไมโคร"],
        "AMD": ["AMD", "EPYC", "RYZEN", "THREADRIPPER", "เอเอ็มดี"],
        "INTEL": ["INTEL", "XEON", "อินเทล"],
        "CLOUDERA": ["CLOUDERA", "คลาวเดอร่า"],
        "NVIDIA": ["NVIDIA", "เอนวีเดีย"],
        "INFINITIX": ["INFINITIX", "อินฟินิทิกซ์"],
        "SOLOMON": ["SOLOMON", "โซโลมอน"],
        "SAS": ["SAS", "แซส", "เอสเอเอส", "สาส"]
    }
    
    matched_brand = None
    search_filter = None
    brand_conditions = []
    
    for brand, keywords in brands.items():
        if any(kw in query_upper for kw in keywords):
            matched_brand = brand
            if brand == "SUPERMICRO":
                brand_conditions.append({
                    "should": [
                        {"key": "filename", "match": {"text": "Supermicro"}},
                        {"key": "filename", "match": {"text": "sys-"}},
                        {"key": "filename", "match": {"text": "as-"}}
                    ]
                })
            else:
                # Case-insensitive brand matching in filename
                brand_conditions.append({
                    "should": [
                        {"key": "filename", "match": {"text": brand.upper()}},
                        {"key": "filename", "match": {"text": brand.lower()}},
                        {"key": "filename", "match": {"text": brand.capitalize()}}
                    ]
                })
            break 
    
    if brand_conditions:
        search_filter = {"must": brand_conditions}

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
        if "BAYS" in text or "SATA" in text or "NVME" in text: score += 800 
        if "G593" in fname or "G593" in text: score += 2000
        if "G493" in fname or "G493" in text: score += 1200
        if "EPYC" in text or "9004" in text or "9005" in text: score += 1000
        if "XEON" in text or "W-3400" in text or "W-2400" in text: score += 1000
        if "CLOUDERA" in text or "CLOUDERA" in fname: score += 1500
        if "SAS" in text or "SAS" in fname: score += 1500
        if "SOLOMON" in text or "SOLOMON" in fname: score += 1500
        if "INFINITIX" in text or "INFINITIX" in fname: score += 1500
        if "NVIDIA" in text or "NVIDIA" in fname: score += 1500
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
    
    return diverse_points[:12], matched_brand

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
    logger.info(f"Processing: {query_text} (User: {user_id})")
    await manager.broadcast({"stage": "query_received", "text": query_text, "user": user_id})
    
    # Save user query immediately
    save_history(user_id, "user", query_text)
    
    # --- INTENT ROUTING (Greeting / Small Talk) ---
    greetings = ["สวัสดี", "hello", "hi", "หวัดดี", "สอบถาม", "ถามหน่อย", "กูรู", "expert"]
    query_lower = query_text.lower().strip()
    
    # If it's just a greeting or very short, don't use RAG
    if any(g == query_lower for g in greetings) or (len(query_lower) < 15 and any(g in query_lower for g in greetings)):
        greeting_response = "สวัสดีครับ! ผมคือผู้เชี่ยวชาญด้านเทคนิค Server และ Software Solutions ยินดีให้ข้อมูลเกี่ยวกับผลิตภัณฑ์ GIGABYTE, Supermicro, AMD, Intel, NVIDIA, Cloudera, SAS, Infinitix และ Solomon ครับ วันนี้ต้องการสอบถามเรื่องอะไรดีครับ?"
        await manager.broadcast({"stage": "llm_end", "answer": greeting_response})
        save_history(user_id, "assistant", greeting_response)
        return greeting_response

    # Get history for this specific user
    history = get_history(user_id)
    
    try:
        context_docs, matched_brand = await hybrid_search(query_text)
        context_text = "\n".join([f"Source File: {d.get('payload',{}).get('filename')}\n{d.get('payload',{}).get('text')}" for d in context_docs])
        
        # Check for brand switch in history to force clear
        history_to_send = [h for h in history if h["role"] != "user" or h["content"] != query_text]
        if matched_brand:
            last_assistant_msg = next((m["content"].upper() for m in reversed(history_to_send) if m["role"] == "assistant"), "")
            if last_assistant_msg and matched_brand not in last_assistant_msg:
                logger.info(f"Brand switch detected: {matched_brand}. Clearing history for this turn.")
                history_to_send = []

        system_prompt = """คุณคือที่ปรึกษาด้านเทคนิค Server และ Software Solutions ผู้เชี่ยวชาญ
        ภารกิจ: ตอบคำถามโดยใช้ข้อมูลจาก "CONTEXT DATA" ที่ให้มาเท่านั้น
        - **สำคัญ**: หากข้อมูลใน CONTEXT DATA มีความกระจัดกระจายหรือเป็นข้อความสั้นๆ ให้พยายามสรุปใจความสำคัญที่เกี่ยวข้องกับคำถามที่สุด
        - ตอบคำถามปัจจุบันโดยตรงในประโยคแรก
        - ห้ามนำข้อมูลจากแบรนด์อื่นที่เคยคุยก่อนหน้ามาตอบเด็ดขาด ให้ยึดตามเอกสารที่ดึงมา (CONTEXT DATA) ล่าสุดเท่านั้น
        - หากไม่พบข้อมูลที่ระบุใน CONTEXT DATA จริงๆ ให้แจ้งว่าไม่พบข้อมูลในเอกสาร
        - ใช้ภาษาไทยที่กระชับ เป็นทางการ และตรงประเด็น"""
        
        user_content = f"--- IMPORTANT: NEW TOPIC ({matched_brand or 'General'}) ---\nCONTEXT DATA:\n{context_text}\n\nUSER QUESTION: {query_text}"
        
        await manager.broadcast({"stage": "llm_start"})
        final_answer = await call_llm(system_prompt, user_content, history=history_to_send)
        await manager.broadcast({"stage": "llm_end", "answer": final_answer})
        
        save_history(user_id, "assistant", final_answer)
        return final_answer
    except Exception as e:
        error_msg = f"ขออภัยครับ เกิดข้อผิดพลาดในการประมวลผล: {str(e)}"
        logger.error(f"Error processing query: {e}")
        save_history(user_id, "assistant", error_msg)
        return error_msg


# --- API Endpoints ---

class ModelUpdate(BaseModel):
    model: str

@app.get("/api/models")
async def list_models():
    try:
        res = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        res.raise_for_status()
        models = res.json().get("models", [])
        return {"models": [m["name"] for m in models]}
    except Exception as e:
        logger.error(f"Failed to fetch models: {e}")
        return {"models": [MODEL_GEN]}

@app.post("/api/model")
async def update_model(data: ModelUpdate):
    global MODEL_GEN
    MODEL_GEN = data.model
    logger.info(f"Active model updated to: {MODEL_GEN}")
    return {"status": "success", "model": MODEL_GEN}

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
