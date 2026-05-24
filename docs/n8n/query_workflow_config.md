# n8n Query Workflow Configuration Guide

This document provides the exact configuration for the nodes in the Query Workflow to ensure consistent implementation.

## 1. Webhook Node
- **HTTP Method**: `POST`
- **Path**: `line-query-webhook`
- **Response Mode**: `When Last Node Finishes`
- **Extraction (Expression)**:
    - `userId`: `{{ $json.body.events[0].source.userId }}`
    - `text`: `{{ $json.body.events[0].message.text }}`

## 2. Memory Retrieval Node (HTTP Request / Execute Command)
- **Method**: `Execute Command`
- **Command**:
  ```bash
  sqlite3 "/home/admin/Documents/Projects/KM RAG/chat_history.db" "SELECT role, content FROM history WHERE user_id='{{ $json.userId }}' ORDER BY timestamp DESC LIMIT 5;"
  ```
- **Post-processing**: Use a `Code` node to convert the SQLite output into a JSON array of messages.

## 3. Intent Router Node (HTTP Request)
- **Method**: `POST`
- **URL**: `http://localhost:11434/api/chat`
- **Authentication**: `None`
- **Body Parameters (JSON)**:
    - `model`: `llama3.3:70b`
    - `messages`:
      ```json
      [
        { "role": "system", "content": "คุณคือผู้เชี่ยวชาญในการวิเคราะห์เจตนา... (see query_workflow_spec.md)" },
        {{ $node["Memory Retrieval"].json.history }},
        { "role": "user", "content": "{{ $node["Webhook"].json.text }}" }
      ]
      ```
    - `stream`: `false`
    - `format`: `json`

## 4. Switch Node
- **Data Type**: `String`
- **Value to Test**: `{{ $json.message.content.intent_type }}`
- **Routing Rules**:
    - `Technical Spec` $\rightarrow$ Route to Technical RAG
    - `Pricing/Quantity` $\rightarrow$ Route to Pricing/Inventory RAG
    - `Visual/Architecture` $\rightarrow$ Route to Visual/Asset RAG
    - `General/Greeting` $\rightarrow$ Route to Greeting/General Flow

## 5. Embedding Generation (HTTP Request)
- **Method**: `POST`
- **URL**: `http://localhost:11434/api/embeddings`
- **Body**:
    - `model`: `mxbai-embed-large`
    - `prompt`: `{{ $node["Webhook"].json.text }}`

## 6. Hybrid Search (Qdrant Node / HTTP Request)
- **Operation**: Hybrid Search (Dense + Sparse)
- **Dense Vector**: `{{ $node["Embedding Generation"].json.embedding }}`
- **Sparse Query**: `{{ $node["Webhook"].json.text }}`
- **Integration**: Reciprocal Rank Fusion (RRF)
- **Limit**: Top 10 results

## 7. Reranking Step (HTTP Request)
- **Method**: `POST`
- **URL**: `http://localhost:11434/api/chat`
- **Body**:
    - `model`: `llama3.3:70b`
    - `messages`:
        - System: `You are a precision reranker. I will provide you with 10 retrieved documents and a user query. Your task is to select the Top 5 most relevant documents and order them by relevance. Return only a JSON list of the original document IDs in the new order.`
        - User: `Query: {{ $node["Webhook"].json.text }}\n\nDocuments:\n{{ $node["Hybrid Search"].json.results }}`
    - `format`: `json`
- **Purpose**: Refine the Top-10 retrieval results to Top-5 for maximum precision.

## 8. Draft Generation (HTTP Request)
- **Method**: `POST`
- **URL**: `http://localhost:11434/api/chat`
- **Body**:
    - `model`: `llama3.3:70b`
    - `messages`:
        - System: |
            คุณคือที่ปรึกษาผู้เชี่ยวชาญ (Detailed Consultant) ที่มีความเป็นมืออาชีพและให้ข้อมูลอย่างละเอียด โดยใช้ภาษาที่เป็นทางการในระดับกึ่งทางการ (Semi-formal)

            งานของคุณคือการตอบคำถามของผู้ใช้โดยใช้ 'บริบท (Context)' ที่ได้รับมาเท่านั้น หากข้อมูลในบริบทไม่เพียงพอ ให้แจ้งผู้ใช้อย่างสุภาพว่าไม่พบข้อมูลดังกล่าวในฐานข้อมูล

            **โครงสร้างการตอบกลับที่ต้องปฏิบัติตามอย่างเคร่งครัด:**
            1. **[Acknowledgement]**: กล่าวรับทราบคำถามและเกริ่นนำสั้นๆ ให้ดูเป็นมืออาชีพ
            2. **[Detailed Answer]**: ให้คำตอบที่ละเอียด ครบถ้วน และเจาะลึก โดยวิเคราะห์จากข้อมูลในบริบท หากเป็นข้อมูลเชิงเทคนิค ให้เน้นความถูกต้องและคำอธิบายที่เข้าใจง่ายแต่ลึกซึ้ง
            3. **[Source Reference]**: ระบุแหล่งที่มาของข้อมูลที่ใช้ในคำตอบ (เช่น ชื่อไฟล์ หรือหัวข้อ)
            4. **[Follow-up Suggestion]**: แนะนำคำถามหรือหัวข้อที่เกี่ยวข้องที่ผู้ใช้อาจสนใจเพิ่มเติม เพื่อนำไปสู่การให้คำปรึกษาที่สมบูรณ์ขึ้น

            **ข้อกำหนดสำคัญ:**
            - ต้องตอบเป็นภาษาไทยเท่านั้น
            - ห้ามสร้างข้อมูลขึ้นมาเอง (No Hallucinations) นอกเหนือจากที่ระบุในบริบท
            - รักษาบุคลิกภาพของที่ปรึกษาที่พร้อมช่วยเหลือและให้ข้อมูลเชิงลึก
        - User: `Context: {{ $node["Reranking Step"].json.top_5_docs }}\n\nQuery: {{ $node["Webhook"].json.text }}`
    - `stream`: `false`

