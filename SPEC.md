# HCIBrain System Specification

**Version**: 1.0  
**Date**: January 13, 2025  
**Purpose**: User-facing specification describing system capabilities and usage

## What is HCIBrain?

HCIBrain is an AI-powered academic paper analysis system that automatically identifies and highlights key research components within PDF documents. It helps researchers, students, and academics quickly understand the essential elements of research papers by using advanced language models to extract and categorize important information.

## Core Capabilities

### 1. **Automatic Research Component Detection**

The system identifies and marks up four key types of content in academic papers:

- **🎯 Research Goals** - What the researchers aimed to achieve
  - Research questions and hypotheses
  - Study objectives and aims
  - Problem statements
  - Intended contributions

- **🔬 Methods** - How the research was conducted
  - Study design and methodology
  - Data collection procedures
  - Analysis techniques
  - Experimental setups

- **📊 Results** - What the researchers found
  - Key findings and outcomes
  - Statistical results
  - Performance metrics
  - Empirical observations

- **💬 Plain Language Summaries** - Accessible explanations
  - Simplified descriptions of complex concepts
  - Non-technical summaries of findings
  - Broader impact statements
  - Accessible interpretations

### 2. **Visual Highlighting System**

Each type of content is highlighted with a distinct color in the web interface:
- Goals: Blue highlighting
- Methods: Green highlighting  
- Results: Orange highlighting
- Plain Language: Purple highlighting

### 3. **Interactive Filtering**

Users can toggle the visibility of different content types to focus on specific aspects:
- Show/hide individual categories
- View only the marked-up content
- See the original text without markup
- Navigate between highlighted sections

### 4. **Document Processing Features**

- **Large Document Support**: Automatically chunks large papers for processing
- **Progress Tracking**: Real-time updates during document analysis
- **Table of Contents**: Auto-generated navigation for quick access to sections
- **Confidence Scores**: Each identified element includes a confidence rating

## How It Works

### Step 1: Upload Your Paper
Simply drag and drop or select a PDF file through the web interface. The system accepts standard academic paper PDFs up to 50MB in size.

### Step 2: Automatic Analysis
The system:
1. Extracts text content from your PDF
2. Identifies document structure and sections
3. Sends content to AI language models for analysis
4. Receives marked-up content with identified research components

### Step 3: Review Results
The processed paper appears with:
- Color-coded highlights for each component type
- Confidence indicators showing analysis certainty
- Interactive controls to filter content
- Navigation aids for long documents

## Supported Document Types

### ✅ Works Best With:
- Academic research papers
- Conference proceedings
- Journal articles
- Technical reports
- Thesis chapters
- Research proposals

### ⚠️ Limited Support:
- Heavily formatted documents with complex layouts
- Papers with extensive mathematical notation
- Documents primarily consisting of figures/tables
- Non-English papers (currently English-only)

## Processing Time Expectations

Processing time depends on document length and complexity:

| Document Size | Typical Processing Time |
|--------------|------------------------|
| 1-5 pages | 15-30 seconds |
| 5-15 pages | 30-90 seconds |
| 15-30 pages | 90-180 seconds |
| 30+ pages | 3-5 minutes |

*Note: Times may vary based on server load and API response times*

## User Interface Features

### Web Application
- **Responsive Design**: Works on desktop, tablet, and mobile devices
- **Real-time Updates**: Progress bar shows processing status
- **Error Handling**: Clear error messages if processing fails
- **Download Results**: Export processed papers with markup

### Filtering Controls
- Toggle buttons for each content type
- "Show All" / "Hide All" quick actions
- Persistent filter settings during session
- Visual feedback for active filters

### Navigation
- Clickable table of contents
- Scroll to highlighted sections
- Section-by-section navigation
- Return to top button

## API Access

For programmatic access, the system provides a REST API:

### Endpoints

**Health Check**
```
GET /api/v1/health
```
Verify system availability

**Process Document**
```
POST /api/v1/extract/markup
Content-Type: multipart/form-data

file: [PDF file]
```
Upload and process a PDF document

**Response Format**
```json
{
  "paper_full_text_with_markup": "...",
  "paper_info": {
    "title": "Paper Title",
    "authors": ["Author Names"]
  },
  "plain_language_summary": "...",
  "processing_time_seconds": 45.2
}
```

## Accuracy and Limitations

### Accuracy Expectations
- **High Confidence (>80%)**: Clear, well-structured statements
- **Medium Confidence (50-80%)**: Context-dependent interpretations
- **Low Confidence (<50%)**: Ambiguous or unclear content

### Known Limitations
1. **Language**: Currently supports English-language papers only
2. **Format**: Best results with standard academic paper formats
3. **Quality**: Depends on PDF text extraction quality
4. **Context**: May miss nuanced or discipline-specific terminology
5. **Length**: Very long papers may have reduced accuracy in later sections

## Privacy and Security

### Data Handling
- Papers are processed in memory only
- No permanent storage of uploaded documents
- Temporary files are automatically cleaned up
- No user tracking or analytics

### Security Measures
- File type validation (PDF only)
- Size limits to prevent abuse
- Input sanitization for all text
- XSS protection in web interface

## Best Practices for Optimal Results

### 1. **Document Preparation**
- Use text-based PDFs (not scanned images)
- Ensure good OCR quality if scanned
- Standard academic formatting helps accuracy

### 2. **Content Structure**
- Papers with clear sections work best
- Abstract and introduction improve summary quality
- Explicit methodology sections enhance detection

### 3. **Usage Tips**
- Start with shorter papers to understand the system
- Use confidence scores to gauge reliability
- Cross-reference important findings with original text
- Report consistent errors for specific paper types

## Common Use Cases

### 1. **Literature Review**
Quickly identify methods and results across multiple papers

### 2. **Research Synthesis**
Extract and compare research goals from related studies

### 3. **Teaching and Learning**
Help students understand paper structure and key components

### 4. **Accessibility**
Access plain language summaries of complex research

### 5. **Time-Saving**
Rapid overview before detailed reading

## Troubleshooting

### Upload Fails
- Verify file is a valid PDF
- Check file size (<50MB)
- Ensure file is not password-protected

### Processing Errors
- Try again after a few minutes
- Check for unusual formatting in PDF
- Verify text is extractable from PDF

### No Results Found
- Paper may lack standard academic structure
- Content may be too technical or specialized
- Document might be in unsupported language

### Incorrect Markup
- Check confidence scores for reliability
- Some disciplines use non-standard terminology
- Complex nested content may confuse analysis

## Future Enhancements

Planned improvements include:
- Multi-language support
- Additional content categories
- Batch processing capabilities
- Export to various formats
- Citation extraction
- Figure and table analysis
- Collaborative annotation features

## Getting Help

For issues or questions:
1. Check this specification document
2. Review the troubleshooting section
3. Examine error messages carefully
4. Contact support with specific examples

## Conclusion

HCIBrain streamlines academic paper analysis by automatically identifying and highlighting key research components. While it cannot replace careful reading and critical analysis, it serves as a powerful tool for initial paper assessment, literature review, and improving research accessibility.