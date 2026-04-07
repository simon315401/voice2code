# Voice2Code 项目收尾 Checklist

## 1. 文档目标

本清单用于在发布、开源或正式交付前，系统性收口 Voice2Code 当前工程，确保：

- 安装链路稳定可用
- 主转写链路质量稳定
- 配置与安全策略一致
- 文档与实际实现一致
- 发布产物可重复生成、可验证、可追溯

本清单关注的是“可交付收口”，不是继续扩张功能。

---

## 2. 收尾原则

- 不再以扩能力为优先级，优先收口已有能力
- 不以“能跑”为验收标准，而以“稳定、可解释、可验证”为验收标准
- 不允许文档、实现、安装包三者不一致
- 不依赖人工记忆隐式规则，关键行为必须有明确校验

---

## 3. 安装与交付稳定性

### 3.1 安装器兼容性

- [ ] 图形安装器在目标 macOS 版本范围内可启动
- [x] 图形安装器失败时，能自动进入终端兼容模式
- [x] helper 二进制构建目标版本、架构、依赖已固定
- [x] 安装包目录名和 zip 文件名带版本号，避免缓存混淆
- [x] 安装器错误会写入明确日志，而不是只显示泛化失败提示

### 3.2 Quick Action 注册

- [x] 安装后校验 `~/Library/Services/AI提纯指令.workflow` 是否存在
- [x] 校验 `Contents/Info.plist` 是否存在
- [x] 校验 `Contents/document.wflow` 是否存在
- [x] 安装后执行完整服务刷新流程
- [x] 安装结果区分：
  - [x] 程序已安装
  - [x] Quick Action 已注册
  - [x] 转写烟测结果

### 3.3 初始化配置

- [x] 安装完成后自动进入初始化配置
- [x] 初始化配置必须包含：
  - [x] Provider 选择
  - [x] API Key 输入
  - [x] 网络方式配置
  - [x] 连通测试
- [x] 连通测试未通过时，不允许保存
- [x] 初始化配置未完成时，主链路给出明确阻断提示
- [x] 初始化配置窗口内完成自动烟测与完成态展示
- [x] 安装成功路径不再额外弹第三个独立完成总结窗

### 3.4 配置与凭据

- [x] API Key 不内嵌在源码或安装包中
- [x] API Key 允许通过以下方式读取：
  - [x] 环境变量
  - [x] 当前环境支持时的 App 内持久化
- [x] 配置文件不保存明文 API Key
- [x] 缺失 API Key 时，错误提示为 provider-aware
- [x] 后续配置入口与首次配置入口行为一致

### 3.5 安装链路验证

- [ ] 首次安装验证通过
- [ ] 覆盖安装验证通过
- [ ] 升级安装验证通过
- [ ] 图形安装失败后终端 fallback 验证通过
- [ ] Quick Action 注册验证通过
- [ ] 安装后首次转写验证通过

---

## 4. 核心主链路收口

### 4.1 两层架构

- [x] 第一层只负责：
  - [x] `main_scene`
  - [x] `structure_mode`
- [x] 第二层只负责：
  - [x] 按 resolved contract 生成
- [x] 不重新引入第一层长说明书式分类 prompt
- [x] 不重新引入本地语义修补链

### 4.2 动态 Contract

- [x] 第二层保持“单场景命中 + 最小组装”
- [x] 不将多个 scene 的完整指令同时注入一次请求
- [x] 中文/英文 contract 同构
- [x] `general / question / discussion_confirm / doc` 边界稳定

### 4.3 双语 Prompt

- [x] 中文输入走 `zh-CN` contract
- [x] 英文输入走 `en-US` contract
- [x] 不进行双语同时注入
- [x] 输出语言默认跟随输入主语言
- [x] 双语支持未导致 token 异常膨胀

### 4.4 多 Provider

- [x] Gemini 可正常完成 `intent + generation`
- [x] OpenAI 可正常完成 `intent + generation`
- [ ] Doubao 可正常完成 `intent + generation`
- [x] 同一 provider 同时承载两阶段，不做跨 provider 混用
- [x] provider 切换不影响 contract 选择逻辑
- [x] 日志能明确记录 provider / model / key source

### 4.5 跨应用输入整理

- [ ] 微信等非编辑器应用中可正常使用
- [ ] 备忘录/通用文本输入场景可正常使用
- [ ] Cursor / antigravity 中可正常使用 Quick Action 主线
- [ ] 选中文本 -> 触发 -> 原地替换 整体闭环稳定

