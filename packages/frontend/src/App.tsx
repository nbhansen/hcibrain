import React, { useState } from 'react';
import './App.css';

interface PaperInfo {
  title: string;
  authors: string[];
  paper_id: string;
}

interface MarkupResponse {
  paper_full_text_with_markup: string;
  paper_info: PaperInfo;
  processing_time_seconds: number;
}

function App() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [markupResult, setMarkupResult] = useState<MarkupResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file && file.type === 'application/pdf') {
      setSelectedFile(file);
      setError(null);
    } else {
      setError('Please select a PDF file');
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setIsProcessing(true);
    setProgress(0);
    setError(null);

    // Simulate progress
    const progressInterval = setInterval(() => {
      setProgress(prev => {
        if (prev < 90) return prev + Math.random() * 15;
        return prev;
      });
    }, 1000);

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);

      console.log('🚀 Uploading PDF to backend:', selectedFile.name);

      const response = await fetch('http://localhost:8000/api/v1/extract/markup', {
        method: 'POST',
        body: formData,
      });

      clearInterval(progressInterval);

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Backend error: ${response.status} - ${errorText}`);
      }

      const result: MarkupResponse = await response.json();
      
      console.log('✅ Markup extraction successful:', {
        textLength: result.paper_full_text_with_markup.length,
        processingTime: result.processing_time_seconds,
        paperTitle: result.paper_info.title
      });

      setMarkupResult(result);
      setProgress(100);
    } catch (err) {
      clearInterval(progressInterval);
      console.error('❌ Upload failed:', err);
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setIsProcessing(false);
    }
  };

  const resetUpload = () => {
    setSelectedFile(null);
    setMarkupResult(null);
    setError(null);
    setProgress(0);
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>🎓 Academic Paper Markup Assistant</h1>
        <p>Upload a PDF to extract goals, methods, and results with color-coded highlights</p>
      </header>

      <main className="app-main">
        {!markupResult ? (
          <div className="upload-section">
            <div className="upload-card">
              <h2>📄 Upload Academic Paper</h2>
              
              <div className="file-input-wrapper">
                <input
                  type="file"
                  accept=".pdf"
                  onChange={handleFileSelect}
                  disabled={isProcessing}
                  id="pdf-upload"
                />
                <label htmlFor="pdf-upload" className="file-input-label">
                  {selectedFile ? selectedFile.name : 'Choose PDF file...'}
                </label>
              </div>

              {selectedFile && !isProcessing && (
                <button onClick={handleUpload} className="upload-button">
                  🚀 Process PDF
                </button>
              )}

              {isProcessing && (
                <div className="processing-status">
                  <div className="progress-bar">
                    <div 
                      className="progress-fill" 
                      style={{ width: `${progress}%` }}
                    ></div>
                  </div>
                  <p>Processing... {Math.round(progress)}%</p>
                  <small>
                    {progress < 20 && "📄 Uploading PDF..."}
                    {progress >= 20 && progress < 50 && "🔍 Extracting text..."}
                    {progress >= 50 && progress < 80 && "🤖 Processing with AI (chunking large document)..."}
                    {progress >= 80 && "✨ Generating markup..."}
                  </small>
                </div>
              )}

              {error && (
                <div className="error-message">
                  ❌ {error}
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="results-section">
            <div className="results-header">
              <h2>📊 Results</h2>
              <button onClick={resetUpload} className="new-upload-button">
                📄 Upload New PDF
              </button>
            </div>

            <div className="paper-info">
              <h3>{markupResult.paper_info.title}</h3>
              <p><strong>Authors:</strong> {markupResult.paper_info.authors.join(', ')}</p>
              <p><strong>Processing time:</strong> {markupResult.processing_time_seconds.toFixed(1)}s</p>
            </div>

            <div className="markup-legend">
              <h4>📝 Markup Legend:</h4>
              <div className="legend-items">
                <span className="legend-item">
                  <span className="legend-color goal"></span>
                  Goals & Objectives
                </span>
                <span className="legend-item">
                  <span className="legend-color method"></span>
                  Methods & Approaches
                </span>
                <span className="legend-item">
                  <span className="legend-color result"></span>
                  Results & Findings
                </span>
              </div>
            </div>

            <div 
              className="markup-content"
              dangerouslySetInnerHTML={{ 
                __html: markupResult.paper_full_text_with_markup 
              }}
            />
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
