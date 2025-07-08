import type { Highlight, HighlightCategory } from "@/components/highlight-overlay";
import type { BackendExtractedElement, BackendExtractionResponse } from "@/types/api";
import {
  constrainToViewport,
  type PDFPageInfo,
  transformBackendToFrontendCoordinates,
  type ViewportInfo,
  validateCoordinates,
} from "./coordinate-transform";

/**
 * Maps backend element types to frontend highlight categories
 */
function mapElementTypeToCategory(elementType: string): HighlightCategory {
  switch (elementType) {
    case "claim":
      return "Goal";
    case "finding":
      return "Result";
    case "method":
      return "Method";
    case "artifact":
      // For now, map artifact to Method - could be expanded later
      return "Method";
    default:
      // Default fallback
      return "Goal";
  }
}

/**
 * Transforms backend coordinate system to frontend coordinate system
 * Uses proper coordinate transformation between PyMuPDF and PDF.js
 */
function transformCoordinates(
  backendCoords: BackendExtractedElement["coordinates"],
  pdfPageInfo?: PDFPageInfo,
  viewportInfo?: ViewportInfo
) {
  if (!backendCoords) return null;

  // If we don't have page/viewport info, fall back to simple mapping
  if (!pdfPageInfo || !viewportInfo) {
    return {
      x: backendCoords.x,
      y: backendCoords.y,
      width: backendCoords.width,
      height: backendCoords.height,
    };
  }

  // Use proper coordinate transformation
  const frontendRect = transformBackendToFrontendCoordinates(
    backendCoords,
    pdfPageInfo,
    viewportInfo
  );

  // Ensure coordinates are valid and within bounds
  if (!validateCoordinates(frontendRect, viewportInfo)) {
    return constrainToViewport(frontendRect, viewportInfo);
  }

  return frontendRect;
}

/**
 * Converts a backend ExtractedElement to a frontend Highlight
 */
export function adaptBackendElementToHighlight(
  element: BackendExtractedElement,
  pdfPageInfo?: PDFPageInfo,
  viewportInfo?: ViewportInfo
): Highlight | null {
  // Skip elements without coordinates for now
  if (!element.coordinates) {
    return null;
  }

  const rect = transformCoordinates(element.coordinates, pdfPageInfo, viewportInfo);
  if (!rect) {
    return null;
  }

  return {
    id: element.element_id,
    category: mapElementTypeToCategory(element.element_type),
    rect,
    pageNumber: element.coordinates.page_number,
    text: element.text,
    // Add metadata for future enhancements
    metadata: {
      confidence: element.confidence,
      evidenceType: element.evidence_type,
      section: element.section,
      supportingEvidence: element.supporting_evidence,
      methodologyContext: element.methodology_context,
      studyPopulation: element.study_population,
      limitations: element.limitations,
      surroundingContext: element.surrounding_context,
    },
  };
}

/**
 * Converts backend extraction response to frontend highlights array
 */
export function adaptBackendExtractionToHighlights(
  response: BackendExtractionResponse,
  pdfPageInfo?: PDFPageInfo,
  viewportInfo?: ViewportInfo
): Highlight[] {
  return response.extracted_elements
    .map((element) => adaptBackendElementToHighlight(element, pdfPageInfo, viewportInfo))
    .filter((highlight): highlight is Highlight => highlight !== null);
}

/**
 * Extract metadata summary from backend response for UI display
 */
export function extractExtractionSummary(response: BackendExtractionResponse) {
  return {
    paper: {
      title: response.paper.title,
      authors: response.paper.authors,
      paperId: response.paper.paper_id,
    },
    summary: {
      totalElements: response.extraction_summary.total_elements,
      elementsByType: response.extraction_summary.elements_by_type,
      elementsBySection: response.extraction_summary.elements_by_section,
      averageConfidence: response.extraction_summary.average_confidence,
      processingTime: response.extraction_summary.processing_time_seconds,
      createdAt: response.extraction_summary.created_at,
      paperSummary: response.extraction_summary.paper_summary,
      paperSummaryConfidence: response.extraction_summary.paper_summary_confidence,
    },
  };
}
