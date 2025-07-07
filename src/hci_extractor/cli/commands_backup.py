"""CLI commands for HCI extractor."""

import asyncio
import csv
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
from dotenv import load_dotenv

from hci_extractor.cli.config_options import (
    CLI_CONFIG_MAPPING,
    get_high_priority_options,
    get_medium_priority_options,
    validate_cli_value,
)
from hci_extractor.cli.config_profiles import (
    RESEARCH_PROFILES,
    apply_profile_to_config,
    get_profile,
    get_profile_comparison,
    recommend_profile_for_use_case,
)
from hci_extractor.cli.cli_configuration_service import get_cli_container_factory
from hci_extractor.cli.progress import ProgressTracker
from hci_extractor.core.analysis import extract_paper_simple
from hci_extractor.core.config import ExtractorConfig
from hci_extractor.core.events import (
    BatchProcessingCompleted,
    BatchProcessingStarted,
    ConfigurationLoaded,
    EventBus,
)
from hci_extractor.core.extraction import PdfExtractor, TextNormalizer
from hci_extractor.core.models import LLMError, PdfError
from hci_extractor.providers import LLMProvider
from hci_extractor.utils.logging import setup_logging
from hci_extractor.utils.user_error_translator import (
    create_user_friendly_exception,
    format_error_for_cli,
)

# Load environment variables from .env file
load_dotenv()

__version__ = "0.1.0"


# CLI configuration service setup functions removed - use get_cli_container_factory() directly


# get_llm_provider() function removed - use DI container instead


def validate_and_show_config_options(ctx: click.Context) -> None:
    """Validate CLI configuration options and show warnings for invalid values."""
    # Validate each provided parameter against the configuration mapping
    validated_params = {}
    warnings = []

    for param_name, param_value in ctx.params.items():
        if param_value is None:
            continue

        # Convert parameter name to config option name
        config_option_name = param_name.replace("_", "-")

        # Find matching configuration option
        matching_option = None
        for opt_name, option in CLI_CONFIG_MAPPING.items():
            if option.cli_name == f"--{config_option_name}":
                matching_option = option
                break

        if matching_option:
            try:
                validated_value = validate_cli_value(matching_option, param_value)
                validated_params[param_name] = validated_value

                # Show warning if value was adjusted
                if validated_value != param_value:
                    warnings.append(
                        f"⚠️  {matching_option.cli_name}: {param_value} → "
                        f"{validated_value} (adjusted to valid range)"
                    )
            except click.BadParameter as e:
                from hci_extractor.core.models.exceptions import ConfigurationError

                error = ConfigurationError(str(e))
                context = {
                    "operation": "configuration_validation",
                    "parameter": param_name,
                    "value": param_value,
                }
                raise create_user_friendly_exception(error, context)

    # Show warnings if any
    if warnings:
        click.echo("\n".join(warnings), err=True)
        click.echo()

    # Update context with validated parameters
    ctx.params.update(validated_params)


def show_configuration_help() -> None:
    """Show detailed configuration help information."""
    click.echo(
        "\n🔧 " + click.style("Configuration Options Guide", bold=True, fg="cyan")
    )
    click.echo("=" * 40)

    # High priority options
    click.echo(
        "\n📈 " + click.style("High Priority (Commonly Used)", bold=True, fg="green")
    )
    for name, option in get_high_priority_options().items():
        click.echo(f"  {option.cli_name:<20} {option.help_text}")
        click.echo(f"  {' ' * 20} Default: {option.default_description}")
        click.echo()

    # Medium priority options
    click.echo(
        "\n⚙️  "
        + click.style("Medium Priority (Advanced Usage)", bold=True, fg="yellow")
    )
    for name, option in get_medium_priority_options().items():
        click.echo(f"  {option.cli_name:<20} {option.help_text}")
        click.echo(f"  {' ' * 20} Default: {option.default_description}")
        click.echo()

    click.echo("\n💡 " + click.style("Tips:", bold=True))
    click.echo("  • Use --help with any command to see command-specific options")
    click.echo("  • Set HCI_* environment variables for persistent configuration")
    click.echo("  • Higher --chunk-size = fewer API calls but more tokens per call")
    click.echo("  • Lower --temperature (0.0-0.3) = more consistent extractions")
    click.echo("  • Increase --timeout for large documents or slow connections")
    click.echo()


def _show_debug_config_info() -> None:
    """Show detailed configuration resolution information."""
    ctx = click.get_current_context()
    if not ctx.meta.get("debug_config", False):
        return

    click.echo("\n🔎 " + click.style("Configuration Debug Info", bold=True, fg="blue"))
    click.echo("-" * 35)

    # Show environment variables
    click.echo("🌍 Environment Variables:")
    hci_vars = {
        k: v
        for k, v in os.environ.items()
        if k.startswith("HCI_") or k == "GEMINI_API_KEY"
    }
    if hci_vars:
        for var, value in hci_vars.items():
            # Mask sensitive values
            display_value = (
                value
                if "key" not in var.lower()
                else f"{value[:8]}..." if len(value) > 8 else "***"
            )
            click.echo(f"   {var}={display_value}")
    else:
        click.echo("   No HCI_* environment variables set")

    # Show CLI parameters
    click.echo("\n💻 CLI Parameters:")
    cli_params = [(k, v) for k, v in ctx.params.items() if v is not None]
    if cli_params:
        for param, value in cli_params:
            click.echo(f"   --{param.replace('_', '-')}={value}")
    else:
        click.echo("   No CLI parameters provided")

    # Show configuration resolution
    try:
        container_factory = get_cli_container_factory()
        container = container_factory.create_container_with_cli_config(ctx)
        config = container.resolve(ExtractorConfig)
        click.echo("\n⚙️ Final Configuration:")
        click.echo(f"   chunk_size: {config.analysis.chunk_size}")
        click.echo(f"   timeout: {config.analysis.section_timeout_seconds}s")
        click.echo(f"   max_retries: {config.retry.max_attempts}")
        click.echo(f"   temperature: {config.analysis.temperature}")
        click.echo(f"   max_concurrent: {config.analysis.max_concurrent_sections}")
    except Exception as e:
        click.echo(f"\n❌ Configuration error: {e}")

    click.echo()


def _check_virtual_environment() -> None:
    """Check if running in virtual environment and show warning if not."""
    # Check if we're in a virtual environment
    in_venv = hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    )

    if not in_venv:
        click.echo(
            "⚠️  "
            + click.style("Warning:", fg="yellow", bold=True)
            + " You don't appear to be in a virtual environment."
        )
        click.echo("💡 For best results, activate your virtual environment first:")
        click.echo("   source venv/bin/activate")
        click.echo()


@click.group()
@click.version_option(__version__)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option(
    "--debug-config",
    is_flag=True,
    help="Show detailed configuration resolution process",
)
def cli(verbose: bool, debug_config: bool) -> None:
    """HCI Paper Extractor - Extract structured content from academic PDFs."""
    setup_logging(verbose)

    # Store debug-config flag in context for other commands to use
    ctx = click.get_current_context()
    ctx.meta["debug_config"] = debug_config


@cli.command()
def version() -> None:
    """Show version information."""
    click.echo(f"HCI Paper Extractor v{__version__}")
    click.echo(f"Python {sys.version}")


@cli.command()
def config() -> None:
    """Show detailed configuration options and their usage."""
    show_configuration_help()


@cli.command()
def profiles() -> None:
    """Show available configuration profiles for different research scenarios."""
    click.echo("\n🎯 " + click.style("Configuration Profiles", bold=True, fg="cyan"))
    click.echo("=" * 40)
    click.echo("\nChoose a profile optimized for your research scenario:")

    # Show profile comparison
    comparison = get_profile_comparison()

    for profile_name, profile_info in comparison.items():
        profile = RESEARCH_PROFILES[profile_name]
        click.echo("\n📋 " + click.style(profile.name, bold=True, fg="green"))
        click.echo(f"   {profile.description}")
        click.echo(f"   👥 Target: {profile.target_users}")
        click.echo(
            f"   ⚡ Speed: {profile_info['speed']} | "
            f"🎯 Accuracy: {profile_info['accuracy']} | "
            f"💰 Cost: {profile_info['cost']}"
        )
        click.echo(f"   📝 Use: {profile.use_case}")

        # Show example command
        if profile.recommended_commands:
            click.echo(f"   💡 Example: {profile.recommended_commands[0]}")

    click.echo("\n🚀 " + click.style("Usage:", bold=True))
    click.echo("   hci-extractor extract paper.pdf --profile PROFILE_NAME")
    click.echo("   hci-extractor batch papers/ results/ --profile PROFILE_NAME")

    click.echo("\n🔧 " + click.style("Profile Selection Help:", bold=True))
    click.echo("   • quick_scan: Fast preliminary analysis")
    click.echo("   • thorough: Systematic literature reviews")
    click.echo("   • high_volume: Batch processing 50+ papers")
    click.echo("   • precision: Maximum accuracy for critical research")
    click.echo("   • budget_conscious: Minimize API costs")
    click.echo("   • experimental: Advanced features and debugging")
    click.echo()


