# Mac 原生“语音->指令” 极简提纯工具 (Voice2Code Refiner) 需求文档

> 当前实现对应的技术架构说明见：[Voice2Code_Architecture.md](/Users/yifeiliu/cursor/AIO/ai_command_optimization/docs/Voice2Code_Architecture.md)

## 1. 产品概述 (Product Overview)

### 1.1 核心痛点
开发者在编写 Issue、PR 描述或沟通开发任务时，常常使用 macOS 自带语音输入（双击 Control）。由于语音识别的局限和思考过程的口语化，生成的文本往往包含：
- **大量废话与语气词**（“那个、帮我把、大概就是”）。
- **同音专业词汇识别错误**（如“一步”替代“异步”，“截藕”替代“解耦”）。
- **逻辑散乱**，无法直接作为清晰的开发指令或 Git Commit。
第三方工具（如 Spokenly）虽能解决该问题，但存在**需要切换窗口、付费订阅、数据隐私泄露风险**以及不够“极客”等体验痛点。

### 1.2 产品定位
打造一个 **完全本地化、BYOK (Bring Your Own Key)、零切换成本** 的工作流方案。通过一次快捷键操作，实现 **“语音乱序输入 -> 捕获文本 -> LLM 提纯 -> 原地替换输出”**，为 macOS 用户带来极致流畅的极简工程体验。

---

## 2. 用户旅程 (User Journey)

1. **输入阶段 (Input)**：在任意输入框（VS Code / Cursor / 微信 / 备忘录），使用系统听写输入冗长、口语化的需求。
   > *示例：“那个...帮我把 user 接口改下，报错 500 时如果是连接超时就再重试三次吧”。*
2. **触发阶段 (Trigger)**：`Cmd + A` 选中文字，按下全局快捷键（推荐 `Option + Command + G`）。
3. **响应阶段 (Response)**：系统后台静默调用大模型（默认极速的 Gemini Flash），将文本提纯。
4. **输出阶段 (Output)**：选中的文字在 1-2 秒内**原地替换**为高品质的开发指令。
   > *示例输出：`- 修改 \`user\` 接口：若报错 500 且原因为数据库连接超时，执行 3 次重试。`*

---

## 3. 核心功能与技术实现 (Core Features & Implementation)

结合 GitHub 社区现有的效率工具生态（Raycast Extensions, Hammerspoon, 独立开源 App），本工具的演进和实现方案分为三个阶段进行定义：

### Phase 1: Quick Action + Voice2Code.app（当前交付形态）
当前正式交付形态是“系统原生 Quick Action + 最小控制壳 App”，不再是纯脚本式 Automator 方案。
- **文本捕获与回填**：继续利用 Automator 的“快速操作 (Quick Action)”服务，勾选“替换选定文本”。
- **运行控制壳**：`Voice2Code.app` 负责初始化配置、设置入口、Provider 选择、网络方式、API Key 配置与本地 CLI 调用壳。
- **处理中枢**：现有 Python Refiner Core 继续保留，承担两层转写、双语 contract、provider-neutral 调度与日志记录。
- **系统暗坑与健壮性优化**：
  - **编码陷阱防范**：破解 Automator 沙盒默认 ASCII 编码问题，强制指定 `PYTHONIOENCODING=utf-8` 和 `LANG=zh_CN.UTF-8`，解决输出中文导致的 `UnicodeEncodeError`。
  - **环境兼容设计**：显式注入 `/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin` 到 PATH，保证支持系统自带及 Homebrew 安装的 Python 运行环境。
  - **本地排错日志**：聚合日志以 JSONL 形式写入 `/tmp/Voice2Code_debug.jsonl`，单次请求明细以 JSON 写入 `/tmp/Voice2Code_logs/<request_id>.json`，方便快速定位异常原因与程序化分析。
  - **术语词典外置化**：词典文件落地到 `~/Library/Application Support/Voice2Code/terminology_glossary.tsv`，支持用户直接维护同音纠错映射（`误识别词<TAB>标准术语`）。
- **安装与配置体验**：
  - 安装器收简为两个阶段：先确认安装，再进入初始化配置。
  - 初始化配置窗口在同一窗口内完成：
    - Provider / 网络方式 / API Key 配置
    - 连通测试
    - 自动转写烟测
    - 完成态展示
  - 不再额外弹出第三个安装完成总结窗。
