"""Allow hci_extractor to be executable as a module with python -m hci_extractor."""

from hci_extractor.cli.commands import cli

if __name__ == "__main__":
    cli()
