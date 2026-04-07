from __future__ import annotations

import json
from typing import Any

from .config_loader import resolve_prompt_contracts
from .protocols import IntentAnalysisResult, RequestContext


ALLOWED_MAIN_SCENE = {"general", "task", "question", "discussion_confirm", "doc", "feedback_meta"}
ALLOWED_STRUCTURE_MODE = {"inline", "structured"}


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
        raise RuntimeError("intent_json_parse_failed: empty_text")
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"intent_json_parse_failed: {exc}") from exc
    if not isinstance(obj, dict):
        raise RuntimeError("intent_json_parse_failed: not_object")
    return obj


def _usage_field(usage: dict[str, Any], *keys: str) -> int:
    for key in keys:
        value = usage.get(key)
        if isinstance(value, int):
            return value
    return -1


def parse_intent_response(data: dict[str, Any], context: RequestContext, config: dict[str, Any]) -> IntentAnalysisResult:
    schema = resolve_prompt_contracts(config, context.contract_language)["intent_analysis"]["response_schema"]
    obj = _extract_json_object(data)
    main_scene = obj.get("main_scene")
    structure_mode = obj.get("structure_mode")

    if main_scene not in schema["main_scene"] or main_scene not in ALLOWED_MAIN_SCENE:
        raise RuntimeError(f"intent_contract_broken: invalid main_scene={main_scene}")
    if structure_mode not in schema["structure_mode"] or structure_mode not in ALLOWED_STRUCTURE_MODE:
        raise RuntimeError(f"intent_contract_broken: invalid structure_mode={structure_mode}")

    usage = data.get("usageMetadata", {}) if isinstance(data.get("usageMetadata"), dict) else {}
    return IntentAnalysisResult(
        main_scene=main_scene,
        structure_mode=structure_mode,
        prompt_token_count=_usage_field(usage, "promptTokenCount"),
        completion_token_count=_usage_field(usage, "candidatesTokenCount", "thoughtsTokenCount", "totalTokenCount"),
        model_version=str(data.get("modelVersion", "")),
    )
