"""
64x64 Pixel Drawpad
====================

A simple paint program for creating 64x64 pixel art, built with Tkinter
(no extra installs needed). Left-click (or click-drag) to paint the
selected color; right-click (or click-drag) to erase back to white.

SAVED DATA FORMAT (JSON)
-------------------------
Clicking "Save Pixel Data (JSON)" writes a file like:

{
  "width": 64,
  "height": 64,
  "grid": [
    [10748681, 16776961, 1, ...],  <- row y=0 (top row), 64 values left to right
    [65281,    256,      100, ...],<- row y=1
    ...                             <- 64 rows total, top to bottom
  ]
}

Each value is the pixel's full (r, g, b) packed into a single 24-bit
integer, one byte per channel:

    packed = (r << 16) | (g << 8) | b     # range 0 - 16,777,215 (0xFFFFFF)

This preserves the exact original color -- unlike a summed value,
packing loses no information, since r, g, and b each occupy their own
non-overlapping 8 bits. Unpacking is cheap bit-masking, no string
parsing required:

    r = (packed >> 16) & 0xFF
    g = (packed >> 8)  & 0xFF
    b = packed & 0xFF

0 is reserved exclusively for untouched/blank cells (i.e. white,
r=g=b=255), so the secondary program can treat 0 as "silence/no tone".
Black (r=g=b=0) packs to 0 on its own, which would collide with that
sentinel -- so every real color's packed value is offset by +1 before
saving:

    stored_value = 0                          if pixel is white (blank)
    stored_value = ((r << 16)|(g << 8)|b) + 1 otherwise

This keeps black -- and every other painted color -- distinguishable
from an untouched cell. To unpack a non-zero stored value, subtract 1
first:

    def unpack(stored_value):
        if stored_value == 0:
            return (255, 255, 255)      # untouched/white
        packed = stored_value - 1
        r = (packed >> 16) & 0xFF
        g = (packed >> 8) & 0xFF
        b = packed & 0xFF
        return r, g, b

"grid" is a plain 64x64 nested array, grid[y][x], stored top-to-bottom,
left-to-right. This one representation is all a secondary program
needs -- every scan direction is a cheap slice/reversal of it, with no
extra copies of the data to keep in sync:

    import json

    with open("pixel_data.json") as f:
        data = json.load(f)

    grid = data["grid"]  # grid[y][x] -> stored value (0 = white/silence)

    # Left to right, top to bottom (row by row, forward)
    for row in grid:
        for value in row:
            play(unpack(value))

    # Right to left, top to bottom (each row reversed)
    for row in grid:
        for value in reversed(row):
            play(unpack(value))

    # Top to bottom, left to right (column by column, forward)
    for x in range(len(grid[0])):
        for row in grid:
            play(unpack(row[x]))

    # Bottom to top, left to right (rows walked in reverse)
    for x in range(len(grid[0])):
        for row in reversed(grid):
            play(unpack(row[x]))

Every one of the 64*64 = 4096 cells is always present (even
untouched/white ones), so the secondary program can rely on a
complete, fixed 64x64 grid with no missing values in any direction.

Optional PNG export requires Pillow (pip install Pillow); JSON
save/load works with the standard library only.
"""

import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox
import json
import os

GRID_SIZE = 64
CELL_SIZE = 10  # on-screen pixels per grid cell (canvas is 640x640)
DEFAULT_COLOR = (255, 255, 255)


