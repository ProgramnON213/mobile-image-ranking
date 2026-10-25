#!/usr/bin/env python3
"""
Batch Image Cleaner v7 Pro
Local GPU-accelerated desktop web app for rapid image set inspection and cleanup.
"""

import os
import sys
import json
import io
import time
import socket
import threading
import subprocess
import urllib.parse
import http.server
import socketserver
from pathlib import Path
from PIL import Image

# Supported image extensions
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif', '.avif'}

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Global initial folder passed via CLI
INITIAL_FOLDER = None

# Thread-safe Thumbnail In-Memory LRU Cache
CACHE_LOCK = threading.Lock()
THUMBNAIL_CACHE = {}  # (path, mtime, size) -> (bytes, content_type)
MAX_CACHE_ENTRIES = 2000

# Folder metadata cache: (folder_str, folder_mtime) -> dict
BATCH_CACHE = {}

def get_cached_thumbnail(file_path, target_size=400):
    try:
        stat = os.stat(file_path)
        cache_key = (file_path, stat.st_mtime, target_size)
    except Exception:
        return None, None

    with CACHE_LOCK:
        if cache_key in THUMBNAIL_CACHE:
            return THUMBNAIL_CACHE[cache_key]

    try:
        with Image.open(file_path) as img:
            # Convert RGBA/P to RGB for JPEG encoding if necessary
            if img.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', img.size, (24, 28, 39))
                background.paste(img, mask=img.split()[-1])
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            img.thumbnail((target_size, target_size), Image.Resampling.BILINEAR)
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=85, optimize=True)
            data = buffer.getvalue()
            content_type = 'image/jpeg'

            with CACHE_LOCK:
                if len(THUMBNAIL_CACHE) >= MAX_CACHE_ENTRIES:
                    # Pop oldest item
                    THUMBNAIL_CACHE.pop(next(iter(THUMBNAIL_CACHE)))
                THUMBNAIL_CACHE[cache_key] = (data, content_type)

            return data, content_type
    except Exception as e:
        print(f"[Error] Failed to generate thumbnail for {file_path}: {e}")
        return None, None


