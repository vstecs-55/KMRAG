# KM RAG: Data Ingestion Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an automated pipeline to ingest diverse documents (PDF, Word, Excel, PPT, Images) from a local directory into Qdrant using n8n and Ollama.

**Architecture:**
- **Trigger:** Scheduled trigger (weekly) or manual.
- **Processing:** n8n orchestrates the flow. Custom Python code nodes are used for specialized parsing.
- **Intelligence:** Llama 3.2 Vision via Ollama is used to describe images/diagrams.
- **Storage:** Qdrant stores both dense vectors (semantic) and sparse vectors (keyword) for hybrid search.

**Tech Stack:** n8n, Ollama (Llama 3.2 Vision), Qdrant, Python (via n8n Code nodes).

---

### Task 1: Qdrant Collection Configuration

**Files:**
- Create: `scripts/setup_collection.py`

- [ ] **Step 1: Write script to create the 'km_knowledge' collection**
```python
import requests

def setup_collection():
    url = "http://localhost:6333/collections/km_knowledge/upsert" # Simplified for example
    # Note: In actual implementation, use /collections/create
    # Vector size: 1024 (for mxbai-embed-large)
    # Distance: Cosine
    print("Creating collection 'km_knowledge' with Cosine distance and 1024 dimensions...")
    # Implementation code here...

if __name__ == "__main__":
    setup_collection()
```

- [ ] **Step 2: Run script to initialize the vector store**
Run: `python3 scripts/setup_collection.py`
Expected: Collection created successfully.

- [ ] **Step 3: Commit**
```bash
git add scripts/setup_collection.py
git commit -m "infra: initialize qdrant collection for km_rag"
```

### Task 2: Base Ingestion Workflow (n8n)

**Files:**
- Create: `docs/n8n/ingestion_workflow_spec.md` (to document the node logic)

- [ ] **Step 1: Define the workflow structure in the spec**
(Define nodes: Local File Trigger $\rightarrow$ File Type Switch $\rightarrow$ Parser Route)

- [ ] **Step 2: Implement the basic n8n workflow**
(Setup the trigger to monitor `/home/admin/Documents/Projects/KM RAG/Database`)

- [ ] **Step 3: Verify file detection**
Test: Drop a file in the folder and verify n8n triggers.

- [ ] **Step 4: Commit the spec**
```bash
git add docs/n8n/ingestion_workflow_spec.md
git commit -m "docs: add ingestion workflow specification"
```

### Task 3: Vision Parsing Integration (Images $\rightarrow$ Text)

**Files:**
- Modify: n8n Workflow (Code Node)

- [ ] **Step 1: Implement Ollama Vision API call in n8n**
```javascript
// n8n Code Node logic
const response = await axios.post('http://localhost:11434/api/generate', {
  model: 'llama3.2-vision:11b',
  prompt: 'Describe this technical diagram/image in detail for a knowledge base. Focus on components and relationships.',
  images: [base64Image]
});
```

- [ ] **Step 2: Test image description quality**
Test: Pass a hardware diagram from `Database/` and verify the output text.

- [ ] **Step 3: Commit any supporting helper scripts**
```bash
git commit -m "feat: integrate llama3.2-vision for image parsing"
```

### Task 4: Advanced Text Parsing (Excel & PDF)

**Files:**
- Create: `scripts/parsers.py` (to be used as reference or via n8n execute-command)

- [ ] **Step 1: Implement Excel $\rightarrow$ Markdown Table converter**
```python
import pandas as pd
def excel_to_markdown(file_path):
    df = pd.read_excel(file_path)
    return df.to_markdown()
```

- [ ] **Step 2: Implement Semantic Chunking for PDF/Word**
(Implement Recursive Character Splitter with overlap to preserve context)

- [ ] **Step 3: Test parsing on actual datasheets**
Verify that tables in Excel and sections in PDF are preserved correctly.

- [ ] **Step 4: Commit**
```bash
git add scripts/parsers.py
git commit -m "feat: add advanced parsers for excel and pdf"
```

### Task 5: Hybrid Indexing into Qdrant

**Files:**
- Modify: n8n Workflow (Qdrant Node)

- [ ] **Step 1: Configure Vector Embedding call**
(Connect to Ollama embeddings model)

- [ ] **Step 2: Implement metadata attachment**
(Attach: `filename`, `page_number`, `source_type`, `timestamp`)

- [ ] **Step 3: Configure Hybrid Indexing**
(Ensure both dense and sparse vectors are pushed to Qdrant)

- [ ] **Step 4: Commit**
```bash
git commit -m "feat: implement hybrid indexing into qdrant"
```

### Task 6: End-to-End Validation

- [ ] **Step 1: Run full ingestion on the Database folder**
Expected: All files in `/Database` are processed without errors.

- [ ] **Step 2: Verify data in Qdrant**
Run a simple query to check if a known technical term from a PDF is retrievable.

- [ ] **Step 3: Final Commit**
```bash
git commit -m "test: validate end-to-end ingestion pipeline"
```