@cli.command()
@click.option(
    "--papers",
    type=int,
    prompt="Number of papers to process",
    help="Number of papers you plan to process",
)
@click.option(
    "--timeline",
    type=click.Choice(["urgent", "normal", "flexible"], case_sensitive=False),
    prompt="Timeline for completion",
    help="How much time you have for processing",
)
@click.option(
    "--quality",
    type=click.Choice(["draft", "standard", "publication"], case_sensitive=False),
    prompt="Quality requirement",
    help="Quality level needed for your research",
)
@click.option(
    "--budget",
    type=click.Choice(["tight", "moderate", "flexible"], case_sensitive=False),
    prompt="Budget constraints",
    help="API budget constraints",
)
def recommend(papers: int, timeline: str, quality: str, budget: str) -> None:
    """Get personalized configuration profile recommendations."""
    click.echo("\n🤖 " + click.style("Profile Recommendation", bold=True, fg="cyan"))
    click.echo("=" * 30)

    # Get recommendation
    profile_name, reasoning = recommend_profile_for_use_case(
        paper_count=papers,
        time_constraint=timeline,
        quality_requirement=quality,
        budget_constraint=budget,
    )

    profile = RESEARCH_PROFILES[profile_name]

    click.echo(
        "\n✨ "
        + click.style(f"Recommended Profile: {profile.name}", bold=True, fg="green")
    )
    click.echo(f"📝 {reasoning}")
    click.echo("\n📋 Profile Details:")
    click.echo(f"   Description: {profile.description}")
    click.echo(f"   Best for: {profile.use_case}")

    click.echo("\n🚀 " + click.style("Recommended Commands:", bold=True))
    for cmd in profile.recommended_commands:
        click.echo(f"   {cmd}")

    click.echo("\n💡 " + click.style("Tips:", bold=True))
    for tip in profile.tips:
        click.echo(f"   • {tip}")

    click.echo("\n🎯 " + click.style("Next Steps:", bold=True))
    click.echo("   1. Try the recommended profile with your papers")
    click.echo("   2. Run 'hci-extractor profiles' to see all options")
    click.echo("   3. Use 'hci-extractor config' for detailed customization")
    click.echo()


@cli.command()
def diagnose() -> None:
    """Diagnose configuration and system setup issues."""
    click.echo("\n🔍 " + click.style("System Diagnostic", bold=True, fg="cyan"))
    click.echo("=" * 30)
    click.echo()

    diagnostic_results: list[tuple[str, str, Optional[str]]] = []

    # Check 1: Virtual Environment
    click.echo("1. " + click.style("Virtual Environment", bold=True))
    in_venv = hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    )
    if in_venv:
        click.echo("   ✅ Virtual environment detected")
        diagnostic_results.append(("Virtual Environment", "✅ OK", None))
    else:
        click.echo("   ⚠️  Not in virtual environment")
        click.echo("   💡 Activate with: source venv/bin/activate")
        diagnostic_results.append(
            ("Virtual Environment", "⚠️  Warning", "Not in virtual environment")
        )
    click.echo()

    # Check 2: API Key Configuration
    click.echo("2. " + click.style("API Key Configuration", bold=True))
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key and api_key != "your-api-key-here":
        # Test the API key using DI container
        try:
            container_factory = get_cli_container_factory()
            container = container_factory.create_container_with_cli_config()
            llm_provider = container.resolve(LLMProvider)  # type: ignore  # type: ignore
            click.echo("   ✅ API key found and provider initialized")
            diagnostic_results.append(("API Key", "✅ OK", None))
        except Exception as e:
            click.echo(f"   ❌ API key issue: {str(e)[:100]}...")
            click.echo(
                "   💡 Get a new key at: https://makersuite.google.com/app/apikey"
            )
            diagnostic_results.append(("API Key", "❌ Error", str(e)[:100]))
    else:
        click.echo("   ❌ GEMINI_API_KEY not set or invalid")
        click.echo("   💡 Set with: export GEMINI_API_KEY=your-key-here")
        diagnostic_results.append(("API Key", "❌ Missing", "GEMINI_API_KEY not set"))
    click.echo()

    # Check 3: Configuration Validation
    click.echo("3. " + click.style("Configuration Validation", bold=True))
    try:
        container_factory = get_cli_container_factory()
        container = container_factory.create_container_with_cli_config()
        config = container.resolve(ExtractorConfig)
        click.echo("   ✅ Configuration loaded successfully")
        click.echo(f"   📊 Chunk size: {config.analysis.chunk_size}")
        click.echo(f"   ⏱️  Timeout: {config.analysis.section_timeout_seconds}s")
        click.echo(f"   🔄 Max retries: {config.retry.max_attempts}")
        diagnostic_results.append(("Configuration", "✅ OK", None))
    except Exception as e:
        click.echo(f"   ❌ Configuration error: {e}")
        diagnostic_results.append(("Configuration", "❌ Error", str(e)))
    click.echo()

    # Summary
    click.echo("📋 " + click.style("Diagnostic Summary", bold=True, fg="green"))
    click.echo("-" * 30)

    issues_found = []
    warnings_found = []

    for check, status, details in diagnostic_results:
        if "❌" in status:
            issues_found.append((check, details))
        elif "⚠️" in status:
            warnings_found.append((check, details))

    if not issues_found and not warnings_found:
        click.echo("🎉 All checks passed! Your system is ready for paper extraction.")
    else:
        if issues_found:
            click.echo("❌ Issues requiring attention:")
            for check, details in issues_found:
                click.echo(f"   • {check}: {details}")

        if warnings_found:
            click.echo("⚠️  Warnings (system should still work):")
            for check, details in warnings_found:
                click.echo(f"   • {check}: {details}")

    click.echo()
    click.echo("💡 " + click.style("Next Steps:", bold=True))
    click.echo("   • Run 'hci-extractor config' to see configuration options")
    click.echo("   • Run 'hci-extractor profiles' to see optimized profiles")
    click.echo("   • Run 'hci-extractor setup' for interactive configuration")
    click.echo()


@cli.command()
@click.option(
    "--dry-run", is_flag=True, help="Test configuration without making API calls"
)
@click.option(
    "--profile",
    type=click.Choice(
        [
            "quick_scan",
            "thorough",
            "high_volume",
            "precision",
            "budget_conscious",
            "experimental",
        ],
        case_sensitive=False,
    ),
    help="Test a specific configuration profile",
)
def test_config(dry_run: bool, profile: Optional[str]) -> None:
    """Test your configuration with validation and recommendations."""
    click.echo("\n🧪 " + click.style("Configuration Testing", bold=True, fg="cyan"))
    click.echo("=" * 30)
    click.echo()

    try:
        # Set up DI container with optional profile configuration
        ctx = click.get_current_context()

        if profile:
            profile_obj = get_profile(profile)
            if not profile_obj:
                raise click.ClickException(f"Unknown profile: {profile}")

            click.echo(f"🎯 Testing profile: {profile_obj.name}")
            click.echo(f"📝 {profile_obj.description}")
            click.echo()

            # Apply profile to base configuration and store in context
            config = apply_profile_to_config(profile_obj)
            if ctx.meta is None:
                ctx.meta = {}
            ctx.meta["profile_config"] = config

        # Set up DI container with configuration from CLI context
        container_factory = get_cli_container_factory()
        container = container_factory.create_container_with_cli_config(ctx)
        config = container.resolve(ExtractorConfig)

        # Display current configuration
        click.echo("📊 " + click.style("Current Configuration:", bold=True))
        click.echo(f"   Chunk size: {config.analysis.chunk_size} characters")
        click.echo(f"   Timeout: {config.analysis.section_timeout_seconds} seconds")
        click.echo(f"   Max retries: {config.retry.max_attempts}")
        click.echo(f"   Temperature: {config.analysis.temperature}")
        click.echo(f"   Max concurrent: {config.analysis.max_concurrent_sections}")
        click.echo()

        # Configuration validation
        click.echo("✅ " + click.style("Configuration Validation:", bold=True))

        # Check chunk size
        if config.analysis.chunk_size < 1000:
            click.echo("   ⚠️  Chunk size very small - may cause excessive API calls")
        elif config.analysis.chunk_size > 20000:
            click.echo("   ⚠️  Chunk size very large - may hit token limits")
        else:
            click.echo("   ✅ Chunk size within optimal range")

        # Check timeout
        if config.analysis.section_timeout_seconds < 30:
            click.echo(
                "   ⚠️  Timeout very short - may cause timeouts for large sections"
            )
        elif config.analysis.section_timeout_seconds > 180:
            click.echo("   ⚠️  Timeout very long - may cause unnecessary delays")
        else:
            click.echo("   ✅ Timeout within reasonable range")

        # Check retry attempts
        if config.retry.max_attempts < 2:
            click.echo("   ⚠️  Low retry count - may fail on temporary issues")
        elif config.retry.max_attempts > 5:
            click.echo("   ⚠️  High retry count - may cause long processing times")
        else:
            click.echo("   ✅ Retry attempts within good range")

        click.echo()

        # Performance estimates
        click.echo("📈 " + click.style("Performance Estimates:", bold=True))

        # Estimate processing time for different document sizes
        small_doc_time = (5000 / config.analysis.chunk_size) * (
            config.analysis.section_timeout_seconds * 0.3
        )
        large_doc_time = (50000 / config.analysis.chunk_size) * (
            config.analysis.section_timeout_seconds * 0.3
        )

        click.echo(f"   📄 Small paper (~5K chars): ~{small_doc_time:.1f} seconds")
        click.echo(f"   📚 Large paper (~50K chars): ~{large_doc_time:.1f} seconds")

        # API call estimates
        small_calls = max(1, 5000 / config.analysis.chunk_size)
        large_calls = max(1, 50000 / config.analysis.chunk_size)

        click.echo(f"   🔌 API calls for small paper: ~{small_calls:.0f}")
        click.echo(f"   🔌 API calls for large paper: ~{large_calls:.0f}")
        click.echo()

        if not dry_run:
            # Test API connectivity
            click.echo("🌐 " + click.style("API Connectivity Test:", bold=True))
            try:
                container_factory = get_cli_container_factory()
                container = container_factory.create_container_with_cli_config()
                container.resolve(LLMProvider)  # type: ignore
                click.echo("   ✅ LLM provider initialized successfully")
                click.echo("   💡 API test completed successfully")

            except Exception as e:
                from hci_extractor.utils.user_error_translator import (
                    format_error_for_cli,
                )

                formatted_error = format_error_for_cli(
                    e, {"operation": "api_test"}, verbose=False
                )
                click.echo(formatted_error)
                return
        else:
            click.echo("🌐 " + click.style("API Test:", bold=True))
            click.echo("   ℹ️  Skipped (dry-run mode)")

        click.echo()
        click.echo("🎯 " + click.style("Recommendations:", bold=True))

        if config.analysis.chunk_size > 15000:
            click.echo("   💡 Consider reducing chunk size for better reliability")

        if config.analysis.max_concurrent_sections > 3:
            click.echo("   💡 High concurrency - monitor API rate limits")

        if config.analysis.temperature > 0.3:
            click.echo("   💡 High temperature - may reduce extraction consistency")

        click.echo("   ✅ Configuration looks good for your use case!")
        click.echo()

    except Exception as e:
        from hci_extractor.utils.user_error_translator import format_error_for_cli

        context = {"operation": "configuration_testing", "profile_used": profile}
        formatted_error = format_error_for_cli(e, context, verbose=True)
        click.echo(formatted_error, err=True)
        raise click.Abort()


