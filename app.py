import os
import re
import json
import uuid
import sqlite3
import logging
import asyncio
import subprocess
import threading

import requests
import psutil
from dotenv import load_dotenv
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any

load_dotenv()

# Configuration
QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
COLLECTION_NAME = os.environ.get("COLLECTION_NAME", "km_knowledge")
DB_PATH = os.environ.get("DB_PATH", "chat_history.db")
LINE_TOKEN = os.environ.get("LINE_TOKEN", "")
MODEL_GEN = os.environ.get("MODEL_GEN", "llama3.2-vision:11b")
MODEL_EMBED = os.environ.get("MODEL_EMBED", "mxbai-embed-large")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KM-RAG-API")

app = FastAPI()

# --- Database Initialization ---

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_user ON history(user_id, timestamp DESC)")
    conn.commit()
    conn.close()

init_db()

@app.on_event("startup")
async def warmup_models():
    # Preload gen model into VRAM in background so the first real query doesn't hit the 180s timeout
    def ping():
        try:
            requests.post(f"{OLLAMA_URL}/api/generate",
                          json={"model": MODEL_GEN, "prompt": "hi", "keep_alive": -1, "options": {"num_predict": 1}},
                          timeout=600)
            logger.info(f"Model warmup complete: {MODEL_GEN}")
        except Exception as e:
            logger.warning(f"Model warmup failed: {e}")
    threading.Thread(target=ping, daemon=True).start()

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
    res = requests.post(f"{OLLAMA_URL}/api/embeddings", json={"model": MODEL_EMBED, "prompt": text, "keep_alive": -1})
    res.raise_for_status()
    return res.json()["embedding"]

# --- Brand Configuration ---

PRIMARY_BRANDS = {
    "GIGABYTE": ["GIGABYTE", "GIGABYUT", "GIGA", "จิกะไบต์"],
    "SUPERMICRO": ["SUPERMICRO", "SUPER", "ซุปเปอร์ไมโคร"],
    "SAS": ["SAS", "แซส", "เอสเอเอส", "สาส"],
    "SOLOMON": ["SOLOMON", "โซโลมอน"],
    "CLOUDERA": ["CLOUDERA", "คลาวเดอร่า"],
    "INFINITIX": ["INFINITIX", "อินฟินิทิกซ์"],
    "NVIDIA": ["NVIDIA", "เอนวีเดีย"]
}

COMPONENT_BRANDS = {
    "AMD": ["AMD", "EPYC", "RYZEN", "THREADRIPPER", "เอเอ็มดี"],
    "INTEL": ["INTEL", "XEON", "อินเทล"]
}

ALL_BRAND_KEYWORDS = {**PRIMARY_BRANDS, **COMPONENT_BRANDS}

