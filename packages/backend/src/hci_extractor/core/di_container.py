"""Dependency injection container for the HCI extractor."""

import logging
import threading
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, Type, TypeVar, Union

if TYPE_CHECKING:
    from hci_extractor.core.config import ExtractorConfig
    from hci_extractor.prompts.markup_prompt_loader import MarkupPromptLoader

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

    def __init__(self, config: Optional["ExtractorConfig"] = None) -> None:
        """Initialize DI container with optional configuration.
        
        Following hexagonal architecture - config is injected, not accessed globally.
        All dependencies must be explicit and immutable.
        """
        self._services: Dict[Type[Any], ServiceDescriptor] = {}
        self._singletons: Dict[Type[Any], Any] = {}
        self._resolving = threading.local()  # Thread-local circular dependency tracking
        self._lock = threading.RLock()  # Thread-safe operations
        self.config = config  # Store config for service creation
        
        # Auto-configure services if config provided
        if config is not None:
            self._configure_default_services()

    def register_singleton(
        self,
        service_type: Type[T],
        implementation: Union[Type[T], Callable[..., T]],
    ) -> None:
        """Register a singleton service."""
        self._services[service_type] = ServiceDescriptor(
            service_type,
            implementation,
            ServiceLifetime.SINGLETON,
        )

    def register_transient(
        self,
        service_type: Type[T],
        implementation: Union[Type[T], Callable[..., T]],
    ) -> None:
        """Register a transient service."""
        self._services[service_type] = ServiceDescriptor(
            service_type,
            implementation,
            ServiceLifetime.TRANSIENT,
        )

    def register_factory(
        self,
        service_type: Type[T],
        factory: Callable[..., T],
        lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT,
    ) -> None:
        """Register a service with a factory function."""
        self._services[service_type] = ServiceDescriptor(
            service_type,
            factory,
            lifetime,
            factory,
        )

    def register_instance(self, service_type: Type[T], instance: T) -> None:
        """Register a specific instance as a singleton."""
        self._services[service_type] = ServiceDescriptor(
            service_type,
            type(instance),
            ServiceLifetime.SINGLETON,
        )
        self._singletons[service_type] = instance

    def resolve(self, service_type: Type[T]) -> T:
        """Resolve a service instance with thread safety."""
        with self._lock:
            # Initialize thread-local resolving set if needed
            if not hasattr(self._resolving, 'resolving_set'):
                self._resolving.resolving_set = set()

            if service_type in self._resolving.resolving_set:
                raise ValueError(f"Circular dependency detected for {service_type}")

            if service_type not in self._services:
                raise ValueError(f"Service {service_type} not registered")

            descriptor = self._services[service_type]

            # Check if it's a singleton and already created
            if descriptor.lifetime == ServiceLifetime.SINGLETON:
                if service_type in self._singletons:
                    return self._singletons[service_type]  # type: ignore

            # Create the instance
            self._resolving.resolving_set.add(service_type)
            try:
                instance = self._create_instance(descriptor)

                # Store singleton
                if descriptor.lifetime == ServiceLifetime.SINGLETON:
                    self._singletons[service_type] = instance

                return instance  # type: ignore
            finally:
                self._resolving.resolving_set.discard(service_type)

    def _create_instance(self, descriptor: ServiceDescriptor) -> Any:
        """Create an instance from a service descriptor."""
        if descriptor.factory:
            # Use factory function
            return self._call_with_injection(descriptor.factory)
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
        with self._lock:
            self._services.clear()
            self._singletons.clear()
            # Clear thread-local data if it exists
            if hasattr(self._resolving, 'resolving_set'):
                self._resolving.resolving_set.clear()

    # TDD-compatible interface methods
    def get_event_bus(self) -> "EventBus":
        """Get EventBus singleton - TDD interface."""
        from hci_extractor.core.events import EventBus
        return self.resolve(EventBus)

    def get_llm_provider(self) -> "LLMProvider":
        """Get LLM provider based on configuration - TDD interface."""
        from hci_extractor.providers.base import LLMProvider
        # Return the actual provider (e.g., GeminiProvider)
        return self.resolve(LLMProvider)

    def get_markup_prompt_loader(self) -> "MarkupPromptLoader":
        """Get markup prompt loader - TDD interface."""
        from hci_extractor.prompts.markup_prompt_loader import MarkupPromptLoader
        return self.resolve(MarkupPromptLoader)

    def cleanup(self) -> None:
        """Clean up resources - TDD interface."""
        # Clean up singletons if they have cleanup methods
        for instance in self._singletons.values():
            if hasattr(instance, 'close') or hasattr(instance, 'cleanup'):
                try:
                    if hasattr(instance, 'close'):
                        instance.close()
                    elif hasattr(instance, 'cleanup'):
                        instance.cleanup()
                except Exception as e:
                    logger.warning(f"Error during cleanup: {e}")
        self.clear()

    def _configure_default_services(self) -> None:
        """Configure default services based on provided config.
        
        Following hexagonal architecture - all dependencies explicit.
        """
        if not self.config:
            return

        # Import here to avoid circular dependencies
        from hci_extractor.core.events import EventBus
        from hci_extractor.providers.gemini_provider import GeminiProvider
        from hci_extractor.providers.provider_config import LLMProviderConfig
        from hci_extractor.prompts.markup_prompt_loader import MarkupPromptLoader
        from hci_extractor.providers.base import LLMProvider

        # Register EventBus as singleton
        self.register_singleton(EventBus, EventBus)

        # Register MarkupPromptLoader as singleton
        def create_prompt_loader() -> MarkupPromptLoader:
            return MarkupPromptLoader(self.config.prompts_directory)
        
        self.register_factory(MarkupPromptLoader, create_prompt_loader, ServiceLifetime.SINGLETON)

        # Register LLM provider based on config
        def create_llm_provider() -> LLMProvider:
            if not self.config:
                raise ValueError("Configuration required for LLM provider")
                
            provider_type = self.config.api.provider_type.lower()
            
            if provider_type == "gemini":
                if not self.config.api.gemini_api_key:
                    raise ValueError("API key required for provider: gemini")
                    
                provider_config = LLMProviderConfig(
                    api_key=self.config.api.gemini_api_key,
                    temperature=self.config.analysis.temperature,
                    max_output_tokens=self.config.analysis.max_output_tokens,
                    max_attempts=self.config.retry.max_attempts,
                    timeout_seconds=self.config.api.timeout_seconds,
                    rate_limit_delay=self.config.api.rate_limit_delay
                )
                
                event_bus = self.resolve(EventBus)
                prompt_loader = self.resolve(MarkupPromptLoader)
                
                return GeminiProvider(
                    provider_config=provider_config,
                    event_bus=event_bus,
                    markup_prompt_loader=prompt_loader,
                    model_name=self.config.analysis.model_name
                )
            elif provider_type == "openai":
                raise NotImplementedError("OpenAI provider not yet implemented")
            else:
                raise ValueError(f"Invalid provider type: {provider_type}")

        # Register both abstract and concrete types
        self.register_factory(LLMProvider, create_llm_provider, ServiceLifetime.SINGLETON)
        self.register_factory(GeminiProvider, create_llm_provider, ServiceLifetime.SINGLETON)


