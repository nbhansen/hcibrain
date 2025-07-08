"use client";

import { useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useResizeObserver } from "@/hooks/use-resize-observer";
import { AlertCircle, ChevronLeft, ChevronRight, Loader2, ZoomIn, ZoomOut } from "lucide-react";
import { type Highlight, HighlightOverlay } from "./highlight-overlay";

// Set up the worker for PDF.js using local file (no CORS issues) - only in browser
if (typeof window !== 'undefined') {
  const workerSrc = '/pdf.worker.min.js';
  console.log('📖 PDF.js worker URL (local):', workerSrc);
  pdfjs.GlobalWorkerOptions.workerSrc = workerSrc;
}

interface PDFViewerClientProps {
  url: string;
  highlights: Highlight[];
  highlightsEnabled: boolean;
  highlightOpacity: number;
}

export function PDFViewerClient({
  url,
  highlights,
  highlightsEnabled,
  highlightOpacity,
}: PDFViewerClientProps) {
  const [numPages, setNumPages] = useState<number | null>(null);
  const [pageNumber, setPageNumber] = useState<number>(1);
  const [containerRef, containerWidth] = useResizeObserver<HTMLDivElement>();
  const [scale, setScale] = useState<number>(1);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  function onDocumentLoadSuccess({ numPages }: { numPages: number }) {
    setNumPages(numPages);
    setLoading(false);
    setError(null);
  }

  function onDocumentLoadError(error: Error) {
    setError(`Failed to load PDF: ${error.message}`);
    setLoading(false);
  }

  const goToPrevPage = () => {
    setPageNumber((prev) => Math.max(prev - 1, 1));
  };

  const goToNextPage = () => {
    setPageNumber((prev) => Math.min(prev + 1, numPages || prev));
  };

  const zoomIn = () => {
    setScale((prev) => Math.min(prev + 0.1, 2));
  };

  const zoomOut = () => {
    setScale((prev) => Math.max(prev - 0.1, 0.5));
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex justify-between items-center p-2 border-b">
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" onClick={goToPrevPage} disabled={pageNumber <= 1}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span>
            Page {pageNumber} of {numPages || "--"}
          </span>
          <Button
            variant="outline"
            size="icon"
            onClick={goToNextPage}
            disabled={pageNumber >= (numPages || 0)}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" onClick={zoomOut}>
            <ZoomOut className="h-4 w-4" />
          </Button>
          <span>{Math.round(scale * 100)}%</span>
          <Button variant="outline" size="icon" onClick={zoomIn}>
            <ZoomIn className="h-4 w-4" />
          </Button>
        </div>
      </div>
      <div ref={containerRef} className="flex-1 overflow-auto flex justify-center p-4 bg-muted/20">
        <div className="relative">
          {error ? (
            <Alert variant="destructive" className="m-4">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          ) : (
            <>
              <Document
                file={url}
                onLoadSuccess={onDocumentLoadSuccess}
                onLoadError={onDocumentLoadError}
                loading={
                  <div className="flex flex-col items-center justify-center p-8 space-y-4">
                    <Loader2 className="h-8 w-8 animate-spin" />
                    <p className="text-sm text-muted-foreground">Loading PDF...</p>
                    <Skeleton className="h-[600px] w-[400px]" />
                  </div>
                }
                error={
                  <Alert variant="destructive" className="m-4">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>Failed to load PDF. Please try again.</AlertDescription>
                  </Alert>
                }
              >
                <Page
                  pageNumber={pageNumber}
                  width={containerWidth ? containerWidth - 80 : undefined}
                  scale={scale}
                  renderTextLayer={false}
                  renderAnnotationLayer={false}
                />
              </Document>

              {/* Highlight overlay - only show when PDF is loaded */}
              {!loading && (
                <HighlightOverlay
                  highlights={highlights}
                  currentPage={pageNumber}
                  opacity={highlightOpacity}
                  enabled={highlightsEnabled}
                  scale={scale}
                />
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}