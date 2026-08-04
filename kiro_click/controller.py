from __future__ import annotations

import logging
import os
import platform
import subprocess
import threading
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import pyautogui
import pystray
from PIL import Image, ImageDraw
from pynput import keyboard, mouse

from .capture import grab_region
from .models import ControllerSnapshot
from .settings import Settings
from .vision import TemplateMatcher
from .windowing import active_window, primary_screen_rect, title_matches

LOG = logging.getLogger(__name__)


class AutoClickController:
    def __init__(self, settings: Settings, base_dir: Path, no_tray: bool = False) -> None:
        self.settings = settings
        self.base_dir = base_dir
        self.no_tray = no_tray
        self.templates_dir = (base_dir / settings.templates_dir).resolve()
        self.matcher = TemplateMatcher(self.templates_dir, settings.template_scales)
        self._background_scanner = None
        if settings.monitor_kiro_in_background and platform.system() == "Windows":
            from .background_windows import WindowsBackgroundScanner

            self._background_scanner = WindowsBackgroundScanner()

        self._active = settings.start_active
        self._state_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._worker: threading.Thread | None = None
        self._hotkeys: keyboard.GlobalHotKeys | None = None
        self._mouse_listener: mouse.Listener | None = None
        self._tray: pystray.Icon | None = None
        self._last_click_time = 0.0
        self._armed = True
        self._consecutive_misses = 0
        self._template_count = 0
        self._status_detail = "Starting"
        self._click_count = 0
        self._last_click_text = "No clicks yet"
        self._show_window_handler: Callable[[], None] | None = None

        pyautogui.PAUSE = 0
        pyautogui.FAILSAFE = True

    @property
    def active(self) -> bool:
        with self._state_lock:
            return self._active

    def status_text(self) -> str:
        if self._stop_event.is_set():
            return "Stopped"
        with self._state_lock:
            template_count = self._template_count
            active = self._active
        if template_count == 0:
            return "Needs a button template"
        return "Active" if active else "Paused"

    def snapshot(self) -> ControllerSnapshot:
        with self._state_lock:
            return ControllerSnapshot(
                active=self._active,
                template_count=self._template_count,
                status_detail=self._status_detail,
                click_count=self._click_count,
                last_click_text=self._last_click_text,
                hotkey=self.settings.resolved_hotkey(),
                stopping=self._stop_event.is_set(),
            )

    def _set_status_detail(self, value: str) -> None:
        with self._state_lock:
            if value == self._status_detail:
                return
            self._status_detail = value
        LOG.debug("State: %s", value)

    def toggle(self) -> None:
        with self._state_lock:
            self._active = not self._active
            active = self._active
        self._armed = True
        self._consecutive_misses = 0
        LOG.info("KiroClick is now %s", "ACTIVE" if active else "PAUSED")
        self._refresh_tray()

    def reload_templates(self) -> None:
        template_count = self.matcher.reload()
        with self._state_lock:
            self._template_count = template_count
            self._status_detail = (
                f"Loaded {template_count} button template(s)"
                if template_count
                else "No button template found"
            )
        self._armed = True
        self._consecutive_misses = 0
        self._refresh_tray()

    def request_stop(self, reason: str = "Quit requested") -> None:
        if self._stop_event.is_set():
            return
        LOG.warning("Stopping: %s", reason)
        self._stop_event.set()
        tray = self._tray
        if tray is not None:
            try:
                tray.stop()
            except Exception:
                pass

    def _is_corner(self, x: float, y: float) -> bool:
        screen = primary_screen_rect()
        threshold = self.settings.corner_threshold_pixels
        near_left = x <= screen.left + threshold
        near_right = x >= screen.right - 1 - threshold
        near_top = y <= screen.top + threshold
        near_bottom = y >= screen.bottom - 1 - threshold
        return (near_left or near_right) and (near_top or near_bottom)

    def _on_mouse_move(self, x: float, y: float) -> bool | None:
        if self.settings.corner_failsafe and self._is_corner(x, y):
            self.request_stop("mouse corner fail-safe triggered")
            return False
        return None

    def _scan_once(self) -> None:
        if self._background_scanner is not None:
            self._scan_background_once()
            return

        window = active_window()
        if self.settings.monitor_active_kiro_window:
            if window is None:
                self._set_status_detail("No foreground window")
                return
            if not title_matches(window.title, self.settings.kiro_window_keywords):
                self._set_status_detail(f"Foreground app is not Kiro: {window.title!r}")
                return
            region = window.bounds
        else:
            region = primary_screen_rect()

        frame = grab_region(region)
        match = self.matcher.find_best(frame.image_bgr)
        if match is None or match.confidence < self.settings.confidence_threshold:
            self._consecutive_misses += 1
            if self.settings.require_button_to_disappear and not self._armed:
                if self._consecutive_misses >= self.settings.rearm_after_misses:
                    self._armed = True
                    LOG.debug("Button disappeared; clicker re-armed")
            self._set_status_detail("Watching")
            return

        self._consecutive_misses = 0
        self._set_status_detail(f"Matched {match.template_name}: {match.confidence:.1%}")
        LOG.debug("Matched %s at %.3f", match.template_name, match.confidence)
        if not self._armed:
            return
        elapsed = time.monotonic() - self._last_click_time
        if elapsed < self.settings.cooldown_seconds:
            return

        image_x, image_y = match.center
        click_x, click_y = frame.image_to_screen(image_x, image_y)
        current_window = active_window()
        if self.settings.monitor_active_kiro_window:
            if current_window is None or not title_matches(
                current_window.title, self.settings.kiro_window_keywords
            ):
                LOG.info("Skipped click because Kiro lost foreground focus")
                return
        if self.settings.corner_failsafe:
            current_position = pyautogui.position()
            if self._is_corner(current_position.x, current_position.y):
                self.request_stop("mouse corner fail-safe triggered before click")
                return

        try:
            pyautogui.moveTo(
                click_x,
                click_y,
                duration=self.settings.move_duration_seconds,
                tween=pyautogui.easeOutQuad,
            )
            pyautogui.click(button="left")
        except pyautogui.FailSafeException:
            self.request_stop("PyAutoGUI corner fail-safe triggered")
            return

        self._last_click_time = time.monotonic()
        self._armed = not self.settings.require_button_to_disappear
        with self._state_lock:
            self._click_count += 1
            self._last_click_text = (
                f"{match.template_name}  •  {match.confidence:.0%}  •  "
                f"{datetime.now().strftime('%I:%M:%S %p')}"
            )
            self._status_detail = "Click sent — waiting for Kiro"
        LOG.info(
            "Clicked %s at (%d, %d), confidence %.1f%%",
            match.template_name,
            click_x,
            click_y,
            match.confidence * 100,
        )

    def _scan_background_once(self) -> None:
        result = self._background_scanner.find_best(self.matcher)
        match = result.match if result is not None else None
        if match is None or match.confidence < self.settings.confidence_threshold:
            self._consecutive_misses += 1
            self._set_status_detail("Watching Kiro in background")
            return

        self._consecutive_misses = 0
        self._set_status_detail(f"Found {match.template_name}: {match.confidence:.1%}")
        elapsed = time.monotonic() - self._last_click_time
        if elapsed < self.settings.cooldown_seconds:
            return
        if self.settings.corner_failsafe:
            current_position = pyautogui.position()
            if self._is_corner(current_position.x, current_position.y):
                self.request_stop("mouse corner fail-safe triggered before background click")
                return

        self._background_scanner.click(result)
        self._last_click_time = time.monotonic()
        # If a synthetic click is ignored, retry after the normal cooldown.
        self._armed = True
        with self._state_lock:
            self._click_count += 1
            self._last_click_text = (
                f"{match.template_name} | {match.confidence:.0%} | "
                f"{datetime.now().strftime('%I:%M:%S %p')} | background"
            )
            self._status_detail = "Background click sent to Kiro"
        LOG.info(
            "Background-clicked %s in %s, confidence %.1f%%",
            match.template_name,
            result.title,
            match.confidence * 100,
        )

    def _worker_loop(self) -> None:
        while not self._stop_event.is_set():
            started = time.monotonic()
            if self.active and self._template_count:
                try:
                    self._scan_once()
                except Exception:
                    LOG.exception("Screen scan failed; retrying")
            elapsed = time.monotonic() - started
            wait_for = max(0.01, self.settings.scan_interval_seconds - elapsed)
            self._stop_event.wait(wait_for)

    @staticmethod
    def _tray_image(color: str) -> Image.Image:
        image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((4, 4, 60, 60), radius=14, fill="#24212b", outline="#ffffff", width=3)
        draw.polygon(((22, 16), (22, 48), (48, 32)), fill=color)
        return image

    def _refresh_tray(self) -> None:
        if self._tray is None:
            return
        color = "#36d66b" if self.active and self._template_count else "#f1c84b"
        self._tray.icon = self._tray_image(color)
        try:
            self._tray.update_menu()
        except Exception:
            pass

    def _open_templates(self) -> None:
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        system = platform.system()
        if system == "Windows":
            os.startfile(self.templates_dir)  # type: ignore[attr-defined]
        elif system == "Darwin":
            subprocess.Popen(["open", str(self.templates_dir)])
        else:
            subprocess.Popen(["xdg-open", str(self.templates_dir)])

    def open_templates(self) -> None:
        self._open_templates()

    def set_show_window_handler(self, handler: Callable[[], None]) -> None:
        self._show_window_handler = handler

    def show_status_window(self) -> None:
        if self._show_window_handler is not None:
            self._show_window_handler()

    def _build_tray(self) -> pystray.Icon:
        def status_label(_item: pystray.MenuItem) -> str:
            return f"Status: {self.status_text()}"

        def toggle_label(_item: pystray.MenuItem) -> str:
            return "Pause" if self.active else "Resume"

        menu = pystray.Menu(
            pystray.MenuItem("Show KiroClick", lambda _icon, _item: self.show_status_window(), default=True),
            pystray.MenuItem(status_label, None, enabled=False),
            pystray.MenuItem(toggle_label, lambda _icon, _item: self.toggle()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Reload button templates", lambda _icon, _item: self.reload_templates()),
            pystray.MenuItem("Open templates folder", lambda _icon, _item: self._open_templates()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", lambda _icon, _item: self.request_stop()),
        )
        color = "#36d66b" if self.active and self._template_count else "#f1c84b"
        return pystray.Icon("KiroClick", self._tray_image(color), "KiroClick", menu)

    def run(self) -> None:
        self.reload_templates()
        hotkey = self.settings.resolved_hotkey()
        self._hotkeys = keyboard.GlobalHotKeys({hotkey: self.toggle})
        self._hotkeys.start()
        if self.settings.corner_failsafe:
            self._mouse_listener = mouse.Listener(on_move=self._on_mouse_move)
            self._mouse_listener.start()

        self._worker = threading.Thread(target=self._worker_loop, name="screen-monitor", daemon=True)
        self._worker.start()
        LOG.info("Toggle hotkey: %s", hotkey)
        LOG.info("Corner fail-safe: %s", "enabled" if self.settings.corner_failsafe else "disabled")
        LOG.info("KiroClick is %s", "ACTIVE" if self.active else "PAUSED")

        try:
            if self.no_tray:
                while not self._stop_event.wait(0.5):
                    pass
            elif self.settings.show_status_window:
                from .ui import StatusWindow

                status_window = StatusWindow(self)
                self.set_show_window_handler(status_window.request_show)
                self._tray = self._build_tray()
                try:
                    self._tray.run_detached()
                except Exception:
                    LOG.exception("System tray could not start; continuing with status window")
                    self._tray = None
                status_window.run()
            else:
                self._tray = self._build_tray()
                self._tray.run()
        except KeyboardInterrupt:
            self.request_stop("Ctrl+C")
        finally:
            self._stop_event.set()
            if self._hotkeys is not None:
                self._hotkeys.stop()
            if self._mouse_listener is not None:
                self._mouse_listener.stop()
            if self._worker is not None:
                self._worker.join(timeout=2.0)
            LOG.info("KiroClick stopped")