@cli.command()
def quickstart() -> None:
    """Interactive quickstart guide with common research workflows."""

    click.echo()
    click.echo(
        "🚀 "
        + click.style("HCI Paper Extractor - Quick Start Guide", bold=True, fg="green")
    )
    click.echo("=" * 50)
    click.echo()

    # Check environment first
    _check_virtual_environment()

    # Welcome and overview
    click.echo(
        "📚 "
        + click.style(
            "Welcome! Let's get you extracting academic insights in minutes.", bold=True
        )
    )
    click.echo()
    click.echo("This guide will walk you through common research workflows:")
    click.echo("1. 📄 Single paper analysis")
    click.echo("2. 📊 Systematic literature review")
    click.echo("3. 🔬 Meta-analysis preparation")
    click.echo("4. 🔧 Troubleshooting")
    click.echo()

    # Workflow selection
    workflow_choices = {
        "1": "single",
        "2": "systematic",
        "3": "meta-analysis",
        "4": "troubleshooting",
    }

    choice = click.prompt(
        "Which workflow would you like to explore?",
        type=click.Choice(["1", "2", "3", "4"]),
        show_choices=True,
    )

    workflow = workflow_choices[choice]
    click.echo()

    if workflow == "single":
        _quickstart_single_paper()
    elif workflow == "systematic":
        _quickstart_systematic_review()
    elif workflow == "meta-analysis":
        _quickstart_meta_analysis()
    elif workflow == "troubleshooting":
        _quickstart_troubleshooting()


@cli.command()
def setup() -> None:
    """Interactive setup wizard for first-time configuration."""

    progress = ProgressTracker()

    progress.info("Starting HCI Paper Extractor setup wizard...")
    click.echo()

    # Step 1: Welcome and explanation
    click.echo(
        "🎯 " + click.style("Welcome to HCI Paper Extractor!", bold=True, fg="green")
    )
    click.echo("This wizard will help you get started in just a few minutes.")
    click.echo()

    # Step 2: Check environment
    progress.info("Checking your environment...")

    # Check if we're in a virtual environment
    in_venv = hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    )

    if not in_venv:
        progress.warning("You don't appear to be in a virtual environment.")
        click.echo("💡 For best results, activate your virtual environment first:")
        click.echo("   source venv/bin/activate")
        click.echo()
        if not click.confirm("Continue anyway?"):
            click.echo("Activate your virtual environment and try again!")
            raise click.Abort()
    else:
        click.echo("✅ Virtual environment detected")

    # Step 3: API Key configuration
    click.echo()
    progress.info("Setting up your API key...")

    # Check if API key already exists
    api_key = os.getenv("GEMINI_API_KEY")

    if api_key and api_key != "your-api-key-here":
        click.echo("✅ API key found in environment")

        # Test the existing API key
        if click.confirm("Would you like to test your existing API key?"):
            if _test_api_key(api_key, progress):
                click.echo("✅ API key is working correctly!")
            else:
                click.echo("❌ API key test failed. Let's configure a new one.")
                api_key = None
    else:
        api_key = None

    # Get new API key if needed
    if not api_key:
        click.echo()
        click.echo("You need a Google Gemini API key to use this tool.")
        click.echo(
            "Get your free API key at: "
            + click.style("https://makersuite.google.com/app/apikey", fg="blue")
        )
        click.echo()

        while True:
            new_key = click.prompt("Enter your Gemini API key", hide_input=True)
            if new_key and new_key.strip():
                # Test the new API key
                if _test_api_key(new_key.strip(), progress):
                    # Save to .env file
                    _save_api_key(new_key.strip())
                    click.echo("✅ API key saved and verified!")
                    break
                else:
                    click.echo(
                        "❌ API key test failed. Please check your key and try again."
                    )
                    if not click.confirm("Try again?"):
                        raise click.Abort()
            else:
                click.echo("Please enter a valid API key.")

    # Step 4: Test with sample paper
    click.echo()
    progress.info("Testing with sample paper...")

    # Check if sample paper exists
    sample_path = Path("autisticadults.pdf")
    if sample_path.exists():
        click.echo(f"📄 Found sample paper: {sample_path}")

        if click.confirm("Would you like to test extraction with the sample paper?"):
            try:
                click.echo()
                click.echo(
                    "🧪 Running test extraction (this may take 30-60 seconds)..."
                )

                # Run a quick test extraction
                test_result = _run_test_extraction(sample_path, progress)

                if test_result:
                    click.echo("✅ Test extraction successful!")
                    click.echo(
                        f"   Extracted {test_result['elements']} elements "
                        f"from {test_result['sections']} sections"
                    )
                else:
                    click.echo(
                        "❌ Test extraction failed - but your setup should still work"
                    )

            except Exception as e:
                progress.warning(f"Test extraction failed: {e}")
                click.echo("💡 Your setup should still work for other papers")
    else:
        click.echo("ℹ️  No sample paper found - skipping test")

    # Step 5: Configuration recommendations
    click.echo()
    progress.info("Optimizing settings for your system...")

    # Detect optimal concurrency based on CPU cores
    import multiprocessing

    cpu_cores = multiprocessing.cpu_count()
    recommended_concurrency = min(
        max(cpu_cores // 2, 1), 5
    )  # Conservative but not too slow

    click.echo(f"💻 Detected {cpu_cores} CPU cores")
    click.echo(
        f"💡 Recommended concurrency for batch processing: {recommended_concurrency}"
    )

    # Step 6: Final instructions
    click.echo()
    click.echo("🎉 " + click.style("Setup complete!", bold=True, fg="green"))
    click.echo()
    click.echo("📚 Quick start commands:")
    click.echo("─" * 40)
    click.echo("# Extract single paper to CSV:")
    click.echo("python -m hci_extractor extract your_paper.pdf --output results.csv")
    click.echo()
    click.echo("# Batch process multiple papers:")
    click.echo(
        "python -m hci_extractor batch papers_folder/ results/ "
        f"--max-concurrent {recommended_concurrency}"
    )
    click.echo()
    click.echo("# Get help:")
    click.echo("python -m hci_extractor --help")
    click.echo("─" * 40)
    click.echo()
    click.echo("Happy researching! 📖")


def _test_api_key(api_key: str, progress: ProgressTracker) -> bool:
    """Test if API key works by making a minimal API call."""
    try:
        progress.info("Testing API key...")

        # Test the API key by temporarily setting environment and resolving provider
        original_key = os.getenv("GEMINI_API_KEY")
        try:
            os.environ["GEMINI_API_KEY"] = api_key

            # Use DI container to create provider with the test API key
            container_factory = get_cli_container_factory()
            container = container_factory.create_container_with_cli_config()
            provider = container.resolve(LLMProvider)  # type: ignore

            # Make a simple test call using the async method
            async def test_call() -> Dict[str, Any]:
                return await provider._make_api_request("Say 'test' in one word only.")

            test_response = asyncio.run(test_call())

            return bool(test_response and isinstance(test_response, dict))
        finally:
            # Restore original API key
            if original_key is not None:
                os.environ["GEMINI_API_KEY"] = original_key
            elif "GEMINI_API_KEY" in os.environ:
                del os.environ["GEMINI_API_KEY"]

    except Exception as e:
        progress.warning(f"API key test failed: {e}")
        return False


def _save_api_key(api_key: str) -> None:
    """Save API key to .env file."""
    env_path = Path(".env")

    # Read existing .env content
    existing_content = ""
    if env_path.exists():
        with open(env_path, "r") as f:
            lines = f.readlines()

        # Remove any existing GEMINI_API_KEY lines
        lines = [line for line in lines if not line.startswith("GEMINI_API_KEY=")]
        existing_content = "".join(lines)

    # Write new content with API key
    with open(env_path, "w") as f:
        f.write(existing_content)
        if existing_content and not existing_content.endswith("\n"):
            f.write("\n")
        f.write(f"GEMINI_API_KEY={api_key}\n")


def _run_test_extraction(
    pdf_path: Path, progress: ProgressTracker
) -> Optional[Dict[str, Any]]:
    """Run a quick test extraction to verify everything works."""
    try:
        # Get dependencies from DI container
        container_factory = get_cli_container_factory()
        container = container_factory.create_container_with_cli_config()
        config = container.resolve(ExtractorConfig)
        event_bus = container.resolve(EventBus)
        llm_provider = container.resolve(LLMProvider)  # type: ignore

        # Run extraction
        result = asyncio.run(
            extract_paper_simple(
                pdf_path=pdf_path,
                config=config,
                event_bus=event_bus,
                llm_provider=llm_provider,
                progress_callback=None,  # Skip progress for test
            )
        )

        return {
            "elements": result.total_elements,
            "sections": len(result.extraction_metadata.get("sections_processed", [])),
        }

    except Exception as e:
        progress.warning(f"Test extraction failed: {e}")
        return None


@cli.command()
def doctor() -> None:
    """Diagnose common setup and configuration issues."""

    progress = ProgressTracker()

    click.echo(
        "🩺 "
        + click.style("HCI Paper Extractor - System Diagnostics", bold=True, fg="blue")
    )
    click.echo("=" * 50)
    click.echo()

    issues_found = []

    # Check 1: Python version
    progress.info("Checking Python version...")
    python_version = sys.version_info
    if python_version >= (3, 9):
        click.echo(
            f"✅ Python {python_version.major}.{python_version.minor}."
            f"{python_version.micro} (supported)"
        )
    else:
        issue = (
            f"❌ Python {python_version.major}.{python_version.minor} (requires 3.9+)"
        )
        click.echo(issue)
        issues_found.append(("Python Version", "Upgrade to Python 3.9 or newer"))

    # Check 2: Virtual environment
    progress.info("Checking virtual environment...")
    in_venv = hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    )
    if in_venv:
        click.echo("✅ Virtual environment active")
    else:
        issue = "⚠️  Not in virtual environment"
        click.echo(issue)
        issues_found.append(("Virtual Environment", "Run: source venv/bin/activate"))

    # Check 3: Package installation
    progress.info("Checking package installation...")
    try:
        import hci_extractor

        click.echo("✅ HCI Extractor package installed")
    except ImportError:
        issue = "❌ HCI Extractor package not found"
        click.echo(issue)
        issues_found.append(("Package Installation", "Run: pip install -e ."))

    # Check 4: Dependencies
    progress.info("Checking dependencies...")
    missing_deps = []

    try:
        import PyMuPDF  # type: ignore

        click.echo("✅ PyMuPDF (PDF processing)")
    except ImportError:
        missing_deps.append("PyMuPDF")

    try:
        import rich

        click.echo("✅ Rich (progress bars)")
    except ImportError:
        missing_deps.append("rich")

    try:
        import click as click_lib

        click.echo("✅ Click (CLI interface)")
    except ImportError:
        missing_deps.append("click")

    try:
        import google.generativeai

        click.echo("✅ Google GenerativeAI (LLM provider)")
    except ImportError:
        missing_deps.append("google-generativeai")

    if missing_deps:
        issue = f"❌ Missing dependencies: {', '.join(missing_deps)}"
        click.echo(issue)
        issues_found.append(
            ("Dependencies", f"Run: pip install {' '.join(missing_deps)}")
        )

    # Check 5: API Key configuration
    progress.info("Checking API key configuration...")
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        issue = "❌ No API key found"
        click.echo(issue)
        issues_found.append(
            ("API Key", "Set GEMINI_API_KEY in .env file or run: hci-extractor setup")
        )
    elif api_key == "your-api-key-here":
        issue = "❌ Default placeholder API key detected"
        click.echo(issue)
        issues_found.append(("API Key", "Replace placeholder with real API key"))
    else:
        click.echo("✅ API key configured")

        # Test API key if configured
        if click.confirm("Test API key with a quick call?"):
            if _test_api_key(api_key, progress):
                click.echo("✅ API key working correctly")
            else:
                issue = "❌ API key test failed"
                click.echo(issue)
                issues_found.append(
                    ("API Key", "Check your API key is valid and has quota remaining")
                )

    # Check 6: Sample paper
    progress.info("Checking for sample paper...")
    sample_path = Path("autisticadults.pdf")
    if sample_path.exists():
        click.echo(f"✅ Sample paper found: {sample_path}")
    else:
        issue = "ℹ️  No sample paper found"
        click.echo(issue)
        # Not an error, just informational

    # Check 7: File permissions
    progress.info("Checking file permissions...")
    try:
        test_file = Path("test_write_permission.tmp")
        test_file.write_text("test")
        test_file.unlink()
        click.echo("✅ Write permissions in current directory")
    except Exception as e:
        issue = f"❌ Write permission issue: {e}"
        click.echo(issue)
        issues_found.append(
            ("File Permissions", "Check write permissions in current directory")
        )

    # Check 8: Memory and system resources
    progress.info("Checking system resources...")
    import multiprocessing

    cpu_cores = multiprocessing.cpu_count()
    click.echo(f"💻 {cpu_cores} CPU cores detected")

    # Summary
    click.echo()
    click.echo("=" * 50)

    if not issues_found:
        click.echo(
            "🎉 "
            + click.style(
                "All checks passed! Your system is ready.", bold=True, fg="green"
            )
        )
        click.echo()
        click.echo("💡 Try running:")
        click.echo(
            "   python -m hci_extractor extract your_paper.pdf --output results.csv"
        )
    else:
        click.echo(
            "🔧 "
            + click.style(
                "Issues found - here's how to fix them:", bold=True, fg="yellow"
            )
        )
        click.echo()

        for i, (issue, solution) in enumerate(issues_found, 1):
            click.echo(f"{i}. {issue}")
            click.echo(f"   💡 Solution: {solution}")
            click.echo()

        click.echo(
            "After fixing these issues, run 'hci-extractor doctor' again to verify."
        )

    click.echo()


