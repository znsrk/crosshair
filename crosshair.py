import ctypes
from ctypes import wintypes
import sys

if sys.platform != "win32":
    print("This script is designed for Windows only.")
    sys.exit(1)

# DPI awareness
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
gdi32 = ctypes.windll.gdi32

# --- Constants ---
WS_EX_TOPMOST = 0x00000008
WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000
WS_POPUP = 0x80000000
WS_VISIBLE = 0x10000000

WM_DESTROY = 0x0002
WM_TIMER = 0x0113
WM_NCHITTEST = 0x0084
WM_MOUSEACTIVATE = 0x0021
HTTRANSPARENT = -1
MA_NOACTIVATEANDEAT = 4

WDA_EXCLUDEFROMCAPTURE = 0x00000011

SRCCOPY = 0x00CC0020
NOTSRCCOPY = 0x00330008
AC_SRC_OVER = 0x00
AC_SRC_ALPHA = 0x01
ULW_ALPHA = 0x02
DIB_RGB_COLORS = 0
BI_RGB = 0

TIMER_ID = 1
REFRESH_MS = 7  # ~60fps

# Crosshair config
CROSSHAIR_SIZE = 15   # odd number for perfect center
CROSSHAIR_THICKNESS = 1
GAP = 0  # gap around center (0 = solid cross)

# Luminance-adaptive colors (BGR order for DIB)
# On dark backgrounds → neon green; on light backgrounds → hot magenta
COLOR_ON_DARK  = (0, 255, 0)      # Neon green  (B, G, R)
COLOR_ON_LIGHT = (255, 0, 255)    # Hot magenta (B, G, R)
LUMA_THRESHOLD = 128              # 0-255, split point between dark/light

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
    ctypes.c_long, wintypes.HWND, ctypes.c_uint,
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
user32.DefWindowProcW.restype = wintypes.LPARAM
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


def build_crosshair_mask(sz, thickness, gap=0):
    """Build a boolean mask for the crosshair '+' shape."""
    center = sz // 2
    half_t = thickness // 2
    mask = bytearray(sz * sz)
    for y in range(sz):
        for x in range(sz):
            # Vertical bar
            if (center - half_t) <= x < (center - half_t + thickness):
                if not ((center - gap) <= y < (center + gap)):
                    mask[y * sz + x] = 1
            # Horizontal bar
            if (center - half_t) <= y < (center - half_t + thickness):
                if not ((center - gap) <= x < (center + gap)):
                    mask[y * sz + x] = 1
    return bytes(mask)


