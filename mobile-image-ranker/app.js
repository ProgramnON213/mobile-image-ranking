// --------------------------------------------------
// Application State
// --------------------------------------------------
let allFiles = [];      // Raw list of file objects
let filterFiles = [];   // List of files to swipe (unrated, or restored session)
let ratings = {};       // UniqueKey -> 'keep' | 'discard' | 'pending'
let currentIndex = 0;   // Current active card index in filterFiles
let undoStack = [];     // Stack of Rated Item IDs in this session
let activeFolderName = "Import Session";

// Swipe parameters
const SWIPE_THRESHOLD = 120; // px
const ROTATION_FACTOR = 0.1; // degrees per px

// Zoom & Pan state for inspection modal
let zoomState = {
    isZoomed: false,
    scale: 1,
    baseScale: 1,
    startX: 0,
    startY: 0,
    currentX: 0,
    currentY: 0,
    translateX: 0,
    translateY: 0,
    initialTouchDist: 0,
    lastTapTime: 0
};

// --------------------------------------------------
// DOM Elements
// --------------------------------------------------
const screens = {
    welcome: document.getElementById('welcome-screen'),
    swiper: document.getElementById('swiper-screen')
};

const folderInput = document.getElementById('folder-input');
const filesInput = document.getElementById('files-input');
const cardDeck = document.getElementById('card-deck');
const activeFolderLabel = document.getElementById('active-folder-name');
const restoreBanner = document.getElementById('restore-banner');

// Progress Elements
const progressBarFill = document.getElementById('progress-bar-fill');
const progressCounts = document.getElementById('progress-counts');
const progressPercent = document.getElementById('progress-percent');

// Swipe Indicators
const badges = {
    discard: document.getElementById('swipe-indicator-discard'),
    keep: document.getElementById('swipe-indicator-keep'),
    pending: document.getElementById('swipe-indicator-pending')
};

// Action Buttons
const btnUndo = document.getElementById('btn-action-undo');
const btnDiscard = document.getElementById('btn-action-discard');
const btnPending = document.getElementById('btn-action-pending');
const btnKeep = document.getElementById('btn-action-keep');
const btnBack = document.getElementById('btn-back');
const btnStats = document.getElementById('btn-stats');

// Stats Overlay
const statsOverlay = document.getElementById('stats-overlay');
const btnCloseStats = document.getElementById('btn-close-stats');
const btnResetSession = document.getElementById('btn-reset-session');
const btnExportJson = document.getElementById('btn-export-json');
const btnExportCsv = document.getElementById('btn-export-csv');
const btnShareResults = document.getElementById('btn-share-results');

const statTotal = document.getElementById('stat-total');
const statRated = document.getElementById('stat-rated');
const statKeeps = document.getElementById('stat-keeps');
const statDiscards = document.getElementById('stat-discards');
const statPendings = document.getElementById('stat-pendings');

// Zoom Overlay
const zoomOverlay = document.getElementById('zoom-overlay');
const zoomImage = document.getElementById('zoom-image');
const zoomVideo = document.getElementById('zoom-video');
const zoomViewport = document.getElementById('zoom-viewport');
const zoomImgName = document.getElementById('zoom-image-name');
const zoomImgDetails = document.getElementById('zoom-image-details');
const btnCloseZoom = document.getElementById('btn-close-zoom');

// --------------------------------------------------
// Initialization & Session Checking
// --------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
    // Check if there is already a saved session in localStorage
    checkSavedSession();
    setupEventListeners();
    registerServiceWorker();
});

function registerServiceWorker() {
    if ('serviceWorker' in navigator) {
        window.addEventListener('load', () => {
            navigator.serviceWorker.register('./sw.js')
                .then((reg) => console.log('[Service Worker] Registered successfully:', reg.scope))
                .catch((err) => console.log('[Service Worker] Registration failed:', err));
        });
    }
}

function checkSavedSession() {
    ratings = JSON.parse(localStorage.getItem('ranker_ratings') || '{}');
    const ratedCount = Object.keys(ratings).length;
    
    if (ratedCount > 0) {
        restoreBanner.classList.remove('hidden');
    } else {
        restoreBanner.classList.add('hidden');
    }
}

