from __future__ import annotations

import json
import os
import sys

from .config_loader import (
    DEFAULT_RUNTIME_CONTEXT,
    DEFAULT_PROVIDER_ID,
    GENERATION_MODEL,
    INTENT_MODEL,
    LOG_DIR,
    LOG_FILE,
    PROVIDERS,
    load_refiner_config,
)
from .generation_gateway import analyze_intent, build_proxy_env, generate_refinement
from .generation_parser import parse_generation_response
from .glossary import ensure_glossary_file, match_glossary
from .intent_analyzer import build_intent_prompt
from .intent_parser import parse_intent_response
from .logging_service import build_log_block, now_ms, write_logs
from .output_formatter import apply_output_formatter
from .prompt_assembler import assemble_prompt
from .prompt_selection import build_prompt_selection
from .protocols import LogRecord, OutputResult, RequestContext
from .request_builder import build_request_context
from .secrets import resolve_api_key


def _resolve_provider_runtime(config: dict[str, object]) -> tuple[str, str, str]:
    provider_settings = config.get("provider", {}) if isinstance(config, dict) else {}
    if not isinstance(provider_settings, dict):
        provider_settings = {}
    providers = provider_settings.get("providers", {})
    if not isinstance(providers, dict):
        providers = {}
    provider_id = str(os.environ.get("V2C_PROVIDER", provider_settings.get("provider_id", DEFAULT_PROVIDER_ID)) or DEFAULT_PROVIDER_ID).strip().lower()
    if provider_id not in PROVIDERS:
        provider_id = DEFAULT_PROVIDER_ID
    configured_provider = providers.get(provider_id, {})
    if not isinstance(configured_provider, dict):
        configured_provider = {}
    provider_defaults = PROVIDERS[provider_id]
    intent_model = (
        os.environ.get("V2C_INTENT_MODEL")
        or os.environ.get("V2C_MODEL")
        or str(configured_provider.get("intent_model", provider_defaults["intent_model"]))
        or provider_defaults["intent_model"]
    )
    generation_model = (
        os.environ.get("V2C_GENERATION_MODEL")
        or os.environ.get("V2C_MODEL")
        or str(configured_provider.get("generation_model", provider_defaults["generation_model"]))
        or provider_defaults["generation_model"]
    )
    return provider_id, intent_model, generation_model


def _execute_request(context: RequestContext) -> tuple[OutputResult, LogRecord]:
    start_ms = now_ms()
    config = load_refiner_config()
    network_config = config.get("network", {})
    _proxy_env, network_mode = build_proxy_env(network_config)
    glossary_file = ensure_glossary_file()

    intent_start = now_ms()
    intent_bundle = build_intent_prompt(context, config)
    intent_raw = analyze_intent(context, intent_bundle, network_config)
    intent_latency = now_ms() - intent_start
    intent_result = parse_intent_response(intent_raw, context, config)

    prompt_selection = build_prompt_selection(context, intent_result, config)
    glossary_result = match_glossary(context, glossary_file, config)

    generation_start = now_ms()
    generation_bundle = assemble_prompt(context, intent_result, prompt_selection, glossary_result, config)
    generation_raw = generate_refinement(context, generation_bundle, network_config)
    generation_latency = now_ms() - generation_start
    generation_result, raw_generation_output = parse_generation_response(generation_raw, context, config)

    output_result = apply_output_formatter(generation_result)
    total_latency = now_ms() - start_ms

    record = LogRecord(
        request_id=context.request_id,
        status="success",
        error_stage="",
        network_mode=network_mode,
        provider_id=context.provider_id,
        key_source=context.key_source,
        input_language_detected=context.input_language_detected,
        contract_language=context.contract_language,
        intent_latency_ms=intent_latency,
        generation_latency_ms=generation_latency,
        total_latency_ms=total_latency,
        intent_model=context.intent_model,
        generation_model=context.generation_model,
        intent_model_version=intent_result.model_version,
        generation_model_version=generation_result.model_version,
        intent_prompt_token_count=intent_result.prompt_token_count,
        intent_completion_token_count=intent_result.completion_token_count,
        generation_prompt_token_count=generation_result.prompt_token_count,
        generation_completion_token_count=generation_result.completion_token_count,
        generation_prompt_char_count=generation_bundle.prompt_char_count,
        forced_rewrite_strategy=context.forced_rewrite_strategy,
        resolved_rewrite_id=prompt_selection.rewrite_id,
        selected_scene_id=prompt_selection.scene_id,
        selected_rewrite_id=prompt_selection.rewrite_id,
        selected_structure_id=prompt_selection.structure_id,
        intent_result={
            "main_scene": intent_result.main_scene,
            "structure_mode": intent_result.structure_mode,
        },
        raw_generation_output=raw_generation_output,
        final_output=output_result.final_output,
        applied_rules=output_result.applied_rules,
        fallback_reason="",
        extra_lines=[],
    )
    return output_result, record