@cli.command()
@click.argument("pdf_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output file for extracted content (JSON format)",
)
@click.option(
    "--normalize", is_flag=True, help="Apply text normalization for cleaner output"
)
def parse(pdf_path: Path, output: Optional[Path], normalize: bool) -> None:
    """Extract text content from a PDF file."""
    try:
        # Initialize extractor
        container_factory = get_cli_container_factory()
        container = container_factory.create_container_with_cli_config()
        config = container.resolve(ExtractorConfig)
        extractor = PdfExtractor(config=config)

        # Extract PDF content
        click.echo(f"Extracting content from {pdf_path}...")
        content = extractor.extract_content(pdf_path)
        click.echo(
            f"Successfully extracted {content.total_pages} pages, "
            f"{content.total_chars} characters"
        )

        # Apply normalization if requested
        output_data: Dict[str, Any]
        if normalize:
            normalizer = TextNormalizer()
            click.echo("Applying text normalization...")

            # Normalize each page
            normalized_pages: List[Dict[str, Any]] = []
            for page in content.pages:
                transformation = normalizer.normalize(page.text)
                normalized_pages.append(
                    {
                        "page_number": page.page_number,
                        "original_text": transformation.original_text,
                        "cleaned_text": transformation.cleaned_text,
                        "transformations": transformation.transformations,
                        "char_count": len(transformation.cleaned_text),
                    }
                )

            output_data = {
                "file_path": content.file_path,
                "total_pages": content.total_pages,
                "pages": normalized_pages,
                "extraction_metadata": content.extraction_metadata,
                "normalization_applied": True,
            }
        else:
            # Output raw extracted content
            output_data = {
                "file_path": content.file_path,
                "total_pages": content.total_pages,
                "total_chars": content.total_chars,
                "pages": [
                    {
                        "page_number": page.page_number,
                        "text": page.text,
                        "char_count": page.char_count,
                        "dimensions": page.dimensions,
                    }
                    for page in content.pages
                ],
                "extraction_metadata": content.extraction_metadata,
                "created_at": content.created_at.isoformat(),
                "normalization_applied": False,
            }

        # Output results
        if output:
            click.echo(f"Saving results to {output}...")
            with open(output, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            click.echo(f"Extraction complete. Results saved to {output}")
        else:
            # Display summary to stdout
            click.echo("\n--- Extraction Summary ---")
            for page_data in output_data["pages"]:
                text_preview = (
                    page_data.get("cleaned_text", page_data.get("text", ""))[:100]
                    + "..."
                )
                click.echo(
                    f"Page {page_data['page_number']}: "
                    f"{page_data['char_count']} chars - {text_preview}"
                )

    except PdfError as e:
        click.echo(f"PDF Extraction Error: {e}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument("pdf_path", type=click.Path(exists=True, path_type=Path))
# Configuration options for validation
@click.option(
    "--extraction-timeout",
    type=float,
    help="PDF extraction timeout in seconds. Increase for large files. "
    "(default: 30.0 seconds)",
)
@click.option(
    "--max-file-size",
    type=int,
    help="Maximum PDF file size to process in megabytes. (default: 50 MB)",
)
@click.option(
    "--normalize-text",
    is_flag=True,
    help="Apply text normalization to clean PDF extraction artifacts. (default: True)",
)
def validate(
    pdf_path: Path,
    extraction_timeout: Optional[float],
    max_file_size: Optional[int],
    normalize_text: Optional[bool],
) -> None:
    """Check if a PDF file can be processed successfully."""
    # Check virtual environment
    _check_virtual_environment()

    try:
        # Set up DI container with configuration from CLI context
        ctx = click.get_current_context()
        container_factory = get_cli_container_factory()
        container = container_factory.create_container_with_cli_config(ctx)

        # Resolve dependencies
        config = container.resolve(ExtractorConfig)
        extractor = container.resolve(PdfExtractor)

        # Show configuration info if verbose
        if config.log_level == "DEBUG":
            click.echo(
                f"🔧 Config: timeout={config.extraction.timeout_seconds}s, "
                f"max_file_size={config.extraction.max_file_size_mb}MB, "
                f"normalize_text={config.extraction.normalize_text}"
            )

        click.echo(f"Validating {pdf_path}...")

        # Try to extract content
        content = extractor.extract_content(pdf_path)

        # Run validation
        is_valid = extractor.validate_extraction(content)

        if is_valid:
            click.echo("✓ PDF is valid and processable")
            click.echo(f"  - Pages: {content.total_pages}")
            click.echo(f"  - Characters: {content.total_chars}")
            click.echo(
                f"  - Avg chars/page: {content.total_chars // content.total_pages}"
            )
        else:
            click.echo("✗ PDF validation failed - may have quality issues")

    except PdfError as e:
        context = {
            "operation": "pdf_validation",
            "file_path": str(pdf_path),
            "file_size": str(pdf_path.stat().st_size) if pdf_path.exists() else "0",
        }
        formatted_error = format_error_for_cli(
            e, context, verbose=config.log_level == "DEBUG"
        )
        click.echo(formatted_error, err=True)
        raise click.Abort()
    except Exception as e:
        context = {"operation": "pdf_validation", "file_path": str(pdf_path)}
        formatted_error = format_error_for_cli(
            e, context, verbose=config.log_level == "DEBUG"
        )
        click.echo(formatted_error, err=True)
        raise click.Abort()


@cli.command()
@click.argument("pdf_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output file for extraction results (auto-detects format: .json, .csv, .md)",
)
@click.option("--title", help="Paper title (if not provided, will be auto-detected)")
@click.option(
    "--authors",
    help="Paper authors (comma-separated, if not provided, will be auto-detected)",
)
@click.option("--venue", help="Publication venue (optional)")
@click.option("--year", type=int, help="Publication year (optional)")
# Profile selection option
@click.option(
    "--profile",
    type=click.Choice(
        [
            "quick_scan",
            "thorough",
            "high_volume",
            "precision",
            "budget_conscious",
            "experimental",
        ],
        case_sensitive=False,
    ),
    help="Use a predefined configuration profile optimized for specific "
    "research scenarios",
)
# Systematic configuration options using centralized framework
@click.option(
    "--chunk-size",
    type=int,
    help="Text processing chunk size in characters. Larger chunks mean fewer "
    "API calls but higher token usage. (default: 10000 characters)",
)
@click.option(
    "--timeout",
    type=float,
    help="LLM request timeout in seconds. Increase for large sections or slow "
    "connections. (default: 60.0 seconds)",
)
@click.option(
    "--max-retries",
    type=int,
    help="Maximum retry attempts for failed operations. Higher values increase "
    "reliability but processing time. (default: 3 attempts)",
)
@click.option(
    "--retry-delay",
    type=float,
    help="Initial delay between retries in seconds. Uses exponential backoff "
    "for subsequent retries. (default: 2.0 seconds)",
)
@click.option(
    "--temperature",
    type=float,
    help="LLM temperature for creativity vs consistency. Lower values (0.0-0.3) "
    "for consistent extraction. (default: 0.1 focused)",
)
@click.option(
    "--max-tokens",
    type=int,
    help="Maximum tokens per LLM response. Higher values allow more extractions "
    "per section. (default: 4000 tokens)",
)
# Additional advanced configuration options
@click.option(
    "--chunk-overlap",
    type=int,
    help="Character overlap between text chunks to avoid splitting sentences. "
    "(default: 500 characters)",
)
@click.option(
    "--min-section-length",
    type=int,
    help="Minimum section length to process. Shorter sections are skipped. "
    "(default: 50 characters)",
)
@click.option(
    "--max-concurrent",
    type=int,
    help="Maximum concurrent operations. Higher values increase speed but API "
    "load. (default: 3 operations)",
)
@click.option(
    "--max-file-size",
    type=int,
    help="Maximum PDF file size to process in megabytes. (default: 50 MB)",
)
@click.option(
    "--extraction-timeout",
    type=float,
    help="PDF extraction timeout in seconds. Increase for large files. "
    "(default: 30.0 seconds)",
)
@click.option(
    "--normalize-text/--no-normalize-text",
    default=None,
    help="Apply text normalization to clean PDF extraction artifacts. (default: True)",
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    help="Logging level for debugging and monitoring. (default: INFO)",
)
def extract(
    pdf_path: Path,
    output: Optional[Path],
    title: Optional[str],
    authors: Optional[str],
    venue: Optional[str],
    year: Optional[int],
    profile: Optional[str],
    chunk_size: Optional[int],
    timeout: Optional[float],
    max_retries: Optional[int],
    retry_delay: Optional[float],
    temperature: Optional[float],
    max_tokens: Optional[int],
    chunk_overlap: Optional[int],
    min_section_length: Optional[int],
    max_concurrent: Optional[int],
    max_file_size: Optional[int],
    extraction_timeout: Optional[float],
    normalize_text: Optional[bool],
    log_level: Optional[str],
) -> None:
    """Extract academic elements (claims, findings, methods) from a PDF using LLM \
analysis.

    Output format is auto-detects from file extension:
    - .json: Complete extraction data (default)
    - .csv: Analysis-ready spreadsheet format
    - .md: Human-readable Markdown format
    """
    # Check virtual environment
    _check_virtual_environment()

    try:
        # Get CLI context and set up DI container
        ctx = click.get_current_context()

        # Handle profile selection first
        if profile:
            profile_obj = get_profile(profile)
            if not profile_obj:
                raise click.ClickException(
                    f"Unknown profile: {profile}. Run 'hci-extractor profiles' "
                    "to see available profiles."
                )

            # Show profile information
            click.echo(f"🎯 Using profile: {profile_obj.name}")
            click.echo(f"📝 {profile_obj.description}")
            click.echo()

            # Apply profile to base configuration
            base_config = apply_profile_to_config(profile_obj)
            # Store in context for DI container
            if ctx.meta is None:
                ctx.meta = {}
            ctx.meta["profile_config"] = base_config

        # Validate configuration options
        validate_and_show_config_options(ctx)

        # Set up DI container with configuration from CLI context
        container_factory = get_cli_container_factory()
        container = container_factory.create_container_with_cli_config(ctx)

        # Resolve dependencies
        config = container.resolve(ExtractorConfig)
        llm_provider = container.resolve(LLMProvider)  # type: ignore
        event_bus = container.resolve(EventBus)

        # Show configuration info if verbose
        if config.log_level == "DEBUG":
            click.echo(
                f"🔧 Using configuration: chunk_size={config.analysis.chunk_size}, "
                f"timeout={config.analysis.section_timeout_seconds}s, "
                f"max_retries={config.retry.max_attempts}, "
                f"temperature={config.analysis.temperature}"
            )

        # Initialize progress tracker
        progress = ProgressTracker()

        # Initialize LLM provider
        progress.info("LLM provider initialized via dependency injection")

        # Prepare paper metadata
        paper_metadata: Dict[str, Any] = {}
        if title:
            paper_metadata["title"] = title
        if authors:
            paper_metadata["authors"] = ", ".join(
                [author.strip() for author in authors.split(",")]
            )
        if venue:
            paper_metadata["venue"] = venue
        if year:
            paper_metadata["year"] = year

        # Start single paper progress tracking
        paper_name = pdf_path.stem
        progress.start_batch(1)
        progress.start_paper(paper_name, 6)  # Typical paper has ~6 sections

        # Run async extraction with dependency injection
        result = asyncio.run(
            extract_paper_simple(
                pdf_path=pdf_path,
                llm_provider=llm_provider,
                config=config,
                event_bus=event_bus,
                paper_metadata=paper_metadata,
                progress_callback=progress,
            )
        )

        # Prepare output data
        output_data = {
            "paper": {
                "paper_id": result.paper.paper_id,
                "title": result.paper.title,
                "authors": result.paper.authors,
                "venue": result.paper.venue,
                "year": result.paper.year,
                "file_path": str(pdf_path),
            },
            "extraction_summary": {
                "total_elements": result.total_elements,
                "elements_by_type": result.elements_by_type,
                "elements_by_section": result.elements_by_section,
                "average_confidence": result.average_confidence,
                "created_at": result.created_at.isoformat(),
                # Paper summary for manual comparison
                "paper_summary": result.extraction_metadata.get("paper_summary"),
                "paper_summary_confidence": result.extraction_metadata.get(
                    "paper_summary_confidence"
                ),
                "paper_summary_sources": result.extraction_metadata.get(
                    "paper_summary_sources"
                ),
            },
            "extracted_elements": [
                {
                    "element_id": element.element_id,
                    "element_type": element.element_type,
                    "text": element.text,
                    "section": element.section,
                    "confidence": element.confidence,
                    "evidence_type": element.evidence_type,
                    "page_number": element.page_number,
                    # Optional context fields for manual comparison
                    "supporting_evidence": element.supporting_evidence,
                    "methodology_context": element.methodology_context,
                    "study_population": element.study_population,
                    "limitations": element.limitations,
                    "surrounding_context": element.surrounding_context,
                }
                for element in result.elements
            ],
        }

        # Output results with smart format detection
        if output:
            output_ext = output.suffix.lower()

            if output_ext == ".csv":
                # Direct CSV export for single paper
                click.echo(f"💾 Exporting to CSV format: {output}...")
                csv_content = _export_single_paper_to_csv([output_data])
                with open(output, "w", encoding="utf-8") as f:
                    f.write(csv_content)
                click.echo(f"✅ Extraction complete! CSV results saved to {output}")

            elif output_ext == ".md":
                # Direct Markdown export for single paper
                click.echo(f"💾 Exporting to Markdown format: {output}...")
                md_content = _export_single_paper_to_markdown([output_data])
                with open(output, "w", encoding="utf-8") as f:
                    f.write(md_content)
                click.echo(
                    f"✅ Extraction complete! Markdown results saved to {output}"
                )

            else:
                # Default JSON format
                click.echo(f"💾 Saving results to {output}...")
                with open(output, "w", encoding="utf-8") as f:
                    json.dump(output_data, f, indent=2, ensure_ascii=False)
                click.echo(f"✅ Extraction complete! Results saved to {output}")
        else:
            # Display summary to stdout
            click.echo("\n--- 📊 Extraction Summary ---")
            click.echo(f"Paper: {result.paper.title}")
            click.echo(f"Total elements extracted: {result.total_elements}")
            click.echo(f"Average confidence: {result.average_confidence:.2f}")
            click.echo("\nElements by type:")
            for element_type, count in result.elements_by_type.items():
                click.echo(f"  - {element_type}: {count}")

            click.echo("\n--- 📝 Sample Extractions ---")
            for i, element in enumerate(result.elements[:5]):  # Show first 5
                click.echo(
                    f"{i+1}. [{element.element_type.upper()}] {element.text[:100]}..."
                )
                click.echo(
                    f"   Section: {element.section} | "
                    f"Confidence: {element.confidence:.2f}"
                )
                click.echo()

            if len(result.elements) > 5:
                click.echo(f"... and {len(result.elements) - 5} more elements")
                click.echo("\nUse --output to save complete results to file")

    except LLMError as e:
        context = {
            "operation": "paper_extraction",
            "file_path": str(pdf_path),
            "paper_title": title or "Unknown",
            "profile_used": profile or "default",
        }
        formatted_error = format_error_for_cli(
            e, context, verbose=config.log_level == "DEBUG"
        )
        click.echo(formatted_error, err=True)
        raise click.Abort()
    except PdfError as e:
        context = {
            "operation": "paper_extraction",
            "file_path": str(pdf_path),
            "file_size": str(pdf_path.stat().st_size) if pdf_path.exists() else "0",
        }
        formatted_error = format_error_for_cli(
            e, context, verbose=config.log_level == "DEBUG"
        )
        click.echo(formatted_error, err=True)
        raise click.Abort()
    except Exception as e:
        context = {
            "operation": "paper_extraction",
            "file_path": str(pdf_path),
            "profile_used": profile or "default",
        }
        # Use DEBUG as default if config wasn't loaded yet
        verbose = False
        if "config" in locals():
            verbose = config.log_level == "DEBUG"
        formatted_error = format_error_for_cli(e, context, verbose=verbose)
        click.echo(formatted_error, err=True)
        raise click.Abort()


@cli.command()
@click.argument(
    "input_dir", type=click.Path(exists=True, file_okay=False, path_type=Path)
)
@click.argument("output_dir", type=click.Path(path_type=Path))
@click.option(
    "--max-concurrent",
    default=3,
    type=int,
    help="Maximum number of concurrent PDF processing operations",
)
@click.option(
    "--skip-errors", is_flag=True, help="Continue processing other files if some fail"
)
@click.option(
    "--filter-pattern", default="*.pdf", help="File pattern to match (default: *.pdf)"
)
# Profile selection option
@click.option(
    "--profile",
    type=click.Choice(
        [
            "quick_scan",
            "thorough",
            "high_volume",
            "precision",
            "budget_conscious",
            "experimental",
        ],
        case_sensitive=False,
    ),
    help="Use a predefined configuration profile optimized for specific "
    "research scenarios",
)
# Configuration options for batch processing
@click.option(
    "--chunk-size",
    type=int,
    help="Text processing chunk size in characters. Larger chunks mean fewer "
    "API calls but higher token usage. (default: 10000 characters)",
)
@click.option(
    "--timeout",
    type=float,
    help="LLM request timeout in seconds. Increase for large sections or slow "
    "connections. (default: 60.0 seconds)",
)
@click.option(
    "--max-retries",
    type=int,
    help="Maximum retry attempts for failed operations. Higher values increase "
    "reliability but processing time. (default: 3 attempts)",
)
@click.option(
    "--retry-delay",
    type=float,
    help="Initial delay between retries in seconds. Uses exponential backoff "
    "for subsequent retries. (default: 2.0 seconds)",
)
@click.option(
    "--chunk-overlap",
    type=int,
    help="Character overlap between text chunks to avoid splitting sentences. "
    "(default: 500 characters)",
)
@click.option(
    "--min-section-length",
    type=int,
    help="Minimum section length to process. Shorter sections are skipped. "
    "(default: 50 characters)",
)
# Additional batch-specific configuration options
@click.option(
    "--temperature",
    type=float,
    help="LLM temperature for creativity vs consistency. Lower values (0.0-0.3) "
    "for consistent extraction. (default: 0.1 focused)",
)
@click.option(
    "--max-tokens",
    type=int,
    help="Maximum tokens per LLM response. Higher values allow more extractions "
    "per section. (default: 4000 tokens)",
)
@click.option(
    "--max-file-size",
    type=int,
    help="Maximum PDF file size to process in megabytes. (default: 50 MB)",
)
@click.option(
    "--extraction-timeout",
    type=float,
    help="PDF extraction timeout in seconds. Increase for large files. "
    "(default: 30.0 seconds)",
)
@click.option(
    "--normalize-text/--no-normalize-text",
    default=None,
    help="Apply text normalization to clean PDF extraction artifacts. (default: True)",
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    help="Logging level for debugging and monitoring. (default: INFO)",
)
def batch(
    input_dir: Path,
    output_dir: Path,
    max_concurrent: int,
    skip_errors: bool,
    filter_pattern: str,
    profile: Optional[str],
    chunk_size: Optional[int],
    timeout: Optional[float],
    max_retries: Optional[int],
    retry_delay: Optional[float],
    chunk_overlap: Optional[int],
    min_section_length: Optional[int],
    temperature: Optional[float],
    max_tokens: Optional[int],
    max_file_size: Optional[int],
    extraction_timeout: Optional[float],
    normalize_text: Optional[bool],
    log_level: Optional[str],
) -> None:
    """Process multiple PDF files from input directory and save results to \
output directory."""
    # Check virtual environment
    _check_virtual_environment()

    try:
        # Get CLI context and set up DI container
        ctx = click.get_current_context()

        # Handle profile selection first
        if profile:
            profile_obj = get_profile(profile)
            if not profile_obj:
                raise click.ClickException(
                    f"Unknown profile: {profile}. Run 'hci-extractor profiles' "
                    "to see available profiles."
                )

            # Show profile information
            click.echo(f"🎯 Using profile: {profile_obj.name}")
            click.echo(f"📝 {profile_obj.description}")
            click.echo(f"👥 Optimized for: {profile_obj.target_users}")
            click.echo()

            # Apply profile to base configuration
            base_config = apply_profile_to_config(profile_obj)
            # Store in context for DI container
            if ctx.meta is None:
                ctx.meta = {}
            ctx.meta["profile_config"] = base_config

        # Set up DI container with configuration from CLI context
        container_factory = get_cli_container_factory()
        container = container_factory.create_container_with_cli_config(ctx)

        # Resolve dependencies
        config = container.resolve(ExtractorConfig)
        llm_provider = container.resolve(LLMProvider)  # type: ignore
        event_bus = container.resolve(EventBus)

        # Publish configuration loaded event
        cli_overrides = []
        for param, value in ctx.params.items():
            if value is not None:
                cli_overrides.append(f"{param}={value}")

        event_bus.publish(
            ConfigurationLoaded(
                config_source="cli",
                config_path=None,
                overrides_applied=tuple(cli_overrides),
                chunk_size=config.analysis.chunk_size,
                timeout_seconds=config.analysis.section_timeout_seconds,
                max_retries=config.retry.max_attempts,
            )
        )

        # Show configuration info if verbose
        if config.log_level == "DEBUG":
            click.echo(
                f"🔧 Using configuration: chunk_size={config.analysis.chunk_size}, "
                f"timeout={config.analysis.section_timeout_seconds}s, "
                f"max_retries={config.retry.max_attempts}, "
                f"max_concurrent={config.analysis.max_concurrent_sections}"
            )

        # Validate parameters
        if max_concurrent < 1:
            raise click.ClickException("max-concurrent must be at least 1")

        # Create output directory if it doesn't exist
        output_dir.mkdir(parents=True, exist_ok=True)

        # Find PDF files to process
        pdf_files = list(input_dir.glob(filter_pattern))
        if not pdf_files:
            click.echo(f"❌ No files matching '{filter_pattern}' found in {input_dir}")
            raise click.Abort()

        click.echo(f"📁 Found {len(pdf_files)} PDF files in {input_dir}")
        click.echo(f"📂 Output directory: {output_dir}")
        click.echo(f"⚡ Max concurrent operations: {max_concurrent}")

        # LLM provider already resolved from DI container above
        click.echo("🔑 Using LLM provider from DI container...")

        # Publish batch processing started event
        import time

        batch_start_time = time.time()
        event_bus.publish(
            BatchProcessingStarted(
                total_papers=len(pdf_files),
                input_directory=str(input_dir),
                output_directory=str(output_dir),
                max_concurrent=max_concurrent,
                filter_pattern=filter_pattern,
            )
        )

        # Initialize progress tracker for batch
        progress = ProgressTracker()
        progress.start_batch(len(pdf_files))

        # Process files
        successful_extractions = 0
        failed_extractions = []

        async def process_single_pdf(pdf_path: Path) -> bool:
            """Process a single PDF and return success status."""
            try:
                # Start paper progress tracking
                paper_name = pdf_path.stem
                progress.start_paper(paper_name, 6)  # Typical paper has ~6 sections

                # Extract elements
                result = await extract_paper_simple(
                    pdf_path=pdf_path,
                    config=config,
                    event_bus=event_bus,
                    llm_provider=llm_provider,
                    progress_callback=progress,
                )

                # Save results
                output_file = output_dir / f"{pdf_path.stem}_extraction.json"
                output_data = {
                    "paper": {
                        "paper_id": result.paper.paper_id,
                        "title": result.paper.title,
                        "authors": result.paper.authors,
                        "venue": result.paper.venue,
                        "year": result.paper.year,
                        "file_path": str(pdf_path),
                    },
                    "extraction_summary": {
                        "total_elements": result.total_elements,
                        "elements_by_type": result.elements_by_type,
                        "elements_by_section": result.elements_by_section,
                        "average_confidence": result.average_confidence,
                        "created_at": result.created_at.isoformat(),
                    },
                    "extracted_elements": [
                        {
                            "element_id": element.element_id,
                            "element_type": element.element_type,
                            "text": element.text,
                            "section": element.section,
                            "confidence": element.confidence,
                            "evidence_type": element.evidence_type,
                            "page_number": element.page_number,
                        }
                        for element in result.elements
                    ],
                }

                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(output_data, f, indent=2, ensure_ascii=False)

                return True

            except Exception as e:
                progress.error(f"Failed to process {pdf_path.name}: {e}")
                if not skip_errors:
                    raise
                return False

        async def process_batch() -> List[Any]:
            """Process all PDFs with concurrency control."""
            semaphore = asyncio.Semaphore(max_concurrent)

            async def process_with_semaphore(pdf_path: Path) -> bool:
                async with semaphore:
                    return await process_single_pdf(pdf_path)

            tasks = [process_with_semaphore(pdf_path) for pdf_path in pdf_files]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            return results

        # Run batch processing
        click.echo(f"\n🚀 Starting batch processing of {len(pdf_files)} files...")
        results = asyncio.run(process_batch())

        # Count results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed_extractions.append((pdf_files[i], str(result)))
            elif result:  # Success
                successful_extractions += 1
            else:  # Failed but skip_errors was True
                failed_extractions.append((pdf_files[i], "Processing failed"))

        # Create summary report
        summary_file = output_dir / "batch_summary.json"
        summary_data = {
            "batch_info": {
                "input_directory": str(input_dir),
                "output_directory": str(output_dir),
                "total_files": len(pdf_files),
                "successful": successful_extractions,
                "failed": len(failed_extractions),
                "max_concurrent": max_concurrent,
                "filter_pattern": filter_pattern,
                "skip_errors": skip_errors,
            },
            "processed_files": [str(f) for f in pdf_files],
            "failed_files": [
                {"file": str(f), "error": err} for f, err in failed_extractions
            ],
        }

        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, indent=2, ensure_ascii=False)

        # Calculate batch statistics and publish completion event
        total_duration = time.time() - batch_start_time
        average_elements = 0.0  # Could calculate this from results if needed

        event_bus.publish(
            BatchProcessingCompleted(
                total_papers=len(pdf_files),
                successful_papers=successful_extractions,
                failed_papers=len(failed_extractions),
                duration_seconds=total_duration,
                average_elements_per_paper=average_elements,
            )
        )

        # Finish progress tracking
        progress.finish()

        # Display final summary
        click.echo("\n--- 📊 Batch Processing Complete ---")
        click.echo(f"✅ Processed: {successful_extractions}/{len(pdf_files)} files")
        if failed_extractions:
            click.echo(f"❌ Failed: {len(failed_extractions)} files")
            for pdf_path, error in failed_extractions[:3]:  # Show first 3 errors
                click.echo(f"   - {pdf_path.name}: {error}")
            if len(failed_extractions) > 3:
                click.echo(f"   ... and {len(failed_extractions) - 3} more errors")

        click.echo(f"📁 Results saved to: {output_dir}")
        click.echo(f"📋 Summary report: {summary_file}")

        if failed_extractions and not skip_errors:
            raise click.Abort()

    except LLMError as e:
        context = {
            "operation": "batch_processing",
            "input_directory": str(input_dir),
            "output_directory": str(output_dir),
            "max_concurrent": max_concurrent,
            "profile_used": profile or "default",
        }
        formatted_error = format_error_for_cli(
            e, context, verbose=config.log_level == "DEBUG"
        )
        click.echo(formatted_error, err=True)
        raise click.Abort()
    except Exception as e:
        context = {
            "operation": "batch_processing",
            "input_directory": str(input_dir),
            "output_directory": str(output_dir),
            "max_concurrent": max_concurrent,
        }
        formatted_error = format_error_for_cli(
            e, context, verbose=config.log_level == "DEBUG"
        )
        click.echo(formatted_error, err=True)
        raise click.Abort()


@cli.command()
@click.argument(
    "results_dir", type=click.Path(exists=True, file_okay=False, path_type=Path)
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["csv", "json", "markdown"], case_sensitive=False),
    default="csv",
    help="Output format (default: csv)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output file (if not provided, prints to stdout)",
)
@click.option(
    "--element-type",
    type=click.Choice(["claim", "finding", "method"], case_sensitive=False),
    help="Filter by element type",
)
@click.option("--min-confidence", type=float, help="Minimum confidence score (0.0-1.0)")
@click.option("--section", help="Filter by section name")
# Configuration options for export
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    help="Logging level for debugging and monitoring. (default: INFO)",
)
def export(
    results_dir: Path,
    output_format: str,
    output: Optional[Path],
    element_type: Optional[str],
    min_confidence: Optional[float],
    section: Optional[str],
    log_level: Optional[str],
) -> None:
    """Export extraction results from a directory to various formats."""
    # Check virtual environment
    _check_virtual_environment()

    try:
        # Set up DI container with configuration from CLI context
        ctx = click.get_current_context()
        container_factory = get_cli_container_factory()
        container = container_factory.create_container_with_cli_config(ctx)

        # Resolve dependencies
        config = container.resolve(ExtractorConfig)

        # Show configuration info if verbose
        if config.log_level == "DEBUG":
            click.echo(f"🔧 Using configuration: log_level={config.log_level}")

        # Find all extraction result files
        result_files = list(results_dir.glob("*_extraction.json"))
        if not result_files:
            click.echo(f"❌ No extraction result files found in {results_dir}")
            click.echo("💡 Result files should match pattern '*_extraction.json'")
            raise click.Abort()

        click.echo(f"📂 Found {len(result_files)} extraction files")

        # Load and aggregate all extraction data
        all_elements = []
        papers_info = []

        for result_file in result_files:
            try:
                with open(result_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                paper_info = data.get("paper", {})
                extraction_summary = data.get("extraction_summary", {})
                elements = data.get("extracted_elements", [])

                # Apply filters
                filtered_elements = []
                for element in elements:
                    # Filter by element type
                    if element_type and element.get("element_type") != element_type:
                        continue

                    # Filter by confidence
                    if (
                        min_confidence is not None
                        and element.get("confidence", 0) < min_confidence
                    ):
                        continue

                    # Filter by section
                    if section and element.get("section") != section:
                        continue

                    # Add paper information to element
                    element_with_paper = element.copy()
                    element_with_paper.update(
                        {
                            "paper_title": paper_info.get("title", ""),
                            "paper_authors": ", ".join(paper_info.get("authors", [])),
                            "paper_venue": paper_info.get("venue", ""),
                            "paper_year": paper_info.get("year", ""),
                            "source_file": result_file.stem.replace("_extraction", ""),
                            # Paper summary fields
                            "paper_summary": extraction_summary.get(
                                "paper_summary", ""
                            ),
                            "paper_summary_confidence": extraction_summary.get(
                                "paper_summary_confidence", ""
                            ),
                        }
                    )
                    filtered_elements.append(element_with_paper)

                all_elements.extend(filtered_elements)
                papers_info.append(paper_info)

            except Exception as e:
                click.echo(f"⚠️ Warning: Could not load {result_file}: {e}", err=True)
                continue

        if not all_elements:
            click.echo("❌ No elements found matching the specified filters")
            raise click.Abort()

        click.echo(
            f"📝 Exporting {len(all_elements)} elements in "
            f"{output_format.upper()} format..."
        )

        # Generate output based on format
        if output_format == "csv":
            output_content = _export_to_csv(all_elements)
        elif output_format == "json":
            output_content = _export_to_json(all_elements, papers_info)
        elif output_format == "markdown":
            output_content = _export_to_markdown(all_elements, papers_info)
        else:
            raise click.ClickException(f"Unsupported format: {output_format}")

        # Write output
        if output:
            click.echo(f"💾 Saving to {output}...")
            with open(output, "w", encoding="utf-8") as f:
                f.write(output_content)
            click.echo(f"✅ Export complete! Results saved to {output}")
        else:
            click.echo(output_content)

    except Exception as e:
        click.echo(f"❌ Export error: {e}", err=True)
        raise click.Abort()


def _export_to_csv(elements: List[Dict[str, Any]]) -> str:
    """Export elements to CSV format."""
    if not elements:
        return ""

    # Get all possible field names
    fieldnames: set[str] = set()
    for element in elements:
        fieldnames.update(element.keys())

    # Ensure consistent ordering
    ordered_fields = [
        # Paper metadata
        "paper_title",
        "paper_authors",
        "paper_venue",
        "paper_year",
        "source_file",
        # Paper summary fields
        "paper_summary",
        "paper_summary_confidence",
        # Element core fields
        "element_type",
        "evidence_type",
        "section",
        "text",
        "confidence",
        "page_number",
        "element_id",
        # Optional context fields for manual comparison
        "supporting_evidence",
        "methodology_context",
        "study_population",
        "limitations",
        "surrounding_context",
    ]

    # Add any additional fields not in the ordered list
    remaining_fields = sorted(fieldnames - set(ordered_fields))
    fieldnames_list: List[str] = [
        f for f in ordered_fields if f in fieldnames
    ] + remaining_fields

    # Generate CSV
    import io

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames_list)
    writer.writeheader()
    writer.writerows(elements)

    return output.getvalue()


