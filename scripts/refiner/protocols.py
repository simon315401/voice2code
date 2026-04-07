from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RequestContext:
    request_id: str
    input_text: str
    runtime_context: dict[str, Any]
    forced_rewrite_strategy: str
    input_language_detected: str
    contract_language: str
    provider_id: str
    key_source: str
    glossary_mode: str
    glossary_max_entries: int
    intent_model: str
    generation_model: str
    api_key: str
    force_intent_parse_fail: bool = False
    force_generation_parse_fail: bool = False


@dataclass
class IntentAnalysisResult:
    main_scene: str
    structure_mode: str
    prompt_token_count: int = -1
    completion_token_count: int = -1
    model_version: str = ""


@dataclass
class PromptSelection:
    scene_id: str
    rewrite_id: str
    structure_id: str
    scene_instruction: str
    rewrite_instruction: str
    structure_instruction: str


@dataclass
class GlossaryResult:
    selected_entries: list[tuple[str, str]] = field(default_factory=list)
    selected_count: int = 0
    glossary_hint_text: str = ""
    warning: str = ""


@dataclass
class PromptBundle:
    cleaned_input: str
    normalized_runtime_context: dict[str, Any]
    selected_glossary_entries: list[tuple[str, str]]
    glossary_warning: str
    system_instruction_text: str
    user_prompt_text: str
    prompt_char_count: int
    prompt_text: str
    payload: dict[str, Any]


@dataclass
class GenerationResult:
    refined_text: str
    self_check: dict[str, Any] = field(default_factory=dict)
    prompt_token_count: int = -1
    completion_token_count: int = -1
    model_version: str = ""


@dataclass
class OutputResult:
    final_output: str
    applied_rules: list[str] = field(default_factory=list)


@dataclass
class LogRecord:
    request_id: str
    status: str
    error_stage: str
    network_mode: str
    provider_id: str
    key_source: str
    input_language_detected: str
    contract_language: str
    intent_latency_ms: int
    generation_latency_ms: int
    total_latency_ms: int
    intent_model: str
    generation_model: str
    intent_model_version: str
    generation_model_version: str
    intent_prompt_token_count: int
    intent_completion_token_count: int
    generation_prompt_token_count: int
    generation_completion_token_count: int
    generation_prompt_char_count: int
    forced_rewrite_strategy: str
    resolved_rewrite_id: str
    selected_scene_id: str
    selected_rewrite_id: str
    selected_structure_id: str
    intent_result: dict[str, Any] = field(default_factory=dict)
    raw_generation_output: str = ""
    final_output: str = ""
    applied_rules: list[str] = field(default_factory=list)
    fallback_reason: str = ""
    extra_lines: list[str] = field(default_factory=list)
