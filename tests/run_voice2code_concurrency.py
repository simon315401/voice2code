from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path("/Users/yifeiliu/cursor/AIO/ai_command_optimization")
RUNNER = ROOT / "scripts" / "voice2code_runner.py"
SAMPLES = ROOT / "docs" / "testdata" / "voice2code_regression_samples.json"


def run_one(text: str, env: dict[str, str]) -> tuple[int, str, str]:
    result = subprocess.run(
        [sys.executable, str(RUNNER)],
        input=text,
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    return result.returncode, result.stdout, result.stderr


def main() -> int:
    samples = json.loads(SAMPLES.read_text(encoding="utf-8"))
    texts = [str(item["input"]) for item in samples if not item.get("force_parse_fail")][:6]
    if len(texts) < 4:
        print("not enough concurrency samples")
        return 1

    with tempfile.TemporaryDirectory(prefix="v2c_concurrency_") as temp_dir:
        log_dir = Path(temp_dir) / "logs"
        log_file = Path(temp_dir) / "debug.log"
        env = os.environ.copy()
        env["V2C_LOG_DIR"] = str(log_dir)
        env["V2C_LOG_FILE"] = str(log_file)
        env["V2C_RUNTIME_CONTEXT_JSON"] = json.dumps(
            {
                "file_type": ".md",
                "editor_name": "Cursor",
                "target_surface": "concurrency_test",
                "selection_length": 0,
            },
            ensure_ascii=False,
        )

        futures = []
        with ThreadPoolExecutor(max_workers=min(6, len(texts))) as executor:
            for text in texts:
                futures.append(executor.submit(run_one, text, env))
            results = [future.result() for future in as_completed(futures)]

        for code, _stdout, stderr in results:
            if code != 0:
                print(f"runner exit code {code}: {stderr}")
                return 1

        request_logs = sorted(log_dir.glob("*.json"))
        if len(request_logs) != len(texts):
            print(f"request log count mismatch: expected {len(texts)}, got {len(request_logs)}")
            return 1

        aggregate_lines = [line for line in log_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        aggregate = [json.loads(line) for line in aggregate_lines]
        request_ids = []
        for path in request_logs:
            request_id = path.stem
            request_ids.append(request_id)
            content = json.loads(path.read_text(encoding="utf-8"))
            if content.get("request_id") != request_id:
                print(f"request log missing request_id field: {path}")
                return 1
            if "status" not in content:
                print(f"request log missing status field: {path}")
                return 1
            if not any(item.get("request_id") == request_id for item in aggregate):
                print(f"aggregate log missing request_id {request_id}")
                return 1

        if len(aggregate) != len(texts):
            print(f"aggregate block count mismatch: expected {len(texts)}, got {len(aggregate)}")
            return 1

        seen = set()
        for item in aggregate:
            request_id = str(item.get("request_id", ""))
            if not request_id:
                print("aggregate block missing request_id")
                return 1
            if request_id in seen:
                print(f"duplicate request_id in aggregate log: {request_id}")
                return 1
            seen.add(request_id)

        print(f"Concurrency regression passed: {len(texts)} request(s)")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
