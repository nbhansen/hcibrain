"""
Configuration profiles for common research scenarios.

This module provides preset configurations optimized for different types
of academic research workflows, making it easier for users to get started
with appropriate settings for their specific use case.
"""

from dataclasses import dataclass, replace
from typing import Any, Dict, Optional

from hci_extractor.core.config import ExtractorConfig


@dataclass(frozen=True)
class ConfigProfile:
    """Definition of a configuration profile for specific research scenarios."""

    name: str
    description: str
    use_case: str
    target_users: str
    config_overrides: Dict[str, Any]
    recommended_commands: tuple[str, ...]
    tips: tuple[str, ...]


# Predefined configuration profiles for common research scenarios
RESEARCH_PROFILES: Dict[str, ConfigProfile] = {
    "quick_scan": ConfigProfile(
        name="Quick Scan",
        description="Fast preliminary analysis for initial paper review",
        use_case="Quick exploration of papers to identify relevant content",
        target_users="Researchers doing initial literature screening",
        config_overrides={
            "analysis.chunk_size": 15000,  # Larger chunks for speed
            "analysis.temperature": 0.2,  # Consistent but fast
            "analysis.max_output_tokens": 3000,  # Fewer tokens for speed
            "retry.max_attempts": 2,  # Fewer retries for speed
            "analysis.min_section_length": 100,  # Skip very short sections
        },
        recommended_commands=(
            "hci-extractor extract paper.pdf --profile quick_scan",
            "hci-extractor batch papers/ results/ --profile quick_scan "
            "--max-concurrent 5",
        ),
        tips=(
            "Optimized for speed over completeness",
            "Good for initial paper screening and relevance assessment",
            "Use higher concurrency for batch processing",
            "Consider upgrading to 'thorough' profile for important papers",
        ),
    ),
    "thorough": ConfigProfile(
        name="Thorough Analysis",
        description="Comprehensive extraction for systematic literature reviews",
        use_case="Detailed analysis for systematic reviews and meta-analyses",
        target_users="Researchers conducting systematic literature reviews",
        config_overrides={
            "analysis.chunk_size": 8000,  # Smaller chunks for thoroughness
            "analysis.chunk_overlap": 800,  # More overlap for context
            "analysis.temperature": 0.1,  # Very consistent extraction
            "analysis.max_output_tokens": 4000,  # More detailed extractions
            "retry.max_attempts": 4,  # More retries for reliability
            "analysis.min_section_length": 25,  # Process even short sections
            "analysis.section_timeout_seconds": 90.0,  # Longer timeout
        },
        recommended_commands=(
            "hci-extractor extract paper.pdf --profile thorough",
            "hci-extractor batch papers/ results/ --profile thorough "
            "--max-concurrent 2",
        ),
        tips=(
            "Optimized for completeness and accuracy",
            "Best for systematic literature reviews",
            "Use lower concurrency to avoid API rate limits",
            "Results suitable for meta-analysis and citation analysis",
        ),
    ),
    "high_volume": ConfigProfile(
        name="High Volume",
        description="Optimized for processing large numbers of papers efficiently",
        use_case="Batch processing of 50+ papers with balanced speed/quality",
        target_users="Researchers processing large literature datasets",
        config_overrides={
            "analysis.chunk_size": 12000,  # Balanced chunk size
            "analysis.temperature": 0.15,  # Slight randomness for robustness
            "analysis.max_concurrent_sections": 2,  # Conservative concurrency
            "retry.max_attempts": 3,  # Standard retry count
            "retry.initial_delay_seconds": 3.0,  # Longer delays for API limits
            "retry.max_delay_seconds": 60.0,  # Longer max delay
            "cache.enabled": True,  # Enable caching for efficiency
        },
        recommended_commands=(
            "hci-extractor batch large_corpus/ results/ --profile high_volume "
            "--max-concurrent 3",
            "hci-extractor export results/ --format csv --min-confidence 0.3",
        ),
        tips=(
            "Balanced approach for large-scale processing",
            "Uses caching to avoid reprocessing",
            "Conservative retry settings to avoid API issues",
            "Consider filtering results by confidence for analysis",
        ),
    ),
    "precision": ConfigProfile(
        name="Precision Focus",
        description="Maximum accuracy for critical research with high standards",
        use_case="High-stakes research requiring maximum extraction accuracy",
        target_users="Meta-analysis researchers, evidence synthesis experts",
        config_overrides={
            "analysis.chunk_size": 6000,  # Small chunks for precision
            "analysis.chunk_overlap": 1000,  # High overlap for context
            "analysis.temperature": 0.05,  # Minimal randomness
            "analysis.max_output_tokens": 5000,  # Detailed extractions
            "retry.max_attempts": 5,  # Maximum retries
            "analysis.min_section_length": 10,  # Process all content
            "analysis.section_timeout_seconds": 120.0,  # Extended timeout
            "export.min_confidence_threshold": 0.4,  # Higher quality filter
        },
        recommended_commands=(
            "hci-extractor extract paper.pdf --profile precision",
            "hci-extractor validate paper.pdf  # Always validate first",
            "hci-extractor export results/ --format json --min-confidence 0.5",
        ),
        tips=(
            "Maximum accuracy at the cost of speed",
            "Always validate PDFs before processing",
            "Manual review of results recommended",
            "Best for high-impact research and publications",
        ),
    ),
    "budget_conscious": ConfigProfile(
        name="Budget Conscious",
        description="Minimize API costs while maintaining reasonable quality",
        use_case="Research with limited API budget or token allowances",
        target_users="Students, independent researchers, cost-sensitive projects",
        config_overrides={
            "analysis.chunk_size": 20000,  # Large chunks to minimize calls
            "analysis.temperature": 0.3,  # Slightly higher for efficiency
            "analysis.max_output_tokens": 2500,  # Fewer tokens per call
            "retry.max_attempts": 2,  # Minimal retries
            "analysis.min_section_length": 200,  # Skip small sections
            "analysis.max_concurrent_sections": 1,  # Sequential processing
        },
        recommended_commands=(
            "hci-extractor extract paper.pdf --profile budget_conscious",
            "hci-extractor batch papers/ results/ --profile budget_conscious "
            "--skip-errors",
        ),
        tips=(
            "Minimizes API calls and token usage",
            "Use --skip-errors to avoid retry costs",
            "Focus on core sections (abstract, results, discussion)",
            "Consider pre-filtering papers by relevance",
        ),
    ),
    "experimental": ConfigProfile(
        name="Experimental",
        description="Advanced settings for testing new approaches and features",
        use_case="Research methodology development and feature testing",
        target_users="Advanced users, methodology researchers, tool developers",
        config_overrides={
            "analysis.chunk_size": 10000,
            "analysis.temperature": 0.0,  # Deterministic for repeatability
            "analysis.max_output_tokens": 6000,  # Maximum detail
            "retry.max_attempts": 3,
            "log_level": "DEBUG",  # Detailed logging
            "extraction.normalize_text": True,  # Advanced text processing
            "cache.enabled": True,  # Enable caching for experiments
        },
        recommended_commands=(
            "hci-extractor extract paper.pdf --profile experimental --log-level DEBUG",
            "hci-extractor config  # Review all available options",
        ),
        tips=(
            "Includes debug logging for analysis",
            "Deterministic settings for reproducible results",
            "Use for developing new extraction approaches",
            "Review logs to understand processing details",
        ),
    ),
}