class BatchProcessorHandler(http.server.BaseHTTPRequestHandler):
    ui_dir = Path(__file__).parent.resolve() / "batch-ui"

    def log_message(self, format, *args):
        # Suppress routine GET logging for image thumbnails to keep terminal clean
        if "/api/thumbnail" in args[0] or "/api/raw_image" in args[0]:
            return
        super().log_message(format, *args)

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # API Routes
        if path == "/api/init_info":
            self.send_json({"initial_folder": INITIAL_FOLDER})
            return

        if path == "/api/select_folder":
            self.handle_select_folder()
            return

        if path == "/api/scan":
            self.handle_scan(query)
            return

        if path == "/api/batch":
            self.handle_batch(query)
            return

        if path == "/api/thumbnail":
            self.handle_thumbnail(query)
            return

        if path == "/api/raw_image":
            self.handle_raw_image(query)
            return

        if path == "/api/open_in_explorer":
            self.handle_open_in_explorer(query)
            return

        # Static Frontend Files
        self.serve_static(path)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/delete":
            self.handle_delete()
            return

        self.send_error(404, "Not Found")

    def serve_static(self, req_path):
        if req_path in ('/', ''):
            file_path = self.ui_dir / "index.html"
        else:
            rel_path = req_path.lstrip('/')
            file_path = self.ui_dir / rel_path

        if not file_path.exists() or not file_path.is_file():
            self.send_error(404, "File not found")
            return

        # Determine Mime Type
        ext = file_path.suffix.lower()
        mime_types = {
            '.html': 'text/html; charset=utf-8',
            '.css': 'text/css; charset=utf-8',
            '.js': 'application/javascript; charset=utf-8',
            '.json': 'application/json',
            '.png': 'image/png',
            '.svg': 'image/svg+xml',
            '.ico': 'image/x-icon'
        }
        content_type = mime_types.get(ext, 'application/octet-stream')

        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, f"Error reading file: {e}")

    def handle_select_folder(self):
        try:
            ps_script = (
                "Add-Type -AssemblyName System.Windows.Forms; "
                "$d = New-Object System.Windows.Forms.FolderBrowserDialog; "
                "$d.Description = 'Select Root Folder to Scan for Albums'; "
                "$d.ShowNewFolderButton = $false; "
                "$null = $d.ShowDialog(); "
                "Write-Output $d.SelectedPath"
            )
            res = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                capture_output=True, text=True
            )
            folder_path = res.stdout.strip()
            self.send_json({"folder": folder_path})
        except Exception as e:
            self.send_json({"error": f"Failed to open native picker: {e}"}, status=500)

    def handle_scan(self, query):
        folder_str = query.get("folder", [""])[0]
        if not folder_str:
            self.send_json({"error": "No folder specified"}, status=400)
            return

        root_path = Path(folder_str)
        if not root_path.exists() or not root_path.is_dir():
            self.send_json({"error": f"Directory does not exist: {folder_str}"}, status=404)
            return

        batches = []
        try:
            for dirpath, _, filenames in os.walk(folder_str):
                imgs = [f for f in filenames if Path(f).suffix.lower() in IMAGE_EXTENSIONS]
                if len(imgs) > 1:
                    dir_name = os.path.basename(dirpath)
                    try:
                        rel_path = os.path.relpath(dirpath, folder_str)
                    except ValueError:
                        rel_path = dir_name

                    batches.append({
                        "name": dir_name if dir_name else folder_str,
                        "rel_path": rel_path if rel_path != "." else dir_name,
                        "path": dirpath,
                        "count": len(imgs)
                    })

            self.send_json({"root": folder_str, "batches": batches})
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.send_json({"error": f"Failed during scan: {e}"}, status=500)

    def handle_batch(self, query):
        folder_str = query.get("path", [""])[0]
        if not folder_str:
            self.send_json({"error": "No batch path specified"}, status=400)
            return

        folder_path = Path(folder_str)
        if not folder_path.exists() or not folder_path.is_dir():
            self.send_json({"error": "Directory not found"}, status=404)
            return

        try:
            folder_mtime = os.path.getmtime(folder_str)
            cache_key = (folder_str, folder_mtime)
            with CACHE_LOCK:
                if cache_key in BATCH_CACHE:
                    self.send_json(BATCH_CACHE[cache_key])
                    return
        except Exception:
            pass

        images = []
        try:
            for item in os.listdir(folder_path):
                ext = Path(item).suffix.lower()
                if ext in IMAGE_EXTENSIONS:
                    full_p = os.path.join(folder_str, item)
                    try:
                        size_bytes = os.path.getsize(full_p)
                        # Fast header read for dimensions
                        with Image.open(full_p) as img:
                            w, h = img.size
                    except Exception:
                        size_bytes = 0
                        w, h = 0, 0

                    images.append({
                        "name": item,
                        "path": full_p,
                        "size": size_bytes,
                        "size_str": self.format_size(size_bytes),
                        "width": w,
                        "height": h
                    })

            result = {
                "folder": folder_str,
                "name": os.path.basename(folder_str),
                "images": images
            }

            try:
                with CACHE_LOCK:
                    BATCH_CACHE[cache_key] = result
            except Exception:
                pass

            self.send_json(result)
        except Exception as e:
            self.send_json({"error": f"Failed to list images: {e}"}, status=500)

    def handle_thumbnail(self, query):
        img_path = query.get("path", [""])[0]
        target_size = int(query.get("size", [400])[0])

        if not img_path or not os.path.isfile(img_path):
            self.send_error(404, "Image not found")
            return

        data, content_type = get_cached_thumbnail(img_path, target_size)
        if data is None:
            self.send_error(500, "Thumbnail generation failed")
            return

        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'public, max-age=86400')
        self.end_headers()
        self.wfile.write(data)

    def handle_raw_image(self, query):
        img_path = query.get("path", [""])[0]
        if not img_path or not os.path.isfile(img_path):
            self.send_error(404, "Image not found")
            return

        ext = Path(img_path).suffix.lower()
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.webp': 'image/webp',
            '.bmp': 'image/bmp',
            '.gif': 'image/gif'
        }
        content_type = mime_types.get(ext, 'application/octet-stream')

        try:
            with open(img_path, 'rb') as f:
                content = f.read()

            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, f"Error streaming image: {e}")

    def handle_delete(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            payload = json.loads(body.decode('utf-8'))
            paths = payload.get("paths", [])
            use_recycle = payload.get("recycle", True)

            deleted_count = 0
            errors = []

            for p in paths:
                if not os.path.exists(p):
                    continue

                deleted_success = False
                if use_recycle:
                    # Windows Native Recycle Bin via PowerShell Microsoft.VisualBasic assembly
                    try:
                        escaped_p = p.replace("'", "''")
                        ps_cmd = (
                            f"Add-Type -AssemblyName Microsoft.VisualBasic; "
                            f"[Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile('{escaped_p}', 'OnlyErrorDialogs', 'SendToRecycleBin')"
                        )
                        res = subprocess.run(
                            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
                            capture_output=True, text=True
                        )
                        if res.returncode == 0 and not os.path.exists(p):
                            deleted_success = True
                    except Exception as e:
                        errors.append(f"Recycle error for {os.path.basename(p)}: {e}")

                # Fallback to permanent delete if recycle was disabled or failed
                if not deleted_success:
                    try:
                        os.remove(p)
                        deleted_success = True
                    except Exception as e:
                        errors.append(f"Delete failed for {os.path.basename(p)}: {e}")

                if deleted_success:
                    deleted_count += 1

            with CACHE_LOCK:
                BATCH_CACHE.clear()

            self.send_json({
                "success": len(errors) == 0,
                "deleted": deleted_count,
                "errors": errors
            })
        except Exception as e:
            self.send_json({"error": f"Invalid delete request: {e}"}, status=500)

    def handle_open_in_explorer(self, query):
        target_path = query.get("path", [""])[0]
        if target_path and os.path.exists(target_path):
            try:
                # Open Windows Explorer and select the specific file
                subprocess.Popen(f'explorer /select,"{os.path.normpath(target_path)}"')
                self.send_json({"success": True})
            except Exception as e:
                self.send_json({"error": str(e)}, status=500)
        else:
            self.send_json({"error": "Path not found"}, status=404)

    def format_size(self, size_bytes):
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.2f} MB"

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))


