# Voice2Code Refiner 实施 Checklist

## 1. 文档目标

本清单用于记录 V2 架构收敛的实施结果、验收门槛和后续工作边界。

它不再作为旧架构的逐项迁移记录，而是作为当前正式实现的验收清单。

## 2. 本轮实施范围

本轮采用的是一次性架构收敛，而不是对旧方案继续修补。

收敛目标：

1. 保留“两层架构”
2. 将第一层改成适配 `gemini-3.1-flash-lite-preview` 的最小语义路由器
3. 让第二层消费稳定的 resolved contract
4. 删除 `output_format` 主链路
5. 杜绝本地语义修补和输出形态干预

## 3. 已完成项

### 3.1 第一层 V2

- [x] 第一层只输出：
  - `main_scene`
  - `structure_mode`
- [x] 第一层删除：
  - `rewrite_strategy`
  - `confidence`
  - `output_format`
- [x] 删除旧的一层长文案组件：
  - `scene_routes`
  - `rewrite_routes`
  - `structure_routes`
  - 长版 `decision_table`
  - 长版 `structure_decision_table`
- [x] 第一层 prompt 改成最小标签契约

### 3.2 Resolved Contract

- [x] 代码侧引入 resolved contract 解析
- [x] 固定规则：
  - `scene_id = main_scene`
  - `structure_id = structure_mode`
  - `rewrite_id = forced_rewrite_strategy or "clarify"`
- [x] 第二层不再依赖第一层判断 `rewrite_strategy`

### 3.3 第二层契约体系

- [x] 第二层保留动态组装
- [x] 第二层组装输入切换为 resolved contract
- [x] 第二层契约收敛为：
  - `global_contract`
  - `scene_policies`
  - `rewrite_policies`
  - `structure_policies`
- [x] 不再使用旧的长文案 `scene_templates / rewrite_constraints / structure_constraints`

### 3.4 本地层职责收口

- [x] `output_format` 已从主链路删除
- [x] 不再有 `format_policies`
- [x] `output_formatter` 当前为纯透传兼容层
- [x] 不再用本地代码修正问句、结构或语义

### 3.5 日志与测试

- [x] 日志新增：
  - `forced_rewrite_strategy`
  - `resolved_rewrite_id`
  - `selected_scene_id`
  - `selected_rewrite_id`
  - `selected_structure_id`
  - `generation_prompt_char_count`
- [x] 回归脚本改为校验新契约
- [x] token smoke 改为服务新架构基线

## 4. 当前正式验收结果

截至 `2026-04-02`，当前工作区验收结果如下。

### 4.1 固定回归

- [x] `35 / 35` 通过

### 4.2 Token / Latency 基线

- [x] 已重写 V2 baseline：
  - `intent_prompt_token_avg = 369.5`
  - `generation_prompt_token_avg = 524.2`
  - `total_latency_ms_avg = 3755.5`

结论：

- 第一层 token 已显著低于旧架构
- 第二层 token 上升已纳入 V2 新基线，不再用旧门槛判断

### 4.3 中文 / 英文质量基线

- [x] 已完成 12 条双语抽样评分

评分维度：

- `scene_fit`
- `semantic_fidelity`
- `ai_collab_usability`
- `structured_natural_expression`
- `scope_control`
- `overall`

`Gemini` 当前主基线均分：

- `scene_fit = 10.0`
- `semantic_fidelity = 10.0`
- `ai_collab_usability = 9.83`
- `structured_natural_expression = 9.29`
- `scope_control = 9.96`
- `overall = 9.81`

补充说明：

- 评测覆盖中文 6 场景与英文 6 场景
- 英文 contract 已通过真实模型输出验证，不再只停留在结构接通
- `structured_natural_expression` 仍是当前最值得继续优化的维度，但未出现系统性恶化

### 4.4 Provider-Neutral 最小质量验证

- [x] `Gemini` 主基线已完成
- [x] `OpenAI` 最小连通烟测已完成
- [x] `OpenAI` 中文 / 英文端到端样本已完成
- [x] `Gemini vs OpenAI` 12 条双语抽样评分已完成
- [ ] `Doubao` 真实验证待补（当前缺少可用 key）

`OpenAI` 当前抽样均分：

- `scene_fit = 10.0`
- `semantic_fidelity = 9.96`
- `ai_collab_usability = 9.83`
- `structured_natural_expression = 9.67`
- `scope_control = 9.83`
- `overall = 9.83`

