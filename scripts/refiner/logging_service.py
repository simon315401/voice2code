from __future__ import annotations

from datetime import datetime
import fcntl
import json
import os
import time

from .protocols import LogRecord


def now_ms() -> int:
    return int(time.time() * 1000)


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def build_log_block(record: LogRecord, *, input_text: str) -> dict[str, object]:
    intent_result = record.intent_result or {}
    return {
        "ts": _now_iso(),
        "request_id": record.request_id,
        "status": record.status,
        "error_stage": record.error_stage,
        "network_mode": record.network_mode,
        "provider_id": record.provider_id,
        "key_source": record.key_source,
        "input_language_detected": record.input_language_detected,
        "contract_language": record.contract_language,
        "input_text": input_text,
        "main_scene": intent_result.get("main_scene", ""),
        "structure_mode": intent_result.get("structure_mode", ""),
        "forced_rewrite_strategy": record.forced_rewrite_strategy,
        "resolved_rewrite_id": record.resolved_rewrite_id,
        "selected_scene_id": record.selected_scene_id,
        "selected_rewrite_id": record.selected_rewrite_id,
        "selected_structure_id": record.selected_structure_id,
        "intent": {
            "result": intent_result,
            "latency_ms": record.intent_latency_ms,
            "model": record.intent_model,
            "model_version": record.intent_model_version,
            "prompt_token_count": record.intent_prompt_token_count,
            "completion_token_count": record.intent_completion_token_count,
        },
        "generation": {
            "latency_ms": record.generation_latency_ms,
            "model": record.generation_model,
            "model_version": record.generation_model_version,
            "prompt_token_count": record.generation_prompt_token_count,
            "completion_token_count": record.generation_completion_token_count,
            "prompt_char_count": record.generation_prompt_char_count,
            "raw_output": record.raw_generation_output,
        },
        "output": {
            "final_output": record.final_output,
            "applied_rules": record.applied_rules,
        },
        "total_latency_ms": record.total_latency_ms,
        "fallback_reason": record.fallback_reason,
        "extra_lines": record.extra_lines,
    }


def write_logs(log_file: str, request_log_file: str, block: dict[str, object]) -> None:
    os.makedirs(os.path.dirname(request_log_file), exist_ok=True)
    with open(request_log_file, "w", encoding="utf-8") as f:
        json.dump(block, f, ensure_ascii=False, indent=2)
        f.write("\n")
    with open(log_file, "a+", encoding="utf-8") as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        lf.write(json.dumps(block, ensure_ascii=False))
        lf.write("\n")
        lf.flush()
        fcntl.flock(lf.fileno(), fcntl.LOCK_UN)
