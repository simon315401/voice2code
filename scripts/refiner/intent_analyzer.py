from __future__ import annotations

import json
from typing import Any

from .config_loader import resolve_prompt_contracts
from .protocols import PromptBundle, RequestContext
from .request_builder import normalize_runtime_context


def _compact_runtime_context(runtime_context: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in runtime_context.items() if value not in ("", None, [])}


def _intent_runtime_context(runtime_context: dict[str, Any]) -> dict[str, Any]:
    compact = _compact_runtime_context(runtime_context)
    allowed_keys = ("target_surface", "selection_length", "file_type")
    return {key: compact[key] for key in allowed_keys if key in compact}


def build_intent_prompt(context: RequestContext, config: dict[str, Any]) -> PromptBundle:
    normalized_runtime_context = normalize_runtime_context(context.runtime_context, context.input_text)
    compact_runtime_context = _intent_runtime_context(normalized_runtime_context)
    resolved_config = resolve_prompt_contracts(config, context.contract_language)
    intent_config = resolved_config["intent_analysis"]
    schema = intent_config["response_schema"]
    scene_labels = intent_config.get("scene_labels", {})
    structure_labels = intent_config.get("structure_labels", {})
    priority_rules = intent_config.get("priority_rules", [])

    scene_lines = "\n".join(f"- {name}: {desc}" for name, desc in scene_labels.items())
    structure_lines = "\n".join(f"- {name}: {desc}" for name, desc in structure_labels.items())
    priority_lines = "\n".join(f"- {rule}" for rule in priority_rules)

    forced_lines = []
    if context.forced_rewrite_strategy:
        forced_lines.append(f"- rewrite_strategy 已由系统前缀固定为 {context.forced_rewrite_strategy}；你无需判断该字段。")
    system_instruction_text = f"""{intent_config['role']}
{intent_config['goal']}
"""
    prompt_sections = [
        "请只判断 main_scene 和 structure_mode，并返回 JSON。",
        "scene_labels:",
        scene_lines,
        "structure_labels:",
        structure_lines,
        "priority_rules:",
        priority_lines,
    ]
    if forced_lines:
        prompt_sections.extend(["system_resolved:", "\n".join(forced_lines)])
    if compact_runtime_context:
        prompt_sections.append(f"runtime_context: {json.dumps(compact_runtime_context, ensure_ascii=False)}")
    prompt_sections.extend(
        [
            f"contract_language: {resolved_config['contract_language']}",
            f"user_input: {context.input_text}",
            "output_fields: main_scene, structure_mode",
        ]
    )
    user_prompt_text = "\n".join(section for section in prompt_sections if section)
    prompt_text = f"{system_instruction_text}\n{user_prompt_text}"

    payload = {
        "system_instruction": {"parts": [{"text": system_instruction_text}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt_text}]}],
        "generationConfig": {
            "temperature": 0.0,
            "responseMimeType": "application/json",
            "responseJsonSchema": {
                "type": "object",
                "properties": {
                    "main_scene": {"type": "string", "enum": schema["main_scene"]},
                    "structure_mode": {"type": "string", "enum": schema["structure_mode"]},
                },
                "required": ["main_scene", "structure_mode"],
                "additionalProperties": False,
            },
        },
    }
    return PromptBundle(
        cleaned_input=context.input_text,
        normalized_runtime_context=normalized_runtime_context,
        selected_glossary_entries=[],
        glossary_warning="",
        system_instruction_text=system_instruction_text,
        user_prompt_text=user_prompt_text,
        prompt_char_count=len(system_instruction_text) + len(user_prompt_text),
        prompt_text=prompt_text,
        payload=payload,
    )
