from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path("/Users/yifeiliu/cursor/AIO/ai_command_optimization")
RUNNER = ROOT / "scripts" / "voice2code_runner.py"
REGRESSION_SAMPLES = ROOT / "docs" / "testdata" / "voice2code_regression_samples.json"
QUALITY_SAMPLE_IDS = ROOT / "docs" / "testdata" / "voice2code_quality_samples.json"

GEMINI_EVAL_MODEL = os.environ.get("V2C_GEMINI_EVAL_MODEL", "gemini-3.1-flash-lite-preview").strip() or "gemini-3.1-flash-lite-preview"


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_sample_map() -> dict[str, dict[str, object]]:
    samples = _load_json(REGRESSION_SAMPLES)
    return {str(sample["id"]): sample for sample in samples}


def _parse_request_log(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _provider_env(provider_id: str) -> dict[str, str]:
    normalized = provider_id.strip().lower()
    env = os.environ.copy()
    env["V2C_PROVIDER"] = normalized
    if normalized == "openai":
        env["V2C_INTENT_MODEL"] = os.environ.get("V2C_OPENAI_INTENT_MODEL", "gpt-5.4-nano")
        env["V2C_GENERATION_MODEL"] = os.environ.get("V2C_OPENAI_GENERATION_MODEL", "gpt-5.4-nano")
    elif normalized == "doubao":
        env["V2C_INTENT_MODEL"] = os.environ.get("V2C_DOUBAO_INTENT_MODEL", "doubao-seed-1-6-250615")
        env["V2C_GENERATION_MODEL"] = os.environ.get("V2C_DOUBAO_GENERATION_MODEL", "doubao-seed-1-6-250615")
    else:
        env.pop("V2C_INTENT_MODEL", None)
        env.pop("V2C_GENERATION_MODEL", None)
    return env


def _run_sample(sample: dict[str, object], provider_id: str) -> dict[str, object]:
    text = str(sample["input"])
    env = _provider_env(provider_id)
    with tempfile.TemporaryDirectory(prefix=f"v2c_quality_{provider_id}_") as temp_dir:
        log_dir = Path(temp_dir) / "logs"
        log_file = Path(temp_dir) / "debug.log"
        env["V2C_LOG_DIR"] = str(log_dir)
        env["V2C_LOG_FILE"] = str(log_file)
        env["V2C_RUNTIME_CONTEXT_JSON"] = json.dumps(
            {
                "file_type": ".md",
                "editor_name": "Cursor",
                "target_surface": "quality_eval",
                "selection_length": len(text),
            },
            ensure_ascii=False,
        )
        result = subprocess.run(
            [sys.executable, str(RUNNER)],
            input=text,
            text=True,
            capture_output=True,
            env=env,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"{provider_id}:{sample['id']} runner exit {result.returncode}: {result.stderr.strip()}")
        request_logs = sorted(log_dir.glob("*.json"))
        if len(request_logs) != 1:
            raise RuntimeError(f"{provider_id}:{sample['id']} expected 1 request log, got {len(request_logs)}")
        metadata = _parse_request_log(request_logs[0])
        return {
            "sample_id": sample["id"],
            "input": text,
            "provider_id": provider_id,
            "status": metadata.get("status", ""),
            "main_scene": metadata.get("main_scene", ""),
            "structure_mode": metadata.get("structure_mode", ""),
            "contract_language": metadata.get("contract_language", ""),
            "intent_model": ((metadata.get("intent") or {}).get("model", "")),
            "generation_model": ((metadata.get("generation") or {}).get("model", "")),
            "output": result.stdout.strip(),
        }


def _gemini_eval(prompt: str) -> dict[str, object]:
    api_key = os.environ.get("V2C_GEMINI_API_KEY", "").strip() or os.environ.get("V2C_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("missing Gemini evaluator key: set V2C_GEMINI_API_KEY or V2C_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_EVAL_MODEL}:generateContent"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0,
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "scene_fit": {"type": "NUMBER"},
                    "semantic_fidelity": {"type": "NUMBER"},
                    "ai_collab_usability": {"type": "NUMBER"},
                    "structured_natural_expression": {"type": "NUMBER"},
                    "scope_control": {"type": "NUMBER"},
                    "overall": {"type": "NUMBER"},
                    "notes": {"type": "STRING"},
                },
                "required": [
                    "scene_fit",
                    "semantic_fidelity",
                    "ai_collab_usability",
                    "structured_natural_expression",
                    "scope_control",
                    "overall",
                    "notes",
                ],
            },
        },
    }
    result = subprocess.run(
        [
            "curl",
            "-sS",
            "-X",
            "POST",
            url,
            "-H",
            "Content-Type: application/json",
            "-H",
            f"x-goog-api-key: {api_key}",
            "--data-binary",
            "@-",
        ],
        input=json.dumps(payload, ensure_ascii=False),
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Gemini evaluator curl failed: {result.stderr.strip()}")
    data = json.loads(result.stdout)
    if isinstance(data, dict) and data.get("error"):
        raise RuntimeError(f"Gemini evaluator API error: {json.dumps(data['error'], ensure_ascii=False)}")
    candidates = data.get("candidates") or []
    parts = (((candidates[0] or {}).get("content") or {}).get("parts") or []) if candidates else []
    text = "".join(str(part.get("text", "")) for part in parts if isinstance(part, dict)).strip()
    if not text:
        raise RuntimeError("Gemini evaluator returned empty content")
    return json.loads(text)


def _build_eval_prompt(sample: dict[str, object], candidate: dict[str, object]) -> str:
    expected_language = sample.get("expected_contract_language")
    language_note = "输出应为英文。" if expected_language == "en-US" else "输出应为中文。"
    return f"""你是 Voice2Code 质量评审器。请只根据给定输入与候选输出，对候选结果做绝对评分，不要做相对比较。

评分维度均为 0-10 分，可使用一位小数。

维度定义：
- scene_fit: 是否符合该场景应有的表达目标
- semantic_fidelity: 是否忠实保留原始输入语义
- ai_collab_usability: 是否更适合继续交给 AI 理解、确认、执行或产出
- structured_natural_expression: 是否结构清晰且表达自然，不僵硬、不压平
- scope_control: 是否没有无根据扩写、没有越权新增结论或任务
- overall: 综合分

场景样本：
- sample_id: {sample['id']}
- 输入文本: {sample['input']}
- 预期说明: {language_note}

候选输出：
{candidate['output']}

请特别注意：
1. 不要因为措辞与你偏好不同就低分，重点看契约目标是否达成。
2. 如果输出结构该分行却压成单段，要影响 structured_natural_expression。
3. 如果输出新增了原文没有的模块、结论、流程，要影响 scope_control。
4. 如果输出语言与输入主语言不一致，要影响 scene_fit 和 overall。

只返回 JSON。"""


def _evaluate_provider_outputs(samples: list[dict[str, object]], provider_outputs: list[dict[str, object]]) -> dict[str, object]:
    scored = []
    for sample, candidate in zip(samples, provider_outputs):
        score = _gemini_eval(_build_eval_prompt(sample, candidate))
        scored.append({
            "sample_id": sample["id"],
            "provider_id": candidate["provider_id"],
            "score": score,
            "output": candidate["output"],
        })
    metric_names = [
        "scene_fit",
        "semantic_fidelity",
        "ai_collab_usability",
        "structured_natural_expression",
        "scope_control",
        "overall",
    ]
    summary = {}
    for metric in metric_names:
        summary[metric] = round(sum(float(item["score"][metric]) for item in scored) / len(scored), 2)
    return {"summary": summary, "samples": scored}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--providers", default="gemini,openai", help="comma-separated provider ids")
    parser.add_argument("--languages", default="zh,en", help="comma-separated language groups from voice2code_quality_samples.json")
    parser.add_argument("--output", default="", help="optional JSON output path")
    args = parser.parse_args()

    provider_ids = [item.strip().lower() for item in args.providers.split(",") if item.strip()]
    language_groups = [item.strip().lower() for item in args.languages.split(",") if item.strip()]

    sample_map = _load_sample_map()
    selected_ids_config = _load_json(QUALITY_SAMPLE_IDS)
    selected_ids: list[str] = []
    for group in language_groups:
        selected_ids.extend(str(x) for x in selected_ids_config[group])
    samples = [sample_map[sample_id] for sample_id in selected_ids]

    results: dict[str, object] = {"providers": {}, "sample_ids": selected_ids}
    for provider_id in provider_ids:
        outputs = [_run_sample(sample, provider_id) for sample in samples]
        results["providers"][provider_id] = _evaluate_provider_outputs(samples, outputs)

    if args.output:
        output_path = Path(args.output)
        output_path.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote quality report to {output_path}")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
