# Query Workflow Specification: Line Webhook & Intent Router

## Overview
The Query Workflow is the entry point for all user interactions via the Line Messaging API. Its primary purpose is to receive incoming messages, retrieve conversation context, and route the query to the appropriate RAG strategy based on the detected intent.

## Workflow Architecture

### 1. Webhook Entry
- **Node**: Webhook
- **Input**: HTTP POST request from Line Messaging API.
- **Data Extraction**:
    - `userId`: From `body.events[0].source.userId`
    - `text`: From `body.events[0].message.text`

### 2. Context Retrieval (Memory)
- **Node**: Execute Command / HTTP Request
- **Action**: Query `chat_history.db` for the last 5 messages associated with the `userId`.
- **Purpose**: Provide short-term memory to the Intent Router to handle anaphoras (e.g., "How much is it?" referring to a product mentioned previously).

### 3. Intent Router
- **Node**: HTTP Request (Ollama API)
- **Model**: `Llama 3.1 70B`
- **Endpoint**: `http://localhost:11434/api/chat`
- **System Prompt (Thai)**:
  "คุณคือผู้เชี่ยวชาญในการวิเคราะห์เจตนา (Intent Classifier) ของลูกค้าที่สอบถามเกี่ยวกับสินค้าไอทีและอุปกรณ์ฮาร์ดแวร์
  หน้าที่ของคุณคือวิเคราะห์ข้อความของผู้ใช้ร่วมกับประวัติการสนทนา และจำแนกประเภทของคำถามออกเป็น 4 กลุ่มดังนี้:
  1. Technical Spec: คำถามเกี่ยวกับคุณสมบัติทางเทคนิค, สเปกเครื่อง, การรองรับ (Compatibility), หรือประสิทธิภาพ
  2. Pricing/Quantity: คำถามเกี่ยวกับราคา, จำนวนสินค้าในสต็อก, การสั่งซื้อ, หรือส่วนลด
  3. Visual/Architecture: คำถามที่ต้องการรูปภาพ, แผนผัง, การออกแบบทางกายภาพ หรือการจัดวางอุปกรณ์
  4. General/Greeting: การทักทาย, คำถามทั่วไปที่ไม่เจาะจงสินค้า, หรือการพูดคุยทั่วไป

  คำตอบของคุณต้องเป็น JSON format เท่านั้น โดยมีโครงสร้างดังนี้:
  {
    \"intent_type\": \"ชื่อประเภทที่เลือก\",
    \"reason\": \"เหตุผลสั้นๆ ในการตัดสินใจ\"
  }
  ห้ามตอบข้อความอื่นนอกเหนือจาก JSON"

- **Payload**: Includes the system prompt, the retrieved chat history, and the current user query.

### 4. Routing Logic (Switch)
- **Node**: Switch
- **Routing Criteria**: `intent_type` from the JSON response.
- **Paths**:
    - `Technical Spec` $\rightarrow$ Technical RAG Pipeline
    - `Pricing/Quantity` $\rightarrow$ Pricing/Inventory Pipeline
    - `Visual/Architecture` $\rightarrow$ Visual/Asset Pipeline
    - `General/Greeting` $\rightarrow$ General Response / Greeting Flow

## Intent Definitions

| Intent | Description | Example Query |
| :--- | :--- | :--- |
| Technical Spec | Technical queries about hardware specs, CPU/GPU, compatibility. | "CPU ตัวนี้รองรับ RAM DDR5 หรือไม่?" |
| Pricing/Quantity | Queries about costs, stock availability, and orders. | "ราคา EPYC 9004 เท่าไหร่ครับ?" |
| Visual/Architecture | Requests for photos, diagrams, or physical layouts. | "ขอดูรูปบอร์ด Gigabyte ตัวนี้หน่อย" |
| General/Greeting | Greetings or general conversation. | "สวัสดีครับ", "ใครอยู่ในนี้บ้าง" |

## Verification Plan
1. **Mock Webhook**: Send a `curl` request simulating a Line event.
2. **Routing Test**:
    - Test greeting $\rightarrow$ `General/Greeting`
    - Test pricing query $\rightarrow$ `Pricing/Quantity`
    - Test spec query $\rightarrow$ `Technical Spec`
    - Test visual request $\rightarrow$ `Visual/Architecture`
3. **Context Test**: Send a product query followed by "ราคาเท่าไหร่" to verify if `Pricing/Quantity` is correctly identified using history.
