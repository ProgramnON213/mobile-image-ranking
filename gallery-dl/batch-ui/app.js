/**
 * Batch Image Cleaner v7 Pro
 * Responsive, hardware-accelerated batch image inspector and cleaner
 */

// Application State
const state = {
  rootFolder: "",
  batches: [],
  filteredBatches: [],
  activeBatch: null,
  images: [],
  markedDeletes: new Set(),
  
  // Lightbox Viewport State
  lb: {
    isOpen: false,
    index: 0,
    scale: 1,
    minScale: 0.2,
    maxScale: 15,
    panX: 0,
    panY: 0,
    isPanning: false,
    startX: 0,
    startY: 0
  }
};

// DOM Element References
const elements = {
  btnBrowseFolder: document.getElementById("btnBrowseFolder"),
  currentFolderPath: document.getElementById("currentFolderPath"),
  batchCountBadge: document.getElementById("batchCountBadge"),
  imageCountBadge: document.getElementById("imageCountBadge"),
  searchBatchesInput: document.getElementById("searchBatchesInput"),
  clearSearchBtn: document.getElementById("clearSearchBtn"),
  filteredBatchCount: document.getElementById("filteredBatchCount"),
  batchList: document.getElementById("batchList"),
  
  // Workspace & Toolbar
  actionBar: document.getElementById("actionBar"),
  activeBatchTitle: document.getElementById("activeBatchTitle"),
  activeBatchMeta: document.getElementById("activeBatchMeta"),
  batchTools: document.getElementById("batchTools"),
  gridContainer: document.getElementById("gridContainer"),
  gridZoomSlider: document.getElementById("gridZoomSlider"),
  btnSelectAll: document.getElementById("btnSelectAll"),
  btnSelectNone: document.getElementById("btnSelectNone"),
  btnInvert: document.getElementById("btnInvert"),
  btnKeepLargestSize: document.getElementById("btnKeepLargestSize"),
  btnKeepHighestRes: document.getElementById("btnKeepHighestRes"),
  btnKeepFirst: document.getElementById("btnKeepFirst"),
  btnDeleteSelected: document.getElementById("btnDeleteSelected"),
  deleteBtnLabel: document.getElementById("deleteBtnLabel"),
  
  // Lightbox
  lightbox: document.getElementById("lightbox"),
  lbViewport: document.getElementById("lbViewport"),
  lbImage: document.getElementById("lbImage"),
  lbIndexBadge: document.getElementById("lbIndexBadge"),
  lbFilename: document.getElementById("lbFilename"),
  lbDimensions: document.getElementById("lbDimensions"),
  lbFilesize: document.getElementById("lbFilesize"),
  lbZoomHUD: document.getElementById("lbZoomHUD"),
  lbToggleDeleteBtn: document.getElementById("lbToggleDeleteBtn"),
  lbDeleteBtnText: document.getElementById("lbDeleteBtnText"),
  lbOpenExplorerBtn: document.getElementById("lbOpenExplorerBtn"),
  lbCloseBtn: document.getElementById("lbCloseBtn"),
  lbPrevBtn: document.getElementById("lbPrevBtn"),
  lbNextBtn: document.getElementById("lbNextBtn"),
  
  // Deletion Modal
  deleteModal: document.getElementById("deleteModal"),
  deleteModalMessage: document.getElementById("deleteModalMessage"),
  deletePreviewThumbnails: document.getElementById("deletePreviewThumbnails"),
  chkRecycleBin: document.getElementById("chkRecycleBin"),
  btnCancelDelete: document.getElementById("btnCancelDelete"),
  btnConfirmDelete: document.getElementById("btnConfirmDelete"),
  
  // Toasts
  toastContainer: document.getElementById("toastContainer")
};

// Initialize Application
document.addEventListener("DOMContentLoaded", () => {
  setupEventListeners();
  checkInitialFolder();
});

