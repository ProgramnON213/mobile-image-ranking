#!/usr/bin/env python3
"""
Feature vector extractor using PyTorch MobileNetV2.
Supports GPU acceleration, incremental cache updates, batched tensor inference,
and safe npz serialization.
"""

import os
import sys
import pickle
import numpy as np
import torch
import torchvision.models as models
from PIL import Image

# --- Configuration Defaults ---
INPUT_DIR_DEFAULT = 'danbooru/remielle_dan'
OUTPUT_DATA_FILE_DEFAULT = 'image_data.npz'
BATCH_SIZE_DEFAULT = 32

def load_existing_data(data_file):
    """Safely loads existing embedding cache from .npz or legacy .pkl."""
    # Check alternate extension if exact file not found
    target = data_file
    if not os.path.exists(target):
        alt = target.replace('.npz', '.pkl') if target.endswith('.npz') else target.replace('.pkl', '.npz')
        if os.path.exists(alt):
            target = alt
        else:
            return [], None

    print(f"Loading existing embedding data from {target}...")
    try:
        if target.endswith('.npz'):
            with np.load(target, allow_pickle=False) as d:
                return list(d['filenames']), d['vectors']
        else:
            try:
                d = torch.load(target, weights_only=True, map_location="cpu")
                return list(d['filenames']), d['vectors']
            except Exception:
                with open(target, 'rb') as f:
                    d = pickle.load(f)
                return list(d['filenames']), d['vectors']
    except Exception as e:
        print(f"Warning: Could not read existing cache ({e}). Starting fresh.")
        return [], None

def save_data(output_file, filenames, vectors):
    """Saves embeddings using safe npz format (or pickle/pt if requested)."""
    if output_file.endswith('.pkl'):
        try:
            torch.save({'filenames': filenames, 'vectors': vectors}, output_file)
        except Exception:
            with open(output_file, 'wb') as f:
                pickle.dump({'filenames': filenames, 'vectors': vectors}, f)
    else:
        # Default: safe compressed numpy format
        np.savez_compressed(output_file, filenames=filenames, vectors=vectors)

def extract_features(input_dir, output_data_file, batch_size=BATCH_SIZE_DEFAULT, force_rebuild=False):
    existing_filenames = []
    existing_vectors = None

    if not force_rebuild:
        existing_filenames, existing_vectors = load_existing_data(output_data_file)
        if existing_filenames:
            print(f"Found {len(existing_filenames)} previously processed images. Skipping those...")

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Loading pre-trained MobileNetV2 model on device: {device}...")
    weights = models.MobileNet_V2_Weights.DEFAULT
    preprocess = weights.transforms()
    model = models.mobilenet_v2(weights=weights)
    model.classifier = torch.nn.Identity()
    model.to(device)
    model.eval()

    valid_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
    existing_set = set(existing_filenames)

    all_files = sorted(os.listdir(input_dir))
    files_to_process = [
        f for f in all_files 
        if os.path.splitext(f)[1].lower() in valid_extensions and f not in existing_set
    ]

    if not files_to_process:
        print("No new images found. Everything is up to date!")
        return

    print(f"Processing {len(files_to_process)} new image(s) with batch size {batch_size}...")

    new_filenames = []
    new_features = []

    batch_tensors = []
    batch_names = []

    for filename in files_to_process:
        filepath = os.path.join(input_dir, filename)
        try:
            with Image.open(filepath) as img:
                img_tensor = preprocess(img.convert('RGB'))
                batch_tensors.append(img_tensor)
                batch_names.append(filename)
        except Exception as e:
            print(f"Error loading {filename}: {e}")
            continue

        if len(batch_tensors) >= batch_size:
            stacked = torch.stack(batch_tensors).to(device)
            with torch.no_grad():
                preds = model(stacked)
                preds = torch.nn.functional.normalize(preds, p=2, dim=1)
            new_filenames.extend(batch_names)
            new_features.extend(preds.cpu().numpy())
            batch_tensors = []
            batch_names = []
            print(f"  Processed {len(new_filenames)}/{len(files_to_process)} images...")

    # Process remaining items in final batch
    if batch_tensors:
        stacked = torch.stack(batch_tensors).to(device)
        with torch.no_grad():
            preds = model(stacked)
            preds = torch.nn.functional.normalize(preds, p=2, dim=1)
        new_filenames.extend(batch_names)
        new_features.extend(preds.cpu().numpy())

    if not new_features:
        print("No new images were successfully processed.")
        return

    new_normalized_vectors = np.array(new_features)

    if existing_vectors is not None and len(existing_filenames) > 0:
        final_filenames = existing_filenames + new_filenames
        final_vectors = np.vstack((existing_vectors, new_normalized_vectors))
    else:
        final_filenames = new_filenames
        final_vectors = new_normalized_vectors

    print(f"Saving {len(final_filenames)} total vectors to {output_data_file}...")
    save_data(output_data_file, final_filenames, final_vectors)
    print("Feature extraction complete!")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Extract feature vectors from images using PyTorch MobileNetV2 with batching.")
    parser.add_argument("--input-dir", "-i", default=INPUT_DIR_DEFAULT, help=f"Input directory of images (default: '{INPUT_DIR_DEFAULT}')")
    parser.add_argument("--output-file", "-o", default=OUTPUT_DATA_FILE_DEFAULT, help=f"Output data file (default: '{OUTPUT_DATA_FILE_DEFAULT}')")
    parser.add_argument("--batch-size", "-b", type=int, default=BATCH_SIZE_DEFAULT, help=f"Batch size for inference (default: {BATCH_SIZE_DEFAULT})")
    parser.add_argument("--force", action="store_true", help="Force rebuilding features from scratch instead of incremental update")
    args = parser.parse_args()

    os.makedirs(args.input_dir, exist_ok=True)
    extract_features(args.input_dir, args.output_file, batch_size=args.batch_size, force_rebuild=args.force)
