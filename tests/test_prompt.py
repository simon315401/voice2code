import json
import os
import urllib.request
import urllib.error
import ssl

ssl._create_default_https_context = ssl._create_unverified_context

API_KEY = os.environ.get("V2C_API_KEY", "").strip()
MODEL = "gemini-3.1-flash-lite-preview"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}"

if not API_KEY:
    raise SystemExit("V2C_API_KEY 未设置")

optimized_prompt_v2 = """你是一个为高效开发者服务的极简“开发任务提纯器”。你的任务是将日常随意的“口语化语音转录文本”浓缩为最精简、最直接的开发指令或代码注释。

【核心规则】
1. 术语自动转译：静默纠正语音识别错乱或同音错别字（例如：一步->异步、买搜扣->MySQL、截藕->解耦、雷迪斯->Redis、卡夫卡->Kafka）。遇到中英混杂时，需自动规范英文大小写（如 token, Bearer, mock, bug）。
2. 精准备份：保留用户提到的所有业务对象、具体数值、前置条件和报错码（如 401, 500），绝不删减任何业务细节。
3. 极速、极简格式：
   - 杜绝一切啰嗦语和解释，如“这是为你修改的指令”、“好的”等。
   - 不要输出顶层的 ```markdown 代码块。
   - 保持扁平化结构：不需要把需求层层拆解为“触发条件、流程、结果”，更不需要大张旗鼓地加上“优化方向”等标题。
   - 多数情况下请使用连贯精悍的单句，用简单的 `- ` 列表。
   - 技术变量、状态码、英文名称、接口名直接套用 `反引号` 提升极客感。

【示例对比】
用户输入："如果接口返回报错五百的话，咱们就是先判断一下是不是超时，超时的话就重试三次，但是如果不是超时就直接抛个错出来给前端"
错误输出（过于死板啰嗦）: 
- 触发条件：接口 500 报错。处理：判断是否超时，超时重试 3 次，非超时抛错前端。
正确输出（极简黑客风）: 
- 接口 `500` 时判断类型：若超时则重试 `3` 次，非超时直接向前端抛出异常。"""

test_cases = [
    "哎那个，查一下订单那边的代码，我看好像没加锁，并发的时候可能会超卖，得赶紧补个分布式锁上去",
    "这里先写个假的 mock 数据跑通流程，另外那个啥，token 传过去好像没带 bearer 导致一直报错四零一",
    "页面往下滑到底部有点卡，应该是那个文章列表里好几个图片没懒加载，全一下子干出来了"
]

def run_test(prompt_version, prompt_text):
    print(f"\\n============== {prompt_version} ==============")
    for i, t in enumerate(test_cases, 1):
        payload = {
            "contents": [{"parts": [{"text": f"{prompt_text}\\n\\n待处理文本：\\n{t}"}]}],
            "generationConfig": {"temperature": 0.1}
        }
        req = urllib.request.Request(URL, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req) as response:
                body = response.read().decode("utf-8")
                data = json.loads(body)
                if 'candidates' in data:
                    result = data['candidates'][0]['content']['parts'][0]['text'].strip()
                else:
                    result = str(data)
                print(f"\\n[口语输入 {i}]: {t}")
                print(f"[极简提纯 {i}]:\\n{result}")
        except Exception as e:
            print(f"[错误 {i}]: {str(e)}")

print("开始测试提示词 V2...")
run_test("最终极简版 Prompt V2", optimized_prompt_v2)
