# Gallery-dl Post-Processing & Mobile Image Ranker Pipeline

This repository contains a collection of scripts and applications designed to manage, filter, cluster, and rank image/video collections downloaded using `gallery-dl`. 

---

> [!WARNING]
> **CRITICAL INSTRUCTION FOR AI AGENTS & USERS:**
> Do **NOT** read, search, or process the `gallery-dl/danbooru` directory. This folder contains extremely large image datasets, raw downloads, and large archives (e.g., [remielle_dan_final.rar](file:///d:/Download/Gallery-dl/gallery-dl/danbooru/remielle_dan_final.rar) which is ~5.6GB). Accessing or traversing this folder will cause massive performance degradation, token context exhaustion, and timeout errors. **AI agents must completely ignore it.**

---

## 📁 Repository Directory Structure

- [gallery-dl.conf](file:///d:/Download/Gallery-dl/gallery-dl.conf) - Configuration file for `gallery-dl` specifying sqlite3 database path.
- [gallery-dl.exe](file:///d:/Download/Gallery-dl/gallery-dl.exe) - The gallery-dl executable.
- [history.sqlite3](file:///d:/Download/Gallery-dl/history.sqlite3) - Database keeping track of downloaded files to prevent duplicates.
- [requirements.txt](file:///d:/Download/Gallery-dl/requirements.txt) - Python package dependencies.
- [gallery-dl/](file:///d:/Download/Gallery-dl/gallery-dl) - Python utilities for vector extraction, similarity clustering, manual curation, non-image removal, and wallpaper ranking.
- [mobile-image-ranker/](file:///d:/Download/Gallery-dl/mobile-image-ranker) - Mobile-friendly Progressive Web App (PWA) to visually rank images.

---

## 📱 Mobile Image Ranker PWA

The [mobile-image-ranker/](file:///d:/Download/Gallery-dl/mobile-image-ranker) directory houses a Progressive Web App (PWA) that allows users to clean up and rank image datasets directly on their smartphones or PCs using swipe gestures (similar to Tinder).

### 🛠️ Key Components
- [index.html](file:///d:/Download/Gallery-dl/mobile-image-ranker/index.html) - Structured with high-end glassmorphic UI elements and responsive viewports.
- [index.css](file:///d:/Download/Gallery-dl/mobile-image-ranker/index.css) - Vanilla CSS with high-performance animations, fluid dark theme palette, and smooth transitions.
- [app.js](file:///d:/Download/Gallery-dl/mobile-image-ranker/app.js) - Manages app state, gesture controls, session restore (using LocalStorage), file import (via `webkitdirectory` folder loading), and exports.
- [sw.js](file:///d:/Download/Gallery-dl/mobile-image-ranker/sw.js) & [manifest.json](file:///d:/Download/Gallery-dl/mobile-image-ranker/manifest.json) - Service worker and web manifest enabling offline installation.
- [serve.py](file:///d:/Download/Gallery-dl/mobile-image-ranker/serve.py) - Python script to serve the application locally and print Wi-Fi access links.

### 🚀 How to Run the Mobile Ranker
1. Ensure your PC and mobile device are connected to the **same Wi-Fi network**.
2. Open terminal and run:
   ```bash
   python mobile-image-ranker/serve.py
   ```
3. The terminal will print local IP URLs (e.g. `http://192.168.x.x:8000/index.html`). Open the URL on your mobile browser.
4. **App Installation:** 
   - **Android (Chrome):** Tap Chrome settings (3 dots) -> "Install App" or "Add to Home Screen".
   - **iOS (Safari):** Tap the Share button -> "Add to Home Screen".
5. **Usage:** Choose "Select Folder" to load a local folder of images, and swipe **Right** to Keep, **Left** to Discard, and **Up** to mark as Pending. You can also view statistics and export results as JSON/CSV or share them.

---

## 🐍 Python Processing Scripts

All post-processing Python utilities are located in [gallery-dl/](file:///d:/Download/Gallery-dl/gallery-dl):

### 1. File Flattening
- **[dumpFile.py](file:///d:/Download/Gallery-dl/gallery-dl/dumpFile.py)**
  Recursively copies all files from a source directory into a flat destination folder. It handles filename collisions by appending numeric suffixes (e.g. `file_1.png`) to prevent data loss.

### 2. Filtering Non-Images
- **[findNonImageFile.py](file:///d:/Download/Gallery-dl/gallery-dl/findNonImageFile.py)**
  Scans a folder recursively and moves all non-image files to a target directory (preserving directory hierarchy).
- **[findNonImageFile1.py](file:///d:/Download/Gallery-dl/gallery-dl/findNonImageFile1.py)**
  Instead of copying/moving, this version creates Windows `.lnk` shortcuts to the non-image files in the target directory, preserving folder structure. (Requires `pywin32`).

### 3. Clustering Similar Images (DBSCAN)
- **[imageToVector.py](file:///d:/Download/Gallery-dl/gallery-dl/imageToVector.py)**
  Uses the pre-trained `MobileNetV2` deep learning model to extract 1D feature embeddings for all images in the input directory. Outputs normalized vectors to [image_data.pkl](file:///d:/Download/Gallery-dl/gallery-dl/image_data.pkl).
- **[imageToVector1.py](file:///d:/Download/Gallery-dl/gallery-dl/imageToVector1.py)**
  An incremental upgrade to the feature extraction script. It loads existing data from `image_data.pkl` first and skips previously processed images to save time.
- **[clusterAndRouteFile.py](file:///d:/Download/Gallery-dl/gallery-dl/clusterAndRouteFile.py)**
  Loads the embeddings from `image_data.pkl` and runs the DBSCAN clustering algorithm using cosine distance. It organizes matching duplicates/similar files into batch folders (e.g., `batch_0`, `batch_1`) and routes unclustered files to an `outliers` directory.

### 4. Wallpaper Curation & Ranking
- **[pickWallpaper.py](file:///d:/Download/Gallery-dl/gallery-dl/pickWallpaper.py)**
  An automated curation script that scores images and video frames based on:
  - Resolution (higher is better)
  - Aspect ratio similarity to target screens (Phone: 1080×2460, Laptop: 1920×1080)
  - Image properties: sharpness, composition, vibrancy, and brightness.
  
  It outputs a ranked table in the console and copies the best-scoring wallpapers to [wallpaper_winners/](file:///d:/Download/Gallery-dl/gallery-dl/wallpaper_winners).

### 5. Desktop Curation GUI
- **[batchManualProcessing6.py](file:///d:/Download/Gallery-dl/gallery-dl/batchManualProcessing6.py)**
  A Python Tkinter desktop application ("Batch Image Cleaner") allowing manual review of clustered image batches. Includes smartphone-like mouse interactions (drag-to-pan, scroll-to-zoom) for detailed inspections.
- **[batchManualProcessing/](file:///d:/Download/Gallery-dl/gallery-dl/batchManualProcessing)**
  Holds older, legacy versions of the manual curation GUI.

---

## 🤖 Guidelines for AI Agents

When interacting with this repository, agents should adhere to the following principles:
1. **Never read `gallery-dl/danbooru`:** Treat this path as blacklisted. 
2. **Context Efficiency:** Do not attempt to process lists of thousands of image filenames unless explicitly requested.
3. **Execution Safety:** When running scripts like `imageToVector.py`, be aware that TensorFlow might initialize GPU context and print standard log warnings; this is normal.
4. **Code References:** When editing or extending code in this repository, always create clickable file links using absolute URLs with the `file:///` scheme (e.g. `[app.js](file:///d:/Download/Gallery-dl/mobile-image-ranker/app.js)`). Use forward slashes.
