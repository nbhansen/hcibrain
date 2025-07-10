"""LLM Provider port interface for domain layer."""

from abc import ABC, abstractmethod


class LLMProviderPort(ABC):
    """
    Port interface for LLM providers in hexagonal architecture.

    This interface defines the contract that infrastructure adapters must implement
    to provide LLM services to the domain layer. The domain layer depends only on
    this abstraction, not on concrete implementations.
    """

    @abstractmethod
    async def generate_markup(self, text: str) -> str:
        """
        Generate HTML markup for paper text with goals, methods, and results.

        Args:
            text: The paper text to markup

        Returns:
            Text with HTML markup tags for highlights
        """
