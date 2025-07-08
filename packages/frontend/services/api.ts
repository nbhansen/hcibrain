import type {
  ApiError,
  BackendConfigResponse,
  BackendExtractionResponse,
  BackendHealthResponse,
} from "@/types/api";

// API Configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_ENDPOINTS = {
  health: "/api/v1/health",
  config: "/api/v1/config",
  extractWithCoordinates: "/api/v1/extract/with-coordinates",
  extractSimple: "/api/v1/extract/simple",
} as const;

class ApiService {
  private baseUrl: string;

  constructor(baseUrl = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async makeRequest<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    
    console.log('🔗 API Request:', { url, method: options.method || 'GET', hasBody: !!options.body });

    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          Accept: "application/json",
          ...options.headers,
        },
      });

      console.log('✅ API Response:', { status: response.status, ok: response.ok });
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('❌ API Error:', { status: response.status, statusText: response.statusText, errorText });
        const error: ApiError = {
          message: `API request failed: ${response.status} ${response.statusText}`,
          status: response.status,
          details: errorText,
        };
        throw error;
      }

      const data = await response.json();
      console.log('📚 API Data received:', { hasData: !!data, type: typeof data });
      return data;
    } catch (error) {
      console.error('🚫 API Request Failed:', { error, url, endpoint });
      
      // Check if error is already an ApiError (has expected shape)
      if (error && typeof error === "object" && "message" in error && "status" in error) {
        throw error;
      }

      const networkError: ApiError = {
        message: `Network error: ${error instanceof Error ? error.message : "Unknown error"}`,
        status: 0,
      };
      throw networkError;
    }
  }

  async checkHealth(): Promise<BackendHealthResponse> {
    return this.makeRequest<BackendHealthResponse>(API_ENDPOINTS.health);
  }

  async getConfig(): Promise<BackendConfigResponse> {
    return this.makeRequest<BackendConfigResponse>(API_ENDPOINTS.config);
  }

  async extractPdfWithCoordinates(
    file: File,
    _onProgress?: (progress: { loaded: number; total: number }) => void
  ): Promise<BackendExtractionResponse> {
    const formData = new FormData();
    formData.append("file", file);

    return this.makeRequest<BackendExtractionResponse>(API_ENDPOINTS.extractWithCoordinates, {
      method: "POST",
      body: formData,
      // Note: Don't set Content-Type header, let browser set it for FormData
    });
  }

  async extractPdfSimple(file: File): Promise<BackendExtractionResponse> {
    const formData = new FormData();
    formData.append("file", file);

    return this.makeRequest<BackendExtractionResponse>(API_ENDPOINTS.extractSimple, {
      method: "POST",
      body: formData,
    });
  }
}

// Create a singleton instance
export const apiService = new ApiService();

// Export individual methods for convenience (with proper binding)
export const checkHealth = apiService.checkHealth.bind(apiService);
export const getConfig = apiService.getConfig.bind(apiService);
export const extractPdfWithCoordinates = apiService.extractPdfWithCoordinates.bind(apiService);
export const extractPdfSimple = apiService.extractPdfSimple.bind(apiService);
