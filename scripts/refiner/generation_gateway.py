from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from typing import Any

from .protocols import PromptBundle, RequestContext
from .runtime_settings import DEFAULT_PROVIDER_ID, PROVIDERS


def build_proxy_env(network_config: dict[str, Any]) -> tuple[dict[str, str], str]:
    env = os.environ.copy()
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        env.pop(key, None)

    if not isinstance(network_config, dict) or not network_config.get("proxy_enabled"):
        return env, "direct"

    scheme = str(network_config.get("proxy_scheme", "http") or "http").strip().lower()
    host = str(network_config.get("proxy_host", "127.0.0.1") or "127.0.0.1").strip()
    port = int(network_config.get("proxy_port", 7897) or 7897)
    proxy_url = f"{scheme}://{host}:{port}"

    if scheme in {"http", "https"}:
        env["HTTP_PROXY"] = proxy_url
        env["HTTPS_PROXY"] = proxy_url
        env["http_proxy"] = proxy_url
        env["https_proxy"] = proxy_url
    elif scheme == "socks5":
        env["ALL_PROXY"] = proxy_url
        env["all_proxy"] = proxy_url
        env["HTTP_PROXY"] = proxy_url
        env["HTTPS_PROXY"] = proxy_url
        env["http_proxy"] = proxy_url
        env["https_proxy"] = proxy_url
    else:
        raise RuntimeError(f"unsupported_proxy_scheme: {scheme}")

    return env, f"proxy:{proxy_url}"


def _resolve_provider(provider_id: str) -> dict[str, str]:
    normalized = (provider_id or DEFAULT_PROVIDER_ID).strip().lower()
    return PROVIDERS.get(normalized, PROVIDERS[DEFAULT_PROVIDER_ID])


def _curl_json(
    url: str,
    headers: list[str],
    payload: dict[str, Any],
    network_config: dict[str, Any],
) -> dict[str, Any]:
    cmd = [
        "curl",
        "-sS",
        "-w",
        "\nHTTP_CODE:%{http_code}",
        "-X",
        "POST",
        "--connect-timeout",
        "3",
        "--max-time",
        "20",
        "--retry",
        "2",
        "--retry-delay",
        "1",
        "--retry-all-errors",
        url,
    ]
    for header in headers:
        cmd.extend(["-H", header])
    cmd.extend(["-d", json.dumps(payload, ensure_ascii=False)])

    env, _mode = build_proxy_env(network_config)
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if result.returncode != 0:
        raise RuntimeError(f"curl_exit={result.returncode}: {result.stderr.strip()}")

    stdout = result.stdout
    marker = "\nHTTP_CODE:"
    if marker not in stdout:
        raise RuntimeError(f"invalid_http_response: {stdout}")
    body, http_code = stdout.rsplit(marker, 1)
    if http_code.strip() != "200":
        raise RuntimeError(f"HTTP {http_code.strip()}: {body.strip()}")
    return json.loads(body)


def _message_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                if isinstance(item.get("text"), str):
                    parts.append(item["text"])
                elif item.get("type") == "text" and isinstance(item.get("text"), str):
                    parts.append(item["text"])
        return "".join(parts)
    return ""


def _normalize_usage(usage: dict[str, Any]) -> dict[str, int]:
    if not isinstance(usage, dict):
        return {}
    return {
        "promptTokenCount": int(usage.get("prompt_tokens", usage.get("input_tokens", -1)) or -1),
        "candidatesTokenCount": int(usage.get("completion_tokens", usage.get("output_tokens", -1)) or -1),
        "totalTokenCount": int(usage.get("total_tokens", -1) or -1),
    }


def _coerce_self_check_value(value: Any) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "yes", "ok", "passed", "pass"}:
            return True
        if normalized in {"false", "no", "failed", "fail"}:
            return False
    if isinstance(value, (list, dict)):
        return bool(value)
    return value


def _normalize_contract_json_text(text: str) -> str:
    try:
        obj = json.loads(text)
    except Exception:
        return text
    if not isinstance(obj, dict):
        return text
    self_check = obj.get("self_check")
    if isinstance(self_check, dict):
        normalized = False
        for key, value in list(self_check.items()):
            coerced = _coerce_self_check_value(value)
            if coerced is not value:
                self_check[key] = coerced
                normalized = True
        if normalized:
            return json.dumps(obj, ensure_ascii=False)
    return text


