---
name: km-rag-query-pipeline
description: Design specification for the KM RAG Query Pipeline using n8n, Qdrant, and Llama 3.1
metadata:
  type: project-spec
  date: 2026-05-23
---

# Design Specification: KM RAG Query Pipeline

## 1. Overview
The Query Pipeline is the user-facing component of the KM RAG system. It enables users to query technical hardware documentation via the Line Application, providing high-precision, detailed answers in Thai. It uses an "Agentic Router 2.5" approach to balance search accuracy, response quality, and latency.

### 1.1 Core Objectives
- **Interface:** Line Messaging API.
- **Persona:** Semi-formal, Detailed Consultant.
- **Language:** Thai only.
- **Accuracy:** High precision through Hybrid Search and a refinement gate to prevent hallucinations.
- **Context:** User-specific chat history (per `userId`) to maintain conversation flow.

## 2. System Architecture

### 2.1 High-Level Data Flow
`User (Line)` $\rightarrow$ `Cloudflare Tunnel` $\rightarrow$ `n8n (Orchestrator)` $\rightarrow$ `Qdrant (Hybrid Search)` $\rightarrow$ `Llama 3.1 (Generation & Refinement)` $\rightarrow$ `User (Line)`

### 2.2 Component Details

#### 2.2.1 Intent Router (The Router)
The first stage of the pipeline. An LLM analyzes the incoming query and the user's chat history to determine the `intent_type`.
- **Intents:**
    - `Technical Spec`: High priority to PDF/Word chunks.
    - `Pricing/Quantity`: High priority to Excel/CSV chunks.
    - `Visual/Architecture`: High priority to Image descriptions.
    - `General/Greeting`: No search required; direct response.

#### 2.2.2 Hybrid Search Engine
Performs retrieval based on the `intent_type`.
- **Dense Retrieval:** Uses `mxbai-embed-large` via Ollama for semantic meaning.
- **Sparse Retrieval:** Uses Qdrant's sparse vectors for exact technical keywords/part numbers.
- **Reranking:** The top-K results from both paths are merged and reranked to select the most relevant context.

#### 2.2.3 Response Generator
Generates a draft answer using Llama 3.1 70B.
- **Prompting:** Uses a system prompt that enforces the "Detailed Consultant" persona and requires the answer to be grounded in the retrieved context.
- **Drafting:** Creates a detailed, structured response in Thai.

#### 2.2.4 Refinement Gate (The 2.5 Stage)
A final verification step before sending the response.
- **Verification:** Checks the draft answer against the context for hallucinations.
- **Optimization:** If the answer is too brief or missing a key detail found in the context, it expands the response.
- **Fallback:** If no relevant information is found, it generates a polite "not found" response suggesting the closest available information.

#### 2.2.5 Conversation Memory
- **Storage:** Per-user history stored in a database (e.g., SQLite/Redis) keyed by Line `userId`.
- **Window:** Maintains the last 5-10 exchanges to provide context without overflowing the LLM context window.

## 3. Technical Implementation

### 3.1 Connectivity & Infrastructure
- **Tunnel:** `cloudflared` connects `linehook.bigdata-ai.online` to n8n port 5678.
- **LLM:** Llama 3.1 70B via Ollama for generation; `mxbai-embed-large` for embeddings.
- **Database:** Qdrant (Collection: `km_knowledge`).

### 3.2 Response Logic (Thai)
- **Tone:** Semi-formal (สุภาพแต่เป็นกันเอง).
- **Structure:** [Acknowledgement] $\rightarrow$ [Detailed Answer] $\rightarrow$ [Source Reference] $\rightarrow$ [Follow-up Suggestion].

## 4. Error Handling & Edge Cases
- **No Context Found:** *"จากการตรวจสอบเอกสารทางเทคนิคที่มีอยู่ ไม่พบข้อมูลส่วนนี้อย่างชัดเจน แต่ข้อมูลที่ใกล้เคียงที่สุดคือ..."*
- **System Timeout:** Send an interim message: *"ขออภัยครับ ระบบกำลังประมวลผลข้อมูลเชิงลึก กรุณารอสักครู่..."*
- **Critical Error:** *"ขออภัยครับ เกิดข้อผิดพลาดทางเทคนิคชั่วคราว กรุณาลองส่งคำถามอีกครั้งในอีกสักครู่ครับ"*

## 5. Success Criteria
- **Accuracy:** Correct identification of technical specs from diverse sources.
- **Persona:** Consistency in the "Detailed Consultant" tone.
- **Latency:** End-to-end response time within an acceptable range for a high-detail bot.
- **Stability:** Correct handling of multiple concurrent users with isolated histories.