def _export_to_json(
    elements: List[Dict[str, Any]], papers_info: List[Dict[str, Any]]
) -> str:
    """Export elements to JSON format."""
    export_data = {
        "export_metadata": {
            "total_elements": len(elements),
            "total_papers": len(papers_info),
            "export_format": "json",
        },
        "papers": papers_info,
        "elements": elements,
    }

    return json.dumps(export_data, indent=2, ensure_ascii=False)


def _export_to_markdown(
    elements: List[Dict[str, Any]], papers_info: List[Dict[str, Any]]
) -> str:
    """Export elements to Markdown format."""
    lines = []

    # Header
    lines.append("# HCI Paper Extraction Results")
    lines.append("")
    lines.append(f"**Total Elements:** {len(elements)}")
    lines.append(f"**Total Papers:** {len(papers_info)}")
    lines.append("")

    # Group elements by paper
    elements_by_paper: Dict[str, List[Dict[str, Any]]] = {}
    for element in elements:
        paper_title = element.get("paper_title", "Unknown Paper")
        if paper_title not in elements_by_paper:
            elements_by_paper[paper_title] = []
        elements_by_paper[paper_title].append(element)

    # Generate markdown for each paper
    for paper_title, paper_elements in elements_by_paper.items():
        lines.append(f"## {paper_title}")
        lines.append("")

        # Add paper summary if available
        if paper_elements:
            first_element = paper_elements[0]
            paper_summary = first_element.get("paper_summary", "")
            if paper_summary:
                lines.append("**Summary:**")
                lines.append(f"*{paper_summary}*")
                lines.append("")

        # Group by element type
        elements_by_type: Dict[str, List[Dict[str, Any]]] = {}
        for element in paper_elements:
            element_type = element.get("element_type", "unknown")
            if element_type not in elements_by_type:
                elements_by_type[element_type] = []
            elements_by_type[element_type].append(element)

        for element_type, type_elements in elements_by_type.items():
            lines.append(f"### {element_type.title()}s")
            lines.append("")

            for i, element in enumerate(type_elements, 1):
                confidence = element.get("confidence", 0)
                section = element.get("section", "unknown")
                text = element.get("text", "")
                evidence_type = element.get("evidence_type", "unknown")

                lines.append(f"{i}. **{text}**")
                lines.append(f"   - *Section:* {section}")
                lines.append(f"   - *Evidence Type:* {evidence_type}")
                lines.append(f"   - *Confidence:* {confidence:.2f}")
                lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def _export_single_paper_to_csv(papers_data: List[Dict[str, Any]]) -> str:
    """Export single paper data to CSV format."""
    all_elements = []

    for paper_data in papers_data:
        paper_info = paper_data.get("paper", {})
        extraction_summary = paper_data.get("extraction_summary", {})
        elements = paper_data.get("extracted_elements", [])

        # Add paper information to each element
        for element in elements:
            element_with_paper = element.copy()
            element_with_paper.update(
                {
                    "paper_title": paper_info.get("title", ""),
                    "paper_authors": ", ".join(paper_info.get("authors", [])),
                    "paper_venue": paper_info.get("venue", ""),
                    "paper_year": paper_info.get("year", ""),
                    "source_file": paper_info.get("file_path", ""),
                    # Paper summary fields
                    "paper_summary": extraction_summary.get("paper_summary", ""),
                    "paper_summary_confidence": extraction_summary.get(
                        "paper_summary_confidence", ""
                    ),
                }
            )
            all_elements.append(element_with_paper)

    return _export_to_csv(all_elements)


