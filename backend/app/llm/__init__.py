"""LLM layer — routes to the configured provider (OpenRouter or SAP AI Core)."""
from __future__ import annotations

from app.config import llm_provider as _default_llm_provider


def explain(prompt: str, llm_provider: str | None = None) -> str:
    """Route to the correct LLM explain function based on provider."""
    provider = llm_provider or _default_llm_provider()
    if provider == "sap_ai_core":
        from app.llm import sap_ai_core
        return sap_ai_core.explain(prompt)
    from app.llm import openrouter
    return openrouter.explain(prompt)


def suggest_workflow(
    description: str,
    file_profiles: list,
    engine_library: dict | None = None,
    llm_provider: str | None = None,
) -> dict:
    """Route to the correct LLM suggest_workflow function based on provider."""
    provider = llm_provider or _default_llm_provider()
    if provider == "sap_ai_core":
        from app.llm import sap_ai_core
        return sap_ai_core.suggest_workflow(description, file_profiles, engine_library)
    from app.llm import openrouter
    return openrouter.suggest_workflow(description, file_profiles, engine_library)