def get_profile(profile_name: str) -> Optional[ConfigProfile]:
    """Get a configuration profile by name."""
    return RESEARCH_PROFILES.get(profile_name.lower())


def list_available_profiles() -> Dict[str, ConfigProfile]:
    """List all available configuration profiles."""
    return RESEARCH_PROFILES.copy()


def apply_profile_to_config(
    profile: ConfigProfile,
    base_config: Optional[ExtractorConfig] = None,
) -> ExtractorConfig:
    """
    Apply a configuration profile to create a new configuration.

    Args:
        profile: The configuration profile to apply
        base_config: Base configuration (defaults to system config)

    Returns:
        New ExtractorConfig with profile settings applied
    """
    if base_config is None:
        base_config = ExtractorConfig.from_yaml()

    # Build override dictionary in the expected nested structure
    overrides: Dict[str, Any] = {}

    for path, value in profile.config_overrides.items():
        # Split the path and create nested structure
        parts = path.split(".")
        current = overrides

        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        current[parts[-1]] = value

    # Apply overrides to create new configuration objects
    new_extraction = base_config.extraction
    if "extraction" in overrides:
        new_extraction = replace(base_config.extraction, **overrides["extraction"])

    new_analysis = base_config.analysis
    if "analysis" in overrides:
        new_analysis = replace(base_config.analysis, **overrides["analysis"])

    new_retry = base_config.retry
    if "retry" in overrides:
        new_retry = replace(base_config.retry, **overrides["retry"])

    new_cache = base_config.cache
    if "cache" in overrides:
        new_cache = replace(base_config.cache, **overrides["cache"])

    new_export = base_config.export
    if "export" in overrides:
        new_export = replace(base_config.export, **overrides["export"])

    # Create new main configuration
    return replace(
        base_config,
        extraction=new_extraction,
        analysis=new_analysis,
        retry=new_retry,
        cache=new_cache,
        export=new_export,
        log_level=overrides.get("log_level", base_config.log_level),
    )


