"""
Crosshair overlay engine — spawns and manages the inverted crosshair window
in a background thread. Controlled by the UI via start/stop/update methods.
"""

import ctypes
from ctypes import wintypes
import threading
import time
import sys
import faulthandler

# Enable faulthandler to get traceback on hard crashes
try:
    faulthandler.enable()
except Exception:
    pass

if sys.platform != "win32":
    raise RuntimeError("Windows only")

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
gdi32 = ctypes.windll.gdi32

# --- Win32 Constants ---
WS_EX_TOPMOST     = 0x00000008
WS_EX_TRANSPARENT  = 0x00000020
WS_EX_LAYERED      = 0x00080000
WS_EX_TOOLWINDOW   = 0x00000080
WS_EX_NOACTIVATE   = 0x08000000
WS_POPUP           = 0x80000000
WS_VISIBLE         = 0x10000000

WM_DESTROY       = 0x0002
WM_CLOSE         = 0x0010
WM_TIMER         = 0x0113
WM_NCHITTEST     = 0x0084
WM_MOUSEACTIVATE = 0x0021
WM_USER          = 0x0400
WM_UPDATE_CONFIG = WM_USER + 1   # custom message to live-update settings
WM_QUIT_OVERLAY  = WM_USER + 2   # custom message to request clean shutdown

HTTRANSPARENT        = -1
MA_NOACTIVATEANDEAT  = 4
WDA_EXCLUDEFROMCAPTURE = 0x00000011
WDA_NONE               = 0x00000000

SRCCOPY    = 0x00CC0020
NOTSRCCOPY = 0x00330008
AC_SRC_OVER  = 0x00
AC_SRC_ALPHA = 0x01
ULW_ALPHA    = 0x02
DIB_RGB_COLORS = 0
BI_RGB         = 0
TIMER_ID   = 1

# --- Structures ---
class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

class SIZE(ctypes.Structure):
    _fields_ = [("cx", ctypes.c_long), ("cy", ctypes.c_long)]

class BLENDFUNCTION(ctypes.Structure):
    _fields_ = [("BlendOp", ctypes.c_byte), ("BlendFlags", ctypes.c_byte),
                ("SourceConstantAlpha", ctypes.c_byte), ("AlphaFormat", ctypes.c_byte)]

class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", ctypes.c_uint), ("biWidth", ctypes.c_long),
        ("biHeight", ctypes.c_long), ("biPlanes", ctypes.c_ushort),
        ("biBitCount", ctypes.c_ushort), ("biCompression", ctypes.c_uint),
        ("biSizeImage", ctypes.c_uint), ("biXPelsPerMeter", ctypes.c_long),
        ("biYPelsPerMeter", ctypes.c_long), ("biClrUsed", ctypes.c_uint),
        ("biClrImportant", ctypes.c_uint),
    ]

class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER)]

WNDPROCTYPE = ctypes.WINFUNCTYPE(
    ctypes.c_longlong, wintypes.HWND, ctypes.c_uint,
    wintypes.WPARAM, wintypes.LPARAM
)

class WNDCLASS(ctypes.Structure):
    _fields_ = [
        ('style', ctypes.c_uint), ('lpfnWndProc', WNDPROCTYPE),
        ('cbClsExtra', ctypes.c_int), ('cbWndExtra', ctypes.c_int),
        ('hInstance', wintypes.HINSTANCE), ('hIcon', wintypes.HICON),
        ('hCursor', wintypes.HANDLE), ('hbrBackground', wintypes.HBRUSH),
        ('lpszMenuName', wintypes.LPCWSTR), ('lpszClassName', wintypes.LPCWSTR),
    ]

