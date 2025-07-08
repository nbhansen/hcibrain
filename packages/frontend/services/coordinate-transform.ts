/**
 * Coordinate transformation service for mapping backend PDF coordinates
 * to frontend PDF.js viewport coordinates
 */

export interface BackendCoordinates {
  page_number: number;
  x: number;
  y: number;
  width: number;
  height: number;
  char_start: number;
  char_end: number;
}

export interface FrontendRect {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface ViewportInfo {
  width: number;
  height: number;
  scale: number;
}

export interface PDFPageInfo {
  width: number;
  height: number;
  rotation: number;
}

/**
 * Transforms backend PyMuPDF coordinates to frontend PDF.js coordinates
 *
 * PyMuPDF uses bottom-left origin (0,0 at bottom-left)
 * PDF.js uses top-left origin (0,0 at top-left)
 *
 * This transformation handles:
 * - Origin flip (bottom-left to top-left)
 * - Scaling based on PDF.js viewport
 * - Page dimensions and rotation
 */
export function transformBackendToFrontendCoordinates(
  backendCoords: BackendCoordinates,
  pdfPageInfo: PDFPageInfo,
  viewportInfo: ViewportInfo
): FrontendRect {
  const { x: backendX, y: backendY, width, height } = backendCoords;
  const { height: pageHeight } = pdfPageInfo;
  const { scale } = viewportInfo;

  // Convert from PyMuPDF coordinate system (bottom-left origin)
  // to PDF.js coordinate system (top-left origin)
  const frontendX = backendX;
  const frontendY = pageHeight - backendY - height; // Flip Y-axis

  // Apply scaling from PDF.js viewport
  const scaledRect: FrontendRect = {
    x: frontendX * scale,
    y: frontendY * scale,
    width: width * scale,
    height: height * scale,
  };

  return scaledRect;
}

/**
 * Validates that coordinates are within reasonable bounds
 */
export function validateCoordinates(rect: FrontendRect, viewport: ViewportInfo): boolean {
  return (
    rect.x >= 0 &&
    rect.y >= 0 &&
    rect.x + rect.width <= viewport.width &&
    rect.y + rect.height <= viewport.height &&
    rect.width > 0 &&
    rect.height > 0
  );
}

/**
 * Adjusts coordinates to ensure they stay within viewport bounds
 */
export function constrainToViewport(rect: FrontendRect, viewport: ViewportInfo): FrontendRect {
  return {
    x: Math.max(0, Math.min(rect.x, viewport.width - rect.width)),
    y: Math.max(0, Math.min(rect.y, viewport.height - rect.height)),
    width: Math.min(rect.width, viewport.width - rect.x),
    height: Math.min(rect.height, viewport.height - rect.y),
  };
}

/**
 * Debug helper to log coordinate transformation
 */
export function debugCoordinateTransformation(
  backend: BackendCoordinates,
  frontend: FrontendRect,
  pageInfo: PDFPageInfo,
  viewport: ViewportInfo
): void {
  console.group(`Coordinate Transform - Page ${backend.page_number}`);
  console.log("Backend (PyMuPDF):", {
    x: backend.x,
    y: backend.y,
    width: backend.width,
    height: backend.height,
  });
  console.log("Page Info:", pageInfo);
  console.log("Viewport Info:", viewport);
  console.log("Frontend (PDF.js):", frontend);
  console.log("Valid:", validateCoordinates(frontend, viewport));
  console.groupEnd();
}

/**
 * Calculates relative position as percentage for responsive scaling
 */
export function getRelativeCoordinates(
  rect: FrontendRect,
  viewport: ViewportInfo
): {
  xPercent: number;
  yPercent: number;
  widthPercent: number;
  heightPercent: number;
} {
  return {
    xPercent: (rect.x / viewport.width) * 100,
    yPercent: (rect.y / viewport.height) * 100,
    widthPercent: (rect.width / viewport.width) * 100,
    heightPercent: (rect.height / viewport.height) * 100,
  };
}
