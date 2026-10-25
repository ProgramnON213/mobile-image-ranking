# ADR-0001: Local Web-Powered Architecture for Batch Image Cleaner v7

## Status
Accepted

## Date
2026-10-25

## Context
Downloaded image sets and galleries often contain burst shots, variations, and duplicates organized into multi-image folders (`> 1` images). Previously, `batchManualProcessing6.py` was used to manually inspect and prune these collections. However, it suffered from severe UX and performance bottlenecks:
- **CPU-bound image decodes:** Loading multi-image folders (with 10MB–40MB high-resolution PNG/JPEG files) caused the single-threaded Tkinter UI loop to freeze and stutter.
- **Choppy Zoom/Pan:** The zoom viewer performed software bilinear resizing via Pillow on CPU for each mouse wheel tick, resulting in 5–15 FPS lag during inspection.
- **Rigid 2-Column Layout:** Wasted screen real estate on modern 1440p and 4K displays.
- **Unsafe Deletions:** Used hard `os.remove()` with no Recycle Bin recovery.
- **Lack of Selection Shortcuts:** Users had to click every checkbox individually without presets like "Keep Highest Resolution" or "Select All".

## Decision
Supersede `batchManualProcessing6.py` by introducing `batchManualProcessing7.py` and its dedicated static client in `gallery-dl/batch-ui/`.

The new system adopts a **local web-powered architecture**:
1. **Backend:** A lightweight Python HTTP server (`http.server` + `socketserver.ThreadingMixIn`) utilizing only standard libraries and Pillow (already available in the environment). It features:
   - Concurrent, multi-threaded thumbnail requests.
   - In-memory thread-safe LRU thumbnail caching (`(path, mtime, size) -> bytes`).
   - Folder metadata caching for sub-millisecond album switching.
   - Native Windows folder selection via PowerShell .NET `FolderBrowserDialog`.
   - Windows Recycle Bin deletion via PowerShell .NET `Microsoft.VisualBasic.FileIO.FileSystem::DeleteFile` with fallback to `os.remove`.
   - Standalone application window launch via Edge/Chrome `--app=...` flag.
2. **Frontend:** Pure Vanilla HTML5, CSS3, and ES6+ JavaScript:
   - GPU-accelerated hardware compositing for buttery 60–144Hz scrolling and lazy-loaded image grids.
   - Responsive CSS auto-fit grid with interactive card size slider.
   - Fullscreen lightbox featuring Figma/Google Maps style cursor-anchored mouse wheel zoom (`translate3d` + `scale`), double-click reset, and drag-to-pan.
   - Album navigation (`←` / `→` or `A` / `D`), Space to toggle deletion mark, and Delete key confirmation.
   - Preset selection tools: `Keep Best Res`, `Keep First`, `Select All`, `Deselect All`, `Invert`.

## Alternatives Considered

### 1. Modernizing Tkinter with CustomTkinter / ThreadPoolExecutor
- **Pros:** Stays within a single Python GUI script.
- **Cons:** Tkinter Canvas is inherently software-rendered on the CPU. Continuous mouse wheel zooming on large images remains choppy. Canvas item destruction causes layout reflow jank.
- **Rejected:** Cannot achieve 60+ FPS fluid zooming and responsive multi-column layouts without heavy complexity.

### 2. Migrating to PyQt6 / PySide6
- **Pros:** GPU-accelerated `QGraphicsView` / `QOpenGLWidget`, native widgets.
- **Cons:** Introduces heavy external C++ binaries (`~100MB+`), requires additional `pip install` dependencies, and potential cross-platform wheel incompatibilities.
- **Rejected:** Violates project goal of zero extra dependencies beyond the base environment.

### 3. Merging into Mobile Image Ranker PWA
- **Pros:** Reuses existing frontend assets.
- **Cons:** `mobile-image-ranker` is optimized for 1-by-1 mobile swipe triage (Tinder deck). Desktop batch album cleaning requires simultaneous multi-image comparison, multi-column grids, and multi-file bulk deletion.
- **Rejected:** Distinct workflows and user contexts justify separate, specialized tools.

## Consequences
- No extra pip packages required (operates with standard library and existing Pillow installation).
- Deletions are recoverable by default via the Windows Recycle Bin.
- Smooth, responsive 60–144Hz UX on any screen resolution.
- `batchManualProcessing6.py` is preserved in the repository as a legacy fallback.
- Documented in `.agents/AGENTS.md` and `README.md`.