async def hybrid_search(query_text: str, brand_override: str = None):
    search_query = query_text
    query_upper = query_text.upper()
    
    # Query enhancement for better retrieval
    if "H200" in query_upper:
        search_query += " NVIDIA H200 HGX SXM5 8-GPU System"
    if "GH200" in query_upper:
        search_query += " NVIDIA GH200 Grace Hopper Superchip"
    if "JETSON" in query_upper:
        search_query += " NVIDIA Jetson Orin embedded GPU module"
    if "AETINA" in query_upper:
        search_query += " Aetina NVIDIA embedded GPU card"
    if any(x in query_upper for x in ["HDD", "SSD", "STORAGE", "BAYS", "ฮาร์ดดิสก์"]):
        search_query += " Storage Specification Drive Bays Capacity"
    if "NVME" in query_upper or "M.2" in query_upper:
        search_query += " NVMe M.2 Storage Drive"
    if "DDR5" in query_upper:
        search_query += " DDR5 Memory DIMM"
    if "CORES" in query_upper or "CORE" in query_upper:
        search_query += " CPU Cores Threads Processor"
    if "GPU" in query_upper and "SUPPORT" not in query_upper:
        search_query += " GPU Graphics Card Accelerator"
    if "LIQUID" in query_upper or "COOLING" in query_upper:
        search_query += " Liquid Cooling Thermal"
    if "SLOT" in query_upper or "SLOTS" in query_upper or "PCIE" in query_upper:
        search_query += " PCIe Slot Expansion"
    if "POWER" in query_upper and "SUPPLY" in query_upper:
        search_query += " Power Supply PSU"
    if "CLOudERA" in query_upper or "คลาวเดอร่า" in query_upper:
        search_query += " Cloudera Big Data Hadoop Data Platform"
    if "INFINITIX" in query_upper or "อินฟินิทิกซ์" in query_upper:
        search_query += " Infinitix AI Stack GPU"
    if "SOLOMON" in query_upper or "โซโลมอน" in query_upper:
        search_query += " Solomon AI Wearable Smart Solution"
    if "SAS" in query_upper:
        search_query += " SAS Analytics Software Platform"
    # Add specific model number for better matching
    model_nums = re.findall(r'\b\d{4}[A-Z]?\b', query_upper)
    for num in model_nums:
        search_query += f" {num} specification datasheet"
        
    await manager.broadcast({"stage": "retrieval_start", "query": search_query})
    vector = await asyncio.to_thread(get_embedding, search_query)
    
    matched_primary_brand = brand_override if brand_override in PRIMARY_BRANDS else None
    matched_component_brand = brand_override if brand_override in COMPONENT_BRANDS else None
    
    # Detect both primary and component brands simultaneously
    detected_primary_brands = []
    detected_component_brands = []
    
    for brand, keywords in PRIMARY_BRANDS.items():
        if any(kw in query_upper for kw in keywords):
            detected_primary_brands.append(brand)
            
    for brand, keywords in COMPONENT_BRANDS.items():
        if any(kw in query_upper for kw in keywords):
            detected_component_brands.append(brand)
    
    if not matched_primary_brand and detected_primary_brands:
        matched_primary_brand = detected_primary_brands[0]
        
    if not matched_primary_brand:
        if re.search(r'\b[A-Z]{1,2}[0-9]{2,3}(-[A-Z0-9]+)?\b', query_upper):
            matched_primary_brand = "GIGABYTE"
            
    if not matched_component_brand and detected_component_brands:
        matched_component_brand = detected_component_brands[0]
    
    # For cross-brand queries, use primary brand filter but keep component brand for scoring
    has_cross_brand = len(detected_primary_brands) > 0 and len(detected_component_brands) > 0
    
    def perform_qdrant_search(filter_brand=None):
        search_filter = None
        brand_conditions = []
        if filter_brand:
            if filter_brand == "SUPERMICRO":
                brand_conditions.append({"should": [{"key": "filename", "match": {"text": "Supermicro"}}, {"key": "filename", "match": {"text": "sys-"}}, {"key": "filename", "match": {"text": "as-"}}, {"key": "filename", "match": {"text": "ars-"}}, {"key": "filename", "match": {"text": "ssg-"}}]})
            elif filter_brand == "NVIDIA":
                # Use specific keywords based on query content
                if "JETSON" in query_upper:
                    brand_conditions.append({"should": [{"key": "filename", "match": {"text": "Jetson"}}, {"key": "filename", "match": {"text": "jetson"}}]})
                elif "AETINA" in query_upper:
                    brand_conditions.append({"should": [{"key": "filename", "match": {"text": "Aetina"}}, {"key": "filename", "match": {"text": "aie-"}}, {"key": "filename", "match": {"text": "aip-"}}, {"key": "filename", "match": {"text": "aimxm"}}]})
                elif "DGX" in query_upper:
                    brand_conditions.append({"should": [{"key": "filename", "match": {"text": "dgx"}}, {"key": "filename", "match": {"text": "nvidia"}}, {"key": "filename", "match": {"text": "NVIDIA"}}]})
                elif "H200" in query_upper:
                    brand_conditions.append({"should": [{"key": "filename", "match": {"text": "h200"}}, {"key": "filename", "match": {"text": "nvidia"}}, {"key": "filename", "match": {"text": "NVIDIA"}}]})
                elif "GH200" in query_upper:
                    brand_conditions.append({"should": [{"key": "filename", "match": {"text": "gh200"}}, {"key": "filename", "match": {"text": "ars-111"}}, {"key": "filename", "match": {"text": "nvidia"}}]})
                else:
                    # General NVIDIA query - include all NVIDIA-related files
                    brand_conditions.append({"should": [{"key": "filename", "match": {"text": "nvidia"}}, {"key": "filename", "match": {"text": "NVIDIA"}}, {"key": "filename", "match": {"text": "dgx"}}, {"key": "filename", "match": {"text": "h200"}}, {"key": "filename", "match": {"text": "jetson"}}, {"key": "filename", "match": {"text": "aetina"}}]})
            elif filter_brand == "GIGABYTE":
                brand_conditions.append({"should": [{"key": "filename", "match": {"text": "gigabyte"}}, {"key": "filename", "match": {"text": "GIGABYTE"}}, {"key": "filename", "match": {"text": "Gigabyte"}}]})
            elif filter_brand == "AMD":
                brand_conditions.append({"should": [{"key": "filename", "match": {"text": "amd"}}, {"key": "filename", "match": {"text": "AMD"}}, {"key": "filename", "match": {"text": "epyc"}}]})
            elif filter_brand == "INTEL":
                brand_conditions.append({"should": [{"key": "filename", "match": {"text": "intel"}}, {"key": "filename", "match": {"text": "INTEL"}}, {"key": "filename", "match": {"text": "Intel"}}, {"key": "filename", "match": {"text": "xeon"}}]})
            elif filter_brand == "CLOUDERA":
                brand_conditions.append({"should": [{"key": "filename", "match": {"text": "cloudera"}}, {"key": "filename", "match": {"text": "CLOUDERA"}}, {"key": "filename", "match": {"text": "Cloudera"}}, {"key": "filename", "match": {"text": "hadoop"}}]})
            elif filter_brand == "INFINITIX":
                brand_conditions.append({"should": [{"key": "filename", "match": {"text": "infinitix"}}, {"key": "filename", "match": {"text": "INFINITIX"}}, {"key": "filename", "match": {"text": "Infinitix"}}, {"key": "filename", "match": {"text": "AI-Stack"}}, {"key": "filename", "match": {"text": "ai-stack"}}, {"key": "filename", "match": {"text": "ai stack"}}]})
            elif filter_brand == "SAS":
                brand_conditions.append({"should": [{"key": "filename", "match": {"text": "sas"}}, {"key": "filename", "match": {"text": "SAS"}}]})
            elif filter_brand == "SOLOMON":
                brand_conditions.append({"should": [{"key": "filename", "match": {"text": "solomon"}}, {"key": "filename", "match": {"text": "SOLOMON"}}]})
            else:
                brand_conditions.append({"should": [{"key": "filename", "match": {"text": filter_brand.upper()}}, {"key": "filename", "match": {"text": filter_brand.lower()}}, {"key": "filename", "match": {"text": filter_brand.capitalize()}}]})
        
        if brand_conditions:
            search_filter = {"must": brand_conditions}

        payload = {"vector": vector, "limit": 70, "with_payload": True}
        if search_filter: payload["filter"] = search_filter
        
        res = requests.post(f"{QDRANT_URL}/collections/{COLLECTION_NAME}/points/search", json=payload)
        res.raise_for_status()
        return res.json().get("result", [])

    # First attempt: with detected brand
    points = await asyncio.to_thread(perform_qdrant_search, matched_primary_brand)

    # Fallback: if no results and a brand was used, try without brand filter
    if not points and matched_primary_brand:
        logger.info(f"Fallback search: 0 results with brand {matched_primary_brand}, retrying without filter.")
        points = await asyncio.to_thread(perform_qdrant_search, None)
        matched_primary_brand = None # Reset brand if fallback triggered

    # For cross-brand queries, also search for component brand files
    if has_cross_brand and matched_component_brand:
        component_points = await asyncio.to_thread(perform_qdrant_search, None)  # Search without filter for component brand
        # Add component brand results that aren't already in the list
        existing_ids = {p.get("id") for p in points}
        for p in component_points:
            if p.get("id") not in existing_ids:
                text = p.get("payload", {}).get("text", "").upper()
                if matched_component_brand in text:
                    points.append(p)
                    existing_ids.add(p.get("id"))

    # Score and Rank
    def score_chunk(p):
        text = p.get("payload", {}).get("text", "").upper()
        fname = p.get("payload", {}).get("filename", "").upper()
        score = 0
        
        # Extract model numbers from query and check if they appear in text
        # Match patterns like: 9754, 9654P, SYS-511R-ML, G294-S43, H173-Z80
        query_model_numbers = re.findall(r'\b\d{4}[A-Z]?\b', query_upper)
        for model_num in query_model_numbers:
            if model_num in text:
                score += 15000
            if model_num in fname:
                score += 10000
        
        # Match patterns like: SYS-511R, G294, H173
        query_model_parts = re.findall(r'\b[A-Z]+-?\d{3,4}[A-Z-]*\b', query_upper)
        for part in query_model_parts:
            if part in text:
                score += 12000
            if part in fname:
                score += 10000
        
        # Also check for partial matches like 511R, G294
        query_short = re.findall(r'\b\d{3}[A-Z]?\b', query_upper)
        for part in query_short:
            if part in text:
                score += 8000
            if part in fname:
                score += 6000
        
        model_match = re.search(r'[0-9]{3}-[A-Z0-9-]{3,}', text)
        if model_match: score += 5000
        
        # Keyword relevance
        if "H200" in text: score += 1000
        if "HGX" in text: score += 2000
        if "8 X" in text or "8X" in text or "8 GPU" in text: score += 1500
        if "BAYS" in text or "SATA" in text or "NVME" in text: score += 1200 
        if "DDR5" in text and "DDR5" in query_upper: score += 2000
        if "CORES" in text and "CORE" in query_upper: score += 2000
        if "LIQUID" in text and "LIQUID" in query_upper: score += 2000
        if "SLOT" in text and "SLOT" in query_upper: score += 1500
        if "POWER SUPPLY" in text and "POWER" in query_upper: score += 1500
        if "JETSON" in text and "JETSON" in query_upper: score += 3000
        if "AETINA" in text and "AETINA" in query_upper: score += 3000
        if "GH200" in text and "GH200" in query_upper: score += 3000
        if "INTEL" in text and "INTEL" in query_upper: score += 1500
        if "AMD" in text and "AMD" in query_upper: score += 1500
        if "CLOudERA" in text and "CLOudERA" in query_upper: score += 2000
        if "INFINITIX" in text and "INFINITIX" in query_upper: score += 2000
        if "SOLOMON" in text and "SOLOMON" in query_upper: score += 2000
        if "SAS" in text and "SAS" in query_upper and len(query_upper) < 15: score += 1500
        
        # Brand matching (filename)
        if matched_primary_brand and matched_primary_brand in fname: score += 10000
        if "GIGABYTE" in fname or "GIGABYTE" in text: score += 2000
        if "SUPERMICRO" in fname or "SUPERMICRO" in text: score += 2000
        
        if matched_component_brand and matched_component_brand in text: score += 1500
        
        return score

    points.sort(key=score_chunk, reverse=True)
    
    # Priority: exact model match first, then diversity
    exact_model_matches = []
    other_points = []
    
    # Extract model parts from query - match full model like G294-S43, SYS-511R-ML
    query_model_parts = re.findall(r'\b[A-Z]+-?\d{3,4}-?[A-Z0-9]+(?:-[A-Z0-9]+)*\b', query_upper)
    # Match 4-digit model numbers like 9754, 9654
    query_4digit = re.findall(r'\b\d{4}[A-Z]?\b', query_upper)
    
    all_query_parts = query_model_parts + query_4digit
    
    for p in points:
        fname = p.get("payload", {}).get("filename", "").upper()
        text = p.get("payload", {}).get("text", "").upper()
        
        # Check if this is an exact model match
        is_exact = False
        for part in all_query_parts:
            if len(part) >= 5:  # Only full model matches (G294-S43, 9754, etc.)
                if part in fname or part in text:
                    is_exact = True
                    break
        
        if is_exact:
            exact_model_matches.append(p)
        else:
            other_points.append(p)
    
    # If we have exact matches, also search for more chunks from the same file
    if exact_model_matches and len(exact_model_matches) < 5:
        # Find the exact model filename
        exact_filenames = set()
        for p in exact_model_matches:
            exact_filenames.add(p.get("payload", {}).get("filename", ""))
        
        # Add more chunks from the same files
        for p in points:
            fname = p.get("payload", {}).get("filename", "")
            if fname in exact_filenames and p not in exact_model_matches:
                exact_model_matches.append(p)
                if len(exact_model_matches) >= 10:
                    break
    
    # Take all exact matches first, then fill with diversity
    file_chunk_counts = {}
    diverse_points = []
    
    # Add exact matches (up to 5 per file)
    for p in exact_model_matches:
        fname = p.get("payload", {}).get("filename")
        count = file_chunk_counts.get(fname, 0)
        if count < 5:
            diverse_points.append(p)
            file_chunk_counts[fname] = count + 1
    
    # Add other points with diversity (up to 3 per file)
    for p in other_points:
        fname = p.get("payload", {}).get("filename")
        count = file_chunk_counts.get(fname, 0)
        if count < 3:
            diverse_points.append(p)
            file_chunk_counts[fname] = count + 1
        if len(diverse_points) >= 20: break
        
    await manager.broadcast({
        "stage": "retrieval_end", 
        "files": list(file_chunk_counts.keys())
    })
    
    return diverse_points, (matched_primary_brand or matched_component_brand)

