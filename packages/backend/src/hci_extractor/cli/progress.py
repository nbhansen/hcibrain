"""
Smart progress tracking for HCI extraction following CLAUDE.md principles.

This module implements single responsibility (progress tracking only) with
immutable data structures and user-friendly feedback.
"""

import time
from dataclasses import dataclass, field
from typing import Optional

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)


@dataclass(frozen=True)
class ExtractionProgress:
    """Immutable progress state for extraction operations."""

    total_papers: int
    completed_papers: int
    current_paper: Optional[str] = None
    current_section: Optional[str] = None
    total_sections: int = 0
    completed_sections: int = 0
    start_time: float = field(default_factory=time.time)

    @property
    def paper_progress(self) -> float:
        """Calculate paper completion percentage."""
        if self.total_papers == 0:
            return 0.0
        return self.completed_papers / self.total_papers

    @property
    def section_progress(self) -> float:
        """Calculate section completion percentage for current paper."""
        if self.total_sections == 0:
            return 0.0
        return self.completed_sections / self.total_sections

    @property
    def elapsed_time(self) -> float:
        """Time elapsed since start."""
        return time.time() - self.start_time

    @property
    def estimated_total_time(self) -> Optional[float]:
        """Estimate total time based on current progress."""
        if self.completed_papers == 0:
            return None

        papers_per_second = self.completed_papers / self.elapsed_time
        if papers_per_second <= 0:
            return None

        return self.total_papers / papers_per_second

    @property
    def estimated_remaining_time(self) -> Optional[float]:
        """Estimate remaining time."""
        total_time = self.estimated_total_time
        if total_time is None:
            return None
        return total_time - self.elapsed_time

    def with_paper_completed(self) -> "ExtractionProgress":
        """Return new progress with one more paper completed."""
        return ExtractionProgress(
            total_papers=self.total_papers,
            completed_papers=self.completed_papers + 1,
            current_paper=None,
            current_section=None,
            total_sections=0,
            completed_sections=0,
            start_time=self.start_time,
        )

    def with_current_paper(
        self,
        paper_name: str,
        total_sections: int,
    ) -> "ExtractionProgress":
        """Return new progress with current paper information."""
        return ExtractionProgress(
            total_papers=self.total_papers,
            completed_papers=self.completed_papers,
            current_paper=paper_name,
            current_section=None,
            total_sections=total_sections,
            completed_sections=0,
            start_time=self.start_time,
        )

    def with_current_section(self, section_name: str) -> "ExtractionProgress":
        """Return new progress with current section information."""
        return ExtractionProgress(
            total_papers=self.total_papers,
            completed_papers=self.completed_papers,
            current_paper=self.current_paper,
            current_section=section_name,
            total_sections=self.total_sections,
            completed_sections=self.completed_sections,
            start_time=self.start_time,
        )

    def with_section_completed(self) -> "ExtractionProgress":
        """Return new progress with one more section completed."""
        return ExtractionProgress(
            total_papers=self.total_papers,
            completed_papers=self.completed_papers,
            current_paper=self.current_paper,
            current_section=None,
            total_sections=self.total_sections,
            completed_sections=self.completed_sections + 1,
            start_time=self.start_time,
        )