// Setup Global Event Listeners
function setupEventListeners() {
  // Folder Selection
  elements.btnBrowseFolder.addEventListener("click", selectFolderDialog);
  
  // Search Filter
  elements.searchBatchesInput.addEventListener("input", handleBatchSearch);
  elements.clearSearchBtn.addEventListener("click", () => {
    elements.searchBatchesInput.value = "";
    elements.clearSearchBtn.style.display = "none";
    handleBatchSearch();
  });
  
  // Grid Thumbnail Zoom Slider
  elements.gridZoomSlider.addEventListener("input", (e) => {
    document.documentElement.style.setProperty("--card-min-width", `${e.target.value}px`);
  });
  
  // Batch Selection Tools
  elements.btnSelectAll.addEventListener("click", selectAllImages);
  elements.btnSelectNone.addEventListener("click", selectNoneImages);
  elements.btnInvert.addEventListener("click", invertSelection);
  elements.btnKeepLargestSize.addEventListener("click", keepLargestSize);
  elements.btnKeepHighestRes.addEventListener("click", keepHighestRes);
  elements.btnKeepFirst.addEventListener("click", keepFirstImage);
  elements.btnDeleteSelected.addEventListener("click", openDeleteModal);
  
  // Delete Modal Actions
  elements.btnCancelDelete.addEventListener("click", closeDeleteModal);
  elements.btnConfirmDelete.addEventListener("click", executeDeletion);
  
  // Lightbox Actions
  elements.lbCloseBtn.addEventListener("click", closeLightbox);
  elements.lbPrevBtn.addEventListener("click", () => navigateLightbox(-1));
  elements.lbNextBtn.addEventListener("click", () => navigateLightbox(1));
  elements.lbToggleDeleteBtn.addEventListener("click", toggleCurrentLightboxMark);
  elements.lbOpenExplorerBtn.addEventListener("click", () => {
    const current = state.images[state.lb.index];
    if (current) openInExplorer(current.path);
  });
  
  // Lightbox Mouse Zoom & Pan
  setupLightboxInteractions();
  
  // Global Keyboard Shortcuts
  window.addEventListener("keydown", handleGlobalShortcuts);
}

// Check if server was launched with an initial folder argument
async function checkInitialFolder() {
  try {
    const res = await fetch("/api/init_info");
    if (res.ok) {
      const data = await res.json();
      if (data.initial_folder) {
        scanDirectory(data.initial_folder);
      }
    }
  } catch (e) {
    console.warn("Could not fetch init info:", e);
  }
}

// Trigger Windows Native Folder Selection Dialog
async function selectFolderDialog() {
  elements.btnBrowseFolder.disabled = true;
  showToast("Opening folder picker...", "info");
  
  try {
    const res = await fetch("/api/select_folder");
    const data = await res.json();
    
    if (data.folder && data.folder.trim() !== "") {
      scanDirectory(data.folder);
    }
  } catch (err) {
    showToast(`Error opening folder picker: ${err.message}`, "danger");
  } finally {
    elements.btnBrowseFolder.disabled = false;
  }
}

// Scan Selected Directory for Multi-Image Sets
async function scanDirectory(folderPath) {
  showToast(`Scanning directory: ${folderPath}`, "info");
  elements.currentFolderPath.textContent = folderPath;
  elements.currentFolderPath.title = folderPath;
  state.rootFolder = folderPath;
  
  try {
    const res = await fetch(`/api/scan?folder=${encodeURIComponent(folderPath)}`);
    const data = await res.json();
    
    if (data.error) {
      showToast(data.error, "danger");
      return;
    }
    
    state.batches = data.batches || [];
    state.filteredBatches = [...state.batches];
    
    // Update header stats
    const totalImages = state.batches.reduce((acc, b) => acc + b.count, 0);
    elements.batchCountBadge.textContent = `${state.batches.length} albums`;
    elements.imageCountBadge.textContent = `${totalImages} images`;
    elements.filteredBatchCount.textContent = state.batches.length;
    
    renderSidebarBatches();
    
    if (state.batches.length > 0) {
      selectBatch(state.batches[0]);
      showToast(`Found ${state.batches.length} multi-image folders`, "success");
    } else {
      elements.gridContainer.innerHTML = `
        <div class="welcome-card">
          <div class="welcome-icon">🔍</div>
          <h3>No multi-image folders found</h3>
          <p>No subfolders containing &gt;1 image were found in this directory.</p>
        </div>
      `;
      elements.batchTools.style.display = "none";
      elements.activeBatchTitle.textContent = "No Multi-Image Folders";
      elements.activeBatchMeta.textContent = folderPath;
    }
  } catch (err) {
    showToast(`Scan error: ${err.message}`, "danger");
  }
}