async def call_llm(system_prompt: str, user_content: str, history: List[Dict[str, str]] = None):
    messages = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_content})
    
    payload = {
        "model": MODEL_GEN,
        "messages": messages,
        "stream": False,
        "keep_alive": -1,  # pin model in VRAM; cold load of 24GB qwen3.6 blows the 180s timeout
        "options": {"temperature": 0.1}
    }
    
    try:
        res = await asyncio.to_thread(requests.post, f"{OLLAMA_URL}/api/chat", json=payload, timeout=180)
        res.raise_for_status()
        return res.json()["message"]["content"]
    except Exception as e:
        logger.error(f"LLM Call failed: {e}")
        raise e

async def process_query(user_id: str, query_text: str, brand_override: str = None):
    logger.info(f"Processing: {query_text} (User: {user_id})")
    await manager.broadcast({"stage": "query_received", "text": query_text, "user": user_id})
    
    query_upper = query_text.upper()
    query_clean = query_text.lower().replace(" ", "").strip()
    
    has_brand = any(kw in query_upper for kw_list in ALL_BRAND_KEYWORDS.values() for kw in kw_list)
    if not has_brand:
        if re.search(r'\b[A-Z]{1,2}[0-9]{2,3}(-[A-Z0-9]+)?\b', query_upper):
            has_brand = True
    
    is_greeting = False
    greetings = ["สวัสดี", "hello", "hi", "หวัดดี", "สวส", "กูรู", "guru", "expert", "ทักทาย", "ดีจ้า", "ดีครับ", "สอบถาม", "ถาม", "ขอทราบ"]
    for g in greetings:
        if g in query_clean:
            is_greeting = True
            break
            
    if is_greeting and (not has_brand or len(query_text) < 12):
        greeting_response = "สวัสดีครับ! ผมคือผู้เชี่ยวชาญด้านเทคนิค Server และ Software Solutions ยินดีให้ข้อมูลเกี่ยวกับผลิตภัณฑ์ GIGABYTE, Supermicro, AMD, Intel, NVIDIA, Cloudera, SAS, Infinitix และ Solomon ครับ วันนี้ต้องการสอบถามเรื่องอะไรดีครับ?"
        await manager.broadcast({"stage": "llm_end", "answer": greeting_response})
        save_history(user_id, "user", query_text)
        save_history(user_id, "assistant", greeting_response)
        return greeting_response

    history = get_history(user_id)
    save_history(user_id, "user", query_text)
    
    brand_from_history = None
    if not has_brand and not brand_override:
        for h in reversed(history):
            h_upper = h["content"].upper()
            for brand, keywords in ALL_BRAND_KEYWORDS.items():
                if any(kw in h_upper for kw in keywords):
                    brand_from_history = brand
                    break
            if brand_from_history: break

    effective_brand = brand_override or brand_from_history
    try:
        context_docs, matched_brand = await hybrid_search(query_text, brand_override=effective_brand)
        
        if not context_docs:
            no_info_msg = f"ขออภัยครับ ไม่พบข้อมูลเกี่ยวกับเรื่องนี้ในเอกสารที่จัดเตรียมไว้ (แบรนด์: {matched_brand or 'ทั่วไป'}) กรุณาสอบถามเกี่ยวกับแบรนด์ที่เราดูแล เช่น GIGABYTE, Supermicro, NVIDIA, SAS, Solomon เป็นต้นครับ"
            await manager.broadcast({"stage": "llm_end", "answer": no_info_msg})
            save_history(user_id, "assistant", no_info_msg)
            return no_info_msg

        # Build context with model list and numbered docs
        def is_readable(text):
            """Check if text has readable content (not just raw table data)"""
            words = text.split()
            if len(words) < 10: return False
            alpha_ratio = sum(c.isalpha() for c in text) / max(len(text), 1)
            return alpha_ratio > 0.3
        
        # Sort: readable text first, then raw data
        readable_docs = [d for d in context_docs if is_readable(d.get("payload", {}).get("text", ""))]
        raw_docs = [d for d in context_docs if not is_readable(d.get("payload", {}).get("text", ""))]
        sorted_docs = readable_docs[:12] + raw_docs[:8]
        
        unique_models = list(dict.fromkeys(d.get("payload", {}).get("filename", "unknown") for d in sorted_docs))
        model_list = "\n".join(f"  - {m}" for m in unique_models[:20])
        model_header = f"MODELS AVAILABLE (from filenames):\n{model_list}\n\n---\n\n"
        context_parts = []
        for idx, d in enumerate(sorted_docs, 1):
            fname = d.get("payload", {}).get("filename", "unknown")
            text = d.get("payload", {}).get("text", "")
            context_parts.append(f"[Doc {idx}] {fname}\n{text.strip()}")
        context_text = model_header + "\n---\n".join(context_parts)
        
        history_to_send = history
        if matched_brand:
            current_detected_brand = None
            for brand, keywords in ALL_BRAND_KEYWORDS.items():
                if any(kw in query_upper for kw in keywords):
                    current_detected_brand = brand
                    break
            
            if current_detected_brand:
                last_assistant_msg = next((m["content"].upper() for m in reversed(history_to_send) if m["role"] == "assistant"), "")
                if last_assistant_msg:
                    last_was_different_brand = False
                    for b, kws in PRIMARY_BRANDS.items():
                        if b != current_detected_brand and any(kw in last_assistant_msg for kw in kws):
                            last_was_different_brand = True
                            break
                    
                    if last_was_different_brand:
                        logger.info(f"Brand switch detected: {current_detected_brand}. Clearing history for this turn.")
                        history_to_send = []

        system_prompt = """คุณคือผู้เชี่ยวชาญด้านเทคนิค Server และ Software Solutions
ภารกิจ: ตอบคำถามโดยใช้ข้อมูลจากเอกสารที่ให้มา

กฎการตอบ:
- วิเคราะห์ข้อมูลในเอกสารให้ดี ทั้งข้อความปกติ ตาราง และข้อมูลดิบ
- ข้อมูลตารางมักจะมี model name ตามด้วยตัวเลข เช่น 9754, 9654, SYS-511R-ML
- หากพบข้อมูลที่เกี่ยวข้อง ให้ตอบตามข้อมูลนั้นโดยตรง
- หากเอกสารมีข้อมูลของแบรนด์หรือผลิตภัณฑ์ที่เกี่ยวข้อง ให้ใช้ข้อมูลนั้นตอบ
- หากมีข้อมูลบางส่วนที่เกี่ยวข้อง ให้ตอบตามข้อมูลที่มี พร้อมระบุว่าเป็นข้อมูลบางส่วน
- ห้ามคิดค้นสเปคหรือตัวเลขขึ้นมาเอง
- หากไม่มีข้อมูลเลยจริงๆ ให้แจ้งว่าไม่พบข้อมูล
- สังเกต "MODELS AVAILABLE" ที่แสดงรายการโมเดลทั้งหมด ใช้ข้อมูลนั้นในการตอบคำถามเกี่ยวกับโมเดล
- ตอบคำถามปัจจุบันโดยตรงในประโยคแรก
- ใช้ภาษาไทยที่กระชับ เป็นทางการ และตรงประเด็น
- หากมีข้อมูลในเอกสารที่เกี่ยวข้องกับคำถาม แม้จะไม่ตรง 100% ให้ตอบตามข้อมูลที่มี"""
        
        user_content = f"CONTEXT DATA:\n{context_text}\n\nUSER QUESTION: {query_text}"
        
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
def list_models():  # ponytail: sync def = FastAPI runs it in threadpool, blocking requests.get is fine here
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

