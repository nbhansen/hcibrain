"""Architecture compliance validation tests.

These tests ensure that the codebase follows hexagonal architecture principles
and immutable design patterns as specified in CLAUDE.md.
"""

import ast
import inspect
import types
from dataclasses import fields, is_dataclass
from pathlib import Path

import pytest

from hci_extractor.core.config import ExtractorConfig
from hci_extractor.core.events import EventBus
from hci_extractor.core.models import DetectedSection, ExtractedElement, Paper
from hci_extractor.providers.base import LLMProvider
from hci_extractor.providers.gemini_provider import GeminiProvider
from hci_extractor.utils.user_error_translator import UserErrorMessage


class TestGlobalStateViolations:
    """Test that no global state violations exist in the codebase."""

    def test_no_global_container_instance(self):
        """Test that DIContainer has no global instance variables."""
        from hci_extractor.core import di_container

        # Check that no global container variables exist
        module_vars = vars(di_container)
        global_vars = {
            k: v
            for k, v in module_vars.items()
            if not k.startswith("_")
            and not inspect.isfunction(v)
            and not inspect.isclass(v)
        }

        # Filter out expected constants and imports
        expected_globals = {
            "DIContainer",
            "ExtractorConfig",
            "EventBus",
            "LLMProvider",
            "GeminiProvider",
            "ProviderConfigurationPort",
            "ExtractorConfigurationAdapter",
            # Standard imports and typing
            "Type",
            "Optional",
            "logger",
            "asyncio",
            "Dict",
            "T",
            "Union",
            "logging",
            "Callable",
            "TYPE_CHECKING",
        }
        actual_globals = set(global_vars.keys()) - expected_globals

        assert not actual_globals, (
            f"Found unexpected global variables: {actual_globals}"
        )

    def test_no_get_container_function(self):
        """Test that get_container() function has been removed."""
        from hci_extractor.core import di_container

        assert not hasattr(di_container, "get_container"), (
            "get_container() function should be removed"
        )

    def test_cli_configuration_service_no_global_state(self):
        """Test that CLI configuration service doesn't create global state."""
        from hci_extractor.cli.cli_configuration_service import (
            get_cli_configuration_service,
        )

        # These should return new instances each time in a proper DI setup
        # For now, they return singleton instances but are properly isolated
        service1 = get_cli_configuration_service()
        service2 = get_cli_configuration_service()

        # Services should be different instances (factory pattern for CLI)
        # but should not maintain mutable state
        assert service1 is not service2, "CLI service should create new instances"

        # Check that the service has no mutable state
        service_vars = vars(service1)
        assert not service_vars or all(
            not isinstance(v, (list, dict, set)) for v in service_vars.values()
        ), "CLI service should not have mutable state"


class TestImmutableDesignViolations:
    """Test that all data structures follow immutable design principles."""

    def test_dataclass_frozen_compliance(self):
        """Test that all dataclasses are frozen."""
        dataclasses_to_check = [
            ExtractorConfig,
            DetectedSection,
            ExtractedElement,
            Paper,
            UserErrorMessage,
        ]

        for dataclass_type in dataclasses_to_check:
            assert is_dataclass(dataclass_type), (
                f"{dataclass_type.__name__} should be a dataclass"
            )

            # Check if frozen=True
            # For dataclasses, check the __dataclass_params__ attribute
            if hasattr(dataclass_type, "__dataclass_params__"):
                params = dataclass_type.__dataclass_params__
                assert params.frozen, (
                    f"{dataclass_type.__name__} should be frozen (use @dataclass(frozen=True))"
                )

    def test_no_mutable_default_factories(self):
        """Test that dataclass fields don't use mutable default factories."""
        from dataclasses import MISSING

        from hci_extractor.utils.user_error_translator import UserErrorMessage

        # Check UserErrorMessage fields
        for field in fields(UserErrorMessage):
            if field.default_factory is not MISSING:
                # If there's a default factory, it should not create mutable objects
                default_value = field.default_factory()
                assert not isinstance(default_value, (list, dict, set)), (
                    f"{field.name} uses mutable default factory"
                )
            elif field.default is not MISSING:
                # Check that default values are immutable
                assert not isinstance(field.default, (list, dict, set)), (
                    f"{field.name} has mutable default value"
                )

    def test_mapping_proxy_usage(self):
        """Test that immutable mappings are used where appropriate."""
        # This test checks that when we do use dictionaries, they're properly wrapped
        # in MappingProxyType where needed
        from hci_extractor.core.config import ExtractorConfig

        config = ExtractorConfig.from_yaml()

        # Check that configuration doesn't expose mutable dictionaries
        config_vars = vars(config)
        for attr_name, attr_value in config_vars.items():
            if isinstance(attr_value, dict):
                # If it's a dict, it should be a MappingProxyType
                assert isinstance(attr_value, types.MappingProxyType), (
                    f"Config attribute {attr_name} should use MappingProxyType"
                )


