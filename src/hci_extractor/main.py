"""CLI entry point for HCI extractor."""

import asyncio
import csv
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any

import click

from .extractors import PdfExtractor, TextNormalizer
from .models import PdfError, LLMError, Paper
from .llm.gemini_provider import GeminiProvider
from .pipeline import extract_paper_simple

__version__ = "0.1.0"


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the application."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )


def get_llm_provider() -> GeminiProvider:
    """Get configured LLM provider with API key validation."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise click.ClickException(
            "GEMINI_API_KEY environment variable is required. "
            "Get your API key from https://makersuite.google.com/app/apikey"
        )
    return GeminiProvider(api_key=api_key)


@click.group()
@click.version_option(__version__)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
def cli(verbose: bool) -> None:
    """HCI Paper Extractor - Extract structured content from academic PDFs."""
    setup_logging(verbose)


@cli.command()
def version() -> None:
    """Show version information."""
    click.echo(f"HCI Paper Extractor v{__version__}")
    click.echo(f"Python {sys.version}")


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
        extractor = PdfExtractor()

        # Extract PDF content
        click.echo(f"Extracting content from {pdf_path}...")
        content = extractor.extract_content(pdf_path)
        click.echo(
            f"Successfully extracted {content.total_pages} pages, {content.total_chars} characters"
        )

        # Apply normalization if requested
        if normalize:
            normalizer = TextNormalizer()
            click.echo("Applying text normalization...")

            # Normalize each page
            normalized_pages = []
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
                    f"Page {page_data['page_number']}: {page_data['char_count']} chars - {text_preview}"
                )

    except PdfError as e:
        click.echo(f"PDF Extraction Error: {e}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument("pdf_path", type=click.Path(exists=True, path_type=Path))
def validate(pdf_path: Path) -> None:
    """Check if a PDF file can be processed successfully."""
    try:
        extractor = PdfExtractor()

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
        click.echo(f"✗ PDF cannot be processed: {e}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"✗ Unexpected validation error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument("pdf_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output",
    "-o", 
    type=click.Path(path_type=Path),
    help="Output file for extraction results (JSON format)"
)
@click.option(
    "--title",
    help="Paper title (if not provided, will be auto-detected)"
)
@click.option(
    "--authors",
    help="Paper authors (comma-separated, if not provided, will be auto-detected)"
)
@click.option(
    "--venue",
    help="Publication venue (optional)"
)
@click.option(
    "--year",
    type=int,
    help="Publication year (optional)"
)
def extract(
    pdf_path: Path, 
    output: Optional[Path], 
    title: Optional[str],
    authors: Optional[str], 
    venue: Optional[str],
    year: Optional[int]
) -> None:
    """Extract academic elements (claims, findings, methods) from a PDF using LLM analysis."""
    try:
        # Initialize LLM provider
        click.echo("🔑 Initializing LLM provider...")
        llm_provider = get_llm_provider()
        
        # Prepare paper metadata
        paper_metadata = {}
        if title:
            paper_metadata["title"] = title
        if authors:
            paper_metadata["authors"] = [author.strip() for author in authors.split(",")]
        if venue:
            paper_metadata["venue"] = venue
        if year:
            paper_metadata["year"] = year
            
        # Run extraction
        click.echo(f"📄 Processing PDF: {pdf_path}")
        click.echo("⚡ Running LLM analysis (this may take 30-60 seconds)...")
        
        # Run async extraction
        result = asyncio.run(extract_paper_simple(
            pdf_path=pdf_path,
            llm_provider=llm_provider,
            paper_metadata=paper_metadata
        ))
        
        # Prepare output data
        output_data = {
            "paper": {
                "paper_id": result.paper.paper_id,
                "title": result.paper.title,
                "authors": result.paper.authors,
                "venue": result.paper.venue,
                "year": result.paper.year,
                "file_path": str(pdf_path)
            },
            "extraction_summary": {
                "total_elements": result.total_elements,
                "elements_by_type": result.elements_by_type,
                "elements_by_section": result.elements_by_section,
                "average_confidence": result.average_confidence,
                "created_at": result.created_at.isoformat()
            },
            "extracted_elements": [
                {
                    "element_id": element.element_id,
                    "element_type": element.element_type,
                    "text": element.text,
                    "section": element.section,
                    "confidence": element.confidence,
                    "evidence_type": element.evidence_type,
                    "page_number": element.page_number
                }
                for element in result.elements
            ]
        }
        
        # Output results
        if output:
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
                click.echo(f"{i+1}. [{element.element_type.upper()}] {element.text[:100]}...")
                click.echo(f"   Section: {element.section} | Confidence: {element.confidence:.2f}")
                click.echo()
            
            if len(result.elements) > 5:
                click.echo(f"... and {len(result.elements) - 5} more elements")
                click.echo("\nUse --output to save complete results to file")
        
    except LLMError as e:
        click.echo(f"❌ LLM processing error: {e}", err=True)
        click.echo("💡 Check your GEMINI_API_KEY and internet connection", err=True)
        raise click.Abort()
    except PdfError as e:
        click.echo(f"❌ PDF processing error: {e}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument("input_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.argument("output_dir", type=click.Path(path_type=Path))
@click.option(
    "--max-concurrent",
    default=3,
    type=int,
    help="Maximum number of concurrent PDF processing operations"
)
@click.option(
    "--skip-errors",
    is_flag=True,
    help="Continue processing other files if some fail"
)
@click.option(
    "--filter-pattern",
    default="*.pdf",
    help="File pattern to match (default: *.pdf)"
)
def batch(
    input_dir: Path,
    output_dir: Path, 
    max_concurrent: int,
    skip_errors: bool,
    filter_pattern: str
) -> None:
    """Process multiple PDF files from input directory and save results to output directory."""
    try:
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
        
        # Initialize LLM provider
        click.echo("🔑 Initializing LLM provider...")
        llm_provider = get_llm_provider()
        
        # Process files
        successful_extractions = 0
        failed_extractions = []
        
        async def process_single_pdf(pdf_path: Path) -> bool:
            """Process a single PDF and return success status."""
            try:
                click.echo(f"📄 Processing: {pdf_path.name}")
                
                # Extract elements
                result = await extract_paper_simple(
                    pdf_path=pdf_path,
                    llm_provider=llm_provider
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
                        "file_path": str(pdf_path)
                    },
                    "extraction_summary": {
                        "total_elements": result.total_elements,
                        "elements_by_type": result.elements_by_type,
                        "elements_by_section": result.elements_by_section,
                        "average_confidence": result.average_confidence,
                        "created_at": result.created_at.isoformat()
                    },
                    "extracted_elements": [
                        {
                            "element_id": element.element_id,
                            "element_type": element.element_type,
                            "text": element.text,
                            "section": element.section,
                            "confidence": element.confidence,
                            "evidence_type": element.evidence_type,
                            "page_number": element.page_number
                        }
                        for element in result.elements
                    ]
                }
                
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(output_data, f, indent=2, ensure_ascii=False)
                
                click.echo(f"✅ {pdf_path.name}: {result.total_elements} elements extracted")
                return True
                
            except Exception as e:
                error_msg = f"❌ {pdf_path.name}: {e}"
                click.echo(error_msg, err=True)
                if not skip_errors:
                    raise
                return False
        
        async def process_batch():
            """Process all PDFs with concurrency control."""
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def process_with_semaphore(pdf_path):
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
                "skip_errors": skip_errors
            },
            "processed_files": [str(f) for f in pdf_files],
            "failed_files": [{"file": str(f), "error": err} for f, err in failed_extractions]
        }
        
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, indent=2, ensure_ascii=False)
        
        # Display final summary
        click.echo(f"\n--- 📊 Batch Processing Complete ---")
        click.echo(f"✅ Successfully processed: {successful_extractions}/{len(pdf_files)} files")
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
        click.echo(f"❌ LLM processing error: {e}", err=True)
        click.echo("💡 Check your GEMINI_API_KEY and internet connection", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument("results_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["csv", "json", "markdown"], case_sensitive=False),
    default="csv",
    help="Output format (default: csv)"
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output file (if not provided, prints to stdout)"
)
@click.option(
    "--element-type",
    type=click.Choice(["claim", "finding", "method"], case_sensitive=False),
    help="Filter by element type"
)
@click.option(
    "--min-confidence",
    type=float,
    help="Minimum confidence score (0.0-1.0)"
)
@click.option(
    "--section",
    help="Filter by section name"
)
def export(
    results_dir: Path,
    output_format: str,
    output: Optional[Path],
    element_type: Optional[str],
    min_confidence: Optional[float],
    section: Optional[str]
) -> None:
    """Export extraction results from a directory to various formats."""
    try:
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
                elements = data.get("extracted_elements", [])
                
                # Apply filters
                filtered_elements = []
                for element in elements:
                    # Filter by element type
                    if element_type and element.get("element_type") != element_type:
                        continue
                    
                    # Filter by confidence
                    if min_confidence is not None and element.get("confidence", 0) < min_confidence:
                        continue
                    
                    # Filter by section
                    if section and element.get("section") != section:
                        continue
                    
                    # Add paper information to element
                    element_with_paper = element.copy()
                    element_with_paper.update({
                        "paper_title": paper_info.get("title", ""),
                        "paper_authors": ", ".join(paper_info.get("authors", [])),
                        "paper_venue": paper_info.get("venue", ""),
                        "paper_year": paper_info.get("year", ""),
                        "source_file": result_file.stem.replace("_extraction", "")
                    })
                    filtered_elements.append(element_with_paper)
                
                all_elements.extend(filtered_elements)
                papers_info.append(paper_info)
                
            except Exception as e:
                click.echo(f"⚠️ Warning: Could not load {result_file}: {e}", err=True)
                continue
        
        if not all_elements:
            click.echo("❌ No elements found matching the specified filters")
            raise click.Abort()
        
        click.echo(f"📝 Exporting {len(all_elements)} elements in {output_format.upper()} format...")
        
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
    fieldnames = set()
    for element in elements:
        fieldnames.update(element.keys())
    
    # Ensure consistent ordering
    ordered_fields = [
        "paper_title", "paper_authors", "paper_venue", "paper_year", "source_file",
        "element_type", "evidence_type", "section", "text", "confidence", 
        "page_number", "element_id"
    ]
    
    # Add any additional fields not in the ordered list
    remaining_fields = sorted(fieldnames - set(ordered_fields))
    fieldnames = [f for f in ordered_fields if f in fieldnames] + remaining_fields
    
    # Generate CSV
    import io
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(elements)
    
    return output.getvalue()


def _export_to_json(elements: List[Dict[str, Any]], papers_info: List[Dict[str, Any]]) -> str:
    """Export elements to JSON format."""
    export_data = {
        "export_metadata": {
            "total_elements": len(elements),
            "total_papers": len(papers_info),
            "export_format": "json"
        },
        "papers": papers_info,
        "elements": elements
    }
    
    return json.dumps(export_data, indent=2, ensure_ascii=False)


def _export_to_markdown(elements: List[Dict[str, Any]], papers_info: List[Dict[str, Any]]) -> str:
    """Export elements to Markdown format."""
    lines = []
    
    # Header
    lines.append("# HCI Paper Extraction Results")
    lines.append("")
    lines.append(f"**Total Elements:** {len(elements)}")
    lines.append(f"**Total Papers:** {len(papers_info)}")
    lines.append("")
    
    # Group elements by paper
    elements_by_paper = {}
    for element in elements:
        paper_title = element.get("paper_title", "Unknown Paper")
        if paper_title not in elements_by_paper:
            elements_by_paper[paper_title] = []
        elements_by_paper[paper_title].append(element)
    
    # Generate markdown for each paper
    for paper_title, paper_elements in elements_by_paper.items():
        lines.append(f"## {paper_title}")
        lines.append("")
        
        # Group by element type
        elements_by_type = {}
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


if __name__ == "__main__":
    cli()
