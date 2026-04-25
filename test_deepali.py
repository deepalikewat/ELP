#!/usr/bin/env python3
import sys, time, json, requests

BASE = "https://deepali.ftp.sh"
MOCK = f"{BASE}/mock"
TIMEOUT = 10
MAX_LATENCY = 2.0
TOTAL_RECORDS = 25

passed = failed = 0

def ok(msg):
    global passed
    passed += 1
    print(f"  ✔ {msg}")

def bad(msg, detail=None):
    global failed
    failed += 1
    print(f"  ✘ {msg}")
    if detail:
        print(f"      → {detail}")

def get(url, label, status=200):
    start = time.perf_counter()
    try:
        r = requests.get(url, timeout=TIMEOUT)
        lat = time.perf_counter() - start
        if r.status_code != status:
            bad(f"{label} HTTP {r.status_code}")
            return None, lat
        try:
            data = r.json()
        except json.JSONDecodeError as e:
            bad(f"{label} bad JSON", e)
            return None, lat
        if lat > MAX_LATENCY:
            bad(f"{label} slow ({lat:.2f}s)")
        else:
            ok(f"{label} {lat:.2f}s")
        return data, lat
    except requests.RequestException as e:
        bad(f"{label} request failed", e)
        return None, time.perf_counter() - start

def post(url, label, status=200):
    start = time.perf_counter()
    try:
        r = requests.post(url, timeout=TIMEOUT)
        lat = time.perf_counter() - start
        if r.status_code != status:
            bad(f"{label} HTTP {r.status_code}")
            return None, lat
        try:
            data = r.json()
        except json.JSONDecodeError as e:
            bad(f"{label} bad JSON", e)
            return None, lat
        if lat > MAX_LATENCY:
            bad(f"{label} slow ({lat:.2f}s)")
        else:
            ok(f"{label} {lat:.2f}s")
        return data, lat
    except requests.RequestException as e:
        bad(f"{label} request failed", e)
        return None, time.perf_counter() - start

print("=" * 50)
print("Testing deepali.ftp.sh")
print("=" * 50)

# -- Mock Server --
print("\n[Mock Health]")
d, _ = get(f"{MOCK}/api/health", "health")
if d and d.get("status") == "healthy" and d.get("records") == TOTAL_RECORDS:
    ok("status & records correct")
else:
    bad("mock health mismatch", d)

print("\n[Mock List]")
d, _ = get(f"{MOCK}/api/customers?page=1&limit=5", "list")
if d and len(d.get("data", [])) == 5 and d.get("total") == TOTAL_RECORDS:
    ok("pagination & total correct")
else:
    bad("mock list mismatch", d)

print("\n[Mock Get]")
for cid in ("CUST-1001", "CUST-1025"):
    d, _ = get(f"{MOCK}/api/customers/{cid}", f"get {cid}")
    if d and d.get("data", {}).get("customer_id") == cid:
        ok(f"{cid} data ok")
    else:
        bad(f"{cid} mismatch", d)
d, _ = get(f"{MOCK}/api/customers/UNKNOWN", "404", status=404)
if d:
    ok("404 for unknown")
else:
    bad("404 check failed")

# -- Pipeline --
print("\n[Pipeline Health]")
d, _ = get(f"{BASE}/api/health", "health")
if d and d.get("status") == "healthy" and d.get("service") == "pipeline":
    ok("pipeline health ok")
else:
    bad("pipeline health mismatch", d)

print("\n[Pipeline Ingest]")
d, _ = post(f"{BASE}/api/ingest", "ingest")
if d and isinstance(d.get("records_processed"), int):
    ok(f"ingested {d['records_processed']} records")
else:
    bad("ingest failed", d)

print("\n[Pipeline List]")
d, _ = get(f"{BASE}/api/customers?page=1&limit=10", "list")
if d and d.get("page") == 1 and d.get("limit") == 10:
    ok("pagination ok")
else:
    bad("pipeline list mismatch", d)

print("\n[Pipeline Get]")
for cid in ("CUST-1001", "CUST-1025"):
    d, _ = get(f"{BASE}/api/customers/{cid}", f"get {cid}")
    if d and d.get("data", {}).get("customer_id") == cid:
        ok(f"{cid} data ok")
    else:
        bad(f"{cid} mismatch", d)

# -- Summary --
print("\n" + "=" * 50)
print(f"Results: {passed} passed, {failed} failed")
if failed:
    print("STATUS: FAIL")
    sys.exit(1)
else:
    print("STATUS: PASS")
    sys.exit(0)
