# Voice2Code 质量基线与模型对比

## 1. 文档目标

本文件用于沉淀 Voice2Code 当前正式使用的质量验证方式与基线结果，避免后续收尾阶段继续依赖临时命令、临时截图或零散口头结论。

质量验证分为三类：

1. `Gemini` 主基线
2. `Gemini vs OpenAI` 抽样对比
3. `Gemini vs Doubao` 抽样对比

当前发布主基线固定为 `Gemini`。

---

## 2. 评测维度

所有 LLM 质量评分统一采用以下维度：

- `scene_fit`
- `semantic_fidelity`
- `ai_collab_usability`
- `structured_natural_expression`
- `scope_control`
- `overall`

说明：

- `scene_fit`：是否符合该场景应有的表达目标
- `semantic_fidelity`：是否忠实保留原始输入语义
- `ai_collab_usability`：是否更适合继续交给 AI 理解、确认、执行或产出
- `structured_natural_expression`：是否结构清晰且表达自然，不僵硬、不压平
- `scope_control`：是否没有无根据扩写、没有越权新增结论或任务
- `overall`：综合分

---

## 3. 抽样集

质量评测默认使用：
[voice2code_quality_samples.json](/Users/yifeiliu/cursor/AIO/ai_command_optimization/docs/testdata/voice2code_quality_samples.json)

包含：

- 中文 6 场景
- 英文 6 场景

来源：
[voice2code_regression_samples.json](/Users/yifeiliu/cursor/AIO/ai_command_optimization/docs/testdata/voice2code_regression_samples.json)

---

## 4. 运行方式

质量评测脚本：
[run_voice2code_quality_eval.py](/Users/yifeiliu/cursor/AIO/ai_command_optimization/tests/run_voice2code_quality_eval.py)

示例：

```bash
python3 tests/run_voice2code_quality_eval.py \
  --providers gemini,openai \
  --languages zh,en \
  --output /tmp/v2c_quality_eval.json
```

说明：

- 评审模型固定使用 `Gemini`
- 被评模型由 `--providers` 指定
- `--languages` 可选择 `zh`、`en` 或 `zh,en`
- 输出为标准 JSON 报告，可用于后续沉淀与比对

---

## 5. 当前结论维护规则

- `Gemini` 必须保持为正式发布主基线
- `OpenAI` 与 `Doubao` 至少需要：
  - 最小连通烟测
  - 1 条中文端到端样本
  - 1 条英文端到端样本
  - 6 场景抽样评分
- 如果某 provider 只做到“能跑通”，但质量明显不稳，则保留接入，不作为主推荐 provider

---

## 6. 结果填写区

### 6.1 Gemini 主基线

- 状态：已完成（2026-04-02）
- 资产：
  - [voice2code_quality_eval_phaseA_2026-04-02.json](/Users/yifeiliu/cursor/AIO/ai_command_optimization/docs/testdata/voice2code_quality_eval_phaseA_2026-04-02.json)
- 结果：
  - `scene_fit = 10.0`
  - `semantic_fidelity = 10.0`
  - `ai_collab_usability = 9.83`
  - `structured_natural_expression = 9.29`
  - `scope_control = 9.96`
  - `overall = 9.81`
- 结论：
  - 当前中文 / 英文双语 contract 已形成稳定主基线
  - `structured_natural_expression` 是最值得继续优化的维度，但未出现系统性失真

### 6.2 Gemini vs OpenAI

- 状态：已完成最小对比（2026-04-02）
- 资产：
  - [voice2code_quality_eval_phaseA_2026-04-02.json](/Users/yifeiliu/cursor/AIO/ai_command_optimization/docs/testdata/voice2code_quality_eval_phaseA_2026-04-02.json)
- OpenAI 结果：
  - `scene_fit = 10.0`
  - `semantic_fidelity = 9.96`
  - `ai_collab_usability = 9.83`
  - `structured_natural_expression = 9.67`
  - `scope_control = 9.83`
  - `overall = 9.83`
- 结论：
  - OpenAI 已完成 provider-neutral 接入后的真实最小质量验证
  - 当前已具备“可比较、可配置、可最小发布验证”的条件
  - 正式发布主基线仍固定为 `Gemini`

### 6.3 Gemini vs Doubao

- 状态：待补真实验证
- 结论：
  - Doubao 接入代码已完成
  - 当前缺少可用 key，尚未形成真实连通、端到端样本与 6 场景抽样评分结论
