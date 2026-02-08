"""
Crosshair Overlay — Settings UI
"""

import tkinter as tk
from tkinter import colorchooser
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from crosshair_overlay import CrosshairOverlay

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crosshair_config.json")

DEFAULT_CONFIG = {
    "size": 15,
    "thickness": 1,
    "gap": 0,
    "shape": "cross",
    "color_mode": "Adaptive",
    "color_on_dark": [0, 255, 0],
    "color_on_light": [255, 0, 255],
    "luma_threshold": 128,
    "static_color": [0, 255, 0],
    "offset_x": 1,
    "offset_y": 1,
    "refresh_ms": 7,
    "opacity": 255,
    "show_in_capture": False,
}

# ──────────────────────────── Theme ────────────────────────────

BG           = "#0f0f0f"
BG_CARD      = "#1a1a1a"
BG_INPUT     = "#252525"
BG_HOVER     = "#2a2a2a"
FG           = "#e0e0e0"
FG_DIM       = "#707070"
FG_BRIGHT    = "#ffffff"
ACCENT       = "#6c63ff"
ACCENT_HOVER = "#7f78ff"
DANGER       = "#e05252"
DANGER_HOVER = "#f06060"
SUCCESS      = "#4caf50"
BORDER       = "#2a2a2a"
TROUGH       = "#2a2a2a"
SLIDER_FG    = "#6c63ff"

FONT         = ("Segoe UI", 9)
FONT_SM      = ("Segoe UI", 8)
FONT_LBL     = ("Segoe UI", 9)
FONT_VAL     = ("Segoe UI Semibold", 9)
FONT_TITLE   = ("Segoe UI Semibold", 13)
FONT_SECTION = ("Segoe UI Semibold", 9)
FONT_BTN     = ("Segoe UI Semibold", 9)


# ──────────────────────────── Helpers ────────────────────────────

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                cfg = json.load(f)
            for k, v in DEFAULT_CONFIG.items():
                cfg.setdefault(k, v)
            return cfg
        except Exception:
            pass
    return dict(DEFAULT_CONFIG)


def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


def rgb_hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(int(rgb[0]), int(rgb[1]), int(rgb[2]))


def luminance(hex_color):
    h = hex_color.lstrip("#")
    r, g, b = int(h[:2], 16), int(h[2:4], 16), int(h[4:], 16)
    return 0.299 * r + 0.587 * g + 0.114 * b


# ──────────────────────────── Custom Widgets ────────────────────────────

