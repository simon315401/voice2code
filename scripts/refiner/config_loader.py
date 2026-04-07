from __future__ import annotations

import copy
import json
import os
import sys
from typing import Any

from .default_contracts import DEFAULT_CONFIG, DEFAULT_GLOSSARY, DEFAULT_RUNTIME_CONTEXT
from .runtime_settings import (
    APP_SUPPORT_DIR,
    CONFIG_DIR,
    CONFIG_FILE,
    DEFAULT_PROVIDER_ID,
    GENERATION_MODEL,
    GLOSSARY_FILE,
    INTENT_MODEL,
    LOG_DIR,
    LOG_FILE,
    MODEL,
    PROVIDERS,
)


def _deep_merge(defaults: dict[str, Any], loaded: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(defaults)
    for key, value in loaded.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _normalize_contracts(config: dict[str, Any]) -> dict[str, Any]:
    normalized = copy.deepcopy(config)
    contracts = normalized.get("contracts")

    if not isinstance(contracts, dict):
        contracts = {}
    if "zh-CN" not in contracts:
        legacy_intent = normalized.get("intent_analysis")
        legacy_generation = normalized.get("generation_contract")
        if isinstance(legacy_intent, dict) and isinstance(legacy_generation, dict):
            contracts["zh-CN"] = {
                "intent_analysis": copy.deepcopy(legacy_intent),
                "generation_contract": copy.deepcopy(legacy_generation),
            }
    defaults_contracts = DEFAULT_CONFIG["contracts"]
    for language, contract_pack in defaults_contracts.items():
        existing_pack = contracts.get(language, {})
        contracts[language] = _deep_merge(contract_pack, existing_pack if isinstance(existing_pack, dict) else {})

    normalized["contracts"] = contracts
    language_settings = normalized.get("language", {})
    if not isinstance(language_settings, dict):
        language_settings = {}
    normalized["language"] = _deep_merge(DEFAULT_CONFIG["language"], language_settings)
    return normalized


def _normalize_provider_settings(config: dict[str, Any]) -> dict[str, Any]:
    normalized = copy.deepcopy(config)

    provider_settings = normalized.get("provider", {})
    if not isinstance(provider_settings, dict):
        provider_settings = {}
    normalized["provider"] = _deep_merge(DEFAULT_CONFIG["provider"], provider_settings)

    credentials = normalized.get("credentials", {})
    if not isinstance(credentials, dict):
        credentials = {}
    configured_providers = credentials.get("configured_providers", {})
    if not isinstance(configured_providers, dict):
        configured_providers = {}
    if isinstance(credentials.get("gemini_api_key_configured"), bool) and "gemini" not in configured_providers:
        configured_providers["gemini"] = credentials["gemini_api_key_configured"]
    credentials["configured_providers"] = _deep_merge(
        DEFAULT_CONFIG["credentials"]["configured_providers"],
        configured_providers,
    )
    normalized["credentials"] = credentials

    provider_id = str(normalized["provider"].get("provider_id", DEFAULT_PROVIDER_ID) or DEFAULT_PROVIDER_ID).strip().lower()
    if provider_id not in PROVIDERS:
        provider_id = DEFAULT_PROVIDER_ID
    normalized["provider"]["provider_id"] = provider_id
    return normalized


def load_refiner_config() -> dict[str, Any]:
    os.makedirs(CONFIG_DIR, exist_ok=True)
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
            f.write("\n")
        return copy.deepcopy(DEFAULT_CONFIG)

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            loaded = json.load(f)
    except Exception as exc:
        print(f"[Voice2Code] 配置文件读取失败，回退默认配置: {exc}", file=sys.stderr)
        return copy.deepcopy(DEFAULT_CONFIG)

    if not isinstance(loaded, dict):
        print("[Voice2Code] 配置文件结构不完整，回退默认配置", file=sys.stderr)
        return copy.deepcopy(DEFAULT_CONFIG)

    return _normalize_provider_settings(_normalize_contracts(_deep_merge(DEFAULT_CONFIG, loaded)))


def resolve_prompt_contracts(config: dict[str, Any], contract_language: str) -> dict[str, Any]:
    normalized = _normalize_contracts(config)
    contracts = normalized["contracts"]
    language_settings = normalized["language"]
    default_language = str(language_settings.get("default_contract_language", "zh-CN"))
    fallback_language = str(language_settings.get("fallback_contract_language", default_language))
    selected_language = contract_language if contract_language in contracts else default_language
    if selected_language not in contracts:
        selected_language = fallback_language if fallback_language in contracts else "zh-CN"
    selected_pack = contracts[selected_language]
    resolved = copy.deepcopy(normalized)
    resolved["contract_language"] = selected_language
    resolved["intent_analysis"] = copy.deepcopy(selected_pack["intent_analysis"])
    resolved["generation_contract"] = copy.deepcopy(selected_pack["generation_contract"])
    return resolved


__all__ = [
    "APP_SUPPORT_DIR",
    "CONFIG_DIR",
    "CONFIG_FILE",
    "DEFAULT_CONFIG",
    "DEFAULT_GLOSSARY",
    "DEFAULT_RUNTIME_CONTEXT",
    "DEFAULT_PROVIDER_ID",
    "GENERATION_MODEL",
    "GLOSSARY_FILE",
    "INTENT_MODEL",
    "LOG_DIR",
    "LOG_FILE",
    "MODEL",
    "PROVIDERS",
    "load_refiner_config",
    "resolve_prompt_contracts",
]
