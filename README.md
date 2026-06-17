# KM RAG - Knowledge Management System

ระบบถาม-ตอบอัจฉริยะ (RAG) สำหรับข้อมูลเทคนิค Server โดยใช้ Qdrant และ Ollama

## คุณสมบัติ
- **Hybrid Search:** ค้นหาข้อมูลจากไฟล์ PDF, Excel, Word, และ Text ได้อย่างแม่นยำ
- **Strict Brand Filtering:** รองรับการค้นหาเจาะจงแบรนด์ (Gigabyte, Supermicro)
- **Fast Performance:** ปรับจูนให้ตอบกลับไวด้วย Llama 3.2 11B
- **LINE Integration:** เชื่อมต่อกับ LINE Messaging API

## การติดตั้งในเครื่องใหม่

1. **ติดตั้ง Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **เริ่มระบบ Database (Qdrant):**
   ```bash
   docker-compose up -d
   ```

3. **ตั้งค่าตัวแปรสภาพแวดล้อม:**
   ```bash
   cp .env.example .env
   ```
   แก้ไขไฟล์ `.env` และเติมค่าที่จำเป็น เช่น `LINE_TOKEN`

4. **นำเข้าข้อมูล (Ingestion):**
   วางไฟล์ PDF/Excel ของคุณในโฟลเดอร์ `Database/` แล้วรัน:
   ```bash
   python3 ingest_all.py
   ```

5. **รันระบบ:**
   ```bash
   python3 app.py
   ```

## โครงสร้างโปรเจกต์
- `app.py`: ไฟล์หลักสำหรับรัน API และ Bot
- `ingest_all.py`: สคริปต์สำหรับนำเข้าข้อมูลทั้งหมดเข้าสู่ฐานข้อมูล
- `Database/`: โฟลเดอร์สำหรับเก็บไฟล์เอกสาร (PDF, XLSX, etc.)
- `scripts/`: สคริปต์เสริมสำหรับระบบ