def run_refiner(context: RequestContext) -> OutputResult:
    output_result, _record = _execute_request(context)
    return output_result


def _build_failure_output(context: RequestContext, error_message: str) -> tuple[str, str, str]:
    provider_name = PROVIDERS.get(context.provider_id, PROVIDERS[DEFAULT_PROVIDER_ID])["display_name"]
    if error_message == "provider_api_key_missing":
        return "failed", "credentials", f"[Voice2Code 尚未完成初始化配置：缺少 {provider_name} API Key。]\n\n请打开 Voice2Code App 的设置页，完成 {provider_name} API Key 与网络测试后再重试。"
    if error_message.startswith("intent_json_parse_failed") or error_message.startswith("intent_contract_broken") or error_message.startswith("API错误:") or error_message.startswith("响应缺少 candidates") or error_message.startswith("candidates 存在但为空"):
        return "fallback", "intent", f"[AI 意图分析失败: {error_message}]\n\n{context.input_text}"
    if error_message.startswith("generation_json_parse_failed") or error_message.startswith("generation_contract_broken"):
        return "fallback", "generation", f"[AI 提纯解析失败: {error_message}]\n{context.input_text}"
    if error_message.startswith("curl_exit=") or error_message.startswith("HTTP ") or error_message.startswith("invalid_http_response"):
        return "failed", "request", f"[AI 请求失败: {error_message}]\n\n{context.input_text}"
    if error_message.startswith("prompt_selection_failed"):
        return "failed", "prompt_selection", context.input_text
    return "failed", "request", context.input_text