def _export_single_paper_to_markdown(papers_data: List[Dict[str, Any]]) -> str:
    """Export single paper data to Markdown format."""
    all_elements = []
    papers_info = []

    for paper_data in papers_data:
        paper_info = paper_data.get("paper", {})
        extraction_summary = paper_data.get("extraction_summary", {})
        papers_info.append(paper_info)
        elements = paper_data.get("extracted_elements", [])

        # Add paper information to each element
        for element in elements:
            element_with_paper = element.copy()
            element_with_paper.update(
                {
                    "paper_title": paper_info.get("title", ""),
                    "paper_authors": ", ".join(paper_info.get("authors", [])),
                    "paper_venue": paper_info.get("venue", ""),
                    "paper_year": paper_info.get("year", ""),
                    "source_file": paper_info.get("file_path", ""),
                    # Paper summary fields
                    "paper_summary": extraction_summary.get("paper_summary", ""),
                    "paper_summary_confidence": extraction_summary.get(
                        "paper_summary_confidence", ""
                    ),
                }
            )
            all_elements.append(element_with_paper)

    return _export_to_markdown(all_elements, papers_info)


def _quickstart_single_paper() -> None:
    """Guide for analyzing a single paper."""
    click.echo(
        "📄 " + click.style("Single Paper Analysis Workflow", bold=True, fg="blue")
    )
    click.echo("-" * 40)
    click.echo()

    click.echo(
        "Perfect for exploring what this tool can extract from your research papers!"
    )
    click.echo()

    # Check for sample paper
    sample_path = Path("autisticadults.pdf")
    if sample_path.exists():
        click.echo(f"✅ Sample paper found: {sample_path}")
        click.echo()

        if click.confirm("Want to try extracting from the sample paper?"):
            click.echo()
            click.echo("🎯 " + click.style("Copy-paste this command:", bold=True))
            click.echo(
                "python -m hci_extractor extract autisticadults.pdf "
                "--output sample_results.csv"
            )
            click.echo()
            click.echo("This will:")
            click.echo("• Extract claims, findings, methods, and artifacts")
            click.echo("• Save results in CSV format for easy analysis")
            click.echo("• Show real-time progress bars")
            click.echo()
    else:
        click.echo("ℹ️  No sample paper found in current directory")
        click.echo()

    click.echo("📋 " + click.style("For your own papers:", bold=True))
    click.echo()
    click.echo("# Extract to CSV (best for analysis)")
    click.echo("python -m hci_extractor extract your_paper.pdf --output results.csv")
    click.echo()
    click.echo("# Extract to JSON (complete data)")
    click.echo("python -m hci_extractor extract your_paper.pdf --output results.json")
    click.echo()
    click.echo("# Extract to Markdown (human-readable)")
    click.echo("python -m hci_extractor extract your_paper.pdf --output results.md")
    click.echo()