// Search and Filter Batches in Sidebar
function handleBatchSearch() {
  const query = elements.searchBatchesInput.value.trim().toLowerCase();
  elements.clearSearchBtn.style.display = query ? "block" : "none";
  
  if (!query) {
    state.filteredBatches = [...state.batches];
  } else {
    state.filteredBatches = state.batches.filter(b => 
      b.name.toLowerCase().includes(query) || b.rel_path.toLowerCase().includes(query)
    );
  }
  
  elements.filteredBatchCount.textContent = state.filteredBatches.length;
  renderSidebarBatches();
}

// Render Sidebar Folder List
function renderSidebarBatches() {
  elements.batchList.innerHTML = "";
  
  if (state.filteredBatches.length === 0) {
    elements.batchList.innerHTML = `
      <div class="empty-state-sidebar">
        <p>No matching folders found.</p>
      </div>
    `;
    return;
  }
  
  state.filteredBatches.forEach(batch => {
    const item = document.createElement("div");
    item.className = "batch-item";
    if (state.activeBatch && state.activeBatch.path === batch.path) {
      item.classList.add("active");
    }
    
    item.innerHTML = `
      <div class="batch-item-info">
        <span class="batch-item-name" title="${escapeHtml(batch.name)}">${escapeHtml(batch.name)}</span>
        <span class="batch-item-relpath" title="${escapeHtml(batch.rel_path)}">${escapeHtml(batch.rel_path)}</span>
      </div>
      <span class="batch-item-count">${batch.count}</span>
    `;
    
    item.addEventListener("click", () => selectBatch(batch));
    elements.batchList.appendChild(item);
  });
}

// Select a Batch to Review
async function selectBatch(batch) {
  state.activeBatch = batch;
  state.markedDeletes.clear();
  
  // Highlight active item in sidebar
  document.querySelectorAll(".batch-item").forEach(el => el.classList.remove("active"));
  renderSidebarBatches();
  
  elements.activeBatchTitle.textContent = batch.name;
  elements.activeBatchMeta.textContent = `Loading ${batch.count} images...`;
  elements.batchTools.style.display = "flex";
  elements.btnDeleteSelected.disabled = true;
  elements.deleteBtnLabel.textContent = "Delete Selected";
  
  elements.gridContainer.innerHTML = `
    <div class="welcome-card">
      <div class="welcome-icon">⏳</div>
      <h3>Loading album images...</h3>
    </div>
  `;
  
  try {
    const res = await fetch(`/api/batch?path=${encodeURIComponent(batch.path)}`);
    const data = await res.json();
    
    state.images = data.images || [];
    renderImageGrid();
    updateBatchSubtitle();
  } catch (err) {
    showToast(`Failed to load batch: ${err.message}`, "danger");
  }
}

