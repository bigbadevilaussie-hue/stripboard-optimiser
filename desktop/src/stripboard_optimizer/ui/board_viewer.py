import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import os

class BoardViewer(ttk.Frame):
    def __init__(self, parent, on_close=None):
        super().__init__(parent, style="Panel.TFrame")
        self.on_close = on_close
        self.current_image = None
        self.photo = None
        self.zoom_mode = True
        self.top_png = None
        self.copper_png = None
        self.schematic_png = None

        controls = ttk.Frame(self, style="Panel.TFrame", padding=(10, 10))
        controls.pack(fill="x")

        self.view_side = tk.StringVar(value="top")
        ttk.Radiobutton(controls, text="Front (Top)", variable=self.view_side, value="top", command=self.update_image).pack(side="left", padx=5)
        ttk.Radiobutton(controls, text="Back (Copper)", variable=self.view_side, value="copper", command=self.update_image).pack(side="left", padx=5)
        self.rb_schematic = ttk.Radiobutton(controls, text="Schematic", variable=self.view_side, value="schematic", command=self.update_image)
        self.rb_schematic.pack(side="left", padx=5)
        self.rb_schematic.configure(state="disabled")

        ttk.Button(controls, text="Close", style="Red.TButton", command=self.close).pack(side="right", padx=5)
        self.btn_zoom = ttk.Button(controls, text="100%", style="Amber.TButton", command=self.toggle_zoom)
        self.btn_zoom.pack(side="right", padx=20)

        self.canvas_frame = ttk.Frame(self, style="Panel.TFrame")
        self.canvas_frame.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(self.canvas_frame, bg="#ffffff", highlightthickness=0)
        self.h_scroll = ttk.Scrollbar(self.canvas_frame, orient="horizontal", command=self.canvas.xview)
        self.v_scroll = ttk.Scrollbar(self.canvas_frame, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=self.h_scroll.set, yscrollcommand=self.v_scroll.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.v_scroll.grid(row=0, column=1, sticky="ns")
        self.h_scroll.grid(row=1, column=0, sticky="ew")
        self.canvas_frame.grid_rowconfigure(0, weight=1)
        self.canvas_frame.grid_columnconfigure(0, weight=1)
        self.canvas.bind("<Configure>", self.on_resize)

    def load(self, top_png, copper_png, schematic_png=None):
        self.top_png = top_png
        self.copper_png = copper_png
        self.schematic_png = schematic_png
        has_schem = bool(schematic_png and os.path.exists(schematic_png))
        self.rb_schematic.configure(state="normal" if has_schem else "disabled")
        if not has_schem and self.view_side.get() == "schematic":
            self.view_side.set("top")
        self.update_image()

    def toggle_zoom(self):
        self.zoom_mode = not self.zoom_mode
        self.btn_zoom.configure(text="Fit" if self.zoom_mode else "100%")
        self.update_image()

    def on_resize(self, event):
        if self.zoom_mode and self.current_image:
            self.update_image()

    def update_image(self):
        side = self.view_side.get()
        if side == "top":
            path = self.top_png
        elif side == "copper":
            path = self.copper_png
        else:
            path = self.schematic_png
        if not path or not os.path.exists(path):
            self.canvas.delete("all")
            self.canvas.create_text(400, 300, text="No image loaded. Click Render JSON...", fill="#ef4444", font=("Helvetica Neue", 14))
            return
        img = Image.open(path)
        self.current_image = img
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if self.zoom_mode and w > 1 and h > 1:
            scale = min(w / img.width, h / img.height, 1.0)
            if scale < 1.0:
                img = img.resize((int(img.width * scale), int(img.height * scale)), Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(img)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self.photo, anchor="nw")
        self.canvas.config(scrollregion=self.canvas.bbox("all"))

    def close(self):
        if self.on_close:
            self.on_close()
