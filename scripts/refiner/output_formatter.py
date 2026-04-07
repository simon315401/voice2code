from __future__ import annotations

from .protocols import GenerationResult, OutputResult


def apply_output_formatter(generation_result: GenerationResult) -> OutputResult:
    return OutputResult(final_output=generation_result.refined_text, applied_rules=[])
