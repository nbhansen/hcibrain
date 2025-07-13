export const UI_TEXT = {
  APP_TITLE: '🎓 Academic Paper Markup Assistant',
  APP_DESCRIPTION: 'Upload a PDF to extract goals, methods, and results with color-coded highlights',
  UPLOAD_TITLE: '📄 Upload Academic Paper',
  CHOOSE_FILE: 'Choose PDF file...',
  PROCESS_BUTTON: '🚀 Process PDF',
  PROCESSING: 'Processing PDF...',
  PROCESSING_DESCRIPTION: '🤖 AI is analyzing your paper...',
  RESULTS_TITLE: '📊 Results',
  NEW_UPLOAD_BUTTON: '📄 Upload New PDF',
  SUMMARY_TITLE: 'Plain Language Summary',
  LEGEND_TITLE: '📝 Markup Legend:',
  LEGEND_GOALS: 'Goals & Objectives',
  LEGEND_METHODS: 'Methods & Approaches', 
  LEGEND_RESULTS: 'Results & Findings',
  FILE_ERROR: 'Please select a PDF file',
  UPLOAD_FAILED: 'Upload failed',
  ERROR_BOUNDARY_TITLE: 'Something went wrong',
  ERROR_BOUNDARY_MESSAGE: 'Please refresh the page and try again.',
  AUTHORS_LABEL: 'Authors:',
  PROCESSING_TIME_LABEL: 'Processing time:',
  EXPORT_BUTTON: '📄 Export Markdown',
  EXPORT_FILENAME_PREFIX: 'academic-paper'
} as const;

export const API_ENDPOINTS = {
  MARKUP: 'http://localhost:8000/api/v1/extract/markup'
} as const;