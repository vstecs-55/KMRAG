import sys, time, threading, requests

BASE = "http://localhost:8001"
QUERIES = [
    ("u1", "สเปคของ GIGABYTE R283 มีอะไรบ้าง"),
    ("u2", "NVIDIA H200 มีหน่วยความจำเท่าไหร่"),
    ("u3", "Supermicro มีรุ่นไหนรองรับ GPU บ้าง"),
    ("u4", "AMD EPYC 9754 มีกี่ core"),
    ("u5", "Cloudera คืออะไร"),
]

def health_probe(stop, results):
    while not stop.is_set():
        t0 = time.time()
        try:
            requests.get(f"{BASE}/health", timeout=15)
            results.append(time.time() - t0)
        except Exception:
            results.append(15.0)
        stop.wait(1)

def chat(user, msg, out):
    t0 = time.time()
    try:
        r = requests.post(f"{BASE}/api/chat", json={"user_id": user, "message": msg}, timeout=300)
        out[user] = (time.time() - t0, len(r.json().get("answer", "")))
    except Exception as e:
        out[user] = (time.time() - t0, f"ERROR: {e}")

def run(n):
    stop, probes, out = threading.Event(), [], {}
    hp = threading.Thread(target=health_probe, args=(stop, probes)); hp.start()
    t0 = time.time()
    threads = [threading.Thread(target=chat, args=(u, q, out)) for u, q in QUERIES[:n]]
    for t in threads: t.start()
    for t in threads: t.join()
    total = time.time() - t0
    stop.set(); hp.join()
    print(f"\n=== {n} concurrent chat request(s), total wall time {total:.1f}s ===")
    for u, (dt, ans) in sorted(out.items()):
        print(f"  {u}: {dt:6.1f}s  answer={ans if isinstance(ans, str) else str(ans)+' chars'}")
    if probes:
        print(f"  /health during load: n={len(probes)} max={max(probes)*1000:.0f}ms avg={sum(probes)/len(probes)*1000:.0f}ms")

if __name__ == "__main__":
    run(int(sys.argv[1]) if len(sys.argv) > 1 else 5)