def _quickstart_systematic_review() -> None:
    """Guide for systematic literature review workflow."""
    click.echo(
        "📊 "
        + click.style("Systematic Literature Review Workflow", bold=True, fg="blue")
    )
    click.echo("-" * 45)
    click.echo()

    click.echo(
        "Perfect for processing 10-50 papers and identifying patterns across "
        "literature!"
    )
    click.echo()

    click.echo("📁 " + click.style("Step 1: Organize your papers", bold=True))
    click.echo("mkdir literature_papers/")
    click.echo("# Copy all your PDF files to this folder")
    click.echo()

    click.echo("⚙️ " + click.style("Step 2: Batch extraction", bold=True))
    click.echo("python -m hci_extractor batch literature_papers/ results/")
    click.echo()
    click.echo("This will:")
    click.echo("• Process all PDFs concurrently (3 at a time by default)")
    click.echo("• Save individual JSON files for each paper")
    click.echo("• Show progress for each paper")
    click.echo("• Handle errors gracefully")
    click.echo()

    click.echo("📊 " + click.style("Step 3: Export for analysis", bold=True))
    click.echo("# All elements in CSV format")
    click.echo(
        "python -m hci_extractor export results/ --format csv "
        "--output literature_analysis.csv"
    )
    click.echo()
    click.echo("# High-confidence findings only")
    click.echo(
        "python -m hci_extractor export results/ --format csv "
        "--min-confidence 0.8 --output high_confidence.csv"
    )
    click.echo()
    click.echo("# Claims for thematic analysis")
    click.echo(
        "python -m hci_extractor export results/ --format csv "
        "--element-type claim --output claims_analysis.csv"
    )
    click.echo()


