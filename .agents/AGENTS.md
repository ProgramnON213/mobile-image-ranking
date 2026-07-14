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
