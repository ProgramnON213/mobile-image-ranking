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

### 📐 Architectural & Privacy Model
The Mobile Image Ranker is designed as a **100% Client-Side Progressive Web App (PWA)**:
* **Zero Uploads:** Your images are loaded locally into the browser memory using the modern `webkitdirectory` API. They are never transmitted to any external server, ensuring complete privacy.
* **Offline Capability:** Once the application files are cached, the PWA works completely offline with zero cell service or internet connection.
* **Storage Footprint:** No server-side storage or database runs on the mobile device. Ratings and sorting state are cached locally in the browser's persistent storage.

### ✨ Key Features
* **Tinder-like Gestures:** Smooth touch drag physics with rotative offset translation:
  - **Swipe Right:** Keep image.
  - **Swipe Left:** Discard image.
  - **Swipe Up:** Mark as Pending.
* **Navigation & Correction:** Includes an **Undo** capability to retrieve the previous rated card if an accidental swipe occurs. Manual buttons are also provided if swiping gestures are not preferred.
* **Smart Zoom & Inspection:** Tapping the active card opens a high-fidelity zoom modal. It supports pinch-to-zoom and double-tap zoom (2.5x magnification), and drag-to-pan touch mechanics to inspect fine image details before rating.
* **Session Restore (Resume Engine):** Tracks rated items using a unique hash combination of `filename + file_size` stored in the browser's `localStorage`. If you close the app or refresh, you can reload the folder/files and instantly resume from the first unrated card.
* **Multiple Export Formats:** Export the session ratings to JSON, CSV, or share the summary via the Web Share API.

### 🛠️ Key Components
* [index.html](file:///d:/Download/Gallery-dl/mobile-image-ranker/index.html) - Structure for the Welcome panel, Tinder card deck viewport, visual indicators (KEEP, DISCARD, PENDING), and the zoom/inspect overlays.
* [index.css](file:///d:/Download/Gallery-dl/mobile-image-ranker/index.css) - Vanilla CSS establishing a responsive glassmorphic UI, card stack offsets, dragging animations, and fluid dark theme palettes.
* [app.js](file:///d:/Download/Gallery-dl/mobile-image-ranker/app.js) - Core engine driving touch physics, zoom/pan calculations, LocalStorage interactions, session tracking, and file exports.
* [sw.js](file:///d:/Download/Gallery-dl/mobile-image-ranker/sw.js) & [manifest.json](file:///d:/Download/Gallery-dl/mobile-image-ranker/manifest.json) - Service worker caching patterns and Web App Manifest defining home screen installation properties.
* [serve.py](file:///d:/Download/Gallery-dl/mobile-image-ranker/serve.py) - Python simple HTTP server with custom CORS headers and zero-caching rules, outputting local network IP links for easy connection.

### 🚀 How to Run the Mobile Ranker

#### Method A: PC-Hosted Server (Local Wi-Fi)
1. Ensure your PC and mobile device are connected to the **same Wi-Fi network**.
2. Open terminal in the repository root and run:
   ```bash
   python mobile-image-ranker/serve.py
   ```
3. The terminal will print local network URLs (e.g., `http://192.168.1.145:8000/index.html`). Open the URL on your phone's browser.
4. **Install as App:**
   - **Android (Chrome):** Tap Chrome settings (3 dots) -> "Install App" or "Add to Home Screen".
   - **iOS (Safari):** Tap the Share button -> "Add to Home Screen".
5. Load your files using **Select Folder** (via folder directory picker API) or **Select Multiple Images** and start swiping.

#### Method B: Zero-PC Cloud Hosting (100% Free & Private)
Since the app is 100% client-side, you do not need a running PC backend to use it. You can host it statically on the cloud:
1. **Netlify Drop:** Drag and drop the [mobile-image-ranker/](file:///d:/Download/Gallery-dl/mobile-image-ranker) directory into [Netlify Drop](https://app.netlify.com/drop) to immediately host the app on a secure HTTPS domain.
2. **GitHub Pages:** Commit the folder to a GitHub repository and enable GitHub Pages under settings.
3. Access the secure HTTPS URL on your phone, click "Add to Home Screen", and run the app offline anywhere.

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
