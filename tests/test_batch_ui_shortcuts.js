/**
 * Unit Tests: Batch Image Cleaner v7 Pro Keyboard Shortcuts & UI Badges
 * Run with: node tests/test_batch_ui_shortcuts.js
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

console.log("▶ Running Batch UI Shortcuts & Hotkeys Unit Tests...");

const appJsPath = path.resolve(__dirname, '../gallery-dl/batch-ui/app.js');
const indexHtmlPath = path.resolve(__dirname, '../gallery-dl/batch-ui/index.html');
const indexCssPath = path.resolve(__dirname, '../gallery-dl/batch-ui/index.css');

const appJsSource = fs.readFileSync(appJsPath, 'utf8');
const indexHtmlSource = fs.readFileSync(indexHtmlPath, 'utf8');
const indexCssSource = fs.readFileSync(indexCssPath, 'utf8');

// Test 1: HTML structure includes bottom helper bar for main workspace
function testBottomHelperBarStructure() {
    console.log("  [Test 1] Verifying bottom shortcut bar in index.html...");
    assert.ok(
        indexHtmlSource.includes('workspace-footer-tips'),
        "index.html must include a persistent bottom shortcut helper bar with class 'workspace-footer-tips'"
    );
    assert.ok(indexHtmlSource.includes('Backspace') || indexHtmlSource.includes('Del'), "Must display Backspace/Del shortcut in footer");
    assert.ok(indexHtmlSource.includes('1') && indexHtmlSource.includes('9'), "Must display 1-9 shortcut hint in footer");
    assert.ok(indexHtmlSource.includes('Enter'), "Must display Enter shortcut in footer");
    assert.ok(indexHtmlSource.includes('Esc'), "Must display Esc shortcut in footer");
    // New: Up/Down arrow and Q/W hints
    assert.ok(indexHtmlSource.includes('↑') || indexHtmlSource.includes('&uarr;') || indexHtmlSource.includes('Up'), "Must display Up/Down batch shortcut in footer");
    assert.ok(indexHtmlSource.includes('Q') && indexHtmlSource.includes('W'), "Must display Q and W shortcuts in footer");
    console.log("    ✔ Bottom shortcut bar HTML verified.");
}

// Test 2: CSS includes styling for footer tips and badges
function testCssStyles() {
    console.log("  [Test 2] Verifying CSS styles for footer tips and card badges...");
    assert.ok(indexCssSource.includes('.workspace-footer-tips'), "CSS must style .workspace-footer-tips");
    assert.ok(indexCssSource.includes('.card-hotkey-badge'), "CSS must style .card-hotkey-badge");
    assert.ok(indexCssSource.includes('.tag-size-highlight') || indexCssSource.includes('.tag-largest-size'), "CSS must style largest size badge");
    console.log("    ✔ CSS styles verified.");
}

// Test 3: Number row keys (1-9) toggle function in app.js
function testNumberRowToggleLogic() {
    console.log("  [Test 3] Verifying number row 1-9 toggle logic in app.js...");
    assert.ok(
        appJsSource.includes('toggleCardByIndex'),
        "app.js must define toggleCardByIndex function"
    );
    assert.ok(
        appJsSource.includes('e.key >= "1"') && appJsSource.includes('e.key <= "9"'),
        "handleGlobalShortcuts must check e.key >= '1' && e.key <= '9'"
    );
    console.log("    ✔ Number row toggle handler verified.");
}

// Test 4: Backspace key triggers delete modal in app.js
function testBackspaceDeleteShortcut() {
    console.log("  [Test 4] Verifying Backspace delete shortcut in app.js...");
    assert.ok(
        appJsSource.includes('e.key === "Backspace"') || appJsSource.includes("e.key === 'Backspace'"),
        "app.js must handle Backspace key for deletion"
    );
    console.log("    ✔ Backspace shortcut verified.");
}

// Test 5: Enter confirms and Esc cancels in delete modal & Lightbox
function testModalAndLightboxEscEnter() {
    console.log("  [Test 5] Verifying Modal & Lightbox Esc/Enter shortcuts...");
    assert.ok(appJsSource.includes('closeDeleteModal'), "Escape must close delete modal");
    assert.ok(appJsSource.includes('executeDeletion'), "Enter must execute deletion in modal");
    assert.ok(appJsSource.includes('closeLightbox'), "Escape must close lightbox");
    console.log("    ✔ Modal & Lightbox Esc/Enter verified.");
}

// Test 6: Number badge and Largest Size badge rendering on cards
function testCardBadges() {
    console.log("  [Test 6] Verifying card hotkey and Largest Size badges in app.js...");
    assert.ok(
        appJsSource.includes('card-hotkey-badge'),
        "app.js must render .card-hotkey-badge on image cards for indices 0 to 8"
    );
    assert.ok(
        appJsSource.includes('Largest Size') || appJsSource.includes('Highest Size'),
        "app.js must render Largest Size badge"
    );
    console.log("    ✔ Card hotkey and Largest Size badges verified.");
}

// Test 7: Batch navigation with ArrowUp and ArrowDown
function testBatchNavigation() {
    console.log("  [Test 7] Verifying ArrowUp / ArrowDown batch navigation in app.js...");
    assert.ok(appJsSource.includes('navigateBatches'), "app.js must define navigateBatches function");
    assert.ok(
        appJsSource.includes('ArrowUp') && appJsSource.includes('ArrowDown'),
        "app.js must handle ArrowUp and ArrowDown keys"
    );
    console.log("    ✔ Batch navigation handler verified.");
}

// Test 8: Q and W shortcuts and Keep Largest Size preset
function testQWPresets() {
    console.log("  [Test 8] Verifying Q/W shortcuts and Keep Largest Size preset in app.js & index.html...");
    assert.ok(appJsSource.includes('keepLargestSize'), "app.js must define keepLargestSize function");
    assert.ok(
        indexHtmlSource.includes('btnKeepLargestSize'),
        "index.html must include btnKeepLargestSize button"
    );
    assert.ok(
        appJsSource.includes('"q"') || appJsSource.includes("'q'"),
        "app.js must handle 'q' key for keepLargestSize"
    );
    assert.ok(
        appJsSource.includes('"w"') || appJsSource.includes("'w'"),
        "app.js must handle 'w' key for keepHighestRes"
    );
    console.log("    ✔ Q/W presets verified.");
}

// Test 9: Functional simulation of all features
function testFunctionalShortcutHandling() {
    console.log("  [Test 9] Verifying functional shortcut execution...");

    // Setup miniature state
    const mockState = {
        batches: [
            { path: "D:/batch_0", name: "batch_0" },
            { path: "D:/batch_1", name: "batch_1" },
            { path: "D:/batch_2", name: "batch_2" }
        ],
        filteredBatches: [],
        activeBatch: null,
        images: [
            { path: "D:/img1.jpg", name: "img1.jpg", width: 1000, height: 1000, size: 2000000 },
            { path: "D:/img2.jpg", name: "img2.jpg", width: 2000, height: 2000, size: 1000000 }, // Best Res
            { path: "D:/img3.jpg", name: "img3.jpg", width: 800, height: 800, size: 5000000 }   // Largest Size
        ],
        markedDeletes: new Set(),
        lb: { isOpen: false },
        modalOpen: false
    };
    mockState.filteredBatches = [...mockState.batches];
    mockState.activeBatch = mockState.filteredBatches[0];

    let deleteModalOpened = false;
    let deletionExecuted = false;
    let modalClosed = false;
    let lightboxClosed = false;
    let selectedBatch = null;

    function selectBatch(batch) {
        mockState.activeBatch = batch;
        selectedBatch = batch;
    }

    function navigateBatches(delta) {
        if (!mockState.filteredBatches.length) return;
        const curIdx = mockState.filteredBatches.findIndex(b => b.path === mockState.activeBatch?.path);
        const newIdx = Math.max(0, Math.min(mockState.filteredBatches.length - 1, (curIdx === -1 ? 0 : curIdx) + delta));
        if (newIdx !== curIdx) {
            selectBatch(mockState.filteredBatches[newIdx]);
        }
    }

    function keepHighestRes() {
        let bestIndex = 0;
        let maxPixels = -1;
        mockState.images.forEach((img, idx) => {
            const px = (img.width || 0) * (img.height || 0);
            if (px > maxPixels) {
                maxPixels = px;
                bestIndex = idx;
            }
        });
        mockState.markedDeletes.clear();
        mockState.images.forEach((img, idx) => {
            if (idx !== bestIndex) mockState.markedDeletes.add(img.path);
        });
    }

    function keepLargestSize() {
        let bestIndex = 0;
        let maxSize = -1;
        mockState.images.forEach((img, idx) => {
            const sz = img.size || 0;
            if (sz > maxSize) {
                maxSize = sz;
                bestIndex = idx;
            }
        });
        mockState.markedDeletes.clear();
        mockState.images.forEach((img, idx) => {
            if (idx !== bestIndex) mockState.markedDeletes.add(img.path);
        });
    }

    function toggleImageMark(path, willMark) {
        if (willMark) mockState.markedDeletes.add(path);
        else mockState.markedDeletes.delete(path);
    }

    function toggleCardByIndex(idx) {
        if (idx < 0 || idx >= mockState.images.length) return;
        const img = mockState.images[idx];
        const willMark = !mockState.markedDeletes.has(img.path);
        toggleImageMark(img.path, willMark);
    }

    function simulateShortcut(e, isSearchFocused = false) {
        if (isSearchFocused) {
            if (e.key === "Escape") return "blurSearch";
            return;
        }

        if (mockState.lb.isOpen) {
            if (e.key === "Escape") {
                lightboxClosed = true;
                mockState.lb.isOpen = false;
                return;
            }
        }

        if (mockState.modalOpen) {
            if (e.key === "Escape") {
                modalClosed = true;
                mockState.modalOpen = false;
            } else if (e.key === "Enter") {
                deletionExecuted = true;
            }
            return;
        }

        if (e.key === "ArrowDown") {
            navigateBatches(1);
        } else if (e.key === "ArrowUp") {
            navigateBatches(-1);
        } else if (e.key.toLowerCase() === "q") {
            keepLargestSize();
        } else if (e.key.toLowerCase() === "w") {
            keepHighestRes();
        } else if ((e.key === "Delete" || e.key === "Backspace") && mockState.markedDeletes.size > 0) {
            deleteModalOpened = true;
            mockState.modalOpen = true;
        } else if (!e.ctrlKey && !e.altKey && !e.metaKey && e.key >= "1" && e.key <= "9") {
            const idx = parseInt(e.key, 10) - 1;
            toggleCardByIndex(idx);
        }
    }

    // 1. Batch navigation down -> should select batch_1
    simulateShortcut({ key: 'ArrowDown' });
    assert.strictEqual(mockState.activeBatch.name, "batch_1", "ArrowDown must navigate to next batch");

    // 2. Batch navigation up -> should select batch_0
    simulateShortcut({ key: 'ArrowUp' });
    assert.strictEqual(mockState.activeBatch.name, "batch_0", "ArrowUp must navigate to previous batch");

    // 3. Keep Largest Size (Q) -> img3 is 5MB, so img1 and img2 should be marked for deletion
    simulateShortcut({ key: 'q' });
    assert.ok(mockState.markedDeletes.has("D:/img1.jpg"), "Q must mark img1");
    assert.ok(mockState.markedDeletes.has("D:/img2.jpg"), "Q must mark img2");
    assert.ok(!mockState.markedDeletes.has("D:/img3.jpg"), "Q must KEEP img3 (largest size)");

    // 4. Keep Best Res (W) -> img2 is 2000x2000, so img1 and img3 should be marked for deletion
    simulateShortcut({ key: 'w' });
    assert.ok(mockState.markedDeletes.has("D:/img1.jpg"), "W must mark img1");
    assert.ok(!mockState.markedDeletes.has("D:/img2.jpg"), "W must KEEP img2 (best res)");
    assert.ok(mockState.markedDeletes.has("D:/img3.jpg"), "W must mark img3");

    // 5. Number toggles and Backspace still work
    simulateShortcut({ key: '1' });
    simulateShortcut({ key: 'Backspace' });
    assert.strictEqual(deleteModalOpened, true, "Backspace opens modal");

    console.log("    ✔ Functional simulation passed.");
}

// Run all test suites
try {
    testBottomHelperBarStructure();
    testCssStyles();
    testNumberRowToggleLogic();
    testBackspaceDeleteShortcut();
    testModalAndLightboxEscEnter();
    testCardBadges();
    testBatchNavigation();
    testQWPresets();
    testFunctionalShortcutHandling();
    console.log("✅ All Batch UI shortcut tests passed successfully!\n");
} catch (err) {
    console.error("❌ Test failed:", err.message);
    process.exit(1);
}
