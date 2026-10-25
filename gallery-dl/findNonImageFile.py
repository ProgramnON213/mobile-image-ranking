#!/usr/bin/env python3
"""
Isolates and copies non-image assets/text logs from downloaded folders,
or creates Windows .lnk shortcuts.
"""

import os
import shutil
import sys
from pathlib import Path

# Common image extensions to exclude (case-insensitive)
IMAGE_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', 
    '.tif', '.webp', '.svg', '.heic', '.ico', '.raw'
}

def copy_non_images(source_directory, destination_directory, create_shortcuts=False):
    source = Path(source_directory).resolve()
    dest = Path(destination_directory).resolve()

    # Validate source directory
    if not source.exists() or not source.is_dir():
        print(f"Error: Source directory '{source}' does not exist.")
        return

    if dest == source:
        print(f"Error: Destination directory cannot be identical to source directory: '{dest}'")
        return

    # Create destination directory if it doesn't exist
    dest.mkdir(parents=True, exist_ok=True)
    
    shell = None
    if create_shortcuts:
        if sys.platform != 'win32':
            print("Error: .lnk shortcut creation is only supported on Windows.")
            return
        try:
            import win32com.client
            shell = win32com.client.Dispatch("WScript.Shell")
        except Exception as e:
            print(f"Error initializing Windows Script Host: {e}")
            print("Please ensure pywin32 is installed: pip install pywin32")
            return

    copied_count = 0
    skipped_count = 0

    mode_label = "shortcut creation" if create_shortcuts else "file copy"
    print(f"Starting non-image {mode_label} process...\n")

    for file_path in source.rglob('*'):
        if not file_path.is_file():
            continue

        # Prevent infinite recursion if destination is inside source directory
        try:
            if file_path.resolve().is_relative_to(dest):
                continue
        except Exception:
            pass

        # Check if the file extension is an image
        if file_path.suffix.lower() in IMAGE_EXTENSIONS:
            skipped_count += 1
            continue

        relative_path = file_path.relative_to(source)

        if create_shortcuts:
            lnk_name = f"{file_path.name}.lnk"
            target_dir = dest / relative_path.parent
            target_lnk_path = target_dir / lnk_name
            target_dir.mkdir(parents=True, exist_ok=True)
            try:
                if target_lnk_path.exists():
                    target_lnk_path.unlink()
                shortcut = shell.CreateShortCut(str(target_lnk_path))
                shortcut.Targetpath = str(file_path)
                shortcut.WorkingDirectory = str(file_path.parent)
                shortcut.Save()
                print(f"Created shortcut: {relative_path.parent / lnk_name}")
                copied_count += 1
            except Exception as e:
                print(f"Failed to create shortcut for {relative_path}: {e}")
        else:
            target_path = dest / relative_path
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, target_path)
            print(f"Copied: {relative_path}")
            copied_count += 1

    print("\n--- Summary ---")
    item_label = "Shortcuts created" if create_shortcuts else "Files copied"
    print(f"{item_label}: {copied_count}")
    print(f"Images skipped: {skipped_count}")


# --- CONFIGURATION DEFAULTS ---
SOURCE_DIR_DEFAULT = r"danbooru/remielle_dan"
DEST_DIR_DEFAULT = r"danbooru/remielle_dan_for_ranking"

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Copy non-image files or create shortcuts from source to destination.")
    parser.add_argument("--source", "-s", default=SOURCE_DIR_DEFAULT, help=f"Source directory (default: '{SOURCE_DIR_DEFAULT}')")
    parser.add_argument("--dest", "-d", default=DEST_DIR_DEFAULT, help=f"Destination directory (default: '{DEST_DIR_DEFAULT}')")
    parser.add_argument("--shortcut", "-l", action="store_true", help="Create Windows .lnk shortcuts instead of copying full files")
    args = parser.parse_args()

    copy_non_images(args.source, args.dest, create_shortcuts=args.shortcut)
