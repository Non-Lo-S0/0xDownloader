"""
0xDownloader - Package update system
Handles requirements parsing, pip checking, package installation, and update GUI
"""

import os
import sys
import subprocess
import threading
import time
import re
from pathlib import Path

import tkinter as tk
from tkinter import ttk

import config as cfg

# =====================================================
# CUSTOM WIDGET: RAINBOW TITLE
# =====================================================


class RainbowTitle(tk.Frame):
    """Title widget with animated RGB gradient"""

    def __init__(self, parent, text, font, bg):
        super().__init__(parent, bg=bg)
        self.text = text
        self.labels = []
        self.phase = 0.0
        self._animate_active = True

        for char in text:
            lbl = tk.Label(self, text=char, font=font, bg=bg, bd=0, padx=0, pady=0)
            lbl.pack(side="left")
            self.labels.append(lbl)

        self.animate()

    def animate(self):
        if not self.winfo_exists() or not self._animate_active:
            return

        colors = cfg.UPDATER_RAINBOW_COLORS
        if not colors:
            return

        speed = cfg.UPDATER_RAINBOW_SPEED
        width = cfg.UPDATER_RAINBOW_WAVE_WIDTH
        num_colors = len(colors)

        for i, lbl in enumerate(self.labels):
            # Wave scrolls Left to Right with MINUS sign
            val = (self.phase - i * width) % num_colors

            idx1 = int(val) % num_colors
            idx2 = (idx1 + 1) % num_colors

            fraction = val - int(val)

            c1 = colors[idx1]
            c2 = colors[idx2]

            color = self._interpolate(c1, c2, fraction)
            lbl.config(fg=color)

        self.phase += speed
        self.after(20, self.animate)

    def _interpolate(self, c1, c2, f):
        """Interpolate between two hex colors"""
        try:
            rgb1 = tuple(int(c1[i : i + 2], 16) for i in (1, 3, 5))
            rgb2 = tuple(int(c2[i : i + 2], 16) for i in (1, 3, 5))

            r = int(rgb1[0] + (rgb2[0] - rgb1[0]) * f)
            g = int(rgb1[1] + (rgb2[1] - rgb1[1]) * f)
            b = int(rgb1[2] + (rgb2[2] - rgb1[2]) * f)

            r = max(0, min(255, r))
            g = max(0, min(255, g))
            b = max(0, min(255, b))

            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception:
            return c1

    def destroy(self):
        self._animate_active = False
        super().destroy()


# =====================================================
# REQUIREMENTS PARSER
# =====================================================


class RequirementsParser:
    """Extracts package names from requirements.txt"""

    @staticmethod
    def parse() -> list[str]:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        req_file = os.path.join(current_dir, "requirements.txt")

        if not os.path.exists(req_file):
            return []

        try:
            pkgs = []
            with open(req_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        package = (
                            re.split(r"[><=~!]", line.split("#")[0])[0].strip().lower()
                        )
                        if package:
                            pkgs.append(package)
            return list(set(pkgs))
        except Exception as e:
            print(f"Requirements read error: {e}")
            return []


# =====================================================
# PIP MANAGEMENT
# =====================================================


class PipManager:
    """Handles checking and installing pip"""

    @staticmethod
    def check_pip() -> bool:
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "--version"],
                capture_output=True,
                check=True,
            )
            return True
        except:
            return False

    @staticmethod
    def install_pip() -> bool:
        try:
            subprocess.run([sys.executable, "-m", "ensurepip", "--upgrade"], check=True)
            return True
        except Exception as e:
            print(f"PIP installation error: {e}")
            return False


# =====================================================
# PACKAGE MANAGEMENT
# =====================================================