# --- Function Prototypes ---
kernel32.GetModuleHandleW.restype = wintypes.HMODULE
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
user32.CreateWindowExW.restype = wintypes.HWND
user32.CreateWindowExW.argtypes = [
    wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID,
]
user32.RegisterClassW.restype = wintypes.ATOM
user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASS)]
user32.UnregisterClassW.restype = wintypes.BOOL
user32.UnregisterClassW.argtypes = [wintypes.LPCWSTR, wintypes.HINSTANCE]
user32.DefWindowProcW.restype = ctypes.c_longlong
user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.PostQuitMessage.argtypes = [ctypes.c_int]
user32.SetTimer.argtypes = [wintypes.HWND, ctypes.c_size_t, ctypes.c_uint, ctypes.c_void_p]
user32.SetTimer.restype = ctypes.c_size_t
user32.KillTimer.argtypes = [wintypes.HWND, ctypes.c_size_t]
user32.KillTimer.restype = wintypes.BOOL
user32.SetWindowDisplayAffinity.argtypes = [wintypes.HWND, ctypes.c_uint]
user32.SetWindowDisplayAffinity.restype = ctypes.c_bool
user32.GetDC.argtypes = [wintypes.HWND]
user32.GetDC.restype = wintypes.HDC
user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
user32.ReleaseDC.restype = ctypes.c_int
user32.UpdateLayeredWindow.argtypes = [
    wintypes.HWND, wintypes.HDC, ctypes.POINTER(POINT),
    ctypes.POINTER(SIZE), wintypes.HDC, ctypes.POINTER(POINT),
    wintypes.COLORREF, ctypes.POINTER(BLENDFUNCTION), ctypes.c_uint,
]
user32.UpdateLayeredWindow.restype = wintypes.BOOL
user32.PostMessageW.argtypes = [wintypes.HWND, ctypes.c_uint, wintypes.WPARAM, wintypes.LPARAM]
user32.PostMessageW.restype = wintypes.BOOL
user32.DestroyWindow.argtypes = [wintypes.HWND]
user32.DestroyWindow.restype = wintypes.BOOL
user32.MoveWindow.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.BOOL]
user32.MoveWindow.restype = wintypes.BOOL
user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
user32.SetWindowPos.restype = wintypes.BOOL
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.ShowWindow.restype = wintypes.BOOL

SW_HIDE = 0
SW_SHOWNA = 8  # Show without activating

# Message loop functions
user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, ctypes.c_uint, ctypes.c_uint]
user32.GetMessageW.restype = wintypes.BOOL
user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.TranslateMessage.restype = wintypes.BOOL
user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.DispatchMessageW.restype = ctypes.c_longlong
user32.PeekMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint]
user32.PeekMessageW.restype = wintypes.BOOL

PM_REMOVE = 0x0001

gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
gdi32.CreateCompatibleDC.restype = wintypes.HDC
gdi32.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
gdi32.CreateCompatibleBitmap.restype = wintypes.HBITMAP
gdi32.CreateDIBSection.argtypes = [
    wintypes.HDC, ctypes.POINTER(BITMAPINFO), ctypes.c_uint,
    ctypes.POINTER(ctypes.c_void_p), wintypes.HANDLE, ctypes.c_uint,
]
gdi32.CreateDIBSection.restype = wintypes.HBITMAP
gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
gdi32.SelectObject.restype = wintypes.HGDIOBJ
gdi32.BitBlt.argtypes = [
    wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_uint,
]
gdi32.BitBlt.restype = wintypes.BOOL
gdi32.DeleteDC.argtypes = [wintypes.HDC]
gdi32.DeleteDC.restype = wintypes.BOOL
gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
gdi32.DeleteObject.restype = wintypes.BOOL


# ---------------------------------------------------------------------------
# Mask builder
# ---------------------------------------------------------------------------

def build_cross_mask(sz, thickness, gap=0):
    center = sz // 2
    half_t = thickness // 2
    half_g = gap  # gap extends this many pixels each side from center
    mask = bytearray(sz * sz)
    for y in range(sz):
        for x in range(sz):
            # Vertical bar
            if (center - half_t) <= x < (center - half_t + thickness):
                if not ((center - half_g) <= y <= (center + half_g)):
                    mask[y * sz + x] = 1
            # Horizontal bar
            if (center - half_t) <= y < (center - half_t + thickness):
                if not ((center - half_g) <= x <= (center + half_g)):
                    mask[y * sz + x] = 1
    return bytes(mask)


