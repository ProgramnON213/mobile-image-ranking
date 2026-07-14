#!/usr/bin/env python3
import http.server
import socketserver
import json
import urllib.parse
import os
import pickle
import sys
import io
import threading
from pathlib import Path

# Add the current directory to sys.path to allow importing pickWallpaper
current_dir = Path(__file__).parent.resolve()
sys.path.append(str(current_dir))

from pickWallpaper import get_crops, safe_extract, IMAGE_EXTS, load_image_safe, device

try:
    import torch
    from transformers import CLIPProcessor, CLIPModel
    from PIL import Image
except ImportError as e:
    print(f"Error importing dependencies: {e}")
    sys.exit(1)

PORT = 8000
model_name = "openai/clip-vit-base-patch32"
model = None
processor = None

# Global Progress State
progress_lock = threading.Lock()
progress_state = {
    "status": "idle",       # "idle", "processing", "completed", "error"
    "current": 0,
    "total": 0,
    "message": "",
    "error_msg": "",
    "gpu_available": torch.cuda.is_available(),
    "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "None",
    "cache_status": "No active folder",
    "results": None
}

def set_progress(status=None, current=None, total=None, message=None, error_msg=None, cache_status=None, results=None):
    with progress_lock:
        if status is not None: progress_state["status"] = status
        if current is not None: progress_state["current"] = current
        if total is not None: progress_state["total"] = total
        if message is not None: progress_state["message"] = message
        if error_msg is not None: progress_state["error_msg"] = error_msg
        if cache_status is not None: progress_state["cache_status"] = cache_status
        if results is not None: progress_state["results"] = results

def lazy_load_clip():
    global model, processor
    if model is None or processor is None:
        set_progress(message="Initializing CLIP model weights...")
        print(f"Loading CLIP model on {device.upper()}...")
        processor = CLIPProcessor.from_pretrained(model_name)
        model = CLIPModel.from_pretrained(model_name, use_safetensors=True).to(device)
        print("CLIP model loaded successfully.")