class PackageManager:
    """Handles version checks and package installation"""

    @staticmethod
    def get_package_info(package: str) -> tuple[str, str]:
        """Returns (Installed Version, Latest Version)"""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "show", package],
                capture_output=True,
                text=True,
                timeout=5,
            )

            installed = "-"
            for line in result.stdout.splitlines():
                if line.startswith("Version:"):
                    installed = line.split(":", 1)[1].strip()
                    break

            try:
                latest_result = subprocess.run(
                    [sys.executable, "-m", "pip", "index", "versions", package],
                    capture_output=True,
                    text=True,
                    timeout=8,
                )

                latest = installed if installed != "-" else "?"

                for line in latest_result.stdout.splitlines():
                    if "Available versions:" in line:
                        versions = [
                            v.strip()
                            for v in line.split(":")[1].split(",")
                            if v.strip()
                        ]
                        if versions:
                            latest = versions[0]
                            break

            except subprocess.TimeoutExpired:
                latest = installed if installed != "-" else "?"
            except Exception:
                latest = installed if installed != "-" else "?"

            return installed, latest

        except:
            return "-", "?"

    @staticmethod
    def install_or_upgrade(package: str, log_callback) -> tuple[bool, str]:
        """Installs or upgrades a package, logging the output"""
        try:
            cmd = [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--upgrade",
                "--no-cache-dir",
                "--no-input",
                "--disable-pip-version-check",
                package,
            ]

            startupinfo = None
            if os.name == "nt":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                encoding="utf-8",
                errors="replace",
                startupinfo=startupinfo,
            )

            for line in process.stdout:
                if line.strip():
                    log_callback(f" > {line.strip()}")

            process.wait()

            if process.returncode == 0:
                new_ver_res = subprocess.run(
                    [sys.executable, "-m", "pip", "show", package],
                    capture_output=True,
                    text=True,
                )
                for line in new_ver_res.stdout.splitlines():
                    if line.startswith("Version:"):
                        return True, line.split(":", 1)[1].strip()
                return True, "Ok"
            else:
                return False, f"Exit Code {process.returncode}"

        except Exception as e:
            log_callback(f"CRITICAL ERROR: {e}")
            return False, str(e)


# =====================================================
# UPDATE GUI
# =====================================================