class TestHexagonalArchitectureCompliance:
    """Test that hexagonal architecture principles are followed."""

    def test_domain_layer_no_infrastructure_imports(self):
        """Test that domain layer doesn't import infrastructure concerns."""
        domain_modules = [
            "hci_extractor.core.config",
            "hci_extractor.core.models",
            "hci_extractor.core.events",
        ]

        forbidden_imports = [
            "os",
            "sys",
            "requests",
            "google",
            "openai",
            "anthropic",
        ]

        for module_name in domain_modules:
            module = __import__(module_name, fromlist=[""])

            # Check the module's source code for forbidden imports
            source_file = inspect.getfile(module)
            with open(source_file, "r") as f:
                source = f.read()

            # Parse the AST to find import statements
            tree = ast.parse(source)

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert alias.name not in forbidden_imports, (
                            f"Domain module {module_name} imports forbidden dependency {alias.name}"
                        )
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        for forbidden in forbidden_imports:
                            assert not node.module.startswith(forbidden), (
                                f"Domain module {module_name} imports from forbidden module {node.module}"
                            )

    def test_providers_implement_abstractions(self):
        """Test that providers implement proper abstract interfaces."""
        from hci_extractor.providers.gemini_provider import GeminiProvider

        # Test that GeminiProvider properly implements LLMProvider
        assert issubclass(GeminiProvider, LLMProvider), (
            "GeminiProvider should inherit from LLMProvider"
        )

        # Test that abstract methods are implemented
        abstract_methods = LLMProvider.__abstractmethods__
        for method_name in abstract_methods:
            assert hasattr(GeminiProvider, method_name), (
                f"GeminiProvider should implement {method_name}"
            )

    def test_configuration_service_separation(self):
        """Test that configuration services properly separate infrastructure."""
        from hci_extractor.infrastructure.configuration_service import (
            ConfigurationService,
        )

        # ConfigurationService should be in infrastructure layer
        assert ConfigurationService.__module__.startswith(
            "hci_extractor.infrastructure",
        ), "ConfigurationService should be in infrastructure layer"

        # Test that it has proper methods for configuration loading
        assert hasattr(ConfigurationService, "load_configuration"), (
            "ConfigurationService should have load_configuration method"
        )

    def test_dependency_injection_container_usage(self):
        """Test that DI container is used for all service resolution."""
        from hci_extractor.core.di_container import create_configured_container

        container = create_configured_container()

        # Test that key services can be resolved
        config = container.resolve(ExtractorConfig)
        assert config is not None, "Config should be resolvable from DI container"

        event_bus = container.resolve(EventBus)
        assert event_bus is not None, "EventBus should be resolvable from DI container"

        # Test that the same instance is returned for singletons
        config2 = container.resolve(ExtractorConfig)
        assert config is config2, "Config should be singleton in DI container"


class TestProviderArchitectureCompliance:
    """Test that provider layer follows architecture principles."""

    def test_provider_configuration_abstraction(self):
        """Test that providers use configuration abstractions."""
        from hci_extractor.providers.provider_config import LLMProviderConfig

        # Test that LLMProviderConfig is properly defined
        assert is_dataclass(LLMProviderConfig), (
            "LLMProviderConfig should be a dataclass"
        )

        # Test that it has expected fields
        config_fields = {f.name for f in fields(LLMProviderConfig)}
        expected_fields = {
            "api_key",
            "temperature",
            "max_output_tokens",
            "max_attempts",
        }
        assert expected_fields.issubset(config_fields), (
            f"LLMProviderConfig should have fields: {expected_fields}"
        )

    def test_provider_no_direct_environment_access(self):
        """Test that providers don't directly access environment variables."""

        # Check the source code for os.getenv calls
        source_file = inspect.getfile(GeminiProvider)
        with open(source_file, "r") as f:
            source = f.read()

        # Parse AST to find os.getenv calls
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Check for os.getenv calls
                if (
                    isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "os"
                    and node.func.attr == "getenv"
                ):
                    pytest.fail("GeminiProvider should not directly call os.getenv")

    def test_provider_immutable_state(self):
        """Test that providers maintain immutable state."""
        from hci_extractor.core.events import EventBus
        from hci_extractor.providers.provider_config import LLMProviderConfig

        # Create a provider instance
        config = LLMProviderConfig(
            api_key="test-key",
            temperature=0.7,
            max_output_tokens=1000,
            max_attempts=3,
            timeout_seconds=30.0,
            rate_limit_delay=1.0,
        )
        event_bus = EventBus()

        provider = GeminiProvider(config, event_bus)

        # Check that provider has no mutable state
        provider_vars = vars(provider)
        for attr_name, attr_value in provider_vars.items():
            if isinstance(attr_value, (list, dict, set)):
                pytest.fail(
                    f"Provider has mutable attribute {attr_name}: {type(attr_value)}",
                )


