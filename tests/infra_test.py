import requests

def test_connectivity():
    results = {}
    endpoints = {
        "Qdrant": "http://localhost:6333/healthz",
        "n8n": "http://localhost:5678/healthz",
        "Ollama": "http://localhost:11434/api/tags"
    }

    for name, url in endpoints.items():
        try:
            res = requests.get(url, timeout=5)
            results[name] = "OK" if res.status_code == 200 else f"FAIL ({res.status_code})"
        except Exception as e:
            results[name] = f"ERROR ({type(e).__name__})"

    for name, status in results.items():
        print(f"{name}: {status}")

    if all(s == "OK" for s in results.values()):
        print("\nOverall Status: SUCCESS")
        exit(0)
    else:
        print("\nOverall Status: FAILURE")
        exit(1)

if __name__ == "__main__":
    test_connectivity()