def build_dot_mask(sz, thickness):
    """Build a filled square dot centered in the mask, sized by thickness."""
    center = sz // 2
    half_t = max(1, thickness) // 2
    t = max(1, thickness)
    mask = bytearray(sz * sz)
    for y in range(sz):
        for x in range(sz):
            if (center - half_t) <= x < (center - half_t + t):
                if (center - half_t) <= y < (center - half_t + t):
                    mask[y * sz + x] = 1
    return bytes(mask)


def build_circle_mask(sz, thickness):
    import math
    center = sz / 2.0 - 0.5
    r_outer = sz / 2.0 - 0.5
    r_inner = max(0, r_outer - thickness)
    mask = bytearray(sz * sz)
    for y in range(sz):
        for x in range(sz):
            d = math.sqrt((x - center) ** 2 + (y - center) ** 2)
            if r_inner <= d <= r_outer:
                mask[y * sz + x] = 1
    return bytes(mask)


# ---------------------------------------------------------------------------
# Color modes
# ---------------------------------------------------------------------------

def color_adaptive(r, g, b, cfg):
    """Luminance-adaptive dual-color."""
    luma = int(0.299 * r + 0.587 * g + 0.114 * b)
    if luma < cfg.get("luma_threshold", 128):
        return cfg.get("color_on_dark", (0, 255, 0))
    else:
        return cfg.get("color_on_light", (255, 0, 255))


def color_invert(r, g, b, _cfg):
    """Pure RGB inversion."""
    return (255 - b, 255 - g, 255 - r)


def color_static(r, g, b, cfg):
    """Static single color (ignores background)."""
    return cfg.get("static_color", (0, 255, 0))


def color_max_contrast(r, g, b, _cfg):
    """Maximum contrast: invert + hue shift + force full saturation/value.
    Converts to HSV, inverts hue by 180, forces S=1 V=1, then back to RGB.
    Returns BGR tuple. Guarantees vivid color maximally different from BG."""
    # Convert RGB to HSV
    r_f, g_f, b_f = r / 255.0, g / 255.0, b / 255.0
    mx = max(r_f, g_f, b_f)
    mn = min(r_f, g_f, b_f)
    d = mx - mn

    # Hue
    if d == 0:
        h = 0.0
    elif mx == r_f:
        h = 60.0 * (((g_f - b_f) / d) % 6)
    elif mx == g_f:
        h = 60.0 * (((b_f - r_f) / d) + 2)
    else:
        h = 60.0 * (((r_f - g_f) / d) + 4)

    # Invert hue by 180 degrees
    h = (h + 180.0) % 360.0

    # Force S=1, V=1 for maximum vividness
    s, v = 1.0, 1.0

    # HSV to RGB
    c = v * s
    x = c * (1.0 - abs((h / 60.0) % 2 - 1.0))
    m = v - c
    if h < 60:
        r2, g2, b2 = c, x, 0.0
    elif h < 120:
        r2, g2, b2 = x, c, 0.0
    elif h < 180:
        r2, g2, b2 = 0.0, c, x
    elif h < 240:
        r2, g2, b2 = 0.0, x, c
    elif h < 300:
        r2, g2, b2 = x, 0.0, c
    else:
        r2, g2, b2 = c, 0.0, x

    ri = int((r2 + m) * 255)
    gi = int((g2 + m) * 255)
    bi = int((b2 + m) * 255)
    return (bi, gi, ri)  # BGR


COLOR_MODES = {
    "Adaptive": color_adaptive,
    "Max Contrast": color_max_contrast,
    "Invert": color_invert,
    "Static": color_static,
}


