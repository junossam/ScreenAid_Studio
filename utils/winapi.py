from __future__ import annotations

import ctypes
from ctypes import wintypes


user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
kernel32 = ctypes.windll.kernel32
magnification = ctypes.windll.magnification

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

HHOOK = ctypes.c_void_p
HINSTANCE = ctypes.c_void_p
HWND = wintypes.HWND
HMONITOR = ctypes.c_void_p
LONG_PTR = wintypes.LPARAM
LRESULT = wintypes.LPARAM
ULONG_PTR = ctypes.c_size_t

GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_TOPMOST = 0x00000008
LWA_ALPHA = 0x00000002
WS_EX_NOACTIVATE = 0x08000000
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_FRAMECHANGED = 0x0020
WDA_NONE = 0x00000000
WDA_EXCLUDEFROMCAPTURE = 0x00000011

WH_KEYBOARD_LL = 13
WH_MOUSE_LL = 14
WM_KEYDOWN = 0x0100
WM_SYSKEYDOWN = 0x0104
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205
WM_MBUTTONDOWN = 0x0207
WM_MBUTTONUP = 0x0208
WM_MOUSEMOVE = 0x0200
WM_MOUSEWHEEL = 0x020A
WM_MOUSEHWHEEL = 0x020E
WM_HOTKEY = 0x0312
HC_ACTION = 0
VK_ESCAPE = 0x1B
VK_LBUTTON = 0x01
VK_RBUTTON = 0x02
VK_MBUTTON = 0x04

MONITOR_DEFAULTTONEAREST = 2
LLMHF_INJECTED = 0x00000001
LLMHF_LOWER_IL_INJECTED = 0x00000002

SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79


class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


class MONITORINFOEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", wintypes.DWORD),
        ("szDevice", wintypes.WCHAR * 32),
    ]


