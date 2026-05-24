# KM RAG: Infrastructure Setup Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish a fully functional local environment with Qdrant installed and connectivity verified between n8n, Ollama, and Qdrant.

**Architecture:** 
- Qdrant will be deployed as a Docker container for easy management and persistence.
- Connectivity will be verified using simple API calls (curl/n8n) to ensure the "plumbing" is correct before building complex workflows.

**Tech Stack:** Docker, Qdrant, n8n, Ollama.

---

### Task 1: Qdrant Deployment

**Files:**
- Create: `docker-compose.yml`

- [ ] **Step 1: Create docker-compose.yml for Qdrant**
```yaml
version: '3.8'
services:
  qdrant:
    image: qdrant/qdrant:latest
    container_name: qdrant
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - ./qdrant_storage:/qdrant/storage
    restart: always
```

- [ ] **Step 2: Launch Qdrant**
Run: `docker compose up -d`
Expected: Container `qdrant` starts successfully.

- [ ] **Step 3: Verify Qdrant Health**
Run: `curl -I http://localhost:6333/healthz`
Expected: `HTTP/1.1 200 OK`

- [ ] **Step 4: Commit**
```bash
git add docker-compose.yml
git commit -m "infra: deploy qdrant via docker-compose"
```

### Task 2: Connectivity Validation

**Files:**
- Create: `tests/infra_test.py`

- [ ] **Step 1: Write connectivity test script**
```python
import requests

def test_connectivity():
    # Test Qdrant
    try:
        q_res = requests.get("http://localhost:6333/healthz")
        print(f"Qdrant: {'OK' if q_res.status_code == 200 else 'FAIL'}")
    except Exception as e:
        print(f"Qdrant: ERROR {e}")
    
    # Test n8n
    try:
        n_res = requests.get("http://localhost:5678/healthz")
        print(f"n8n: {'OK' if n_res.status_code == 200 else 'FAIL'}")
    except Exception as e:
        print(f"n8n: ERROR {e}")
    
    # Test Ollama
    try:
        o_res = requests.get("http://localhost:11434/api/tags")
        print(f"Ollama: {'OK' if o_res.status_code == 200 else 'FAIL'}")
    except Exception as e:
        print(f"Ollama: ERROR {e}")

if __name__ == "__main__":
    test_connectivity()
```

- [ ] **Step 2: Run test to verify all systems are up**
Run: `python3 tests/infra_test.py`
Expected: All three services report 'OK'.

- [ ] **Step 3: Commit**
```bash
git add tests/infra_test.py
git commit -m "test: add infrastructure connectivity check"
```