// --------------------------------------------------
// File Parsing & Image Processing
// --------------------------------------------------
function setupEventListeners() {
    folderInput.addEventListener('change', (e) => handleFileSelection(e.target.files, true));
    filesInput.addEventListener('change', (e) => handleFileSelection(e.target.files, false));

    // Navigations
    btnBack.addEventListener('click', goBackToWelcome);
    btnStats.addEventListener('click', () => toggleOverlay(statsOverlay, true));
    btnCloseStats.addEventListener('click', () => toggleOverlay(statsOverlay, false));
    statsOverlay.addEventListener('click', (e) => {
        if (e.target === statsOverlay) toggleOverlay(statsOverlay, false);
    });

    // Reset Progress
    btnResetSession.addEventListener('click', resetSession);

    // Export Triggers
    btnExportJson.addEventListener('click', exportJSON);
    btnExportCsv.addEventListener('click', exportCSV);
    btnShareResults.addEventListener('click', shareResults);

    // Bottom Bar Buttons
    btnKeep.addEventListener('click', () => animateButtonSwipe('keep'));
    btnDiscard.addEventListener('click', () => animateButtonSwipe('discard'));
    btnPending.addEventListener('click', () => animateButtonSwipe('pending'));
    btnUndo.addEventListener('click', triggerUndo);

    // Zoom inspection close
    btnCloseZoom.addEventListener('click', closeZoomModal);
}

function handleFileSelection(fileList, isFolder) {
    if (!fileList || fileList.length === 0) return;

    allFiles = [];
    filterFiles = [];
    currentIndex = 0;
    undoStack = [];
    
    // Determine folder name
    if (isFolder && fileList[0].webkitRelativePath) {
        const parts = fileList[0].webkitRelativePath.split('/');
        activeFolderName = parts.length > 1 ? parts[0] : "Imported Folder";
    } else {
        activeFolderName = "Selected Files";
    }
    
    activeFolderLabel.textContent = activeFolderName;

    // Load ratings from storage
    ratings = JSON.parse(localStorage.getItem('ranker_ratings') || '{}');

    // Show a loading/placeholder card in the DOM
    cardDeck.innerHTML = `
        <div class="card placeholder-card">
            <div class="spinner"></div>
            <p>Scanning files...</p>
        </div>
    `;
    
    switchScreen('swiper');

    // Process files asynchronously
    setTimeout(() => {
        const mediaExtensions = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg', 'mp4', 'webm', 'ogg', 'mov', 'm4v'];
        
        for (let i = 0; i < fileList.length; i++) {
            const file = fileList[i];
            const ext = file.name.split('.').pop().toLowerCase();
            const isVideo = ['mp4', 'webm', 'ogg', 'mov', 'm4v'].includes(ext) || file.type.startsWith('video/');
            
            if (mediaExtensions.includes(ext) || file.type.startsWith('image/') || isVideo) {
                // Generate a key using filename + size as a unique footprint
                const relativePath = file.webkitRelativePath || file.name;
                const fileKey = `${relativePath}_${file.size}`;
                
                const fileItem = {
                    file: file,
                    name: file.name,
                    path: relativePath,
                    key: fileKey,
                    size: file.size,
                    formattedSize: formatBytes(file.size),
                    dimensions: 'Loading...',
                    isVideo: isVideo
                };
                
                allFiles.push(fileItem);
                
                // Keep file in swiping list if it hasn't been rated yet
                if (!ratings[fileKey]) {
                    filterFiles.push(fileItem);
                }
            }
        }

        if (allFiles.length === 0) {
            alert("No images found in the selected folder/files.");
            goBackToWelcome();
            return;
        }

        updateProgress();
        renderCards();
    }, 100);
}

