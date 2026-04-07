from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path("/Users/yifeiliu/cursor/AIO/ai_command_optimization")
RUNNER = ROOT / "scripts" / "voice2code_runner.py"
SAMPLES = ROOT / "docs" / "testdata" / "voice2code_regression_samples.json"


def parse_request_log(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def assert_sample(sample: dict[str, object], stdout: str, metadata: dict[str, object]) -> list[str]:
    failures: list[str] = []
    expected_status = str(sample.get("expected_status", "success"))
    if metadata.get("status") != expected_status:
        failures.append(f"status expected {expected_status}, got {metadata.get('status', '')}")

    allowed_scenes = [str(x) for x in sample.get("allowed_scenes", [])]
    if allowed_scenes and metadata.get("main_scene", "") not in allowed_scenes:
        failures.append(f"main_scene not in {allowed_scenes}: {metadata.get('main_scene', '')}")

    expected_structure_mode = sample.get("expected_structure_mode")
    if expected_structure_mode is not None and metadata.get("structure_mode", "") != str(expected_structure_mode):
        failures.append(
            f"structure_mode expected {expected_structure_mode}, got {metadata.get('structure_mode', '')}"
        )

    expected_contract_language = sample.get("expected_contract_language")
    if expected_contract_language is not None and metadata.get("contract_language", "") != str(expected_contract_language):
        failures.append(
            f"contract_language expected {expected_contract_language}, got {metadata.get('contract_language', '')}"
        )

    for token in sample.get("must_contain_all", []):
        if str(token) not in stdout:
            failures.append(f"missing required token: {token}")

    any_tokens = [str(x) for x in sample.get("must_contain_any", [])]
    if any_tokens and not any(token in stdout for token in any_tokens):
        failures.append(f"none of required-any tokens found: {any_tokens}")

    for raw_group in sample.get("must_contain_groups", []):
        group = [str(x) for x in raw_group]
        if group and not any(token in stdout for token in group):
            failures.append(f"none of grouped tokens found: {group}")

    for token in sample.get("must_not_contain", []):
        if str(token) in stdout:
            failures.append(f"forbidden token found: {token}")

    custom = sample.get("custom_assertions", {})
    if isinstance(custom, dict):
        min_newlines = custom.get("min_newlines")
        if min_newlines is not None:
            actual_newlines = stdout.count("\n")
            if actual_newlines < int(min_newlines):
                failures.append(f"newline count expected >= {int(min_newlines)}, got {actual_newlines}")
        max_newlines = custom.get("max_newlines")
        if max_newlines is not None:
            actual_newlines = stdout.count("\n")
            if actual_newlines > int(max_newlines):
                failures.append(f"newline count expected <= {int(max_newlines)}, got {actual_newlines}")

    return failures


def run_sample(sample: dict[str, object], timeout_seconds: float) -> tuple[str, list[str], float]:
    started_at = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="v2c_reg_") as temp_dir:
        log_dir = Path(temp_dir) / "logs"
        log_file = Path(temp_dir) / "debug.log"
        env = os.environ.copy()
        env["V2C_LOG_DIR"] = str(log_dir)
        env["V2C_LOG_FILE"] = str(log_file)
        env["V2C_RUNTIME_CONTEXT_JSON"] = json.dumps(
            {
                "file_type": ".md",
                "editor_name": "Cursor",
                "target_surface": "regression_test",
                "selection_length": len(str(sample["input"])),
            },
            ensure_ascii=False,
        )
        if sample.get("force_parse_fail"):
            env["V2C_TEST_FORCE_GENERATION_PARSE_FAIL"] = "1"
        else:
            env.pop("V2C_TEST_FORCE_GENERATION_PARSE_FAIL", None)
            env.pop("V2C_TEST_FORCE_PARSE_FAIL", None)

        try:
            result = subprocess.run(
                [sys.executable, str(RUNNER)],
                input=str(sample["input"]),
                text=True,
                capture_output=True,
                env=env,
                check=False,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            return str(sample["id"]), [f"runner timed out after {timeout_seconds:.1f}s"], time.perf_counter() - started_at
        if result.returncode != 0:
            return str(sample["id"]), [f"runner exit code {result.returncode}", result.stderr.strip()], time.perf_counter() - started_at

        request_logs = sorted(log_dir.glob("*.json"))
        if len(request_logs) != 1:
            return str(sample["id"]), [f"expected 1 request log, got {len(request_logs)}"], time.perf_counter() - started_at

        metadata = parse_request_log(request_logs[0])
        failures = assert_sample(sample, result.stdout, metadata)
        return str(sample["id"]), failures, time.perf_counter() - started_at


def main() -> int:
    timeout_seconds = float(os.environ.get("V2C_REGRESSION_TIMEOUT_SECONDS", "45"))
    samples = json.loads(SAMPLES.read_text(encoding="utf-8"))
    failed = []
    total = len(samples)
    suite_started_at = time.perf_counter()
    for index, sample in enumerate(samples, start=1):
        sample_id, failures, elapsed = run_sample(sample, timeout_seconds)
        if failures:
            failed.append((sample_id, failures))
            print(f"[{index}/{total}] [FAIL] {sample_id} ({elapsed:.1f}s)", flush=True)
            for failure in failures:
                print(f"  - {failure}", flush=True)
        else:
            print(f"[{index}/{total}] [PASS] {sample_id} ({elapsed:.1f}s)", flush=True)
    suite_elapsed = time.perf_counter() - suite_started_at
    if failed:
        print(f"\nRegression failed: {len(failed)} sample(s) / {total} in {suite_elapsed:.1f}s", flush=True)
        return 1
    print(f"\nRegression passed: {total} sample(s) in {suite_elapsed:.1f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
