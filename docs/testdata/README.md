# Voice2Code Testdata

本目录用于固化 Voice2Code 的回归样本资产，避免后续验证继续依赖临时日志或人工回忆。

## 文件

- `voice2code_regression_samples.json`
  - 固定回归样本集
  - 包含输入文本、预期状态、允许场景、允许格式、必须包含与禁止包含约束

## 配套脚本

- `/Users/yifeiliu/cursor/AIO/ai_command_optimization/tests/run_voice2code_regression.py`
  - 顺序回归脚本
- `/Users/yifeiliu/cursor/AIO/ai_command_optimization/tests/run_voice2code_concurrency.py`
  - 并发日志与请求隔离回归脚本

## 使用方式

```bash
python3 /Users/yifeiliu/cursor/AIO/ai_command_optimization/tests/run_voice2code_regression.py
python3 /Users/yifeiliu/cursor/AIO/ai_command_optimization/tests/run_voice2code_concurrency.py
```
