"""
0xDownloader - Download logic core

Handles YouTube video/audio downloads with throttling management, progress tracking,
and format conversion.
"""

import os
import time
import sys
import re
import yt_dlp
import config as cfg
from yt_dlp.utils import sanitize_filename
from collections import deque


class ThrottleManager:
    def __init__(self):
        self.is_throttled = False
        self.retry_count = 0
        self.last_throttle_time = 0

    def detect_throttling(self, error_msg: str) -> bool:
        """Detect whether the error message indicates throttling / rate-limiting."""
        error_lower = str(error_msg).lower()
        throttle_indicators = [
            "throttling",
            "429",
            "too many requests",
            "rate limit",
            "slow down",
            "temporary failure",
        ]
        return any(indicator in error_lower for indicator in throttle_indicators)

    def get_retry_delay(self) -> int:
        """Exponential backoff delay (capped)."""
        base_delay = cfg.THROTTLE_RETRY_DELAY
        delay = base_delay * (cfg.THROTTLE_BACKOFF_MULTIPLIER**self.retry_count)
        return min(int(delay), 300)

    def should_retry(self) -> bool:
        return self.retry_count < cfg.THROTTLE_MAX_RETRIES

    def mark_throttled(self):
        self.is_throttled = True
        self.retry_count += 1
        self.last_throttle_time = time.time()

    def reset(self):
        self.is_throttled = False
        self.retry_count = 0


def get_real_total_size(url, ydl_opts, throttle_manager=None):
    try:
        opts = ydl_opts.copy()
        opts["quiet"] = True
        opts["simulate"] = True
        opts.pop("concurrent_fragment_downloads", None)

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)

        title = info.get("title", "Unknown")

        if "requested_formats" in info:
            total = sum(
                f.get("filesize") or f.get("filesize_approx") or 0
                for f in info["requested_formats"]
            )
            return total, title

        return info.get("filesize") or info.get("filesize_approx") or 0, title

    except Exception as e:
        if throttle_manager and throttle_manager.detect_throttling(str(e)):
            throttle_manager.mark_throttled()
            raise Exception("THROTTLING_DETECTED")
        return 0, "Unknown"


