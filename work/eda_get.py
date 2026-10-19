#!/usr/bin/env python3
import sys, json, urllib.request

BRIDGE = "http://localhost:49620"
JS_FILE = sys.argv[1]
OUT = sys.argv[2] if len(sys.argv) > 2 else None

with open(JS_FILE, "r", encoding="utf-8") as f:
    code = f.read()

payload = {"code": code}
req = urllib.request.Request(
    BRIDGE + "/execute",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
)
resp = urllib.request.urlopen(req, timeout=180)
data = json.loads(resp.read().decode("utf-8"))

if not data.get("success"):
    print("FAILED:", data.get("error"))
    sys.exit(1)

result = data.get("result")
if OUT:
    if isinstance(result, str):
        with open(OUT, "w", encoding="utf-8", newline="") as f:
            f.write(result)
        print("saved raw string to", OUT, "len", len(result))
    else:
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print("saved json to", OUT)
else:
    if isinstance(result, str):
        print(result[:2000])
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))