BIGDATA_AUTH_URL = os.environ.get("BIGDATA_AUTH_URL", "http://localhost:8000")

def is_bigdata_admin(token: str) -> bool:
    """Validate a Bigdata Website JWT and require role=admin (backend is the source of truth)."""
    if not token:
        return False
    try:
        res = requests.get(f"{BIGDATA_AUTH_URL}/api/auth/me",
                           headers={"Authorization": f"Bearer {token}"}, timeout=5)
        return res.status_code == 200 and res.json().get("role") == "admin"
    except Exception:
        return False

@app.websocket("/ws/flow")
async def websocket_endpoint(websocket: WebSocket):
    # The flow feed broadcasts every user's queries/answers → admin only
    token = websocket.query_params.get("token", "")
    if not await asyncio.to_thread(is_bigdata_admin, token):
        await websocket.accept()
        await websocket.close(code=4401)
        return
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/")
async def read_root():
    return FileResponse("chat.html")

@app.get("/dashboard")
async def read_dashboard():
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
            res = await asyncio.to_thread(requests.post, "https://api.line.me/v2/bot/message/push",
                          headers={"Authorization": f"Bearer {LINE_TOKEN}"},
                          json={"to": user_id, "messages": [{"type": "text", "text": answer}]})
            res.raise_for_status()
        except Exception as e:
            logger.error(f"Error in background task: {e}")
            try:
                await asyncio.to_thread(requests.post, "https://api.line.me/v2/bot/message/push",
                          headers={"Authorization": f"Bearer {LINE_TOKEN}"},
                          json={"to": user_id, "messages": [{"type": "text", "text": "ขออภัยครับ ระบบขัดข้องชั่วคราว"}]})
            except: pass

    asyncio.create_task(run_and_reply())
    return {"status": "ok"}

@app.post("/api/chat")
async def web_chat(request: Request):
    body = await request.json()
    user_id = (body.get("user_id") or "web_anonymous").strip()
    message = (body.get("message") or "").strip()
    brand = (body.get("brand") or "").strip().upper() or None
    if not message:
        return {"answer": "", "brand": brand or ""}
    answer = await process_query(user_id, message, brand_override=brand)
    return {"answer": answer, "brand": brand or ""}

from ingest_slow import main as run_ingestion_slow

@app.get("/api/status")
def get_status():  # ponytail: sync def = FastAPI runs it in threadpool, blocking requests.get is fine here
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

@app.post("/api/ingest")
async def trigger_ingest():
    threading.Thread(target=run_ingestion_slow).start()
    return {"status": "ingestion_started"}

@app.post("/api/restart")
async def restart_system():
    await manager.broadcast({"stage": "system", "message": "System restart initiated."})
    def do_restart():
        import time
        time.sleep(1)
        subprocess.run(["sudo", "systemctl", "restart", "km-rag.service"], check=False)
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
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)