class WallpaperUIRequestHandler(http.server.BaseHTTPRequestHandler):
    def end_headers(self):
        # Disable caching for active development
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)

        # 1. API Endpoints
        if path == "/api/status":
            self.handle_api_status(query)
            return
        elif path == "/api/image":
            self.handle_api_image(query)
            return
        elif path == "/api/select_folder":
            self.handle_api_select_folder()
            return
        elif path == "/api/progress":
            self.handle_api_progress()
            return

        # 2. Serve Static Frontend Files
        ui_dir = current_dir / "wallpaper-ui"
        
        if path in ["/", "/index.html"]:
            file_to_serve = ui_dir / "index.html"
            content_type = "text/html"
        elif path == "/index.css":
            file_to_serve = ui_dir / "index.css"
            content_type = "text/css"
        elif path == "/app.js":
            file_to_serve = ui_dir / "app.js"
            content_type = "application/javascript"
        else:
            self.send_error(404, "File Not Found")
            return

        if file_to_serve.exists():
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.end_headers()
            with open(file_to_serve, "rb") as f:
                self.wfile.write(f.read())
        else:
            self.send_error(404, f"Frontend File Not Found: {file_to_serve.name}")

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8')
        try:
            data = json.loads(post_data) if post_data else {}
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON data")
            return

        if path == "/api/rank":
            self.handle_api_rank(data)
        elif path == "/api/save":
            self.handle_api_save(data)
        else:
            self.send_error(404, "Endpoint Not Found")

    def handle_api_status(self, query):
        folder_str = query.get("folder", [""])[0]
        if not folder_str:
            self.send_json({"error": "No folder specified"}, status=400)
            return

        folder = Path(folder_str)
        if not folder.exists() or not folder.is_dir():
            self.send_json({
                "exists": False,
                "images": 0,
                "videos": 0,
                "has_cache": False
            })
            return

        VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".m4v", ".webm"}
        img_count = 0
        vid_count = 0

        for p in folder.rglob("*"):
            if p.is_file():
                ext = p.suffix.lower()
                if ext in IMAGE_EXTS:
                    img_count += 1
                elif ext in VIDEO_EXTS:
                    vid_count += 1

        cache_path = folder / "wallpaper_cache.pkl"
        has_cache = cache_path.exists()

        gpu_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "None"

        self.send_json({
            "exists": True,
            "images": img_count,
            "videos": vid_count,
            "has_cache": has_cache,
            "gpu_available": torch.cuda.is_available(),
            "gpu_name": gpu_name
        })

    def handle_api_select_folder(self):
        try:
            import subprocess
            # Use PowerShell's .NET FolderBrowserDialog — works correctly on Windows
            # regardless of COM apartment threading issues introduced by PyTorch/CUDA.
            ps_script = (
                "Add-Type -AssemblyName System.Windows.Forms; "
                "$d = New-Object System.Windows.Forms.FolderBrowserDialog; "
                "$d.Description = 'Select the folder containing your wallpapers'; "
                "$d.ShowNewFolderButton = $false; "
                "$null = $d.ShowDialog(); "
                "Write-Output $d.SelectedPath"
            )
            result = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                capture_output=True, text=True
            )
            folder_path = result.stdout.strip()
            self.send_json({"folder": folder_path})
        except Exception as e:
            self.send_json({"error": f"Failed to open native explorer: {e}"}, status=500)

    def handle_api_progress(self):
        with progress_lock:
            # We copy the state to return it safely
            state = dict(progress_state)
        self.send_json(state)

    def handle_api_image(self, query):
        img_path_str = query.get("path", [""])[0]
        crop_type = query.get("crop", ["center"])[0]
        device_type = query.get("device", ["phone"])[0]
        
        # Dimensions
        target_w = int(query.get("w", [1080])[0])
        target_h = int(query.get("h", [2460])[0])

        if not img_path_str:
            self.send_error(400, "Image path missing")
            return

        img_path = Path(img_path_str)
        if not img_path.exists() or not img_path.is_file():
            self.send_error(404, f"Image not found: {img_path_str}")
            return

        try:
            img = load_image_safe(img_path)
            if img is None:
                self.send_error(500, "Failed to load image")
                return

            crops = get_crops(img, target_w, target_h)
            selected_crop = None
            for name, crop_img in crops:
                if name == crop_type:
                    selected_crop = crop_img
                    break
            
            if selected_crop is None:
                selected_crop = crops[0][1]

            # Downsample preview so browser loads fast
            preview_max_w = 400
            w, h = selected_crop.size
            if w > preview_max_w:
                scale = preview_max_w / w
                selected_crop = selected_crop.resize((preview_max_w, int(h * scale)), Image.Resampling.LANCZOS)

            buffer = io.BytesIO()
            selected_crop.save(buffer, format="JPEG", quality=80)
            buffer.seek(0)

            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.end_headers()
            self.wfile.write(buffer.read())
        except Exception as e:
            self.send_error(500, f"Error cropping image: {e}")

    def handle_api_rank(self, data):
        with progress_lock:
            # Check if background thread is active
            if progress_state["status"] == "processing":
                self.send_json({"error": "An analysis is already in progress"}, status=400)
                return
        
        # Reset progress state
        set_progress(
            status="processing",
            current=0,
            total=0,
            message="Validating target folder...",
            error_msg="",
            cache_status="Checking cache files...",
            results=None
        )

        # Launch evaluation daemon thread
        t = threading.Thread(target=self.run_ranking_thread, args=(data,), daemon=True)
        t.start()
        
        self.send_json({"status": "started"})

    def run_ranking_thread(self, data):
        try:
            folder_str = data.get("folder", "")
            pos_prompts_str = data.get("pos_prompts", "")
            neg_prompts_str = data.get("neg_prompts", "")
            
            phone_w = int(data.get("phone_width", 1080))
            phone_h = int(data.get("phone_height", 2460))
            laptop_w = int(data.get("laptop_width", 1920))
            laptop_h = int(data.get("laptop_height", 1080))

            folder = Path(folder_str)
            files = [p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXTS]
            if not files:
                set_progress(status="error", error_msg="No supported images found in target folder.")
                return

            # Verify cache
            cache_path = folder / "wallpaper_cache.pkl"
            cache = {
                "phone_width": phone_w,
                "phone_height": phone_h,
                "laptop_width": laptop_w,
                "laptop_height": laptop_h,
                "entries": {}
            }

            if cache_path.exists():
                try:
                    with open(cache_path, "rb") as f:
                        loaded_cache = pickle.load(f)
                    if (loaded_cache.get("phone_width") == phone_w and
                        loaded_cache.get("phone_height") == phone_h and
                        loaded_cache.get("laptop_width") == laptop_w and
                        loaded_cache.get("laptop_height") == laptop_h):
                        cache = loaded_cache
                except Exception:
                    pass

            cached_entries = cache["entries"]
            files_to_process = []

            for file_path in files:
                try:
                    mtime = os.path.getmtime(file_path)
                except Exception:
                    mtime = 0.0
                rel_path = str(file_path.relative_to(folder))
                if rel_path in cached_entries and cached_entries[rel_path].get("mtime") == mtime:
                    continue
                files_to_process.append((file_path, rel_path, mtime))

            # Lazy load CLIP model
            set_progress(message="Initializing CLIP weights...")
            lazy_load_clip()

            # Process missing files
            if files_to_process:
                set_progress(
                    total=len(files_to_process),
                    cache_status=f"Cache rebuild needed for {len(files_to_process)} image(s)."
                )
                cache_dirty = False
                
                for idx, (file_path, rel_path, mtime) in enumerate(files_to_process):
                    set_progress(
                        current=idx + 1,
                        message=f"Extracting vectors for {file_path.name}..."
                    )
                    img = load_image_safe(file_path)
                    if img is None:
                        continue
                    
                    phone_crops = get_crops(img, phone_w, phone_h)
                    laptop_crops = get_crops(img, laptop_w, laptop_h)

                    with torch.no_grad():
                        # Phone
                        images_p = [c[1] for c in phone_crops]
                        names_p = [c[0] for c in phone_crops]
                        inputs_p = processor(images=images_p, return_tensors="pt", padding=True).to(device)
                        feats_p = model.get_image_features(**inputs_p)
                        feats_p = safe_extract(feats_p, model.visual_projection)
                        feats_p = feats_p / feats_p.norm(dim=-1, keepdim=True)

                        # Laptop
                        images_l = [c[1] for c in laptop_crops]
                        names_l = [c[0] for c in laptop_crops]
                        inputs_l = processor(images=images_l, return_tensors="pt", padding=True).to(device)
                        feats_l = model.get_image_features(**inputs_l)
                        feats_l = safe_extract(feats_l, model.visual_projection)
                        feats_l = feats_l / feats_l.norm(dim=-1, keepdim=True)

                    cached_entries[rel_path] = {
                        "mtime": mtime,
                        "phone": {
                            "names": names_p,
                            "features": feats_p.cpu()
                        },
                        "laptop": {
                            "names": names_l,
                            "features": feats_l.cpu()
                        }
                    }
                    cache_dirty = True

                if cache_dirty:
                    try:
                        with open(cache_path, "wb") as f:
                            pickle.dump(cache, f)
                    except Exception:
                        pass
            else:
                set_progress(cache_status="Cache hit: all vectors retrieved successfully.")

            # Compute Text Embeddings
            set_progress(message="Computing text prompt alignments...")
            pos_prompts = [p.strip() for p in pos_prompts_str.split(",") if p.strip()]
            neg_prompts = [p.strip() for p in neg_prompts_str.split(",") if p.strip()]

            with torch.no_grad():
                inputs = processor(text=pos_prompts + neg_prompts, return_tensors="pt", padding=True).to(device)
                text_features = model.get_text_features(**inputs)
                text_features = safe_extract(text_features, model.text_projection)
                text_features = text_features / text_features.norm(dim=-1, keepdim=True)
                num_pos = len(pos_prompts)
                pos_features = text_features[:num_pos]
                neg_features = text_features[num_pos:]

            # Run similarities
            set_progress(message="Ranking crops against prompts...")
            results_phone = []
            results_laptop = []

            for file_path in files:
                rel_path = str(file_path.relative_to(folder))
                if rel_path not in cached_entries:
                    continue

                entry = cached_entries[rel_path]
                phone_names = entry["phone"]["names"]
                phone_feats = entry["phone"]["features"].to(device)
                laptop_names = entry["laptop"]["names"]
                laptop_feats = entry["laptop"]["features"].to(device)

                with torch.no_grad():
                    # Phone
                    sim_pos_p = phone_feats @ pos_features.T
                    sim_neg_p = phone_feats @ neg_features.T
                    max_pos_p = sim_pos_p.max(dim=-1).values
                    max_neg_p = sim_neg_p.max(dim=-1).values
                    scores_p = (max_pos_p - max_neg_p).cpu().numpy()
                    best_idx_p = scores_p.argmax()
                    best_score_p = float(scores_p[best_idx_p])

                    # Laptop
                    sim_pos_l = laptop_feats @ pos_features.T
                    sim_neg_l = laptop_feats @ neg_features.T
                    max_pos_l = sim_pos_l.max(dim=-1).values
                    max_neg_l = sim_neg_l.max(dim=-1).values
                    scores_l = (max_pos_l - max_neg_l).cpu().numpy()
                    best_idx_l = scores_l.argmax()
                    best_score_l = float(scores_l[best_idx_l])

                    results_phone.append({
                        "path": str(file_path.resolve()),
                        "name": file_path.name,
                        "score": best_score_p,
                        "crop_type": phone_names[best_idx_p],
                        "all_crops": phone_names
                    })

                    results_laptop.append({
                        "path": str(file_path.resolve()),
                        "name": file_path.name,
                        "score": best_score_l,
                        "crop_type": laptop_names[best_idx_l],
                        "all_crops": laptop_names
                    })

            results_phone.sort(key=lambda x: x["score"], reverse=True)
            results_laptop.sort(key=lambda x: x["score"], reverse=True)

            set_progress(
                status="completed",
                message="Processing completed!",
                results={
                    "phone": results_phone,
                    "laptop": results_laptop
                }
            )
        except Exception as e:
            set_progress(status="error", error_msg=str(e))

    def handle_api_save(self, data):
        output_dir_str = data.get("output_dir", "./wallpaper_winners")
        selections = data.get("selections", [])

        if not selections:
            self.send_json({"error": "No selections received"}, status=400)
            return

        workspace_root = Path(__file__).parent.parent.resolve()
        out_path = Path(output_dir_str).resolve()
        
        # Prevent path traversal by constraining output folder inside the workspace
        try:
            out_path.relative_to(workspace_root)
        except ValueError:
            out_path = workspace_root / "gallery-dl" / "wallpaper_winners"

        out_path.mkdir(parents=True, exist_ok=True)
        
        success_count = 0
        
        for item in selections:
            try:
                img_path = Path(item["path"]).resolve()
                device_type = item["device"]
                crop_type = item["crop_type"]
                w = int(item["w"])
                h = int(item["h"])
                index = int(item["index"])
            except (ValueError, KeyError, TypeError):
                # Skip invalid selection items gracefully
                continue

            # Ensure device_type and crop_type are safe directory names
            if device_type not in ("phone", "laptop"):
                continue
            if crop_type not in ("left", "center", "right", "top", "bottom"):
                continue
            if w <= 0 or h <= 0 or index < 0:
                continue

            if not img_path.exists() or not img_path.is_file():
                continue

            device_folder = out_path / device_type
            device_folder.mkdir(exist_ok=True)

            ext = img_path.suffix
            out_file = device_folder / f"{device_type}_{index:02d}_{img_path.stem}{ext}"

            try:
                img = load_image_safe(img_path)
                if img is None:
                    continue

                crops = get_crops(img, w, h)
                for name, crop_img in crops:
                    if name == crop_type:
                        crop_img.save(out_file)
                        success_count += 1
                        break
            except Exception as e:
                print(f"Error saving {img_path.name}: {e}")

        self.send_json({"message": f"Successfully cropped and saved {success_count} wallpapers!"})

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

def run():
    socketserver.TCPServer.allow_reuse_address = True
    print(f"Starting Wallpaper UI server at http://localhost:{PORT}")
    with socketserver.TCPServer(("", PORT), WallpaperUIRequestHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server. Goodbye!")

if __name__ == "__main__":
    run()