class AutoUpdaterGUI:
    """Graphical interface for package updating"""

    WINDOW_WIDTH = cfg.UPDATER_WINDOW_WIDTH
    WINDOW_HEIGHT = cfg.UPDATER_WINDOW_HEIGHT
    CARD_WIDTH = cfg.UPDATER_CARD_WIDTH
    PROGRESS_STEPS = cfg.UPDATER_PROGRESS_STEPS
    BLINK_INTERVAL = cfg.UPDATER_BLINK_INTERVAL

    def __init__(self, root, packages, statuses):
        self.root = root
        self.root.title = cfg.UPDATER_TITLE_TEXT

        w, h = self.WINDOW_WIDTH, self.WINDOW_HEIGHT
        ws = self.root.winfo_screenwidth()
        hs = self.root.winfo_screenheight()
        x = (ws // 2) - (w // 2)
        y = (hs // 2) - (h // 2)
        self.root.geometry(f"{w}x{h}+{x}+{y}")

        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.root.configure(bg=cfg.COLOR_BG)

        self.statuses = statuses
        self.card_widgets = {}

        self._create_ui()

        self.root.after(500, self._init_process)

    def _on_closing(self):
        pass

    def _safe_close(self):
        """Prevents Tcl errors during window destruction"""
        try:
            if hasattr(self, "canvas"):
                self.canvas.config(yscrollcommand=None)
            if hasattr(self, "log_text"):
                self.log_text.config(yscrollcommand=None)

            self.root.destroy()
        except Exception:
            pass

    def _create_ui(self):
        # --- HEADER ---
        header = tk.Frame(self.root, bg=cfg.COLOR_BG, height=60)
        header.pack(fill="x")

        title_container = tk.Frame(header, bg=cfg.COLOR_BG)
        title_container.pack(pady=5)

        RainbowTitle(
            title_container,
            text="📦 0xDownloader Updater",
            font=cfg.FONT_UPDATER_TITLE,
            bg=cfg.COLOR_BG,
        ).pack()

        # --- MAIN CONTAINER ---
        container = tk.Frame(self.root, bg=cfg.COLOR_BG)
        container.pack(fill="both", expand=True, padx=20, pady=0)

        self.status_label = tk.Label(
            container,
            text="  ⏳ Installation in progress, do not close this window",
            font=cfg.FONT_UPDATER,
            bg=cfg.COLOR_BG,
            fg=cfg.COLOR_TEXT_WHITE,
        )
        self.status_label.pack(anchor="w", pady=(0, 10))

        # --- PACKAGES GRID ---
        dash = tk.Frame(container, bg=cfg.COLOR_TERMINAL_BG)
        dash.pack(fill="both", expand=True, pady=(0, 15), padx=15)

        c_frame = tk.Frame(dash, bg=cfg.COLOR_TERMINAL_BG)
        c_frame.pack(fill="both", expand=True)

        v_bar = ttk.Scrollbar(
            c_frame, orient="vertical", style="Hidden.Vertical.TScrollbar"
        )

        self.canvas = tk.Canvas(
            c_frame,
            bg=cfg.COLOR_TERMINAL_BG,
            highlightthickness=0,
            yscrollcommand=v_bar.set,
        )
        self.canvas.pack(side="left", fill="both", expand=True)
        v_bar.config(command=self.canvas.yview)

        self.scroll_frame = tk.Frame(self.canvas, bg=cfg.COLOR_TERMINAL_BG)
        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")

        self.root.after(
            100, lambda: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        # --- LOG CONSOLE ---
        log_frame = tk.Frame(container, bg=cfg.COLOR_BG)
        log_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15), side="bottom")

        log_inner = tk.Frame(log_frame, bg=cfg.COLOR_BG)
        log_inner.pack(fill="both", expand=True, padx=0, pady=0)

        log_scroll = ttk.Scrollbar(log_inner, orient="vertical")

        self.log_text = tk.Text(
            log_inner,
            height=8,
            bg=cfg.COLOR_TERMINAL_BG,
            fg=cfg.COLOR_ACCENT,
            font=cfg.FONT_LOG_UPDATER,
            relief="flat",
            padx=10,
            pady=10,
            yscrollcommand=log_scroll.set,
        )
        self.log_text.pack(side="left", fill="both", expand=True)
        log_scroll.config(command=self.log_text.yview)

    def _log(self, msg: str):
        ts = time.strftime("%H:%M:%S")
        try:
            self.root.after(
                0,
                lambda: [
                    self.log_text.insert("end", f"[{ts}] {msg}\n"),
                    self.log_text.see("end"),
                ],
            )
        except:
            pass

    def _init_process(self):
        self._build_grid()
        self.root.after(1000, self._start_updates)

    def _build_grid(self):
        for w in self.scroll_frame.winfo_children():
            w.destroy()

        window_width = self.root.winfo_width()
        cols = max(1, (window_width - 60) // (self.CARD_WIDTH + 20))

        for i, (pkg, info) in enumerate(self.statuses.items()):
            missing = info["installed"] in ["-", "none"]
            outdated = info["installed"] != info["latest"] and not missing

            if missing:
                color = cfg.COLOR_CRITICAL
                ver_text = f"ↆ N/A -> {info['latest']}"
                text_color = cfg.COLOR_TEXT_WHITE
            elif outdated:
                color = cfg.COLOR_WARNING
                ver_text = f"⚠️ {info['installed']} -> {info['latest']}"
                text_color = "black"
            else:
                color = cfg.COLOR_SUCCESS
                ver_text = f"✅ {info['installed']} -> {info['latest']}"
                text_color = cfg.COLOR_TEXT_WHITE

            card = tk.Frame(
                self.scroll_frame, bg=color, width=180, height=80, relief="flat"
            )
            card.grid(row=i // cols, column=i % cols, padx=10, pady=10)
            card.pack_propagate(False)

            inner_frame = tk.Frame(card, bg=color)
            inner_frame.pack(expand=True, fill="both", padx=5, pady=5)

            title_lbl = tk.Label(
                inner_frame,
                text=pkg.upper(),
                font=cfg.FONT_PACK_TITLE,
                bg=color,
                fg=text_color,
            )
            title_lbl.pack(expand=True)

            lbl_v = tk.Label(
                inner_frame,
                text=ver_text,
                font=cfg.FONT_VER_UPDATER,
                bg=color,
                fg=text_color,
                justify="center",
            )
            lbl_v.pack(expand=True)

            self.card_widgets[pkg] = {
                "card": card,
                "inner_frame": inner_frame,
                "title_lbl": title_lbl,
                "lbl_v": lbl_v,
                "blinking": False,
            }

        self.root.after(
            50, lambda: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

    def _blink_card(
        self, pkg: str, base_color: str, blink_count: int = 0, phase: str = "fade_out"
    ):
        """Smooth blinking animation for card"""
        w = self.card_widgets.get(pkg)
        if not w:
            return

        if not w.get("blinking", False):
            return

        blink_color = cfg.COLOR_BLINK
        steps = self.PROGRESS_STEPS

        if phase == "fade_out":
            progress = (blink_count % steps) / steps
            current_color = self._interpolate_color(base_color, blink_color, progress)

            w["card"].config(bg=current_color)
            w["inner_frame"].config(bg=current_color)

            text_color = (
                "black" if current_color == cfg.COLOR_WARNING else cfg.COLOR_TEXT_WHITE
            )
            for label_key in ["title_lbl", "lbl_v"]:
                if label_key in w:
                    w[label_key].config(bg=current_color, fg=text_color)

            if blink_count < steps - 1:
                self.root.after(
                    self.BLINK_INTERVAL,
                    lambda: self._blink_card(
                        pkg, base_color, blink_count + 1, "fade_out"
                    ),
                )
            else:
                self.root.after(
                    self.BLINK_INTERVAL,
                    lambda: self._blink_card(pkg, base_color, 0, "fade_in"),
                )

        elif phase == "fade_in":
            progress = (blink_count % steps) / steps
            current_color = self._interpolate_color(blink_color, base_color, progress)

            w["card"].config(bg=current_color)
            w["inner_frame"].config(bg=current_color)

            text_color = (
                "black" if current_color == cfg.COLOR_WARNING else cfg.COLOR_TEXT_WHITE
            )
            for label_key in ["title_lbl", "lbl_v"]:
                if label_key in w:
                    w[label_key].config(bg=current_color, fg=text_color)

            if blink_count < steps - 1:
                self.root.after(
                    self.BLINK_INTERVAL,
                    lambda: self._blink_card(
                        pkg, base_color, blink_count + 1, "fade_in"
                    ),
                )
            else:
                self.root.after(
                    self.BLINK_INTERVAL,
                    lambda: self._blink_card(pkg, base_color, 0, "fade_out"),
                )

    @staticmethod
    def _interpolate_color(color1: str, color2: str, progress: float) -> str:
        c1 = tuple(int(color1[i : i + 2], 16) for i in (1, 3, 5))
        c2 = tuple(int(color2[i : i + 2], 16) for i in (1, 3, 5))

        r = int(c1[0] + (c2[0] - c1[0]) * progress)
        g = int(c1[1] + (c2[1] - c1[1]) * progress)
        b = int(c1[2] + (c2[2] - c1[2]) * progress)

        return f"#{r:02x}{g:02x}{b:02x}"

    def _update_card_ui(self, pkg: str, state: str, new_v: str = None):
        w = self.card_widgets.get(pkg)
        if not w:
            return

        if state == "working":
            color = cfg.COLOR_UPDATING
            latest = self.statuses.get(pkg, {}).get("latest", "?")
            text = f"⏳ installation -> {latest}"

            w["card"].config(bg=color)
            w["inner_frame"].config(bg=color)
            w["title_lbl"].config(bg=color)
            w["lbl_v"].config(bg=color, text=text)

            w["blinking"] = True
            self.root.after(0, lambda: self._blink_card(pkg, color, 0, "fade_out"))

        elif state == "done":
            color = cfg.COLOR_SUCCESS
            text = f"✅ {new_v} -> {new_v}"

            w["blinking"] = False
            w["card"].config(bg=color)
            w["inner_frame"].config(bg=color)
            w["title_lbl"].config(bg=color)
            w["lbl_v"].config(bg=color, text=text)

        elif state == "error":
            color = cfg.COLOR_CRITICAL
            text = "❗ error"

            w["blinking"] = False
            w["card"].config(bg=color)
            w["inner_frame"].config(bg=color)
            w["title_lbl"].config(bg=color)
            w["lbl_v"].config(bg=color, text=text)

    def _start_updates(self):
        to_install = [
            p
            for p, i in self.statuses.items()
            if i["installed"] != i["latest"] or i["installed"] in ["-", "none"]
        ]

        if not to_install:
            self._log("✅ No packages to install.")
            self.root.after(0, self._safe_close)
            return

        self._log(f"🚀 Starting installation of {len(to_install)} packages...")

        def run():
            for pkg in to_install:
                self.root.after(0, lambda p=pkg: self._update_card_ui(p, "working"))
                self._log(f"--- Installing {pkg} ---")

                success, result = PackageManager.install_or_upgrade(pkg, self._log)

                if success:
                    self.root.after(
                        0, lambda p=pkg, v=result: self._update_card_ui(p, "done", v)
                    )
                    self._log(f"✅ {pkg} installed successfully.")
                else:
                    self.root.after(0, lambda p=pkg: self._update_card_ui(p, "error"))
                    self._log(f"❌ FAILED {pkg}: {result}")
                    self._log(
                        "💡 Make sure you are connected to the internet and have the required permissions."
                    )

            self._log("=" * 40)
            self._log("✅ Process completed. Launching 0xDownloader...")

            time.sleep(3)
            self.root.after(0, self._safe_close)

        threading.Thread(target=run, daemon=True).start()


# =====================================================
# ENTRY POINT
# =====================================================

if __name__ == "__main__":
    print("⚠️ Run main.py instead of this file")