// --------------------------------------------------
// Card Rendering & Touch Interaction Engine
// --------------------------------------------------
function renderCards() {
    cardDeck.innerHTML = '';
    
    if (currentIndex >= filterFiles.length) {
        renderDeckCompleted();
        return;
    }

    // Aggressive Memory Management:
    // Revoke object URLs for cards outside our active window to prevent mobile out-of-memory crashes.
    // We keep a wider window (-10 to +5) to allow 10 historical "Undos" and 5 stacked visual cards.
    filterFiles.forEach((fileItem, idx) => {
        if (idx < currentIndex - 10 || idx > currentIndex + 5) {
            if (fileItem.objectUrl) {
                URL.revokeObjectURL(fileItem.objectUrl);
                fileItem.objectUrl = null; // Mark for recreation if user undoes back to it
            }
        }
    });

    // Render up to 5 cards for a deep visual stack
    const cardsToRender = filterFiles.slice(currentIndex, currentIndex + 5);

    cardsToRender.forEach((fileItem, offsetIndex) => {
        const isTopCard = offsetIndex === 0;
        const card = document.createElement('div');
        card.className = 'card';
        card.dataset.key = fileItem.key;
        card.dataset.index = currentIndex + offsetIndex;
        
        // Lazy load the Object URL only for visible cards to prevent browser out-of-memory crashes
        let imgUrl = "";
        if (!fileItem.objectUrl) {
            fileItem.objectUrl = URL.createObjectURL(fileItem.file);
        }
        imgUrl = fileItem.objectUrl;

        // Fetch image/video dimensions asynchronously if not cached and not already loading
        if (fileItem.dimensions === 'Loading...' && !fileItem.isDimensionLoading) {
            fileItem.isDimensionLoading = true;
            if (fileItem.isVideo) {
                const tempVid = document.createElement('video');
                tempVid.onloadedmetadata = function() {
                    fileItem.dimensions = `${this.videoWidth}×${this.videoHeight}`;
                    fileItem.isDimensionLoading = false;
                    const dimEl = document.querySelector(`.card[data-key="${fileItem.key}"] .dim-val`);
                    if (dimEl) dimEl.textContent = fileItem.dimensions;
                    if (zoomOverlay.classList.contains('active') && zoomVideo.src === imgUrl) {
                        zoomImgDetails.textContent = `${fileItem.formattedSize} • ${fileItem.dimensions}`;
                    }
                };
                tempVid.src = imgUrl;
            } else {
                const tempImg = new Image();
                tempImg.onload = function() {
                    fileItem.dimensions = `${this.width}×${this.height}`;
                    fileItem.isDimensionLoading = false;
                    const dimEl = document.querySelector(`.card[data-key="${fileItem.key}"] .dim-val`);
                    if (dimEl) dimEl.textContent = fileItem.dimensions;
                    if (zoomOverlay.classList.contains('active') && zoomImage.src === imgUrl) {
                        zoomImgDetails.textContent = `${fileItem.formattedSize} • ${fileItem.dimensions}`;
                    }
                };
                tempImg.src = imgUrl;
            }
        }


        let mediaHTML = '';
        if (fileItem.isVideo) {
            mediaHTML = `<video src="${imgUrl}" autoplay loop muted playsinline disablePictureInPicture draggable="false"></video>`;
        } else {
            mediaHTML = `<img src="${imgUrl}" alt="${fileItem.name}" draggable="false">`;
        }

        card.innerHTML = `
            <div class="card-media">
                <span class="zoom-hint">🔍 Zoom</span>
                ${mediaHTML}
            </div>
            <div class="card-details">
                <span class="card-title" title="${fileItem.name}">${fileItem.name}</span>
                <div class="card-meta">
                    <span class="meta-item">📦 ${fileItem.formattedSize}</span>
                    <span class="meta-item">📐 <span class="dim-val">${fileItem.dimensions}</span></span>
                </div>
            </div>
        `;

        if (isTopCard) {
            setupDragAndSwipe(card);
            // Setup click to Zoom details
            const mediaContainer = card.querySelector('.card-media');
            mediaContainer.addEventListener('click', (e) => {
                // If the user didn't swipe/drag, treat as tap to inspect
                openZoomModal(fileItem);
            });
        }

        // Add card to back of deck
        cardDeck.appendChild(card);
    });

    // Toggle Undo button availability
    if (undoStack.length > 0) {
        btnUndo.classList.remove('disabled');
    } else {
        btnUndo.classList.add('disabled');
    }
}

function renderDeckCompleted() {
    cardDeck.innerHTML = `
        <div class="card placeholder-card">
            <h2 style="font-size: 24px; color: var(--color-keep); margin-bottom: 8px;">🎉 Deck Sorted!</h2>
            <p style="padding: 0 20px;">All images have been ranked.</p>
            <button class="btn btn-primary" onclick="toggleOverlay(statsOverlay, true)" style="margin-top: 16px;">Export Results</button>
        </div>
    `;
    btnUndo.classList.add('disabled');
}

