#!/usr/bin/env python3
"""
wallpaper_picker.py
───────────────────
Scans a folder of images and videos, scores each file for suitability
as a phone (1080×2460) or laptop (1920×1080 / 16:9) wallpaper, prints
a ranked table, and copies the top pick for each device to an output folder.

Usage:
    python wallpaper_picker.py <folder> [--output ./wallpaper_winners]

Dependencies:
    pip install pillow opencv-python numpy rich
    # ffmpeg + ffprobe must be on your PATH for video support
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from rich.console import Console
from rich.table import Table

# ─── Device Targets ───────────────────────────────────────────────────────────

PHONE_TARGET  = (1080, 2460)   # width × height (portrait)
LAPTOP_TARGET = (1920, 1080)   # width × height (landscape)

# ─── Supported Extensions ─────────────────────────────────────────────────────

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".tiff", ".tif", ".bmp"}
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".m4v"}

# ─── Scoring Weights (must sum to 1.0) ────────────────────────────────────────

WEIGHTS = {
    "resolution":   0.25,
    "aspect_ratio": 0.25,
    "sharpness":    0.20,
    "composition":  0.15,
    "vibrancy":     0.10,
    "brightness":   0.05,
}

console = Console()


# ══════════════════════════════════════════════════════════════════════════════
#  File Loading
# ══════════════════════════════════════════════════════════════════════════════

def extract_video_frame(video_path: Path) -> np.ndarray | None:
    """Extract a representative frame at 10 % of the video duration via ffmpeg."""
    try:
        # ── 1. get duration ──────────────────────────────────────────────────
        probe = subprocess.run(
            ["ffprobe", "-v", "error",
             "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1",
             str(video_path)],
            capture_output=True, text=True, timeout=10,
        )
        duration = float(probe.stdout.strip())
        seek_time = max(duration * 0.10, 0)

        # ── 2. extract frame ─────────────────────────────────────────────────
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp_path = tmp.name

        subprocess.run(
            ["ffmpeg", "-ss", str(seek_time), "-i", str(video_path),
             "-vframes", "1", "-q:v", "2", tmp_path, "-y"],
            capture_output=True, timeout=15,
        )

        frame = cv2.imread(tmp_path)
        os.unlink(tmp_path)
        return frame

    except Exception as exc:
        console.print(f"[yellow]⚠  Frame extraction failed for {video_path.name}: {exc}[/yellow]")
        return None


def load_file(path: Path, is_video: bool) -> tuple[np.ndarray | None, tuple[int, int] | None]:
    """Return (BGR frame, (width, height)) or (None, None) on failure."""
    if is_video:
        frame = extract_video_frame(path)
        if frame is None:
            return None, None
        h, w = frame.shape[:2]
        return frame, (w, h)

    try:
        pil_img = Image.open(path).convert("RGB")
        w, h    = pil_img.size
        frame   = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        return frame, (w, h)
    except Exception as exc:
        console.print(f"[yellow]⚠  Could not load {path.name}: {exc}[/yellow]")
        return None, None


def get_video_metadata(path: Path) -> dict:
    """Return {duration, width, height, codec} for a video file."""
    try:
        probe = subprocess.run(
            ["ffprobe", "-v", "error",
             "-show_entries", "format=duration:stream=width,height,codec_name",
             "-of", "json", str(path)],
            capture_output=True, text=True, timeout=10,
        )
        data     = json.loads(probe.stdout)
        duration = float(data.get("format", {}).get("duration", 0))
        streams  = data.get("streams", [])
        vs       = next((s for s in streams if "width" in s), {})
        return {
            "duration": duration,
            "width":    vs.get("width", 0),
            "height":   vs.get("height", 0),
            "codec":    vs.get("codec_name", "unknown"),
        }
    except Exception:
        return {"duration": 0, "width": 0, "height": 0, "codec": "unknown"}


# ══════════════════════════════════════════════════════════════════════════════
#  Metric Functions  (each returns a float in [0.0, 1.0])
# ══════════════════════════════════════════════════════════════════════════════

def score_resolution(w: int, h: int, tw: int, th: int) -> float:
    """
    Full marks when the image meets or exceeds the target resolution.
    Partial marks when it is within 80 % of the target (still usable).
    """
    min_w, min_h = tw * 0.80, th * 0.80

    # Accept either portrait or landscape orientation
    fits = (w >= min_w and h >= min_h) or (h >= min_w and w >= min_h)
    if not fits:
        return min((w * h) / (min_w * min_h), 1.0) * 0.50

    # Reward higher-than-target resolution, capped at 2× target pixels
    pixel_ratio = min((w * h) / (tw * th), 2.0)
    return 0.50 + (pixel_ratio / 2.0) * 0.50


def score_aspect_ratio(w: int, h: int, tw: int, th: int) -> float:
    """
    Penalises the need for heavy cropping.
    Both portrait and landscape orientations are considered.
    """
    if h == 0 or w == 0:
        return 0.0
    target = tw / th
    ratios = [w / h, h / w]
    best_delta = min(abs(r - target) / target for r in ratios)
    # A 50 % ratio deviation → 0 score
    return max(0.0, 1.0 - best_delta / 0.50)


def score_sharpness(frame: np.ndarray) -> float:
    """
    Laplacian variance as a proxy for focus quality.
    Empirically: < 50 = blurry, > 1000 = very sharp.
    """
    gray     = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    variance = cv2.Laplacian(gray, cv2.CV_64F).var()
    return min(variance / 1000.0, 1.0)


def score_composition(frame: np.ndarray) -> float:
    """
    Edge density in the central 60 % of the frame.
    Rewards balanced composition; penalises empty or cluttered centres.
    Peak reward at ~0.15 edge density.
    """
    h, w   = frame.shape[:2]
    y1, y2 = int(h * 0.20), int(h * 0.80)
    x1, x2 = int(w * 0.20), int(w * 0.80)
    centre = frame[y1:y2, x1:x2]
    gray   = cv2.cvtColor(centre, cv2.COLOR_BGR2GRAY)
    edges  = cv2.Canny(gray, 50, 150)
    density = edges.mean() / 255.0

    if density <= 0.30:
        return max(0.0, 1.0 - abs(density - 0.15) / 0.15)
    return max(0.0, 1.0 - (density - 0.30) / 0.70)


def score_brightness(frame: np.ndarray) -> float:
    """
    Ideal mean luminance: 80–180 (out of 255).
    Linearly penalises very dark (< 80) or blown-out (> 180) images.
    """
    mean = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).mean()
    if 80 <= mean <= 180:
        return 1.0
    if mean < 80:
        return max(0.0, mean / 80.0)
    return max(0.0, 1.0 - (mean - 180) / 75.0)


def score_vibrancy(frame: np.ndarray) -> float:
    """Mean HSV saturation — higher = more colourful / vibrant."""
    saturation = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)[:, :, 1].mean()
    return saturation / 255.0


# ══════════════════════════════════════════════════════════════════════════════
#  Live Wallpaper Flag (videos only)
# ══════════════════════════════════════════════════════════════════════════════

def live_wallpaper_label(meta: dict) -> str:
    duration = meta.get("duration", 0)
    if duration == 0:
        return "❓ Unknown"
    if duration <= 30:
        return "✅ Great"
    if duration <= 120:
        return "⚠  OK (long)"
    return "❌ Too long"


# ══════════════════════════════════════════════════════════════════════════════
#  Per-file Analysis
# ══════════════════════════════════════════════════════════════════════════════

def analyse(path: Path) -> dict | None:
    """Analyse one image or video and return a results dict, or None on failure."""
    is_video    = path.suffix.lower() in VIDEO_EXTS
    frame, dims = load_file(path, is_video)
    if frame is None:
        return None

    w, h    = dims
    results = {"path": path, "is_video": is_video, "width": w, "height": h}

    for device, (tw, th) in [("phone", PHONE_TARGET), ("laptop", LAPTOP_TARGET)]:
        s_res  = score_resolution(w, h, tw, th)
        s_ar   = score_aspect_ratio(w, h, tw, th)
        s_sh   = score_sharpness(frame)
        s_comp = score_composition(frame)
        s_br   = score_brightness(frame)
        s_vib  = score_vibrancy(frame)

        total = (
            s_res  * WEIGHTS["resolution"]   +
            s_ar   * WEIGHTS["aspect_ratio"]  +
            s_sh   * WEIGHTS["sharpness"]     +
            s_comp * WEIGHTS["composition"]   +
            s_vib  * WEIGHTS["vibrancy"]      +
            s_br   * WEIGHTS["brightness"]
        )

        results[device] = {
            "resolution":   s_res,
            "aspect_ratio": s_ar,
            "sharpness":    s_sh,
            "composition":  s_comp,
            "brightness":   s_br,
            "vibrancy":     s_vib,
            "total":        total,
        }

    if is_video:
        meta = get_video_metadata(path)
        results["live_label"] = live_wallpaper_label(meta)

    return results


# ══════════════════════════════════════════════════════════════════════════════
#  Output Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _bar(score: float, width: int = 5) -> str:
    filled = round(score * width)
    return "█" * filled + "░" * (width - filled)


def print_tables(results: list[dict]) -> None:
    for device, target in [("phone", PHONE_TARGET), ("laptop", LAPTOP_TARGET)]:
        ranked  = sorted(results, key=lambda r: r[device]["total"], reverse=True)
        icon    = "📱" if device == "phone" else "💻"
        title   = f"{icon} {device.capitalize()} Rankings  (target {target[0]}×{target[1]})"

        tbl = Table(title=title, show_lines=True, header_style="bold cyan")
        tbl.add_column("#",      width=4,  style="bold")
        tbl.add_column("File",   min_width=22)
        tbl.add_column("Size",   width=12)
        tbl.add_column("Score",  width=16)
        tbl.add_column("Res",    width=10)
        tbl.add_column("Ratio",  width=10)
        tbl.add_column("Sharp",  width=10)
        tbl.add_column("Comp",   width=10)
        tbl.add_column("Vibe",   width=10)
        tbl.add_column("Bright", width=10)
        if device == "phone":
            tbl.add_column("Live?", width=14)

        for rank, r in enumerate(ranked, 1):
            s          = r[device]
            is_winner  = rank == 1
            row_style  = "bold green" if is_winner else ""
            rank_label = "🏆 " if is_winner else f"{rank:>2}."

            row = [
                rank_label,
                r["path"].name,
                f"{r['width']}×{r['height']}",
                f"{_bar(s['total'], 8)} {s['total']:.2f}",
                f"{_bar(s['resolution'])}   {s['resolution']:.2f}",
                f"{_bar(s['aspect_ratio'])} {s['aspect_ratio']:.2f}",
                f"{_bar(s['sharpness'])}    {s['sharpness']:.2f}",
                f"{_bar(s['composition'])}  {s['composition']:.2f}",
                f"{_bar(s['vibrancy'])}     {s['vibrancy']:.2f}",
                f"{_bar(s['brightness'])}   {s['brightness']:.2f}",
            ]

            if device == "phone":
                row.append(r.get("live_label", "—") if r["is_video"] else "—")

            tbl.add_row(*row, style=row_style)

        console.print()
        console.print(tbl)


def copy_winners(results: list[dict], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    for device in ("phone", "laptop"):
        winner = max(results, key=lambda r: r[device]["total"])
        src    = winner["path"]
        dst    = output_dir / f"wallpaper_{device}{src.suffix}"
        shutil.copy2(src, dst)
        score  = winner[device]["total"]
        console.print(
            f"[bold green]✅ {device.capitalize()} winner:[/bold green] "
            f"{src.name}  (score {score:.2f})  →  {dst}"
        )


# ══════════════════════════════════════════════════════════════════════════════
#  Entry Point
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    global PHONE_TARGET, LAPTOP_TARGET
    parser = argparse.ArgumentParser(
        description="Pick the best wallpaper candidates for phone and laptop.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("folder",   type=Path, help="Folder containing your image/video files")
    parser.add_argument("--output", "-o", type=Path,
                        default=Path("./wallpaper_winners"),
                        help="Destination folder for the winning files (default: ./wallpaper_winners)")
    parser.add_argument("--phone-width", type=int, default=1080, help="Phone target width (default: 1080)")
    parser.add_argument("--phone-height", type=int, default=2460, help="Phone target height (default: 2460)")
    parser.add_argument("--laptop-width", type=int, default=1920, help="Laptop target width (default: 1920)")
    parser.add_argument("--laptop-height", type=int, default=1080, help="Laptop target height (default: 1080)")
    args = parser.parse_args()

    PHONE_TARGET = (args.phone_width, args.phone_height)
    LAPTOP_TARGET = (args.laptop_width, args.laptop_height)

    if not args.folder.exists():
        console.print(f"[red]❌  Folder not found: {args.folder}[/red]")
        sys.exit(1)

    # ── discover ──────────────────────────────────────────────────────────────
    all_exts = IMAGE_EXTS | VIDEO_EXTS
    files    = [p for p in args.folder.rglob("*")
                if p.is_file() and p.suffix.lower() in all_exts]

    if not files:
        console.print("[red]❌  No supported image or video files found.[/red]")
        sys.exit(1)

    console.print(f"\n[bold]Found {len(files)} file(s) — analysing …[/bold]\n")

    # ── analyse ───────────────────────────────────────────────────────────────
    results = []
    for f in files:
        console.print(f"  🔍 {f.name}", end="  ")
        r = analyse(f)
        if r:
            results.append(r)
            console.print(
                f"phone [cyan]{r['phone']['total']:.2f}[/cyan]  "
                f"laptop [cyan]{r['laptop']['total']:.2f}[/cyan]"
            )
        else:
            console.print("[yellow]skipped[/yellow]")

    if not results:
        console.print("[red]❌  No files could be analysed.[/red]")
        sys.exit(1)

    # ── rank & display ────────────────────────────────────────────────────────
    print_tables(results)

    # ── copy winners ─────────────────────────────────────────────────────────
    console.print()
    copy_winners(results, args.output)
    console.print(f"\n[bold green]Done!  Winners saved to: {args.output.resolve()}[/bold green]\n")


if __name__ == "__main__":
    main()