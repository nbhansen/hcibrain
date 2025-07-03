"""LLM provider abstractions and implementations."""

from .base import LLMProvider

__all__ = ["LLMProvider"]

# Try to import providers with optional dependencies
try:
    from .gemini_provider import GeminiProvider
    __all__.append("GeminiProvider")
except ImportError:
    # GeminiProvider requires google-generativeai dependency
    # This allows the base LLM classes to be imported without it
    pass