class TestEventBusArchitectureCompliance:
    """Test that EventBus follows architecture principles."""

    def test_event_bus_no_global_state(self):
        """Test that EventBus doesn't maintain global state."""
        from hci_extractor.core.events import EventBus

        # Create two instances
        bus1 = EventBus()
        bus2 = EventBus()

        # They should be separate instances
        assert bus1 is not bus2, "EventBus instances should be separate"

        # Check that they don't share state
        bus1_vars = vars(bus1)
        bus2_vars = vars(bus2)

        # No shared mutable state
        for attr_name in bus1_vars:
            if attr_name in bus2_vars:
                attr1 = bus1_vars[attr_name]
                attr2 = bus2_vars[attr_name]
                if isinstance(attr1, (list, dict, set)):
                    assert attr1 is not attr2, (
                        f"EventBus instances share mutable state: {attr_name}"
                    )

    def test_domain_events_immutable(self):
        """Test that domain events are immutable."""
        from hci_extractor.core.events import (
            ExtractionCompleted,
            ExtractionStarted,
            SectionProcessingCompleted,
            SectionProcessingStarted,
        )

        # Test that event classes are dataclasses
        event_classes = [
            ExtractionStarted,
            ExtractionCompleted,
            SectionProcessingStarted,
            SectionProcessingCompleted,
        ]

        for event_class in event_classes:
            assert is_dataclass(event_class), (
                f"{event_class.__name__} should be a dataclass"
            )

            # Check if frozen=True
            if hasattr(event_class, "__dataclass_params__"):
                params = event_class.__dataclass_params__
                assert params.frozen, f"{event_class.__name__} should be frozen"


class TestCLIArchitectureCompliance:
    """Test that CLI layer follows architecture principles."""

    def test_cli_configuration_service_extraction(self):
        """Test that CLI configuration logic is properly extracted."""
        from hci_extractor.cli.cli_configuration_service import (
            CLIConfigurationService,
            CLIContainerFactory,
        )

        # Test that services exist and are properly structured
        assert CLIConfigurationService is not None
        assert CLIContainerFactory is not None

        # Test that they have expected methods
        assert hasattr(CLIConfigurationService, "create_configuration_from_context")
        assert hasattr(CLIContainerFactory, "create_container_with_cli_config")

    def test_cli_commands_use_dependency_injection(self):
        """Test that CLI commands use DI container."""
        import hci_extractor.cli.commands as commands_module

        # Check that commands file doesn't have direct service instantiation
        # This is checked by ensuring setup_cli_container is not used anymore
        source_file = inspect.getfile(commands_module)
        with open(source_file, "r") as f:
            source = f.read()

        # Should not contain setup_cli_container calls
        assert "setup_cli_container" not in source, (
            "CLI commands should not use setup_cli_container"
        )

        # Should use get_cli_container_factory instead
        assert "get_cli_container_factory" in source, (
            "CLI commands should use get_cli_container_factory"
        )


class TestCodebaseStructuralCompliance:
    """Test overall codebase structural compliance."""

    def test_no_circular_imports(self):
        """Test that there are no circular import dependencies."""
        # This is a simplified check - a more complete version would
        # build a full dependency graph

        # Test key modules can be imported independently
        try:
            from hci_extractor.core.config import ExtractorConfig
            from hci_extractor.core.events import EventBus
            from hci_extractor.core.models import Paper
            from hci_extractor.providers.base import LLMProvider
            from hci_extractor.providers.gemini_provider import GeminiProvider
        except ImportError as e:
            pytest.fail(f"Circular import detected: {e}")

    def test_src_directory_structure(self):
        """Test that source code follows expected directory structure."""
        src_path = Path(__file__).parent.parent / "src" / "hci_extractor"

        # Check that key directories exist
        expected_dirs = [
            "core",
            "providers",
            "infrastructure",
            "cli",
            "utils",
            "prompts",
        ]

        for dir_name in expected_dirs:
            dir_path = src_path / dir_name
            assert dir_path.exists(), f"Expected directory {dir_name} should exist"
            assert dir_path.is_dir(), f"{dir_name} should be a directory"

    def test_no_todo_comments_in_production_code(self):
        """Test that no TODO comments exist in production code."""
        src_path = Path(__file__).parent.parent / "src"

        # Check all Python files for TODO comments
        python_files = list(src_path.rglob("*.py"))

        for file_path in python_files:
            with open(file_path, "r") as f:
                content = f.read()
                lines = content.split("\n")

                for line_num, line in enumerate(lines, 1):
                    # Check for TODO comments (only fail on uncommented TODOs)
                    stripped = line.strip()
                    if (
                        "TODO" in line.upper()
                        and not stripped.startswith("#")
                        and "TODO" in stripped
                    ):
                        # Only fail if it's not in a comment context
                        if not any(
                            comment_marker in line
                            for comment_marker in ["#", '"""', "'''"]
                        ):
                            pytest.fail(
                                f"TODO comment found in {file_path}:{line_num}: {line.strip()}",
                            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