// --------------------------------------------------
// Touch and Swipe Gesture Physics Handler
// --------------------------------------------------
function setupDragAndSwipe(card) {
    let startX = 0;
    let startY = 0;
    let currentX = 0;
    let currentY = 0;
    let isDragging = false;

    // Remove old listeners to be clean
    card.addEventListener('touchstart', onTouchStart, { passive: true });
    card.addEventListener('touchmove', onTouchMove, { passive: false });
    card.addEventListener('touchend', onTouchEnd);

    card.addEventListener('mousedown', onMouseDown);

    function onTouchStart(e) {
        if (e.touches.length > 1) return; // Ignore multitouch
        startX = e.touches[0].clientX;
        startY = e.touches[0].clientY;
        isDragging = true;
        card.style.transition = 'none';
    }

    function onTouchMove(e) {
        if (!isDragging) return;
        
        currentX = e.touches[0].clientX - startX;
        currentY = e.touches[0].clientY - startY;

        // Prevent body bounce scroll on Android while swiping
        if (Math.abs(currentX) > 10 || Math.abs(currentY) > 10) {
            if (e.cancelable) e.preventDefault();
        }

        const rotation = currentX * ROTATION_FACTOR;
        card.style.transform = `translate3d(${currentX}px, ${currentY}px, 0) rotate(${rotation}deg)`;

        // Visual badges highlighting swipe intent
        updateSwipeBadges(currentX, currentY);
    }

    function onTouchEnd() {
        if (!isDragging) return;
        isDragging = false;

        card.style.transition = 'transform 0.25s cubic-bezier(0.175, 0.885, 0.32, 1.1), opacity 0.2s ease';
        
        // Hide badges
        resetSwipeBadges();

        // Check if swipe triggered rating
        if (currentX > SWIPE_THRESHOLD) {
            swipeCard(card, 'keep');
        } else if (currentX < -SWIPE_THRESHOLD) {
            swipeCard(card, 'discard');
        } else if (currentY < -SWIPE_THRESHOLD) {
            swipeCard(card, 'pending');
        } else {
            // Snap back
            card.style.transform = 'translate3d(0, 0, 0) rotate(0deg)';
        }
        
        startX = startY = currentX = currentY = 0;
    }

    // Mouse handlers (For testing on PC browsers)
    function onMouseDown(e) {
        if (e.target.closest('.zoom-hint') || e.target.closest('.card-details')) return;
        startX = e.clientX;
        startY = e.clientY;
        isDragging = true;
        card.style.transition = 'none';

        document.addEventListener('mousemove', onMouseMove);
        document.addEventListener('mouseup', onMouseUp);
    }

    function onMouseMove(e) {
        if (!isDragging) return;
        currentX = e.clientX - startX;
        currentY = e.clientY - startY;

        const rotation = currentX * ROTATION_FACTOR;
        card.style.transform = `translate3d(${currentX}px, ${currentY}px, 0) rotate(${rotation}deg)`;
        
        updateSwipeBadges(currentX, currentY);
    }

    function onMouseUp() {
        if (!isDragging) return;
        isDragging = false;

        document.removeEventListener('mousemove', onMouseMove);
        document.removeEventListener('mouseup', onMouseUp);

        card.style.transition = 'transform 0.25s cubic-bezier(0.175, 0.885, 0.32, 1.1), opacity 0.2s ease';
        resetSwipeBadges();

        if (currentX > SWIPE_THRESHOLD) {
            swipeCard(card, 'keep');
        } else if (currentX < -SWIPE_THRESHOLD) {
            swipeCard(card, 'discard');
        } else if (currentY < -SWIPE_THRESHOLD) {
            swipeCard(card, 'pending');
        } else {
            card.style.transform = 'translate3d(0, 0, 0) rotate(0deg)';
        }

        startX = startY = currentX = currentY = 0;
    }
}