- **AI 引擎**：当前实现采用 provider-neutral AI service layer，已接入 `gemini / openai / doubao` 三类 Provider；正式发布主基线固定为 Gemini，默认模型使用 `gemini-3.1-flash-lite-preview`。系统按统一接入层调度 `intent` 与 `generation` 两阶段调用，同一请求始终由同一 provider 承载，不做跨 provider 混用。
- **预设 Prompt 规则**：
  1. 完整保留原句动作、对象、具体数值及条件，不改变业务语义。
  2. 自动纠正明显同音技术术语并规范英文术语大小写（如 MySQL、Redis、OSS）。
  3. 默认模式仅做低风险结构化整理：修正明显错别字、补标点、整理空格、理顺条件/因果/转折/先后顺序；不主动改写业务对象、约束强度和结论。
  4. 第一层只识别 `main_scene` 与 `structure_mode`，第二层按 resolved contract 做最小动态组装，不再使用长篇模板堆叠。
  5. 当前主场景固定为：`general / task / question / discussion_confirm / doc / feedback_meta`。
  6. 词典默认只注入“与当前输入匹配”的条目（`matched` 模式），可通过 `V2C_GLOSSARY_MODE=matched|full|off` 与 `V2C_GLOSSARY_MAX_ENTRIES` 控制注入策略与条目上限。
  7. 当前支持中英双语 contract：中文输入走 `zh-CN`，英文输入走 `en-US`，一次请求只注入单语 contract，输出语言默认跟随输入主语言。
  8. 本地代码不再承担语义重写、问句强修、场景重判或结构补齐，只负责确定性解析、contract resolve、JSON 校验与日志记录。

### Phase 2: 插件 / 扩展路线（后续预研方向）
插件化不是当前主线交付目标，仅作为后续预研方向保留。
- Cursor / Antigravity / 标准 VS Code 扩展路线，需要在不影响当前 Quick Action 主线的前提下单独验证。
- **交互更优雅**：Raycast 支持调用 `getSelectedText()` 与 `Clipboard.paste()`，并自带 Loading Toast 提示，用户知道 AI 正在处理。
- **配置更简单**：在 Raycast Store 直接安装，插件设置页提供可视化的 API Key 填入口及 System Prompt 自定义入口。

### Phase 3: 全本地大模型化 (终极形态)
基于 Tauri 或 SwiftUI 构建常驻状态栏应用，结合开源社区力量：
- **接入本地模型**：自动检测后台的 Ollama 或 LM Studio，利用本地 `llama3` 或 `qwen-code` 模型完成处理，彻底解决断网可用和绝密代码防泄漏问题。

---

## 4. API 与 数据流定义 (Data Standard)

- **接入形态**：当前实现采用 provider-neutral AI service layer。运行时可选择 `gemini / openai / doubao` 等 Provider，并为 `intent` 与 `generation` 分别指定模型；默认 Provider 为 Gemini。
- **请求方法**：`POST`
- **Provider 端点**：
  - Gemini：`https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent`
  - OpenAI：`https://api.openai.com/v1/chat/completions`
  - Doubao：`https://ark.cn-beijing.volces.com/api/v3/chat/completions`
- **安全与存储**：无任何中间数据库，所有请求均通过 HTTPS 直连对应 Provider。系统不再内嵌默认 API Key；当前版本以 `Voice2Code.app` 作为配置与运行控制壳，环境变量始终可作为显式覆盖与兜底入口；本地配置文件只保存非敏感状态，不保存明文密钥。系统级安全存储与更强等级的无感凭据持久化，已明确降级为后续增强专项，不作为本轮发布门禁。
- **重试与兜底机制**：
  - 若选中文本为空 `[ -z "$INPUT_TEXT" ]`，则记录日志并平滑退出 `exit 0`，不修改原内容。
  - 若 API 超时或抛出 HTTP 错误，使用 `curl --connect-timeout 2 --max-time 10 --retry 2 --retry-delay 1 --retry-all-errors` 自动重试；最终失败时记录 `[详细报错]` 至日志并输出 `[AI 请求失败...]` 防原文被空文本覆盖丢失。
  - 若 `curl` 进程级失败（退出码非 `0`），记录退出码与响应内容并回退原文。
  - 若意图分析或转写阶段返回非法 JSON / 缺少关键 contract 字段，则落入解析失败分支并输出显式错误前缀，不静默吞错。
  - 若当前未完成初始化配置（缺少当前 provider 的 API Key），系统直接返回 provider-aware 错误提示，而不是尝试以缺省凭据运行。
  - 若启用双语 contract，语言检测在第一层之前由代码侧完成，不额外增加 LLM 调用。

---

## 5. 项目验收标准 (Acceptance Criteria)
1. **可靠性**：连续 10 次选中极端乱码或多行代码段触发快捷键，不能破坏原有系统剪贴板。
2. **时效性**：从按下快捷键到文本替换完成，整体 P90 耗时需低于 `1.5` 秒。
3. **格式化**：输出的文本不能带有 "Here is your refined text:" 等模型聊天废话，纯净输出可直接作为代码提交信息（Commit Message）。
