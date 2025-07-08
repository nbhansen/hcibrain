"""Main CLI commands module that imports from decomposed command modules."""

import sys

import click

from hci_extractor.utils.logging import setup_logging

# Import command modules
from .commands.processing_commands import batch, extract, parse, validate

__version__ = "0.1.0"


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
    ctx.meta = ctx.meta or {}
    ctx.meta["debug_config"] = debug_config


# Add the processing commands
cli.add_command(extract)
cli.add_command(batch)
cli.add_command(parse)
cli.add_command(validate)


@cli.command()
def version() -> None:
    """Show version information."""
    click.echo(f"HCI Paper Extractor v{__version__}")
    click.echo(f"Python {sys.version}")


# Placeholder for other commands that will be added in subsequent phases
@cli.command()
def config() -> None:
    """Show detailed configuration options and their usage."""
    click.echo("⚠️  Config command will be implemented in next phase")


@cli.command()
def profiles() -> None:
    """Show available configuration profiles for different research scenarios."""
    click.echo("⚠️  Profiles command will be implemented in next phase")


@cli.command()
def serve() -> None:
    """Start the web UI server."""
    click.echo("⚠️  Serve command will be implemented in next phase")


# Add other placeholder commands
for cmd_name in ["diagnose", "test-config", "quickstart", "setup", "doctor", "export"]:
    @click.command(name=cmd_name)
    def placeholder_cmd() -> None:
        f"""Placeholder for {cmd_name} command."""
        click.echo(f"⚠️  {cmd_name} command will be implemented in next phase")

    cli.add_command(placeholder_cmd)
