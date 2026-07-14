#!/usr/bin/env python3
import os
import json
import sys

# Optional GUI imports
GUI_AVAILABLE = False
try:
    import tkinter as tk
    from tkinter import messagebox, Toplevel
    from PIL import Image, ImageTk
    GUI_AVAILABLE = True
except ImportError:
    pass

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

def find_file(root_dir, file_path_str, dir_map=None):
    """
    Attempts to locate the file in root_dir using several fallback strategies:
    1. Direct match with path in JSON.
    2. Match with basename in root_dir.
    3. Recursive search for basename in root_dir (optimized with dir_map).
    """
    file_path_str = file_path_str.replace('\\', '/')
    basename = os.path.basename(file_path_str)

    # Strategy 1: Direct join
    candidate1 = os.path.join(root_dir, file_path_str)
    if os.path.isfile(candidate1):
        return candidate1

    # Strategy 2 & 3: Basename map lookup or fallback search
    if dir_map is not None:
        basename_lower = basename.lower()
        if basename_lower in dir_map:
            return dir_map[basename_lower]
    else:
        # Fallback to direct check in root_dir (Strategy 2)
        candidate2 = os.path.join(root_dir, basename)
        if os.path.isfile(candidate2):
            return candidate2

        # Fallback to recursive search (Strategy 3)
        for dirpath, _, filenames in os.walk(root_dir):
            if basename in filenames:
                return os.path.join(dirpath, basename)

    return None


