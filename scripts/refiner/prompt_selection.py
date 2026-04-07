from __future__ import annotations

from typing import Any

from .config_loader import resolve_prompt_contracts
from .protocols import IntentAnalysisResult, PromptSelection, RequestContext


def build_prompt_selection(context: RequestContext, intent_result: IntentAnalysisResult, config: dict[str, Any]) -> PromptSelection:
    contract_config = resolve_prompt_contracts(config, context.contract_language)["generation_contract"]
    scene_policies = contract_config["scene_policies"]
    rewrite_policies = contract_config["rewrite_policies"]
    structure_policies = contract_config["structure_policies"]

    scene_id = intent_result.main_scene
    rewrite_id = context.forced_rewrite_strategy or "clarify"
    structure_id = intent_result.structure_mode

    if scene_id not in scene_policies:
        raise RuntimeError(f"prompt_selection_failed: unknown main_scene={intent_result.main_scene}")
    if rewrite_id not in rewrite_policies:
        raise RuntimeError(f"prompt_selection_failed: unknown rewrite_strategy={rewrite_id}")
    if structure_id not in structure_policies:
        raise RuntimeError(f"prompt_selection_failed: unknown structure_mode={intent_result.structure_mode}")

    return PromptSelection(
        scene_id=scene_id,
        rewrite_id=rewrite_id,
        structure_id=structure_id,
        scene_instruction=str(scene_policies[scene_id]["instruction"]),
        rewrite_instruction=str(rewrite_policies[rewrite_id]["instruction"]),
        structure_instruction=str(structure_policies[structure_id]["instruction"]),
    )