def recommend_profile_for_use_case(
    paper_count: int,
    time_constraint: str,  # "urgent", "normal", "flexible"
    quality_requirement: str,  # "draft", "standard", "publication"
    budget_constraint: str,  # "tight", "moderate", "flexible"
) -> tuple[str, str]:
    """
    Recommend a configuration profile based on research parameters.

    Args:
        paper_count: Number of papers to process
        time_constraint: Time available for processing
        quality_requirement: Quality level needed
        budget_constraint: API budget constraints

    Returns:
        Tuple of (profile_name, reasoning)
    """
    # Budget is the primary constraint
    if budget_constraint == "tight":
        return "budget_conscious", "Budget constraints require minimizing API costs"

    # Quality is highest priority for publication work
    if quality_requirement == "publication":
        return "precision", "Publication-quality work requires maximum accuracy"

    # Large volume processing
    if paper_count > 50:
        return (
            "high_volume",
            "Large number of papers requires efficient batch processing",
        )

    # Time-sensitive work
    if time_constraint == "urgent":
        return "quick_scan", "Urgent timeline requires fast processing"

    # Systematic review work (high quality, moderate volume)
    if quality_requirement == "standard" and paper_count > 10:
        return "thorough", "Systematic review work benefits from thorough analysis"

    # Default recommendation
    return "thorough", "Balanced approach suitable for most academic research"


def get_profile_comparison() -> Dict[str, Dict[str, Any]]:
    """
    Get a comparison matrix of all profiles for decision making.

    Returns:
        Dictionary with profile characteristics for comparison
    """
    comparison = {}

    for name, profile in RESEARCH_PROFILES.items():
        comparison[name] = {
            "description": profile.description,
            "target_users": profile.target_users,
            "speed": _estimate_speed(profile),
            "accuracy": _estimate_accuracy(profile),
            "cost": _estimate_cost(profile),
            "best_for": profile.use_case,
        }

    return comparison


def _estimate_speed(profile: ConfigProfile) -> str:
    """Estimate processing speed based on profile settings."""
    chunk_size = profile.config_overrides.get("analysis.chunk_size", 10000)
    retries = profile.config_overrides.get("retry.max_attempts", 3)

    if chunk_size > 15000 and retries <= 2:
        return "Fast"
    if chunk_size < 8000 or retries >= 4:
        return "Slow"
    return "Moderate"


def _estimate_accuracy(profile: ConfigProfile) -> str:
    """Estimate extraction accuracy based on profile settings."""
    chunk_size = profile.config_overrides.get("analysis.chunk_size", 10000)
    temperature = profile.config_overrides.get("analysis.temperature", 0.1)
    overlap = profile.config_overrides.get("analysis.chunk_overlap", 500)

    if chunk_size <= 8000 and temperature <= 0.1 and overlap >= 800:
        return "High"
    if chunk_size >= 15000 or temperature >= 0.3:
        return "Moderate"
    return "Good"


def _estimate_cost(profile: ConfigProfile) -> str:
    """Estimate API cost based on profile settings."""
    chunk_size = profile.config_overrides.get("analysis.chunk_size", 10000)
    max_tokens = profile.config_overrides.get("analysis.max_output_tokens", 4000)
    retries = profile.config_overrides.get("retry.max_attempts", 3)

    if chunk_size >= 15000 and max_tokens <= 3000 and retries <= 2:
        return "Low"
    if chunk_size <= 8000 or max_tokens >= 5000 or retries >= 4:
        return "High"
    return "Moderate"