# No global state - container must be passed explicitly through dependency injection


def configure_services(container: DIContainer) -> None:
    """Configure all services in the DI container."""
    from hci_extractor.core.config import ExtractorConfig
    from hci_extractor.core.domain.services import (
        PaperSummaryService,
        SectionAnalysisService,
    )
    from hci_extractor.core.events import EventBus
    from hci_extractor.core.extraction import PdfExtractor
    from hci_extractor.core.ports import LLMProviderPort

    # Register configuration service and configuration as singletons
    from hci_extractor.infrastructure.configuration_service import ConfigurationService
    from hci_extractor.providers import GeminiProvider
    from hci_extractor.utils.retry_handler import RetryHandler

    container.register_singleton(ConfigurationService, ConfigurationService)

    def create_configuration(config_service: ConfigurationService) -> ExtractorConfig:
        config_data = config_service.load_configuration()
        return ExtractorConfig.from_configuration_data(config_data, config_service)

    container.register_factory(
        ExtractorConfig,
        create_configuration,
        ServiceLifetime.SINGLETON,
    )

    # Register event bus as singleton
    container.register_singleton(EventBus, EventBus)

    # Register metrics collector as singleton
    from hci_extractor.core.metrics import MetricsCollector

    container.register_singleton(MetricsCollector, MetricsCollector)

    # Register WebSocket manager as singleton
    from hci_extractor.web.progress import WebSocketManager

    container.register_singleton(WebSocketManager, WebSocketManager)

    # Register UserErrorTranslator as singleton
    from hci_extractor.utils.user_error_translator import UserErrorTranslator

    container.register_singleton(UserErrorTranslator, UserErrorTranslator)

    # Note: ErrorClassifier removed - complex error classification not needed
    # Simple error handling is sufficient for this use case

    # Register markup prompt loader as singleton
    def create_markup_prompt_loader(config: ExtractorConfig) -> "MarkupPromptLoader":
        from hci_extractor.prompts.markup_prompt_loader import MarkupPromptLoader

        prompts_dir = config.prompts_directory
        return MarkupPromptLoader(prompts_dir)

    # Import the actual class for registration
    from hci_extractor.prompts.markup_prompt_loader import MarkupPromptLoader

    container.register_factory(MarkupPromptLoader, create_markup_prompt_loader)

    # Register PDF extractor factory with config dependency
    def create_pdf_extractor(config: ExtractorConfig) -> PdfExtractor:
        return PdfExtractor(config=config)

    container.register_factory(PdfExtractor, create_pdf_extractor)

    # Register retry handler factory that creates instances with dependencies
    def create_retry_handler(event_bus: EventBus) -> RetryHandler:
        return RetryHandler(
            operation_name="default_operation",
            publish_events=True,
            event_bus=event_bus,
        )

    container.register_factory(RetryHandler, create_retry_handler)

    # Register LLM provider factory (configurable based on provider_type)
    def create_llm_provider(
        config: ExtractorConfig,
        event_bus: EventBus,
        markup_prompt_loader: MarkupPromptLoader,
    ) -> LLMProviderPort:
        from hci_extractor.providers.provider_config import (
            ExtractorConfigurationAdapter,
        )

        provider_type = config.api.provider_type.lower()

        if provider_type == "gemini":
            from hci_extractor.providers.gemini_provider import GeminiProvider

            # Create provider-specific configuration adapter
            config_adapter = ExtractorConfigurationAdapter(config)
            provider_config = config_adapter.get_gemini_config()

            return GeminiProvider(
                provider_config=provider_config,
                event_bus=event_bus,
                markup_prompt_loader=markup_prompt_loader,
                model_name=config.analysis.model_name,
            )
        raise ValueError(f"Unsupported provider type: {provider_type}")

    # Register the configurable provider factory for the abstract interface
    container.register_factory(LLMProviderPort, create_llm_provider)

    # Also register GeminiProvider specifically for backward compatibility
    def create_gemini_provider(
        config: ExtractorConfig,
        event_bus: EventBus,
        markup_prompt_loader: "MarkupPromptLoader",
    ) -> GeminiProvider:
        provider = create_llm_provider(
            config,
            event_bus,
            markup_prompt_loader,
        )
        if not isinstance(provider, GeminiProvider):
            raise TypeError(
                "GeminiProvider requested but different provider configured",
            )
        return provider

    container.register_factory(GeminiProvider, create_gemini_provider)

    # Note: LLMSectionProcessor was removed with the analysis module
    # Section processing is now handled directly by domain services

    # Register domain services
    def create_section_analysis_service(
        llm_provider: LLMProviderPort,
        config: ExtractorConfig,
        event_bus: EventBus,
    ) -> SectionAnalysisService:
        return SectionAnalysisService(llm_provider, config, event_bus)

    def create_paper_summary_service(
        llm_provider: LLMProviderPort,
        config: ExtractorConfig,
        event_bus: EventBus,
    ) -> PaperSummaryService:
        return PaperSummaryService(llm_provider, config, event_bus)

    container.register_factory(SectionAnalysisService, create_section_analysis_service)
    container.register_factory(PaperSummaryService, create_paper_summary_service)

    # Register TextProcessingService as singleton (stateless domain service)
    from hci_extractor.core.domain.text_processing_service import TextProcessingService

    container.register_singleton(TextProcessingService, TextProcessingService)


def create_configured_container() -> DIContainer:
    """Create and configure a new DI container."""
    container = DIContainer()
    configure_services(container)
    return container