if GUI_AVAILABLE:
    class ZoomableImageViewer(Toplevel):
        """A custom pop-up window that auto-sizes to the image aspect ratio and allows zooming/panning."""
        def __init__(self, master, image_path):
            super().__init__(master)
            self.title(os.path.basename(image_path))
            
            try:
                self.original_img = Image.open(image_path)
            except Exception as e:
                print(f"Error opening image for zoom: {e}")
                self.destroy()
                return

            img_w, img_h = self.original_img.size
            
            # Get monitor dimensions with a buffer
            screen_w = self.winfo_screenwidth() - 100
            screen_h = self.winfo_screenheight() - 100
            
            if img_w > screen_w or img_h > screen_h:
                self.scale = min(screen_w / img_w, screen_h / img_h)
            else:
                self.scale = 1.0

            initial_w = int(img_w * self.scale)
            initial_h = int(img_h * self.scale)
            
            pos_x = int((self.winfo_screenwidth() - initial_w) / 2)
            pos_y = int((self.winfo_screenheight() - initial_h) / 2)
            
            self.geometry(f"{initial_w}x{initial_h}+{pos_x}+{pos_y}")

            self.canvas = tk.Canvas(self, bg="#1a1a1a", highlightthickness=0)
            self.canvas.pack(fill=tk.BOTH, expand=True)

            self.image_id = self.canvas.create_image(initial_w//2, initial_h//2, anchor="center")
            
            self.canvas.bind("<ButtonPress-1>", self.start_pan)
            self.canvas.bind("<B1-Motion>", self.do_pan)
            self.canvas.bind("<MouseWheel>", self.zoom)
            
            self.update_image()

        def start_pan(self, event):
            self.canvas.config(cursor="fleur")
            self.canvas.scan_mark(event.x, event.y)

        def do_pan(self, event):
            self.canvas.scan_dragto(event.x, event.y, gain=1)

        def zoom(self, event):
            if event.delta < 0:
                self.scale *= 0.85
            else:
                self.scale *= 1.15
            self.update_image()

        def update_image(self):
            new_w = int(self.original_img.width * self.scale)
            new_h = int(self.original_img.height * self.scale)
            
            if new_w < 50 or new_h < 50: 
                return 
                
            resized = self.original_img.resize((new_w, new_h), Image.Resampling.BILINEAR)
            self.photo = ImageTk.PhotoImage(resized)
            
            self.canvas.itemconfig(self.image_id, image=self.photo)
            self.canvas.config(scrollregion=self.canvas.bbox("all"))
            self.canvas.config(cursor="hand2")


    class DeletionPreviewApp:
        """Tkinter UI to display images scheduled for deletion with confirmation checkboxes."""
        def __init__(self, root, to_delete_list):
            self.root = root
            self.root.title("Confirm Deletion - Image Preview")
            
            # Dynamic window sizing (85% of screen size, capped at a reasonable limit)
            screen_w = self.root.winfo_screenwidth()
            screen_h = self.root.winfo_screenheight()
            
            width = min(1400, int(screen_w * 0.85))
            height = min(900, int(screen_h * 0.85))
            
            pos_x = int((screen_w - width) / 2)
            pos_y = int((screen_h - height) / 2)
            
            self.root.geometry(f"{width}x{height}+{pos_x}+{pos_y}")
            self.root.configure(bg="#121212")

            self.to_delete = to_delete_list  # List of tuples: (full_path, size)
            self.vars = {}                   # full_path -> tk.BooleanVar
            self.photo_cache = {}            # full_path -> ImageTk.PhotoImage (prevent garbage collection)
            self.cards = {}                  # full_path -> tk.Frame
            self.loading_job = None
            self.confirmed_deletion = False

            # Set dark theme styles
            self.root.option_add('*Label.Background', '#121212')
            self.root.option_add('*Label.Foreground', '#ffffff')
            self.root.option_add('*Frame.Background', '#121212')
            self.root.option_add('*Checkbutton.Background', '#121212')
            self.root.option_add('*Checkbutton.Foreground', '#ffffff')
            self.root.option_add('*Checkbutton.SelectColor', '#1e1e1e')

            self.setup_ui()
            self.load_images_progressively()

        def setup_ui(self):
            # 1. Top Instruction bar (Packed first, static height)
            top_frame = tk.Frame(self.root, bg="#1e1e1e", height=60)
            top_frame.pack(side=tk.TOP, fill=tk.X)
            top_frame.pack_propagate(False)

            lbl_title = tk.Label(
                top_frame, 
                text="🖼️ Preview Discarded Images: Uncheck any images you want to SAVE. Checked images will be deleted.", 
                font=("Arial", 11, "bold"), 
                bg="#1e1e1e", 
                fg="#e0e0e0"
            )
            lbl_title.pack(side=tk.LEFT, padx=15, pady=15)

            # 2. Bottom control panel (Packed second, static height at bottom of window frame)
            bottom_frame = tk.Frame(self.root, bg="#1e1e1e", height=70)
            bottom_frame.pack(side=tk.BOTTOM, fill=tk.X)
            bottom_frame.pack_propagate(False)

            # Selection Helpers
            btn_select_all = tk.Button(
                bottom_frame, text="Select All", font=("Arial", 10),
                bg="#333333", fg="white", bd=0, padx=12, pady=6, cursor="hand2",
                command=self.select_all
            )
            btn_select_all.pack(side=tk.LEFT, padx=(15, 10), pady=18)

            btn_deselect_all = tk.Button(
                bottom_frame, text="Deselect All", font=("Arial", 10),
                bg="#333333", fg="white", bd=0, padx=12, pady=6, cursor="hand2",
                command=self.deselect_all
            )
            btn_deselect_all.pack(side=tk.LEFT, padx=5, pady=18)

            # Stats label in bottom panel
            self.lbl_stats = tk.Label(bottom_frame, text="", font=("Arial", 10, "bold"), bg="#1e1e1e", fg="#39ff14")
            self.lbl_stats.pack(side=tk.LEFT, padx=20, pady=18)

            # Deletion Action Buttons
            btn_cancel = tk.Button(
                bottom_frame, text="Cancel", font=("Arial", 10, "bold"),
                bg="#444444", fg="white", bd=0, padx=20, pady=6, cursor="hand2",
                command=self.root.destroy
            )
            btn_cancel.pack(side=tk.RIGHT, padx=15, pady=18)

            self.btn_delete = tk.Button(
                bottom_frame, text="Delete Selected Files", font=("Arial", 11, "bold"),
                bg="#d9534f", fg="white", bd=0, padx=25, pady=8, cursor="hand2",
                command=self.confirm_and_delete
            )
            self.btn_delete.pack(side=tk.RIGHT, padx=5, pady=18)

            # 3. Scrollable main area (Packed last, dynamically fills remaining middle space)
            self.canvas = tk.Canvas(self.root, bg="#121212", highlightthickness=0)
            self.scrollbar = tk.Scrollbar(self.root, orient="vertical", command=self.canvas.yview)
            self.scrollable_frame = tk.Frame(self.canvas, bg="#121212")

            self.scrollable_frame.bind(
                "<Configure>", 
                lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            )
            self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
            self.canvas.configure(yscrollcommand=self.scrollbar.set)

            self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

            # Bind mousewheel to canvas scrolling
            self.canvas.bind_all("<MouseWheel>", self.on_mouse_scroll)
            
            # Bind resize event to adjust grid columns dynamically
            self.root.bind("<Configure>", self.on_window_resize)

            # Initialize variables
            for path, _ in self.to_delete:
                self.vars[path] = tk.BooleanVar(value=True)
                
            self.update_stats_label()

        def on_mouse_scroll(self, event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def on_window_resize(self, event):
            # Slow down grid updates to prevent layout thrashing
            if hasattr(self, '_resize_after_id'):
                self.root.after_cancel(self._resize_after_id)
            self._resize_after_id = self.root.after(150, self.regrid)

        def regrid(self):
            # Calculate how many columns fit based on window width
            width = self.canvas.winfo_width()
            card_width = 240  # approximate card width + padding
            cols = max(1, width // card_width)
            
            for idx, (path, _) in enumerate(self.to_delete):
                card = self.cards.get(path)
                if card:
                    r = idx // cols
                    c = idx % cols
                    card.grid(row=r, column=c, padx=10, pady=10)

        def load_images_progressively(self, index=0):
            if index >= len(self.to_delete):
                self.loading_job = None
                return

            path, size = self.to_delete[index]
            
            # Create a card frame
            card = tk.Frame(self.scrollable_frame, bg="#1e1e1e", bd=1, relief=tk.FLAT, width=220, height=270)
            card.pack_propagate(False)
            self.cards[path] = card

            # Thumbnail loading
            lbl_img = None
            is_video = os.path.splitext(path)[1].lower() in ['.mp4', '.webm', '.ogg', '.mov', '.m4v']
            try:
                if is_video:
                    # Render clean video placeholder representation
                    lbl_img = tk.Label(
                        card, 
                        text="🎥\n[Video File]", 
                        font=("Arial", 14, "bold"),
                        bg="#2a2a2a", 
                        fg="#00bcd4",
                        bd=0,
                        relief=tk.FLAT
                    )
                else:
                    img = Image.open(path)
                    # Keep aspect ratio fitting inside 200x180
                    img.thumbnail((200, 180), Image.Resampling.BILINEAR)
                    photo = ImageTk.PhotoImage(img)
                    self.photo_cache[path] = photo
                    
                    lbl_img = tk.Label(card, image=photo, bg="#1e1e1e", cursor="hand2")
                    lbl_img.bind("<Button-1>", lambda e, p=path: ZoomableImageViewer(self.root, p))
            except Exception:
                # Fallback if image fails to load
                lbl_img = tk.Label(
                    card, 
                    text="⚠️\n[Unrenderable]", 
                    font=("Arial", 12, "bold"),
                    bg="#2a2a2a", 
                    fg="#ff4c4c",
                    bd=0,
                    relief=tk.FLAT
                )

            lbl_img.pack(fill=tk.BOTH, expand=True, padx=5, pady=(5, 2))

            # File metadata details
            name_label_text = os.path.basename(path)
            if len(name_label_text) > 22:
                name_label_text = name_label_text[:19] + "..."
                
            chk = tk.Checkbutton(
                card, 
                text=f"{name_label_text}\n({format_size(size)})", 
                variable=self.vars[path],
                font=("Arial", 9),
                anchor="w",
                justify=tk.LEFT,
                bg="#1e1e1e",
                fg="white",
                selectcolor="#121212",
                command=self.update_stats_label
            )
            chk.pack(fill=tk.X, padx=5, pady=(2, 5))

            # Call regrid to position it correctly
            self.regrid()

            # Schedule loading of next thumbnail
            self.loading_job = self.root.after(1, self.load_images_progressively, index + 1)

        def select_all(self):
            for var in self.vars.values():
                var.set(True)
            self.update_stats_label()

        def deselect_all(self):
            for var in self.vars.values():
                var.set(False)
            self.update_stats_label()

        def update_stats_label(self):
            selected_count = sum(1 for var in self.vars.values() if var.get())
            selected_size = sum(size for path, size in self.to_delete if self.vars[path].get())
            self.lbl_stats.config(text=f"Selected: {selected_count} / {len(self.to_delete)} files ({format_size(selected_size)})")

        def confirm_and_delete(self):
            selected_paths = [path for path, var in self.vars.items() if var.get()]
            if not selected_paths:
                messagebox.showinfo("Nothing Selected", "Please check at least one image to delete.")
                return

            confirm = messagebox.askyesno(
                "Confirm Deletion",
                f"Permanently delete {len(selected_paths)} checked image file(s)?"
            )
            if confirm:
                # Perform the deletion
                deleted_count = 0
                failed_paths = []
                for path in selected_paths:
                    try:
                        os.remove(path)
                        deleted_count += 1
                    except Exception as e:
                        failed_paths.append((path, e))

                if failed_paths:
                    err_msg = "\n".join([f"- {os.path.basename(p)}: {err}" for p, err in failed_paths[:10]])
                    if len(failed_paths) > 10:
                        err_msg += f"\n... and {len(failed_paths) - 10} more errors."
                    messagebox.showerror(
                        "Deletion Completed with Errors",
                        f"Deleted {deleted_count} files successfully.\nFailed to delete {len(failed_paths)} files:\n\n{err_msg}"
                    )
                else:
                    messagebox.showinfo(
                        "Success",
                        f"Successfully deleted {deleted_count} files!"
                    )
                self.confirmed_deletion = True
                self.root.destroy()


def run_gui_preview(to_delete_list):
    """Launches the Tkinter visual preview grid."""
    root = tk.Tk()
    app = DeletionPreviewApp(root, to_delete_list)
    root.mainloop()
    return app.confirmed_deletion


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Discarded images deleter for image ranker")
    parser.add_argument("--json", "-j", help="Path to the exported JSON file")
    parser.add_argument("--root", "-r", help="Root directory containing the source images")
    parser.add_argument("--yes", "-y", action="store_true", help="Confirm deletion without prompting")
    parser.add_argument("--cli", action="store_true", help="Force CLI mode even if GUI is available")
    args = parser.parse_args()

    print("=" * 60)
    print("      🗑️  DISCARDED IMAGES DELETER FOR IMAGE RANKER")
    print("=" * 60)
    
    # 1. Ask for JSON file path (handles drag-and-drop quotes)
    json_path = None
    if args.json:
        json_path = args.json.strip('"').strip("'")
        if not os.path.isfile(json_path):
            print(f"❌ File not found at: {json_path}")
            sys.exit(1)
    else:
        while True:
            json_input = input("\nEnter the path to the exported JSON file: ").strip()
            json_path = json_input.strip('"').strip("'")
            
            if not json_path:
                print("❌ File path cannot be empty.")
                continue
                
            if os.path.isfile(json_path):
                break
            else:
                print(f"❌ File not found at: {json_path}")

    # 2. Parse the JSON file
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Failed to parse JSON file: {e}")
        sys.exit(1)

    if not isinstance(data, list):
        print("❌ Invalid format: Expected a JSON array of items.")
        sys.exit(1)

    # 3. Analyze rankings
    keeps = []
    discards = []
    pendings = []
    other = []

    for item in data:
        if not isinstance(item, dict) or 'file' not in item or 'rating' not in item:
            continue
        
        rating = item.get('rating')
        if rating == 'keep':
            keeps.append(item)
        elif rating == 'discard':
            discards.append(item)
        elif rating == 'pending':
            pendings.append(item)
        else:
            other.append(item)

    print("\n📊 Ranking Stats in JSON:")
    print(f"   ⭐ Keep:    {len(keeps)}")
    print(f"   ❌ Discard: {len(discards)}")
    print(f"   ⏳ Pending: {len(pendings)}")
    if other:
        print(f"   ❓ Other:   {len(other)}")

    if not discards:
        print("\nℹ️ No 'discard' items found in the JSON file. Nothing to delete!")
        return

    # 4. Ask for root image directory
    default_root = os.path.dirname(os.path.abspath(json_path))
    if args.root:
        root_dir = args.root.strip('"').strip("'")
    else:
        print(f"\nSelect the root directory containing the source images.")
        print(f"Default directory is: {default_root}")
        root_input = input(f"Enter path [Or press Enter for default]: ").strip().strip('"').strip("'")
        root_dir = root_input if root_input else default_root
        
    if not os.path.isdir(root_dir):
        print(f"❌ Directory not found: {root_dir}")
        sys.exit(1)

    print(f"\nScanning '{root_dir}' for {len(discards)} discard images...")

    # Build a directory map recursively to avoid O(N * M) os.walk bottleneck
    dir_map = {}
    for dirpath, _, filenames in os.walk(root_dir):
        for f in filenames:
            f_lower = f.lower()
            if f_lower not in dir_map:
                dir_map[f_lower] = os.path.join(dirpath, f)

    # 5. Find files on disk
    to_delete = []
    missing = []
    total_size = 0

    for item in discards:
        rel_path = item['file']
        found_path = find_file(root_dir, rel_path, dir_map)
        
        if found_path:
            try:
                size = os.path.getsize(found_path)
                total_size += size
                to_delete.append((found_path, size))
            except Exception:
                to_delete.append((found_path, 0))
        else:
            missing.append(rel_path)

    # 6. Show results summary
    print(f"\nScan results:")
    print(f"   ✅ Found on disk: {len(to_delete)} files (Total size: {format_size(total_size)})")
    if missing:
        print(f"   ⚠️ Missing on disk: {len(missing)} files (not found under root directory)")

    if not to_delete:
        print("\n❌ None of the discard images were found on your computer. Please check the root directory path.")
        return

    # 7. Visual Preview or CLI Fallback
    if GUI_AVAILABLE and not args.cli:
        print("\n✨ Launching visual preview window...")
        gui_confirmed = run_gui_preview(to_delete)
        if gui_confirmed:
            print("\n🎉 Deletion process completed via GUI.")
        else:
            print("\n❌ Deletion cancelled or window closed without deleting.")
    else:
        # CLI Fallback
        if not GUI_AVAILABLE:
            print("\n⚠️ Tkinter/Pillow GUI library not found. Falling back to Command Line preview.")
        else:
            print("\n📄 Command Line preview:")
        
        preview_limit = 15
        for i, (path, size) in enumerate(to_delete[:preview_limit]):
            print(f"   [{i+1}] {os.path.basename(path)} ({format_size(size)}) -> {path}")
        if len(to_delete) > preview_limit:
            print(f"   ... and {len(to_delete) - preview_limit} more files.")

        if args.yes:
            confirm = 'yes'
        else:
            confirm = input(f"\n⚠️  Are you sure you want to PERMANENTLY DELETE these {len(to_delete)} files? (yes/no): ").strip().lower()
            
        if confirm not in ('y', 'yes'):
            print("\n❌ Deletion cancelled. No files were modified.")
            return

        print("\nDeleting files...")
        deleted_count = 0
        fail_count = 0
        for path, size in to_delete:
            try:
                os.remove(path)
                deleted_count += 1
            except Exception as e:
                print(f"   ❌ Failed to delete {path}: {e}")
                fail_count += 1

        print(f"\n🎉 Done! Successfully deleted {deleted_count} files.")
        if fail_count > 0:
            print(f"   ⚠️ Failed to delete {fail_count} files due to permission or other errors.")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nScript interrupted by user. Exiting.")
        sys.exit(0)
