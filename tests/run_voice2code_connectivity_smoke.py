from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path("/Users/yifeiliu/cursor/AIO/ai_command_optimization")
RUNNER = ROOT / "scripts" / "voice2code_runner.py"


def parse_request_log(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    sample_input = "整理一下这段需求表达，让它更适合继续交给 AI 执行。"
    provider_id = os.environ.get("V2C_PROVIDER", "gemini").strip().lower() or "gemini"
    with tempfile.TemporaryDirectory(prefix="v2c_connectivity_") as temp_dir:
        log_dir = Path(temp_dir) / "logs"
        log_file = Path(temp_dir) / "debug.log"
        env = os.environ.copy()
        env["V2C_LOG_DIR"] = str(log_dir)
        env["V2C_LOG_FILE"] = str(log_file)
        env["V2C_RUNTIME_CONTEXT_JSON"] = json.dumps(
            {
                "file_type": ".md",
                "editor_name": "Cursor",
                "target_surface": "connectivity_smoke",
                "selection_length": len(sample_input),
            },
            ensure_ascii=False,
        )

        result = subprocess.run(
            [sys.executable, str(RUNNER)],
            input=sample_input,
            text=True,
            capture_output=True,
            env=env,
            check=False,
        )
        if result.returncode != 0:
            print(json.dumps({"ok": False, "reason": f"runner_exit_{result.returncode}", "stderr": result.stderr}, ensure_ascii=False, indent=2))
            return 1

        request_logs = sorted(log_dir.glob("*.json"))
        if len(request_logs) != 1:
            print(json.dumps({"ok": False, "reason": f"expected_1_request_log_got_{len(request_logs)}"}, ensure_ascii=False, indent=2))
            return 1

        metadata = parse_request_log(request_logs[0])
        final_output = result.stdout.strip()
        ok = (
            metadata.get("status") == "success"
            and bool(final_output)
            and int(((metadata.get("intent") or {}).get("prompt_token_count", 0))) > 0
            and int(((metadata.get("generation") or {}).get("prompt_token_count", 0))) > 0
        )
        payload = {
            "ok": ok,
            "provider_id": provider_id,
            "status": str(metadata.get("status", "")),
            "network_mode": str(metadata.get("network_mode", "")),
            "main_scene": str(metadata.get("main_scene", "")),
            "structure_mode": str(metadata.get("structure_mode", "")),
            "contract_language": str(metadata.get("contract_language", "")),
            "intent_model": str(((metadata.get("intent") or {}).get("model", ""))),
            "generation_model": str(((metadata.get("generation") or {}).get("model", ""))),
            "intent_prompt_token_count": (metadata.get("intent") or {}).get("prompt_token_count", ""),
            "generation_prompt_token_count": (metadata.get("generation") or {}).get("prompt_token_count", ""),
            "total_latency_ms": metadata.get("total_latency_ms", ""),
            "final_output_preview": final_output[:200],
            "fallback_reason": str(metadata.get("fallback_reason", "")),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
