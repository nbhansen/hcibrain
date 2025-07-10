"""Domain ports (interfaces) for hexagonal architecture."""

from hci_extractor.core.ports.configuration_port import ConfigurationPort
from hci_extractor.core.ports.llm_provider_port import LLMProviderPort

__all__ = [
    "ConfigurationPort",
    "LLMProviderPort",
]