function updateSwipeBadges(x, y) {
    // Reset opacities
    badges.keep.style.opacity = 0;
    badges.discard.style.opacity = 0;
    badges.pending.style.opacity = 0;

    // Check which direction is stronger
    if (Math.abs(y) > Math.abs(x) && y < -50) {
        // Dragging up (Pending)
        const alpha = Math.min(Math.abs(y) / SWIPE_THRESHOLD, 1);
        badges.pending.style.opacity = alpha;
        badges.pending.style.transform = `translateX(-50%) scale(${0.8 + alpha * 0.2})`;
    } else {
        // Dragging left/right
        if (x > 50) {
            const alpha = Math.min(x / SWIPE_THRESHOLD, 1);
            badges.keep.style.opacity = alpha;
            badges.keep.style.transform = `rotate(15deg) scale(${0.8 + alpha * 0.2})`;
        } else if (x < -50) {
            const alpha = Math.min(Math.abs(x) / SWIPE_THRESHOLD, 1);
            badges.discard.style.opacity = alpha;
            badges.discard.style.transform = `rotate(-15deg) scale(${0.8 + alpha * 0.2})`;
        }
    }
}

function resetSwipeBadges() {
    badges.keep.style.opacity = 0;
    badges.discard.style.opacity = 0;
    badges.pending.style.opacity = 0;
}

function swipeCard(card, rating) {
    const screenWidth = window.innerWidth;
    const screenHeight = window.innerHeight;
    let destinationX = 0;
    let destinationY = 0;
    let rotation = 0;

    if (rating === 'keep') {
        destinationX = screenWidth + 200;
        rotation = 45;
    } else if (rating === 'discard') {
        destinationX = -screenWidth - 200;
        rotation = -45;
    } else if (rating === 'pending') {
        destinationY = -screenHeight - 200;
    }

    card.style.transform = `translate3d(${destinationX}px, ${destinationY}px, 0) rotate(${rotation}deg)`;
    card.style.opacity = 0;

    // Log rating and transition to next card
    setTimeout(() => {
        saveFileRating(card.dataset.key, rating);
        currentIndex++;
        updateProgress();
        renderCards();
    }, 200);
}

function animateButtonSwipe(rating) {
    const cards = cardDeck.querySelectorAll('.card');
    if (cards.length === 0 || cards[0].classList.contains('placeholder-card')) return;
    
    const topCard = cards[0];
    topCard.style.transition = 'transform 0.3s ease-in, opacity 0.2s ease';
    swipeCard(topCard, rating);
}

// --------------------------------------------------
// State Persistence & Resume Logic
// --------------------------------------------------
function saveFileRating(key, rating) {
    ratings[key] = rating;
    localStorage.setItem('ranker_ratings', JSON.stringify(ratings));
    
    // Add to session undo stack
    undoStack.push({ key: key, rating: rating });
}

function triggerUndo() {
    if (undoStack.length === 0) return;
    
    const lastRated = undoStack.pop();
    delete ratings[lastRated.key];
    localStorage.setItem('ranker_ratings', JSON.stringify(ratings));

    // Rewind index
    currentIndex--;
    updateProgress();
    renderCards();
}

function updateProgress() {
    const totalCount = allFiles.length;
    const unratedCount = filterFiles.length;
    const ratedCount = totalCount - unratedCount + currentIndex;
    
    let percent = 0;
    if (totalCount > 0) {
        percent = Math.round((ratedCount / totalCount) * 100);
    }

    progressBarFill.style.width = `${percent}%`;
    progressCounts.textContent = `${ratedCount} / ${totalCount} images sorted`;
    progressPercent.textContent = `(${percent}%)`;

    // Also update statistics overlay numbers
    statTotal.textContent = totalCount;
    statRated.textContent = ratedCount;

    let keeps = 0, discards = 0, pendings = 0;
    Object.values(ratings).forEach(v => {
        if (v === 'keep') keeps++;
        else if (v === 'discard') discards++;
        else if (v === 'pending') pendings++;
    });

    statKeeps.textContent = keeps;
    statDiscards.textContent = discards;
    statPendings.textContent = pendings;
}

