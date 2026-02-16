"""
0xDownloader - Launcher with dependency checks
Checks PIP and packages, then launches the update GUI or the main app
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import sys
import os
import subprocess
import time


import config as cfg


# =====================================================
# MODULE IMPORT HANDLING
# =====================================================


try:
    from updater import RequirementsParser, PipManager, PackageManager, AutoUpdaterGUI
except ImportError as e:
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(
        "Critical Error", f"File 'updater.py' is missing or corrupted!\n\nDetails: {e}"
    )
    sys.exit()


# =====================================================
# MAIN CLASS
# =====================================================


class MiniSplashLauncher:
    """Launcher with a splash screen that checks dependencies before starting main.py"""

    MIN_DISPLAY_TIME = cfg.CHECKER_MIN_DISPLAY_TIME
    WINDOW_WIDTH = cfg.CHECKER_WINDOW_WIDTH
    WINDOW_HEIGHT = cfg.CHECKER_WINDOW_HEIGHT
    PROGRESS_LENGTH = cfg.CHECKER_PROGRESS_LENGTH

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("0xDownloader Checker")

        self.scan_results = {"needed": False, "pkgs": [], "statuses": {}}
        self.progress = None
        self.lbl_status = None

        self._setup_ui()

        threading.Thread(target=self._run_logic, daemon=True).start()

        self.root.mainloop()

    def _setup_ui(self):
        """Configure the splash screen interface"""

        w, h = self.WINDOW_WIDTH, self.WINDOW_HEIGHT
        ws = self.root.winfo_screenwidth()
        hs = self.root.winfo_screenheight()
        x = (ws // 2) - (w // 2)
        y = (hs // 2) - (h // 2)
        self.root.geometry(f"{w}x{h}+{x}+{y}")

        self.root.configure(bg=cfg.COLOR_BG)
        self.root.attributes("-topmost", True)
        self.root.resizable(False, False)

        tk.Frame(self.root, bg=cfg.COLOR_BG, height=2).pack(fill="x", side="top")

        self.lbl_status = tk.Label(
            self.root,
            text="Initializing system...",
            font=cfg.FONT_CHECKER,
            bg=cfg.COLOR_BG,
            fg=cfg.COLOR_TEXT_WHITE,
        )
        self.lbl_status.pack(pady=(35, 10))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Green.Horizontal.TProgressbar",
            background=cfg.COLOR_PROGRESS_BAR,
            troughcolor=cfg.COLOR_THROUGH,
            borderwidth=0,
            bordercolor=cfg.COLOR_BORDER,
            lightcolor=cfg.COLOR_PROGRESS_BAR,
            darkcolor=cfg.COLOR_PROGRESS_BAR,
        )

        self.progress = ttk.Progressbar(
            self.root,
            style="Green.Horizontal.TProgressbar",
            mode="indeterminate",
            length=self.PROGRESS_LENGTH,
        )
        self.progress.pack(pady=10)
        self.progress.start(25)

    def _run_logic(self):
        """Run the verification logic: PIP → Requirements → Versions"""

        start_time = time.time()

        # 1. Check and repair PIP
        self.root.after(0, lambda: self.lbl_status.config(text="Checking for PIP..."))
        if not PipManager.check_pip():
            self.root.after(0, lambda: self.lbl_status.config(text="Installing PIP..."))
            PipManager.install_pip()

        # 2. Read requirements
        self.root.after(
            0, lambda: self.lbl_status.config(text="Checking dependencies...")
        )
        pkgs = RequirementsParser.parse()
        statuses = {}
        updates_needed = False

        # 3. Version scan (multithreaded)
        if pkgs:
            threads = []
            lock = threading.Lock()

            def check_pkg(pkg):
                """Check the version of a single package"""
                nonlocal updates_needed
                installed, latest = PackageManager.get_package_info(pkg)
                with lock:
                    statuses[pkg] = {"installed": installed, "latest": latest}
                if installed in ["-", "none"] or installed != latest:
                    updates_needed = True

            for pkg in pkgs:
                t = threading.Thread(target=check_pkg, args=(pkg,))
                threads.append(t)
                t.start()

            for t in threads:
                t.join()

        self.scan_results = {
            "needed": updates_needed,
            "pkgs": pkgs,
            "statuses": statuses,
        }

        # --- MINIMUM DISPLAY TIME HANDLING ---
        elapsed = time.time() - start_time
        if elapsed < self.MIN_DISPLAY_TIME:
            time.sleep(self.MIN_DISPLAY_TIME - elapsed)

        self.root.after(0, self._finalize)

    def _finalize(self):
        """Finalize the splash screen and decide the next step"""

        # Stop progress bar animation
        current_position = self.progress["value"]
        self.progress.stop()
        self.progress["value"] = current_position

        if not self.scan_results["needed"]:
            # ✓ POSITIVE CASE: Everything up to date
            self.lbl_status.config(text="Starting...", fg=cfg.COLOR_SUCCESS)
            self.root.update()
            time.sleep(1.5)
            self.root.destroy()
            self._launch_main()
        else:
            # ✗ NEGATIVE CASE: Updates needed
            self.lbl_status.config(text="Updates are available", fg=cfg.COLOR_WARNING)
            self.root.update()
            time.sleep(1.5)
            self.root.destroy()
            self._launch_updater_gui()

    def _launch_updater_gui(self):
        """Launch the update GUI"""
        updater_root = tk.Tk()
        AutoUpdaterGUI(
            updater_root, self.scan_results["pkgs"], self.scan_results["statuses"]
        )
        updater_root.mainloop()

        # When the updater finishes, try launching main
        self._launch_main()

    def _launch_main(self):
        """Launch main.py with the --verified flag"""
        main_script = "main.py"

        if not os.path.exists(main_script):
            messagebox.showerror("Error", f"File '{main_script}' not found!")
            return

        try:
            subprocess.Popen([sys.executable, main_script, "--verified"])
            sys.exit()
        except Exception as e:
            messagebox.showerror("Launch Error", f"Unable to start main.py:\n{e}")
            sys.exit()


# =====================================================
# ENTRY POINT
# =====================================================


if __name__ == "__main__":
    MiniSplashLauncher()