class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def find_free_port(start_port=8008, max_attempts=50):
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('localhost', port)) != 0:
                return port
    return start_port


def launch_in_app_mode(url):
    """
    Launch Chrome or Edge in standalone '--app' mode for a borderless native-feel window.
    Falls back to standard browser tab.
    """
    import webbrowser

    edge_paths = [
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
    ]
    for edge in edge_paths:
        if os.path.isfile(edge):
            try:
                subprocess.Popen([edge, f"--app={url}"])
                return
            except Exception:
                pass

    chrome_paths = [
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
    ]
    for chrome in chrome_paths:
        if os.path.isfile(chrome):
            try:
                subprocess.Popen([chrome, f"--app={url}"])
                return
            except Exception:
                pass

    webbrowser.open(url)


def main():
    global INITIAL_FOLDER
    import argparse
    parser = argparse.ArgumentParser(description="Batch Image Cleaner v7 Pro")
    parser.add_argument("--folder", "-f", help="Initial directory to scan for albums")
    parser.add_argument("--port", "-p", type=int, default=None, help="Server port (default: auto-detected from 8008)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically launch browser window")
    args = parser.parse_args()

    if args.folder:
        folder_p = os.path.abspath(args.folder)
        if os.path.isdir(folder_p):
            INITIAL_FOLDER = folder_p
            print(f"[*] Initial scan target set: {INITIAL_FOLDER}")

    port = args.port if args.port else find_free_port(8008)
    server_url = f"http://localhost:{port}"

    server = ThreadingHTTPServer(("localhost", port), BatchProcessorHandler)
    print("=" * 60)
    print(f"[*] Batch Image Cleaner v7 Pro running at: {server_url}")
    print("=" * 60)

    if not args.no_browser:
        # Launch browser in separate thread to let server start
        threading.Timer(0.6, lambda: launch_in_app_mode(server_url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Shutting down server. Goodbye!")
        server.server_close()


if __name__ == "__main__":
    main()
