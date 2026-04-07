from __future__ import annotations

import json
from typing import Any

from .config_loader import resolve_prompt_contracts
from .protocols import RequestContext
from .protocols import GenerationResult


def _extract_json_object(data: dict[str, Any]) -> dict[str, Any]:
    if "error" in data:
        raise RuntimeError(f"API错误: {data['error']}")
    candidates = data.get("candidates")
    if candidates is None:
        raise RuntimeError("响应缺少 candidates")
    if not isinstance(candidates, list) or not candidates:
        raise RuntimeError("candidates 存在但为空")
    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
    if not text:
        raise RuntimeError("generation_json_parse_failed: empty_text")
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"generation_json_parse_failed: {exc}") from exc
    if not isinstance(obj, dict):
        raise RuntimeError("generation_json_parse_failed: not_object")
    return obj


def _usage_field(usage: dict[str, Any], *keys: str) -> int:
    for key in keys:
        value = usage.get(key)
        if isinstance(value, int):
            return value
    return -1


def parse_generation_response(data: dict[str, Any], context: RequestContext, config: dict[str, Any]) -> tuple[GenerationResult, str]:
    obj = _extract_json_object(data)
    refined_text = obj.get("refined_text")
    self_check = obj.get("self_check")
    if not isinstance(refined_text, str) or not refined_text.strip():
        raise RuntimeError("generation_contract_broken: refined_text")
    if not isinstance(self_check, dict):
        raise RuntimeError("generation_contract_broken: self_check")

    required_fields = resolve_prompt_contracts(config, context.contract_language)["generation_contract"]["response_schema"]["required_self_check_fields"]
    for field in required_fields:
        if field not in self_check or not isinstance(self_check[field], bool):
            raise RuntimeError(f"generation_contract_broken: self_check.{field}")

    usage = data.get("usageMetadata", {}) if isinstance(data.get("usageMetadata"), dict) else {}
    return (
        GenerationResult(
            refined_text=refined_text.strip(),
            self_check=self_check,
            prompt_token_count=_usage_field(usage, "promptTokenCount"),
            completion_token_count=_usage_field(usage, "candidatesTokenCount", "thoughtsTokenCount", "totalTokenCount"),
            model_version=str(data.get("modelVersion", "")),
        ),
        refined_text,
    )
