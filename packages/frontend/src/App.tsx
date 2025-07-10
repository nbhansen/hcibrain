import React, { useState, useEffect, useCallback, useRef } from 'react';
import DOMPurify from 'dompurify';
import './App.css';
import { UI_TEXT, API_ENDPOINTS } from './constants';

interface PaperInfo {
  title: string;
  authors: string[];
  paper_id: string;
}

interface MarkupResponse {
  paper_full_text_with_markup: string;
  paper_info: PaperInfo;
  plain_language_summary: string;
  processing_time_seconds: number;
}

interface TocItem {
  id: string;
  text: string;
  level: number;
  element?: HTMLElement;
}

function App() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [markupResult, setMarkupResult] = useState<MarkupResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  
  // TOC state
  const [tocItems, setTocItems] = useState<TocItem[]>([]);
  const [activeSection, setActiveSection] = useState<string>('');
  const [processedHtml, setProcessedHtml] = useState<string>('');
  const markupContentRef = useRef<HTMLDivElement>(null);
  const observerRef = useRef<IntersectionObserver | null>(null);
  
  // Filter state
  const [filters, setFilters] = useState({
    goals: true,
    methods: true,
    results: true,
  });

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file && file.type === 'application/pdf') {
      setSelectedFile(file);
      setError(null);
    } else {
      setError(UI_TEXT.FILE_ERROR);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setIsProcessing(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);

      const response = await fetch(API_ENDPOINTS.MARKUP, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Backend error: ${response.status} - ${errorText}`);
      }

      const result: MarkupResponse = await response.json();
      setMarkupResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : UI_TEXT.UPLOAD_FAILED);
    } finally {
      setIsProcessing(false);
    }
  };

  const resetUpload = () => {
    setSelectedFile(null);
    setMarkupResult(null);
    setError(null);
    setTocItems([]);
    setActiveSection('');
    setProcessedHtml('');
    
    // Clean up intersection observer
    if (observerRef.current) {
      observerRef.current.disconnect();
      observerRef.current = null;
    }
  };

  // Add IDs to headings in HTML content for navigation
  const addHeadingIds = useCallback((htmlContent: string): string => {
    const parser = new DOMParser();
    const doc = parser.parseFromString(htmlContent, 'text/html');
    const headings = doc.querySelectorAll('h1, h2, h3, h4, h5, h6');
    
    // Add IDs to headings that don't already have them
    Array.from(headings)
      .filter((heading) => heading.textContent && heading.textContent.trim().length > 0)
      .forEach((heading, index) => {
        if (!heading.id) {
          heading.id = `heading-${index}`;
        }
      });
    
    return doc.body.innerHTML;
  }, []);

  // Generate TOC from HTML content
  const generateTOC = useCallback((htmlContent: string): TocItem[] => {
    const parser = new DOMParser();
    const doc = parser.parseFromString(htmlContent, 'text/html');
    const headings = doc.querySelectorAll('h1, h2, h3, h4, h5, h6');
    
    return Array.from(headings)
      .filter((heading) => heading.textContent && heading.textContent.trim().length > 0)
      .map((heading, index) => ({
        id: heading.id || `heading-${index}`,
        text: heading.textContent?.trim() || '',
        level: parseInt(heading.tagName.charAt(1)),
      }));
  }, []);

  // Setup intersection observer for active section tracking
  const setupIntersectionObserver = useCallback(() => {
    if (!markupContentRef.current) return;

    // Clean up existing observer
    if (observerRef.current) {
      observerRef.current.disconnect();
    }

    const headings = markupContentRef.current.querySelectorAll('h1, h2, h3, h4, h5, h6');
    
    // Create intersection observer
    const options = {
      root: markupContentRef.current,
      rootMargin: '-20% 0px -70% 0px',
      threshold: 0,
    };

    observerRef.current = new IntersectionObserver((entries) => {
      let mostVisible = '';
      let maxRatio = 0;

      entries.forEach((entry) => {
        if (entry.isIntersecting && entry.intersectionRatio > maxRatio) {
          maxRatio = entry.intersectionRatio;
          mostVisible = entry.target.id;
        }
      });

      if (mostVisible) {
        setActiveSection(mostVisible);
      }
    }, options);

    // Observe all headings
    headings.forEach((heading) => {
      if (observerRef.current) {
        observerRef.current.observe(heading);
      }
    });
  }, []);

  // Handle TOC item click with smooth scrolling
  const handleTocClick = useCallback((itemId: string) => {
    const element = document.getElementById(itemId);
    if (element && markupContentRef.current) {
      const container = markupContentRef.current;
      const containerRect = container.getBoundingClientRect();
      const elementRect = element.getBoundingClientRect();
      
      const scrollTop = container.scrollTop + elementRect.top - containerRect.top - 20;
      
      container.scrollTo({
        top: scrollTop,
        behavior: 'smooth',
      });
      
      setActiveSection(itemId);
    }
  }, []);

  // Handle filter toggle
  const toggleFilter = useCallback((filterType: 'goals' | 'methods' | 'results') => {
    setFilters(prev => ({
      ...prev,
      [filterType]: !prev[filterType],
    }));
  }, []);

  // Setup TOC and processed HTML when markup result is available
  useEffect(() => {
    if (markupResult?.paper_full_text_with_markup) {
      // Process HTML to add heading IDs
      const htmlWithIds = addHeadingIds(markupResult.paper_full_text_with_markup);
      setProcessedHtml(htmlWithIds);
      
      // Generate TOC from processed HTML
      const toc = generateTOC(htmlWithIds);
      setTocItems(toc);
    }
  }, [markupResult, generateTOC, addHeadingIds]);

  // Setup intersection observer when processed HTML is ready
  useEffect(() => {
    if (processedHtml && tocItems.length > 0) {
      // Setup observer after DOM is updated
      setTimeout(() => {
        setupIntersectionObserver();
      }, 100);
    }
  }, [processedHtml, tocItems.length, setupIntersectionObserver]);

  // Cleanup observer on unmount
  useEffect(() => {
    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect();
      }
    };
  }, []);

  return (
    <div className="app">
      <header className="app-header">
        <h1>{UI_TEXT.APP_TITLE}</h1>
        <p>{UI_TEXT.APP_DESCRIPTION}</p>
      </header>

      <main className="app-main">
        {!markupResult ? (
          <div className="upload-section">
            <div className="upload-card">
              <h2>{UI_TEXT.UPLOAD_TITLE}</h2>
              
              <div className="file-input-wrapper">
                <input
                  type="file"
                  accept=".pdf"
                  onChange={handleFileSelect}
                  disabled={isProcessing}
                  id="pdf-upload"
                />
                <label htmlFor="pdf-upload" className="file-input-label">
                  {selectedFile ? selectedFile.name : UI_TEXT.CHOOSE_FILE}
                </label>
              </div>

              {selectedFile && !isProcessing && (
                <button onClick={handleUpload} className="upload-button">
                  {UI_TEXT.PROCESS_BUTTON}
                </button>
              )}

              {isProcessing && (
                <div className="processing-status">
                  <div className="progress-bar">
                    <div className="progress-fill"></div>
                  </div>
                  <p>{UI_TEXT.PROCESSING}</p>
                  <small>{UI_TEXT.PROCESSING_DESCRIPTION}</small>
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
              <h2>{UI_TEXT.RESULTS_TITLE}</h2>
              <button onClick={resetUpload} className="new-upload-button">
                {UI_TEXT.NEW_UPLOAD_BUTTON}
              </button>
            </div>

            {markupResult.plain_language_summary && (
              <div className="summary-section">
                <h3>{UI_TEXT.SUMMARY_TITLE}</h3>
                <p className="summary-text">{markupResult.plain_language_summary}</p>
              </div>
            )}

            <div className="paper-info">
              <h3>{markupResult.paper_info.title}</h3>
              <p><strong>{UI_TEXT.AUTHORS_LABEL}</strong> {markupResult.paper_info.authors.join(', ')}</p>
              <p><strong>{UI_TEXT.PROCESSING_TIME_LABEL}</strong> {markupResult.processing_time_seconds.toFixed(1)}s</p>
            </div>

            <div className="markup-legend">
              <h4>{UI_TEXT.LEGEND_TITLE}</h4>
              <div className="legend-items">
                <button 
                  className={`legend-item legend-toggle ${filters.goals ? 'active' : ''}`}
                  onClick={() => toggleFilter('goals')}
                  title={filters.goals ? 'Hide Goals' : 'Show Goals'}
                >
                  <span className="legend-color goal"></span>
                  {UI_TEXT.LEGEND_GOALS}
                </button>
                <button 
                  className={`legend-item legend-toggle ${filters.methods ? 'active' : ''}`}
                  onClick={() => toggleFilter('methods')}
                  title={filters.methods ? 'Hide Methods' : 'Show Methods'}
                >
                  <span className="legend-color method"></span>
                  {UI_TEXT.LEGEND_METHODS}
                </button>
                <button 
                  className={`legend-item legend-toggle ${filters.results ? 'active' : ''}`}
                  onClick={() => toggleFilter('results')}
                  title={filters.results ? 'Hide Results' : 'Show Results'}
                >
                  <span className="legend-color result"></span>
                  {UI_TEXT.LEGEND_RESULTS}
                </button>
              </div>
            </div>

            <div className="results-layout">
              {/* Table of Contents Sidebar */}
              {tocItems.length > 0 && (
                <div className="toc-sidebar">
                  <div className="toc-container">
                    <h4 className="toc-title">📑 Table of Contents</h4>
                    <nav className="toc-nav">
                      {tocItems.map((item) => (
                        <button
                          key={item.id}
                          className={`toc-item toc-level-${item.level} ${
                            activeSection === item.id ? 'active' : ''
                          }`}
                          onClick={() => handleTocClick(item.id)}
                          title={item.text}
                        >
                          {item.text}
                        </button>
                      ))}
                    </nav>
                  </div>
                </div>
              )}

              {/* Main Content */}
              <div className="content-main">
                {/* Note: HTML content contains goal/method/result markup tags from backend AI analysis */}
                <div 
                  ref={markupContentRef}
                  className={`markup-content ${!filters.goals ? 'hide-goals' : ''} ${!filters.methods ? 'hide-methods' : ''} ${!filters.results ? 'hide-results' : ''}`}
                  dangerouslySetInnerHTML={{ 
                    __html: DOMPurify.sanitize(processedHtml || markupResult.paper_full_text_with_markup, {
                      ADD_TAGS: ['goal', 'method', 'result', 'summary'],
                      ADD_ATTR: ['confidence']
                    })
                  }}
                />
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
