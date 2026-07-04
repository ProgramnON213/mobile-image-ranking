// State Management
let appState = {
    folderExists: false,
    results: {
        phone: [],
        laptop: []
    },
    selections: {
        phone: new Map(),
        laptop: new Map()
    },
    activeTab: 'phone',
    currentPage: 1,
    pageSize: 12,
    progressPollInterval: null
};

// UI Elements
const els = {
    folderPath: document.getElementById('folder-path'),
    btnBrowse: document.getElementById('btn-browse'),
    folderStatus: document.getElementById('folder-status'),
    posPrompts: document.getElementById('pos-prompts'),
    negPrompts: document.getElementById('neg-prompts'),
    
    phoneWidth: document.getElementById('phone-width'),
    phoneHeight: document.getElementById('phone-height'),
    laptopWidth: document.getElementById('laptop-width'),
    laptopHeight: document.getElementById('laptop-height'),
    topK: document.getElementById('top-k'),
    outputPath: document.getElementById('output-path'),
    
    btnAnalyze: document.getElementById('btn-analyze'),
    loadingArea: document.getElementById('loading-area'),
    resultsArea: document.getElementById('results-area'),
    previewsGrid: document.getElementById('previews-grid'),
    
    // Progress UI Elements
    progressTitle: document.getElementById('progress-main-title'),
    progressGpu: document.getElementById('progress-gpu-status'),
    progressCache: document.getElementById('progress-cache-status'),
    progressFiles: document.getElementById('progress-files-status'),
    progressFill: document.getElementById('progress-fill'),
    progressPercent: document.getElementById('progress-percent'),
    progressMsg: document.getElementById('progress-msg'),
    
    tabBtns: document.querySelectorAll('.tab-btn'),
    paginationSummary: document.getElementById('pagination-summary'),
    pageNum: document.getElementById('page-num'),
    btnPrev: document.getElementById('btn-prev'),
    btnNext: document.getElementById('btn-next'),
    
    btnSave: document.getElementById('btn-save'),
    selectCount: document.getElementById('select-count')
};

// Initialize listeners
document.addEventListener('DOMContentLoaded', () => {
    // Browse native folder picker
    els.btnBrowse.addEventListener('click', async () => {
        try {
            els.btnBrowse.disabled = true;
            els.btnBrowse.textContent = 'Picking...';
            const res = await fetch('/api/select_folder');
            const data = await res.json();
            if (data.folder) {
                els.folderPath.value = data.folder;
                checkFolderStatus();
            }
        } catch (e) {
            console.error('Error selecting folder:', e);
        } finally {
            els.btnBrowse.disabled = false;
            els.btnBrowse.textContent = 'Browse...';
        }
    });

    // Debounce folder path checking
    let debounceTimer;
    els.folderPath.addEventListener('input', () => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(checkFolderStatus, 600);
    });
    
    if (els.folderPath.value) {
        checkFolderStatus();
    }

    els.btnAnalyze.addEventListener('click', startAnalysis);
    
    // Tab switching
    els.tabBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            els.tabBtns.forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            appState.activeTab = e.target.dataset.tab;
            appState.currentPage = 1;
            renderResults();
        });
    });

    // Pagination
    els.btnPrev.addEventListener('click', () => {
        if (appState.currentPage > 1) {
            appState.currentPage--;
            renderResults();
        }
    });

    els.btnNext.addEventListener('click', () => {
        const totalItems = appState.results[appState.activeTab].length;
        const totalPages = Math.ceil(totalItems / appState.pageSize);
        if (appState.currentPage < totalPages) {
            appState.currentPage++;
            renderResults();
        }
    });

    els.btnSave.addEventListener('click', saveWallpapers);
});

// Check Folder Status via API
async function checkFolderStatus() {
    const folder = els.folderPath.value.trim();
    if (!folder) {
        els.folderStatus.textContent = 'Folder not loaded';
        els.folderStatus.className = 'folder-status-badge';
        appState.folderExists = false;
        return;
    }

    try {
        const res = await fetch(`/api/status?folder=${encodeURIComponent(folder)}`);
        const data = await res.json();
        
        if (data.exists) {
            let statusText = `Found ${data.images} images`;
            if (data.videos > 0) statusText += `, ${data.videos} videos/GIFs`;
            statusText += ` | GPU: ${data.gpu_available ? data.gpu_name : 'OFFLINE (CPU)'}`;
            if (data.has_cache) statusText += ` | Cache: READY`;

            els.folderStatus.textContent = statusText;
            els.folderStatus.className = 'folder-status-badge success';
            appState.folderExists = true;
        } else {
            els.folderStatus.textContent = 'Folder path does not exist';
            els.folderStatus.className = 'folder-status-badge error';
            appState.folderExists = false;
        }
    } catch (e) {
        els.folderStatus.textContent = 'Error checking folder status';
        els.folderStatus.className = 'folder-status-badge error';
        appState.folderExists = false;
    }
}

