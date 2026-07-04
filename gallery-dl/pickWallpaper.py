#!/usr/bin/env python3
"""
pickWallpaper.py
────────────────
Zero-Shot CLIP Classification script to rank wallpapers.
Evaluates images for Phone and Laptop aspect ratios, applies smart cropping,
and uses AI to rank them based on a dark, aesthetic anime theme.
"""

import argparse
import os
import pickle
import shutil
import sys
from pathlib import Path
from PIL import Image
from rich.console import Console
from rich.table import Table

console = Console()

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".tiff", ".tif", ".bmp"}

try:
    import torch
    from transformers import CLIPProcessor, CLIPModel
except ImportError:
    console.print("[red]:x: PyTorch or Transformers not installed.[/red]")
    console.print("Please install them using:")
    console.print("pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121")
    console.print("pip install transformers")
    sys.exit(1)

# Device Configuration
device = "cuda" if torch.cuda.is_available() else "cpu"

def get_crops(pil_img, target_w, target_h):
    """
    Given a PIL image and target dimensions, return up to 3 cropped PIL images 
    (e.g. left, center, right OR top, center, bottom) that match the target aspect ratio,
    maximizing the area.
    """
    img_w, img_h = pil_img.size
    target_ratio = target_w / target_h
    img_ratio = img_w / img_h

    # We want to crop a rectangle of aspect ratio `target_ratio` from `img_w` x `img_h`
    if img_ratio > target_ratio:
        # Image is wider than target. Fit height, crop width.
        crop_h = img_h
        crop_w = int(img_h * target_ratio)
        
        # 3 horizontal crops
        c1 = pil_img.crop((0, 0, crop_w, crop_h)) # Left
        c2 = pil_img.crop(((img_w - crop_w) // 2, 0, (img_w + crop_w) // 2, crop_h)) # Center
        c3 = pil_img.crop((img_w - crop_w, 0, img_w, crop_h)) # Right
        
        return [("left", c1), ("center", c2), ("right", c3)]
    else:
        # Image is taller than target. Fit width, crop height.
        crop_w = img_w
        crop_h = int(img_w / target_ratio)
        
        # 3 vertical crops
        c1 = pil_img.crop((0, 0, crop_w, crop_h)) # Top
        c2 = pil_img.crop((0, (img_h - crop_h) // 2, crop_w, (img_h + crop_h) // 2)) # Middle
        c3 = pil_img.crop((0, img_h - crop_h, crop_w, img_h)) # Bottom
        
        return [("top", c1), ("center", c2), ("bottom", c3)]

def safe_extract(features, projection_layer, expected_dim=512):
    """
    Safely extracts projected features (512-dim) across different transformers versions.
    Some versions return Tensors, others return ModelOutput objects that may or may not be projected.
    """
    if isinstance(features, torch.Tensor):
        return features
    if hasattr(features, "text_embeds") and features.text_embeds is not None:
        return features.text_embeds
    if hasattr(features, "image_embeds") and features.image_embeds is not None:
        return features.image_embeds
    if hasattr(features, "pooler_output") and features.pooler_output is not None:
        tensor = features.pooler_output
        if tensor.shape[-1] != expected_dim:
            tensor = projection_layer(tensor)
        return tensor
    if isinstance(features, tuple):
        for item in features:
            if isinstance(item, torch.Tensor) and item.shape[-1] == expected_dim:
                return item
        if len(features) > 1:
            return projection_layer(features[1])
    return features

def load_image_safe(path: Path):
    try:
        return Image.open(path).convert("RGB")
    except Exception as e:
        console.print(f"[yellow]:warning: Could not load {path.name}: {e}[/yellow]")
        return None

def main():
    parser = argparse.ArgumentParser(description="Rank wallpapers using Zero-Shot CLIP.")
    parser.add_argument("folder", type=Path, help="Folder containing images")
    parser.add_argument("--output", type=Path, default=Path("./wallpaper_winners"), help="Destination folder for winners")
    parser.add_argument("--phone-width", type=int, default=1080)
    parser.add_argument("--phone-height", type=int, default=2460)
    parser.add_argument("--laptop-width", type=int, default=1920)
    parser.add_argument("--laptop-height", type=int, default=1080)
    parser.add_argument("--top-k", type=int, default=10, help="Number of top wallpapers to output per device")
    parser.add_argument("--pos-prompts", type=str, 
                        default="a high-quality dark theme anime illustration of a girl with pink hair,centered portrait of a pink-haired anime girl,a beautiful clean anime wallpaper", 
                        help="Comma-separated positive prompts for CLIP matching")
    parser.add_argument("--neg-prompts", type=str, 
                        default="bright white background,messy cluttered background,text,memes,empty background with no character,cropped out face,off-center cut", 
                        help="Comma-separated negative prompts for CLIP matching")
    args = parser.parse_args()

    if not args.folder.exists():
        console.print(f"[red]:x: Folder not found: {args.folder}[/red]")
        sys.exit(1)

    VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".m4v", ".webm"}

    # GPU Status Check
    console.print("\n[bold]=== System Status Check ===[/bold]")
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        console.print(f"[green]:white_check_mark: GPU Acceleration ACTIVE:[/green] {gpu_name}")
    else:
        console.print("[yellow]:warning: GPU Acceleration INACTIVE (Running on CPU).[/yellow]")
        console.print("  [dim]Reasons why this might happen:[/dim]")
        console.print("  [dim]- You installed the CPU-only version of PyTorch.[/dim]")
        console.print("  [dim]- You don't have an NVIDIA GPU, or CUDA drivers are missing.[/dim]")
        console.print("  [dim]- To fix: run `pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121`[/dim]")

    # File Status Check
    images = []
    videos = []
    for p in args.folder.rglob("*"):
        if p.is_file():
            ext = p.suffix.lower()
            if ext in IMAGE_EXTS:
                images.append(p)
            elif ext in VIDEO_EXTS:
                videos.append(p)

    console.print(f"\n[bold]=== File Status Check ===[/bold]")
    console.print(f"Found [cyan]{len(images)}[/cyan] image(s) to process.")
    if videos:
        console.print(f"Found [yellow]{len(videos)}[/yellow] video(s) (Videos are currently skipped for CLIP analysis).")
    
    if not images:
        console.print("[red]:x: No supported images found in the target folder.[/red]")
        sys.exit(1)

    files = images

    # Load cache
    cache_path = args.folder / "wallpaper_cache.pkl"
    cache = {
        "phone_width": args.phone_width,
        "phone_height": args.phone_height,
        "laptop_width": args.laptop_width,
        "laptop_height": args.laptop_height,
        "entries": {}
    }

    if cache_path.exists():
        try:
            with open(cache_path, "rb") as f:
                loaded_cache = pickle.load(f)
            # Verify if resolution settings match
            if (loaded_cache.get("phone_width") == args.phone_width and
                loaded_cache.get("phone_height") == args.phone_height and
                loaded_cache.get("laptop_width") == args.laptop_width and
                loaded_cache.get("laptop_height") == args.laptop_height):
                cache = loaded_cache
                console.print(f"[green]:white_check_mark: Loaded feature cache with {len(cache['entries'])} entries.[/green]")
            else:
                console.print("[yellow]:warning: Resolution settings changed. Ignoring old cache and rebuilding...[/yellow]")
        except Exception as e:
            console.print(f"[yellow]:warning: Could not load cache ({e}). Rebuilding...[/yellow]")

    cached_entries = cache["entries"]
    files_to_process = []

    for file_path in files:
        try:
            mtime = os.path.getmtime(file_path)
        except Exception:
            mtime = 0.0
            
        rel_path = str(file_path.relative_to(args.folder))
        
        # Check if valid cached entry exists
        if rel_path in cached_entries and cached_entries[rel_path].get("mtime") == mtime:
            entry = cached_entries[rel_path]
            if "phone" in entry and "laptop" in entry:
                continue
                
        files_to_process.append((file_path, rel_path, mtime))

    # Initialize CLIP Model
    # Note: We must always load it to encode the user's text prompts (even if 0 images to process)
    console.print(f"\n[bold cyan]:rocket: Initializing CLIP Model on {device.upper()}...[/bold cyan]")
    model_name = "openai/clip-vit-base-patch32"
    processor = CLIPProcessor.from_pretrained(model_name)
    model = CLIPModel.from_pretrained(model_name, use_safetensors=True).to(device)

    # Process new/modified images if any
    if files_to_process:
        console.print(f"[yellow]:mag: Processing {len(files_to_process)} new/modified image(s)...[/yellow]")
        cache_dirty = False
        
        for idx, (file_path, rel_path, mtime) in enumerate(files_to_process):
            img = load_image_safe(file_path)
            if img is None:
                continue
                
            phone_crops = get_crops(img, args.phone_width, args.phone_height)
            laptop_crops = get_crops(img, args.laptop_width, args.laptop_height)
            
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
                    "features": feats_p.cpu()  # Save to CPU so it is picklable
                },
                "laptop": {
                    "names": names_l,
                    "features": feats_l.cpu()
                }
            }
            cache_dirty = True
            
            if (idx + 1) % 50 == 0 or (idx + 1) == len(files_to_process):
                console.print(f"  Processed {idx + 1}/{len(files_to_process)} images...")

        if cache_dirty:
            try:
                with open(cache_path, "wb") as f:
                    pickle.dump(cache, f)
                console.print("[green]:white_check_mark: Saved updated feature cache to disk.[/green]")
            except Exception as e:
                console.print(f"[red]❌ Failed to save cache: {e}[/red]")

    positive_prompts = [p.strip() for p in args.pos_prompts.split(",") if p.strip()]
    negative_prompts = [p.strip() for p in args.neg_prompts.split(",") if p.strip()]

    console.print(f"\n[bold]Evaluating wallpapers...[/bold]")

    # Pre-compute text embeddings
    with torch.no_grad():
        inputs = processor(text=positive_prompts + negative_prompts, return_tensors="pt", padding=True).to(device)
        text_features = model.get_text_features(**inputs)
        text_features = safe_extract(text_features, model.text_projection)
        text_features = text_features / text_features.norm(dim=-1, keepdim=True)
        num_pos = len(positive_prompts)
        pos_features = text_features[:num_pos]
        neg_features = text_features[num_pos:]

    results_phone = []
    results_laptop = []

    # Run ranking using cached features
    for file_path in files:
        rel_path = str(file_path.relative_to(args.folder))
        if rel_path not in cached_entries:
            continue
            
        entry = cached_entries[rel_path]
        phone_names = entry["phone"]["names"]
        phone_feats = entry["phone"]["features"].to(device)
        laptop_names = entry["laptop"]["names"]
        laptop_feats = entry["laptop"]["features"].to(device)

        with torch.no_grad():
            for features, names, device_name in [(phone_feats, phone_names, "phone"), (laptop_feats, laptop_names, "laptop")]:
                sim_pos = features @ pos_features.T
                sim_neg = features @ neg_features.T
                
                max_pos = sim_pos.max(dim=-1).values
                max_neg = sim_neg.max(dim=-1).values
                scores = (max_pos - max_neg).cpu().numpy()
                
                best_idx = scores.argmax()
                best_score = float(scores[best_idx])
                best_crop_name = names[best_idx]
                
                if device_name == "phone":
                    results_phone.append({
                        "path": file_path, "score": best_score, "crop_type": best_crop_name
                    })
                else:
                    results_laptop.append({
                        "path": file_path, "score": best_score, "crop_type": best_crop_name
                    })

    # Sort results
    results_phone.sort(key=lambda x: x["score"], reverse=True)
    results_laptop.sort(key=lambda x: x["score"], reverse=True)

    # Save Winners
    args.output.mkdir(parents=True, exist_ok=True)
    out_phone = args.output / "phone"
    out_laptop = args.output / "laptop"
    out_phone.mkdir(exist_ok=True)
    out_laptop.mkdir(exist_ok=True)

    console.print(f"\n[bold green]:trophy: Top {args.top_k} Phone Winners:[/bold green]")
    for i, res in enumerate(results_phone[:args.top_k], 1):
        ext = res['path'].suffix
        out_file = out_phone / f"phone_{i:02d}_{res['path'].stem}{ext}"
        
        img = load_image_safe(res['path'])
        crops = get_crops(img, args.phone_width, args.phone_height)
        for crop_name, crop_img in crops:
            if crop_name == res['crop_type']:
                crop_img.save(out_file)
                break
                
        console.print(f"  {i}. {res['path'].name} (Score: {res['score']:.3f}, Crop: {res['crop_type']}) -> saved to {out_file.name}")

    console.print(f"\n[bold green]:computer: Top {args.top_k} Laptop Winners:[/bold green]")
    for i, res in enumerate(results_laptop[:args.top_k], 1):
        ext = res['path'].suffix
        out_file = out_laptop / f"laptop_{i:02d}_{res['path'].stem}{ext}"
        
        img = load_image_safe(res['path'])
        crops = get_crops(img, args.laptop_width, args.laptop_height)
        for crop_name, crop_img in crops:
            if crop_name == res['crop_type']:
                crop_img.save(out_file)
                break
        console.print(f"  {i}. {res['path'].name} (Score: {res['score']:.3f}, Crop: {res['crop_type']}) -> saved to {out_file.name}")

    console.print(f"\n[bold green]:white_check_mark: Done! Saved top {args.top_k} crops to {args.output.resolve()}[/bold green]")

if __name__ == "__main__":
    main()


