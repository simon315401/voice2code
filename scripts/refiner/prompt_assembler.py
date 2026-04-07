from __future__ import annotations

import json
from typing import Any

from .config_loader import resolve_prompt_contracts
from .protocols import GlossaryResult, IntentAnalysisResult, PromptBundle, PromptSelection, RequestContext
from .request_builder import normalize_runtime_context


def _compact_runtime_context(runtime_context: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in runtime_context.items() if value not in ("", None, [])}


def assemble_prompt(
    context: RequestContext,
    intent_result: IntentAnalysisResult,
    prompt_selection: PromptSelection,
    glossary_result: GlossaryResult,
    config: dict[str, Any],
) -> PromptBundle:
    normalized_runtime_context = normalize_runtime_context(context.runtime_context, context.input_text)
    compact_runtime_context = _compact_runtime_context(normalized_runtime_context)
    resolved_config = resolve_prompt_contracts(config, context.contract_language)
    contract_config = resolved_config["generation_contract"]
    global_contract = contract_config["global_contract"]

    rule_lines = "\n".join(f"- {rule}" for rule in global_contract["rules"])
    output_lines = "\n".join(f"- {rule}" for rule in global_contract["output_requirements"])
    system_instruction_text = f"""{global_contract['role']}
目标：{global_contract['goal']}

全局边界：
{rule_lines}

输出契约：
{output_lines}
"""

    content_lines = [
        "请按当前路由契约整理用户输入。",
        f"route: scene={prompt_selection.scene_id}; rewrite={prompt_selection.rewrite_id}; structure={prompt_selection.structure_id}",
        f"contract_language: {resolved_config['contract_language']}",
        f"scene_instruction: {prompt_selection.scene_instruction}",
        f"rewrite_instruction: {prompt_selection.rewrite_instruction}",
        f"structure_instruction: {prompt_selection.structure_instruction}",
    ]
    if compact_runtime_context:
        content_lines.append(f"runtime_context: {json.dumps(compact_runtime_context, ensure_ascii=False)}")
    if glossary_result.selected_entries or glossary_result.warning:
        content_lines.append(glossary_result.glossary_hint_text)
    content_lines.extend(
        [
            f"user_input: {context.input_text}",
            "output_fields: refined_text, self_check.json_valid, self_check.hard_constraints_kept",
        ]
    )
    user_prompt_text = "\n".join(content_lines)
    prompt_text = f"{system_instruction_text}\n\n{user_prompt_text}"
    prompt_char_count = len(system_instruction_text) + len(user_prompt_text)

    payload = {
        "system_instruction": {"parts": [{"text": system_instruction_text}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt_text}]}],
        "generationConfig": {
            "temperature": 0.0,
            "responseMimeType": "application/json",
            "responseJsonSchema": {
                "type": "object",
                "properties": {
                    "refined_text": {"type": "string"},
                    "self_check": {
                        "type": "object",
                        "properties": {
                            field: {"type": "boolean"}
                            for field in contract_config["response_schema"]["required_self_check_fields"]
                        },
                        "required": contract_config["response_schema"]["required_self_check_fields"],
                        "additionalProperties": True,
                    },
                },
                "required": ["refined_text", "self_check"],
                "additionalProperties": False,
            },
        },
    }
    return PromptBundle(
        cleaned_input=context.input_text,
        normalized_runtime_context=normalized_runtime_context,
        selected_glossary_entries=glossary_result.selected_entries,
        glossary_warning=glossary_result.warning,
        system_instruction_text=system_instruction_text,
        user_prompt_text=user_prompt_text,
        prompt_char_count=prompt_char_count,
        prompt_text=prompt_text,
        payload=payload,
    )