# ---------------------------------------------------------------------------
# Overlay class
# ---------------------------------------------------------------------------

class CrosshairOverlay:
    """Manages the crosshair overlay window in a background thread."""

    _instance_counter = 0

    def __init__(self):
        self._hwnd = None
        self._thread = None
        self._running = False
        self._lock = threading.Lock()
        self._paint_lock = threading.Lock()
        CrosshairOverlay._instance_counter += 1
        self._class_name = f"InvertCrosshairOverlay_{CrosshairOverlay._instance_counter}"

        # Current config (thread-safe — only read during timer tick)
        self.config = {
            "size": 15,
            "thickness": 1,
            "gap": 0,
            "shape": "cross",          # cross | dot | circle
            "color_mode": "Adaptive",  # Adaptive | Invert | Static
            "color_on_dark": (0, 255, 0),
            "color_on_light": (255, 0, 255),
            "luma_threshold": 128,
            "static_color": (0, 255, 0),
            "offset_x": 1,
            "offset_y": 1,
            "refresh_ms": 7,
            "opacity": 255,            # 1-255
            "show_in_capture": False,   # visible in screen recordings
        }

        # Runtime state filled during _run
        self._mask = None
        self._sz = 0
        self._wx = 0
        self._wy = 0
        self._color_fn = color_adaptive
        self._config_dirty = False

    # ---- public API ----

    @property
    def is_running(self):
        return self._running and self._thread is not None and self._thread.is_alive()

    def start(self):
        if self.is_running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        if not self.is_running:
            return
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
        self._hwnd = None

    def update_config(self, **kwargs):
        """Update config keys. Takes effect on next timer tick."""
        with self._lock:
            self.config.update(kwargs)
            self._config_dirty = True

    # ---- internals ----

    def _rebuild(self):
        with self._lock:
            cfg = dict(self.config)
        sz = cfg["size"]
        if sz % 2 == 0:
            sz += 1  # force odd
        shape = cfg["shape"]
        thick = cfg["thickness"]
        gap = cfg["gap"]

        if shape == "dot":
            mask = build_dot_mask(sz, thick)
        elif shape == "circle":
            mask = build_circle_mask(sz, thick)
        else:
            mask = build_cross_mask(sz, thick, gap)

        screen_w = user32.GetSystemMetrics(0)
        screen_h = user32.GetSystemMetrics(1)
        # Anchor center of crosshair at screen center + offset
        cx = screen_w // 2 + cfg["offset_x"]
        cy = screen_h // 2 + cfg["offset_y"]
        wx = cx - sz // 2
        wy = cy - sz // 2

        self._mask = mask
        self._sz = sz
        self._wx = wx
        self._wy = wy
        self._color_fn = COLOR_MODES.get(cfg["color_mode"], color_adaptive)
        self._opacity = cfg.get("opacity", 255)
        self._refresh_ms = cfg.get("refresh_ms", 7)
        self._show_in_capture = cfg.get("show_in_capture", False)

        return cfg

    def _paint(self):
        if not self._paint_lock.acquire(blocking=False):
            return  # skip if already painting
        try:
            self._paint_inner()
        except Exception:
            pass  # never crash the timer thread
        finally:
            self._paint_lock.release()

    def _paint_inner(self):
        hwnd = self._hwnd
        sz = self._sz
        wx = self._wx
        wy = self._wy
        mask = self._mask
        color_fn = self._color_fn
        opacity = self._opacity

        if not hwnd or not mask or sz <= 0 or not self._running:
            return

        with self._lock:
            cfg = dict(self.config)

        # Track all GDI resources for guaranteed cleanup
        screen_dc = None
        cap_dc = None
        out_dc = None
        cap_bmp = None
        dib = None
        old_cap = None
        old_out = None

        try:
            screen_dc = user32.GetDC(None)
            if not screen_dc:
                return

            cap_dc = gdi32.CreateCompatibleDC(screen_dc)
            out_dc = gdi32.CreateCompatibleDC(screen_dc)
            if not cap_dc or not out_dc:
                return

            cap_bmp = gdi32.CreateCompatibleBitmap(screen_dc, sz, sz)
            if not cap_bmp:
                return

            old_cap = gdi32.SelectObject(cap_dc, cap_bmp)
            gdi32.BitBlt(cap_dc, 0, 0, sz, sz, screen_dc, wx, wy, SRCCOPY)

            bmi = BITMAPINFO()
            bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            bmi.bmiHeader.biWidth = sz
            bmi.bmiHeader.biHeight = -sz
            bmi.bmiHeader.biPlanes = 1
            bmi.bmiHeader.biBitCount = 32
            bmi.bmiHeader.biCompression = BI_RGB

            bits = ctypes.c_void_p()
            dib = gdi32.CreateDIBSection(screen_dc, ctypes.byref(bmi), DIB_RGB_COLORS,
                                          ctypes.byref(bits), None, 0)
            if not dib or not bits.value:
                return

            old_out = gdi32.SelectObject(out_dc, dib)
            gdi32.BitBlt(out_dc, 0, 0, sz, sz, cap_dc, 0, 0, SRCCOPY)

            # Copy pixel data into a safe Python buffer to avoid access violations
            num_bytes = sz * sz * 4
            buf = (ctypes.c_ubyte * num_bytes)()
            ctypes.memmove(buf, bits.value, num_bytes)

            mask_len = len(mask)
            alpha_f = opacity / 255.0  # premultiply factor
            show_cap = self._show_in_capture
            for i in range(sz * sz):
                off = i * 4
                if i < mask_len and mask[i]:
                    # When visible in recordings, sample from nearest
                    # non-masked neighbor to avoid self-capture feedback.
                    # The crosshair's own rendered pixels are under the mask,
                    # so we read from an adjacent clean pixel instead (1px away).
                    if show_cap:
                        px, py = i % sz, i // sz
                        b, g, r = buf[off], buf[off + 1], buf[off + 2]  # fallback
                        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                            nx, ny = px + dx, py + dy
                            if 0 <= nx < sz and 0 <= ny < sz:
                                ni = ny * sz + nx
                                if ni < mask_len and not mask[ni]:
                                    noff = ni * 4
                                    b, g, r = buf[noff], buf[noff + 1], buf[noff + 2]
                                    break
                    else:
                        b, g, r = buf[off], buf[off + 1], buf[off + 2]
                    try:
                        cb, cg, cr = color_fn(r, g, b, cfg)
                    except Exception:
                        cb, cg, cr = 255 - b, 255 - g, 255 - r
                    # Premultiplied alpha: RGB must be scaled by alpha/255
                    cb = max(0, min(255, int(cb * alpha_f)))
                    cg = max(0, min(255, int(cg * alpha_f)))
                    cr = max(0, min(255, int(cr * alpha_f)))
                    buf[off] = cb
                    buf[off + 1] = cg
                    buf[off + 2] = cr
                    buf[off + 3] = opacity
                else:
                    buf[off] = 0
                    buf[off + 1] = 0
                    buf[off + 2] = 0
                    buf[off + 3] = 0

            # Write the processed buffer back to the DIB
            ctypes.memmove(bits.value, buf, num_bytes)

            pt_dst = POINT(wx, wy)
            pt_src = POINT(0, 0)
            wnd_sz = SIZE(sz, sz)
            blend = BLENDFUNCTION(AC_SRC_OVER, 0, 255, AC_SRC_ALPHA)

            user32.UpdateLayeredWindow(
                hwnd, screen_dc, ctypes.byref(pt_dst), ctypes.byref(wnd_sz),
                out_dc, ctypes.byref(pt_src), 0, ctypes.byref(blend), ULW_ALPHA,
            )
        finally:
            # Guaranteed GDI resource cleanup — prevents handle leak
            try:
                if old_out and out_dc:
                    gdi32.SelectObject(out_dc, old_out)
                if old_cap and cap_dc:
                    gdi32.SelectObject(cap_dc, old_cap)
                if dib:
                    gdi32.DeleteObject(dib)
                if cap_bmp:
                    gdi32.DeleteObject(cap_bmp)
                if cap_dc:
                    gdi32.DeleteDC(cap_dc)
                if out_dc:
                    gdi32.DeleteDC(out_dc)
                if screen_dc:
                    user32.ReleaseDC(None, screen_dc)
            except Exception:
                pass

    def _run(self):
        # DPI
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

        cfg = self._rebuild()

        # Minimal WNDPROC — NO heavy work here, just hit-test passthrough.
        # All painting/rebuilding happens in the loop below, never in a callback.
        def wnd_proc(hwnd, msg, wparam, lparam):
            try:
                if msg == WM_NCHITTEST:
                    return HTTRANSPARENT
                if msg == WM_MOUSEACTIVATE:
                    return MA_NOACTIVATEANDEAT
            except BaseException:
                pass
            try:
                return user32.DefWindowProcW(hwnd, msg, wparam, lparam)
            except BaseException:
                return 0

        self._wnd_proc = WNDPROCTYPE(wnd_proc)  # prevent GC

        hInst = kernel32.GetModuleHandleW(None)

        # Unregister old class if it exists (from a previous start/stop cycle)
        try:
            user32.UnregisterClassW(self._class_name, hInst)
        except Exception:
            pass

        wc = WNDCLASS()
        wc.lpfnWndProc = self._wnd_proc
        wc.lpszClassName = self._class_name
        wc.hInstance = hInst
        self._wndclass = wc  # prevent GC
        user32.RegisterClassW(ctypes.byref(wc))

        ex_style = (WS_EX_TOPMOST | WS_EX_TRANSPARENT | WS_EX_LAYERED |
                    WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE)

        self._hwnd = user32.CreateWindowExW(
            ex_style, self._class_name, "XH",
            WS_POPUP | WS_VISIBLE,
            self._wx, self._wy, self._sz, self._sz,
            None, None, hInst, None,
        )

        if not self._hwnd:
            self._running = False
            return

        affinity = WDA_NONE if self._show_in_capture else WDA_EXCLUDEFROMCAPTURE
        user32.SetWindowDisplayAffinity(self._hwnd, affinity)

        # SWP flags — no activation, no z-order change, no repaints, no sent messages
        SWP_FLAGS = 0x0010 | 0x0004 | 0x0008 | 0x0400  # NOACTIVATE|NOZORDER|NOREDRAW|NOSENDCHANGING

        # ===== Main loop: sleep-based, no WM_TIMER, no re-entrancy possible =====
        while self._running:
            try:
                # Drain any pending window messages (non-blocking)
                msg = wintypes.MSG()
                while user32.PeekMessageW(ctypes.byref(msg), self._hwnd, 0, 0, PM_REMOVE):
                    user32.TranslateMessage(ctypes.byref(msg))
                    user32.DispatchMessageW(ctypes.byref(msg))

                # Apply config changes
                if self._config_dirty:
                    self._config_dirty = False
                    self._rebuild()
                    user32.SetWindowPos(self._hwnd, None, self._wx, self._wy,
                                        self._sz, self._sz, SWP_FLAGS)
                    affinity = WDA_NONE if self._show_in_capture else WDA_EXCLUDEFROMCAPTURE
                    user32.SetWindowDisplayAffinity(self._hwnd, affinity)

                # Paint
                self._paint()

                # Sleep for refresh interval
                time.sleep(self._refresh_ms / 1000.0)

            except BaseException:
                break

        # Cleanup
        try:
            if self._hwnd:
                user32.DestroyWindow(self._hwnd)
        except Exception:
            pass
        self._running = False
        self._hwnd = None
