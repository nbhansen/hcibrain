"""Processing commands for PDF extraction and validation."""

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import click

from hci_extractor.cli.cli_configuration_service import get_cli_container_factory
from hci_extractor.cli.config_options import CLI_CONFIG_MAPPING, validate_cli_value
from hci_extractor.cli.config_profiles import (
    apply_profile_to_config,
    get_profile,
)
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
from hci_extractor.core.models.exceptions import (
    ClickParameterError,
    ClickProfileError,
)
from hci_extractor.providers import LLMProvider
from hci_extractor.utils.user_error_translator import format_error_for_cli


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
        for _opt_name, option in CLI_CONFIG_MAPPING.items():
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
                        f"{validated_value} (adjusted to valid range)",
                    )
            except click.BadParameter as e:
                from hci_extractor.core.models.exceptions import ConfigurationError

                error = ConfigurationError(str(e))
                context = {
                    "operation": "configuration_validation",
                    "parameter": param_name,
                    "value": param_value,
                }
                formatted_error = format_error_for_cli(error, context)
                click.echo(formatted_error, err=True)
                raise click.Abort() from e

    # Display warnings if any values were adjusted
    if warnings:
        click.echo("Configuration adjustments:", err=True)
        for warning in warnings:
            click.echo(warning, err=True)
        click.echo()


def _check_virtual_environment() -> None:
    """Check if we're running in a virtual environment."""
    # This is a safety check to help users avoid installation issues
    import sys

    if not hasattr(sys, "real_prefix") and not (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    ):
        click.echo(
            "⚠️  WARNING: You don't appear to be in a virtual environment. "
            "This can cause dependency conflicts.",
            err=True,
        )
        click.echo(
            "   Consider running: python -m venv venv && source venv/bin/activate",
            err=True,
        )
        click.echo()


def _export_single_paper_to_csv(papers_data: List[Dict[str, Any]]) -> str:
    """Export single paper data to CSV format."""
    from hci_extractor.cli.commands.export_utils import _export_to_csv

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
                        "paper_summary_confidence", "",
                    ),
                },
            )
            all_elements.append(element_with_paper)

    return _export_to_csv(all_elements)


def _export_single_paper_to_markdown(papers_data: List[Dict[str, Any]]) -> str:
    """Export single paper data to Markdown format."""
    from hci_extractor.cli.commands.export_utils import _export_to_markdown

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
                        "paper_summary_confidence", "",
                    ),
                },
            )
            all_elements.append(element_with_paper)

    return _export_to_markdown(all_elements, papers_info)


