"""LLM Provider port interface for domain layer."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class LLMProviderPort(ABC):
    """
    Port interface for LLM providers in hexagonal architecture.

    This interface defines the contract that infrastructure adapters must implement
    to provide LLM services to the domain layer. The domain layer depends only on
    this abstraction, not on concrete implementations.
    """

    @abstractmethod
    async def generate_markup(
        self,
        text: str,
        paper_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate markup for paper text with goals, methods, and results.

        Args:
            text: The paper text to markup
            paper_id: Unique identifier for the paper
            context: Additional context for markup generation

        Returns:
            Dictionary containing:
            - paper_full_text_with_markup: Text with inline markup tags
            - plain_language_summary: Summary for non-researchers
            - confidence_scores: Confidence metrics for markup quality
        """

    @abstractmethod
    def get_model_name(self) -> str:
        """
        Get the name of the underlying model being used.

        Returns:
            Model name string
        """

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the LLM provider is available and properly configured.

        Returns:
            True if available, False otherwise
        """
