# Workspace Rules: gallery-dl & mobile-image-ranker

This workspace combines `gallery-dl` (a robust image downloader) with `mobile-image-ranker` (a web-based Tinder-style swipe interface to quickly review and sort downloaded images offline) and companion python tools to manage files.

## Tech Stack
- **Frontend App**: Pure Vanilla HTML5, CSS3, and JavaScript (ES6+), built as an offline-first Progressive Web App (PWA) with a Service Worker.
- **Styling**: Sleek dark mode design with modern typography (Outfit via Google Fonts), glassmorphism, responsive tinder-style swipe animations, and fluid transitions.
- **Local Dev Server**: Python 3 http server (`mobile-image-ranker/serve.py`) that handles cross-origin resource sharing (CORS) and disables aggressive caching headers.
- **Python Utilities**: Helper scripts (like `delete_discarded.py`, clustering tools) to process rated images on the local disk using standard Python libraries (e.g. `tkinter`, `pillow`, `sqlite3`).
- **Downloader Configuration**: `gallery-dl.conf` specifies extractor archives to track downloads in `history.sqlite3`.

## Commands
- **Launch Frontend Server**: `python mobile-image-ranker/serve.py` (serves the PWA locally on port 8000 and prints local IP links for mobile debugging).
- **Run Discard Processing GUI/CLI**: `python delete_discarded.py`
- **Run Pick Wallpaper UI**: `python gallery-dl/pickWallpaper_ui.py`
- **Run Gallery-dl**: `gallery-dl --config gallery-dl.conf "<URL>"`

## Project Map

### Root Directory
- [gallery-dl.conf](file:///d:/Download/Gallery-dl/gallery-dl.conf): Extractor archive configuration pointing to `./history.sqlite3`.
- [history.sqlite3](file:///d:/Download/Gallery-dl/history.sqlite3): SQLite database mapping downloaded URLs to prevent redownloads.
- [delete_discarded.py](file:///d:/Download/Gallery-dl/delete_discarded.py): A Python script with optional Tkinter GUI (and CLI fallback) to preview and delete images rated as 'discard' in exports from the PWA.
- [delete_by_filename.py](file:///d:/Download/Gallery-dl/delete_by_filename.py): Interactive or CLI synchronization script to delete files in Target Dir A that exist in Reference Dir B.

### Mobile Image Ranker App (PWA) (`mobile-image-ranker/`)
A mobile-first Tinder-style swipe interface to quickly review and sort downloaded images offline.
- [serve.py](file:///d:/Download/Gallery-dl/mobile-image-ranker/serve.py): Python dev server (default port 8000) disabling caching, enabling CORS, and listing local IP links for mobile testing.
- [index.html](file:///d:/Download/Gallery-dl/mobile-image-ranker/index.html): HTML entrypoint including Outfits fonts, manifest, and service worker registration.
- [index.css](file:///d:/Download/Gallery-dl/mobile-image-ranker/index.css): Sleek CSS variables, animations, and layouts.
- [app.js](file:///d:/Download/Gallery-dl/mobile-image-ranker/app.js): Tinder swipe UI controller, handling folder input, local/IndexedDB session saving, gesture mechanics, stats calculation, and JSON/CSV exporting.
- [sw.js](file:///d:/Download/Gallery-dl/mobile-image-ranker/sw.js) & [manifest.json](file:///d:/Download/Gallery-dl/mobile-image-ranker/manifest.json): Offline configuration mapping assets, and PWA metadata.

### Gallery-dl Utilities & Wallpaper Processing (`gallery-dl/`)
- [pickWallpaper.py](file:///d:/Download/Gallery-dl/gallery-dl/pickWallpaper.py): CLIP-based CLI ranker. Uses OpenAI CLIP model to rank images according to positive/negative prompts (e.g. aesthetic, dark theme) and crop aspect ratios for phone and laptop.
- [pickWallpaper_ui.py](file:///d:/Download/Gallery-dl/gallery-dl/pickWallpaper_ui.py): Web server hosting CLIP ranking and cropping tool, featuring powershell-based folder selection for Windows environments.
- [batchManualProcessing6.py](file:///d:/Download/Gallery-dl/gallery-dl/batchManualProcessing6.py): Tkinter-based bulk image review, selection, and deletion tool.
- [imageToVector.py](file:///d:/Download/Gallery-dl/gallery-dl/imageToVector.py): Feature vector extractor using MobileNetV2. Saves embeddings to `image_data.pkl`.
- [clusterAndRouteFile.py](file:///d:/Download/Gallery-dl/gallery-dl/clusterAndRouteFile.py): Groups images into clusters using DBSCAN and Cosine distance based on MobileNetV2 embeddings.
- [findNonImageFile.py](file:///d:/Download/Gallery-dl/findNonImageFile.py): Script to isolate and copy non-image assets/text logs from downloaded folders.

## Code Conventions

### PWA / Web Client
- Keep frontend 100% client-side. Images must never be uploaded to any remote server.
- No build steps or frameworks (no React, Webpack, Vite, etc.) — write standard, clean ES6+ JavaScript.
- Preserve PWA features, manifest configurations, and Service Worker offline caching functionality.
- For styling additions, update `mobile-image-ranker/index.css` respecting defined CSS Custom Properties (e.g., `--bg-primary`, `--color-primary`, `--font-sans`).
- Ensure swipe gestures and pinch-to-zoom overlays work smoothly on mobile browsers (Safari iOS, Chrome Android) with proper touch translations.

### Python Helper Scripts
- Ensure cross-platform path compatibility. Paths inside JSON or CSV export files can use backslashes or forward slashes depending on client export.
- When performing filesystem modifications (like deleting discarded files), always prompt the user or offer confirmation.
- Use standard GUI elements (`tkinter` with optional `pillow` imports) for interactive tools. Fall back gracefully to CLI if UI libraries are missing.

## Boundaries
- Never commit configuration files containing credentials or secrets.
- Do not introduce NPM/Node.js dependencies to the frontend unless explicitly requested.
- Always test local server hosting with mobile layouts in mind (responsive design, touch responsiveness).

## Context Engineering Guidelines
- **Level 1 (Rules Files)**: Keep this `.agents/AGENTS.md` file up to date with project conventions.
- **Level 2 (Feature Work)**: Focus reads strictly on files relevant to the active task (e.g. read `mobile-image-ranker/app.js` when modifying swipe animations).
- **Level 3 (Safety)**: When parsing user JSON outputs or file configurations, verify paths exist under the designated roots and confirm deletions.