class PixelDrawpad:
    def __init__(self, root):
        self.root = root
        self.root.title("64x64 Pixel Drawpad")

        # In-memory pixel data: pixels[y][x] = (r, g, b)
        self.pixels = [[DEFAULT_COLOR for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        self.current_color = [0, 0, 0]  # r, g, b currently selected for painting

        self._build_ui()

    # ---------- UI construction ----------

    def _build_ui(self):
        main_frame = tk.Frame(self.root)
        main_frame.pack(padx=10, pady=10)

        canvas_size = GRID_SIZE * CELL_SIZE
        self.canvas = tk.Canvas(
            main_frame, width=canvas_size, height=canvas_size,
            bg="white", highlightthickness=1, highlightbackground="black"
        )
        self.canvas.grid(row=0, column=0, rowspan=12)

        # Pre-draw all cells as rectangles so we can recolor them cheaply later
        self.rects = [[None] * GRID_SIZE for _ in range(GRID_SIZE)]
        for y in range(GRID_SIZE):
            for x in range(GRID_SIZE):
                x0, y0 = x * CELL_SIZE, y * CELL_SIZE
                x1, y1 = x0 + CELL_SIZE, y0 + CELL_SIZE
                rect = self.canvas.create_rectangle(
                    x0, y0, x1, y1, fill=self._rgb_to_hex(DEFAULT_COLOR), outline="#dddddd"
                )
                self.rects[y][x] = rect

        self.canvas.bind("<Button-1>", self.paint)
        self.canvas.bind("<B1-Motion>", self.paint)
        self.canvas.bind("<Button-3>", self.erase)
        self.canvas.bind("<B3-Motion>", self.erase)

        # ---- Controls panel ----
        controls = tk.Frame(main_frame)
        controls.grid(row=0, column=1, sticky="n", padx=15)

        tk.Label(controls, text="Color Controls", font=("Arial", 12, "bold")).pack(pady=(0, 10))

        self.sliders = {}
        for i, name in enumerate(["R", "G", "B"]):
            row = tk.Frame(controls)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=name, width=2).pack(side="left")
            slider = tk.Scale(
                row, from_=0, to=255, orient="horizontal", length=160,
                command=lambda val, idx=i: self.update_color(idx, val)
            )
            slider.pack(side="left")
            self.sliders[name] = slider

        self.color_preview = tk.Canvas(
            controls, width=160, height=40, bg="black",
            highlightthickness=1, highlightbackground="gray"
        )
        self.color_preview.pack(pady=10)

        tk.Button(controls, text="Pick Color...", command=self.pick_color).pack(fill="x", pady=2)
        tk.Button(controls, text="Clear Canvas", command=self.clear_canvas).pack(fill="x", pady=(10, 2))

        tk.Frame(controls, height=10).pack()  # spacer

        tk.Button(controls, text="Save Pixel Data (JSON)", command=self.save_data).pack(fill="x", pady=2)
        tk.Button(controls, text="Load Pixel Data (JSON)", command=self.load_data).pack(fill="x", pady=2)
        tk.Button(controls, text="Export as PNG", command=self.export_png).pack(fill="x", pady=2)

        tk.Label(
            controls, text="Left-click: paint\nRight-click: erase",
            fg="gray30", justify="left"
        ).pack(pady=(10, 2), anchor="w")

        self.status_label = tk.Label(controls, text="", fg="green", wraplength=160, justify="left")
        self.status_label.pack(pady=10)

    # ---------- helpers ----------

    @staticmethod
    def _rgb_to_hex(rgb):
        return "#%02x%02x%02x" % tuple(rgb)

    def _cell_from_event(self, event):
        return event.x // CELL_SIZE, event.y // CELL_SIZE

    # ---------- color controls ----------

    def update_color(self, idx, val):
        self.current_color[idx] = int(val)
        self.color_preview.config(bg=self._rgb_to_hex(self.current_color))

    def pick_color(self):
        result = colorchooser.askcolor(color=self._rgb_to_hex(self.current_color))
        if result[0]:
            r, g, b = (int(c) for c in result[0])
            self.current_color = [r, g, b]
            for name, val in zip(["R", "G", "B"], (r, g, b)):
                self.sliders[name].set(val)
            self.color_preview.config(bg=self._rgb_to_hex(self.current_color))

    # ---------- painting ----------

    def paint(self, event):
        x, y = self._cell_from_event(event)
        if 0 <= x < GRID_SIZE and 0 <= y < GRID_SIZE:
            color = tuple(self.current_color)
            self.pixels[y][x] = color
            self.canvas.itemconfig(self.rects[y][x], fill=self._rgb_to_hex(color))

    def erase(self, event):
        x, y = self._cell_from_event(event)
        if 0 <= x < GRID_SIZE and 0 <= y < GRID_SIZE:
            self.pixels[y][x] = DEFAULT_COLOR
            self.canvas.itemconfig(self.rects[y][x], fill=self._rgb_to_hex(DEFAULT_COLOR))

    def clear_canvas(self):
        if messagebox.askyesno("Clear Canvas", "Clear all pixels to white?"):
            for y in range(GRID_SIZE):
                for x in range(GRID_SIZE):
                    self.pixels[y][x] = DEFAULT_COLOR
                    self.canvas.itemconfig(self.rects[y][x], fill=self._rgb_to_hex(DEFAULT_COLOR))
            self.status_label.config(text="Canvas cleared.")

    # ---------- save / load ----------

    def save_data(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile="pixel_data.json"
        )
        if not filepath:
            return

        # grid[y][x] = (r, g, b) packed into one 24-bit integer, stored
        # top-to-bottom, left-to-right. Packing (rather than summing)
        # keeps every channel intact -- r, g, and b each live in their
        # own 8 bits, so no color information is lost.
        #
        # 0 is reserved exclusively for "blank/white" (silence). Black
        # (0,0,0) packs to 0 on its own, which would collide with that
        # sentinel, so every real color's packed value is offset by +1
        # before saving. This keeps black -- and every other color --
        # distinguishable from an untouched cell.
        grid = [[0] * GRID_SIZE for _ in range(GRID_SIZE)]

        for y in range(GRID_SIZE):
            for x in range(GRID_SIZE):
                r, g, b = self.pixels[y][x]
                if (r, g, b) == DEFAULT_COLOR:
                    # Untouched/blank cell -> the only value allowed to be 0
                    packed = 0
                else:
                    packed = ((r << 16) | (g << 8) | b) + 1
                grid[y][x] = packed

        data = {
            "width": GRID_SIZE,
            "height": GRID_SIZE,
            "grid": grid,
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        self.status_label.config(text=f"Saved to {os.path.basename(filepath)}")

    def load_data(self):
        filepath = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if not filepath:
            return
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
            # Prefer the 2D "grid" form; fall back to an older flat
            # "pixels" list if loading a file saved by a previous version.
            if "grid" in data:
                entries = (
                    {"x": x, "y": y, "value": data["grid"][y][x]}
                    for y in range(len(data["grid"]))
                    for x in range(len(data["grid"][y]))
                )
            else:
                entries = data["pixels"]

            for entry in entries:
                x, y = entry["x"], entry["y"]
                value = entry["value"]
                if value == 0:
                    # 0 is the reserved "blank/white" sentinel
                    rgb = DEFAULT_COLOR
                else:
                    # Reverse the +1 offset applied at save time, then unpack
                    value = min(max(value, 1), 0xFFFFFF + 1)
                    packed = value - 1
                    r = (packed >> 16) & 0xFF
                    g = (packed >> 8) & 0xFF
                    b = packed & 0xFF
                    rgb = (r, g, b)
                if 0 <= x < GRID_SIZE and 0 <= y < GRID_SIZE:
                    self.pixels[y][x] = rgb
                    self.canvas.itemconfig(self.rects[y][x], fill=self._rgb_to_hex(rgb))
            self.status_label.config(text=f"Loaded {os.path.basename(filepath)}")
        except Exception as e:
            messagebox.showerror("Load Error", str(e))

    def export_png(self):
        try:
            from PIL import Image
        except ImportError:
            messagebox.showerror(
                "Missing Dependency",
                "Pillow is required for PNG export.\nInstall with: pip install Pillow"
            )
            return
        filepath = filedialog.asksaveasfilename(
            defaultextension=".png", filetypes=[("PNG files", "*.png")], initialfile="pixel_art.png"
        )
        if not filepath:
            return
        img = Image.new("RGB", (GRID_SIZE, GRID_SIZE))
        for y in range(GRID_SIZE):
            for x in range(GRID_SIZE):
                img.putpixel((x, y), self.pixels[y][x])
        img.save(filepath)
        self.status_label.config(text=f"Exported to {os.path.basename(filepath)}")


def main():
    root = tk.Tk()
    PixelDrawpad(root)
    root.mainloop()


if __name__ == "__main__":
    main()