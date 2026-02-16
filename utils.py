"""
0xDownloader - Utility functions

Handles filesystem operations, byte formatting, custom console logging with color tags,
folder opening, and cleanup of temporary download files.
"""

import os
import re
import subprocess
import time
import tkinter as tk
import platform
import config as cfg

# ============================================================================
# FILESYSTEM UTILITIES
# ============================================================================


def setup_download_directory(folder_name="downloads"):
    path = os.path.join(os.getcwd(), folder_name)
    if not os.path.exists(path):
        os.makedirs(path)
    return path


def format_bytes(size):
    if size is None or size <= 0:
        return "..."
    power = 1024
    n = 0
    power_labels = {0: "", 1: "K", 2: "M", 3: "G", 4: "T"}
    while size > power:
        size /= power
        n += 1
    return f"{size:.2f} {power_labels.get(n, '')}B"


# ============================================================================
# GUI / SYSTEM UTILITIES
# ============================================================================


class CustomConsoleWriter:
    def __init__(self, text_widget):
        self.text_widget = text_widget

        self.text_widget.tag_config(
            "TIME", foreground=cfg.LOG_COLOR_TIME, font=cfg.FONT_LOG
        )
        self.text_widget.tag_config(
            "SEP", foreground=cfg.LOG_COLOR_SEP, font=cfg.FONT_LOG
        )
        self.text_widget.tag_config(
            "NORMAL", foreground=cfg.LOG_COLOR_DEFAULT, font=cfg.FONT_LOG
        )
        self.text_widget.tag_config(
            "SUCCESS", foreground=cfg.LOG_COLOR_SUCCESS, font=cfg.FONT_LOG
        )
        self.text_widget.tag_config(
            "ERROR", foreground=cfg.LOG_COLOR_ERROR, font=cfg.FONT_LOG
        )
        self.text_widget.tag_config(
            "WARN", foreground=cfg.LOG_COLOR_WARN, font=cfg.FONT_LOG
        )
        self.text_widget.tag_config(
            "INFO", foreground=cfg.LOG_COLOR_INFO, font=cfg.FONT_LOG
        )
        self.text_widget.tag_config(
            "FFMPEG", foreground=cfg.LOG_COLOR_FFMPEG, font=cfg.FONT_LOG
        )
        self.text_widget.tag_config(
            "HEADER", foreground=cfg.LOG_COLOR_HEADER, font=("Consolas", 9, "bold")
        )

    def write(self, text):
        if not text or text.isspace():
            return

        ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        text = ansi_escape.sub("", text)

        # keep original for rule checks
        original_text = text

        # strip bracketed tags like [INFO], [ERROR] from the visible message
        clean_text = re.sub(r"\[.*?\]", "", text).strip()
        if not clean_text:
            return

        # noise filters
        if "%" in original_text and "MiB/s" in original_text:
            return
        if "Destination:" in original_text:
            return
        if "Deleting" in original_text:
            return
        if "Merging video & audio into container" in clean_text:
            return

        row_tag = "NORMAL"
        label = "SYSTEM"

        # Pause / Resume (new)
        if (
            "download paused" in clean_text.lower()
            or "paused download" in clean_text.lower()
        ):
            row_tag = "WARN"
            label = "PAUSE"
            clean_text = "⏸ Download paused"
        elif (
            "download resumed" in clean_text.lower()
            or "resumed download" in clean_text.lower()
        ):
            row_tag = "INFO"
            label = "PAUSE"
            clean_text = "▶ Download resumed"

        # Abort
        elif "ABORTED" in original_text or "Aborted" in original_text:
            row_tag = "ERROR"
            label = "ABORT"
            clean_text = "⚠️ Operation interrupted by the user"

        # Errors
        elif "ERROR" in original_text or "FAILED" in original_text:
            row_tag = "ERROR"
            label = "ERROR"

        # Success
        elif "completed" in original_text and (
            "download" in original_text.lower() or "(" in original_text
        ):
            row_tag = "SUCCESS"
            label = "SUCCESS"
            clean_text = "✨ Operation completed"

        # ffmpeg / merging
        elif "Muxing" in original_text or "Merger" in original_text:
            row_tag = "FFMPEG"
            label = "MERGING"
            clean_text = "Merging Audio/Video streams..."
        elif "ExtractAudio" in original_text:
            row_tag = "FFMPEG"
            label = "FFMPEG"
            clean_text = "Extracting audio track..."

        # yt-dlp download stages
        elif "Downloading" in original_text:
            row_tag = "INFO"
            label = "YOUTUBE"
            if "video" in clean_text.lower():
                clean_text = "Downloading video stream..."
            elif "audio" in clean_text.lower():
                clean_text = "Downloading audio stream..."
            else:
                clean_text = "Download in progress..."
        elif "Analyzing metadata" in original_text:
            row_tag = "INFO"
            label = "YOUTUBE"
            clean_text = "Analyzing metadata..."
        elif "Starting download" in original_text:
            row_tag = "INFO"
            label = "YOUTUBE"
            clean_text = "Starting download..."

        # headers
        elif any(
            x in original_text
            for x in ["Title:", "File:", "Size:", "Quality:", "Resolution:"]
        ):
            row_tag = "HEADER"
            label = "INFO"
            if "Title:" in original_text:
                clean_text = original_text.replace("Title:", "📺 Title:").strip()
            if "File:" in original_text:
                clean_text = original_text.replace("File:", "💾 File:").strip()
            if "Size:" in original_text:
                clean_text = original_text.replace("Size:", "📦 Size:").strip()
            if "Quality:" in original_text:
                clean_text = original_text.replace("Quality:", "💎 Quality:").strip()

        if clean_text:
            self.text_widget.configure(state="normal")

            timestamp = time.strftime("%H:%M:%S")
            self.text_widget.insert(tk.END, f"[{timestamp}]", "TIME")
            self.text_widget.insert(tk.END, " | ", "SEP")
            self.text_widget.insert(tk.END, f"{label:^10}", row_tag)
            self.text_widget.insert(tk.END, " | ", "SEP")
            self.text_widget.insert(tk.END, f"{clean_text}\n", row_tag)

            self.text_widget.see(tk.END)
            self.text_widget.configure(state="disabled")

    def flush(self):
        pass


def open_folder(path):
    path = os.path.abspath(path)
    try:
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception as e:
        print(f"[ERR] Cannot open folder: {e}")


def perform_cleanup(file_path):
    target_dir = os.path.join(os.getcwd(), "downloads")

    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass

    if file_path:
        filename = os.path.basename(file_path)
        clean_name = filename.replace(".part", "")
        if "." in clean_name:
            clean_name = os.path.splitext(clean_name)[0]

        if os.path.exists(target_dir):
            for f in os.listdir(target_dir):
                if f.startswith(clean_name) and (".part" in f or ".ytdl" in f):
                    try:
                        os.remove(os.path.join(target_dir, f))
                    except Exception:
                        pass
