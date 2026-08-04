from __future__ import annotations

import ctypes
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .models import Match
from .vision import TemplateMatcher


@dataclass(frozen=True)
class BackgroundMatch:
    hwnd: int
    title: str
    match: Match


class WindowsBackgroundScanner:
    """Capture and click Kiro without requiring it to be the foreground window."""

    def __init__(self) -> None:
        import win32api
        import win32con
        import win32gui
        import win32ui

        self.win32api = win32api
        self.win32con = win32con
        self.win32gui = win32gui
        self.win32ui = win32ui

    @staticmethod
    def _process_name(hwnd: int) -> str:
        from ctypes import wintypes

        process_id = wintypes.DWORD()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
        process = ctypes.windll.kernel32.OpenProcess(0x1000, False, process_id.value)
        if not process:
            return ""
        try:
            size = wintypes.DWORD(32768)
            buffer = ctypes.create_unicode_buffer(size.value)
            if not ctypes.windll.kernel32.QueryFullProcessImageNameW(
                process, 0, buffer, ctypes.byref(size)
            ):
                return ""
            return Path(buffer.value).name.casefold()
        finally:
            ctypes.windll.kernel32.CloseHandle(process)

    def _kiro_windows(self) -> list[tuple[int, str]]:
        found: list[tuple[int, str]] = []

        def collect(hwnd: int, _extra: object) -> None:
            if not self.win32gui.IsWindow(hwnd) or not self.win32gui.IsWindowVisible(hwnd):
                return
            if self._process_name(hwnd) != "kiro.exe":
                return
            title = self.win32gui.GetWindowText(hwnd).strip()
            if title:
                found.append((hwnd, title))

        self.win32gui.EnumWindows(collect, None)
        return found

    def _capture(self, hwnd: int) -> np.ndarray | None:
        left, top, right, bottom = self.win32gui.GetWindowRect(hwnd)
        width, height = right - left, bottom - top
        if width < 100 or height < 100:
            return None

        window_dc = self.win32gui.GetWindowDC(hwnd)
        source_dc = self.win32ui.CreateDCFromHandle(window_dc)
        memory_dc = source_dc.CreateCompatibleDC()
        bitmap = self.win32ui.CreateBitmap()
        try:
            bitmap.CreateCompatibleBitmap(source_dc, width, height)
            memory_dc.SelectObject(bitmap)
            rendered = ctypes.windll.user32.PrintWindow(hwnd, memory_dc.GetSafeHdc(), 2)
            if not rendered:
                return None
            pixels = bitmap.GetBitmapBits(True)
            image = np.frombuffer(pixels, dtype=np.uint8).reshape((height, width, 4))[:, :, :3]
            if float(image.std()) < 1.0:
                return None
            return image.copy()
        finally:
            self.win32gui.DeleteObject(bitmap.GetHandle())
            memory_dc.DeleteDC()
            source_dc.DeleteDC()
            self.win32gui.ReleaseDC(hwnd, window_dc)

    def find_best(self, matcher: TemplateMatcher) -> BackgroundMatch | None:
        best: BackgroundMatch | None = None
        for hwnd, title in self._kiro_windows():
            image = self._capture(hwnd)
            if image is None:
                continue
            match = matcher.find_best(image)
            if match is None:
                continue
            candidate = BackgroundMatch(hwnd, title, match)
            if best is None or candidate.match.confidence > best.match.confidence:
                best = candidate
        return best

    def click(self, result: BackgroundMatch) -> None:
        match_x, match_y = result.match.center
        left, top, _right, _bottom = self.win32gui.GetWindowRect(result.hwnd)
        screen_point = (int(round(left + match_x)), int(round(top + match_y)))

        target = result.hwnd
        children: list[int] = []
        self.win32gui.EnumChildWindows(result.hwnd, lambda hwnd, _extra: children.append(hwnd), None)
        for child in children:
            if self.win32gui.GetClassName(child) == "Chrome_RenderWidgetHostHWND":
                target = child
                break

        client_x, client_y = self.win32gui.ScreenToClient(target, screen_point)
        message_position = self.win32api.MAKELONG(client_x, client_y)
        self.win32gui.PostMessage(target, self.win32con.WM_MOUSEMOVE, 0, message_position)
        self.win32gui.PostMessage(
            target, self.win32con.WM_LBUTTONDOWN, self.win32con.MK_LBUTTON, message_position
        )
        self.win32gui.PostMessage(target, self.win32con.WM_LBUTTONUP, 0, message_position)