---

## 5. 质量评估

### 5.1 中文质量评测

- [x] 6 个主场景抽样完成
- [x] 使用 LLM 进行多维度评分
- [ ] 评分维度至少包括：
  - [x] `scene_fit`
  - [x] `semantic_fidelity`
  - [x] `ai_collab_usability`
  - [x] `structured_natural_expression`
  - [x] `scope_control`
  - [x] `overall`

### 5.2 英文质量评测

- [x] 英文 6 场景抽样完成
- [x] 英文 contract 真实验证完成
- [x] `general / discussion_confirm` 边界已专项验证

### 5.3 模型对比评测

- [x] Gemini 作为主基线质量已确认
- [x] OpenAI 最小质量对比已完成
- [ ] Doubao 最小质量对比已完成
- [x] 模型差异结论已记录，不只看“能跑通”

### 5.4 回归与 token

- [x] Gemini 正式回归完整跑通
- [x] token smoke 跑通
- [x] 第一层 token 处于目标范围
- [x] 第二层 token 未异常膨胀
- [x] provider-neutral 改造未造成 Gemini 基线明显退化

---

## 6. 安全与发布阻断项

### 6.1 凭据安全

- [x] 安装器结果文件不包含明文 API Key
- [x] shell 不通过进程参数传递明文 API Key
- [x] 安全存储相关逻辑不再阻断主安装闭环
- [x] 仓库中不存在可用 live key
- [x] `.gitignore` 已覆盖日志、缓存、构建产物、临时文件

### 6.2 日志安全与可观测性

- [x] 聚合日志使用 JSONL
- [x] 单请求日志使用 JSON
- [x] 日志中不记录明文 API Key
- [ ] 日志字段足够支撑：
  - [x] 安装排障
  - [x] provider 排障
  - [x] 质量分析
  - [x] token 分析

### 6.3 GitHub 发布前检查

- [x] 文档中不再出现“内嵌 API Key”描述
- [x] 文档中不再把当前实现描述为 Gemini-only
- [x] README / PRD / Architecture 文档与实际实现一致
- [x] 安装包说明与实际安装流程一致
- [x] 不发布 `dist/` 产物作为源码面

---

## 7. 文档一致性

### 7.1 必须同步更新的文档

- [x] `Voice2Code_PRD.md`
- [x] `Voice2Code_Architecture.md`
- [x] `Voice2Code_Implementation_Checklist.md`
- [x] 收尾分析 / 重构分析文档
- [x] 安装说明与 release notes

### 7.2 文档要求

- [x] 描述当前真实实现，不保留历史过时表述
- [x] 区分：
  - [x] Quick Action 主线
  - [x] 初始化配置
  - [x] 多 provider
  - [x] 双语 contract
- [x] 当前 `Voice2Code.app` 仅作为最小控制壳，不把正规 App 化作为本轮门禁
- [x] 文档中的路径、版本、配置方式与代码一致

---

## 8. 发布验收标准

以下条件全部满足后，才视为可以进入正式发布 / 开源阶段：

- [ ] 安装链路稳定
- [ ] Quick Action 注册链路稳定
- [ ] 初始化配置闭环稳定
- [x] Gemini 主基线质量稳定
- [ ] OpenAI / 豆包最小验证完成
- [x] 中文 / 英文质量评估完成
- [x] provider-neutral 日志与配置治理完成
- [x] 安全阻断项已清理
- [x] 文档与实现一致
- [x] 版本化安装包可重复构建

---

## 9. 当前建议优先级

### P0

- [ ] 安装器兼容性与 Quick Action 注册闭环
- [ ] 初始化配置闭环
- [ ] Gemini 正式回归 + 中文 / 英文质量评分
- [ ] 发布 blocker 安全项清理
- [ ] 文档与实现对齐

### P1

- [ ] OpenAI / 豆包最小端到端质量验证
- [ ] 安装器日志与错误提示继续优化
- [ ] 质量评测脚本与报告沉淀

### P2

- [ ] 插件分支可行性验证
- [ ] 更进一步的宿主特化体验优化
- [ ] 非核心视觉与交互 polish

---

## 10. 收尾结论

项目收尾阶段的重点不是继续扩能力，而是确保两件事：

1. 用户一定能安装、配置并成功跑通第一条请求
2. 核心转写链路的质量、边界与安全性都可验证、可解释、可交付
