from __future__ import annotations

import ctypes
from datetime import datetime
from ctypes import wintypes

from PySide6.QtGui import QGuiApplication, QImage

from capture.models import CaptureRequest, CaptureResult
from utils.winapi import gdi32, user32


SRCCOPY = 0x00CC0020
CAPTUREBLT = 0x40000000
DIB_RGB_COLORS = 0
BI_RGB = 0


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class RGBQUAD(ctypes.Structure):
    _fields_ = [
        ("rgbBlue", ctypes.c_ubyte),
        ("rgbGreen", ctypes.c_ubyte),
        ("rgbRed", ctypes.c_ubyte),
        ("rgbReserved", ctypes.c_ubyte),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", RGBQUAD * 1)]


gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
gdi32.CreateCompatibleDC.restype = wintypes.HDC
gdi32.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
gdi32.CreateCompatibleBitmap.restype = wintypes.HBITMAP
gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
gdi32.SelectObject.restype = wintypes.HGDIOBJ
gdi32.BitBlt.argtypes = [
    wintypes.HDC,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.HDC,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.DWORD,
]
gdi32.BitBlt.restype = wintypes.BOOL
gdi32.GetDIBits.argtypes = [
    wintypes.HDC,
    wintypes.HBITMAP,
    wintypes.UINT,
    wintypes.UINT,
    ctypes.c_void_p,
    ctypes.POINTER(BITMAPINFO),
    wintypes.UINT,
]
gdi32.GetDIBits.restype = ctypes.c_int
gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
gdi32.DeleteObject.restype = wintypes.BOOL
gdi32.DeleteDC.argtypes = [wintypes.HDC]
gdi32.DeleteDC.restype = wintypes.BOOL
user32.GetDC.argtypes = [wintypes.HWND]
user32.GetDC.restype = wintypes.HDC
user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
user32.ReleaseDC.restype = ctypes.c_int


class GdiCaptureBackend:
    def capture_region(self, request: CaptureRequest) -> CaptureResult:
        rect = request.rect.normalized()
        width = rect.width()
        height = rect.height()
        if width <= 0 or height <= 0:
            raise ValueError(f"Invalid capture region: {rect}")

        screen_dc = user32.GetDC(None)
        memory_dc = gdi32.CreateCompatibleDC(screen_dc)
        bitmap = gdi32.CreateCompatibleBitmap(screen_dc, width, height)
        old_object = gdi32.SelectObject(memory_dc, bitmap)
        try:
            ok = gdi32.BitBlt(
                memory_dc,
                0,
                0,
                width,
                height,
                screen_dc,
                rect.left(),
                rect.top(),
                SRCCOPY | CAPTUREBLT,
            )
            if not ok:
                image = self._fallback_grab_window(rect)
                return CaptureResult(
                    capture_type=request.capture_type,
                    image=image,
                    virtual_rect=rect,
                    width=width,
                    height=height,
                    dpi_x=96,
                    dpi_y=96,
                    captured_at=datetime.now(),
                    includes_annotations=False,
                    includes_cursor=request.include_cursor,
                )
            try:
                image = self._bitmap_to_qimage(memory_dc, bitmap, width, height)
            except Exception:
                image = self._fallback_grab_window(rect)
            return CaptureResult(
                capture_type=request.capture_type,
                image=image,
                virtual_rect=rect,
                width=width,
                height=height,
                dpi_x=96,
                dpi_y=96,
                captured_at=datetime.now(),
                includes_annotations=False,
                includes_cursor=request.include_cursor,
            )
        finally:
            if old_object:
                gdi32.SelectObject(memory_dc, old_object)
            if bitmap:
                gdi32.DeleteObject(bitmap)
            if memory_dc:
                gdi32.DeleteDC(memory_dc)
            if screen_dc:
                user32.ReleaseDC(None, screen_dc)

    def _bitmap_to_qimage(self, dc, bitmap, width: int, height: int) -> QImage:
        info = BITMAPINFO()
        info.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        info.bmiHeader.biWidth = width
        info.bmiHeader.biHeight = -height
        info.bmiHeader.biPlanes = 1
        info.bmiHeader.biBitCount = 32
        info.bmiHeader.biCompression = BI_RGB
        byte_count = width * height * 4
        buffer = (ctypes.c_ubyte * byte_count)()
        scan_lines = gdi32.GetDIBits(
            dc,
            bitmap,
            0,
            height,
            ctypes.byref(buffer),
            ctypes.byref(info),
            DIB_RGB_COLORS,
        )
        if scan_lines != height:
            raise OSError("GetDIBits failed")
        image_format = getattr(QImage.Format, "Format_BGRX8888", QImage.Format.Format_RGB32)
        return QImage(bytes(buffer), width, height, width * 4, image_format).copy()

    def _fallback_grab_window(self, rect) -> QImage:
        screen = QGuiApplication.screenAt(rect.center()) or QGuiApplication.primaryScreen()
        if screen is None:
            raise OSError("BitBlt failed and no Qt screen fallback is available")
        geometry = screen.geometry()
        local_x = rect.left() - geometry.left()
        local_y = rect.top() - geometry.top()
        pixmap = screen.grabWindow(0, local_x, local_y, rect.width(), rect.height())
        image = pixmap.toImage()
        if image.isNull():
            raise OSError("BitBlt failed and Qt screen fallback returned a null image")
        return image
