# Gallery-DL & Mobile Image Ranker - Quick Start Guide

This directory contains tools for downloading images (`gallery-dl`), reviewing & sorting downloaded images on mobile/desktop (`mobile-image-ranker`), AI wallpaper selection (`gallery-dl/pickWallpaper.py`), and managing discarded downloads (`delete_discarded.py`).

---

## ⚡ Quick Start (No Manual Activation Needed)

Double-click **[RUNME.bat](file:///d:/Download/Gallery-dl/RUNME.bat)** in Windows Explorer, or run:

```cmd
.\RUNME.bat
```

This presents an interactive menu to launch any tool with `.venv` pre-loaded automatically.

---

## ❓ What happens if you do NOT activate `.venv`?

If you run `python script.py` directly without activating `.venv` (or without specifying `.\.venv\Scripts\python.exe`):

1. **Missing Dependencies Error**: Windows will run your system Python (`Python 3.14`), which does **not** have the CUDA PyTorch, Transformers, Pillow, or Scikit-Learn packages installed.
   - Example Error: `ModuleNotFoundError: No module named 'torch'`
2. **GPU Acceleration Lost**: System Python will fail to access your **NVIDIA GeForce RTX 3050 Ti GPU** drivers configured in `.venv`.

---

## 🛠️ Direct Commands (Alternative to RUNME.bat)

Instead of activating `.venv` first, you can run scripts directly by referencing `.\.venv\Scripts\python.exe`:

### 1. Mobile Tinder Swipe PWA Server
```powershell
.\.venv\Scripts\python.exe mobile-image-ranker/serve.py
```
*Access on phone/browser via local IP output on port 8000.*

### 2. GPU-Accelerated Wallpaper AI Ranker UI
```powershell
.\.venv\Scripts\python.exe gallery-dl/pickWallpaper_ui.py
```

### 3. Delete Discarded Downloads
```powershell
.\.venv\Scripts\python.exe delete_discarded.py
```

### 4. Download Media via Gallery-DL
```powershell
.\.venv\Scripts\gallery-dl.exe --config gallery-dl.conf "https://example.com/gallery"
```
