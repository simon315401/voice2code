# Cursor / Antigravity 插件分支兼容性验证 Checklist

## 1. 文档目标

本清单只用于 P2 预研，帮助判断是否值得启动 Voice2Code 的插件分支版本。

它不作为当前 Quick Action 主线发布门槛，也不允许反向影响主线架构。

---

## 2. 验证目标

要回答的核心问题只有四个：

1. 是否能稳定读取选中文本
2. 是否能调用现有 refiner 核心
3. 是否能将结果稳定回写到宿主编辑区
4. 同一套标准 VS Code 扩展，是否能同时在 Cursor / Antigravity 中运行

---

## 3. Cursor 验证

- [ ] 可安装标准 VS Code 扩展
- [ ] 可通过命令面板触发 Voice2Code 命令
- [ ] 可读取编辑器选中文本
- [ ] 可将处理结果回写编辑区
- [ ] 可调用现有本地 refiner 入口
- [ ] 可配置 Provider / API Key / 网络方式
- [ ] 不依赖 Cursor 专有 API 才能跑通核心链路

---

## 4. Antigravity 验证

- [ ] 可安装标准 VS Code 扩展
- [ ] Open VSX / 市场来源不会阻塞安装
- [ ] 可通过命令面板触发 Voice2Code 命令
- [ ] 可读取编辑器选中文本
- [ ] 可将处理结果回写编辑区
- [ ] 可调用现有本地 refiner 入口
- [ ] 可配置 Provider / API Key / 网络方式
- [ ] 不依赖 Cursor 专有 API

---

## 5. 技术约束

- [ ] 插件分支只复用现有 refiner 核心，不重写转写逻辑
- [ ] 不把 Quick Action 主线实现迁移成插件主线
- [ ] 不允许插件分支需求反向改变当前两层主链路 contract
- [ ] 优先按“标准 VS Code 扩展”开发，不按 Cursor 专有插件开发

---

## 6. 启动条件

只有以下条件满足，才建议进入正式插件分支开发：

- [ ] Quick Action 主线已稳定
- [ ] Gemini 主基线质量稳定
- [ ] 初始化配置闭环稳定
- [ ] 插件 capability spike 已证明 Cursor 与 Antigravity 至少有一边能稳定跑通

若以上条件未满足，插件方向继续保持预研状态，不进入正式开发。
