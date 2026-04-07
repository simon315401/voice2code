#!/bin/zsh

export PYTHONIOENCODING=utf-8
export LANG=zh_CN.UTF-8

API_KEY="${V2C_API_KEY:-}"
MODEL="gemini-3.1-flash-lite-preview"

if [[ -z "$API_KEY" ]]; then
  echo "V2C_API_KEY 未设置" >&2
  exit 1
fi

run_gemini() {
    local text="$1"
    local system_prompt="$2"
    
    local TEMP_JSON=$(mktemp)
    
    python3 -c "
import json
payload = {
    'contents': [{'parts': [{'text': '''$system_prompt\n\n待处理文本：\n$text'''}]}],
    'generationConfig': { 'temperature': 0.1 }
}
with open('$TEMP_JSON', 'w', encoding='utf-8') as f:
    json.dump(payload, f)
"
    
    local RESP=$(curl -s "https://generativelanguage.googleapis.com/v1beta/models/${MODEL}:generateContent?key=${API_KEY}" \
      -H "Content-Type: application/json" \
      -d @"$TEMP_JSON")
      
    rm -f "$TEMP_JSON"
    
    echo "$RESP" | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(data['candidates'][0]['content']['parts'][0]['text'].strip())
"
}

PROMPT_CURRENT="开发指令提纯器：将口语化的乱序语音稿转为专业、直接的开发任务指令。
规则：
1. 原意保留：绝对保留原句包含的所有动作、对象、数值、条件及原因。
2. 术语纠错：自动修正同音技术词（如：一步->异步，截藕->解耦），规范化代码及英文格式。
3. 结构化输出：单任务输出长条目的 Markdown，多任务出 Markdown 列表。
4. 输出限制：严禁开场白、严禁结语解释、严禁废话，必须只输出最终可用的结果。"

PROMPT_NEW="你是一个极简专业的开发任务提纯器。请将口语化、乱序的语音输入转化为专业直接的开发指令。

【核心规则】
1. 术语转译：静默纠正语音同音错别字（如：一步->异步、买搜扣->MySQL、截藕->解耦、雷迪斯->Redis）。
2. 精准备份：绝对保留用户提到的所有数值、条件判断、操作对象或前置逻辑，不得擅自删减。
3. 极简格式：
   - 绝对不准输出说明性质的话语，如“好的”、“这是提纯后的指令”。
   - 绝对不要在最外层套用 \`\`\`markdown 代码块盒子，必须直接只输出纯 Markdown 内容。
   - 单一需求直接输出一条如 \`- 优化部分\`，多需求采用 \`- 模块1\\n- 模块2\` 的并列清单。
   - 所有专业名词（URL、接口返回值、英文方法）请主动套用反引号以符合技术习惯。"

TEST1="恩那个，按钮颜色不太对，把它设为红色的吧，字弄成白色的稍微加大一点"
TEST2="如果接口返回报错五百的话，咱们就是先判断一下是不是超时，超时的话就重试三次，但是如果不是超时就直接抛个错出来给前端"
TEST3="帮我加一个一步的方法，然后用微服务把它解耦，主要是雷迪斯缓存要设置一个小时过期"

echo "\n============== 【测试】当前 Prompt =============="
echo "[输入 1]: $TEST1"
echo "[输出 1]:"
run_gemini "$TEST1" "$PROMPT_CURRENT"

echo "\n[输入 2]: $TEST2"
echo "[输出 2]:"
run_gemini "$TEST2" "$PROMPT_CURRENT"

echo "\n[输入 3]: $TEST3"
echo "[输出 3]:"
run_gemini "$TEST3" "$PROMPT_CURRENT"


echo "\n============== 【测试】优化 Prompt =============="
echo "[输入 1]: $TEST1"
echo "[输出 1]:"
run_gemini "$TEST1" "$PROMPT_NEW"

echo "\n[输入 2]: $TEST2"
echo "[输出 2]:"
run_gemini "$TEST2" "$PROMPT_NEW"

echo "\n[输入 3]: $TEST3"
echo "[输出 3]:"
run_gemini "$TEST3" "$PROMPT_NEW"
