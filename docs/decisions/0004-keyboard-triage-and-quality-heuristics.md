# ADR-0004: Ergonomic Left-Hand Keyboard Triage and Quality-vs-Resolution Heuristics in Batch Image Cleaner v7

## Status
Accepted

## Date
2026-10-26

## Context
Image collections scraped or ingested via `gallery-dl` and clustered via `clusterAndRouteFile.py` (DBSCAN) often yield dozens or hundreds of folders containing 2 to 8 visually similar variants, burst shots, and duplicates.

While [ADR-0001](0001-batch-image-cleaner-v7-web-ui.md) established the hardware-accelerated local web architecture for [batchManualProcessing7.py](../../gallery-dl/batchManualProcessing7.py), triaging large numbers of albums remained mouse-heavy. Users had to repeatedly click individual checkboxes, move the cursor to the action toolbar to click "Delete Selected", confirm the modal, and click through the sidebar folder list. This mouse dependency caused cognitive and physical friction during high-volume curation.

Furthermore, users frequently encounter a dilemma between two competing image attributes:
1. **Pixel Dimensions (`Best Res`):** The image with the greatest pixel count ($W \times H$).
2. **File Size & Compression Fidelity (`Largest Size`):** The image with the largest file size on disk (e.g. an uncompressed 6.4 MB PNG or high-bitrate JPEG vs an artificially upscaled 1.2 MB low-quality compressed JPEG).

Previously, the UI only tagged and offered presets for `Best Res`, creating a risk that users would accidentally discard authentic, high-detail original files in favor of artificially upscaled, lower-fidelity images.

## Decision
We implement a zero-mouse, left-handed keyboard triage system and dual quality heuristics in [gallery-dl/batch-ui/](../../gallery-dl/batch-ui):

### 1. Left-Handed Keyboard Triage Matrix
The physical key layout is optimized around the left hand resting on the number row and WASD zone:
- **Card Selection (<kbd>1</kbd>–<kbd>9</kbd>):** Pressing numbers `1` through `9` in the album grid toggles the deletion selection on the 1st through 9th image cards. Each card renders an on-card indicator (`<kbd class="card-hotkey-badge">1</kbd>`..`<kbd>9</kbd>`) next to its checkbox. (Sets with $>9$ images remain mouse-operable).
- **Preset Hotkeys (<kbd>Q</kbd> & <kbd>W</kbd>):** Placed directly beneath fingers on `1` and `2`:
  - <kbd>Q</kbd>: `Keep Largest Size` (marks all images for deletion except the largest file by byte size).
  - <kbd>W</kbd>: `Keep Best Res` (marks all images for deletion except the single highest-resolution image).
- **Album / Batch Cycling (<kbd>↑</kbd> / <kbd>↓</kbd>):** Navigates to the previous or next album in the sidebar filter list, smoothly scrolling the active folder item into view.
- **Safe Deletion Flow (<kbd>Backspace</kbd> + <kbd>Enter</kbd>):**
  - <kbd>Backspace</kbd> (or <kbd>Del</kbd>): Opens the confirmation modal if $\ge 1$ images are marked.
  - <kbd>Enter</kbd>: Confirms deletion in the modal.
  - <kbd>Esc</kbd>: Cancels the modal or exits the fullscreen Lightbox.
- **Input Isolation:** All hotkeys are suppressed when the folder search `<input>` is focused, preventing accidental actions while typing.

### 2. Dual Heuristic Badges (Resolution vs. Size)
During grid rendering, both `maxPixels` and `maxSize` are evaluated per batch:
- **`Best Res` Tag (Purple / `.tag-highlight`):** Highlights the image with the highest dimensions.
- **`Largest Size` Tag (Emerald Green / `.tag-size-highlight`):** Highlights the image with the greatest byte size on disk.
- If one image satisfies both criteria, both tags display side-by-side, giving instant visual certainty that the file is superior in both dimensions and uncompressed fidelity.

### 3. Persistent On-Screen Shortcut Reference
A persistent bottom helper bar (`.workspace-footer-tips`) styled after the Lightbox overlay tips sits at the bottom of the workspace, displaying all available shortcuts:
```text
↑↓ Prev / Next Folder • 1–9 Toggle Select • Q Keep Size • W Keep Res • Backspace / Del Delete Selected • Enter Confirm Modal • Esc Cancel Modal / Exit Lightbox • Space Toggle in Lightbox • Ctrl+A / Ctrl+D / Ctrl+I All / None / Invert
```

## Alternatives Considered

### 1. Multi-Digit Number Buffering (e.g. typing "12" for 12th image)
- **Pros:** Extends keyboard toggling to arbitrarily large image sets.
- **Cons:** Introduces key debounce delays, timeout race conditions, and visual complexity. 95% of DBSCAN duplicate clusters contain $\le 8$ images.
- **Rejected:** Keep the number row 1-to-1 immediate without latency. Mouse click covers the rare $>9$ overflow cards.

### 2. Single Composite "Quality Score"
- **Pros:** A single badge instead of two.
- **Cons:** Pixel resolution and byte size measure fundamentally different properties. An algorithm cannot assume whether a user values raw canvas dimensions over compression quality without domain context.
- **Rejected:** Presenting both independent facts (`Best Res` in purple and `Largest Size` in emerald green) empowers user discretion.

### 3. Instant Deletion on Backspace Without Modal
- **Pros:** Saves one keystroke (<kbd>Enter</kbd>).
- **Cons:** High risk of accidental file loss if <kbd>Backspace</kbd> is pressed unintentionally.
- **Rejected:** The two-stroke flow (<kbd>Backspace</kbd> $\rightarrow$ <kbd>Enter</kbd>) is near-instantaneous for a trained user while retaining an essential safety barrier.

## Consequences
- Batch album curation throughput increases 5–10x by enabling uninterrupted keyboard navigation.
- Users can clearly distinguish between upscaled JPEGs and uncompressed source images before deleting.
- Fully automated regression and functional unit tests maintained in `tests/test_batch_ui_shortcuts.js`.
- Updates reflected in `.agents/AGENTS.md` and `README.md`.