function resetSession() {
    if (confirm("⚠️ This will delete ALL ratings saved on this device. Are you sure?")) {
        ratings = {};
        localStorage.removeItem('ranker_ratings');
        undoStack = [];
        currentIndex = 0;
        
        // Re-process imported list
        filterFiles = [...allFiles];
        
        toggleOverlay(statsOverlay, false);
        updateProgress();
        renderCards();
        checkSavedSession();
    }
}

// --------------------------------------------------
// Mobile Zoom & Pan Modal View Engine
// --------------------------------------------------
function openZoomModal(fileItem) {
    // Prevent double triggers
    if (zoomOverlay.classList.contains('active')) return;
    
    zoomImgName.textContent = fileItem.name;
    zoomImgDetails.textContent = `${fileItem.formattedSize} • ${fileItem.dimensions}`;
    
    if (fileItem.isVideo) {
        zoomImage.classList.add('hidden');
        zoomVideo.classList.remove('hidden');
        zoomVideo.src = fileItem.objectUrl;
    } else {
        zoomVideo.classList.add('hidden');
        zoomImage.classList.remove('hidden');
        zoomImage.src = fileItem.objectUrl;
    }

    // Reset zoom transformation settings
    zoomState = {
        isZoomed: false,
        scale: 1,
        baseScale: 1,
        startX: 0,
        startY: 0,
        currentX: 0,
        currentY: 0,
        translateX: 0,
        translateY: 0,
        initialTouchDist: 0,
        lastTapTime: 0
    };
    
    applyZoomTransformations();
    zoomOverlay.classList.add('active');

    // Register active zoom listeners
    zoomViewport.addEventListener('touchstart', handleZoomTouchStart, { passive: false });
    zoomViewport.addEventListener('touchmove', handleZoomTouchMove, { passive: false });
    zoomViewport.addEventListener('touchend', handleZoomTouchEnd);
}

function closeZoomModal() {
    zoomOverlay.classList.remove('active');
    // Clear image src to free memory on mobile
    zoomImage.src = "";
    zoomVideo.src = "";
    
    // Deregister listeners to preserve cycles
    zoomViewport.removeEventListener('touchstart', handleZoomTouchStart);
    zoomViewport.removeEventListener('touchmove', handleZoomTouchMove);
    zoomViewport.removeEventListener('touchend', handleZoomTouchEnd);
}

function applyZoomTransformations() {
    const activeMedia = zoomImage.classList.contains('hidden') ? zoomVideo : zoomImage;
    activeMedia.style.transform = `translate3d(${zoomState.translateX}px, ${zoomState.translateY}px, 0) scale(${zoomState.scale})`;
}

// Mobile Pinch-to-Zoom, Panning, and Double Tap triggers
function handleZoomTouchStart(e) {
    e.preventDefault(); // Stop default scroll/scale behaviors

    if (e.touches.length === 1) {
        // Drag panning start
        zoomState.startX = e.touches[0].clientX - zoomState.translateX;
        zoomState.startY = e.touches[0].clientY - zoomState.translateY;
    } else if (e.touches.length === 2) {
        // Pinch start
        zoomState.initialTouchDist = getTouchDistance(e.touches[0], e.touches[1]);
        zoomState.baseScale = zoomState.scale;
    }
}

function handleZoomTouchMove(e) {
    e.preventDefault();

    if (e.touches.length === 1) {
        // Only pan if we are actually zoomed in
        if (zoomState.scale > 1) {
            zoomState.translateX = e.touches[0].clientX - zoomState.startX;
            zoomState.translateY = e.touches[0].clientY - zoomState.startY;
            
            // Constrain bounding boxes (rough limits)
            const limitX = (zoomState.scale - 1) * window.innerWidth / 2;
            const limitY = (zoomState.scale - 1) * window.innerHeight / 2;
            zoomState.translateX = Math.max(-limitX, Math.min(limitX, zoomState.translateX));
            zoomState.translateY = Math.max(-limitY, Math.min(limitY, zoomState.translateY));
            
            applyZoomTransformations();
        }
    } else if (e.touches.length === 2) {
        // Zoom pinch drag
        const dist = getTouchDistance(e.touches[0], e.touches[1]);
        const factor = dist / zoomState.initialTouchDist;
        zoomState.scale = Math.max(1, Math.min(5, zoomState.baseScale * factor));
        
        if (zoomState.scale === 1) {
            zoomState.translateX = 0;
            zoomState.translateY = 0;
        }
        applyZoomTransformations();
    }
}

