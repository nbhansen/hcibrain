"""Dependency injection container for the HCI extractor."""

import asyncio
import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Callable, Dict, Optional, Type, TypeVar, Union

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ServiceLifetime(Enum):
    """Service lifetime management."""

    SINGLETON = "singleton"
    TRANSIENT = "transient"


class ServiceDescriptor:
    """Describes how to create a service."""

    def __init__(
        self,
        service_type: Type[T],
        implementation: Union[Type[T], Callable[..., T]],
        lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT,
        factory: Optional[Callable[..., T]] = None,
    ):
        self.service_type = service_type
        self.implementation = implementation
        self.lifetime = lifetime
        self.factory = factory


class DIContainer:
    """Dependency injection container."""

    def __init__(self) -> None:
        self._services: Dict[Type[Any], ServiceDescriptor] = {}
        self._singletons: Dict[Type[Any], Any] = {}
        self._resolving: set[Type[Any]] = set()  # Track circular dependency resolution

    def register_singleton(
        self, service_type: Type[T], implementation: Union[Type[T], Callable[..., T]]
    ) -> None:
        """Register a singleton service."""
        self._services[service_type] = ServiceDescriptor(
            service_type, implementation, ServiceLifetime.SINGLETON
        )

    def register_transient(
        self, service_type: Type[T], implementation: Union[Type[T], Callable[..., T]]
    ) -> None:
        """Register a transient service."""
        self._services[service_type] = ServiceDescriptor(
            service_type, implementation, ServiceLifetime.TRANSIENT
        )

    def register_factory(
        self,
        service_type: Type[T],
        factory: Callable[..., T],
        lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT,
    ) -> None:
        """Register a service with a factory function."""
        self._services[service_type] = ServiceDescriptor(
            service_type, factory, lifetime, factory
        )

    def register_instance(self, service_type: Type[T], instance: T) -> None:
        """Register a specific instance as a singleton."""
        self._services[service_type] = ServiceDescriptor(
            service_type, type(instance), ServiceLifetime.SINGLETON
        )
        self._singletons[service_type] = instance

    def resolve(self, service_type: Type[T]) -> T:
        """Resolve a service instance."""
        if service_type in self._resolving:
            raise ValueError(f"Circular dependency detected for {service_type}")

        if service_type not in self._services:
            raise ValueError(f"Service {service_type} not registered")

        descriptor = self._services[service_type]

        # Check if it's a singleton and already created
        if descriptor.lifetime == ServiceLifetime.SINGLETON:
            if service_type in self._singletons:
                return self._singletons[service_type]  # type: ignore

        # Create the instance
        self._resolving.add(service_type)
        try:
            instance = self._create_instance(descriptor)

            # Store singleton
            if descriptor.lifetime == ServiceLifetime.SINGLETON:
                self._singletons[service_type] = instance

            return instance  # type: ignore
        finally:
            self._resolving.discard(service_type)

    def _create_instance(self, descriptor: ServiceDescriptor) -> Any:
        """Create an instance from a service descriptor."""
        if descriptor.factory:
            # Use factory function
            return self._call_with_injection(descriptor.factory)
        else:
            # Use constructor
            return self._call_with_injection(descriptor.implementation)

    def _call_with_injection(self, callable_obj: Callable[..., Any]) -> Any:
        """Call a function/constructor with dependency injection."""
        import inspect

        # Get the signature
        sig = inspect.signature(callable_obj)

        # Resolve dependencies
        kwargs = {}
        for param_name, param in sig.parameters.items():
            if param.annotation != inspect.Parameter.empty:
                # Try to resolve the parameter type
                try:
                    kwargs[param_name] = self.resolve(param.annotation)
                except ValueError:
                    # If we can't resolve it, skip it (might be a primitive type)
                    pass

        return callable_obj(**kwargs)

    def is_registered(self, service_type: Type[Any]) -> bool:
        """Check if a service is registered."""
        return service_type in self._services

    def clear(self) -> None:
        """Clear all registrations and singletons."""
        self._services.clear()
        self._singletons.clear()
        self._resolving.clear()


# Application-level container instance - centralized service management
# All services are registered and resolved through this container
_container: Optional[DIContainer] = None


def get_container() -> DIContainer:
    """Get the global DI container."""
    global _container
    if _container is None:
        _container = DIContainer()
    return _container


def configure_services(container: DIContainer) -> None:
    """Configure all services in the DI container."""
    from hci_extractor.core.config import ExtractorConfig
    from hci_extractor.core.events import EventBus
    from hci_extractor.core.extraction import PdfExtractor
    from hci_extractor.prompts import PromptManager
    from hci_extractor.providers import GeminiProvider, LLMProvider
    from hci_extractor.utils.retry_handler import RetryHandler
    from hci_extractor.core.domain.services import (
        SectionAnalysisService,
        PaperSummaryService,
    )

    # Register configuration as singleton
    container.register_factory(
        ExtractorConfig, lambda: ExtractorConfig.from_env(), ServiceLifetime.SINGLETON
    )

    # Register event bus as singleton
    container.register_singleton(EventBus, EventBus)

    # Register prompt manager as singleton
    container.register_singleton(PromptManager, PromptManager)

    # Register PDF extractor factory with config dependency
    def create_pdf_extractor(config: ExtractorConfig) -> PdfExtractor:
        return PdfExtractor(config=config)

    container.register_factory(PdfExtractor, create_pdf_extractor)

    # Register retry handler factory that creates instances with dependencies
    def create_retry_handler(event_bus: EventBus) -> RetryHandler:
        return RetryHandler(
            operation_name="default_operation", publish_events=True, event_bus=event_bus
        )

    container.register_factory(RetryHandler, create_retry_handler)

    # Register LLM provider factory (GeminiProvider implementation)
    def create_gemini_provider(
        config: ExtractorConfig, event_bus: EventBus, prompt_manager: PromptManager
    ) -> GeminiProvider:
        return GeminiProvider(
            config=config, event_bus=event_bus, prompt_manager=prompt_manager
        )

    # Register as both the concrete type and the interface
    container.register_factory(GeminiProvider, create_gemini_provider)
    # Note: LLMProvider is abstract, register concrete implementation
    container.register_factory(LLMProvider, create_gemini_provider)  # type: ignore

    # Register LLMSectionProcessor factory
    # Register LLMSectionProcessor factory
    def create_section_processor(
        llm_provider: LLMProvider, config: ExtractorConfig, event_bus: EventBus
    ) -> Any:  # Using Any to avoid circular import
        from hci_extractor.core.analysis import LLMSectionProcessor

        return LLMSectionProcessor(llm_provider, config, event_bus)

    # Use the actual class after import
    from hci_extractor.core.analysis import LLMSectionProcessor

    container.register_factory(LLMSectionProcessor, create_section_processor)

    # Register domain services
    def create_section_analysis_service(
        llm_provider: LLMProvider, config: ExtractorConfig, event_bus: EventBus
    ) -> SectionAnalysisService:
        return SectionAnalysisService(llm_provider, config, event_bus)

    def create_paper_summary_service(
        llm_provider: LLMProvider, config: ExtractorConfig, event_bus: EventBus
    ) -> PaperSummaryService:
        return PaperSummaryService(llm_provider, config, event_bus)

    container.register_factory(SectionAnalysisService, create_section_analysis_service)
    container.register_factory(PaperSummaryService, create_paper_summary_service)


def setup_container() -> DIContainer:
    """Set up and configure the DI container."""
    container = get_container()
    configure_services(container)
    return container
