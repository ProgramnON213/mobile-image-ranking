#!/usr/bin/env python3
"""
Dump all files from a source directory (recursively) into a single flat destination folder.
No subdirectory structure is preserved — every file lands directly in the destination.

Usage: python flat_copy.py <source> <destination> [options]
"""

import argparse
import shutil
import sys
from pathlib import Path


def flat_copy(src: Path, dst: Path, overwrite: bool = False, verbose: bool = False) -> tuple[int, int, int]:
    """
    Copy every file found under src into dst (no subdirectories).

    When two files share the same name, the later one is renamed
    '<stem>_<n><suffix>' to avoid silent data loss (unless --overwrite is set).

    Returns:
        (copied_count, renamed_count, skipped_count)
    """
    copied = 0
    renamed = 0
    skipped = 0

    for src_file in src.rglob("*"):
        if not src_file.is_file():
            continue

        dst_file = dst / src_file.name

        # Handle name collisions
        if dst_file.exists():
            if overwrite:
                pass  # just overwrite in place
            else:
                # Try to find a free name: file_1.txt, file_2.txt, …
                counter = 1
                stem, suffix = src_file.stem, src_file.suffix
                while dst_file.exists():
                    dst_file = dst / f"{stem}_{counter}{suffix}"
                    counter += 1
                renamed += 1

        shutil.copy2(src_file, dst_file)

        if verbose:
            tag = "[RENAMED]" if dst_file.name != src_file.name else "[COPY]  "
            print(f"  {tag}  {src_file.relative_to(src)}  →  {dst_file.name}")
        copied += 1

    return copied, renamed, skipped


def main():
    parser = argparse.ArgumentParser(
        description="Dump all files from a directory tree into a single flat folder."
    )
    parser.add_argument("source",      help="Source directory")
    parser.add_argument("destination", help="Destination directory (flat)")
    parser.add_argument("--overwrite", action="store_true",
                        help="Overwrite destination files with the same name instead of renaming")
    parser.add_argument("--verbose",   action="store_true",
                        help="Print each file as it is copied")
    args = parser.parse_args()

    src = Path(args.source).resolve()
    dst = Path(args.destination).resolve()

    if not src.exists():
        print(f"Error: source '{src}' does not exist.", file=sys.stderr)
        sys.exit(1)
    if not src.is_dir():
        print(f"Error: source '{src}' is not a directory.", file=sys.stderr)
        sys.exit(1)

    dst.mkdir(parents=True, exist_ok=True)

    print(f"Source : {src}")
    print(f"Dest   : {dst}")
    print()

    copied, renamed, skipped = flat_copy(src, dst, overwrite=args.overwrite, verbose=args.verbose)

    print()
    print(f"Done — {copied} file(s) copied ({renamed} renamed to avoid collisions).")


if __name__ == "__main__":
    main()