def _normalize_chat_response(data: dict[str, Any]) -> dict[str, Any]:
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        return {"error": "响应缺少 choices"}
    message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
    text = _normalize_contract_json_text(_message_text(message.get("content")))
    return {
        "modelVersion": str(data.get("model", "")),
        "usageMetadata": _normalize_usage(data.get("usage", {})),
        "candidates": [{"content": {"parts": [{"text": text}]}}],
    }


def _build_chat_payload(model: str, bundle: PromptBundle) -> dict[str, Any]:
    messages: list[dict[str, str]] = []
    if bundle.system_instruction_text.strip():
        messages.append({"role": "system", "content": bundle.system_instruction_text})
    messages.append({"role": "user", "content": bundle.user_prompt_text})
    return {
        "model": model,
        "messages": messages,
        "response_format": {"type": "json_object"},
    }


@dataclass
class ProviderTestResult:
    ok: bool
    message: str


class BaseProviderAdapter:
    provider_id: str

    def __init__(self, provider_id: str) -> None:
        self.provider = _resolve_provider(provider_id)
        self.provider_id = self.provider["provider_id"]

    def analyze_intent(self, context: RequestContext, bundle: PromptBundle, network_config: dict[str, Any]) -> dict[str, Any]:
        return self._request(context.intent_model, context.api_key, bundle, network_config)

    def generate_refinement(self, context: RequestContext, bundle: PromptBundle, network_config: dict[str, Any]) -> dict[str, Any]:
        return self._request(context.generation_model, context.api_key, bundle, network_config)

    def test_connectivity(
        self,
        model: str,
        api_key: str,
        network_config: dict[str, Any],
    ) -> ProviderTestResult:
        try:
            bundle = PromptBundle(
                cleaned_input="ping",
                normalized_runtime_context={},
                selected_glossary_entries=[],
                glossary_warning="",
                system_instruction_text="",
                user_prompt_text="ping",
                prompt_char_count=4,
                prompt_text="ping",
                payload={"contents": [{"role": "user", "parts": [{"text": "ping"}]}]},
            )
            self._request(model, api_key, bundle, network_config)
            return ProviderTestResult(ok=True, message=f"{self.provider['display_name']} connectivity passed")
        except Exception as exc:
            return ProviderTestResult(ok=False, message=str(exc))

    def _request(self, model: str, api_key: str, bundle: PromptBundle, network_config: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class GeminiAdapter(BaseProviderAdapter):
    def _request(self, model: str, api_key: str, bundle: PromptBundle, network_config: dict[str, Any]) -> dict[str, Any]:
        base_url = self.provider["base_url"].rstrip("/")
        url = f"{base_url}/models/{model}:generateContent"
        headers = [
            "Content-Type: application/json",
            f"x-goog-api-key: {api_key}",
        ]
        return _curl_json(url, headers, bundle.payload, network_config)


class OpenAICompatibleAdapter(BaseProviderAdapter):
    def _request(self, model: str, api_key: str, bundle: PromptBundle, network_config: dict[str, Any]) -> dict[str, Any]:
        base_url = self.provider["base_url"].rstrip("/")
        url = f"{base_url}/chat/completions"
        headers = [
            "Content-Type: application/json",
            f"Authorization: Bearer {api_key}",
        ]
        raw = _curl_json(url, headers, _build_chat_payload(model, bundle), network_config)
        return _normalize_chat_response(raw)


def get_provider_adapter(provider_id: str) -> BaseProviderAdapter:
    provider = _resolve_provider(provider_id)
    if provider["api_style"] == "gemini_generate_content":
        return GeminiAdapter(provider["provider_id"])
    return OpenAICompatibleAdapter(provider["provider_id"])


def analyze_intent(context: RequestContext, bundle: PromptBundle, network_config: dict[str, Any]) -> dict[str, Any]:
    if context.force_intent_parse_fail:
        return {"candidates": [{"content": {"parts": [{"text": "not-json"}]}}]}
    return get_provider_adapter(context.provider_id).analyze_intent(context, bundle, network_config)


def generate_refinement(context: RequestContext, bundle: PromptBundle, network_config: dict[str, Any]) -> dict[str, Any]:
    if context.force_generation_parse_fail:
        return {"candidates": [{"content": {"parts": [{"text": "not-json"}]}}]}
    return get_provider_adapter(context.provider_id).generate_refinement(context, bundle, network_config)


def test_provider_connectivity(
    provider_id: str,
    model: str,
    api_key: str,
    network_config: dict[str, Any],
) -> ProviderTestResult:
    return get_provider_adapter(provider_id).test_connectivity(model, api_key, network_config)
