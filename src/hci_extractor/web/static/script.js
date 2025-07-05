// DOM Elements
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const uploadSection = document.getElementById('upload-section');
const progressSection = document.getElementById('progress-section');
const resultsSection = document.getElementById('results-section');
const errorSection = document.getElementById('error-section');
const progressFill = document.getElementById('progress-fill');
const progressText = document.getElementById('progress-text');
const newExtractionBtn = document.getElementById('new-extraction');
const tryAgainBtn = document.getElementById('try-again');
const typeFilter = document.getElementById('type-filter');
const sectionFilter = document.getElementById('section-filter');

let extractionData = null;

// File Upload Handling
dropZone.addEventListener('click', () => fileInput.click());

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('drag-over');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    
    const files = e.dataTransfer.files;
    if (files.length > 0 && files[0].type === 'application/pdf') {
        handleFile(files[0]);
    } else {
        showError('Please drop a PDF file');
    }
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFile(e.target.files[0]);
    }
});

// File Processing
async function handleFile(file) {
    if (file.type !== 'application/pdf') {
        showError('Please select a PDF file');
        return;
    }
    
    if (file.size > 50 * 1024 * 1024) {
        showError('File is too large. Maximum size is 50MB');
        return;
    }
    
    showProgress();
    await uploadFile(file);
}

async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        updateProgress(10, 'Uploading file...');
        
        const response = await fetch('/api/v1/extract/simple', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Upload failed');
        }
        
        updateProgress(50, 'Processing paper...');
        
        // Simulate progress while processing
        const progressInterval = setInterval(() => {
            const currentProgress = parseInt(progressFill.style.width) || 50;
            if (currentProgress < 90) {
                updateProgress(currentProgress + 5, 'Extracting elements...');
            }
        }, 1000);
        
        const data = await response.json();
        clearInterval(progressInterval);
        
        updateProgress(100, 'Complete!');
        extractionData = data;
        
        setTimeout(() => {
            showResults(data);
        }, 500);
        
    } catch (error) {
        showError(error.message);
    }
}

// Progress Updates
function showProgress() {
    uploadSection.classList.add('hidden');
    progressSection.classList.remove('hidden');
    resultsSection.classList.add('hidden');
    errorSection.classList.add('hidden');
    updateProgress(0, 'Starting...');
}

function updateProgress(percent, text) {
    progressFill.style.width = percent + '%';
    progressText.textContent = text;
}

// Results Display
function showResults(data) {
    progressSection.classList.add('hidden');
    resultsSection.classList.remove('hidden');
    
    // Paper Info
    document.getElementById('paper-title').textContent = data.paper.title || 'Untitled Paper';
    document.getElementById('paper-authors').textContent = 
        data.paper.authors ? data.paper.authors.join(', ') : '';
    document.getElementById('paper-venue').textContent = 
        data.paper.venue ? `${data.paper.venue}${data.paper.year ? ', ' + data.paper.year : ''}` : '';
    
    // Summary
    document.getElementById('total-elements').textContent = data.extraction_summary.total_elements;
    document.getElementById('processing-time').textContent = 
        Math.round(data.extraction_summary.processing_time_seconds) + 's';
    document.getElementById('avg-confidence').textContent = 
        Math.round(data.extraction_summary.average_confidence * 100) + '%';
    
    // Populate section filter
    const sections = [...new Set(data.extracted_elements.map(el => el.section))];
    sectionFilter.innerHTML = '<option value="">All sections</option>';
    sections.forEach(section => {
        const option = document.createElement('option');
        option.value = section;
        option.textContent = section;
        sectionFilter.appendChild(option);
    });
    
    // Display elements
    displayElements(data.extracted_elements);
}

function displayElements(elements) {
    const elementsList = document.getElementById('elements-list');
    elementsList.innerHTML = '';
    
    const typeFilterValue = typeFilter.value;
    const sectionFilterValue = sectionFilter.value;
    
    const filteredElements = elements.filter(el => {
        return (!typeFilterValue || el.element_type === typeFilterValue) &&
               (!sectionFilterValue || el.section === sectionFilterValue);
    });
    
    if (filteredElements.length === 0) {
        elementsList.innerHTML = '<p style="text-align: center; color: #7f8c8d;">No elements found matching filters</p>';
        return;
    }
    
    filteredElements.forEach(element => {
        const card = document.createElement('div');
        card.className = `element-card ${element.element_type}`;
        
        const typeColor = {
            claim: '#e74c3c',
            finding: '#27ae60',
            method: '#f39c12',
            artifact: '#9b59b6'
        }[element.element_type] || '#3498db';
        
        card.innerHTML = `
            <div class="element-header">
                <span class="element-type" style="color: ${typeColor}">${element.element_type}</span>
                <span class="confidence">Confidence: ${Math.round(element.confidence * 100)}%</span>
            </div>
            <div class="element-text">${escapeHtml(element.text)}</div>
            <div class="element-meta">
                ${element.section} • ${element.evidence_type}
                ${element.page_number ? ` • Page ${element.page_number}` : ''}
            </div>
        `;
        
        elementsList.appendChild(card);
    });
}

// Error Handling
function showError(message) {
    uploadSection.classList.add('hidden');
    progressSection.classList.add('hidden');
    resultsSection.classList.add('hidden');
    errorSection.classList.remove('hidden');
    
    document.getElementById('error-message').textContent = message;
}

// Event Listeners
newExtractionBtn.addEventListener('click', reset);
tryAgainBtn.addEventListener('click', reset);
typeFilter.addEventListener('change', () => {
    if (extractionData) {
        displayElements(extractionData.extracted_elements);
    }
});
sectionFilter.addEventListener('change', () => {
    if (extractionData) {
        displayElements(extractionData.extracted_elements);
    }
});

// Reset
function reset() {
    uploadSection.classList.remove('hidden');
    progressSection.classList.add('hidden');
    resultsSection.classList.add('hidden');
    errorSection.classList.add('hidden');
    fileInput.value = '';
    extractionData = null;
}

// Utility Functions
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}