class FlatButton(tk.Canvas):
    """Rounded flat button drawn on canvas."""

    def __init__(self, parent, text="", command=None, bg=ACCENT, fg="#ffffff",
                 hover_bg=ACCENT_HOVER, width=100, height=32, radius=6, font=FONT_BTN, **kw):
        super().__init__(parent, width=width, height=height, bg=BG_CARD,
                         highlightthickness=0, cursor="hand2", **kw)
        self._bg = bg
        self._fg = fg
        self._hover_bg = hover_bg
        self._cur_bg = bg
        self._text = text
        self._command = command
        self._r = radius
        self._font = font
        self._draw()
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonRelease-1>", self._on_click)

    def _round_rect(self, x1, y1, x2, y2, r, **kw):
        pts = [
            x1+r, y1, x2-r, y1, x2, y1, x2, y1+r,
            x2, y2-r, x2, y2, x2-r, y2, x1+r, y2,
            x1, y2, x1, y2-r, x1, y1+r, x1, y1,
        ]
        return self.create_polygon(pts, smooth=True, **kw)

    def _draw(self):
        self.delete("all")
        w, h = int(self["width"]), int(self["height"])
        self._round_rect(0, 0, w, h, self._r, fill=self._cur_bg, outline="")
        self.create_text(w // 2, h // 2, text=self._text, fill=self._fg, font=self._font)

    def _on_enter(self, e):
        self._cur_bg = self._hover_bg
        self._draw()

    def _on_leave(self, e):
        self._cur_bg = self._bg
        self._draw()

    def _on_click(self, e):
        if self._command:
            self._command()

    def set_colors(self, bg, hover_bg):
        self._bg = bg
        self._hover_bg = hover_bg
        self._cur_bg = bg
        self._draw()

    def set_text(self, text):
        self._text = text
        self._draw()


class SliderRow(tk.Frame):
    """Label + slider + clickable value (click to type a number)."""

    def __init__(self, parent, label, from_, to_, variable, on_change, **kw):
        super().__init__(parent, bg=BG_CARD, **kw)
        self._var = variable
        self._on_change = on_change
        self._from = from_
        self._to = to_
        self._editing = False

        lbl = tk.Label(self, text=label, bg=BG_CARD, fg=FG_DIM, font=FONT_LBL, anchor="w", width=13)
        lbl.pack(side="left", padx=(12, 0))

        # Value label (click to edit)
        self._val_frame = tk.Frame(self, bg=BG_CARD, width=42, height=20)
        self._val_frame.pack(side="right", padx=(0, 12))
        self._val_frame.pack_propagate(False)

        self._val_lbl = tk.Label(self._val_frame, text=str(variable.get()), bg=BG_CARD,
                                  fg=FG_BRIGHT, font=FONT_VAL, anchor="e", cursor="xterm")
        self._val_lbl.pack(fill="both", expand=True)
        self._val_lbl.bind("<Button-1>", self._start_edit)

        # Hidden entry for editing
        self._entry = tk.Entry(self._val_frame, bg=BG_INPUT, fg=FG_BRIGHT, font=FONT_VAL,
                                insertbackground=FG_BRIGHT, relief="flat", bd=0,
                                highlightthickness=1, highlightcolor=ACCENT,
                                highlightbackground=BG_INPUT, justify="right", width=4)

        self._entry.bind("<Return>", self._commit_edit)
        self._entry.bind("<Escape>", self._cancel_edit)
        self._entry.bind("<FocusOut>", self._commit_edit)

        self._slider = tk.Scale(
            self, from_=from_, to=to_, orient="horizontal", variable=variable,
            command=self._changed, showvalue=False, sliderlength=16, sliderrelief="flat",
            bg="#4a4a4a", fg=FG, troughcolor="#333333", activebackground=ACCENT,
            highlightthickness=0, bd=0, width=10,
        )
        self._slider.pack(side="right", fill="x", expand=True, padx=(8, 8))

    def _start_edit(self, e=None):
        if self._editing:
            return
        self._editing = True
        self._val_lbl.pack_forget()
        self._entry.delete(0, "end")
        self._entry.insert(0, str(self._var.get()))
        self._entry.pack(fill="both", expand=True)
        self._entry.focus_set()
        self._entry.select_range(0, "end")

    def _commit_edit(self, e=None):
        if not self._editing:
            return
        txt = self._entry.get().strip()
        try:
            v = int(float(txt))
            v = max(self._from, min(self._to, v))
            self._var.set(v)
            self._val_lbl.config(text=str(v))
            if self._on_change:
                self._on_change(v)
        except ValueError:
            pass
        self._editing = False
        self._entry.pack_forget()
        self._val_lbl.pack(fill="both", expand=True)

    def _cancel_edit(self, e=None):
        self._editing = False
        self._entry.pack_forget()
        self._val_lbl.pack(fill="both", expand=True)

    def _changed(self, val):
        v = int(float(val))
        self._val_lbl.config(text=str(v))
        if self._on_change:
            self._on_change(v)

    def set(self, val):
        self._var.set(val)
        self._val_lbl.config(text=str(int(val)))


class DropdownRow(tk.Frame):
    """Label + styled option menu."""

    def __init__(self, parent, label, variable, options, on_change, **kw):
        super().__init__(parent, bg=BG_CARD, **kw)
        self._var = variable
        self._on_change = on_change

        lbl = tk.Label(self, text=label, bg=BG_CARD, fg=FG_DIM, font=FONT_LBL, anchor="w", width=13)
        lbl.pack(side="left", padx=(12, 0))

        self._menu = tk.OptionMenu(self, variable, *options, command=self._changed)
        self._menu.config(
            bg=BG_INPUT, fg=FG, activebackground=BG_HOVER, activeforeground=FG_BRIGHT,
            font=FONT, highlightthickness=0, relief="flat", bd=0, width=10,
            indicatoron=True, cursor="hand2",
        )
        self._menu["menu"].config(
            bg=BG_INPUT, fg=FG, activebackground=ACCENT, activeforeground="#ffffff",
            font=FONT, bd=0, relief="flat",
        )
        self._menu.pack(side="right", padx=(0, 8))

    def _changed(self, val):
        if self._on_change:
            self._on_change(val)


class ColorRow(tk.Frame):
    """Label + color swatch button."""

    def __init__(self, parent, label, initial_color, on_change, **kw):
        super().__init__(parent, bg=BG_CARD, **kw)
        self._on_change = on_change
        self._color = list(initial_color)

        lbl = tk.Label(self, text=label, bg=BG_CARD, fg=FG_DIM, font=FONT_LBL, anchor="w", width=13)
        lbl.pack(side="left", padx=(12, 0))

        self._hex_lbl = tk.Label(self, text=rgb_hex(self._color).upper(), bg=BG_CARD,
                                  fg=FG_DIM, font=FONT_SM)
        self._hex_lbl.pack(side="right", padx=(0, 12))

        self._swatch = tk.Canvas(self, width=24, height=24, bg=BG_CARD, highlightthickness=0,
                                  cursor="hand2")
        self._swatch.pack(side="right", padx=(0, 6))
        self._draw_swatch()
        self._swatch.bind("<ButtonRelease-1>", self._pick)

    def _draw_swatch(self):
        self._swatch.delete("all")
        c = rgb_hex(self._color)
        self._swatch.create_oval(2, 2, 22, 22, fill=c, outline="#404040", width=1)

    def _pick(self, e=None):
        result = colorchooser.askcolor(color=rgb_hex(self._color), title="Pick Color")
        if result and result[0]:
            self._color = [int(c) for c in result[0]]
            self._draw_swatch()
            self._hex_lbl.config(text=rgb_hex(self._color).upper())
            if self._on_change:
                self._on_change(list(self._color))

    def set_color(self, rgb):
        self._color = list(rgb)
        self._draw_swatch()
        self._hex_lbl.config(text=rgb_hex(self._color).upper())

    def get_color(self):
        return list(self._color)


class SectionHeader(tk.Frame):
    """Subtle section divider with label."""

    def __init__(self, parent, text, **kw):
        super().__init__(parent, bg=BG_CARD, **kw)
        tk.Label(self, text=text.upper(), bg=BG_CARD, fg=FG_DIM, font=FONT_SECTION,
                 anchor="w").pack(side="left", padx=12, pady=(10, 4))
        sep = tk.Frame(self, bg=BORDER, height=1)
        sep.pack(side="bottom", fill="x", padx=12)


class SegmentedControl(tk.Canvas):
    """Animated segmented toggle with sliding highlight."""

    def __init__(self, parent, options, variable, on_change, **kw):
        self._items = list(options)
        self._var = variable
        self._on_change = on_change
        self._selected = self._items.index(variable.get()) if variable.get() in self._items else 0
        self._seg_w = 72
        self._total_h = 28
        self._total_w = self._seg_w * len(self._items)
        self._radius = 6
        self._anim_x = float(self._selected * self._seg_w)
        self._target_x = self._anim_x

        super().__init__(parent, width=self._total_w + 4, height=self._total_h + 4,
                         bg=BG_CARD, highlightthickness=0, cursor="hand2", **kw)
        self._draw()
        self.bind("<ButtonRelease-1>", self._on_click)

    def _round_rect(self, x1, y1, x2, y2, r, **kw):
        pts = [
            x1+r, y1, x2-r, y1, x2, y1, x2, y1+r,
            x2, y2-r, x2, y2, x2-r, y2, x1+r, y2,
            x1, y2, x1, y2-r, x1, y1+r, x1, y1,
        ]
        return self.create_polygon(pts, smooth=True, **kw)

    def _draw(self):
        self.delete("all")
        # Background track
        self._round_rect(2, 2, self._total_w + 2, self._total_h + 2, self._radius,
                         fill=BG_INPUT, outline=BORDER)
        # Sliding highlight pill
        x = self._anim_x + 2
        self._round_rect(x + 2, 4, x + self._seg_w - 2, self._total_h, self._radius - 2,
                         fill=ACCENT, outline="")
        # Labels
        for i, opt in enumerate(self._items):
            cx = i * self._seg_w + self._seg_w // 2 + 2
            cy = self._total_h // 2 + 2
            fg = "#ffffff" if i == self._selected else FG_DIM
            self.create_text(cx, cy, text=opt.capitalize(), fill=fg, font=FONT_SM)

    def _on_click(self, e):
        idx = max(0, min(len(self._items) - 1, (e.x - 2) // self._seg_w))
        if idx != self._selected:
            self._selected = idx
            self._var.set(self._items[idx])
            self._target_x = float(idx * self._seg_w)
            self._animate()
            if self._on_change:
                self._on_change(self._items[idx])

    def _animate(self):
        diff = self._target_x - self._anim_x
        if abs(diff) < 1.5:
            self._anim_x = self._target_x
            self._draw()
            return
        self._anim_x += diff * 0.28
        self._draw()
        self.after(10, self._animate)

    def set(self, value):
        if value in self._items:
            self._selected = self._items.index(value)
            self._var.set(value)
            self._anim_x = float(self._selected * self._seg_w)
            self._target_x = self._anim_x
            self._draw()


# ──────────────────────────── Crosshair Preview ────────────────────────────

class CrosshairPreview(tk.Canvas):
    """Small canvas that draws a preview of the crosshair shape."""

    def __init__(self, parent, **kw):
        super().__init__(parent, width=80, height=80, bg=BG_INPUT, highlightthickness=0, **kw)
        self._cfg = {}

    def update_preview(self, cfg):
        self._cfg = cfg
        self.delete("all")
        w, h = 80, 80
        cx, cy = w // 2, h // 2

        # checkerboard background to show transparency
        sq = 8
        for row in range(h // sq + 1):
            for col in range(w // sq + 1):
                c = "#1f1f1f" if (row + col) % 2 == 0 else "#2a2a2a"
                self.create_rectangle(col * sq, row * sq, (col + 1) * sq, (row + 1) * sq,
                                       fill=c, outline="")

        shape = cfg.get("shape", "cross")
        sz = min(cfg.get("size", 15), 60)
        thick = max(1, cfg.get("thickness", 1))
        gap = cfg.get("gap", 0)
        color = ACCENT
        alpha_hex = ACCENT

        if shape == "cross":
            half = sz // 2
            ht = thick // 2
            # vertical
            if gap > 0:
                self.create_rectangle(cx - ht, cy - half, cx - ht + thick, cy - gap,
                                       fill=color, outline="")
                self.create_rectangle(cx - ht, cy + gap + 1, cx - ht + thick, cy + half + 1,
                                       fill=color, outline="")
                self.create_rectangle(cx - half, cy - ht, cx - gap, cy - ht + thick,
                                       fill=color, outline="")
                self.create_rectangle(cx + gap + 1, cy - ht, cx + half + 1, cy - ht + thick,
                                       fill=color, outline="")
            else:
                self.create_rectangle(cx - ht, cy - half, cx - ht + thick, cy + half + 1,
                                       fill=color, outline="")
                self.create_rectangle(cx - half, cy - ht, cx + half + 1, cy - ht + thick,
                                       fill=color, outline="")
        elif shape == "dot":
            ht = thick // 2
            self.create_rectangle(cx - ht, cy - ht, cx - ht + thick, cy - ht + thick,
                                   fill=color, outline="")
        elif shape == "circle":
            r = sz // 2
            self.create_oval(cx - r, cy - r, cx + r, cy + r, outline=color, width=thick)


# ──────────────────────────── Main App ────────────────────────────

class CrosshairApp:
    def __init__(self):
        self.overlay = CrosshairOverlay()
        self.cfg = load_config()

        self.root = tk.Tk()
        self.root.title("Crosshair")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Try to set dark title bar on Windows 10/11
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE,
                ctypes.byref(ctypes.c_int(1)), ctypes.sizeof(ctypes.c_int)
            )
        except Exception:
            pass

        self._build_ui()
        self._apply_config()
        self._update_preview()

    def _build_ui(self):
        root = self.root

        # ── Title bar area ──
        title_bar = tk.Frame(root, bg=BG)
        title_bar.pack(fill="x", padx=16, pady=(14, 0))

        tk.Label(title_bar, text="Crosshair", bg=BG, fg=FG_BRIGHT,
                 font=FONT_TITLE).pack(side="left")

        # Status dot
        self._status_canvas = tk.Canvas(title_bar, width=10, height=10, bg=BG,
                                         highlightthickness=0)
        self._status_canvas.pack(side="left", padx=(10, 0), pady=2)
        self._status_dot = self._status_canvas.create_oval(1, 1, 9, 9, fill=DANGER, outline="")

        self._status_lbl = tk.Label(title_bar, text="OFF", bg=BG, fg=FG_DIM, font=FONT_SM)
        self._status_lbl.pack(side="left", padx=(4, 0))

        self.btn_toggle = FlatButton(title_bar, text="START", command=self._toggle,
                                      bg=ACCENT, hover_bg=ACCENT_HOVER, width=80, height=30)
        self.btn_toggle.pack(side="right")

        # ── Main card ──
        card = tk.Frame(root, bg=BG_CARD)
        card.pack(fill="both", expand=True, padx=16, pady=12)

        # ── Preview + quick info ──
        top_row = tk.Frame(card, bg=BG_CARD)
        top_row.pack(fill="x", padx=0, pady=(8, 0))

        self._preview = CrosshairPreview(top_row)
        self._preview.pack(side="left", padx=(12, 12), pady=4)

        info = tk.Frame(top_row, bg=BG_CARD)
        info.pack(side="left", fill="both", expand=True)

        self._info_shape = tk.Label(info, text="", bg=BG_CARD, fg=FG, font=FONT_VAL, anchor="w")
        self._info_shape.pack(anchor="w", pady=(8, 0))
        self._info_detail = tk.Label(info, text="", bg=BG_CARD, fg=FG_DIM, font=FONT_SM, anchor="w")
        self._info_detail.pack(anchor="w", pady=(2, 0))
        self._info_mode = tk.Label(info, text="", bg=BG_CARD, fg=FG_DIM, font=FONT_SM, anchor="w")
        self._info_mode.pack(anchor="w", pady=(2, 0))

        # ── Shape section ──
        SectionHeader(card, "Shape").pack(fill="x")

        self.shape_var = tk.StringVar()
        self._shape_seg = SegmentedControl(card, ["cross", "dot", "circle"],
                                           self.shape_var, self._on_any_change)
        self._shape_seg.pack(padx=12, pady=(6, 2))

        self.size_var = tk.IntVar()
        self._sl_size = SliderRow(card, "Size", 3, 61, self.size_var, lambda v: self._on_any_change())
        self._sl_size.pack(fill="x")

        self.thick_var = tk.IntVar()
        self._sl_thick = SliderRow(card, "Thickness", 1, 10, self.thick_var, lambda v: self._on_any_change())
        self._sl_thick.pack(fill="x")

        self.gap_var = tk.IntVar()
        self._sl_gap = SliderRow(card, "Gap", 0, 10, self.gap_var, lambda v: self._on_any_change())
        self._sl_gap.pack(fill="x")

        # ── Color section ──
        SectionHeader(card, "Color").pack(fill="x")

        self.cmode_var = tk.StringVar()
        DropdownRow(card, "Mode", self.cmode_var,
                    ["Adaptive", "Max Contrast", "Invert", "Static"],
                    self._on_any_change).pack(fill="x")

        self._cr_dark = ColorRow(card, "On Dark BG", self.cfg["color_on_dark"],
                                  lambda c: self._on_color("color_on_dark", c))
        self._cr_dark.pack(fill="x")

        self._cr_light = ColorRow(card, "On Light BG", self.cfg["color_on_light"],
                                   lambda c: self._on_color("color_on_light", c))
        self._cr_light.pack(fill="x")

        self._cr_static = ColorRow(card, "Static Color", self.cfg["static_color"],
                                    lambda c: self._on_color("static_color", c))
        self._cr_static.pack(fill="x")

        self.luma_var = tk.IntVar()
        self._sl_luma = SliderRow(card, "Luma Threshold", 1, 254, self.luma_var,
                                   lambda v: self._on_any_change())
        self._sl_luma.pack(fill="x")

        self.opacity_var = tk.IntVar()
        self._sl_opacity = SliderRow(card, "Opacity", 10, 255, self.opacity_var,
                                      lambda v: self._on_any_change())
        self._sl_opacity.pack(fill="x")

        # ── Position section ──
        SectionHeader(card, "Position").pack(fill="x")

        self.offx_var = tk.IntVar()
        self._sl_offx = SliderRow(card, "X Offset", -10, 10, self.offx_var,
                                   lambda v: self._on_any_change())
        self._sl_offx.pack(fill="x")

        self.offy_var = tk.IntVar()
        self._sl_offy = SliderRow(card, "Y Offset", -10, 10, self.offy_var,
                                   lambda v: self._on_any_change())
        self._sl_offy.pack(fill="x")

        # ── Performance section ──
        SectionHeader(card, "Performance").pack(fill="x")

        self.refresh_var = tk.IntVar()
        self._sl_refresh = SliderRow(card, "Refresh (ms)", 1, 100, self.refresh_var,
                                      lambda v: self._on_any_change())
        self._sl_refresh.pack(fill="x")

        # ── Recording toggle ──
        rec_row = tk.Frame(card, bg=BG_CARD)
        rec_row.pack(fill="x", padx=12, pady=(8, 4))
        tk.Label(rec_row, text="Show in Recordings", bg=BG_CARD, fg=FG_DIM,
                 font=FONT_LBL, anchor="w").pack(side="left")
        self.capture_var = tk.BooleanVar(value=False)
        self._rec_toggle = tk.Checkbutton(
            rec_row, variable=self.capture_var, command=self._on_any_change,
            bg=BG_CARD, fg=FG, selectcolor=BG_INPUT, activebackground=BG_CARD,
            activeforeground=FG, highlightthickness=0, bd=0, cursor="hand2",
        )
        self._rec_toggle.pack(side="right")

        rec_note = tk.Label(card, text="This feature may cause some weird artifacts on the crosshair,\n"
                                        "and is recommended to be used only with a thickness of 1 pixel.",
                            bg=BG_CARD, fg="#555555", font=("Segoe UI", 7), anchor="w", justify="left")
        rec_note.pack(fill="x", padx=16, pady=(0, 4))

        # bottom spacer inside card
        tk.Frame(card, bg=BG_CARD, height=8).pack()

        # ── Bottom buttons ──
        bottom = tk.Frame(root, bg=BG)
        bottom.pack(fill="x", padx=16, pady=(0, 14))

        FlatButton(bottom, text="SAVE", command=self._save,
                   bg=BG_INPUT, hover_bg=BG_HOVER, fg=FG, width=70, height=28).pack(side="left")

        FlatButton(bottom, text="RESET", command=self._reset,
                   bg=BG_INPUT, hover_bg=BG_HOVER, fg=FG, width=70, height=28).pack(side="left", padx=(8, 0))

        self._toast_lbl = tk.Label(bottom, text="", bg=BG, fg=SUCCESS, font=FONT_SM)
        self._toast_lbl.pack(side="right")

    # ──────────────────── Config ↔ UI ────────────────────

    def _apply_config(self):
        c = self.cfg
        self._shape_seg.set(c["shape"])
        self._sl_size.set(c["size"])
        self._sl_thick.set(c["thickness"])
        self._sl_gap.set(c["gap"])
        self.cmode_var.set(c["color_mode"])
        self._sl_luma.set(c["luma_threshold"])
        self._sl_opacity.set(c["opacity"])
        self._sl_offx.set(c["offset_x"])
        self._sl_offy.set(c["offset_y"])
        self._sl_refresh.set(c["refresh_ms"])
        self.capture_var.set(c.get("show_in_capture", False))
        self._cr_dark.set_color(c["color_on_dark"])
        self._cr_light.set_color(c["color_on_light"])
        self._cr_static.set_color(c["static_color"])

    def _read_ui(self):
        self.cfg["shape"] = self.shape_var.get()
        self.cfg["size"] = self.size_var.get()
        self.cfg["thickness"] = self.thick_var.get()
        self.cfg["gap"] = self.gap_var.get()
        self.cfg["color_mode"] = self.cmode_var.get()
        self.cfg["luma_threshold"] = self.luma_var.get()
        self.cfg["opacity"] = self.opacity_var.get()
        self.cfg["offset_x"] = self.offx_var.get()
        self.cfg["offset_y"] = self.offy_var.get()
        self.cfg["refresh_ms"] = self.refresh_var.get()
        self.cfg["show_in_capture"] = self.capture_var.get()
        self.cfg["color_on_dark"] = self._cr_dark.get_color()
        self.cfg["color_on_light"] = self._cr_light.get_color()
        self.cfg["static_color"] = self._cr_static.get_color()

    def _update_preview(self):
        self._read_ui()
        self._preview.update_preview(self.cfg)
        shape = self.cfg["shape"].capitalize()
        self._info_shape.config(text=f"{shape} Crosshair")
        self._info_detail.config(text=f"Size {self.cfg['size']}  ·  Thick {self.cfg['thickness']}  ·  Gap {self.cfg['gap']}")
        self._info_mode.config(text=f"Mode: {self.cfg['color_mode']}  ·  Opacity: {self.cfg['opacity']}")

    # ──────────────────── Events ────────────────────

    def _on_any_change(self, *_):
        self._read_ui()
        self._update_preview()
        self._push()

    def _on_color(self, key, rgb):
        self.cfg[key] = rgb
        self._update_preview()
        self._push()

    def _push(self):
        if self.overlay.is_running:
            self.overlay.update_config(
                size=self.cfg["size"],
                thickness=self.cfg["thickness"],
                gap=self.cfg["gap"],
                shape=self.cfg["shape"],
                color_mode=self.cfg["color_mode"],
                color_on_dark=tuple(self.cfg["color_on_dark"]),
                color_on_light=tuple(self.cfg["color_on_light"]),
                luma_threshold=self.cfg["luma_threshold"],
                static_color=tuple(self.cfg["static_color"]),
                offset_x=self.cfg["offset_x"],
                offset_y=self.cfg["offset_y"],
                opacity=self.cfg["opacity"],
                refresh_ms=self.cfg["refresh_ms"],
                show_in_capture=self.cfg["show_in_capture"],
            )

    def _toggle(self):
        if self.overlay.is_running:
            self.overlay.stop()
            self.btn_toggle.set_text("START")
            self.btn_toggle.set_colors(ACCENT, ACCENT_HOVER)
            self._status_canvas.itemconfig(self._status_dot, fill=DANGER)
            self._status_lbl.config(text="OFF", fg=FG_DIM)
        else:
            self._read_ui()
            self.overlay.config.update({
                k: (tuple(v) if isinstance(v, list) else v)
                for k, v in self.cfg.items()
            })
            self.overlay.start()
            self.btn_toggle.set_text("STOP")
            self.btn_toggle.set_colors(DANGER, DANGER_HOVER)
            self._status_canvas.itemconfig(self._status_dot, fill=SUCCESS)
            self._status_lbl.config(text="ACTIVE", fg=SUCCESS)

    def _save(self):
        self._read_ui()
        save_config(self.cfg)
        self._toast("Saved")

    def _reset(self):
        self.cfg = dict(DEFAULT_CONFIG)
        self._apply_config()
        self._update_preview()
        self._push()
        self._toast("Reset")

    def _toast(self, msg):
        self._toast_lbl.config(text=msg)
        self.root.after(2000, lambda: self._toast_lbl.config(text=""))

    def _on_close(self):
        if self.overlay.is_running:
            self.overlay.stop()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = CrosshairApp()
    app.run()