// Trigger CLIP Analysis (Background Threading)
async function startAnalysis() {
    if (!appState.folderExists) {
        alert('Please enter a valid folder path first.');
        return;
    }

    // Reset Progress View
    els.progressTitle.textContent = "Launching CLIP Analysis...";
    els.progressGpu.textContent = "-";
    els.progressCache.textContent = "-";
    els.progressFiles.textContent = "-";
    els.progressFill.style.width = "0%";
    els.progressPercent.textContent = "0%";
    els.progressMsg.textContent = "Sending configuration to server...";

    els.loadingArea.classList.remove('hidden');
    els.resultsArea.classList.add('hidden');
    els.btnAnalyze.disabled = true;

    const payload = {
        folder: els.folderPath.value.trim(),
        pos_prompts: els.posPrompts.value.trim(),
        neg_prompts: els.negPrompts.value.trim(),
        phone_width: parseInt(els.phoneWidth.value),
        phone_height: parseInt(els.phoneHeight.value),
        laptop_width: parseInt(els.laptopWidth.value),
        laptop_height: parseInt(els.laptopHeight.value)
    };

    try {
        const response = await fetch('/api/rank', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        const data = await response.json();
        if (data.error) {
            alert(`Error starting analysis: ${data.error}`);
            els.loadingArea.classList.add('hidden');
            els.btnAnalyze.disabled = false;
            return;
        }

        // Start polling progress state
        if (appState.progressPollInterval) clearInterval(appState.progressPollInterval);
        appState.progressPollInterval = setInterval(pollProgress, 500);
    } catch (e) {
        alert(`Analysis failed: ${e}`);
        els.loadingArea.classList.add('hidden');
        els.btnAnalyze.disabled = false;
    }
}

// Poll Progress Endpoint
async function pollProgress() {
    try {
        const res = await fetch('/api/progress');
        const state = await res.json();

        // 1. Update Hardware/Status Stats Grid
        els.progressGpu.textContent = state.gpu_available ? state.gpu_name : "CPU ONLY";
        els.progressGpu.title = els.progressGpu.textContent;
        els.progressCache.textContent = state.cache_status;
        els.progressCache.title = state.cache_status;

        if (state.total > 0) {
            els.progressFiles.textContent = `${state.current} / ${state.total}`;
        } else {
            els.progressFiles.textContent = state.status === 'processing' ? 'Calculating...' : 'Idle';
        }

        // 2. Update Progress Bar
        let pct = 0;
        if (state.total > 0) {
            pct = Math.round((state.current / state.total) * 100);
        } else if (state.status === 'completed') {
            pct = 100;
        }
        els.progressFill.style.width = `${pct}%`;
        els.progressPercent.textContent = `${pct}%`;

        // 3. Update Message Text
        els.progressTitle.textContent = state.status === 'processing' ? "Analyzing Images..." : "Finalizing results...";
        els.progressMsg.textContent = state.message || "Working...";

        // 4. Handle Terminal Conditions
        if (state.status === 'completed') {
            clearInterval(appState.progressPollInterval);
            appState.progressPollInterval = null;

            // Load results into State
            appState.results = state.results;
            
            // Reset Selections
            appState.selections.phone.clear();
            appState.selections.laptop.clear();
            
            // Auto-select Top K
            const topK = parseInt(els.topK.value) || 10;
            state.results.phone.slice(0, topK).forEach(item => {
                appState.selections.phone.set(item.path, item.crop_type);
            });
            state.results.laptop.slice(0, topK).forEach(item => {
                appState.selections.laptop.set(item.path, item.crop_type);
            });

            // Display Results
            els.loadingArea.classList.add('hidden');
            els.resultsArea.classList.remove('hidden');
            els.btnAnalyze.disabled = false;
            appState.currentPage = 1;
            
            renderResults();
            updateSelectCount();
        } else if (state.status === 'error') {
            clearInterval(appState.progressPollInterval);
            appState.progressPollInterval = null;
            
            alert(`CLIP Analysis Error: ${state.error_msg}`);
            els.loadingArea.classList.add('hidden');
            els.btnAnalyze.disabled = false;
        }
    } catch (e) {
        console.error('Error polling progress:', e);
    }
}

// Render Preview Grid
function renderResults() {
    const tab = appState.activeTab;
    const items = appState.results[tab];
    els.previewsGrid.className = `grid-previews ${tab}-grid`;
    
    const totalItems = items.length;
    const totalPages = Math.ceil(totalItems / appState.pageSize) || 1;
    
    if (appState.currentPage > totalPages) appState.currentPage = totalPages;
    
    const startIdx = (appState.currentPage - 1) * appState.pageSize;
    const endIdx = Math.min(startIdx + appState.pageSize, totalItems);
    const paginatedItems = items.slice(startIdx, endIdx);

    els.paginationSummary.textContent = totalItems > 0 
        ? `Showing ${startIdx + 1} - ${endIdx} of ${totalItems} results`
        : `No items found`;
    els.pageNum.textContent = `Page ${appState.currentPage} of ${totalPages}`;
    els.btnPrev.disabled = appState.currentPage === 1;
    els.btnNext.disabled = appState.currentPage === totalPages || totalItems === 0;

    els.previewsGrid.innerHTML = '';

    const w = tab === 'phone' ? els.phoneWidth.value : els.laptopWidth.value;
    const h = tab === 'phone' ? els.phoneHeight.value : els.laptopHeight.value;

    paginatedItems.forEach((item) => {
        const isSelected = appState.selections[tab].has(item.path);
        const currentCrop = isSelected 
            ? appState.selections[tab].get(item.path) 
            : item.crop_type;

        const card = document.createElement('div');
        card.className = `preview-card ${tab}-card ${isSelected ? 'selected' : ''}`;
        
        const previewUrl = `/api/image?path=${encodeURIComponent(item.path)}&crop=${currentCrop}&device=${tab}&w=${w}&h=${h}`;
        
        card.innerHTML = `
            <div class="thumbnail-wrapper" style="aspect-ratio: ${w} / ${h};">
                <div class="score-badge">${item.score.toFixed(3)}</div>
                <img src="${previewUrl}" alt="${item.name}" loading="lazy">
            </div>
            <div class="card-details">
                <div class="img-name" title="${item.name}">${item.name}</div>
                
                <div class="crop-control">
                    <label>Crop Selection</label>
                    <div class="crop-buttons">
                        ${item.all_crops.map(crop => `
                            <button class="crop-btn ${currentCrop === crop ? 'active' : ''}" data-crop="${crop}">
                                ${crop}
                            </button>
                        `).join('')}
                    </div>
                </div>

                <div class="card-select-row">
                    <label class="checkbox-container">
                        <input type="checkbox" class="cb-select" ${isSelected ? 'checked' : ''}>
                        Select Wallpaper
                    </label>
                </div>
            </div>
        `;

        // Selection Listener
        const checkbox = card.querySelector('.cb-select');
        checkbox.addEventListener('change', (e) => {
            if (e.target.checked) {
                appState.selections[tab].set(item.path, currentCrop);
                card.classList.add('selected');
            } else {
                appState.selections[tab].delete(item.path);
                card.classList.remove('selected');
            }
            updateSelectCount();
        });

        // Crop Buttons Listener
        const cropBtns = card.querySelectorAll('.crop-btn');
        cropBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const newCrop = e.target.dataset.crop;
                cropBtns.forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                
                const img = card.querySelector('img');
                img.src = `/api/image?path=${encodeURIComponent(item.path)}&crop=${newCrop}&device=${tab}&w=${w}&h=${h}`;

                if (checkbox.checked) {
                    appState.selections[tab].set(item.path, newCrop);
                }
            });
        });

        els.previewsGrid.appendChild(card);
    });
}

