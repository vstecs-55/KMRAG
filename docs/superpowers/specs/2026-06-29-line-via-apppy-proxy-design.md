---
name: line-via-apppy-proxy
description: Route LINE answers through app.py's tuned RAG pipeline, using n8n as a thin forwarding proxy
metadata:
  type: project-spec
  date: 2026-06-29
---

# Design: LINE → app.py (n8n as thin proxy)

## Problem

LINE answers are lower quality than the web chat. Root cause: the active n8n
workflow (`KM RAG LINE Chatbot`, id `foDJWql33xyHeOCh`) reimplements a *primitive*
RAG (embed → Qdrant top-5 → short English prompt → `qwen3.6 /api/generate` → push)
and ignores all of app.py's hand-tuned logic. Symptoms:

- Greeting "สวัสดี" has no short-circuit → retrieves random chunks and rambles
  (e.g. dumps Solomon AI / INFINITIX content).
- No brand detection, query enhancement, `score_chunk` reranking, Thai
  anti-hallucination system prompt, or per-file diversity. Only 5 chunks.

app.py already has ALL of this in `process_query` → `hybrid_search` → `call_llm`,
and its `/line/webhook` route returns `200` immediately then pushes the answer to
LINE asynchronously.

## Decision

Make LINE use app.py's pipeline. Keep n8n in the path as a **thin proxy** (least
disruptive — no tunnel or LINE Console change; the working
`line.bigdata-ai.online/webhook/line-chat` route stays).

## New data flow

```
LINE → Cloudflare (line.bigdata-ai.online) → n8n /webhook/line-chat
     → [n8n: forward raw body → http://localhost:8001/line/webhook, then respond 200]
     → app.py /line/webhook (returns 200 instantly)
          → async: process_query (greeting short-circuit + hybrid_search + call_llm)
          → push answer to LINE via LINE push API (LINE_TOKEN from .env, 172-char)
```

## n8n workflow (replace nodes in id `foDJWql33xyHeOCh`)

Three nodes only:
1. **Line Webhook** — path `line-chat`, POST, `responseMode: responseNode` (unchanged).
2. **Forward to app.py** — HTTP Request, POST `http://localhost:8001/line/webhook`,
   body = raw `={{ JSON.stringify($json.body) }}`, contentType `application/json`.
   n8n runs host-network so `localhost:8001` reaches app.py. app.py returns `200`
   instantly, so this node returns fast (no LLM wait).
3. **Respond to Webhook** — return `200`.

Removed: Extract Data, Get Embedding, Search Qdrant, Build Context, Generate Answer,
Push to LINE (app.py owns all of this now).

## app.py

No code change. `/line/webhook` already does greeting short-circuit, the full tuned
pipeline, and the async LINE push.

## Why this fixes it

- Greeting → app.py short-circuit → clean reply, no rambling.
- All queries get brand detection / query enhancement / rerank / Thai
  anti-hallucination prompt / up to 20 chunks (identical to web).
- LINE webhook timeout removed: n8n responds 200 immediately (app.py is async),
  so LINE never waits on the LLM.
- One RAG pipeline to maintain instead of two.

## Apply mechanism

1. Back up the current workflow: `docker exec n8n n8n export:workflow
   --id=foDJWql33xyHeOCh --output=/tmp/line-backup.json`, copy out.
2. Build the new workflow JSON (same `id`), copy into the container, import with
   `n8n import:workflow`, restart n8n so the webhook re-registers.

## Rollback

Re-import the backed-up workflow JSON (same id) and restart n8n.

## Testing

From a real LINE account send "สวัสดี" and "H200 คืออะไร". Expect:
- Greeting → short clean reply (matches web).
- H200 → tuned technical answer (matches web).
- `journalctl` for app.py shows `Processing: ...` then LINE push `200`.
- n8n execution finishes `success` quickly (no LLM wait inside n8n).
