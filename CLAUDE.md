# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

KM RAG is a Thai-language RAG (retrieval-augmented generation) system that answers technical
questions about server hardware and software products. It retrieves from a local Qdrant vector
store and generates answers with a local Ollama LLM. The product domain is a fixed set of brands
(GIGABYTE, Supermicro, NVIDIA, AMD, Intel, Cloudera, SAS, Infinitix, Solomon) and much of the
retrieval logic is hand-tuned around those brands and their model-number conventions.

It serves two front-ends: a web chat (`chat.html` at `/`, `dashboard.html` at `/dashboard`) and a
LINE Messaging API bot (`/webhook`, alias `/line/webhook`). Answers are expected to be in Thai.

**Respond to the user in Thai** during pair programming in this repo (per `.agents/AGENTS.md`).

## Architecture

The request pipeline lives almost entirely in `app.py` and flows:

`process_query` → `hybrid_search` → `call_llm`

- **`process_query`** orchestrates a turn: greeting short-circuit, brand carry-over from chat
  history, context assembly, and persisting the exchange to SQLite (`chat_history.db`, table
  `history`, keyed by `user_id`). History is the last 5 messages per user.
- **`hybrid_search`** is the core retrieval logic and the most likely place to need edits:
  - **Query enhancement** — appends domain keywords to the embed text based on tokens in the query
    (e.g. "H200" → "NVIDIA H200 HGX SXM5 ...") to improve recall.
  - **Brand detection** — maps query keywords to a brand, then filters Qdrant by matching the
    `filename` payload field against brand-specific substrings. `PRIMARY_BRANDS` filter the search;
    `COMPONENT_BRANDS` (AMD/Intel) are used for cross-brand scoring. A bare model-number pattern
    (`[A-Z]{1,2}[0-9]{2,3}`) defaults the brand to GIGABYTE.
  - **Fallback** — if a brand filter returns 0 results, it retries with no filter and clears the brand.
  - **`score_chunk`** — a large weighted heuristic over the chunk `text` and `filename`. Exact model
    numbers score highest (15000 in text). Re-rank, then enforce per-file diversity (≤5 chunks/file
    for exact model matches, ≤3 otherwise, ≤20 total) before returning.
- **`call_llm`** sends a Thai system prompt + assembled context to Ollama `/api/chat` at
  `temperature=0.1`. The system prompt forbids inventing specs and instructs use of the
  `MODELS AVAILABLE` header that lists candidate filenames.

WebSocket `/ws/flow` broadcasts pipeline stage events (`retrieval_start`, `llm_end`, ...) that the
dashboard visualizes. When changing the pipeline, keep `manager.broadcast({"stage": ...})` calls in
sync with what the front-ends expect. The feed carries every user's queries/answers, so it is
**admin-only**: connects require `?token=<Bigdata Website JWT>`, validated against
`BIGDATA_AUTH_URL` (`/api/auth/me`, role `admin`); otherwise closed with code 4401. `chat.html`
does not use the WebSocket — it gets answers from `POST /api/chat` and shows status locally.

### Ingestion

Documents live under `Database/<Brand>/` and are parsed by `scripts/parsers.py` (PDF via
pdfplumber, Excel/Word/PowerPoint/text). Parsers emit chunks joined by the literal
`\n\n---CHUNK---\n\n` delimiter; text uses `semantic_chunking` (700 chars, 150 overlap). Each chunk
is embedded with `mxbai-embed-large` (1024-dim, Cosine) and stored in the `km_knowledge` Qdrant
collection with payload `{text, filename, path, chunk_index}`. **Retrieval relies on `filename`
substrings for brand filtering**, so filenames carry brand/model meaning — preserve them on ingest.

Three ingestion variants exist:
- `ingest_optimized.py` — parallel (ProcessPool parse + ThreadPool embed), **drops and recreates**
  the collection. Use for a full rebuild.
- `ingest_slow.py` — sequential, checkpointed (`ingest_checkpoint.json`), rate-limited; resumable
  and safe for flaky Ollama. This is what the `/api/ingest` endpoint triggers.
- `ingest_all.py` — older sequential checkpointed variant.

## Commands

```bash
# Install deps (uses the project .venv)
pip install -r requirements.txt

# Start everything (Ollama+Vulkan, app.py:8001, Cloudflare tunnel, n8n) — paths are hardcoded
./start_all.sh
# Minimal start (Ollama + app.py only)
./start.sh
# Run the API directly (PORT defaults to 8001)
python3 app.py

# Qdrant — either via Docker (README) or the local binary in qdrant_bin/
docker-compose up -d

# Ingestion
python3 ingest_optimized.py      # full parallel rebuild (wipes collection)
python3 ingest_slow.py           # resumable, checkpointed

# Infra connectivity check (verifies Qdrant + Ollama reachable; exits non-zero on failure)
python3 tests/infra_test.py
```

There is no pytest/test runner. Files named `test_*.py` (root) and `scripts/test_*.py` /
`scripts/verify_*.py` are standalone scripts run with `python3 <file>` against the **live** running
stack (Qdrant + Ollama + ingested data must be up). They are not isolated unit tests.

## Configuration

Config is read from environment (`.env`, see `.env.example`). Key vars: `QDRANT_URL`, `OLLAMA_URL`,
`COLLECTION_NAME` (`km_knowledge`), `MODEL_GEN` (code default `llama3.2-vision:11b`, but `.env` on
this machine sets `qwen3.6:latest`), `MODEL_EMBED` (`mxbai-embed-large`), `LINE_TOKEN`, `DB_PATH`,
`PORT` (defaults to 8001). The generation model can also be switched at runtime via `POST /api/model`.
`ingest_optimized.py` hardcodes these values rather than reading env.

## Gotchas

- **Embedding model is load-bearing**: changing `MODEL_EMBED` changes the vector dimension and
  requires re-ingesting the whole collection (the 1024 size is hardcoded in ingestion).
- **Brand filtering is filename-based**, not metadata-tagged — a new brand or renamed files require
  adding cases in `hybrid_search`'s `perform_qdrant_search` and the brand keyword dicts at the top
  of `app.py`.
- `/api/restart` calls `sudo systemctl restart km-rag.service` — the app expects to run as a
  systemd service in production.
- The LINE webhook replies asynchronously via `asyncio.create_task` + LINE push API; it returns
  `200 ok` immediately, so errors surface in logs (`server_v2.log`), not the HTTP response.
- **Public LINE traffic is fronted by n8n, not app.py directly.** `start_all.sh` opens a Cloudflare
  quick tunnel to n8n (`localhost:5678`) and the LINE Console webhook is set to
  `<tunnel>/webhook/line-chat` (an n8n webhook), which then calls app.py. The tunnel URL is
  ephemeral and written to `.tunnel_url` on each start.
- **Two Ollama binaries exist**: `start_all.sh` runs `/usr/local/bin/ollama` with `OLLAMA_LLM_LIBRARY=vulkan`
  (GPU); `start.sh` runs the bundled `./local_ollama/bin/ollama` (CPU/no-Vulkan). Pick the one matching
  your GPU situation.