function handleZoomTouchEnd(e) {
    // Handle double-tap to zoom
    if (e.touches.length === 0) {
        const now = new Date().getTime();
        const delta = now - zoomState.lastTapTime;
        
        if (delta < 300 && delta > 0) {
            // Trigger zoom double tap toggle
            if (zoomState.scale > 1) {
                // Reset
                zoomState.scale = 1;
                zoomState.translateX = 0;
                zoomState.translateY = 0;
            } else {
                // Zoom to 2.5x
                zoomState.scale = 2.5;
            }
            applyZoomTransformations();
        }
        zoomState.lastTapTime = now;
    }
}

function getTouchDistance(t1, t2) {
    const dx = t1.clientX - t2.clientX;
    const dy = t1.clientY - t2.clientY;
    return Math.sqrt(dx * dx + dy * dy);
}

// --------------------------------------------------
// Exports & Share Sheets Formatting
// --------------------------------------------------
function getRatingData() {
    const result = [];
    Object.keys(ratings).forEach(key => {
        // Split key to extract original name
        const lastUnderscore = key.lastIndexOf('_');
        const originalPath = lastUnderscore !== -1 ? key.substring(0, lastUnderscore) : key;
        
        result.push({
            file: originalPath,
            rating: ratings[key]
        });
    });
    return result;
}

function exportJSON() {
    const data = getRatingData();
    if (data.length === 0) {
        alert("No rating data available to export.");
        return;
    }

    const jsonString = JSON.stringify(data, null, 2);
    const blob = new Blob([jsonString], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement("a");
    a.href = url;
    a.download = `image_rankings_${activeFolderName.replace(/\s+/g, '_')}.json`;
    a.click();
    URL.revokeObjectURL(url);
}

function exportCSV() {
    const data = getRatingData();
    if (data.length === 0) {
        alert("No rating data available to export.");
        return;
    }

    let csvContent = "file,rating\n";
    data.forEach(row => {
        // Escape quotes just in case
        const escapedFile = row.file.replace(/"/g, '""');
        csvContent += `"${escapedFile}","${row.rating}"\n`;
    });

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement("a");
    a.href = url;
    a.download = `image_rankings_${activeFolderName.replace(/\s+/g, '_')}.csv`;
    a.click();
    URL.revokeObjectURL(url);
}

function shareResults() {
    const data = getRatingData();
    if (data.length === 0) {
        alert("No rating data available to share.");
        return;
    }

    const summaryText = `Ranks sorted: Total: ${allFiles.length} | Kept: ${statKeeps.textContent} | Discarded: ${statDiscards.textContent} | Pending: ${statPendings.textContent}`;
    const csvContent = getRatingData().map(r => `${r.file},${r.rating}`).join('\n');
    
    if (navigator.share) {
        navigator.share({
            title: `Image Ranker Results: ${activeFolderName}`,
            text: `${summaryText}\n\nMapping:\n${csvContent}`,
        }).catch(err => {
            console.log("Sharing failed: ", err);
        });
    } else {
        // Fallback: Copy to Clipboard
        navigator.clipboard.writeText(`${summaryText}\n\n${csvContent}`).then(() => {
            alert("Results summary copied to clipboard! (Share API not supported on this browser)");
        }).catch(err => {
            alert("Could not copy automatically. Export as JSON/CSV instead.");
        });
    }
}

// --------------------------------------------------
// Page Switch Navigation Helpers
// --------------------------------------------------
function switchScreen(screenName) {
    Object.keys(screens).forEach(key => {
        if (key === screenName) {
            screens[key].classList.add('active');
        } else {
            screens[key].classList.remove('active');
        }
    });
}

function goBackToWelcome() {
    // Revoke object URLs to free memory
    allFiles.forEach(f => {
        if (f.objectUrl) {
            URL.revokeObjectURL(f.objectUrl);
            delete f.objectUrl;
        }
    });
    
    switchScreen('welcome');
    checkSavedSession();
}

function toggleOverlay(overlayEl, show) {
    if (show) {
        overlayEl.classList.add('active');
    } else {
        overlayEl.classList.remove('active');
    }
}

function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}
