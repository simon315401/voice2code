#!/bin/zsh
API_KEY="${V2C_API_KEY:-}"
MODEL="gemini-3.1-flash-lite-preview"
INPUT_TEXT="如果连接超时重试三次"
export SYSTEM_PROMPT="测试"

if [[ -z "$API_KEY" ]]; then
  echo "V2C_API_KEY 未设置" >&2
  exit 1
fi

TEMP_JSON=$(mktemp)
python3 -c "
import json, os, sys
payload = {
    'contents': [{'parts': [{'text': '测试'}]}],
    'generationConfig': { 'temperature': 0.1 }
}
with open('$TEMP_JSON', 'w', encoding='utf-8') as f:
    json.dump(payload, f)
"

RESPONSE=$(curl -s -w "%{http_code}" -X POST \
  "https://generativelanguage.googleapis.com/v1beta/models/${MODEL}:generateContent?key=${API_KEY}" \
  -H "Content-Type: application/json" \
  -d @"$TEMP_JSON")

HTTP_CODE="${RESPONSE:${#RESPONSE}-3}"
BODY="${RESPONSE:0:${#RESPONSE}-3}"

echo "HTTP_CODE: $HTTP_CODE"
echo "BODY: $BODY"
