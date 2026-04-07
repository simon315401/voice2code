from __future__ import annotations

import os


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_DIR = os.path.join(BASE_DIR, "config")
CONFIG_FILE = os.path.join(CONFIG_DIR, "voice2code_refiner_config.json")
APP_SUPPORT_DIR = os.path.expanduser("~/Library/Application Support/Voice2Code")
GLOSSARY_FILE = os.path.join(APP_SUPPORT_DIR, "terminology_glossary.json")

DEFAULT_PROVIDER_ID = "gemini"

PROVIDERS: dict[str, dict[str, str]] = {
    "gemini": {
        "provider_id": "gemini",
        "api_style": "gemini_generate_content",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "intent_model": "gemini-3.1-flash-lite-preview",
        "generation_model": "gemini-3.1-flash-lite-preview",
        "keychain_service": "Voice2Code.GeminiAPIKey",
        "keychain_account": "default",
        "display_name": "Gemini",
    },
    "openai": {
        "provider_id": "openai",
        "api_style": "openai_chat_completions",
        "base_url": "https://api.openai.com/v1",
        "intent_model": "gpt-5.4-nano",
        "generation_model": "gpt-5.4-nano",
        "keychain_service": "Voice2Code.OpenAIAPIKey",
        "keychain_account": "default",
        "display_name": "OpenAI",
    },
    "doubao": {
        "provider_id": "doubao",
        "api_style": "openai_chat_completions",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "intent_model": "doubao-seed-1-6-250615",
        "generation_model": "doubao-seed-1-6-250615",
        "keychain_service": "Voice2Code.DoubaoAPIKey",
        "keychain_account": "default",
        "display_name": "Doubao",
    },
}

MODEL = PROVIDERS[DEFAULT_PROVIDER_ID]["generation_model"]
INTENT_MODEL = PROVIDERS[DEFAULT_PROVIDER_ID]["intent_model"]
GENERATION_MODEL = PROVIDERS[DEFAULT_PROVIDER_ID]["generation_model"]

LOG_FILE = "/tmp/Voice2Code_debug.jsonl"
LOG_DIR = "/tmp/Voice2Code_logs"

KEYCHAIN_SERVICE = PROVIDERS[DEFAULT_PROVIDER_ID]["keychain_service"]
KEYCHAIN_ACCOUNT = PROVIDERS[DEFAULT_PROVIDER_ID]["keychain_account"]
