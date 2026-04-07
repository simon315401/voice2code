from __future__ import annotations

import re


_ZH_CHAR_PATTERN = re.compile(r"[\u4e00-\u9fff]")
_EN_WORD_PATTERN = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")

_ENGLISH_OVERRIDE_PATTERNS = (
    re.compile(r"\b(reply|respond|answer|write|output)\s+in\s+english\b", re.IGNORECASE),
    re.compile(r"\buse\s+english\b", re.IGNORECASE),
    re.compile(r"(请|请你)?用英文(回复|回答|输出|写)"),
    re.compile(r"英文(回复|回答|输出)"),
)

_CHINESE_OVERRIDE_PATTERNS = (
    re.compile(r"\b(reply|respond|answer|write|output)\s+in\s+chinese\b", re.IGNORECASE),
    re.compile(r"\buse\s+chinese\b", re.IGNORECASE),
    re.compile(r"(请|请你)?用中文(回复|回答|输出|写)"),
    re.compile(r"中文(回复|回答|输出)"),
)


def detect_input_language(text: str) -> str:
    zh_chars = len(_ZH_CHAR_PATTERN.findall(text))
    en_words = len(_EN_WORD_PATTERN.findall(text))

    if zh_chars == 0 and en_words == 0:
        return "zh-CN"
    if zh_chars > 0 and en_words == 0:
        return "zh-CN"
    if en_words > 0 and zh_chars == 0:
        return "en-US"
    if zh_chars >= en_words * 1.2:
        return "zh-CN"
    if en_words >= zh_chars * 1.2:
        return "en-US"
    return "zh-CN"


def detect_explicit_output_language(text: str) -> str:
    if any(pattern.search(text) for pattern in _ENGLISH_OVERRIDE_PATTERNS):
        return "en-US"
    if any(pattern.search(text) for pattern in _CHINESE_OVERRIDE_PATTERNS):
        return "zh-CN"
    return ""


def resolve_contract_language(
    text: str,
    *,
    default_language: str = "zh-CN",
    fallback_language: str = "zh-CN",
) -> tuple[str, str]:
    input_language = detect_input_language(text)
    explicit_language = detect_explicit_output_language(text)
    if explicit_language:
        return input_language, explicit_language
    if input_language in {"zh-CN", "en-US"}:
        return input_language, input_language
    if default_language in {"zh-CN", "en-US"}:
        return input_language, default_language
    return input_language, fallback_language