## 9. Refinement Gate (HTTP Request)
- **Method**: `POST`
- **URL**: `http://localhost:11434/api/chat`
- **Body**:
    - `model`: `llama3.3:70b`
    - `messages`:
        - System: |
            คุณคือผู้ตรวจสอบคุณภาพคำตอบ (Quality Assurance Gate) สำหรับระบบ RAG โดยมีหน้าที่ตรวจสอบคำตอบที่ร่างขึ้นมาเปรียบเทียบกับบริบทที่ได้รับ

            **เกณฑ์การตรวจสอบ:**
            1. **การหลอนของข้อมูล (Hallucinations)**: มีข้อมูลใดในคำตอบที่ไม่อยู่ในบริบทที่ให้มาหรือไม่? หากมี ต้องตัดออกหรือแก้ไขให้ถูกต้องตามบริบท
            2. **ระดับรายละเอียด (Detail Level)**: คำตอบมีความละเอียดเพียงพอสำหรับระดับ 'ที่ปรึกษาผู้เชี่ยวชาญ' หรือไม่? หากสั้นเกินไป หรือขาดการวิเคราะห์เชิงลึก ให้ทำการขยายความโดยใช้ข้อมูลจากบริบท
            3. **ความเป็นธรรมชาติของภาษา (Language)**: ภาษาไทยที่ใช้มีความเป็นธรรมชาติ สละสลวย และคงระดับกึ่งทางการ (Semi-formal) หรือไม่?

            **แนวทางการดำเนินการ:**
            - หากคำตอบผ่านเกณฑ์ทั้งหมด: ให้ตอบกลับด้วยคำว่า 'APPROVED' ตามด้วยคำตอบเดิม
            - หากคำตอบไม่ผ่านเกณฑ์: ให้เขียนคำตอบฉบับปรับปรุง (Refined Version) ที่แก้ไขข้อบกพร่องข้างต้น โดยยังคงโครงสร้าง [Acknowledgement] $\rightarrow$ [Detailed Answer] $\rightarrow$ [Source Reference] $\rightarrow$ [Follow-up Suggestion] และต้องเป็นภาษาไทยเท่านั้น
        - User: `Context: {{ $node["Reranking Step"].json.top_5_docs }}\n\nDraft Answer: {{ $node["Draft Generation"].json.message.content }}`
    - `stream`: `false`
- **Fallback Mechanism**: หาก Refinement Gate ไม่สามารถให้คำตอบที่ใช้งานได้ (เช่น เกิด Error หรือผลลัพธ์ว่างเปล่า) ให้ระบบ Fallback ไปใช้คำตอบจาก `Draft Generation` โดยเพิ่มคำเตือน (Disclaimer) ต่อท้ายว่า: "ขออภัย ข้อมูลนี้เป็นฉบับร่างเบื้องต้น โปรดตรวจสอบความถูกต้องอีกครั้ง"

## 10. Post-Processing (Code Node)
- **Purpose**: ลบ Prefix ที่ใช้ในการตรวจสอบออกก่อนส่งคำตอบให้ผู้ใช้
- **Logic**: ใช้ Code node เพื่อ Strip คำว่า `APPROVED` หรือ `REFINED:` ออกจากจุดเริ่มต้นของข้อความ
- **Code Snippet**:
  ```javascript
  const text = $json.message.content;
  const finalResponse = text.replace(/^APPROVED\s*/i, '').replace(/^REFINED:\s*/i, '');
  return { finalResponse };
  ```

## Testing the Webhook
...
You can simulate a Line webhook request using the following `curl` command:

```bash
curl -X POST http://localhost:5678/webhook/line-query-webhook \
-H "Content-Type: application/json" \
-d '{
  "events": [
    {
      "source": { "userId": "test_user_123" },
      "message": { "text": "ราคา EPYC เท่าไหร่ครับ" }
    }
  ]
}'
```
