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
SAMPLES = ROOT / "docs" / "testdata" / "voice2code_token_budget_smoke.json"
BASELINE = ROOT / "docs" / "testdata" / "voice2code_token_budget_baseline.json"


def parse_request_log(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_sample(sample: dict[str, str]) -> dict[str, object]:
    text = sample["input"]
    with tempfile.TemporaryDirectory(prefix="v2c_token_") as temp_dir:
        log_dir = Path(temp_dir) / "logs"
        log_file = Path(temp_dir) / "debug.log"
        env = os.environ.copy()
        env["V2C_LOG_DIR"] = str(log_dir)
        env["V2C_LOG_FILE"] = str(log_file)
        env["V2C_RUNTIME_CONTEXT_JSON"] = json.dumps(
            {
                "file_type": ".md",
                "editor_name": "Cursor",
                "target_surface": "token_smoke",
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
            raise RuntimeError(f"{sample['id']} failed: {result.stderr.strip()}")

        request_logs = sorted(log_dir.glob("*.json"))
        if len(request_logs) != 1:
            raise RuntimeError(f"{sample['id']} expected 1 request log, got {len(request_logs)}")

        metadata = parse_request_log(request_logs[0])
        return {
            "id": sample["id"],
            "input": text,
            "status": str(metadata.get("status", "")),
            "main_scene": str(metadata.get("main_scene", "")),
            "resolved_rewrite_id": str(metadata.get("resolved_rewrite_id", "")),
            "intent_prompt_token_count": int(((metadata.get("intent") or {}).get("prompt_token_count", -1))),
            "generation_prompt_token_count": int(((metadata.get("generation") or {}).get("prompt_token_count", -1))),
            "total_latency_ms": int(metadata.get("total_latency_ms", -1)),
            "final_output": str(((metadata.get("output") or {}).get("final_output", ""))),
        }


def summarize(samples: list[dict[str, object]]) -> dict[str, float]:
    count = len(samples)
    return {
        "sample_count": count,
        "intent_prompt_token_avg": round(sum(int(sample["intent_prompt_token_count"]) for sample in samples) / count, 1),
        "generation_prompt_token_avg": round(sum(int(sample["generation_prompt_token_count"]) for sample in samples) / count, 1),
        "total_latency_ms_avg": round(sum(int(sample["total_latency_ms"]) for sample in samples) / count, 1),
    }


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def print_report(current: dict[str, object], baseline: dict[str, object] | None) -> int:
    print(json.dumps(current, ensure_ascii=False, indent=2))
    if not baseline:
        return 0

    current_summary = current["summary"]
    baseline_summary = baseline["summary"]
    intent_change = float(current_summary["intent_prompt_token_avg"]) - float(baseline_summary["intent_prompt_token_avg"])
    generation_change = float(current_summary["generation_prompt_token_avg"]) - float(
        baseline_summary["generation_prompt_token_avg"]
    )
    latency_growth = 0.0
    if float(baseline_summary["total_latency_ms_avg"]) > 0:
        latency_growth = (
            (float(current_summary["total_latency_ms_avg"]) - float(baseline_summary["total_latency_ms_avg"]))
            / float(baseline_summary["total_latency_ms_avg"])
            * 100.0
        )

    print("\nDiff vs baseline:")
    print(
        f"- intent_prompt_token_avg: {baseline_summary['intent_prompt_token_avg']} -> {current_summary['intent_prompt_token_avg']} ({intent_change:+.1f})"
    )
    print(
        f"- generation_prompt_token_avg: {baseline_summary['generation_prompt_token_avg']} -> {current_summary['generation_prompt_token_avg']} ({generation_change:+.1f})"
    )
    print(
        f"- total_latency_ms_avg: {baseline_summary['total_latency_ms_avg']} -> {current_summary['total_latency_ms_avg']} ({latency_growth:+.1f}%)"
    )

    if intent_change > 60.0:
        print("\n[FAIL] intent_prompt_token_avg regressed too much")
        return 1
    if generation_change > 40.0:
        print("\n[FAIL] generation_prompt_token_avg regressed too much")
        return 1
    if latency_growth > 35.0:
        print("\n[FAIL] total_latency_ms_avg regressed too much")
        return 1
    print("\n[PASS] token smoke baseline respected")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-baseline", action="store_true")
    args = parser.parse_args()

    samples = load_json(SAMPLES)
    results = [run_sample(sample) for sample in samples]
    current = {"summary": summarize(results), "samples": results}

    if args.write_baseline:
        BASELINE.write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote baseline to {BASELINE}")
        print(json.dumps(current["summary"], ensure_ascii=False, indent=2))
        return 0

    baseline = load_json(BASELINE) if BASELINE.exists() else None
    return print_report(current, baseline)


if __name__ == "__main__":
    raise SystemExit(main())
