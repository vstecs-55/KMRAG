# Retrieval Accuracy and Performance Implementation Plan

> **For Gemini:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Resolve GIGABYTE retrieval failures, improve greeting robustness, and decrease response latency.

**Architecture:** 
1. Categorize brands into Primary (exclusive filtering) and Component (broad filtering) to prevent Xeon/EPYC queries from being locked to brand-specific files.
2. Implement regex-based model number detection (GIGABYTE R/H/G series).
3. Add a "Search Fallback" mechanism: if a query with an inherited brand filter returns zero results, retry with a broad search.
4. Switch the default generation model to `llama3.2-vision:11b` for speed.

**Tech Stack:** Python, FastAPI, Qdrant, Ollama, re (regex).

---

### Task 1: Performance and Model Update

**Files:**
- Modify: `app.py`

**Step 1: Write the failing test (Manual verification of model speed)**
*No automated test needed for speed, but will verify model name.*

**Step 2: Update default model and greeting keywords**

```python
# Change MODEL_GEN in app.py
MODEL_GEN = "llama3.2-vision:11b"

# Update greetings list in process_query
greetings = ["สวัสดี", "hello", "hi", "หวัดดี", "สวส", "กูรู", "guru", "expert", "ทักทาย", "ดีจ้า", "ดีครับ", "สอบถาม", "ถาม", "ขอทราบ"]
```

**Step 3: Run app and verify /api/status returns correct model**

Run: `curl http://localhost:8000/api/status | jq .model`
Expected: `"llama3.2-vision:11b"`

---

### Task 2: Advanced Brand Categorization and Regex

**Files:**
- Modify: `app.py`

**Step 1: Implement PRIMARY and COMPONENT brand separation**

```python
PRIMARY_BRANDS = {
    "GIGABYTE": ["GIGABYTE", "GIGABYUT", "GIGA", "จิกะไบต์"],
    "SUPERMICRO": ["SUPERMICRO", "SUPER", "ซุปเปอร์ไมโคร"],
    "SAS": ["SAS", "แซส", "เอสเอเอส", "สาส"],
    "SOLOMON": ["SOLOMON", "โซโลมอน"],
    "CLOUDERA": ["CLOUDERA", "คลาวเดอร่า"],
    "INFINITIX": ["INFINITIX", "อินฟินิทิกซ์"],
    "NVIDIA": ["NVIDIA", "เอนวีเดีย"]
}

COMPONENT_BRANDS = {
    "AMD": ["AMD", "EPYC", "RYZEN", "THREADRIPPER", "เอเอ็มดี"],
    "INTEL": ["INTEL", "XEON", "อินเทล"]
}
```

**Step 2: Update regex for GIGABYTE model recognition**

```python
# In hybrid_search
if not matched_primary_brand:
    # Pattern for R283, R163, MZ31, etc.
    if re.search(r'\b[A-Z]{1,2}[0-9]{2,3}(-[A-Z0-9]+)?\b', query_upper):
        matched_primary_brand = "GIGABYTE"
```

**Step 3: Commit**

```bash
git add app.py
git commit -m "feat: improve brand detection and categorization"
```

---

### Task 3: Search Fallback and Robust Retrieval

**Files:**
- Modify: `app.py`

**Step 1: Implement fallback logic in hybrid_search or process_query**

```python
# In hybrid_search, if results are 0 and brand was inherited/forced, try without filter.
# Or handle it in process_query. Let's do it in hybrid_search.
```

**Step 2: Update Scoring with better weights**

```python
if model_match: score += 5000
if matched_primary_brand and matched_primary_brand in fname: score += 10000
```

**Step 3: Test with "Dual CPU Intel Xeon" (Previously failing)**

Run: `python3 -c "import asyncio; from app import process_query; print(asyncio.run(process_query('TEST_USER', 'Dual CPU Intel Xeon')))"`
Expected: Non-empty response referring to server specs.

**Step 4: Commit**

```bash
git add app.py
git commit -m "fix: implement search fallback and enhance hardware scoring"
```

---

### Task 4: Final Cleanup and Logging

**Files:**
- Modify: `app.py`
- Modify: `dashboard.html` (Optional styling fix)

**Step 1: Ensure substring matching for greetings**

```python
# In process_query
query_clean = query_text.lower().replace(" ", "").strip()
is_greeting = any(g in query_clean for g in greetings)
```

**Step 2: Verify all 33 questions from Round 8 pass internally**

**Step 3: Commit and Push**

```bash
git push origin master
```