当前判断：

- `Gemini` 仍然是正式发布主基线
- `OpenAI` 已达到“可接入、可验证、可最小对比”的阶段
- `Doubao` 代码接入已完成，但未拿到真实质量结论

## 5. 本轮发布决策

本轮在通过以下门槛后，进入正式集成：

1. 固定回归通过
2. 6 场景多维度 LLM 评分通过
3. token smoke 建立新基线

通过后执行：

- [x] 更新架构文档
- [x] 更新实施清单
- [x] 更新发布版本与 release notes
- [x] 重建安装包

## 5.1 安装器 UI 重构验收

安装包交互侧已切换到原生 AppKit 小窗口，并在收尾阶段进一步收简为“两阶段安装 + 同窗完成态”：

- [x] `install.command` 不再依赖 AppleScript 表单式交互
- [x] `配置代理.command` 与安装器共用同一个窗口 helper
- [x] `Voice2Code.app` 作为最小设置与运行控制壳保留
- [x] 本地版本状态可在窗口中识别：
  - 首次安装
  - 升级安装
  - 同版本覆盖
  - 降级覆盖
- [x] 安装流程已拆成两阶段：
  - 第 1 阶段为安装确认
  - 第 2 阶段为初始化配置窗口
- [x] Gemini 连通性可在网络配置窗口内测试
- [x] 网络配置窗口支持动态显隐：
  - 直连时隐藏代理输入区
  - 代理时展开代理输入区
- [x] 初始化配置窗口内部完成三态切换：
  - `editing`
  - `running_smoke`
  - `completed`
- [x] 保存后自动转写烟测在同一窗口内执行
- [x] 成功路径不再额外弹第三个独立完成总结窗
- [x] 最小自动化烟测通过：
  - 网络通讯可走通
  - Gemini 调用可返回成功结果

补充说明：

- 安装器侧本轮不再以 6 场景多维度评分作为发布门禁
- 当前门禁已收敛为：
  - helper / app shell 可编译
  - shell 脚本语法通过
  - 初始化配置窗口内的最小 Gemini 烟测可走通
- `SecItem* + 签名 / entitlement` 已降级为后续增强专项，不再阻断本轮交付

## 6. 不再采用的做法

以下方案已在当前架构中明确弃用：

- [x] 第一层输出 `output_format`
- [x] 第一层输出 `rewrite_strategy`
- [x] 第一层输出 `confidence`
- [x] 本地 `commit / issue / todo` 输出形态治理主链路
- [x] 样本特化本地修补
- [x] 用 formatter 影响模型语义结果
- [x] 用越来越长的一层提示词说明书换稳定性

## 7. 后续工作边界

后续优化只应发生在以下位置：

1. 第一层最小路由标签定义
2. 第二层短契约文案
3. glossary 注入策略
4. 回归样本与质量评测资产

后续不应回到以下方向：

- 重新恢复 `output_format`
- 重新引入语义性本地 guard
- 通过本地规则修单个样本
- 在第一层重新堆长篇 decision table

## 8. 相关文件

- 配置：
  [voice2code_refiner_config.json](/Users/yifeiliu/cursor/AIO/ai_command_optimization/config/voice2code_refiner_config.json)
- 协议对象：
  [protocols.py](/Users/yifeiliu/cursor/AIO/ai_command_optimization/scripts/refiner/protocols.py)
- 第一层：
  [intent_analyzer.py](/Users/yifeiliu/cursor/AIO/ai_command_optimization/scripts/refiner/intent_analyzer.py)
- 第二层：
  [prompt_selection.py](/Users/yifeiliu/cursor/AIO/ai_command_optimization/scripts/refiner/prompt_selection.py)
  [prompt_assembler.py](/Users/yifeiliu/cursor/AIO/ai_command_optimization/scripts/refiner/prompt_assembler.py)
- 执行编排：
  [runner.py](/Users/yifeiliu/cursor/AIO/ai_command_optimization/scripts/refiner/runner.py)
- 测试资产：
  [voice2code_regression_samples.json](/Users/yifeiliu/cursor/AIO/ai_command_optimization/docs/testdata/voice2code_regression_samples.json)
  [voice2code_token_budget_baseline.json](/Users/yifeiliu/cursor/AIO/ai_command_optimization/docs/testdata/voice2code_token_budget_baseline.json)
