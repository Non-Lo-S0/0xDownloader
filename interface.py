"""
0xDownloader - User Interface

Handles the GUI application with Tkinter, including URL input, quality selection menu,
download progress visualization with animated ring, color theming, and all user interactions.
"""

import tkinter as tk
from tkinter import Canvas
import threading
import sys
import colorsys
import re
import time
from urllib.parse import urlparse
import math

import config as cfg
import utils
import logic

from modules.youtube import YouTubeVideoHandler


class OxUI:
    def __init__(self, root):
        self.root = root
        self.root.title(cfg.TITLE_TEXT)
        self.root.geometry(cfg.WINDOW_GEOMETRY)
        self.root.configure(bg=cfg.COLOR_BG)
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.url_var = tk.StringVar()
        self.current_theme_color = cfg.COLOR_DEFAULT_THEME

        self.resolutions = []
        self.audio_details_map = {}
        self.selected_res = tk.StringVar()

        self.is_analyzing = False
        self.is_downloading = False
        self.is_paused = False
        self.abort_requested = False
        self.pause_requested = False

        self.is_aborted_state = False
        self.is_error_state = False
        self.is_coming_soon = False
        self.is_menu_open = False
        self.is_input_disabled = False
        self.is_input_focused = False
        self.is_url_valid = False
        self.show_folder_btn = False
        self.is_download_completed = False
        self.is_merging = False
        self.is_throttled = False

        # Main button (Analyze / Ready / etc.)
        self.btn_pressed = False
        self.btn_hovered = False
        self.input_hovered = False

        # Folder button
        self.folder_btn_pressed = False
        self.folder_hovered = False

        # Split controls (Pause + Abort) shown during download
        self.split_controls_visible = False
        self.pause_hovered = False
        self.pause_pressed = False
        self.abort_hovered_small = False
        self.abort_pressed_small = False

        self.handler = None
        self.menu_canvas = None
        self.menu_buttons = []

        self.target_btn_color = cfg.COLOR_BTN_DEFAULT
        self.current_btn_color_rgb = self.hex_to_rgb(cfg.COLOR_BTN_DEFAULT)
        self.target_btn_text_color = cfg.COLOR_TEXT_DARK

        # We will switch this target between WARNING (Pause) and SUCCESS (Resume)
        self.target_pause_color = cfg.COLOR_BTN_PAUSE
        self.current_pause_color_rgb = self.hex_to_rgb(cfg.COLOR_BTN_PAUSE)

        self.target_abort_small_color = cfg.COLOR_BTN_ABORT
        self.current_abort_small_color_rgb = self.hex_to_rgb(cfg.COLOR_BTN_ABORT)

        self.target_input_border = "#333333"
        self.current_input_border_rgb = self.hex_to_rgb("#333333")

        self.target_folder_bg = cfg.COLOR_BTN_HOVER
        self.current_folder_bg_rgb = self.hex_to_rgb(cfg.COLOR_BTN_HOVER)

        # Lift offsets
        self.btn_offset_y = 0.0
        self.folder_offset_y = 0.0
        self.pause_offset_y = 0.0
        self.abort_small_offset_y = 0.0

        # Progress
        self.progress_target = 0.0
        self.progress_current = 0.0

        # Info cards
        self.display_speed = "0 B/s"
        self.display_eta = "--:--"
        self.display_data = "-"
        self.display_res_label = "---"

        # Title animation
        self.title_chars = []
        self.hue_shift = 0.0

        # Ring animation
        self.ring_frame_i = 0
        self.ring_frame_last = time.time()
        self.ring_frame_dt = cfg.ANIM_SPEED_RING

        s = cfg.GRID_SPACING
        self.grid_coords = [
            (-s, -s),
            (0, -s),
            (s, -s),
            (-s, 0),
            (0, 0),
            (s, 0),
            (-s, s),
            (0, s),
            (s, s),
        ]
        self.loading = cfg.LOADING

        self.ids = {}

        self.setup_ui()
        self.validate_ui_state()
        self.url_var.trace_add("write", self.on_url_change)

        self.run_animation_loop()
        print("SYSTEM ONLINE - Waiting for link...")

    # ============================================================================
    # COLOR UTILITIES
    # ============================================================================

    def hex_to_rgb(self, hex_val):
        try:
            hex_val = hex_val.lstrip("#")
            return tuple(int(hex_val[i : i + 2], 16) for i in (0, 2, 4))
        except Exception:
            return (0, 0, 0)

    def rgb_to_hex(self, rgb):
        return "#%02x%02x%02x" % (int(rgb[0]), int(rgb[1]), int(rgb[2]))

    def lerp_color(self, current_rgb, target_hex, speed=0.2):
        target_rgb = self.hex_to_rgb(target_hex)
        r = current_rgb[0] + (target_rgb[0] - current_rgb[0]) * speed
        g = current_rgb[1] + (target_rgb[1] - current_rgb[1]) * speed
        b = current_rgb[2] + (target_rgb[2] - current_rgb[2]) * speed
        return (r, g, b)

    def lighten_color(self, hex_color, factor=0.3):
        try:
            c = hex_color.lstrip("#")
            r, g, b = tuple(int(c[i : i + 2], 16) for i in (0, 2, 4))
            r = int(r + (255 - r) * factor)
            g = int(g + (255 - g) * factor)
            b = int(b + (255 - b) * factor)
            return "#%02x%02x%02x" % (r, g, b)
        except Exception:
            return cfg.COLOR_TEXT_WHITE

    # ============================================================================
    # UI GEOMETRY
    # ============================================================================

    def get_rounded_rect_points(self, x1, y1, x2, y2, radius=25):
        return [
            x1 + radius,
            y1,
            x1 + radius,
            y1,
            x2 - radius,
            y1,
            x2 - radius,
            y1,
            x2,
            y1,
            x2,
            y1 + radius,
            x2,
            y1 + radius,
            x2,
            y2 - radius,
            x2,
            y2 - radius,
            x2,
            y2,
            x2 - radius,
            y2,
            x2 - radius,
            y2,
            x1 + radius,
            y2,
            x1 + radius,
            y2,
            x1,
            y2,
            x1,
            y2 - radius,
            x1,
            y2 - radius,
            x1,
            y1 + radius,
            x1,
            y1 + radius,
            x1,
            y1,
        ]

    def create_rounded_rect(self, x1, y1, x2, y2, radius=25, **kwargs):
        points = self.get_rounded_rect_points(x1, y1, x2, y2, radius)
        return self.canvas.create_polygon(points, **kwargs, smooth=True)

    # ============================================================================
    # UI SETUP
    # ============================================================================

    def setup_ui(self):
        self.canvas = Canvas(
            self.root,
            width=cfg.WINDOW_WIDTH,
            height=cfg.WINDOW_HEIGHT,
            bg=cfg.COLOR_BG,
            highlightthickness=0,
        )
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.on_background_click)

        # Title
        title_text = cfg.TITLE_TEXT
        start_x = (cfg.WINDOW_WIDTH // 2) - (len(title_text) * 10)
        for i, char in enumerate(title_text):
            tid = self.canvas.create_text(
                start_x + (i * 20),
                40,
                text=char,
                font=cfg.FONT_TITLE,
                fill=cfg.COLOR_TEXT_WHITE,
            )
            self.title_chars.append(tid)

        # Input + main button
        self.INPUT_X = cfg.LAYOUT_INPUT_X
        self.INPUT_Y = cfg.LAYOUT_INPUT_Y
        self.INPUT_W = cfg.LAYOUT_INPUT_W
        self.BTN_W = cfg.LAYOUT_BTN_W
        self.GAP = cfg.LAYOUT_GAP

        right_align_edge = self.INPUT_X + self.INPUT_W + self.GAP + self.BTN_W

        self.ids["input_bg"] = self.create_rounded_rect(
            self.INPUT_X,
            self.INPUT_Y,
            self.INPUT_X + self.INPUT_W,
            self.INPUT_Y + cfg.LAYOUT_INPUT_H,
            radius=20,
            fill=cfg.COLOR_INPUT_BG,
            outline="#333333",
            width=2,
            tags="border_elem_input",
        )

        self.canvas.tag_bind(
            self.ids["input_bg"],
            "<Enter>",
            lambda e: [self.set_input_hover(True), self.canvas.config(cursor="xterm")],
        )
        self.canvas.tag_bind(
            self.ids["input_bg"],
            "<Leave>",
            lambda e: [self.set_input_hover(False), self.canvas.config(cursor="")],
        )
        self.canvas.tag_bind(self.ids["input_bg"], "<Button-1>", self.focus_input)

        self.ids["link_icon"] = self.canvas.create_text(
            self.INPUT_X + 30,
            self.INPUT_Y + 25,
            text="🔗",
            font=cfg.FONT_ICON,
            fill="#555555",
        )
        self.canvas.tag_bind(self.ids["link_icon"], "<Button-1>", self.focus_input)
        self.canvas.tag_bind(
            self.ids["link_icon"],
            "<Enter>",
            lambda e: self.canvas.config(cursor="xterm"),
        )

        self.ids["error_text"] = self.canvas.create_text(
            self.INPUT_X,
            self.INPUT_Y + 75,
            text="⚠️ Invalid Format",
            font=cfg.FONT_UI_SMALL,
            fill=cfg.COLOR_ERROR,
            anchor="w",
            state="hidden",
        )

        entry_h = cfg.LAYOUT_INPUT_H - 2
        self.entry_url = tk.Entry(
            self.root,
            textvariable=self.url_var,
            bg=cfg.COLOR_INPUT_BG,
            fg="#555555",
            font=cfg.FONT_UI,
            bd=0,
            highlightthickness=0,
            insertbackground=cfg.COLOR_INPUT_BG,
            disabledbackground="#151515",
            cursor="xterm",
        )
        self.entry_url.place(
            x=self.INPUT_X + 55,
            y=self.INPUT_Y + 1,
            width=self.INPUT_W - 80,
            height=entry_h,
        )
        self.entry_url.insert(0, "Paste link here...")
        self.entry_url.bind("<FocusIn>", self.on_entry_focus)
        self.entry_url.bind("<FocusOut>", self.on_entry_blur)
        self.entry_url.bind("<Button-1>", self.on_entry_click)
        self.entry_url.bind("<Enter>", lambda e: self.set_input_hover(True))
        self.entry_url.bind("<Leave>", lambda e: self.set_input_hover(False))

        # Main button (Analyze / Ready / etc.)
        self.BTN_X = self.INPUT_X + self.INPUT_W + self.GAP
        self.ids["btn_main"] = self.create_rounded_rect(
            self.BTN_X,
            self.INPUT_Y,
            self.BTN_X + self.BTN_W,
            self.INPUT_Y + cfg.LAYOUT_INPUT_H,
            radius=20,
            fill=cfg.COLOR_BTN_DEFAULT,
            outline=cfg.COLOR_BTN_DEFAULT,
            width=0,
            tags="btn_main_grp",
        )
        self.ids["btn_text"] = self.canvas.create_text(
            self.BTN_X + (self.BTN_W / 2),
            self.INPUT_Y + 30,
            text="⚡ ANALYZE",
            font=cfg.FONT_UI_BOLD,
            fill=cfg.COLOR_BTN_DISABLED_TEXT,
            tags="btn_main_grp",
        )
        self.canvas.tag_bind("btn_main_grp", "<Enter>", self.on_btn_hover_enter)
        self.canvas.tag_bind("btn_main_grp", "<Leave>", self.on_btn_hover_leave)
        self.canvas.tag_bind("btn_main_grp", "<Button-1>", self.on_btn_click)
        self.canvas.tag_bind(
            "btn_main_grp", "<ButtonRelease-1>", self.handle_main_action
        )

        # Split download controls (Pause + Abort) - initially hidden
        self._create_split_controls()

        # Cards
        card_w = cfg.LAYOUT_CARD_W
        card_h = cfg.LAYOUT_CARD_H
        col_gap = cfg.LAYOUT_COL_GAP
        row_gap = cfg.LAYOUT_ROW_GAP
        total_right_w = (card_w * 2) + col_gap
        start_right_x = right_align_edge - total_right_w

        col1_x = start_right_x
        col2_x = start_right_x + card_w + col_gap
        row1_y = 200
        row2_y = row1_y + card_h + row_gap

        self.draw_card(col1_x, row1_y, card_w, card_h, "SPEED", "display_speed", "🚀")
        self.draw_card(col2_x, row1_y, card_w, card_h, "ETA", "display_eta", "⏳")
        self.draw_card(col1_x, row2_y, card_w, card_h, "SIZE", "display_data", "📦")
        self.draw_card(
            col2_x, row2_y, card_w, card_h, "QUALITY", "display_res_label", "⚙️"
        )

        # Log panel
        term_y = row2_y + card_h + 25
        term_h = 150
        self.create_rounded_rect(
            start_right_x,
            term_y,
            start_right_x + total_right_w,
            term_y + term_h,
            radius=15,
            fill=cfg.LOG_BG,
            outline="#333333",
            width=1,
        )
        self.canvas.create_text(
            start_right_x + 20,
            term_y + 20,
            text=">_ SYSTEM LOG",
            font=cfg.FONT_UI_SMALL_BOLD,
            fill=cfg.COLOR_TEXT_DARK,
            anchor="w",
        )
        self.canvas.create_line(
            start_right_x,
            term_y + 35,
            start_right_x + total_right_w,
            term_y + 35,
            fill="#222222",
            width=1,
        )

        self.log_text = tk.Text(
            self.root,
            bg=cfg.LOG_BG,
            fg=cfg.LOG_COLOR_SUCCESS,
            font=cfg.FONT_LOG,
            bd=0,
            state="disabled",
        )
        self.log_text.place(
            x=start_right_x + 20,
            y=term_y + 40,
            width=total_right_w - 30,
            height=term_h - 50,
        )
        sys.stdout = utils.CustomConsoleWriter(self.log_text)

        # Ring
        self.ring_center_x = cfg.LAYOUT_RING_X
        self.ring_center_y = cfg.LAYOUT_RING_Y
        self.draw_ring()

        # Folder button
        folder_y = self.ring_center_y + 140
        self.FOLDER_W = cfg.LAYOUT_FOLDER_W
        self.FOLDER_H = cfg.LAYOUT_FOLDER_H
        self.FOLDER_X1 = self.ring_center_x - (self.FOLDER_W / 2)
        self.FOLDER_Y1 = folder_y
        self.FOLDER_X2 = self.ring_center_x + (self.FOLDER_W / 2)
        self.FOLDER_Y2 = folder_y + self.FOLDER_H

        self.ids["btn_folder_bg"] = self.create_rounded_rect(
            self.FOLDER_X1,
            self.FOLDER_Y1,
            self.FOLDER_X2,
            self.FOLDER_Y2,
            radius=15,
            fill=cfg.COLOR_BTN_HOVER,
            outline="#333333",
            width=0,
            state="hidden",
            tags="btn_folder_grp",
        )
        self.ids["btn_folder_text"] = self.canvas.create_text(
            self.ring_center_x,
            folder_y + (self.FOLDER_H / 2),
            text="📂 OPEN FOLDER",
            font=cfg.FONT_UI_SMALL_BOLD,
            fill=cfg.COLOR_TEXT_WHITE,
            state="hidden",
            tags="btn_folder_grp",
        )
        self.canvas.tag_bind("btn_folder_grp", "<Button-1>", self.on_folder_click)
        self.canvas.tag_bind(
            "btn_folder_grp", "<ButtonRelease-1>", self.on_folder_release
        )
        self.canvas.tag_bind("btn_folder_grp", "<Enter>", self.on_folder_hover_enter)
        self.canvas.tag_bind("btn_folder_grp", "<Leave>", self.on_folder_hover_leave)

    def _create_split_controls(self):
        # geometry (same slot as main button)
        self.SPLIT_GAP = 10
        self.SPLIT_W = (self.BTN_W - self.SPLIT_GAP) / 2

        self.PAUSE_X1 = self.BTN_X
        self.PAUSE_X2 = self.BTN_X + self.SPLIT_W
        self.ABORT_X1 = self.PAUSE_X2 + self.SPLIT_GAP
        self.ABORT_X2 = self.BTN_X + self.BTN_W

        y1 = self.INPUT_Y
        y2 = self.INPUT_Y + cfg.LAYOUT_INPUT_H

        # --- LEFT BUTTON: PAUSE / RESUME ---
        self.ids["btn_pause_bg"] = self.create_rounded_rect(
            self.PAUSE_X1,
            y1,
            self.PAUSE_X2,
            y2,
            radius=16,
            fill=cfg.COLOR_BTN_PAUSE,
            outline=cfg.COLOR_BTN_PAUSE,
            width=0,
            state="hidden",
            tags="btn_pause_grp",
        )

        # Pause Icon (Two Bars) - Initially Hidden (shown when downloading)
        self.ids["btn_icon_pause_bar1"] = self.canvas.create_rectangle(
            0,
            0,
            0,
            0,
            fill=cfg.COLOR_TEXT_BLACK,
            outline="",
            state="hidden",
            tags=("btn_pause_grp", "icon_shape"),
        )
        self.ids["btn_icon_pause_bar2"] = self.canvas.create_rectangle(
            0,
            0,
            0,
            0,
            fill=cfg.COLOR_TEXT_BLACK,
            outline="",
            state="hidden",
            tags=("btn_pause_grp", "icon_shape"),
        )

        # Resume Icon (Triangle) - Initially Hidden (shown when paused)
        self.ids["btn_icon_resume_tri"] = self.canvas.create_polygon(
            0,
            0,
            0,
            0,
            0,
            0,
            fill=cfg.COLOR_TEXT_WHITE,
            outline="",
            state="hidden",
            tags=("btn_pause_grp", "icon_shape"),
        )

        # --- RIGHT BUTTON: ABORT ---
        self.ids["btn_abort_small_bg"] = self.create_rounded_rect(
            self.ABORT_X1,
            y1,
            self.ABORT_X2,
            y2,
            radius=16,
            fill=cfg.COLOR_BTN_ABORT,
            outline=cfg.COLOR_BTN_ABORT,
            width=0,
            state="hidden",
            tags="btn_abort_small_grp",
        )

        # Abort Icon (Square)
        self.ids["btn_icon_abort_rect"] = self.canvas.create_rectangle(
            0,
            0,
            0,
            0,
            fill=cfg.COLOR_TEXT_WHITE,
            outline="",
            state="hidden",
            tags=("btn_abort_small_grp", "icon_shape"),
        )

        # bindings
        self.canvas.tag_bind("btn_pause_grp", "<Enter>", self.on_pause_hover_enter)
        self.canvas.tag_bind("btn_pause_grp", "<Leave>", self.on_pause_hover_leave)
        self.canvas.tag_bind("btn_pause_grp", "<Button-1>", self.on_pause_click)
        self.canvas.tag_bind(
            "btn_pause_grp", "<ButtonRelease-1>", self.handle_pause_action
        )

        self.canvas.tag_bind(
            "btn_abort_small_grp", "<Enter>", self.on_abort_small_hover_enter
        )
        self.canvas.tag_bind(
            "btn_abort_small_grp", "<Leave>", self.on_abort_small_hover_leave
        )
        self.canvas.tag_bind(
            "btn_abort_small_grp", "<Button-1>", self.on_abort_small_click
        )
        self.canvas.tag_bind(
            "btn_abort_small_grp", "<ButtonRelease-1>", self.handle_abort_small_action
        )

    def _set_split_controls_visible(self, visible: bool):
        self.split_controls_visible = visible

        # main button state
        main_state = "hidden" if visible else "normal"
        self.canvas.itemconfigure(self.ids["btn_main"], state=main_state)
        self.canvas.itemconfigure(self.ids["btn_text"], state=main_state)

        # split buttons state
        split_state = "normal" if visible else "hidden"
        self.canvas.itemconfigure(self.ids["btn_pause_bg"], state=split_state)
        self.canvas.itemconfigure(self.ids["btn_abort_small_bg"], state=split_state)
        self.canvas.itemconfigure(self.ids["btn_icon_abort_rect"], state=split_state)

        # Pause/Resume icon visibility is handled in animation loop based on self.is_paused

        # reset offsets (prevents jumps)
        if visible:
            self.btn_offset_y = 0.0
        else:
            self.pause_offset_y = 0.0
            self.abort_small_offset_y = 0.0
            # Hide icons when main controls hide
            self.canvas.itemconfigure(self.ids["btn_icon_pause_bar1"], state="hidden")
            self.canvas.itemconfigure(self.ids["btn_icon_pause_bar2"], state="hidden")
            self.canvas.itemconfigure(self.ids["btn_icon_resume_tri"], state="hidden")

    def draw_card(self, x, y, w, h, title, var_name, icon):
        self.create_rounded_rect(
            x,
            y,
            x + w,
            y + h,
            radius=15,
            fill="#161b22",
            outline=self.current_theme_color,
            width=1,
            tags="border_elem",
        )
        self.canvas.create_text(
            x + 20,
            y + 25,
            text=f"{icon} {title}",
            font=cfg.FONT_UI_SMALL_BOLD,
            fill=cfg.COLOR_TEXT_DIM,
            anchor="w",
        )
        self.ids[var_name] = self.canvas.create_text(
            x + 20,
            y + 55,
            text="---",
            font=("Consolas", 14, "bold"),
            fill=cfg.COLOR_TEXT_WHITE,
            anchor="w",
        )

    # ============================================================================
    # RING VISUALIZATION
    # ============================================================================

    def draw_ring(self):
        self.canvas.delete("ring_elem", "ring_arc", "ring_text", "anim_elem")
        if self.is_menu_open:
            return

        cx, cy, r = self.ring_center_x, self.ring_center_y, cfg.LAYOUT_RING_RADIUS

        self.canvas.create_oval(
            cx - r,
            cy - r,
            cx + r,
            cy + r,
            outline="#1f1f1f",
            width=cfg.LAYOUT_RING_WIDTH,
            tags="ring_elem",
        )

        if self.is_error_state:
            self._draw_arc(cfg.COLOR_ERROR)
            self.canvas.create_text(
                cx,
                cy,
                text="X",
                font=cfg.FONT_BIG_ICON,
                fill=cfg.COLOR_ERROR,
                tags="ring_text",
            )
            return

        if self.is_aborted_state:
            self._draw_arc(cfg.COLOR_ERROR)
            self.canvas.create_text(
                cx,
                cy,
                text="!",
                font=cfg.FONT_BIG_ICON,
                fill=cfg.COLOR_ERROR,
                tags="ring_text",
            )
            return

        if self.is_throttled:
            self._draw_arc(cfg.COLOR_ERROR)
            self.canvas.create_text(
                cx,
                cy,
                text="!",
                font=cfg.FONT_BIG_ICON,
                fill=cfg.COLOR_ERROR,
                tags="ring_text",
            )
            return

        force_square = (
            self.is_downloading
            and self.progress_current >= 99.0
            and not self.is_download_completed
        )

        if self.is_merging or self.is_analyzing or force_square:
            sq_color = (
                cfg.COLOR_MERGING
                if self.is_merging or force_square
                else cfg.COLOR_TEXT_WHITE
            )
            self._draw_loading_square(cx, cy, sq_color)
            return

        if self.is_download_completed:
            self._draw_arc(cfg.COLOR_SUCCESS)
            self.canvas.create_text(
                cx,
                cy,
                text="✓",
                font=("Roboto", 70, "bold"),
                fill=cfg.COLOR_SUCCESS,
                tags="ring_text",
            )
            return

        if self.is_downloading:
            if self.is_paused:
                # Paused: Yellow arc, big pause icon
                self._draw_arc(cfg.COLOR_WARNING)
                self.canvas.create_text(
                    cx,
                    cy,
                    text="II",
                    font=cfg.FONT_BIG_ICON,
                    fill=cfg.COLOR_WARNING,
                    tags="ring_text",
                )
            else:
                # Downloading: Theme color arc, percentage
                self._draw_arc(self.current_theme_color)
                txt = f"{self.progress_current:.1f}%"
                self.canvas.create_text(
                    cx,
                    cy,
                    text=txt,
                    font=cfg.FONT_PERCENTAGE,
                    fill=cfg.COLOR_TEXT_WHITE,
                    tags="ring_text",
                )
            return

        # idle state (dot)
        self.canvas.create_text(
            cx,
            cy,
            text="•",
            font=("Segoe UI", 34, "bold"),
            fill=cfg.COLOR_TEXT_WHITE,
            tags="ring_text",
        )

    def _draw_arc(self, color):
        cx, cy, r = self.ring_center_x, self.ring_center_y, cfg.LAYOUT_RING_RADIUS
        if self.progress_current > 0.1:
            extent = -self.progress_current * 3.6
            self.canvas.create_arc(
                cx - r,
                cy - r,
                cx + r,
                cy + r,
                start=90,
                extent=extent,
                style="arc",
                outline=color,
                width=cfg.LAYOUT_RING_WIDTH,
                tags="ring_arc",
            )

    def _draw_loading_square(self, cx, cy, color="#FFFFFF"):
        now = time.time()
        if now - self.ring_frame_last > self.ring_frame_dt:
            self.ring_frame_last = now
            self.ring_frame_i = (self.ring_frame_i + 1) % len(self.loading)

        hole_idx = self.loading[self.ring_frame_i]
        dot_r = 5

        for i, (dx, dy) in enumerate(self.grid_coords):
            if i != hole_idx:
                self.canvas.create_oval(
                    cx + dx - dot_r,
                    cy + dy - dot_r,
                    cx + dx + dot_r,
                    cy + dy + dot_r,
                    fill=color,
                    outline="",
                    tags="anim_elem",
                )

    # ============================================================================
    # UI STATE / INPUT
    # ============================================================================

    def reset_info_labels(self):
        self.display_speed = "0 B/s"
        self.display_eta = "--:--"
        self.display_data = "-"
        self.display_res_label = "---"
        self.canvas.itemconfig(self.ids["display_speed"], text="--")
        self.canvas.itemconfig(self.ids["display_eta"], text="--")
        self.canvas.itemconfig(self.ids["display_data"], text="--")
        self.canvas.itemconfig(self.ids["display_res_label"], text="---")

    def clear_input_and_reset(self):
        self.url_var.set("")
        self.entry_url.delete(0, tk.END)
        self.entry_url.config(fg="#555555", insertbackground=cfg.COLOR_INPUT_BG)
        self.entry_url.insert(0, "Paste link here...")
        self.check_url_theme()
        self.validate_ui_state()
        self.root.focus()

    def on_url_change(self, *args):
        if self.is_input_disabled:
            return

        current_text = self.url_var.get()
        if current_text and "Paste" not in current_text:
            if self.is_download_completed:
                self.is_download_completed = False
            if self.is_aborted_state:
                self.is_aborted_state = False
            if self.is_error_state:
                self.is_error_state = False
            self.check_url_theme()
            self.validate_ui_state()

    def validate_ui_state(self):
        url = self.url_var.get().strip()

        if not url or "Paste" in url:
            self.is_url_valid = False
            self.is_coming_soon = False
            self.canvas.itemconfig(self.ids["error_text"], state="hidden")
            self.target_btn_color = cfg.COLOR_BTN_DEFAULT
            self.target_btn_text_color = cfg.COLOR_BTN_DISABLED_TEXT
            return

        try:
            regex = re.compile(
                r"^(?:http|ftp)s?://"
                r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|"
                r"localhost|"
                r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
                r"(?::\d+)?"
                r"(?:/?|[/?]\S+)$",
                re.IGNORECASE,
            )
            if not re.match(regex, url):
                raise ValueError
        except Exception:
            self.is_url_valid = False
            self.is_coming_soon = False
            self.canvas.itemconfig(
                self.ids["error_text"],
                text="⚠️ Invalid Format",
                fill=cfg.COLOR_ERROR,
                state="normal",
            )
            self.target_btn_color = cfg.COLOR_BTN_DEFAULT
            self.target_btn_text_color = cfg.COLOR_BTN_DISABLED_TEXT
            return

        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        core = domain.replace("www.", "")

        is_youtube = "youtu" in core and core in [
            "youtube.com",
            "youtu.be",
            "m.youtube.com",
            "music.youtube.com",
        ]
        is_playlist = is_youtube and "playlist" in url.lower()

        future_platforms = [
            "twitch",
            "instagram",
            "tiktok",
            "facebook",
            "soundcloud",
            "twitter",
            "x.com",
        ]
        is_future = any(p in domain for p in future_platforms)

        if is_playlist or is_future:
            self.is_url_valid = False
            self.is_coming_soon = True
            self.canvas.itemconfig(
                self.ids["error_text"],
                text="⏳ Coming Soon...",
                fill=cfg.COLOR_COMING_SOON,
                state="normal",
            )
            self.target_btn_color = cfg.COLOR_BTN_DEFAULT
            self.target_btn_text_color = cfg.COLOR_BTN_DISABLED_TEXT

        elif is_youtube:
            self.is_url_valid = True
            self.is_coming_soon = False
            self.canvas.itemconfig(self.ids["error_text"], state="hidden")
            self.target_btn_color = self.current_theme_color
            self.target_btn_text_color = cfg.COLOR_TEXT_WHITE

        else:
            self.is_url_valid = False
            self.is_coming_soon = False
            self.canvas.itemconfig(
                self.ids["error_text"],
                text="⚠️ Unsupported URL",
                fill=cfg.COLOR_ERROR,
                state="normal",
            )
            self.target_btn_color = cfg.COLOR_BTN_DEFAULT
            self.target_btn_text_color = cfg.COLOR_BTN_DISABLED_TEXT

    def set_input_state(self, enabled: bool):
        self.is_input_disabled = not enabled
        if enabled:
            self.entry_url.config(
                state="normal", fg=cfg.COLOR_TEXT_WHITE, bg=cfg.COLOR_INPUT_BG
            )
            self.canvas.itemconfig(self.ids["input_bg"], fill=cfg.COLOR_INPUT_BG)
        else:
            self.entry_url.config(
                state="disabled", fg=cfg.COLOR_TEXT_DARK, bg="#151515"
            )
            self.canvas.itemconfig(self.ids["input_bg"], fill="#151515")

    def check_url_theme(self, event=None):
        url = self.url_var.get().strip()
        is_empty = (not url) or ("Paste" in url)
        self.current_theme_color = (
            cfg.COLOR_DEFAULT_THEME if is_empty else self.get_color_by_url(url)
        )
        self.update_theme_colors()

    def update_theme_colors(self):
        self.canvas.itemconfig("border_elem", outline=self.current_theme_color)
        if self.progress_current > 0.1:
            self.canvas.itemconfig("ring_arc", outline=self.current_theme_color)

    def get_color_by_url(self, url):
        try:
            d = urlparse(url).netloc.lower()
            if "youtube" in d or "youtu.be" in d:
                return "#FF0000"
            if "twitch" in d:
                return "#9146FF"
            if "instagram" in d:
                return "#A63AB8"
            if "facebook" in d:
                return "#0080FF"
            if "tiktok" in d:
                return "#FE2C55"
            if "soundcloud" in d:
                return "#FF5500"
        except Exception:
            pass
        return cfg.COLOR_DEFAULT_THEME

    def reset_ui(self):
        self.is_downloading = False
        self.is_analyzing = False
        self.is_merging = False
        self.is_download_completed = False
        self.is_throttled = False
        self.is_paused = False
        self.pause_requested = False

        self.progress_current = 0.0
        self.progress_target = 0.0

        self.reset_info_labels()
        self.set_input_state(True)
        self.validate_ui_state()

        self.canvas.itemconfig(self.ids["btn_text"], text="⚡ ANALYZE")
        self._set_split_controls_visible(False)

    def set_input_hover(self, hovered: bool):
        self.input_hovered = hovered

    def focus_input(self, event=None):
        if self.is_input_disabled:
            return
        self.entry_url.focus_set()
        if "Paste" not in self.url_var.get():
            self.entry_url.icursor(tk.END)
        else:
            self.entry_url.icursor(0)

    # ============================================================================
    # FOLDER BUTTON EVENTS
    # ============================================================================

    def on_folder_hover_enter(self, event=None):
        if not self.show_folder_btn:
            return
        self.folder_hovered = True
        self.canvas.config(cursor="hand2")

    def on_folder_hover_leave(self, event=None):
        self.folder_hovered = False
        self.canvas.config(cursor="")

    def on_folder_click(self, event=None):
        if not self.show_folder_btn:
            return
        self.folder_btn_pressed = True

    def on_folder_release(self, event=None):
        if not self.show_folder_btn:
            return
        if self.folder_btn_pressed:
            self.folder_btn_pressed = False
            utils.open_folder(cfg.DL_FOLDER_NAME)

    # ============================================================================
    # MAIN BUTTON EVENTS
    # ============================================================================

    def on_btn_hover_enter(self, event=None):
        if self.is_merging or self.is_download_completed:
            return
        if not self.is_url_valid and not self.is_downloading:
            return
        self.btn_hovered = True
        self.canvas.config(cursor="hand2")

    def on_btn_hover_leave(self, event=None):
        self.btn_hovered = False
        self.canvas.config(cursor="")

    def on_btn_click(self, event=None):
        if self.is_merging or self.is_download_completed:
            return
        if self.is_menu_open or self.is_analyzing:
            return
        if not self.is_url_valid and not self.is_downloading:
            return
        self.btn_pressed = True

    # ============================================================================
    # SPLIT CONTROLS EVENTS (Pause + Abort)
    # ============================================================================

    def on_pause_hover_enter(self, event=None):
        if not self.split_controls_visible:
            return
        if self.is_merging or self.is_download_completed:
            return
        if not self.is_downloading:
            return
        self.pause_hovered = True
        self.canvas.config(cursor="hand2")

    def on_pause_hover_leave(self, event=None):
        self.pause_hovered = False
        self.canvas.config(cursor="")

    def on_pause_click(self, event=None):
        if not self.split_controls_visible:
            return
        if self.is_merging or self.is_download_completed:
            return
        if not self.is_downloading:
            return
        self.pause_pressed = True

    def handle_pause_action(self, event=None):
        if not self.split_controls_visible:
            self.pause_pressed = False
            return
        if not self.is_downloading or self.is_merging or self.is_download_completed:
            self.pause_pressed = False
            return

        if self.pause_pressed:
            self.pause_pressed = False

        # Toggle pause
        self.pause_requested = not self.pause_requested
        self.is_paused = self.pause_requested

        # Color & Icon update handled in animation loop
        if self.is_paused:
            print("[INFO] Download paused")
        else:
            print("[INFO] Download resumed")

        self.draw_ring()

    def on_abort_small_hover_enter(self, event=None):
        if not self.split_controls_visible:
            return
        if self.is_merging or self.is_download_completed:
            return
        if not self.is_downloading:
            return
        self.abort_hovered_small = True
        self.canvas.config(cursor="hand2")

    def on_abort_small_hover_leave(self, event=None):
        self.abort_hovered_small = False
        self.canvas.config(cursor="")

    def on_abort_small_click(self, event=None):
        if not self.split_controls_visible:
            return
        if self.is_merging or self.is_download_completed:
            return
        if not self.is_downloading:
            return
        self.abort_pressed_small = True

    def handle_abort_small_action(self, event=None):
        if not self.split_controls_visible:
            self.abort_pressed_small = False
            return
        if not self.is_downloading or self.is_merging or self.is_download_completed:
            self.abort_pressed_small = False
            return

        if self.abort_pressed_small:
            self.abort_pressed_small = False

        if not self.abort_requested:
            self.abort_requested = True
            self.pause_requested = False
            self.is_paused = False
            print("[ABORT] ABORTED BY USER")

            # bring back main button immediately (like old behavior)
            self.target_btn_color = cfg.COLOR_BTN_DEFAULT
            self.target_btn_text_color = cfg.COLOR_BTN_DISABLED_TEXT
            self.canvas.itemconfig(self.ids["btn_text"], text="⚡ ANALYZE")
            self._set_split_controls_visible(False)

    # ============================================================================
    # ENTRY EVENTS
    # ============================================================================

    def on_entry_click(self, event=None):
        if self.is_input_disabled:
            return
        if "Paste" in self.url_var.get():
            self.entry_url.delete(0, tk.END)
            self.entry_url.config(fg=cfg.COLOR_TEXT_WHITE, insertbackground="white")
        else:
            self.entry_url.config(insertbackground="white")

    def on_entry_focus(self, event=None):
        if self.is_input_disabled:
            return
        self.is_input_focused = True
        if "Paste" in self.url_var.get():
            self.entry_url.delete(0, tk.END)
            self.entry_url.config(fg=cfg.COLOR_TEXT_WHITE, insertbackground="white")
        self.set_input_hover(True)

    def on_entry_blur(self, event=None):
        self.is_input_focused = False
        if self.is_input_disabled:
            return
        if not self.url_var.get().strip():
            self.entry_url.delete(0, tk.END)
            self.entry_url.config(fg="#555555", insertbackground=cfg.COLOR_INPUT_BG)
            self.entry_url.insert(0, "Paste link here...")
            self.canvas.itemconfig(self.ids["error_text"], state="hidden")
            self.validate_ui_state()
        else:
            self.entry_url.config(insertbackground=cfg.COLOR_INPUT_BG)
        self.set_input_hover(False)

    def on_background_click(self, event=None):
        self.root.focus()

    # ============================================================================
    # WINDOW CLOSE
    # ============================================================================

    def on_closing(self):
        if self.is_downloading:
            if not self.abort_requested:
                self.abort_requested = True
                self.pause_requested = False
                self.is_paused = False
                print("[ABORT] ABORTED BY USER - Closing")
            self.root.destroy()
            sys.exit()
        self.root.destroy()
        sys.exit()

    # ============================================================================
    # MAIN ACTION FLOW
    # ============================================================================

    def handle_main_action(self, event=None):
        if self.is_merging:
            return
        if self.is_download_completed:
            return

        if self.btn_pressed:
            self.btn_pressed = False

        if self.is_menu_open or self.is_analyzing:
            return
        if self.abort_requested:
            return
        if not self.is_url_valid and not self.is_downloading:
            return

        # IMPORTANT: download abort is handled by the red split button now
        if self.is_downloading:
            return

        url = self.url_var.get().strip()
        if not self.is_analyzing and not self.is_downloading:
            self.is_aborted_state = False
            self.is_error_state = False
            self.is_download_completed = False
            self.abort_requested = False
            self.start_analysis(url)

    def start_analysis(self, url):
        self.show_folder_btn = False
        self.canvas.itemconfigure(self.ids["btn_folder_bg"], state="hidden")
        self.canvas.itemconfigure(self.ids["btn_folder_text"], state="hidden")

        self.is_analyzing = True
        self.set_input_state(False)
        self.canvas.config(cursor="")

        self.target_btn_color = cfg.COLOR_BTN_HOVER
        self.target_btn_text_color = cfg.COLOR_TEXT_DIM
        self.canvas.itemconfig(self.ids["btn_text"], text="⌛ SEARCHING...")

        print("Fetching link...")

        def task():
            try:
                self.handler = YouTubeVideoHandler(url)
                res_list, title = self.handler.fetch_info()

                info = self.handler.video_info
                audio_formats = [
                    f
                    for f in info.get("formats", [])
                    if f.get("vcodec") == "none" and f.get("acodec") != "none"
                ]
                best_audio = (
                    max(audio_formats, key=lambda x: x.get("abr") or 0)
                    if audio_formats
                    else None
                )

                audio_label = "Audio Only"
                if best_audio:
                    ext = best_audio.get("ext", "mp3")
                    abr = best_audio.get("abr")
                    audio_label = f"Audio {ext} {int(abr)}k" if abr else f"Audio {ext}"

                self.audio_details_map[audio_label] = "Audio Only"
                if audio_label not in res_list:
                    res_list.append(audio_label)

                self.resolutions = res_list

                print(f"FOUND: {title}")
                self.root.after(0, self.show_custom_menu)

            except Exception as e:
                error_msg = str(e).lower()
                if (
                    "throttling" in error_msg
                    or "429" in error_msg
                    or "rate limit" in error_msg
                ):
                    print("[WARNING] YouTube throttling detected - retrying later...")
                    self.root.after(0, self.on_throttling_detected)
                else:
                    print(f"[ERROR] CRITICAL ERROR: {e}")
                    self.root.after(0, self.on_analysis_error)

        threading.Thread(target=task, daemon=True).start()

    def on_throttling_detected(self):
        self.is_throttled = True
        self.is_analyzing = False
        self.set_input_state(True)
        self.canvas.itemconfig(self.ids["btn_text"], text="⚠️ THROTTLED")
        self.target_btn_color = cfg.COLOR_WARNING
        self.target_btn_text_color = cfg.COLOR_TEXT_DARK
        self.draw_ring()

        def retry():
            time.sleep(cfg.THROTTLE_RETRY_DELAY)
            if self.is_throttled:
                print("[INFO] Retrying after throttling delay...")
                self.is_throttled = False
                self.root.after(
                    0, lambda: self.start_analysis(self.url_var.get().strip())
                )

        threading.Thread(target=retry, daemon=True).start()

    def on_analysis_error(self):
        self.reset_ui()
        self.url_var.set(self.url_var.get())
        self.is_error_state = True

    # ============================================================================
    # QUALITY MENU
    # ============================================================================

    def show_custom_menu(self):
        if self.menu_canvas:
            return

        self.is_menu_open = True
        self.is_analyzing = False

        self.canvas.itemconfig(self.ids["btn_text"], text="✓ READY")
        self.target_btn_color = cfg.COLOR_SUCCESS
        self.target_btn_text_color = cfg.COLOR_TEXT_WHITE

        self.menu_canvas = Canvas(
            self.root,
            width=cfg.WINDOW_WIDTH,
            height=cfg.WINDOW_HEIGHT,
            bg="#000000",
            highlightthickness=0,
        )
        self.menu_canvas.place(x=0, y=0)
        self.menu_canvas.bind("<Button-1>", self.close_menu)

        self.menu_canvas.create_rectangle(
            0,
            0,
            cfg.WINDOW_WIDTH,
            cfg.WINDOW_HEIGHT,
            fill="#000000",
            stipple="gray50",
            outline="",
        )

        audio_items = [r for r in self.resolutions if "Audio" in r]
        video_items = [r for r in self.resolutions if "Audio" not in r]

        columns = 3
        btn_h = 45
        gap_x = 15
        gap_y = 15
        menu_w = 600
        header_h = 70
        video_title_h = 40

        video_rows = math.ceil(len(video_items) / columns) if video_items else 0
        video_grid_h = video_rows * (btn_h + gap_y)

        audio_title_h = 50
        audio_items_h = len(audio_items) * (btn_h + gap_y)

        content_h = (
            header_h + video_title_h + video_grid_h + audio_title_h + audio_items_h
        )
        vertical_padding = 30

        menu_h = content_h + (vertical_padding * 2)
        menu_x = (cfg.WINDOW_WIDTH - menu_w) // 2
        menu_y = (cfg.WINDOW_HEIGHT - menu_h) // 2

        self.menu_canvas.create_rectangle(
            menu_x,
            menu_y,
            menu_x + menu_w,
            menu_y + menu_h,
            fill="#1a1a1a",
            outline=self.current_theme_color,
            width=2,
        )

        y_cursor = menu_y + vertical_padding

        self.menu_canvas.create_text(
            menu_x + menu_w // 2,
            y_cursor + 15,
            text="SELECT QUALITY",
            font=("Segoe UI", 16, "bold"),
            fill=cfg.COLOR_TEXT_WHITE,
        )
        y_cursor += header_h

        start_x = menu_x + 30
        btn_width = (menu_w - 60 - ((columns - 1) * gap_x)) / columns

        if video_items:
            self.menu_canvas.create_text(
                start_x,
                y_cursor + 10,
                text="VIDEO",
                font=("Segoe UI", 10, "bold"),
                fill="#888888",
                anchor="w",
            )
            y_cursor += video_title_h

            for i, res in enumerate(video_items):
                row = i // columns
                col = i % columns
                x = start_x + (col * (btn_width + gap_x))
                y = y_cursor + (row * (btn_h + gap_y))
                btn = self.create_menu_button(x, y, btn_width, btn_h, res)
                self.menu_buttons.append(btn)

            y_cursor += video_grid_h

        if audio_items:
            self.menu_canvas.create_text(
                start_x,
                y_cursor + 20,
                text="AUDIO",
                font=("Segoe UI", 10, "bold"),
                fill="#888888",
                anchor="w",
            )
            y_cursor += audio_title_h

            for i, res in enumerate(audio_items):
                y = y_cursor + (i * (btn_h + gap_y))
                btn = self.create_menu_button(start_x, y, btn_width, btn_h, res)
                self.menu_buttons.append(btn)

    def create_menu_button(self, x, y, w, h, label):
        default_bg = "#252526"
        hover_bg = "#4f4f55"

        btn_data = {
            "hovered": False,
            "label": label,
            "target_bg": default_bg,
            "current_bg_rgb": self.hex_to_rgb(default_bg),
        }

        radius = 10
        points = self.get_rounded_rect_points(x, y, x + w, y + h, radius)

        bg_id = self.menu_canvas.create_polygon(
            points, fill=default_bg, outline="", smooth=True
        )
        text_id = self.menu_canvas.create_text(
            x + w // 2,
            y + h // 2,
            text=label,
            font=("Segoe UI", 11, "bold"),
            fill="#E0E0E0",
        )

        def on_hover_enter(e=None):
            btn_data["hovered"] = True
            btn_data["target_bg"] = hover_bg
            self.menu_canvas.config(cursor="hand2")

        def on_hover_leave(e=None):
            btn_data["hovered"] = False
            btn_data["target_bg"] = default_bg
            self.menu_canvas.config(cursor="")

        def on_click(e=None):
            if btn_data["hovered"]:
                self.selected_res.set(label)
                self.close_menu()
                self.start_download()

        self.menu_canvas.tag_bind(bg_id, "<Enter>", on_hover_enter)
        self.menu_canvas.tag_bind(bg_id, "<Leave>", on_hover_leave)
        self.menu_canvas.tag_bind(bg_id, "<Button-1>", on_click)

        self.menu_canvas.tag_bind(text_id, "<Enter>", on_hover_enter)
        self.menu_canvas.tag_bind(text_id, "<Leave>", on_hover_leave)
        self.menu_canvas.tag_bind(text_id, "<Button-1>", on_click)

        return {"bg_id": bg_id, "data": btn_data}

    def close_menu(self, event=None):
        if self.menu_canvas:
            self.menu_canvas.destroy()
            self.menu_canvas = None
            self.menu_buttons.clear()
            self.is_menu_open = False

    # ============================================================================
    # DOWNLOAD PROCESS
    # ============================================================================

    def start_download(self):
        url = self.url_var.get().strip()
        resolution = self.selected_res.get()

        if resolution in self.audio_details_map:
            resolution = self.audio_details_map[resolution]

        self.is_downloading = True
        self.is_download_completed = False
        self.is_paused = False
        self.pause_requested = False

        self.progress_current = 0.0
        self.progress_target = 0.0

        # Show split controls and hide main button
        self._set_split_controls_visible(True)

        self.display_res_label = resolution
        self.canvas.itemconfig(self.ids["display_res_label"], text=resolution)

        print(f"[INFO] Starting download: {resolution}")

        def progress_cb(progress, speed, eta, size):
            self.progress_target = progress
            self.display_speed = speed
            self.display_eta = eta
            self.display_data = size

        def stage_cb(stage):
            if stage == "merging":
                self.is_merging = True
                # During merging keep original UI behavior (single disabled button)
                self._set_split_controls_visible(False)
                self.canvas.itemconfig(self.ids["btn_text"], text="⚙️ MERGING")
                self.target_btn_color = "#222222"
                self.target_btn_text_color = "#888888"

        def check_abort_cb():
            return self.abort_requested

        def check_pause_cb():
            return self.pause_requested

        callbacks = {
            "progress": progress_cb,
            "stage": stage_cb,
            "check_abort": check_abort_cb,
            "check_pause": check_pause_cb,
        }

        def _download_task():
            success, final_file = logic.run_download(
                url, resolution, self.handler, callbacks
            )
            self.root.after(0, lambda: self.on_download_complete(success, final_file))

        threading.Thread(target=_download_task, daemon=True).start()

    def on_download_complete(self, success, final_file):
        self.is_downloading = False
        self.is_merging = False
        self.is_paused = False
        self.pause_requested = False

        # always restore main button
        self._set_split_controls_visible(False)

        if success:
            self.is_download_completed = True
            self.progress_current = 100.0
            print("[SUCCESS] Download completed successfully!")

            self.reset_info_labels()
            self.set_input_state(True)
            self.clear_input_and_reset()

            self.show_folder_btn = True
            self.canvas.itemconfigure(self.ids["btn_folder_bg"], state="normal")
            self.canvas.itemconfigure(self.ids["btn_folder_text"], state="normal")

            self.canvas.itemconfig(self.ids["btn_text"], text="⚡ ANALYZE")
            self.target_btn_color = "#222222"
            self.target_btn_text_color = "#888888"

        else:
            if self.abort_requested:
                self.is_aborted_state = True
                self.progress_current = 100.0
                print("[WARNING] Download was aborted.")
                utils.perform_cleanup(final_file)

                self.reset_info_labels()
                self.set_input_state(True)
                self.clear_input_and_reset()
                self.check_url_theme()

            else:
                self.is_error_state = True
                print("[ERROR] Download failed.")
                self.reset_ui()

        self.abort_requested = False

    # ============================================================================
    # ANIMATION LOOP
    # ============================================================================

    def run_animation_loop(self):
        # Main button color animation
        if self.is_merging or self.is_download_completed:
            self.target_btn_color = "#222222"

        self.current_btn_color_rgb = self.lerp_color(
            self.current_btn_color_rgb, self.target_btn_color, cfg.ANIM_SPEED_LERP
        )
        btn_hex = self.rgb_to_hex(self.current_btn_color_rgb)
        self.canvas.itemconfig(self.ids["btn_main"], fill=btn_hex, outline=btn_hex)

        # Split controls color animation
        # Logic: If paused -> Show Resume Button (Green). If downloading -> Show Pause Button (Warning)
        if self.split_controls_visible:
            if self.is_paused:
                self.target_pause_color = cfg.COLOR_BTN_RESUME
                # Show Triangle, Hide Bars
                self.canvas.itemconfigure(
                    self.ids["btn_icon_resume_tri"], state="normal"
                )
                self.canvas.itemconfigure(
                    self.ids["btn_icon_pause_bar1"], state="hidden"
                )
                self.canvas.itemconfigure(
                    self.ids["btn_icon_pause_bar2"], state="hidden"
                )
            else:
                self.target_pause_color = cfg.COLOR_BTN_PAUSE
                # Hide Triangle, Show Bars
                self.canvas.itemconfigure(
                    self.ids["btn_icon_resume_tri"], state="hidden"
                )
                self.canvas.itemconfigure(
                    self.ids["btn_icon_pause_bar1"], state="normal"
                )
                self.canvas.itemconfigure(
                    self.ids["btn_icon_pause_bar2"], state="normal"
                )

        self.current_pause_color_rgb = self.lerp_color(
            self.current_pause_color_rgb, self.target_pause_color, cfg.ANIM_SPEED_LERP
        )
        pause_hex = self.rgb_to_hex(self.current_pause_color_rgb)
        self.canvas.itemconfig(
            self.ids["btn_pause_bg"], fill=pause_hex, outline=pause_hex
        )

        # Abort button always Critical Red
        self.current_abort_small_color_rgb = self.lerp_color(
            self.current_abort_small_color_rgb,
            self.target_abort_small_color,
            cfg.ANIM_SPEED_LERP,
        )
        abort_hex = self.rgb_to_hex(self.current_abort_small_color_rgb)
        self.canvas.itemconfig(
            self.ids["btn_abort_small_bg"], fill=abort_hex, outline=abort_hex
        )

        # Input border color animation
        target_border_hex = "#333333"
        if self.is_url_valid:
            target_border_hex = self.current_theme_color
        else:
            if self.is_input_focused or self.input_hovered:
                target_border_hex = "#888888"

        if self.is_error_state:
            target_border_hex = cfg.COLOR_ERROR
        if self.is_coming_soon:
            target_border_hex = cfg.COLOR_COMING_SOON

        self.current_input_border_rgb = self.lerp_color(
            self.current_input_border_rgb, target_border_hex, 0.2
        )
        border_hex = self.rgb_to_hex(self.current_input_border_rgb)
        self.canvas.itemconfig(self.ids["input_bg"], outline=border_hex)

        # Menu buttons lerp
        if self.is_menu_open and self.menu_canvas:
            for btn in self.menu_buttons:
                data = btn["data"]
                current_bg = data["current_bg_rgb"]
                target_hex = data["target_bg"]
                new_rgb = self.lerp_color(current_bg, target_hex, 0.25)
                data["current_bg_rgb"] = new_rgb
                self.menu_canvas.itemconfig(btn["bg_id"], fill=self.rgb_to_hex(new_rgb))

        # Main button text color
        self.canvas.itemconfig(self.ids["btn_text"], fill=self.target_btn_text_color)

        # Lift animation for main button (only when visible)
        if not self.split_controls_visible:
            target_offset = -8 if self.btn_hovered else 0
            if self.btn_pressed:
                target_offset = -2
            self.btn_offset_y += (
                target_offset - self.btn_offset_y
            ) * cfg.ANIM_SPEED_LIFT

            self.canvas.coords(
                self.ids["btn_main"],
                *self.get_rounded_rect_points(
                    self.BTN_X,
                    self.INPUT_Y + self.btn_offset_y,
                    self.BTN_X + self.BTN_W,
                    self.INPUT_Y + cfg.LAYOUT_INPUT_H + self.btn_offset_y,
                    radius=20,
                ),
            )
            self.canvas.coords(
                self.ids["btn_text"],
                self.BTN_X + (self.BTN_W / 2),
                self.INPUT_Y + 30 + self.btn_offset_y,
            )

        # Lift animation for split controls (only when visible)
        if self.split_controls_visible:
            pause_target_offset = -8 if self.pause_hovered else 0
            if self.pause_pressed:
                pause_target_offset = -2
            self.pause_offset_y += (
                pause_target_offset - self.pause_offset_y
            ) * cfg.ANIM_SPEED_LIFT

            abort_target_offset = -8 if self.abort_hovered_small else 0
            if self.abort_pressed_small:
                abort_target_offset = -2
            self.abort_small_offset_y += (
                abort_target_offset - self.abort_small_offset_y
            ) * cfg.ANIM_SPEED_LIFT

            # Update geometry
            y_base = self.INPUT_Y
            y2_base = self.INPUT_Y + cfg.LAYOUT_INPUT_H

            # 1. Left Button (Pause/Resume)
            self.canvas.coords(
                self.ids["btn_pause_bg"],
                *self.get_rounded_rect_points(
                    self.PAUSE_X1,
                    y_base + self.pause_offset_y,
                    self.PAUSE_X2,
                    y2_base + self.pause_offset_y,
                    radius=16,
                ),
            )

            # 1b. Update Pause/Resume Shapes coords
            cx_pause = (self.PAUSE_X1 + self.PAUSE_X2) / 2
            cy_pause = self.INPUT_Y + 30 + self.pause_offset_y

            # Pause Bars (two vertical rectangles)
            # Size: 14h, 4w each, 4 gap
            # Left Bar: cx-6 to cx-2. Right Bar: cx+2 to cx+6. Top cy-7, Bot cy+7
            self.canvas.coords(
                self.ids["btn_icon_pause_bar1"],
                cx_pause - 6,
                cy_pause - 7,
                cx_pause - 2,
                cy_pause + 7,
            )
            self.canvas.coords(
                self.ids["btn_icon_pause_bar2"],
                cx_pause + 2,
                cy_pause - 7,
                cx_pause + 6,
                cy_pause + 7,
            )

            # Resume Triangle (Right pointing)
            # Center roughly at cx. Size 14h.
            # Points: (cx-4, cy-7), (cx-4, cy+7), (cx+7, cy)
            self.canvas.coords(
                self.ids["btn_icon_resume_tri"],
                cx_pause - 4,
                cy_pause - 7,
                cx_pause - 4,
                cy_pause + 7,
                cx_pause + 7,
                cy_pause,
            )

            # 2. Right Button (Abort)
            self.canvas.coords(
                self.ids["btn_abort_small_bg"],
                *self.get_rounded_rect_points(
                    self.ABORT_X1,
                    y_base + self.abort_small_offset_y,
                    self.ABORT_X2,
                    y2_base + self.abort_small_offset_y,
                    radius=16,
                ),
            )

            # 2b. Update Abort Shape coords
            cx_abort = (self.ABORT_X1 + self.ABORT_X2) / 2
            cy_abort = self.INPUT_Y + 30 + self.abort_small_offset_y

            # Stop Square (12x12)
            # cx-6, cy-6 to cx+6, cy+6
            self.canvas.coords(
                self.ids["btn_icon_abort_rect"],
                cx_abort - 6,
                cy_abort - 6,
                cx_abort + 6,
                cy_abort + 6,
            )

        # Folder hover lift + color
        if self.show_folder_btn:
            folder_target = -5 if self.folder_hovered else 0
            if self.folder_btn_pressed:
                folder_target = -1
            self.folder_offset_y += (
                folder_target - self.folder_offset_y
            ) * cfg.ANIM_SPEED_LIFT

            self.canvas.coords(
                self.ids["btn_folder_bg"],
                *self.get_rounded_rect_points(
                    self.FOLDER_X1,
                    self.FOLDER_Y1 + self.folder_offset_y,
                    self.FOLDER_X2,
                    self.FOLDER_Y2 + self.folder_offset_y,
                    radius=15,
                ),
            )
            self.canvas.coords(
                self.ids["btn_folder_text"],
                self.ring_center_x,
                self.FOLDER_Y1 + (self.FOLDER_H / 2) + self.folder_offset_y,
            )

            folder_color_target = (
                self.lighten_color(cfg.COLOR_BTN_HOVER, 0.2)
                if self.folder_hovered
                else cfg.COLOR_BTN_HOVER
            )
            self.target_folder_bg = folder_color_target
            self.current_folder_bg_rgb = self.lerp_color(
                self.current_folder_bg_rgb, self.target_folder_bg, cfg.ANIM_SPEED_LERP
            )
            self.canvas.itemconfig(
                self.ids["btn_folder_bg"],
                fill=self.rgb_to_hex(self.current_folder_bg_rgb),
            )

        # Progress smoothing
        if abs(self.progress_target - self.progress_current) > 0.01:
            self.progress_current += (
                self.progress_target - self.progress_current
            ) * 0.1

        # Update cards
        self.canvas.itemconfig(self.ids["display_speed"], text=self.display_speed)
        self.canvas.itemconfig(self.ids["display_eta"], text=self.display_eta)
        self.canvas.itemconfig(self.ids["display_data"], text=self.display_data)

        # Title rainbow animation
        self.hue_shift = (self.hue_shift - cfg.ANIM_HUE_SPEED) % 1.0
        for i, char_id in enumerate(self.title_chars):
            hue = (self.hue_shift + (i * 0.05)) % 1.0
            rgb = colorsys.hsv_to_rgb(hue, 0.8, 1.0)
            color = "#%02x%02x%02x" % (
                int(rgb[0] * 255),
                int(rgb[1] * 255),
                int(rgb[2] * 255),
            )
            self.canvas.itemconfig(char_id, fill=color)

        self.draw_ring()
        self.root.after(16, self.run_animation_loop)


if __name__ == "__main__":
    root = tk.Tk()
    app = OxUI(root)
    root.mainloop()
