from __future__ import annotations

import json
import re
import uuid
from typing import Any

from .config_loader import DEFAULT_RUNTIME_CONTEXT, DEFAULT_PROVIDER_ID, GENERATION_MODEL, INTENT_MODEL
from .language import resolve_contract_language
from .protocols import RequestContext


PREFIX_PATTERN = re.compile(r"^\s*(rewrite|preserve|clarify)\s*[:：]\s*", re.IGNORECASE)

def parse_prefix(input_text: str) -> tuple[str, str]:
    forced_rewrite_strategy = ""
    cleaned_input = input_text.strip()
    match = PREFIX_PATTERN.match(cleaned_input)
    if match:
        prefix = match.group(1).lower()
        cleaned_input = PREFIX_PATTERN.sub("", cleaned_input, count=1).strip() or cleaned_input
        if prefix in {"rewrite", "preserve", "clarify"}:
            forced_rewrite_strategy = prefix
    if not cleaned_input:
        cleaned_input = input_text.strip()
    return cleaned_input, forced_rewrite_strategy


def parse_runtime_context(runtime_context_json: str) -> dict[str, Any]:
    try:
        runtime_context = json.loads(runtime_context_json or "{}")
    except Exception:
        runtime_context = DEFAULT_RUNTIME_CONTEXT
    return runtime_context if isinstance(runtime_context, dict) else DEFAULT_RUNTIME_CONTEXT


def normalize_runtime_context(runtime_context: dict[str, Any], cleaned_input: str) -> dict[str, Any]:
    selection_length = runtime_context.get("selection_length", len(cleaned_input)) if isinstance(runtime_context, dict) else len(cleaned_input)
    if not isinstance(selection_length, int):
        selection_length = len(cleaned_input)
    return {
        "file_type": runtime_context.get("file_type", "") if isinstance(runtime_context, dict) else "",
        "editor_name": runtime_context.get("editor_name", "") if isinstance(runtime_context, dict) else "",
        "target_surface": runtime_context.get("target_surface", DEFAULT_RUNTIME_CONTEXT["target_surface"]) if isinstance(runtime_context, dict) else DEFAULT_RUNTIME_CONTEXT["target_surface"],
        "selection_length": selection_length,
    }


def build_request_context(
    input_text: str,
    runtime_context_json: str,
    glossary_mode: str,
    glossary_max_entries: int,
    provider_id: str,
    intent_model: str,
    generation_model: str,
    key_source: str,
    api_key: str,
    force_intent_parse_fail: bool,
    force_generation_parse_fail: bool,
) -> RequestContext:
    cleaned_input, forced_rewrite_strategy = parse_prefix(input_text)
    input_language_detected, contract_language = resolve_contract_language(cleaned_input)
    return RequestContext(
        request_id=str(uuid.uuid4())[:8],
        input_text=cleaned_input,
        runtime_context=parse_runtime_context(runtime_context_json),
        forced_rewrite_strategy=forced_rewrite_strategy,
        input_language_detected=input_language_detected,
        contract_language=contract_language,
        provider_id=(provider_id or DEFAULT_PROVIDER_ID).strip().lower(),
        key_source=(key_source or "none").strip().lower(),
        glossary_mode=glossary_mode,
        glossary_max_entries=glossary_max_entries,
        intent_model=intent_model or INTENT_MODEL,
        generation_model=generation_model or GENERATION_MODEL,
        api_key=api_key.strip(),
        force_intent_parse_fail=force_intent_parse_fail,
        force_generation_parse_fail=force_generation_parse_fail,
    )
