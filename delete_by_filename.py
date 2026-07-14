#!/usr/bin/env python3
import os
import sys

def format_size(size_in_bytes):
    """Formats bytes into a human-readable string (KB, MB, GB)."""
    if size_in_bytes < 1024:
        return f"{size_in_bytes} Bytes"
    elif size_in_bytes < 1024 * 1024:
        return f"{size_in_bytes / 1024:.2f} KB"
    elif size_in_bytes < 1024 * 1024 * 1024:
        return f"{size_in_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_in_bytes / (1024 * 1024 * 1024):.2f} GB"

def main():
    print("=" * 60)
    print("  DIRECTORY FILENAME SYNCHRONIZATION & CLEANUP TOOL")
    print("=" * 60)

    # 1. Retrieve directory paths
    if len(sys.argv) == 3:
        dir_a = sys.argv[1]
        dir_b = sys.argv[2]
        print(f"Using arguments:\n  Target (dirA):    {dir_a}\n  Reference (dirB): {dir_b}\n")
    else:
        if len(sys.argv) > 1:
            print("Invalid arguments. Providing interactive mode instead.\n")
        try:
            dir_a = input("Enter path to Directory A (Target where files will be deleted): ").strip()
            dir_b = input("Enter path to Directory B (Reference containing names to match): ").strip()
            print()
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled.")
            sys.exit(0)

    # 2. Path validation
    if not dir_a or not dir_b:
        print("Error: Both Directory A and Directory B must be specified.")
        sys.exit(1)

    abs_a = os.path.abspath(dir_a)
    abs_b = os.path.abspath(dir_b)

    if not os.path.isdir(abs_a):
        print(f"Error: Target directory A does not exist or is not a directory:\n  {abs_a}")
        sys.exit(1)

    if not os.path.isdir(abs_b):
        print(f"Error: Reference directory B does not exist or is not a directory:\n  {abs_b}")
        sys.exit(1)

    # Check for directory identity
    if abs_a == abs_b:
        print("Error: Target directory A and Reference directory B cannot be the exact same directory.")
        sys.exit(1)

    print(f"Scanning files...\n  Directory A (Target):    {abs_a}\n  Directory B (Reference): {abs_b}\n")

    # 3. Retrieve files from B (Reference)
    try:
        files_b = set()
        for f in os.listdir(abs_b):
            full_path = os.path.join(abs_b, f)
            if os.path.isfile(full_path):
                files_b.add(f.lower())
    except Exception as e:
        print(f"Error reading Reference Directory B: {e}")
        sys.exit(1)

    # 4. Scan files in A and find matches
    try:
        all_files_a = []
        matches = []
        for f in os.listdir(abs_a):
            full_path = os.path.join(abs_a, f)
            if os.path.isfile(full_path):
                all_files_a.append(f)
                if f.lower() in files_b:
                    size = os.path.getsize(full_path)
                    matches.append((f, full_path, size))
    except Exception as e:
        print(f"Error reading Target Directory A: {e}")
        sys.exit(1)

    # 5. Output statistics and matches
    total_a = len(all_files_a)
    total_b = len(files_b)
    match_count = len(matches)

    print(f"Scan Complete:")
    print(f"  - Files in target Directory A: {total_a}")
    print(f"  - Files in reference Directory B: {total_b}")
    print(f"  - Duplicate filenames found to delete: {match_count}")
    print("-" * 60)

    if match_count == 0:
        print("No matching filenames found in Directory A. Nothing to delete.")
        sys.exit(0)

    # List matching files
    total_size = sum(m[2] for m in matches)
    print("Files marked for deletion in Directory A:")
    for idx, (filename, _, size) in enumerate(matches, 1):
        print(f"  [{idx}] {filename} ({format_size(size)})")
    
    print("-" * 60)
    print(f"Total files to delete: {match_count}")
    print(f"Total space to free:   {format_size(total_size)}")
    print("-" * 60)

    # 6. User confirmation
    try:
        confirm = input("[WARNING] Are you sure you want to PERMANENTLY delete these files? [y/N]: ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        print("\nDeletion cancelled.")
        sys.exit(0)

    if confirm != 'y':
        print("Deletion cancelled. No files were deleted.")
        sys.exit(0)

    # 7. Execute Deletion
    print("\nStarting deletion...")
    deleted_count = 0
    errors_count = 0
    
    for filename, full_path, _ in matches:
        try:
            os.remove(full_path)
            print(f"  [SUCCESS] Deleted: {filename}")
            deleted_count += 1
        except Exception as e:
            print(f"  [ERROR] Error deleting {filename}: {e}")
            errors_count += 1

    print("-" * 60)
    print(f"Deletion complete. Successfully deleted {deleted_count} files.")
    if errors_count > 0:
        print(f"Encountered {errors_count} errors during deletion.")
    print("=" * 60)

if __name__ == "__main__":
    main()