class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("pt", POINT),
        ("mouseData", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


LowLevelMouseProc = ctypes.WINFUNCTYPE(
    LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM
)
LowLevelKeyboardProc = ctypes.WINFUNCTYPE(
    LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM
)
MonitorEnumProc = ctypes.WINFUNCTYPE(
    wintypes.BOOL,
    HMONITOR,
    wintypes.HDC,
    ctypes.POINTER(RECT),
    wintypes.LPARAM,
)

user32.SetWindowsHookExW.argtypes = [
    ctypes.c_int,
    ctypes.c_void_p,
    HINSTANCE,
    wintypes.DWORD,
]
user32.SetWindowsHookExW.restype = HHOOK
user32.UnhookWindowsHookEx.argtypes = [HHOOK]
user32.UnhookWindowsHookEx.restype = wintypes.BOOL
user32.CallNextHookEx.argtypes = [
    HHOOK,
    ctypes.c_int,
    wintypes.WPARAM,
    wintypes.LPARAM,
]
user32.CallNextHookEx.restype = LRESULT
user32.MonitorFromPoint.argtypes = [POINT, wintypes.DWORD]
user32.MonitorFromPoint.restype = ctypes.c_void_p
user32.GetMonitorInfoW.argtypes = [ctypes.c_void_p, ctypes.POINTER(MONITORINFOEXW)]
user32.GetMonitorInfoW.restype = wintypes.BOOL
user32.EnumDisplayMonitors.argtypes = [
    wintypes.HDC,
    ctypes.POINTER(RECT),
    MonitorEnumProc,
    wintypes.LPARAM,
]
user32.EnumDisplayMonitors.restype = wintypes.BOOL
user32.GetDoubleClickTime.argtypes = []
user32.GetDoubleClickTime.restype = wintypes.UINT
user32.GetSystemMetrics.argtypes = [ctypes.c_int]
user32.GetSystemMetrics.restype = ctypes.c_int
user32.RegisterHotKey.argtypes = [HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
user32.RegisterHotKey.restype = wintypes.BOOL
user32.UnregisterHotKey.argtypes = [HWND, ctypes.c_int]
user32.UnregisterHotKey.restype = wintypes.BOOL
user32.RegisterWindowMessageW.argtypes = [wintypes.LPCWSTR]
user32.RegisterWindowMessageW.restype = wintypes.UINT
user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
user32.GetCursorPos.restype = wintypes.BOOL
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short
user32.GetForegroundWindow.argtypes = []
user32.GetForegroundWindow.restype = HWND
user32.GetWindowThreadProcessId.argtypes = [HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.QueryFullProcessImageNameW.argtypes = [
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.LPWSTR,
    ctypes.POINTER(wintypes.DWORD),
]
kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL
user32.GetWindowRect.argtypes = [HWND, ctypes.POINTER(RECT)]
user32.GetWindowRect.restype = wintypes.BOOL
user32.WindowFromPoint.argtypes = [POINT]
user32.WindowFromPoint.restype = HWND
user32.SetWindowPos.argtypes = [
    HWND,
    HWND,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.UINT,
]
user32.SetWindowPos.restype = wintypes.BOOL
user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
user32.SetCursorPos.restype = wintypes.BOOL
user32.mouse_event.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ULONG_PTR]
user32.mouse_event.restype = None
# Magnification API's full-screen transform - the same in-process API Windows
# Magnifier and Sysinternals Zoomit's LiveZoom use internally to do a live
# display-level zoom (DWM transform, no window covers the screen, so mouse/
# keyboard input keeps hitting the real, already-correct on-screen target).
magnification.MagInitialize.restype = wintypes.BOOL
magnification.MagUninitialize.restype = wintypes.BOOL
magnification.MagSetFullscreenTransform.argtypes = [ctypes.c_float, ctypes.c_int, ctypes.c_int]
magnification.MagSetFullscreenTransform.restype = wintypes.BOOL
magnification.MagGetFullscreenTransform.argtypes = [
    ctypes.POINTER(ctypes.c_float),
    ctypes.POINTER(ctypes.c_int),
    ctypes.POINTER(ctypes.c_int),
]
magnification.MagGetFullscreenTransform.restype = wintypes.BOOL

if hasattr(user32, "SetWindowDisplayAffinity"):
    user32.SetWindowDisplayAffinity.argtypes = [HWND, wintypes.DWORD]
    user32.SetWindowDisplayAffinity.restype = wintypes.BOOL

if hasattr(user32, "GetWindowLongPtrW"):
    user32.GetWindowLongPtrW.argtypes = [HWND, ctypes.c_int]
    user32.GetWindowLongPtrW.restype = LONG_PTR
    user32.SetWindowLongPtrW.argtypes = [HWND, ctypes.c_int, LONG_PTR]
    user32.SetWindowLongPtrW.restype = LONG_PTR
else:
    user32.GetWindowLongW.argtypes = [HWND, ctypes.c_int]
    user32.GetWindowLongW.restype = ctypes.c_long
    user32.SetWindowLongW.argtypes = [HWND, ctypes.c_int, ctypes.c_long]
    user32.SetWindowLongW.restype = ctypes.c_long


def set_click_through(hwnd: int, enabled: bool) -> None:
    get_window_long = getattr(user32, "GetWindowLongPtrW", user32.GetWindowLongW)
    set_window_long = getattr(user32, "SetWindowLongPtrW", user32.SetWindowLongW)
    style = get_window_long(hwnd, GWL_EXSTYLE)
    style |= WS_EX_TOOLWINDOW | WS_EX_TOPMOST
    if enabled:
        style |= WS_EX_TRANSPARENT | WS_EX_NOACTIVATE
    else:
        style &= ~WS_EX_TRANSPARENT
        style &= ~WS_EX_NOACTIVATE
    set_window_long(hwnd, GWL_EXSTYLE, style)
    user32.SetWindowPos(
        hwnd,
        None,
        0,
        0,
        0,
        0,
        SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED,
    )


def set_exclude_from_capture(hwnd: int, enabled: bool) -> None:
    if not hwnd or not hasattr(user32, "SetWindowDisplayAffinity"):
        return
    affinity = WDA_EXCLUDEFROMCAPTURE if enabled else WDA_NONE
    user32.SetWindowDisplayAffinity(HWND(hwnd), affinity)


def signed_hiword(value: int) -> int:
    high = (value >> 16) & 0xFFFF
    return high - 0x10000 if high & 0x8000 else high


def monitor_info_from_point(x: int, y: int) -> MONITORINFOEXW | None:
    monitor = user32.MonitorFromPoint(POINT(x, y), MONITOR_DEFAULTTONEAREST)
    if not monitor:
        return None
    info = MONITORINFOEXW()
    info.cbSize = ctypes.sizeof(MONITORINFOEXW)
    if not user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
        return None
    return info


def display_monitor_infos() -> list[MONITORINFOEXW]:
    infos: list[MONITORINFOEXW] = []

    def _callback(monitor, _dc, _rect, _data) -> bool:
        info = MONITORINFOEXW()
        info.cbSize = ctypes.sizeof(MONITORINFOEXW)
        if user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
            infos.append(info)
        return True

    callback = MonitorEnumProc(_callback)
    if not user32.EnumDisplayMonitors(None, None, callback, 0):
        raise OSError("EnumDisplayMonitors failed")
    if not infos:
        raise OSError("EnumDisplayMonitors returned no monitors")
    return infos


def cursor_pos() -> POINT:
    point = POINT()
    if not user32.GetCursorPos(ctypes.byref(point)):
        raise OSError("GetCursorPos failed")
    return point


def virtual_desktop_rect() -> tuple[int, int, int, int]:
    """(left, top, right, bottom) of the union of all monitors, in virtual-
    screen coordinates - the same coordinate system GetCursorPos uses. The
    primary monitor's own top-left is always (0, 0) in this system, so other
    monitors can have negative coordinates.
    """
    left = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
    top = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
    width = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
    height = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
    return left, top, left + width, top + height


def mag_initialize() -> bool:
    return bool(magnification.MagInitialize())


def mag_uninitialize() -> bool:
    return bool(magnification.MagUninitialize())


def mag_set_fullscreen_transform(scale: float, x_offset: int, y_offset: int) -> bool:
    return bool(magnification.MagSetFullscreenTransform(ctypes.c_float(scale), x_offset, y_offset))


def foreground_window_rect() -> tuple[int, RECT]:
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        raise OSError("GetForegroundWindow failed")
    rect = RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        raise OSError("GetWindowRect failed")
    return int(hwnd), rect


def window_from_point(x: int, y: int) -> int:
    return int(user32.WindowFromPoint(POINT(x, y)) or 0)


def register_window_message(name: str) -> int:
    return int(user32.RegisterWindowMessageW(name))


def mouse_button_down(vk_code: int) -> bool:
    return bool(user32.GetAsyncKeyState(vk_code) & 0x8000)


def foreground_process_id() -> int:
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return 0
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return int(pid.value)


def process_image_name(pid: int) -> str | None:
    if not pid:
        return None
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return None
    try:
        buffer = ctypes.create_unicode_buffer(260)
        size = wintypes.DWORD(len(buffer))
        if not kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            return None
        return buffer.value
    finally:
        kernel32.CloseHandle(handle)