@click.command()
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
    """Extract academic elements (claims, findings, methods) from a PDF using LLM analysis.

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
                raise ClickProfileError()

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
                f"temperature={config.analysis.temperature}",
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
                [author.strip() for author in authors.split(",")],
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
            ),
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
                    "paper_summary_confidence",
                ),
                "paper_summary_sources": result.extraction_metadata.get(
                    "paper_summary_sources",
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
                    f"✅ Extraction complete! Markdown results saved to {output}",
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
                    f"{i+1}. [{element.element_type.upper()}] {element.text[:100]}...",
                )
                click.echo(
                    f"   Section: {element.section} | "
                    f"Confidence: {element.confidence:.2f}",
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
            e, context, verbose=config.log_level == "DEBUG",
        )
        click.echo(formatted_error, err=True)
        raise click.Abort() from e
    except PdfError as e:
        context = {
            "operation": "paper_extraction",
            "file_path": str(pdf_path),
            "file_size": str(pdf_path.stat().st_size) if pdf_path.exists() else "0",
        }
        formatted_error = format_error_for_cli(
            e, context, verbose=config.log_level == "DEBUG",
        )
        click.echo(formatted_error, err=True)
        raise click.Abort() from e
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
        raise click.Abort() from e


@click.command()
@click.argument("pdf_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output file for extracted text (default: stdout)",
)
@click.option(
    "--normalize/--no-normalize",
    default=True,
    help="Apply text normalization to clean PDF extraction artifacts",
)
def parse(pdf_path: Path, output: Optional[Path], normalize: bool) -> None:
    """Extract text content from PDF without LLM analysis.

    This command extracts raw text from PDF files for debugging or
    manual review purposes. Use 'extract' for full LLM-based analysis.
    """
    _check_virtual_environment()

    try:
        # Initialize dependencies
        normalizer = TextNormalizer() if normalize else None

        # Create PDF extractor with basic configuration
        config = ExtractorConfig()  # Default config
        extractor = PdfExtractor(config)

        # Extract text
        click.echo(f"📄 Extracting text from {pdf_path}...")
        text = extractor.extract_text(pdf_path)

        # Apply normalization if requested
        if normalizer and text:
            text = normalizer.normalize(text)

        if not text:
            click.echo("❌ No text could be extracted from the PDF", err=True)
            raise click.Abort()

        # Output results
        if output:
            with open(output, "w", encoding="utf-8") as f:
                f.write(text)
            click.echo(f"✅ Text extracted to {output}")
            click.echo(f"📊 Total characters: {len(text):,}")
        else:
            # Output to stdout with pagination
            lines = text.split("\n")
            click.echo(f"📊 Extracted {len(lines):,} lines, {len(text):,} characters\n")
            click.echo_via_pager(text)

    except Exception as e:
        context = {
            "operation": "text_extraction",
            "file_path": str(pdf_path),
            "normalize": normalize,
        }
        formatted_error = format_error_for_cli(e, context)
        click.echo(formatted_error, err=True)
        raise click.Abort() from e


@click.command()
@click.argument("pdf_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--max-file-size",
    type=int,
    default=50,
    help="Maximum file size in MB (default: 50)",
)
@click.option(
    "--extraction-timeout",
    type=float,
    default=30.0,
    help="Extraction timeout in seconds (default: 30.0)",
)
@click.option(
    "--normalize-text/--no-normalize-text",
    default=True,
    help="Apply text normalization (default: True)",
)
def validate(
    pdf_path: Path,
    max_file_size: int,
    extraction_timeout: float,
    normalize_text: bool,
) -> None:
    """Validate that a PDF can be processed by the extractor.

    This command performs comprehensive validation including:
    - File size and format checks
    - Text extraction capability
    - Structural analysis

    Use this before running expensive LLM extraction operations.
    """
    _check_virtual_environment()

    try:
        click.echo(f"🔍 Validating PDF: {pdf_path}")
        click.echo()

        # File size check
        file_size_mb = pdf_path.stat().st_size / (1024 * 1024)
        click.echo(f"📏 File size: {file_size_mb:.1f} MB")

        if file_size_mb > max_file_size:
            click.echo(
                f"❌ File too large (>{max_file_size} MB). "
                f"Use --max-file-size to override.",
                err=True,
            )
            raise click.Abort()

        # Create basic configuration for validation
        config = ExtractorConfig()
        extractor = PdfExtractor(config)

        # Test text extraction
        click.echo("📄 Testing text extraction...")
        try:
            import time

            start_time = time.time()
            text = extractor.extract_text(pdf_path)
            extraction_time = time.time() - start_time

            if extraction_time > extraction_timeout:
                click.echo(
                    f"⚠️  Extraction took {extraction_time:.1f}s "
                    f"(>{extraction_timeout}s timeout)",
                    err=True,
                )
            else:
                click.echo(f"✅ Text extracted in {extraction_time:.1f}s")

        except Exception as e:
            click.echo(f"❌ Text extraction failed: {e!s}", err=True)
            raise click.Abort() from e

        # Analyze extracted content
        if not text or len(text.strip()) < 100:
            click.echo("❌ Insufficient text content extracted", err=True)
            raise click.Abort()

        # Text statistics
        lines = text.split("\n")
        words = len(text.split())
        click.echo("📊 Content analysis:")
        click.echo(f"   • {len(text):,} characters")
        click.echo(f"   • {len(lines):,} lines")
        click.echo(f"   • {words:,} words")

        # Test normalization if enabled
        if normalize_text:
            click.echo("🧹 Testing text normalization...")
            try:
                normalizer = TextNormalizer()
                normalized = normalizer.normalize(text)
                reduction = len(text) - len(normalized)
                if reduction > 0:
                    click.echo(f"✅ Normalization cleaned {reduction:,} characters")
                else:
                    click.echo("✅ Text normalization ready")
            except Exception as e:
                click.echo(f"⚠️  Normalization issue: {e!s}", err=True)

        # Structure analysis
        click.echo("🔍 Analyzing document structure...")

        # Check for common academic paper sections
        text_lower = text.lower()
        sections_found = []
        for section in ["abstract", "introduction", "method", "result", "conclusion"]:
            if section in text_lower:
                sections_found.append(section)

        if sections_found:
            click.echo(f"✅ Found academic sections: {', '.join(sections_found)}")
        else:
            click.echo("⚠️  No standard academic sections detected")

        click.echo()
        click.echo("✅ PDF validation complete - file is ready for extraction!")

    except Exception as e:
        context = {
            "operation": "pdf_validation",
            "file_path": str(pdf_path),
            "max_file_size": max_file_size,
        }
        formatted_error = format_error_for_cli(e, context)
        click.echo(formatted_error, err=True)
        raise click.Abort() from e


@click.command()
@click.argument(
    "input_dir", type=click.Path(exists=True, file_okay=False, path_type=Path),
)
@click.argument("output_dir", type=click.Path(path_type=Path))
@click.option(
    "--max-concurrent",
    default=3,
    type=int,
    help="Maximum number of concurrent PDF processing operations",
)
@click.option(
    "--skip-errors", is_flag=True, help="Continue processing other files if some fail",
)
@click.option(
    "--filter-pattern", default="*.pdf", help="File pattern to match (default: *.pdf)",
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
    """Process multiple PDF files from input directory and save results to output directory."""
    # Check virtual environment
    _check_virtual_environment()

    try:
        # Get CLI context and set up DI container
        ctx = click.get_current_context()

        # Handle profile selection first
        if profile:
            profile_obj = get_profile(profile)
            if not profile_obj:
                raise ClickProfileError()

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
            ),
        )

        # Show configuration info if verbose
        if config.log_level == "DEBUG":
            click.echo(
                f"🔧 Using configuration: chunk_size={config.analysis.chunk_size}, "
                f"timeout={config.analysis.section_timeout_seconds}s, "
                f"max_retries={config.retry.max_attempts}, "
                f"max_concurrent={config.analysis.max_concurrent_sections}",
            )

        # Validate parameters
        if max_concurrent < 1:
            raise ClickParameterError()

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
            ),
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
            return await asyncio.gather(*tasks, return_exceptions=True)


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
            ),
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
            e, context, verbose=config.log_level == "DEBUG",
        )
        click.echo(formatted_error, err=True)
        raise click.Abort() from e
    except Exception as e:
        context = {
            "operation": "batch_processing",
            "input_directory": str(input_dir),
            "output_directory": str(output_dir),
            "max_concurrent": max_concurrent,
        }
        formatted_error = format_error_for_cli(
            e, context, verbose=config.log_level == "DEBUG",
        )
        click.echo(formatted_error, err=True)
        raise click.Abort() from e
