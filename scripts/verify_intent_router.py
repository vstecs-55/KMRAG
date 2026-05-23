import sqlite3
import requests
import json
import sys

DB_PATH = "/home/admin/Documents/Projects/KM RAG/chat_history.db"
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.3:70b" # Adjust if the model name is different

SYSTEM_PROMPT = """คุณคือผู้เชี่ยวชาญในการวิเคราะห์เจตนา (Intent Classifier) ของลูกค้าที่สอบถามเกี่ยวกับสินค้าไอทีและอุปกรณ์ฮาร์ดแวร์
หน้าที่ของคุณคือวิเคราะห์ข้อความของผู้ใช้ร่วมกับประวัติการสนทนา และจำแนกประเภทของคำถามออกเป็น 4 กลุ่มดังนี้:
1. Technical Spec: คำถามเกี่ยวกับคุณสมบัติทางเทคนิค, สเปกเครื่อง, การรองรับ (Compatibility), หรือประสิทธิภาพ
2. Pricing/Quantity: คำถามเกี่ยวกับราคา, จำนวนสินค้าในสต็อก, การสั่งซื้อ, หรือส่วนลด
3. Visual/Architecture: คำถามที่ต้องการรูปภาพ, แผนผัง, การออกแบบทางกายภาพ หรือการจัดวางอุปกรณ์
4. General/Greeting: การทักทาย, คำถามทั่วไปที่ไม่เจาะจงสินค้า, หรือการพูดคุยทั่วไป

คำตอบของคุณต้องเป็น JSON format เท่านั้น โดยมีโครงสร้างดังนี้:
{
  "intent_type": "ชื่อประเภทที่เลือก",
  "reason": "เหตุผลสั้นๆ ในการตัดสินใจ"
}
ห้ามตอบข้อความอื่นนอกเหนือจาก JSON"""

def get_chat_history(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role, content FROM history WHERE user_id = ? ORDER BY timestamp DESC LIMIT 5",
        (user_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    # Reverse to get chronological order
    return [{"role": row[0], "content": row[1]} for row in reversed(rows)]

def classify_intent(user_id, text):
    history = get_chat_history(user_id)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in history:
        messages.append(msg)
    messages.append({"role": "user", "content": text})

    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": False,
        "format": "json"
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload)
        response.raise_for_status()
        result = response.json()
        return json.loads(result['message']['content'])
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python verify_intent_router.py <userId> <text>")
        sys.exit(1)

    user_id = sys.argv[1]
    text = sys.argv[2]

    print(f"Query: {text}")
    print(f"User ID: {user_id}")
    result = classify_intent(user_id, text)
    print(json.dumps(result, indent=2, ensure_ascii=False))