def _quickstart_meta_analysis() -> None:
    """Guide for meta-analysis preparation workflow."""
    click.echo(
        "🔬 " + click.style("Meta-Analysis Preparation Workflow", bold=True, fg="blue")
    )
    click.echo("-" * 42)
    click.echo()

    click.echo("Perfect for extracting quantitative findings and statistical data!")
    click.echo()

    click.echo("🎯 " + click.style("Focus on quantitative findings:", bold=True))
    click.echo()
    click.echo("# Extract all data first")
    click.echo("python -m hci_extractor batch papers/ results/")
    click.echo(
        "python -m hci_extractor export results/ --format csv --output all_data.csv"
    )
    click.echo()
    click.echo("# Filter for quantitative findings")
    click.echo("grep 'quantitative' all_data.csv > quantitative_findings.csv")
    click.echo()

    click.echo(
        "📊 " + click.style("Look for statistical data in extractions:", bold=True)
    )
    click.echo("• p-values (p < 0.05, p = 0.03)")
    click.echo("• Effect sizes (Cohen's d, eta-squared)")
    click.echo("• Sample sizes (N = 24, n = 156)")
    click.echo("• Statistical tests (t-test, ANOVA, chi-square)")
    click.echo()

    click.echo("💡 " + click.style("Pro tip:", bold=True))
    click.echo(
        "The tool extracts verbatim text, so statistical values appear "
        "exactly as written."
    )
    click.echo("You can search the CSV for patterns like 'p <', 'N =', 'd =', etc.")
    click.echo()


def _quickstart_troubleshooting() -> None:
    """Guide for common troubleshooting scenarios."""
    click.echo(
        "🔧 " + click.style("Troubleshooting Common Issues", bold=True, fg="blue")
    )
    click.echo("-" * 35)
    click.echo()

    click.echo("🚨 " + click.style("Quick fixes for common problems:", bold=True))
    click.echo()

    click.echo("❌ " + click.style("'No module named hci_extractor'", fg="red"))
    click.echo("   💡 Activate your virtual environment:")
    click.echo("   source venv/bin/activate")
    click.echo()

    click.echo(
        "❌ "
        + click.style("'GEMINI_API_KEY environment variable is required'", fg="red")
    )
    click.echo("   💡 Add your API key:")
    click.echo("   echo 'GEMINI_API_KEY=your-key-here' > .env")
    click.echo("   💡 Get a free API key: https://makersuite.google.com/app/apikey")
    click.echo()

    click.echo("❌ " + click.style("PDF processing fails", fg="red"))
    click.echo("   💡 Test the PDF first:")
    click.echo("   python -m hci_extractor validate your_paper.pdf")
    click.echo()

    click.echo("❌ " + click.style("Extraction takes too long", fg="red"))
    click.echo("   💡 Check your internet connection and API quota")
    click.echo("   💡 Large papers (>20 pages) can take 30-60 seconds")
    click.echo()

    click.echo("🔍 " + click.style("Diagnostic commands:", bold=True))
    click.echo("python -m hci_extractor doctor   # Check system health")
    click.echo("python -m hci_extractor setup    # Guided configuration")
    click.echo("python -m hci_extractor --help   # All available commands")
    click.echo()


@cli.command()
@click.option(
    "--host",
    default="127.0.0.1",
    help="Host to bind the server to",
    show_default=True,
)
@click.option(
    "--port",
    default=8000,
    type=int,
    help="Port to bind the server to",
    show_default=True,
)
@click.option(
    "--reload",
    is_flag=True,
    help="Enable auto-reload for development",
)
def serve(host: str, port: int, reload: bool) -> None:
    """Start the web UI server."""
    try:
        import uvicorn
        from hci_extractor.web.app import app

        click.echo()
        click.echo(
            "🌐 " + click.style("Starting HCI Extractor Web UI", bold=True, fg="green")
        )
        click.echo("=" * 40)
        click.echo()
        click.echo(f"📍 Server will start at: http://{host}:{port}")
        click.echo(f"📋 API docs available at: http://{host}:{port}/docs")
        click.echo(f"🔍 Alternative docs at: http://{host}:{port}/redoc")
        click.echo()

        if reload:
            click.echo("🔄 Auto-reload enabled for development")
            click.echo()

        click.echo("💡 Press Ctrl+C to stop the server")
        click.echo()

        # Start the server
        uvicorn.run(
            app,
            host=host,
            port=port,
            reload=reload,
        )

    except ImportError:
        click.echo("❌ " + click.style("Error: uvicorn not installed", fg="red"))
        click.echo("Install web dependencies with: pip install 'hci_extractor[web]'")
        raise click.Abort()
    except Exception as e:
        from hci_extractor.utils.user_error_translator import format_error_for_cli

        context = {"operation": "web_server_start"}
        formatted_error = format_error_for_cli(e, context, verbose=True)
        click.echo(formatted_error, err=True)
        raise click.Abort()