// Update selections counter
function updateSelectCount() {
    const count = appState.selections.phone.size + appState.selections.laptop.size;
    els.selectCount.textContent = count;
}

// Save crops to folder
async function saveWallpapers() {
    const list = [];
    
    // Process Phone Selections
    let i = 1;
    appState.selections.phone.forEach((cropType, path) => {
        list.push({
            path: path,
            device: 'phone',
            crop_type: cropType,
            w: parseInt(els.phoneWidth.value),
            h: parseInt(els.phoneHeight.value),
            index: i++
        });
    });

    // Process Laptop Selections
    i = 1;
    appState.selections.laptop.forEach((cropType, path) => {
        list.push({
            path: path,
            device: 'laptop',
            crop_type: cropType,
            w: parseInt(els.laptopWidth.value),
            h: parseInt(els.laptopHeight.value),
            index: i++
        });
    });

    if (list.length === 0) {
        alert('Please select at least one wallpaper to save.');
        return;
    }

    const payload = {
        output_dir: els.outputPath.value.trim(),
        selections: list
    };

    els.btnSave.disabled = true;
    els.btnSave.textContent = 'Saving Wallpapers...';

    try {
        const response = await fetch('/api/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await response.json();
        
        alert(data.message || 'Saved successfully!');
    } catch (e) {
        alert(`Failed to save: ${e}`);
    } finally {
        els.btnSave.disabled = false;
        updateSelectCount();
    }
}
