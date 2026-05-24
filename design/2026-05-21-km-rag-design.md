---
name: km-rag-design
description: Design specification for the KM RAG system using n8n and Ollama
metadata:
  type: project-spec
  date: 2026-05-21
---

# Design Specification: KM RAG System

## 1. Overview
The KM RAG system is a local-first, privacy-preserving knowledge retrieval system that allows users to query technical hardware documentation via the Line Application. It prioritizes accuracy and detail over response speed, leveraging high-performance local hardware (DGX Spark).

### 1.1 Core Objectives
- **Interface:** Line Messaging API (Group Chat / Tagging Bot).
- **Knowledge Base:** Local folder containing Word, Excel, PDF, PowerPoint, and Images.
- **Processing:** Local LLMs via Ollama to ensure data privacy.
- **Accuracy:** High precision through Hybrid Search and Agentic retrieval.

## 2. System Architecture

### 2.1 High-Level Component Diagram
`User (Line)` $\rightarrow$ `n8n (Orchestrator)` $\rightarrow$ `Vector DB (Qdrant)` $\rightarrow$ `LLM (Ollama)` $\rightarrow$ `User (Line)`

### 2.2 Component Details
- **Orchestrator:** n8n (Self-hosted). Handles API integrations, workflow logic, and agentic routing.
- **LLM Engine:** Ollama.
    - **Generation:** Llama 3.1 70B (for high-accuracy final answers).
    - **Vision:** Llama 3.2 Vision (for describing images/diagrams).
    - **Embeddings:** `mxbai-embed-large` or similar high-dimension local embedding model.
- **Vector Store:** Qdrant. Supports hybrid search (Vector + Full-text), which is critical for technical part numbers.
- **Integration:** Line Messaging API.

## 3. Data Pipeline (Ingestion)
The pipeline runs once per week to synchronize the local database folder with the Vector DB.

### 3.1 Ingestion Workflow
1. **File Scanning:** n8n scans `/home/admin/Documents/Projects/KM RAG/Database`.
2. **Format-Specific Parsing:**
    - **PDF/Word/PPT:** Text extraction $\rightarrow$ Semantic Chunking (keeping headers and context).
    - **Excel:** Conversion to Markdown tables to preserve row-column relationships.
    - **Images:** Llama 3.2 Vision generates a detailed textual description of the image/diagram.
3. **Embedding & Indexing:**
    - Generate vectors for all text chunks.
    - Store in Qdrant with metadata (filename, page number, source type).
    - Create sparse indexes for keyword-based retrieval of technical terms.

## 4. Query Pipeline (Retrieval & Generation)

### 4.1 Agentic Workflow
When a message is received via Line:
1. **Intent Analysis:** The Agent (LLM) analyzes the query to determine the search strategy:
    - *Technical Specification* $\rightarrow$ Priority to PDF/Word chunks.
    - *Pricing/Quantities* $\rightarrow$ Priority to Excel chunks.
    - *Visual/Diagram* $\rightarrow$ Priority to Image descriptions.
2. **Hybrid Retrieval:**
    - **Dense Search:** Finds semantically similar content.
    - **Sparse Search:** Finds exact matches for model numbers (e.g., "EPYC 9004").
3. **Reranking:** Use a cross-encoder or a refined LLM prompt to select the top-K most relevant chunks.
4. **Grounded Generation:**
    - Prompt the LLM with the retrieved context.
    - **Constraint:** "Answer ONLY based on the provided context. If information is missing, state that it is not found or provide the closest available match."

## 5. Technical Constraints & Success Criteria
- **Hardware:** Optimized for DGX Spark (NVIDIA Blackwell GPU, 121Gi RAM).
- **Privacy:** No data leaves the local network.
- **Success Metric:** Correct identification of technical specs from complex datasheets and tables.
- **Failure Mode:** If no relevant information is found, the system should politely inform the user or provide the most relevant partial match.

## 6. Implementation Phases
1. **Phase 1: Infrastructure** (n8n, Ollama, Qdrant setup).
2. **Phase 2: Ingestion Pipeline** (File parsing $\rightarrow$ Vectorization).
3. **Phase 3: Retrieval Pipeline** (Line API $\rightarrow$ Search $\rightarrow$ Generation).
4. **Phase 4: Tuning & Validation** (Testing accuracy and agentic routing).