def run_from_stdin() -> int:
    start_ms = now_ms()
    config = load_refiner_config()
    provider_id, intent_model, generation_model = _resolve_provider_runtime(config)
    api_key, key_source = resolve_api_key(provider_id)
    glossary_mode = os.environ.get("V2C_GLOSSARY_MODE", "matched").strip().lower()
    try:
        glossary_max_entries = int(os.environ.get("V2C_GLOSSARY_MAX_ENTRIES", "12"))
    except ValueError:
        glossary_max_entries = 12
    runtime_context_json = os.environ.get("V2C_RUNTIME_CONTEXT_JSON", json.dumps(DEFAULT_RUNTIME_CONTEXT, ensure_ascii=False))
    force_intent_parse_fail = os.environ.get("V2C_TEST_FORCE_INTENT_PARSE_FAIL", "0") == "1"
    force_generation_parse_fail = (
        os.environ.get("V2C_TEST_FORCE_GENERATION_PARSE_FAIL", "0") == "1"
        or os.environ.get("V2C_TEST_FORCE_PARSE_FAIL", "0") == "1"
    )

    log_file = os.environ.get("V2C_LOG_FILE", LOG_FILE)
    log_dir = os.environ.get("V2C_LOG_DIR", LOG_DIR)

    input_text = sys.stdin.read()
    if not input_text:
        context = build_request_context(
            "",
            runtime_context_json,
            glossary_mode,
            glossary_max_entries,
            provider_id,
            intent_model,
            generation_model,
            key_source,
            api_key,
            force_intent_parse_fail,
            force_generation_parse_fail,
        )
        request_log_file = os.path.join(log_dir, f"{context.request_id}.json")
        record = LogRecord(
            request_id=context.request_id,
            status="empty_input",
            error_stage="input",
            network_mode="direct",
            provider_id=context.provider_id,
            key_source=context.key_source,
            input_language_detected=context.input_language_detected,
            contract_language=context.contract_language,
            intent_latency_ms=0,
            generation_latency_ms=0,
            total_latency_ms=0,
            intent_model=context.intent_model,
            generation_model=context.generation_model,
            intent_model_version=intent_model,
            generation_model_version=generation_model,
            intent_prompt_token_count=-1,
            intent_completion_token_count=-1,
            generation_prompt_token_count=-1,
            generation_completion_token_count=-1,
            generation_prompt_char_count=0,
            forced_rewrite_strategy="",
            resolved_rewrite_id="",
            selected_scene_id="",
            selected_rewrite_id="",
            selected_structure_id="",
            intent_result={},
            raw_generation_output="",
            final_output="",
        )
        write_logs(log_file, request_log_file, build_log_block(record, input_text=""))
        return 0

    context = build_request_context(
        input_text,
        runtime_context_json,
        glossary_mode,
        glossary_max_entries,
        provider_id,
        intent_model,
        generation_model,
        key_source,
        api_key,
        force_intent_parse_fail,
        force_generation_parse_fail,
    )
    request_log_file = os.path.join(log_dir, f"{context.request_id}.json")
    os.makedirs(log_dir, exist_ok=True)

    if not context.api_key:
        total_latency = now_ms() - start_ms
        final_output = _build_failure_output(context, "provider_api_key_missing")[2]
        record = LogRecord(
            request_id=context.request_id,
            status="failed",
            error_stage="credentials",
            network_mode="direct",
            provider_id=context.provider_id,
            key_source=context.key_source,
            input_language_detected=context.input_language_detected,
            contract_language=context.contract_language,
            intent_latency_ms=0,
            generation_latency_ms=0,
            total_latency_ms=total_latency,
            intent_model=context.intent_model,
            generation_model=context.generation_model,
            intent_model_version=intent_model,
            generation_model_version=generation_model,
            intent_prompt_token_count=-1,
            intent_completion_token_count=-1,
            generation_prompt_token_count=-1,
            generation_completion_token_count=-1,
            generation_prompt_char_count=0,
            forced_rewrite_strategy=context.forced_rewrite_strategy,
            resolved_rewrite_id="",
            selected_scene_id="",
            selected_rewrite_id="",
            selected_structure_id="",
            intent_result={},
            raw_generation_output="",
            final_output=final_output,
            applied_rules=[],
            fallback_reason="provider_api_key_missing",
            extra_lines=[],
        )
        write_logs(log_file, request_log_file, build_log_block(record, input_text=context.input_text))
        sys.stdout.write(final_output)
        return 0

    try:
        output_result, record = _execute_request(context)
    except Exception as exc:
        total_latency = now_ms() - start_ms
        error_message = str(exc)
        _proxy_env, network_mode = build_proxy_env(config.get("network", {}))
        status, error_stage, final_output = _build_failure_output(context, error_message)
        fallback_reason = error_message.split(":", 1)[0] if ":" in error_message else error_message
        record = LogRecord(
            request_id=context.request_id,
            status=status,
            error_stage=error_stage,
            network_mode=network_mode,
            provider_id=context.provider_id,
            key_source=context.key_source,
            input_language_detected=context.input_language_detected,
            contract_language=context.contract_language,
            intent_latency_ms=0,
            generation_latency_ms=0,
            total_latency_ms=total_latency,
            intent_model=context.intent_model,
            generation_model=context.generation_model,
            intent_model_version=intent_model,
            generation_model_version=generation_model,
            intent_prompt_token_count=-1,
            intent_completion_token_count=-1,
            generation_prompt_token_count=-1,
            generation_completion_token_count=-1,
            generation_prompt_char_count=0,
            forced_rewrite_strategy=context.forced_rewrite_strategy,
            resolved_rewrite_id="",
            selected_scene_id="",
            selected_rewrite_id="",
            selected_structure_id="",
            intent_result={},
            raw_generation_output="",
            final_output=final_output,
            applied_rules=[],
            fallback_reason=fallback_reason,
            extra_lines=[f"error: {error_message}"],
        )
        write_logs(log_file, request_log_file, build_log_block(record, input_text=context.input_text))
        sys.stdout.write(final_output)
        return 0

    write_logs(log_file, request_log_file, build_log_block(record, input_text=context.input_text))
    sys.stdout.write(output_result.final_output)
    return 0
