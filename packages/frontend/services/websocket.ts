/**
 * WebSocket service for real-time progress tracking during PDF extraction
 */

export interface ProgressUpdate {
  stage: string;
  progress: number;
  message: string;
  timestamp: string;
}

export type ProgressCallback = (update: ProgressUpdate) => void;

class WebSocketService {
  private ws: WebSocket | null = null;
  private sessionId: string | null = null;
  private progressCallback: ProgressCallback | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 3;

  /**
   * Connects to the WebSocket endpoint for progress tracking
   */
  connect(sessionId: string, onProgress: ProgressCallback): Promise<void> {
    this.sessionId = sessionId;
    this.progressCallback = onProgress;

    return new Promise((resolve, reject) => {
      try {
        const wsUrl = `ws://localhost:8000/api/v1/ws/progress/${sessionId}`;
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
          console.log("WebSocket connected for session:", sessionId);
          this.reconnectAttempts = 0;
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const update: ProgressUpdate = JSON.parse(event.data);
            this.progressCallback?.(update);
          } catch (error) {
            console.error("Failed to parse WebSocket message:", error);
          }
        };

        this.ws.onclose = (event) => {
          console.log("WebSocket closed:", event.code, event.reason);
          this.handleReconnect();
        };

        this.ws.onerror = (error) => {
          console.error("WebSocket error:", error);
          reject(error);
        };
      } catch (error) {
        reject(error);
      }
    });
  }

  /**
   * Disconnects from the WebSocket
   */
  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.sessionId = null;
    this.progressCallback = null;
    this.reconnectAttempts = 0;
  }

  /**
   * Handles automatic reconnection with exponential backoff
   */
  private handleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts || !this.sessionId) {
      console.log("Max reconnection attempts reached or no session ID");
      return;
    }

    const delay = 2 ** this.reconnectAttempts * 1000; // Exponential backoff
    this.reconnectAttempts++;

    console.log(`Attempting to reconnect in ${delay}ms (attempt ${this.reconnectAttempts})`);

    setTimeout(() => {
      if (this.sessionId && this.progressCallback) {
        this.connect(this.sessionId, this.progressCallback).catch((error) => {
          console.error("Reconnection failed:", error);
        });
      }
    }, delay);
  }

  /**
   * Checks if WebSocket is currently connected
   */
  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

// Create singleton instance
export const webSocketService = new WebSocketService();

/**
 * Hook for using WebSocket progress tracking in React components
 */
export function useProgressWebSocket() {
  const connect = (sessionId: string, onProgress: ProgressCallback) => {
    return webSocketService.connect(sessionId, onProgress);
  };

  const disconnect = () => {
    webSocketService.disconnect();
  };

  const isConnected = () => {
    return webSocketService.isConnected();
  };

  return {
    connect,
    disconnect,
    isConnected,
  };
}
