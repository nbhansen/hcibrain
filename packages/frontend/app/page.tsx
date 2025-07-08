"use client";

import { AlertCircle, CheckCircle, Loader2 } from "lucide-react";
import { useCallback, useState } from "react";
import type { Highlight } from "@/components/highlight-overlay";
import { FileUpload } from "@/components/pdf/file-upload";
import dynamic from "next/dynamic";

// Dynamically import PDF viewer to avoid SSR issues
const PDFViewer = dynamic(() => import("@/components/pdf-viewer-client").then(mod => ({ default: mod.PDFViewerClient })), {
  ssr: false,
  loading: () => <div className="flex items-center justify-center h-64"><div className="text-sm text-muted-foreground">Loading PDF viewer...</div></div>
});
import { SkimmingSidebar } from "@/components/skimming-sidebar";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { extractPdfWithCoordinates } from "@/services/api";
import {
  adaptBackendExtractionToHighlights,
  extractExtractionSummary,
} from "@/services/data-adapter";

export default function HomePage() {
  // Debug: Check if API functions are available
  console.log('🔧 Debug - API functions:', { 
    extractPdfWithCoordinates: typeof extractPdfWithCoordinates,
    isFunction: typeof extractPdfWithCoordinates === 'function'
  });
  
  // PDF and extraction state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string>("/deep_speech_2.pdf"); // Default demo PDF
  const [highlights, setHighlights] = useState<Highlight[]>([]);
  const [extractionSummary, setExtractionSummary] = useState<{
    paper: {
      title: string;
      authors: string[];
      paperId: string;
    };
    summary: {
      totalElements: number;
      elementsByType: Record<string, number>;
      elementsBySection: Record<string, number>;
      averageConfidence: number;
      processingTime: number;
      createdAt: string;
      paperSummary?: string;
      paperSummaryConfidence?: number;
    };
  } | null>(null);

  // UI state
  const [isExtracting, setIsExtracting] = useState(false);
  const [extractionProgress, setExtractionProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  // Highlight settings
  const [highlightsEnabled, setHighlightsEnabled] = useState(true);
  const [highlightOpacity, setHighlightOpacity] = useState(0.3);
  const [highlightCount, setHighlightCount] = useState(10);
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.5);

  // Filter highlights based on confidence threshold
  const filteredHighlights = highlights.filter(
    (highlight) =>
      !highlight.metadata?.confidence || highlight.metadata.confidence >= confidenceThreshold
  );

  // Then filter by count
  const visibleHighlights = filteredHighlights.slice(0, highlightCount);

  const handleFileSelect = useCallback(async (file: File) => {
    setSelectedFile(file);
    setError(null);
    setIsExtracting(true);
    setExtractionProgress(0);

    try {
      // Create object URL for PDF display
      const fileUrl = URL.createObjectURL(file);
      setPdfUrl(fileUrl);

      // Simulate progress steps for better UX
      setExtractionProgress(10);

      // Start extraction
      const progressInterval = setInterval(() => {
        setExtractionProgress((prev) => {
          if (prev < 80) return prev + Math.random() * 15;
          return prev;
        });
      }, 500);

      try {
        console.log('📄 Starting PDF extraction for:', file.name, 'Size:', file.size);
        
        // Extract highlights from backend
        const response = await extractPdfWithCoordinates(file);
        
        console.log('✅ PDF extraction successful:', { 
          elements: response.extracted_elements?.length || 0,
          paperTitle: response.paper?.title 
        });

        // Clear progress simulation
        clearInterval(progressInterval);
        setExtractionProgress(90);

        // For now, transform without page/viewport info (will be enhanced when PDF loads)
        const adaptedHighlights = adaptBackendExtractionToHighlights(response);
        const summary = extractExtractionSummary(response);

        setHighlights(adaptedHighlights);
        setExtractionSummary(summary);
        setExtractionProgress(100);

        // Small delay to show completion
        setTimeout(() => setIsExtracting(false), 500);
      } catch (extractionError) {
        clearInterval(progressInterval);
        throw extractionError;
      }
    } catch (err) {
      console.error('🚫 Extraction failed:', { 
        error: err, 
        message: err instanceof Error ? err.message : 'Unknown error',
        stack: err instanceof Error ? err.stack : undefined 
      });
      setError(err instanceof Error ? err.message : "Failed to process PDF");
      // Keep the demo PDF on error
      setPdfUrl("/deep_speech_2.pdf");
      setIsExtracting(false);
    }
  }, []);

  const showUploadInterface = !selectedFile && highlights.length === 0;

  // Processing state component
  const ProcessingIndicator = () => (
    <div className="max-w-2xl mx-auto pt-12">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Loader2 className="h-5 w-5 animate-spin" />
            Processing PDF
          </CardTitle>
          <CardDescription>Extracting highlights from your research paper...</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>Progress</span>
              <span>{Math.round(extractionProgress)}%</span>
            </div>
            <Progress value={extractionProgress} className="h-2" />
          </div>

          <div className="space-y-2 text-sm text-muted-foreground">
            <div className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-green-500" />
              <span>PDF uploaded successfully</span>
            </div>
            <div className="flex items-center gap-2">
              {extractionProgress > 20 ? (
                <CheckCircle className="h-4 w-4 text-green-500" />
              ) : (
                <Loader2 className="h-4 w-4 animate-spin" />
              )}
              <span>Analyzing document structure</span>
            </div>
            <div className="flex items-center gap-2">
              {extractionProgress > 60 ? (
                <CheckCircle className="h-4 w-4 text-green-500" />
              ) : (
                <div className="h-4 w-4 rounded-full bg-muted" />
              )}
              <span>Extracting key elements (Goals, Methods, Results)</span>
            </div>
            <div className="flex items-center gap-2">
              {extractionProgress > 90 ? (
                <CheckCircle className="h-4 w-4 text-green-500" />
              ) : (
                <div className="h-4 w-4 rounded-full bg-muted" />
              )}
              <span>Mapping coordinates for highlights</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );

  return (
    <div className="flex flex-col min-h-screen">
      {/* Header */}
      <header className="border-b bg-background">
        <div className="container flex items-center justify-between h-14">
          <h1 className="text-lg font-semibold">Academic Paper Skimming Assistant</h1>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 container py-6">
        <div className="flex gap-6">
          {/* Main content area */}
          <div className="flex-1 overflow-auto">
            {showUploadInterface ? (
              // Upload interface when no file is selected
              <div className="max-w-2xl mx-auto pt-12">
                <FileUpload
                  onFileSelect={handleFileSelect}
                  isUploading={isExtracting}
                  uploadProgress={extractionProgress}
                  error={error || undefined}
                />
              </div>
            ) : isExtracting ? (
              // Processing indicator during extraction
              <ProcessingIndicator />
            ) : error ? (
              // Error state
              <div className="max-w-2xl mx-auto pt-12">
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              </div>
            ) : (
              // PDF viewer when file is loaded and processed
              <PDFViewer
                url={pdfUrl}
                highlights={visibleHighlights}
                highlightsEnabled={highlightsEnabled}
                highlightOpacity={highlightOpacity}
              />
            )}
          </div>

          {/* Sidebar */}
          <div className="w-80">
            <SkimmingSidebar
              enabled={highlightsEnabled}
              setEnabled={setHighlightsEnabled}
              opacity={highlightOpacity}
              setOpacity={setHighlightOpacity}
              highlightCount={highlightCount}
              setHighlightCount={setHighlightCount}
              totalHighlights={highlights.length}
              confidenceThreshold={confidenceThreshold}
              setConfidenceThreshold={setConfidenceThreshold}
              highlightsAboveThreshold={filteredHighlights.length}
              extractionSummary={extractionSummary}
              onNewUpload={() => {
                setSelectedFile(null);
                setHighlights([]);
                setExtractionSummary(null);
                setPdfUrl("/deep_speech_2.pdf");
                setError(null);
              }}
            />
          </div>
        </div>
      </main>
    </div>
  );
}
