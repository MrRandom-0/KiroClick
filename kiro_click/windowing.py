from __future__ import annotations

import ctypes
import platform
from ctypes import wintypes
from typing import Optional

import pyautogui

from .models import Rect, WindowInfo


def enable_dpi_awareness() -> None:
    """Align capture and input coordinates on high-DPI Windows displays."""
    if platform.system() != "Windows":
        return
    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except (AttributeError, OSError):
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except (AttributeError, OSError):
            ctypes.windll.user32.SetProcessDPIAware()


def _active_window_windows() -> Optional[WindowInfo]:
    user32 = ctypes.windll.user32
    user32.GetForegroundWindow.restype = wintypes.HWND
    hwnd = user32.GetForegroundWindow()
    if not hwnd or user32.IsIconic(hwnd):
        return None

    title_length = user32.GetWindowTextLengthW(hwnd)
    title_buffer = ctypes.create_unicode_buffer(title_length + 1)
    user32.GetWindowTextW(hwnd, title_buffer, title_length + 1)

    rect = wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return None
    bounds = Rect(rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top)
    return WindowInfo(title=title_buffer.value, bounds=bounds) if bounds.is_valid() else None


def _active_window_macos() -> Optional[WindowInfo]:
    try:
        from AppKit import NSWorkspace
        from Quartz import (
            CGWindowListCopyWindowInfo,
            kCGNullWindowID,
            kCGWindowListExcludeDesktopElements,
            kCGWindowListOptionOnScreenOnly,
        )
    except ImportError:
        return None

    app = NSWorkspace.sharedWorkspace().frontmostApplication()
    if app is None:
        return None
    pid = app.processIdentifier()
    app_name = app.localizedName() or ""
    options = kCGWindowListOptionOnScreenOnly | kCGWindowListExcludeDesktopElements
    windows = CGWindowListCopyWindowInfo(options, kCGNullWindowID) or []

    candidates: list[WindowInfo] = []
    for item in windows:
        if int(item.get("kCGWindowOwnerPID", -1)) != pid:
            continue
        if int(item.get("kCGWindowLayer", 0)) != 0:
            continue
        raw = item.get("kCGWindowBounds", {})
        try:
            bounds = Rect(
                int(round(raw["X"])),
                int(round(raw["Y"])),
                int(round(raw["Width"])),
                int(round(raw["Height"])),
            )
        except (KeyError, TypeError, ValueError):
            continue
        if bounds.is_valid():
            window_name = item.get("kCGWindowName", "") or ""
            title = f"{app_name} {window_name}".strip()
            candidates.append(WindowInfo(title=title, bounds=bounds))

    return max(candidates, key=lambda window: window.bounds.width * window.bounds.height, default=None)


def active_window() -> Optional[WindowInfo]:
    system = platform.system()
    if system == "Windows":
        return _active_window_windows()
    if system == "Darwin":
        return _active_window_macos()

    # Best-effort fallback for development on other desktop systems.
    try:
        window = pyautogui.getActiveWindow()
        if window is None:
            return None
        bounds = Rect(int(window.left), int(window.top), int(window.width), int(window.height))
        return WindowInfo(str(window.title), bounds) if bounds.is_valid() else None
    except Exception:
        return None


def primary_screen_rect() -> Rect:
    size = pyautogui.size()
    return Rect(0, 0, int(size.width), int(size.height))


def title_matches(title: str, keywords: tuple[str, ...]) -> bool:
    normalized = title.casefold()
    return any(keyword.casefold() in normalized for keyword in keywords)
