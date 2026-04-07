import json
import os
import urllib.request
import urllib.error

API_KEY = os.environ.get("V2C_API_KEY", "").strip()
MODEL = "gemini-3.1-flash-lite-preview"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}"

if not API_KEY:
    raise SystemExit("V2C_API_KEY 未设置")

payload = {
    "contents": [{"parts": [{"text": "Hello, translate to Chinese: I am testing."}]}],
    "generationConfig": {"temperature": 0.1}
}

req = urllib.request.Request(URL, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")

try:
    with urllib.request.urlopen(req) as response:
        print("HTTP:", response.status)
        body = response.read().decode("utf-8")
        print("BODY:", body)
except urllib.error.HTTPError as e:
    print("HTTP ERROR:", e.code)
    print(e.read().decode("utf-8"))
except Exception as e:
    print("ERROR:", str(e))
