import os
import tkinter as tk
from tkinter import filedialog, messagebox, Toplevel
from PIL import Image, ImageTk

class ImageBatchCleaner:
    def __init__(self, root):
        self.root = root
        self.root.title("Batch Image Cleaner - High Res")
        self.root.geometry("1000x800")

        self.image_vars = {} 
        self.current_images = [] 
        self.batches = {} 

        # --- Top Bar: Directory Selection ---
        top_frame = tk.Frame(root)
        top_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        tk.Button(top_frame, text="Select Root Folder", command=self.load_directory).pack(side=tk.LEFT)
        self.lbl_path = tk.Label(top_frame, text="No folder selected", fg="gray")
        self.lbl_path.pack(side=tk.LEFT, padx=10)

        # --- Left Panel: List of Batches ---
        left_frame = tk.Frame(root, width=200)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        tk.Label(left_frame, text="Folders with Images:", font=("Arial", 10, "bold")).pack(anchor="w")
        self.listbox = tk.Listbox(left_frame, width=25)
        self.listbox.pack(fill=tk.BOTH, expand=True)
        self.listbox.bind('<<ListboxSelect>>', self.on_batch_select)

        # --- Right Panel: Image Display Grid ---
        right_frame = tk.Frame(root)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.canvas = tk.Canvas(right_frame)
        self.scrollbar = tk.Scrollbar(right_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # --- Bottom Panel: Action Buttons ---
        bottom_frame = tk.Frame(root)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
        
        tk.Button(bottom_frame, text="Delete Selected", bg="#ff4c4c", fg="white", 
                  font=("Arial", 10, "bold"), command=self.delete_images).pack(side=tk.RIGHT)

    def load_directory(self):
        folder_path = filedialog.askdirectory()
        if not folder_path:
            return

        self.lbl_path.config(text=folder_path)
        self.listbox.delete(0, tk.END)
        self.batches.clear()

        for root_dir, dirs, files in os.walk(folder_path):
            img_files = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
            if img_files:
                folder_name = os.path.basename(root_dir)
                display_name = f"{folder_name} ({len(img_files)} imgs)"
                
                self.batches[display_name] = root_dir
                self.listbox.insert(tk.END, display_name)

    def on_batch_select(self, event):
        selection = self.listbox.curselection()
        if not selection:
            return

        display_name = self.listbox.get(selection[0])
        folder_path = self.batches[display_name]

        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.image_vars.clear()
        self.current_images.clear()

        img_files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]

        row, col = 0, 0
        # Reduced columns to 2 to make room for larger images
        max_columns = 2 

        for file in img_files:
            full_path = os.path.join(folder_path, file)

            card = tk.Frame(self.scrollable_frame, bd=1, relief=tk.SOLID, padx=5, pady=5)
            card.grid(row=row, column=col, padx=10, pady=10)

            try:
                # Increased thumbnail resolution
                img = Image.open(full_path)
                img.thumbnail((350, 350), Image.Resampling.LANCZOS) 
                photo = ImageTk.PhotoImage(img)
                self.current_images.append(photo)

                lbl_img = tk.Label(card, image=photo, cursor="hand2")
                lbl_img.pack()
                
                # Bind click event to open full resolution preview
                lbl_img.bind("<Button-1>", lambda e, p=full_path: self.show_full_image(p))
                
            except Exception as e:
                tk.Label(card, text="[Render Error]", width=20, height=10).pack()

            var = tk.BooleanVar()
            self.image_vars[full_path] = var
            
            display_text = file if len(file) < 30 else file[:27] + "..."
            chk = tk.Checkbutton(card, text=display_text, variable=var, font=("Arial", 10))
            chk.pack()

            col += 1
            if col >= max_columns:
                col = 0
                row += 1

    def show_full_image(self, path):
        """Opens a new window showing the image at its original resolution."""
        try:
            top = Toplevel(self.root)
            top.title(os.path.basename(path))
            
            img = Image.open(path)
            
            # Optional: cap the max size of the pop-up so it doesn't exceed your monitor
            screen_width = self.root.winfo_screenwidth() - 100
            screen_height = self.root.winfo_screenheight() - 100
            img.thumbnail((screen_width, screen_height), Image.Resampling.LANCZOS)
            
            photo = ImageTk.PhotoImage(img)
            
            lbl = tk.Label(top, image=photo)
            lbl.image = photo # Keep a reference
            lbl.pack()
            
            # Click the big image to close it quickly
            lbl.bind("<Button-1>", lambda e: top.destroy())
            
        except Exception as e:
            messagebox.showerror("Error", f"Could not load image: {e}")

    def delete_images(self):
        to_delete = [path for path, var in self.image_vars.items() if var.get()]

        if not to_delete:
            messagebox.showinfo("Notice", "No images selected.")
            return

        confirm = messagebox.askyesno("Confirm Deletion", 
                                      f"Permanently delete {len(to_delete)} images?\n\nThis cannot be undone.")
        
        if confirm:
            deleted_count = 0
            for path in to_delete:
                try:
                    os.remove(path)
                    deleted_count += 1
                except Exception as e:
                    print(f"Failed to delete {path}: {e}")

            self.on_batch_select(None)
            messagebox.showinfo("Success", f"{deleted_count} images removed.")

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageBatchCleaner(root)
    root.mainloop()