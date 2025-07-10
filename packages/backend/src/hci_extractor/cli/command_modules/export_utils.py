"""Export utilities for CLI commands."""

import csv
import json
from typing import Any, Dict, List


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
    elements: List[Dict[str, Any]],
    papers_info: List[Dict[str, Any]],
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
    elements: List[Dict[str, Any]],
    papers_info: List[Dict[str, Any]],
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
