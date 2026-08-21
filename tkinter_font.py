import tkinter as tk
from tkinter import font

root = tk.Tk()

# Fetch and sort all font families available on your OS
available_fonts = sorted(list(font.families()))

for f in available_fonts:
    print(f)
