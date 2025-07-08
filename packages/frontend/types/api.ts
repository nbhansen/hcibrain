// Backend API Types and Interfaces

export interface BackendExtractedElement {
  element_id: string;
  element_type: "claim" | "finding" | "method" | "artifact";
  text: string;
  section: string;
  confidence: number;
  evidence_type: "quantitative" | "qualitative" | "theoretical" | "unknown";
  page_number?: number;
  coordinates?: {
    page_number: number;
    x: number;
    y: number;
    width: number;
    height: number;
    char_start: number;
    char_end: number;
  };
  supporting_evidence?: string;
  methodology_context?: string;
  study_population?: string;
  limitations?: string;
  surrounding_context?: string;
}

export interface BackendExtractionResponse {
  paper: {
    paper_id: string;
    title: string;
    authors: string[];
  };
  extraction_summary: {
    total_elements: number;
    elements_by_type: Record<string, number>;
    elements_by_section: Record<string, number>;
    average_confidence: number;
    processing_time_seconds: number;
    created_at: string;
    paper_summary?: string;
    paper_summary_confidence?: number;
  };
  extracted_elements: BackendExtractedElement[];
}

export interface BackendHealthResponse {
  status: "healthy" | "unhealthy";
  service: string;
}

export interface BackendConfigResponse {
  analysis: {
    chunk_size: number;
    max_concurrent_sections: number;
    temperature: number;
  };
  extraction: {
    max_file_size_mb: number;
    timeout_seconds: number;
  };
  retry: {
    max_attempts: number;
  };
}

export interface ApiError {
  message: string;
  status: number;
  details?: string;
}