def run_download(url, resolution, handler, callbacks):
    download_path = os.path.join(os.getcwd(), cfg.DL_FOLDER_NAME)
    if not os.path.exists(download_path):
        os.makedirs(download_path)

    progress_callback = callbacks.get("progress")
    stage_callback = callbacks.get("stage")
    check_abort = callbacks.get("check_abort")
    check_pause = callbacks.get("check_pause")

    if stage_callback:
        stage_callback("downloading")

    final_filename = None
    throttle_manager = ThrottleManager()

    ydl_opts = {
        "quiet": False,
        "no_warnings": True,
        "nocheckcertificate": True,
        "concurrent_fragment_downloads": cfg.DL_CONCURRENT_FRAGMENTS,
        "speed_history_len": cfg.DL_SPEED_HISTORY_LEN,
        "socket_timeout": cfg.DL_SOCKET_TIMEOUT,
        "retries": cfg.DL_RETRIES,
        "fragment_retries": cfg.DL_RETRIES,
        "file_access_retries": cfg.DL_FILE_ACCESS_RETRIES,
        "no_continue": True,
        "part": True,
        "geo_bypass": True,
        "http_chunk_size": cfg.DL_HTTP_CHUNK_SIZE,
    }

    if "Audio" in resolution:
        ydl_opts["format"] = "bestaudio/best"
        ydl_opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": cfg.DL_AUDIO_QUALITY,
            }
        ]
        final_ext = "mp3"
        target_h = "Audio"
    else:
        res_key = resolution.lower().strip()
        nums = re.findall(r"\d{3,4}", res_key)
        hmap = {"4k": 2160, "hd": 1080}
        h = int(nums[0]) if nums else hmap.get(res_key, 1080)
        target_h = h

        format_str = (
            f"bestvideo[height={h}]+bestaudio/" f"bestvideo[height<={h}]+bestaudio/best"
        )
        ydl_opts["format"] = format_str
        ydl_opts["merge_output_format"] = "mp4"
        ydl_opts["postprocessor_args"] = {
            "ffmpeg": ["-c:v", "copy", "-c:a", "aac", "-b:a", cfg.DL_AUDIO_BITRATE]
        }
        final_ext = "mp4"

    print("[INFO] Analyzing metadata (Default Client)...")

    try:
        global_total_bytes, video_title = get_real_total_size(
            url, ydl_opts, throttle_manager
        )
    except Exception as e:
        if "THROTTLING_DETECTED" in str(e):
            if throttle_manager.should_retry():
                delay = throttle_manager.get_retry_delay()
                print(
                    f"[WARNING] Throttling detected. Waiting {delay}s before retry..."
                )
                time.sleep(delay)
                return run_download(url, resolution, handler, callbacks)
            print("[ERROR] Max throttling retries reached. Aborting.")
            return False, None
        raise

    basename = sanitize_filename(video_title)
    candidate_name = basename
    counter = 1
    while os.path.exists(os.path.join(download_path, f"{candidate_name}.{final_ext}")):
        candidate_name = f"{basename} ({counter})"
        counter += 1

    full_final_path = os.path.join(download_path, f"{candidate_name}.{final_ext}")
    ydl_opts["outtmpl"] = os.path.join(download_path, f"{candidate_name}.%(ext)s")

    size_mb = (global_total_bytes / 1024 / 1024) if global_total_bytes else 0
    print(f"[HEADER] Title: {video_title[:40]}...")
    print(f"[HEADER] File: {candidate_name}.{final_ext}")
    print(f"[HEADER] Size: {size_mb:.2f} MB")
    print(f"[HEADER] Quality: {target_h}p")

    print("[BLUE] Initializing streams...")
    print("[WARNING] Downloading file...")

    state = {
        "finished_files_bytes": 0,
        "current_file_bytes": 0,
        "files_downloaded_count": 0,
    }

    speed_buffer = deque(maxlen=cfg.DL_SMOOTHING_WINDOW)
    last_ui_update_time = 0
    is_in_postprocessing = False

    def _pause_gate():
        """Hard pause gate: blocks the download thread while paused."""
        while check_pause and check_pause():
            if check_abort and check_abort():
                raise yt_dlp.utils.DownloadError("Aborted by user")
            time.sleep(0.2)

    def progress_hook(d):
        nonlocal last_ui_update_time, final_filename, is_in_postprocessing

        _pause_gate()

        if is_in_postprocessing:
            if check_abort and check_abort():
                raise yt_dlp.utils.DownloadError("Aborted by user")
            return

        if check_abort and check_abort():
            d["status"] = "aborted"
            raise yt_dlp.utils.DownloadError("Aborted by user")

        if d.get("filename"):
            final_filename = d["filename"]

        if d["status"] == "downloading":
            current_time = time.time()

            state["current_file_bytes"] = d.get("downloaded_bytes", 0)
            actual_downloaded = (
                state["finished_files_bytes"] + state["current_file_bytes"]
            )

            p = (
                (actual_downloaded / global_total_bytes) * 100
                if global_total_bytes
                else 0
            )
            if p > 99.9:
                p = 99.9

            raw_speed = d.get("speed")
            if raw_speed and raw_speed > 0:
                speed_buffer.append(raw_speed)

            avg_speed = (sum(speed_buffer) / len(speed_buffer)) if speed_buffer else 0

            if (current_time - last_ui_update_time > cfg.DL_UI_UPDATE_DELAY) or (
                p >= 99.0
            ):
                last_ui_update_time = current_time

                eta = d.get("eta")
                spd_str = (
                    f"{avg_speed/1024/1024:.2f} MB/s" if avg_speed > 0 else "-- MB/s"
                )

                if eta is None:
                    eta_str = "--:--"
                else:
                    m, s = divmod(int(eta), 60)
                    if m >= 60:
                        h, m = divmod(m, 60)
                        eta_str = f"{int(h)}:{int(m):02}:{int(s):02}"
                    else:
                        eta_str = f"{int(m):02}:{int(s):02}"

                sz_str = (
                    f"{global_total_bytes/1024/1024:.1f} MB"
                    if global_total_bytes
                    else "---"
                )

                if progress_callback:
                    progress_callback(p, spd_str, eta_str, sz_str)

        elif d["status"] == "finished":
            state["finished_files_bytes"] += d.get("total_bytes", 0)
            state["current_file_bytes"] = 0
            state["files_downloaded_count"] += 1

            final_filename = d.get("filename", final_filename)

            file_type = (
                "Audio Track"
                if "Audio" in resolution
                else (
                    "Video Stream"
                    if state["files_downloaded_count"] == 1
                    else "Audio Stream"
                )
            )
            file_size_mb = (
                (d.get("total_bytes", 0) / 1024 / 1024) if d.get("total_bytes") else 0
            )
            print(f"[SUCCESS] {file_type} completed ({file_size_mb:.1f} MB)")

    def postprocessor_hook(d):
        nonlocal is_in_postprocessing

        _pause_gate()

        if d.get("status") == "started":
            if not is_in_postprocessing:
                is_in_postprocessing = True
                if stage_callback:
                    stage_callback("merging")
                print("[BLUE] Merging video & audio into container...")
                sys.stdout.flush()

    ydl_opts["progress_hooks"] = [progress_hook]
    ydl_opts["postprocessor_hooks"] = [postprocessor_hook]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        if not is_in_postprocessing:
            is_in_postprocessing = True
            if stage_callback:
                stage_callback("merging")

        throttle_manager.reset()
        return True, full_final_path

    except Exception as e:
        error_msg = str(e)

        if throttle_manager.detect_throttling(error_msg):
            if throttle_manager.should_retry():
                delay = throttle_manager.get_retry_delay()
                print(
                    f"[WARNING] Throttling detected during download. Waiting {delay}s..."
                )
                time.sleep(delay)
                return run_download(url, resolution, handler, callbacks)
            print("[ERROR] Max throttling retries reached.")
            return False, final_filename if final_filename else full_final_path

        if "Aborted" in error_msg:
            return False, final_filename if final_filename else full_final_path

        print(f"[ERROR] Error: {e}")
        return False, None
