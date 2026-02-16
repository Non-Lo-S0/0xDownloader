import sys
import os
import subprocess
import tkinter as tk
from tkinter import messagebox

def is_frozen():
    return getattr(sys, 'frozen', False)

# Logica di avvio
if not is_frozen() and "--verified" not in sys.argv:
    checker_path = "checker.py"
    if os.path.exists(checker_path):
        subprocess.Popen([sys.executable, checker_path])
        sys.exit()

import interface

if __name__ == "__main__":
    root = tk.Tk()
    app = interface.OxUI(root)
    root.mainloop()
