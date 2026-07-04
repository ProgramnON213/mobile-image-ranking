import os
from pathlib import Path
import win32com.client

def create_lnk_shortcuts(source_directory, destination_directory):
    # Tập hợp các đuôi file ảnh cần bỏ qua
    IMAGE_EXTENSIONS = {
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', 
        '.tif', '.webp', '.svg', '.heic', '.ico', '.raw'
    }

    source = Path(source_directory).resolve()
    dest = Path(destination_directory).resolve()

    if not source.exists() or not source.is_dir():
        print(f"Error: Source directory '{source}' does not exist.")
        return

    dest.mkdir(parents=True, exist_ok=True)
    
    # Khởi tạo Windows Script Host Shell
    try:
        shell = win32com.client.Dispatch("WScript.Shell")
    except Exception as e:
        print(f"Error initializing WScript.Shell: {e}")
        print("Please ensure pywin32 is installed: pip install pywin32")
        return

    shortcut_count = 0
    skipped_count = 0

    print("Starting .lnk shortcut creation...\n")

    for file_path in source.rglob('*'):
        if file_path.is_file():
            if file_path.suffix.lower() in IMAGE_EXTENSIONS:
                skipped_count += 1
                continue
            
            # Tính toán cấu trúc thư mục con
            relative_path = file_path.relative_to(source)
            
            # Tạo đường dẫn cho file .lnk mới
            lnk_name = f"{file_path.name}.lnk"
            target_dir = dest / relative_path.parent
            target_lnk_path = target_dir / lnk_name
            
            target_dir.mkdir(parents=True, exist_ok=True)
            
            try:
                # Xóa file shortcut cũ nếu đã tồn tại để tránh lỗi
                if target_lnk_path.exists():
                    target_lnk_path.unlink()
                
                # Tạo và lưu shortcut
                shortcut = shell.CreateShortCut(str(target_lnk_path))
                shortcut.Targetpath = str(file_path)
                shortcut.WorkingDirectory = str(file_path.parent) # Đặt thư mục làm việc tại vị trí file gốc
                shortcut.Save()
                
                print(f"Created: {relative_path.parent / lnk_name}")
                shortcut_count += 1
                
            except Exception as e:
                print(f"Failed to create shortcut for {relative_path}: {e}")

    print("\n--- Summary ---")
    print(f"Shortcuts created: {shortcut_count}")
    print(f"Images skipped: {skipped_count}")

# --- CONFIGURATION DEFAULTS ---
SOURCE_DIR_DEFAULT = r"danbooru/remielle_dan"
DEST_DIR_DEFAULT = r"danbooru/remielle_dan_non_img_link"

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Create Windows .lnk shortcuts for non-image files.")
    parser.add_argument("--source", "-s", default=SOURCE_DIR_DEFAULT, help=f"Source directory (default: '{SOURCE_DIR_DEFAULT}')")
    parser.add_argument("--dest", "-d", default=DEST_DIR_DEFAULT, help=f"Destination directory (default: '{DEST_DIR_DEFAULT}')")
    args = parser.parse_args()

    create_lnk_shortcuts(args.source, args.dest)