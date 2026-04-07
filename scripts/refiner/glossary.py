from __future__ import annotations

import json
import os
from typing import Any

from .config_loader import APP_SUPPORT_DIR, DEFAULT_GLOSSARY, GLOSSARY_FILE, resolve_prompt_contracts
from .protocols import GlossaryResult, RequestContext


def ensure_glossary_file() -> str:
    os.makedirs(APP_SUPPORT_DIR, exist_ok=True)
    if not os.path.exists(GLOSSARY_FILE):
        with open(GLOSSARY_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_GLOSSARY, f, ensure_ascii=False, indent=2)
            f.write("\n")
    return GLOSSARY_FILE


def load_glossary_entries(glossary_file: str) -> tuple[dict[str, Any], str]:
    entries: dict[str, Any] = {}
    warning = ""
    if glossary_file:
        try:
            with open(glossary_file, "r", encoding="utf-8") as gf:
                loaded = json.load(gf)
            if isinstance(loaded, dict):
                entries = loaded
        except Exception:
            entries = {}
            warning = "invalid_glossary_json"
    return entries, warning


def select_glossary_entries(cleaned_input: str, entries: dict[str, Any], glossary_mode: str, glossary_max_entries: int) -> list[tuple[str, str]]:
    selected_entries: list[tuple[str, str]] = []
    if glossary_mode == "off":
        return selected_entries
    if glossary_mode == "full":
        for canonical, meta in entries.items():
            aliases = meta.get("aliases") if isinstance(meta, dict) else []
            aliases = aliases if isinstance(aliases, list) else []
            selected_entries.append((aliases[0] if aliases else canonical, canonical))
            if len(selected_entries) >= glossary_max_entries:
                break
        return selected_entries

    for canonical, meta in entries.items():
        if len(selected_entries) >= glossary_max_entries:
            break
        if not isinstance(meta, dict):
            continue
        aliases = meta.get("aliases") or []
        case_sensitive = bool(meta.get("case_sensitive", False))
        haystack = cleaned_input if case_sensitive else cleaned_input.lower()
        for alias in aliases:
            if not isinstance(alias, str) or not alias:
                continue
            needle = alias if case_sensitive else alias.lower()
            if needle in haystack:
                selected_entries.append((alias, canonical))
                break
    return selected_entries


def match_glossary(context: RequestContext, glossary_file: str, config: dict[str, Any]) -> GlossaryResult:
    glossary_config = resolve_prompt_contracts(config, context.contract_language)["generation_contract"]["glossary"]
    entries, warning = load_glossary_entries(glossary_file)
    selected_entries = select_glossary_entries(
        context.input_text,
        entries,
        context.glossary_mode,
        context.glossary_max_entries,
    )
    if selected_entries:
        glossary_lines = "\n".join(f"- {alias} -> {canonical}" for alias, canonical in selected_entries)
        glossary_hint_text = f"【{glossary_config['title']}】\n{glossary_lines}"
    else:
        glossary_hint_text = f"【{glossary_config['title']}】\n- {glossary_config['empty_text']}"

    if warning:
        glossary_hint_text += f"\n\n【{glossary_config['status_title']}】\n- {warning}"

    return GlossaryResult(
        selected_entries=selected_entries,
        selected_count=len(selected_entries),
        glossary_hint_text=glossary_hint_text,
        warning=warning,
    )