// Navigate between albums in the sidebar using keyboard (ArrowUp / ArrowDown)
function navigateBatches(delta) {
  if (!state.filteredBatches.length) return;
  const curIdx = state.filteredBatches.findIndex(b => b.path === state.activeBatch?.path);
  const newIdx = Math.max(0, Math.min(state.filteredBatches.length - 1, (curIdx === -1 ? 0 : curIdx) + delta));
  if (newIdx !== curIdx) {
    selectBatch(state.filteredBatches[newIdx]);
    const batchItems = elements.batchList.querySelectorAll(".batch-item");
    if (batchItems[newIdx]) {
      batchItems[newIdx].scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  }
}

// Render Image Cards in the Responsive Grid
function renderImageGrid() {
  elements.gridContainer.innerHTML = "";
  
  if (state.images.length === 0) {
    elements.gridContainer.innerHTML = `
      <div class="welcome-card">
        <div class="welcome-icon">✨</div>
        <h3>All images in this album processed</h3>
        <p>No remaining images in this folder.</p>
      </div>
    `;
    return;
  }
  
  // Determine highest resolution and largest file size in this batch for highlight badges
  let maxPixels = 0;
  let maxSize = 0;
  state.images.forEach(img => {
    const px = (img.width || 0) * (img.height || 0);
    if (px > maxPixels) maxPixels = px;
    const sz = img.size || 0;
    if (sz > maxSize) maxSize = sz;
  });
  
  state.images.forEach((img, index) => {
    const isMarked = state.markedDeletes.has(img.path);
    const card = document.createElement("div");
    card.className = `img-card ${isMarked ? "marked-delete" : ""}`;
    card.dataset.index = index;
    card.dataset.path = img.path;
    
    const isBestRes = maxPixels > 0 && ((img.width || 0) * (img.height || 0)) === maxPixels;
    const isLargestSize = maxSize > 0 && (img.size || 0) === maxSize;
    
    const hotkeyBadgeHtml = index < 9 ? `<kbd class="card-hotkey-badge" title="Press '${index + 1}' to toggle">${index + 1}</kbd>` : "";

    card.innerHTML = `
      <div class="card-overlay-actions">
        <input type="checkbox" class="card-checkbox" ${isMarked ? "checked" : ""} title="Mark for Deletion">
        ${hotkeyBadgeHtml}
      </div>
      <div class="img-thumbnail-wrapper">
        <img class="img-thumbnail" src="/api/thumbnail?path=${encodeURIComponent(img.path)}&size=500" loading="lazy" alt="${escapeHtml(img.name)}">
      </div>
      <div class="card-info">
        <div class="card-filename" title="${escapeHtml(img.name)}">${escapeHtml(img.name)}</div>
        <div class="card-meta-tags">
          <span class="tag ${isBestRes ? "tag-highlight" : ""}">${img.width && img.height ? `${img.width}×${img.height}` : "image"}</span>
          <span class="tag ${isLargestSize ? "tag-size-highlight" : ""}">${img.size_str || ""}</span>
          ${isBestRes ? '<span class="tag tag-highlight">Best Res</span>' : ""}
          ${isLargestSize ? '<span class="tag tag-size-highlight">Largest Size</span>' : ""}
        </div>
      </div>
    `;
    
    // Checkbox Click (Toggle delete mark without opening lightbox)
    const chk = card.querySelector(".card-checkbox");
    chk.addEventListener("click", (e) => {
      e.stopPropagation();
      toggleImageMark(img.path, chk.checked);
    });
    
    // Card Click (Opens Lightbox Viewer)
    card.addEventListener("click", (e) => {
      // If clicking checkbox, don't open lightbox
      if (e.target === chk) return;
      openLightbox(index);
    });
    
    elements.gridContainer.appendChild(card);
  });
  
  updateDeleteButton();
}

// Toggle Deletion Mark for an Image
function toggleImageMark(imagePath, isMarked) {
  if (isMarked) {
    state.markedDeletes.add(imagePath);
  } else {
    state.markedDeletes.delete(imagePath);
  }
  
  // Update card DOM state
  const card = document.querySelector(`.img-card[data-path="${CSS.escape(imagePath)}"]`);
  if (card) {
    card.classList.toggle("marked-delete", isMarked);
    const chk = card.querySelector(".card-checkbox");
    if (chk) chk.checked = isMarked;
  }
  
  // Update Lightbox button if open
  if (state.lb.isOpen && state.images[state.lb.index]?.path === imagePath) {
    updateLightboxMarkButton();
  }
  
  updateDeleteButton();
  updateBatchSubtitle();
}

// Toggle Deletion Mark for an Image by its Grid Index (0-based)
function toggleCardByIndex(index) {
  if (index < 0 || index >= state.images.length) return;
  const img = state.images[index];
  if (!img) return;
  const willMark = !state.markedDeletes.has(img.path);
  toggleImageMark(img.path, willMark);
}

// Update the Subtitle Meta with selection stats
function updateBatchSubtitle() {
  const total = state.images.length;
  const marked = state.markedDeletes.size;
  const totalBytes = state.images.reduce((acc, img) => acc + (img.size || 0), 0);
  const totalSizeStr = formatBytes(totalBytes);
  
  let subtitle = `${total} images • ${totalSizeStr}`;
  if (marked > 0) {
    subtitle += ` • ${marked} marked for deletion`;
  }
  elements.activeBatchMeta.textContent = subtitle;
}

// Update the Delete Action Button
function updateDeleteButton() {
  const count = state.markedDeletes.size;
  if (count > 0) {
    elements.btnDeleteSelected.disabled = false;
    elements.deleteBtnLabel.textContent = `Delete Selected (${count})`;
  } else {
    elements.btnDeleteSelected.disabled = true;
    elements.deleteBtnLabel.textContent = "Delete Selected";
  }
}

// Selection Presets
function selectAllImages() {
  state.images.forEach(img => state.markedDeletes.add(img.path));
  refreshCardSelections();
}

function selectNoneImages() {
  state.markedDeletes.clear();
  refreshCardSelections();
}

function invertSelection() {
  state.images.forEach(img => {
    if (state.markedDeletes.has(img.path)) {
      state.markedDeletes.delete(img.path);
    } else {
      state.markedDeletes.add(img.path);
    }
  });
  refreshCardSelections();
}

// Keep single highest resolution image and mark all other images
function keepHighestRes() {
  if (state.images.length <= 1) return;
  
  let bestIndex = 0;
  let maxPixels = -1;
  
  state.images.forEach((img, idx) => {
    const px = (img.width || 0) * (img.height || 0);
    if (px > maxPixels) {
      maxPixels = px;
      bestIndex = idx;
    }
  });
  
  state.markedDeletes.clear();
  state.images.forEach((img, idx) => {
    if (idx !== bestIndex) {
      state.markedDeletes.add(img.path);
    }
  });
  
  refreshCardSelections();
  showToast(`Kept best resolution (${state.images[bestIndex].width}×${state.images[bestIndex].height}), marked others`, "info");
}

// Keep single largest file by byte size and mark all others
function keepLargestSize() {
  if (state.images.length <= 1) return;
  
  let bestIndex = 0;
  let maxSize = -1;
  
  state.images.forEach((img, idx) => {
    const sz = img.size || 0;
    if (sz > maxSize) {
      maxSize = sz;
      bestIndex = idx;
    }
  });
  
  state.markedDeletes.clear();
  state.images.forEach((img, idx) => {
    if (idx !== bestIndex) {
      state.markedDeletes.add(img.path);
    }
  });
  
  refreshCardSelections();
  showToast(`Kept largest file (${state.images[bestIndex].size_str || ""}), marked others`, "info");
}

// Keep the first image and mark all others
function keepFirstImage() {
  if (state.images.length <= 1) return;
  
  state.markedDeletes.clear();
  state.images.forEach((img, idx) => {
    if (idx !== 0) {
      state.markedDeletes.add(img.path);
    }
  });
  
  refreshCardSelections();
  showToast("Kept first image, marked others", "info");
}

function refreshCardSelections() {
  document.querySelectorAll(".img-card").forEach(card => {
    const p = card.dataset.path;
    const isMarked = state.markedDeletes.has(p);
    card.classList.toggle("marked-delete", isMarked);
    const chk = card.querySelector(".card-checkbox");
    if (chk) chk.checked = isMarked;
  });
  
  if (state.lb.isOpen) {
    updateLightboxMarkButton();
  }
  
  updateDeleteButton();
  updateBatchSubtitle();
}

/* -------------------------------------------------------------
 * FULLSCREEN LIGHTBOX & FLUID MOUSE-CENTERED ZOOM / PAN
 * ------------------------------------------------------------- */
function openLightbox(index) {
  if (index < 0 || index >= state.images.length) return;
  
  state.lb.isOpen = true;
  state.lb.index = index;
  state.lb.scale = 1;
  state.lb.panX = 0;
  state.lb.panY = 0;
  
  const img = state.images[index];
  elements.lbImage.src = `/api/raw_image?path=${encodeURIComponent(img.path)}`;
  elements.lbIndexBadge.textContent = `${index + 1} / ${state.images.length}`;
  elements.lbFilename.textContent = img.name;
  elements.lbDimensions.textContent = img.width && img.height ? `${img.width}×${img.height}` : "";
  elements.lbFilesize.textContent = img.size_str || "";
  
  updateLightboxMarkButton();
  applyLightboxTransform();
  
  elements.lightbox.style.display = "flex";
}

function closeLightbox() {
  state.lb.isOpen = false;
  elements.lightbox.style.display = "none";
  elements.lbImage.src = "";
}

function navigateLightbox(delta) {
  const newIndex = state.lb.index + delta;
  if (newIndex >= 0 && newIndex < state.images.length) {
    openLightbox(newIndex);
  }
}

function toggleCurrentLightboxMark() {
  const current = state.images[state.lb.index];
  if (!current) return;
  
  const willMark = !state.markedDeletes.has(current.path);
  toggleImageMark(current.path, willMark);
}

function updateLightboxMarkButton() {
  const current = state.images[state.lb.index];
  if (!current) return;
  
  const isMarked = state.markedDeletes.has(current.path);
  elements.lbToggleDeleteBtn.classList.toggle("marked", isMarked);
  elements.lbDeleteBtnText.textContent = isMarked ? "Marked for Deletion" : "Mark for Deletion";
}

// Hardware-accelerated CSS transform application
function applyLightboxTransform() {
  elements.lbImage.style.transform = `translate3d(${state.lb.panX}px, ${state.lb.panY}px, 0) scale(${state.lb.scale})`;
  elements.lbZoomHUD.textContent = `${Math.round(state.lb.scale * 100)}%`;
}

// Setup smooth mouse wheel zoom anchored to cursor
function setupLightboxInteractions() {
  const viewport = elements.lbViewport;
  
  // Wheel Zoom (GPU accelerated with cursor anchoring)
  viewport.addEventListener("wheel", (e) => {
    e.preventDefault();
    if (!state.lb.isOpen) return;
    
    const zoomFactor = e.deltaY < 0 ? 1.18 : 0.84;
    const oldScale = state.lb.scale;
    const newScale = Math.min(Math.max(oldScale * zoomFactor, state.lb.minScale), state.lb.maxScale);
    
    if (newScale === oldScale) return;
    
    // Calculate cursor position relative to viewport center
    const rect = viewport.getBoundingClientRect();
    const cursorX = e.clientX - rect.left - rect.width / 2;
    const cursorY = e.clientY - rect.top - rect.height / 2;
    
    // Adjust pan offsets so point under cursor remains stationary
    state.lb.panX -= (cursorX - state.lb.panX) * (newScale / oldScale - 1);
    state.lb.panY -= (cursorY - state.lb.panY) * (newScale / oldScale - 1);
    state.lb.scale = newScale;
    
    applyLightboxTransform();
  }, { passive: false });
  
  // Mouse Drag Panning
  viewport.addEventListener("mousedown", (e) => {
    if (e.button !== 0) return; // Left mouse button only
    state.lb.isPanning = true;
    state.lb.startX = e.clientX - state.lb.panX;
    state.lb.startY = e.clientY - state.lb.panY;
    viewport.style.cursor = "grabbing";
  });
  
  window.addEventListener("mousemove", (e) => {
    if (!state.lb.isPanning) return;
    state.lb.panX = e.clientX - state.lb.startX;
    state.lb.panY = e.clientY - state.lb.startY;
    applyLightboxTransform();
  });
  
  window.addEventListener("mouseup", () => {
    if (state.lb.isPanning) {
      state.lb.isPanning = false;
      viewport.style.cursor = "grab";
    }
  });
  
  // Double-Click to Reset / Fit
  viewport.addEventListener("dblclick", () => {
    if (state.lb.scale !== 1 || state.lb.panX !== 0 || state.lb.panY !== 0) {
      state.lb.scale = 1;
      state.lb.panX = 0;
      state.lb.panY = 0;
    } else {
      state.lb.scale = 2.5; // Zoom in to 250% on dblclick
    }
    applyLightboxTransform();
  });
}

/* -------------------------------------------------------------
 * DELETION CONFIRMATION & EXECUTION
 * ------------------------------------------------------------- */
function openDeleteModal() {
  const count = state.markedDeletes.size;
  if (count === 0) return;
  
  elements.deleteModalMessage.textContent = `Are you sure you want to delete ${count} selected ${count === 1 ? "image" : "images"}?`;
  
  // Populate preview thumbnails
  elements.deletePreviewThumbnails.innerHTML = "";
  Array.from(state.markedDeletes).slice(0, 10).forEach(path => {
    const thumb = document.createElement("img");
    thumb.className = "delete-preview-thumb";
    thumb.src = `/api/thumbnail?path=${encodeURIComponent(path)}&size=100`;
    elements.deletePreviewThumbnails.appendChild(thumb);
  });
  
  if (count > 10) {
    const more = document.createElement("div");
    more.className = "tag";
    more.textContent = `+${count - 10} more`;
    elements.deletePreviewThumbnails.appendChild(more);
  }
  
  elements.deleteModal.style.display = "flex";
}

function closeDeleteModal() {
  elements.deleteModal.style.display = "none";
}

async function executeDeletion() {
  const toDelete = Array.from(state.markedDeletes);
  const useRecycleBin = elements.chkRecycleBin.checked;
  
  elements.btnConfirmDelete.disabled = true;
  elements.btnConfirmDelete.textContent = "Deleting...";
  
  try {
    const res = await fetch("/api/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        paths: toDelete,
        recycle: useRecycleBin
      })
    });
    
    const result = await res.json();
    closeDeleteModal();
    
    if (result.success) {
      showToast(
        `Successfully deleted ${result.deleted} items ${useRecycleBin ? "(sent to Recycle Bin)" : "(permanently)"}`,
        "success"
      );
      
      // If lightbox was open on a deleted image, close it
      if (state.lb.isOpen) {
        closeLightbox();
      }
      
      // Reload the current batch
      if (state.activeBatch) {
        await selectBatch(state.activeBatch);
      }
      
      // Update sidebar album image count
      state.activeBatch.count -= result.deleted;
      renderSidebarBatches();
    } else {
      showToast(`Delete completed with errors: ${result.errors.join(", ")}`, "danger");
    }
  } catch (err) {
    showToast(`Deletion request failed: ${err.message}`, "danger");
  } finally {
    elements.btnConfirmDelete.disabled = false;
    elements.btnConfirmDelete.textContent = "Confirm Delete";
  }
}

