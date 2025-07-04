"""
Metrics collection for monitoring and analysis.

This module provides immutable metrics tracking that can be used to monitor
system performance without adding mutable state to core components.
"""

import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional


@dataclass(frozen=True)
class LLMUsageMetric:
    """Immutable record of a single LLM API usage."""

    timestamp: datetime
    provider: str
    model: str
    operation: str
    tokens_input: int
    tokens_output: int
    tokens_total: int
    response_time_seconds: float
    success: bool
    error_type: Optional[str] = None
    paper_id: Optional[str] = None
    section_type: Optional[str] = None


@dataclass(frozen=True)
class ExtractionMetric:
    """Immutable record of a PDF extraction operation."""

    timestamp: datetime
    pdf_path: str
    paper_id: str
    file_size_bytes: int
    pages_extracted: int
    characters_extracted: int
    sections_detected: int
    elements_extracted: int
    duration_seconds: float
    success: bool
    error_type: Optional[str] = None


@dataclass(frozen=True)
class MetricsSummary:
    """Immutable summary of collected metrics."""

    period_start: datetime
    period_end: datetime
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_tokens: int
    total_cost_estimate: float
    average_response_time: float
    requests_by_provider: Dict[str, int]
    tokens_by_provider: Dict[str, int]
    errors_by_type: Dict[str, int]


class MetricsCollector:
    """
    Collects metrics without polluting provider implementations.

    This collector maintains internal state but provides immutable
    views of the metrics data.
    """

    def __init__(self) -> None:
        self._llm_metrics: List[LLMUsageMetric] = []
        self._extraction_metrics: List[ExtractionMetric] = []
        self._start_time = datetime.now()

    def record_llm_usage(self, metric: LLMUsageMetric) -> None:
        """Record a new LLM usage metric."""
        self._llm_metrics.append(metric)

    def record_extraction(self, metric: ExtractionMetric) -> None:
        """Record a new extraction metric."""
        self._extraction_metrics.append(metric)

    def get_llm_summary(self) -> MetricsSummary:
        """Get an immutable summary of LLM usage metrics."""
        if not self._llm_metrics:
            return self._empty_summary()

        total_requests = len(self._llm_metrics)
        successful = sum(1 for m in self._llm_metrics if m.success)
        failed = total_requests - successful

        total_tokens = sum(m.tokens_total for m in self._llm_metrics)

        # Estimate costs (example rates, adjust for actual providers)
        cost_per_1k_tokens = {
            "gemini-1.5-flash": 0.000075,
            "gpt-4": 0.03,
            "claude-3": 0.025,
        }

        total_cost = sum(
            m.tokens_total / 1000 * cost_per_1k_tokens.get(m.model, 0.01)
            for m in self._llm_metrics
        )

        avg_response_time = (
            sum(m.response_time_seconds for m in self._llm_metrics) / total_requests
            if total_requests > 0
            else 0.0
        )

        # Group by provider
        requests_by_provider: defaultdict[str, int] = defaultdict(int)
        tokens_by_provider: defaultdict[str, int] = defaultdict(int)
        for metric in self._llm_metrics:
            requests_by_provider[metric.provider] += 1
            tokens_by_provider[metric.provider] += metric.tokens_total

        # Group errors
        errors_by_type: defaultdict[str, int] = defaultdict(int)
        for metric in self._llm_metrics:
            if metric.error_type:
                errors_by_type[metric.error_type] += 1

        return MetricsSummary(
            period_start=self._start_time,
            period_end=datetime.now(),
            total_requests=total_requests,
            successful_requests=successful,
            failed_requests=failed,
            total_tokens=total_tokens,
            total_cost_estimate=total_cost,
            average_response_time=avg_response_time,
            requests_by_provider=dict(requests_by_provider),
            tokens_by_provider=dict(tokens_by_provider),
            errors_by_type=dict(errors_by_type),
        )

    def get_extraction_summary(self) -> Dict[str, Any]:
        """Get an immutable summary of extraction metrics."""
        if not self._extraction_metrics:
            return {
                "total_extractions": 0,
                "successful_extractions": 0,
                "failed_extractions": 0,
                "total_pages": 0,
                "total_elements": 0,
                "average_duration": 0.0,
            }

        total = len(self._extraction_metrics)
        successful = sum(1 for m in self._extraction_metrics if m.success)

        return {
            "total_extractions": total,
            "successful_extractions": successful,
            "failed_extractions": total - successful,
            "total_pages": sum(m.pages_extracted for m in self._extraction_metrics),
            "total_elements": sum(
                m.elements_extracted for m in self._extraction_metrics
            ),
            "average_duration": sum(
                m.duration_seconds for m in self._extraction_metrics
            )
            / total,
            "total_characters": sum(
                m.characters_extracted for m in self._extraction_metrics
            ),
            "errors_by_type": self._group_errors(self._extraction_metrics),
        }

    def _empty_summary(self) -> MetricsSummary:
        """Create an empty summary when no metrics exist."""
        return MetricsSummary(
            period_start=self._start_time,
            period_end=datetime.now(),
            total_requests=0,
            successful_requests=0,
            failed_requests=0,
            total_tokens=0,
            total_cost_estimate=0.0,
            average_response_time=0.0,
            requests_by_provider={},
            tokens_by_provider={},
            errors_by_type={},
        )

    def _group_errors(self, metrics: List[Any]) -> Dict[str, int]:
        """Group error counts by type."""
        errors: defaultdict[str, int] = defaultdict(int)
        for metric in metrics:
            if hasattr(metric, "error_type") and metric.error_type:
                errors[metric.error_type] += 1
        return dict(errors)

    def clear(self) -> None:
        """Clear all collected metrics."""
        self._llm_metrics.clear()
        self._extraction_metrics.clear()
        self._start_time = datetime.now()


# Global metrics collector
_metrics_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance."""
    return _metrics_collector


# Context managers for easy metrics collection


class LLMMetricsContext:
    """Context manager for collecting LLM metrics."""

    def __init__(
        self,
        provider: str,
        model: str,
        operation: str,
        paper_id: Optional[str] = None,
        section_type: Optional[str] = None,
    ):
        self.provider = provider
        self.model = model
        self.operation = operation
        self.paper_id = paper_id
        self.section_type = section_type
        self.start_time: Optional[float] = None
        self.tokens_input = 0
        self.tokens_output = 0

    def __enter__(self) -> "LLMMetricsContext":
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> Literal[False]:
        duration = time.time() - (self.start_time or 0)
        success = exc_type is None
        error_type = exc_type.__name__ if exc_type else None

        metric = LLMUsageMetric(
            timestamp=datetime.now(),
            provider=self.provider,
            model=self.model,
            operation=self.operation,
            tokens_input=self.tokens_input,
            tokens_output=self.tokens_output,
            tokens_total=self.tokens_input + self.tokens_output,
            response_time_seconds=duration,
            success=success,
            error_type=error_type,
            paper_id=self.paper_id,
            section_type=self.section_type,
        )

        get_metrics_collector().record_llm_usage(metric)

        # Don't suppress exceptions
        return False
