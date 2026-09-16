"""Select LanguageInterface providers for ANNE web runtime.

Providers are expression tools only. Cognitive authority stays in CognitiveConversation.
"""

from __future__ import annotations

import os
from typing import Any


class ProviderConfigurationError(RuntimeError):
    """Raised when no supported language provider is configured."""


def create_language_provider() -> Any:
    """Instantiate the configured language provider (openai|xai|openrouter|gemini)."""
    provider_name = os.getenv("ANNE_WEB_PROVIDER", "").strip().lower()
    if provider_name in {"chatgpt"}:
        provider_name = "openai"
    if provider_name in {"grok"}:
        provider_name = "xai"

    if provider_name == "openai":
        from anne.providers.openai_provider import OpenAIProvider

        return OpenAIProvider()
    if provider_name == "xai":
        from anne.providers.xai_provider import XAIProvider

        return XAIProvider()
    if provider_name == "openrouter":
        from anne.providers.openrouter import OpenRouterProvider

        return OpenRouterProvider()
    if provider_name == "gemini":
        from anne.providers.gemini import GeminiProvider

        return GeminiProvider()

    raise ProviderConfigurationError(
        "ANNE_WEB_PROVIDER must be one of: openai, xai, openrouter, gemini "
        "(aliases: chatgpt, grok). Ollama is not a V1 cognitive engine."
    )


__all__ = ["ProviderConfigurationError", "create_language_provider"]