class ProgressTracker:
    """
    User-friendly progress tracking for extraction operations.

    Follows single responsibility principle - only handles progress display.
    Thread-safe through immutable progress state.
    """

    def __init__(self, console: Optional[Console] = None):
        """Initialize progress tracker with optional console."""
        self.console = console or Console()
        self.progress: Optional[Progress] = None
        self.paper_task: Optional[TaskID] = None
        self.section_task: Optional[TaskID] = None
        self._current_state: Optional[ExtractionProgress] = None

    def start_batch(self, total_papers: int) -> ExtractionProgress:
        """Start tracking batch extraction progress."""
        self._current_state = ExtractionProgress(
            total_papers=total_papers,
            completed_papers=0,
        )

        # Initialize rich progress display
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            "[progress.percentage]{task.percentage:>3.0f}%",
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=self.console,
        )

        self.progress.start()

        # Create main progress task
        self.paper_task = self.progress.add_task(
            "Processing papers...",
            total=total_papers,
        )

        return self._current_state

    def start_paper(self, paper_name: str, total_sections: int) -> ExtractionProgress:
        """Start tracking single paper progress."""
        if self._current_state is None:
            raise ValueError("Must call start_batch first")

        self._current_state = self._current_state.with_current_paper(
            paper_name,
            total_sections,
        )

        # Update main task description
        if self.progress and self.paper_task is not None:
            self.progress.update(
                self.paper_task,
                description=f"Processing {paper_name} "
                f"({self._current_state.completed_papers + 1}/"
                f"{self._current_state.total_papers})",
            )

            # Add section progress task if we have sections
            if total_sections > 0:
                self.section_task = self.progress.add_task(
                    "└─ Detecting sections...",
                    total=total_sections,
                )

        return self._current_state

    def update_section(self, section_name: str) -> ExtractionProgress:
        """Update current section being processed."""
        if self._current_state is None:
            raise ValueError("Must call start_batch first")

        self._current_state = self._current_state.with_current_section(section_name)

        # Update section task description
        if self.progress and self.section_task is not None:
            self.progress.update(
                self.section_task,
                description=f"└─ Processing {section_name} section...",
            )

        return self._current_state

    def complete_section(self) -> ExtractionProgress:
        """Mark current section as completed."""
        if self._current_state is None:
            raise ValueError("Must call start_batch first")

        self._current_state = self._current_state.with_section_completed()

        # Update section progress
        if self.progress and self.section_task is not None:
            self.progress.update(self.section_task, advance=1)

        return self._current_state

    def complete_paper(self, elements_extracted: int) -> ExtractionProgress:
        """Mark current paper as completed."""
        if self._current_state is None:
            raise ValueError("Must call start_batch first")

        # Remove section task if it exists
        if self.progress and self.section_task is not None:
            self.progress.remove_task(self.section_task)
            self.section_task = None

        self._current_state = self._current_state.with_paper_completed()

        # Update main progress
        if self.progress and self.paper_task is not None:
            self.progress.update(
                self.paper_task,
                advance=1,
                description=f"Completed {self._current_state.current_paper or 'paper'} "
                f"({elements_extracted} elements)",
            )

        return self._current_state

    def finish(self) -> None:
        """Finish progress tracking and display summary."""
        if self.progress:
            self.progress.stop()

        if self._current_state:
            self.console.print()
            self.console.print("🎉 [bold green]Extraction complete![/bold green]")
            self.console.print(
                f"📊 Processed {self._current_state.completed_papers} papers "
                f"in {self._current_state.elapsed_time:.1f}s",
            )

            if self._current_state.completed_papers > 1:
                avg_time = (
                    self._current_state.elapsed_time
                    / self._current_state.completed_papers
                )
                self.console.print(f"⚡ Average: {avg_time:.1f}s per paper")

    def error(self, message: str) -> None:
        """Display error message."""
        if self.progress:
            self.progress.stop()
        self.console.print(f"❌ [bold red]Error:[/bold red] {message}")

    def warning(self, message: str) -> None:
        """Display warning message."""
        self.console.print(f"⚠️  [bold yellow]Warning:[/bold yellow] {message}")

    def info(self, message: str) -> None:
        """Display info message."""
        self.console.print(f"i  [bold blue]Info:[/bold blue] {message}")


def create_progress_tracker(verbose: bool = False) -> ProgressTracker:
    """
    Factory function to create progress tracker with appropriate console.

    Args:
        verbose: If True, shows detailed progress. If False, minimal output.

    Returns:
        Configured ProgressTracker instance
    """
    console = Console(quiet=not verbose) if not verbose else Console()
    return ProgressTracker(console)
