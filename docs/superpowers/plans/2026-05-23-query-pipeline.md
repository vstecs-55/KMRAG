# KM RAG: Query Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a high-precision, agentic query pipeline that retrieves information from Qdrant and generates detailed Thai responses via Line Messaging API.

**Architecture:** 
- **Interface:** Line Webhook $\rightarrow$ Cloudflare Tunnel $\rightarrow$ n8n.
- **Core Logic:** Agentic Router (Intent Analysis) $\rightarrow$ Hybrid Retrieval (Dense+Sparse) $\rightarrow$ Llama 3.1 Generation $\rightarrow$ Refinement Gate.
- **Memory:** User-specific chat history stored in SQLite/Redis keyed by `userId`.

**Tech Stack:** n8n, Qdrant, Ollama (Llama 3.1 70B, mxbai-embed-large), Line Messaging API, SQLite.

---

### Task 1: Chat History Storage Setup

**Files:**
- Create: `scripts/setup_memory.py`

- [ ] **Step 1: Write script to initialize history database**
```python
import sqlite3

def init_db():
    conn = sqlite3.connect('chat_history.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS history (
            user_id TEXT,
            role TEXT,
            content TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, timestamp)
        )
    ''')
    conn.commit()
    conn.close()
    print("Chat history database initialized.")

if __name__ == "__main__":
    init_db()
```

- [ ] **Step 2: Run initialization script**
Run: `python3 scripts/setup_memory.py`
Expected: `Chat history database initialized.`

- [ ] **Step 3: Commit**
```bash
git add scripts/setup_memory.py
git commit -m "feat: initialize chat history database"
```

### Task 2: Line Webhook & Intent Router Implementation

**Files:**
- Create: `docs/n8n/query_workflow_spec.md`
- Modify: n8n Workflow

- [ ] **Step 1: Create detailed workflow spec for the Router**
(Define the prompt for the Intent Router LLM to classify queries into: Technical, Pricing, Visual, General)

- [ ] **Step 2: Implement Line Webhook trigger in n8n**
(Configure Webhook node to accept Line events and extract `userId` and `text`)

- [ ] **Step 3: Implement the Intent Router node**
(HTTP Request to Ollama: analyze query + history $\rightarrow$ return `intent_type`)

- [ ] **Step 4: Verify routing logic**
Test: Send "สวัสดี" $\rightarrow$ Expect `General`; Send "ราคา EPYC 9004" $\rightarrow$ Expect `Pricing`.

- [ ] **Step 5: Commit spec**
```bash
git add docs/n8n/query_workflow_spec.md
git commit -m "docs: add query pipeline workflow spec"
```

### Task 3: Hybrid Retrieval & Reranking Implementation

**Files:**
- Modify: n8n Workflow

- [ ] **Step 1: Implement Dense Embedding call**
(HTTP Request to Ollama: `mxbai-embed-large` $\rightarrow$ vector)

- [ ] **Step 2: Implement Qdrant Hybrid Search**
(Use the `intent_type` to adjust search weights between dense and sparse vectors)

- [ ] **Step 3: Implement Reranking logic**
(Filter and sort top-K results to ensure the most relevant chunks are passed to the generator)

- [ ] **Step 4: Verify retrieval quality**
Test: Query a specific part number $\rightarrow$ Verify the exact document is retrieved.

- [ ] **Step 5: Commit**
```bash
git commit -m "feat: implement hybrid retrieval and reranking"
```

### Task 4: Detailed Generation & Refinement Gate

**Files:**
- Modify: n8n Workflow

- [ ] **Step 1: Implement Draft Generation**
(HTTP Request to Llama 3.1 70B using the "Detailed Consultant" persona and retrieved context)

- [ ] **Step 2: Implement the Refinement Gate**
(Secondary LLM call to verify the draft against the context for hallucinations and detail level)

- [ ] **Step 3: Implement Thai-only output constraint**
(Ensure system prompt strictly mandates Thai language)

- [ ] **Step 4: Verify response quality**
Test: Ask a complex technical question $\rightarrow$ Verify the answer is detailed, accurate, and in Thai.

- [ ] **Step 5: Commit**
```bash
git commit -m "feat: implement detailed generation and refinement gate"
```

### Task 5: Line Response & Memory Update

**Files:**
- Modify: n8n Workflow

- [ ] **Step 1: Implement Line Response node**
(HTTP Request to Line Messaging API to send the final refined answer)

- [ ] **Step 2: Implement Memory Update node**
(Execute SQL to save the current exchange to `chat_history.db`)

- [ ] **Step 3: End-to-End Testing**
Test: Full flow from Line $\rightarrow$ n8n $\rightarrow$ Qdrant $\rightarrow$ Line.

- [ ] **Step 4: Commit**
```bash
git commit -m "feat: complete query pipeline with memory and line integration"
```
