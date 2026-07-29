from __future__ import annotations

import ctypes
from ctypes import wintypes

kernel32 = ctypes.windll.kernel32

ERROR_ALREADY_EXISTS = 183

kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.CreateMutexW.restype = wintypes.HANDLE
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL
kernel32.GetLastError.argtypes = []
kernel32.GetLastError.restype = wintypes.DWORD


class SingleInstanceLock:
    def __init__(self, name: str = "Local\\ScreenAssistant") -> None:
        self.name = name
        self._handle: int | None = None

    def acquire(self) -> bool:
        if self._handle:
            return True
        handle = kernel32.CreateMutexW(None, False, self.name)
        if not handle:
            raise OSError("CreateMutexW failed")
        self._handle = int(handle)
        return kernel32.GetLastError() != ERROR_ALREADY_EXISTS

    def release(self) -> None:
        if not self._handle:
            return
        kernel32.CloseHandle(self._handle)
        self._handle = None

    def __enter__(self) -> "SingleInstanceLock":
        self.acquire()
        return self

    def __exit__(self, *_exc_info) -> None:
        self.release()
