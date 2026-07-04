import os
import shutil
from pathlib import Path

def copy_non_images(source_directory, destination_directory):
    # Set of common image extensions to exclude (case-insensitive)
    IMAGE_EXTENSIONS = {
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', 
        '.tif', '.webp', '.svg', '.heic', '.ico', '.raw'
    }

    source = Path(source_directory)
    dest = Path(destination_directory)

    # Validate source directory
    if not source.exists() or not source.is_dir():
        print(f"Error: Source directory '{source}' does not exist.")
        return

    # Create destination directory if it doesn't exist
    dest.mkdir(parents=True, exist_ok=True)
    
    copied_count = 0
    skipped_count = 0

    print("Starting file copy process...\n")

    # rglob('*') walks through all files and subfolders recursively
    for file_path in source.rglob('*'):
        if file_path.is_file():
            # Check if the file extension is an image
            if file_path.suffix.lower() in IMAGE_EXTENSIONS:
                skipped_count += 1
                continue
            
            # Replicate the folder structure in the destination path
            relative_path = file_path.relative_to(source)
            target_path = dest / relative_path
            
            # Create subdirectories inside destination if they don't exist
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy the file (shutil.copy2 preserves file metadata like timestamps)
            shutil.copy2(file_path, target_path)
            print(f"Copied: {relative_path}")
            copied_count += 1

    print("\n--- Summary ---")
    print(f"Files copied: {copied_count}")
    print(f"Images skipped: {skipped_count}")


# --- CONFIGURATION DEFAULTS ---
SOURCE_DIR_DEFAULT = r"danbooru/remielle_dan"
DEST_DIR_DEFAULT = r"danbooru/remielle_dan_for_ranking"

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Copy non-image files from source to destination.")
    parser.add_argument("--source", "-s", default=SOURCE_DIR_DEFAULT, help=f"Source directory (default: '{SOURCE_DIR_DEFAULT}')")
    parser.add_argument("--dest", "-d", default=DEST_DIR_DEFAULT, help=f"Destination directory (default: '{DEST_DIR_DEFAULT}')")
    args = parser.parse_args()

    copy_non_images(args.source, args.dest)