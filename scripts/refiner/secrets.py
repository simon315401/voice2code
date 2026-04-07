from __future__ import annotations

import os

from .runtime_settings import DEFAULT_PROVIDER_ID, PROVIDERS


def resolve_provider_id(provider_id: str) -> str:
    normalized = (provider_id or DEFAULT_PROVIDER_ID).strip().lower()
    return normalized if normalized in PROVIDERS else DEFAULT_PROVIDER_ID


def get_provider_keychain_binding(provider_id: str) -> tuple[str, str]:
    provider = PROVIDERS[resolve_provider_id(provider_id)]
    return provider["keychain_service"], provider["keychain_account"]


def _provider_env_key(provider_id: str) -> str:
    return f"V2C_{resolve_provider_id(provider_id).upper()}_API_KEY"


def resolve_api_key(provider_id: str, explicit_key: str = "") -> tuple[str, str]:
    if explicit_key.strip():
        return explicit_key.strip(), "explicit"

    provider_env_key = os.environ.get(_provider_env_key(provider_id), "").strip()
    if provider_env_key:
        return provider_env_key, "env"

    env_key = os.environ.get("V2C_API_KEY", "").strip()
    if env_key:
        return env_key, "env"
    return "", "none"
