#!/usr/bin/env python3
import sys, json, urllib.request

BRIDGE = "http://localhost:49620"
JS_FILE = sys.argv[1] if len(sys.argv) > 1 else None
WINDOW = sys.argv[2] if len(sys.argv) > 2 else None

if JS_FILE:
    with open(JS_FILE, "r", encoding="utf-8") as f:
        code = f.read()
else:
    code = sys.stdin.read()

payload = {"code": code}
if WINDOW:
    payload["windowId"] = WINDOW

req = urllib.request.Request(
    BRIDGE + "/execute",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
)
try:
    resp = urllib.request.urlopen(req, timeout=120)
    data = json.loads(resp.read().decode("utf-8"))
    print(json.dumps(data, ensure_ascii=False, indent=2))
except urllib.error.HTTPError as e:
    print("HTTPError", e.code, e.read().decode("utf-8", "replace"))
except Exception as e:
    print("ERR", repr(e))