// Reveal File in Windows Explorer
async function openInExplorer(path) {
  try {
    await fetch(`/api/open_in_explorer?path=${encodeURIComponent(path)}`);
  } catch (e) {
    console.error("Open in explorer error:", e);
  }
}

/* -------------------------------------------------------------
 * KEYBOARD SHORTCUTS
 * ------------------------------------------------------------- */
function handleGlobalShortcuts(e) {
  // If user is typing in search input, don't trigger hotkeys
  if (e.target === elements.searchBatchesInput) {
    if (e.key === "Escape") {
      elements.searchBatchesInput.blur();
    }
    return;
  }
  
  // Lightbox Active Keys
  if (state.lb.isOpen) {
    if (e.key === "Escape") {
      closeLightbox();
      return;
    }
    if (e.key === "ArrowLeft" || e.key.toLowerCase() === "a") {
      navigateLightbox(-1);
      return;
    }
    if (e.key === "ArrowRight" || e.key.toLowerCase() === "d") {
      navigateLightbox(1);
      return;
    }
    if (e.key === " ") {
      e.preventDefault();
      toggleCurrentLightboxMark();
      return;
    }
    if (e.key === "Delete" || e.key === "Backspace") {
      openDeleteModal();
      return;
    }
    return;
  }
  
  // Modal Active Keys
  if (elements.deleteModal.style.display === "flex") {
    if (e.key === "Escape") {
      closeDeleteModal();
    } else if (e.key === "Enter") {
      executeDeletion();
    }
    return;
  }
  
  // Main Grid Keys
  if (e.ctrlKey && e.key.toLowerCase() === "a") {
    e.preventDefault();
    selectAllImages();
  } else if (e.ctrlKey && e.key.toLowerCase() === "d") {
    e.preventDefault();
    selectNoneImages();
  } else if (e.ctrlKey && e.key.toLowerCase() === "i") {
    e.preventDefault();
    invertSelection();
  } else if (e.key === "ArrowDown") {
    e.preventDefault();
    navigateBatches(1);
  } else if (e.key === "ArrowUp") {
    e.preventDefault();
    navigateBatches(-1);
  } else if (!e.ctrlKey && !e.altKey && !e.metaKey && e.key.toLowerCase() === "q") {
    e.preventDefault();
    keepLargestSize();
  } else if (!e.ctrlKey && !e.altKey && !e.metaKey && e.key.toLowerCase() === "w") {
    e.preventDefault();
    keepHighestRes();
  } else if (e.key === "Delete" || e.key === "Backspace") {
    if (state.markedDeletes.size > 0) {
      e.preventDefault();
      openDeleteModal();
    }
  } else if (!e.ctrlKey && !e.altKey && !e.metaKey && e.key >= "1" && e.key <= "9") {
    const cardIndex = parseInt(e.key, 10) - 1;
    if (cardIndex >= 0 && cardIndex < state.images.length) {
      e.preventDefault();
      toggleCardByIndex(cardIndex);
    }
  }
}

/* -------------------------------------------------------------
 * UTILITY HELPERS
 * ------------------------------------------------------------- */
function showToast(message, type = "info") {
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `<span>${escapeHtml(message)}</span>`;
  
  elements.toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(50px)";
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

function formatBytes(bytes) {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/[&<>"']/g, m => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;"
  })[m]);
}

// Export for Node.js unit tests if applicable
if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    state,
    elements,
    toggleCardByIndex,
    navigateBatches,
    keepLargestSize,
    keepHighestRes,
    handleGlobalShortcuts,
    escapeHtml,
    formatBytes
  };
}
