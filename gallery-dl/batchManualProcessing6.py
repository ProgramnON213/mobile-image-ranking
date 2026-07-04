import os
import tkinter as tk
from tkinter import filedialog, messagebox, Toplevel
from PIL import Image, ImageTk

class ZoomableImageViewer(Toplevel):
    """A custom pop-up window that auto-sizes to the image aspect ratio and allows smartphone-like interaction."""
    def __init__(self, master, image_path):
        super().__init__(master)
        self.title(os.path.basename(image_path))
        
        self.original_img = Image.open(image_path)
        img_w, img_h = self.original_img.size
        
        # Get monitor dimensions with a 100px buffer to account for taskbars
        screen_w = self.winfo_screenwidth() - 100
        screen_h = self.winfo_screenheight() - 100
        
        # 1. Calculate the scale required to fit the image on the screen
        if img_w > screen_w or img_h > screen_h:
            self.scale = min(screen_w / img_w, screen_h / img_h)
        else:
            self.scale = 1.0

        # 2. Calculate the exact pixel dimensions the image will take
        initial_w = int(img_w * self.scale)
        initial_h = int(img_h * self.scale)
        
        # 3. Calculate center position to spawn the window neatly in the middle of your monitor
        pos_x = int((self.winfo_screenwidth() - initial_w) / 2)
        pos_y = int((self.winfo_screenheight() - initial_h) / 2)
        
        # 4. Set the window geometry to perfectly wrap the image with zero gray space
        self.geometry(f"{initial_w}x{initial_h}+{pos_x}+{pos_y}")

        self.canvas = tk.Canvas(self, bg="#222222", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Anchor the image exactly in the center of our perfectly-sized window
        self.image_id = self.canvas.create_image(initial_w//2, initial_h//2, anchor="center")
        
        # --- Smartphone-like Interaction Bindings ---
        self.canvas.bind("<ButtonPress-1>", self.start_pan)
        self.canvas.bind("<B1-Motion>", self.do_pan)
        
        self.canvas.bind("<MouseWheel>", self.zoom)
        self.canvas.bind("<Button-4>", self.zoom) 
        self.canvas.bind("<Button-5>", self.zoom) 
        
        self.update_image()

    def start_pan(self, event):
        self.canvas.config(cursor="fleur")
        self.canvas.scan_mark(event.x, event.y)

    def do_pan(self, event):
        self.canvas.scan_dragto(event.x, event.y, gain=1)

    def zoom(self, event):
        if event.num == 5 or event.delta < 0:
            self.scale *= 0.85 # Zoom out
        elif event.num == 4 or event.delta > 0:
            self.scale *= 1.15 # Zoom in
            
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


class ImageBatchCleaner:
    def __init__(self, root):
        self.root = root
        self.root.title("Batch Image Cleaner - High Performance")
        
        self.root.geometry("1680x1050")
        try:
            self.root.state('zoomed')
        except:
            pass

        self.image_vars = {} 
        self.current_images = [] 
        self.batches = {} 
        self.loading_job = None 

        self.setup_ui()

    def setup_ui(self):
        top_frame = tk.Frame(self.root)
        top_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        tk.Button(top_frame, text="Select Root Folder", font=("Arial", 10, "bold"), command=self.load_directory).pack(side=tk.LEFT)
        self.lbl_path = tk.Label(top_frame, text="No folder selected", fg="gray", font=("Arial", 10))
        self.lbl_path.pack(side=tk.LEFT, padx=10)

        left_frame = tk.Frame(self.root, width=250)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        tk.Label(left_frame, text="Folders with Images (>1):", font=("Arial", 11, "bold")).pack(anchor="w", pady=(0, 5))
        self.listbox = tk.Listbox(left_frame, width=30, font=("Arial", 10))
        self.listbox.pack(fill=tk.BOTH, expand=True)
        self.listbox.bind('<<ListboxSelect>>', self.on_batch_select)

        right_frame = tk.Frame(self.root)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.canvas = tk.Canvas(right_frame)
        self.scrollbar = tk.Scrollbar(right_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas)

        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._bind_mouse_scroll(self.canvas)
        self._bind_mouse_scroll(self.scrollable_frame)

        bottom_frame = tk.Frame(self.root)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
        
        tk.Button(bottom_frame, text="Delete Selected", bg="#ff4c4c", fg="white", 
                  font=("Arial", 12, "bold"), padx=10, pady=5, command=self.delete_images).pack(side=tk.RIGHT)

    def _bind_mouse_scroll(self, widget):
        widget.bind("<MouseWheel>", self._on_main_scroll)
        widget.bind("<Button-4>", self._on_main_scroll)
        widget.bind("<Button-5>", self._on_main_scroll)

    def _on_main_scroll(self, event):
        if event.num == 5 or event.delta < 0:
            self.canvas.yview_scroll(1, "units")
        elif event.num == 4 or event.delta > 0:
            self.canvas.yview_scroll(-1, "units")

    def format_size(self, size_in_bytes):
        return f"{size_in_bytes / 1024:.1f} KB" if size_in_bytes < 1024 * 1024 else f"{size_in_bytes / (1024 * 1024):.2f} MB"

    def load_directory(self, folder_path=None):
        if not folder_path:
            folder_path = filedialog.askdirectory()
        if not folder_path: return

        self.lbl_path.config(text=folder_path)
        self.listbox.delete(0, tk.END)
        self.batches.clear()

        for root_dir, dirs, files in os.walk(folder_path):
            img_files = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
            if len(img_files) > 1:
                folder_name = os.path.basename(root_dir)
                display_name = f"{folder_name} ({len(img_files)} imgs)"
                self.batches[display_name] = root_dir
                self.listbox.insert(tk.END, display_name)

    def on_batch_select(self, event):
        selection = self.listbox.curselection()
        if not selection: return

        if self.loading_job is not None:
            self.root.after_cancel(self.loading_job)

        display_name = self.listbox.get(selection[0])
        folder_path = self.batches[display_name]

        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.image_vars.clear()
        self.current_images.clear()

        img_files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
        self.load_image_progressively(folder_path, img_files, index=0, row=0, col=0)

    def load_image_progressively(self, folder_path, img_files, index, row, col):
        if index >= len(img_files):
            self.loading_job = None
            return

        file = img_files[index]
        full_path = os.path.join(folder_path, file)
        file_size_bytes = os.path.getsize(full_path)
        file_size_str = self.format_size(file_size_bytes)

        card = tk.Frame(self.scrollable_frame, bd=1, relief=tk.SOLID, padx=10, pady=10)
        card.grid(row=row, column=col, padx=15, pady=15)
        self._bind_mouse_scroll(card)

        try:
            img = Image.open(full_path)
            img.thumbnail((500, 500), Image.Resampling.BILINEAR) 
            photo = ImageTk.PhotoImage(img)
            self.current_images.append(photo)

            lbl_img = tk.Label(card, image=photo, cursor="hand2")
            lbl_img.pack()
            self._bind_mouse_scroll(lbl_img)
            lbl_img.bind("<Button-1>", lambda e, p=full_path: ZoomableImageViewer(self.root, p))
            
        except Exception:
            err_lbl = tk.Label(card, text="[Render Error]", width=30, height=15)
            err_lbl.pack()
            self._bind_mouse_scroll(err_lbl)

        var = tk.BooleanVar()
        self.image_vars[full_path] = var
        
        lbl_size = tk.Label(card, text=f"Size: {file_size_str}", fg="#555555", font=("Arial", 10))
        lbl_size.pack(pady=(5, 0))
        self._bind_mouse_scroll(lbl_size)

        display_text = file if len(file) < 35 else file[:32] + "..."
        chk = tk.Checkbutton(card, text=display_text, variable=var, font=("Arial", 11, "bold"))
        chk.pack()
        self._bind_mouse_scroll(chk)

        col += 1
        if col >= 2:
            col = 0
            row += 1

        self.loading_job = self.root.after(10, self.load_image_progressively, folder_path, img_files, index + 1, row, col)

    def delete_images(self):
        to_delete = [path for path, var in self.image_vars.items() if var.get()]
        if not to_delete:
            messagebox.showinfo("Notice", "No images selected.")
            return

        if messagebox.askyesno("Confirm", f"Permanently delete {len(to_delete)} images?"):
            for path in to_delete:
                try: os.remove(path)
                except Exception as e: print(f"Failed to delete {path}: {e}")

            self.on_batch_select(None)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Batch Image Cleaner")
    parser.add_argument("--folder", "-f", help="Initial folder to scan")
    args = parser.parse_args()

    root = tk.Tk()
    app = ImageBatchCleaner(root)
    if args.folder:
        app.load_directory(args.folder)
    root.mainloop()