def update_crosshair(hwnd, wx, wy, sz, mask):
    """Capture screen behind crosshair, invert pixels, apply to layered window."""
    screen_dc = user32.GetDC(None)
    cap_dc = gdi32.CreateCompatibleDC(screen_dc)
    out_dc = gdi32.CreateCompatibleDC(screen_dc)

    # Capture screen content at crosshair position
    cap_bmp = gdi32.CreateCompatibleBitmap(screen_dc, sz, sz)
    old_cap = gdi32.SelectObject(cap_dc, cap_bmp)
    gdi32.BitBlt(cap_dc, 0, 0, sz, sz, screen_dc, wx, wy, SRCCOPY)

    # 32bpp top-down DIB for per-pixel alpha output
    bmi = BITMAPINFO()
    bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.bmiHeader.biWidth = sz
    bmi.bmiHeader.biHeight = -sz  # top-down
    bmi.bmiHeader.biPlanes = 1
    bmi.bmiHeader.biBitCount = 32
    bmi.bmiHeader.biCompression = BI_RGB

    bits = ctypes.c_void_p()
    dib = gdi32.CreateDIBSection(screen_dc, ctypes.byref(bmi), DIB_RGB_COLORS,
                                  ctypes.byref(bits), None, 0)
    old_out = gdi32.SelectObject(out_dc, dib)

    # Invert into DIB (we still need the pixel data to read luminance)
    gdi32.BitBlt(out_dc, 0, 0, sz, sz, cap_dc, 0, 0, SRCCOPY)

    # Luminance-adaptive coloring for maximum visibility
    pixel_data = (ctypes.c_ubyte * (sz * sz * 4)).from_address(bits.value)
    for i in range(sz * sz):
        off = i * 4
        if mask[i]:
            # Read original BGR from captured screen
            b, g, r = pixel_data[off], pixel_data[off + 1], pixel_data[off + 2]
            # Perceived luminance (ITU-R BT.601)
            luma = int(0.299 * r + 0.587 * g + 0.114 * b)
            if luma < LUMA_THRESHOLD:
                cb, cg, cr = COLOR_ON_DARK
            else:
                cb, cg, cr = COLOR_ON_LIGHT
            pixel_data[off] = cb
            pixel_data[off + 1] = cg
            pixel_data[off + 2] = cr
            pixel_data[off + 3] = 255
        else:
            pixel_data[off] = 0
            pixel_data[off + 1] = 0
            pixel_data[off + 2] = 0
            pixel_data[off + 3] = 0

    # Push to screen via UpdateLayeredWindow
    pt_dst = POINT(wx, wy)
    pt_src = POINT(0, 0)
    wnd_sz = SIZE(sz, sz)
    blend = BLENDFUNCTION(AC_SRC_OVER, 0, 255, AC_SRC_ALPHA)

    user32.UpdateLayeredWindow(
        hwnd, screen_dc, ctypes.byref(pt_dst), ctypes.byref(wnd_sz),
        out_dc, ctypes.byref(pt_src), 0, ctypes.byref(blend), ULW_ALPHA,
    )

    # Cleanup
    gdi32.SelectObject(cap_dc, old_cap)
    gdi32.SelectObject(out_dc, old_out)
    gdi32.DeleteObject(cap_bmp)
    gdi32.DeleteObject(dib)
    gdi32.DeleteDC(cap_dc)
    gdi32.DeleteDC(out_dc)
    user32.ReleaseDC(None, screen_dc)


def create_crosshair():
    sz = CROSSHAIR_SIZE
    mask = build_crosshair_mask(sz, CROSSHAIR_THICKNESS, GAP)

    screen_w = user32.GetSystemMetrics(0)
    screen_h = user32.GetSystemMetrics(1)
    wx = (screen_w - sz) // 2 + 1
    wy = (screen_h - sz) // 2 + 1

    def wnd_proc(hwnd, msg, wparam, lparam):
        if msg == WM_NCHITTEST:
            return HTTRANSPARENT
        if msg == WM_MOUSEACTIVATE:
            return MA_NOACTIVATEANDEAT
        if msg == WM_TIMER:
            update_crosshair(hwnd, wx, wy, sz, mask)
            return 0
        if msg == WM_DESTROY:
            user32.KillTimer(hwnd, TIMER_ID)
            user32.PostQuitMessage(0)
            return 0
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    proc = WNDPROCTYPE(wnd_proc)

    wc = WNDCLASS()
    wc.lpfnWndProc = proc
    wc.lpszClassName = "InvertCrosshair"
    wc.hInstance = kernel32.GetModuleHandleW(None)

    if not user32.RegisterClassW(ctypes.byref(wc)):
        print("Failed to register window class")
        return

    ex_style = (WS_EX_TOPMOST | WS_EX_TRANSPARENT | WS_EX_LAYERED |
                WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE)

    hwnd = user32.CreateWindowExW(
        ex_style, "InvertCrosshair", "XH",
        WS_POPUP | WS_VISIBLE,
        wx, wy, sz, sz,
        None, None, wc.hInstance, None,
    )
    if not hwnd:
        print("Failed to create window")
        return

    # Exclude from capture so BitBlt doesn't see our own window
    if not user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE):
        print("Warning: SetWindowDisplayAffinity failed — may self-capture")

    # Initial paint
    update_crosshair(hwnd, wx, wy, sz, mask)

    # Start refresh timer
    user32.SetTimer(hwnd, TIMER_ID, REFRESH_MS, None)

    print(f"Crosshair active at ({wx}, {wy}), size {sz}x{sz}. Close this terminal to quit.")

    msg = wintypes.MSG()
    try:
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    create_crosshair()
