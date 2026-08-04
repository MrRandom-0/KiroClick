from __future__ import annotations

import json
import platform
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Settings:
    templates_dir: str = "templates"
    confidence_threshold: float = 0.82
    scan_interval_seconds: float = 0.5
    cooldown_seconds: float = 2.5
    require_button_to_disappear: bool = True
    rearm_after_misses: int = 2
    monitor_kiro_in_background: bool = True
    monitor_active_kiro_window: bool = True
    kiro_window_keywords: tuple[str, ...] = ("kiro",)
    toggle_hotkey: str = "auto"
    start_active: bool = True
    show_status_window: bool = True
    window_always_on_top: bool = True
    move_duration_seconds: float = 0.12
    corner_failsafe: bool = True
    corner_threshold_pixels: int = 4
    template_scales: tuple[float, ...] = (0.9, 1.0, 1.1)
    debug: bool = False

    @classmethod
    def load(cls, path: Path) -> "Settings":
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")
        with path.open("r", encoding="utf-8") as handle:
            raw: dict[str, Any] = json.load(handle)

        allowed = {field.name for field in fields(cls)}
        unknown = sorted(set(raw) - allowed)
        if unknown:
            raise ValueError(f"Unknown config option(s): {', '.join(unknown)}")

        if "kiro_window_keywords" in raw:
            raw["kiro_window_keywords"] = tuple(raw["kiro_window_keywords"])
        if "template_scales" in raw:
            raw["template_scales"] = tuple(float(value) for value in raw["template_scales"])

        settings = cls(**raw)
        settings.validate()
        return settings

    def validate(self) -> None:
        if not 0.0 < self.confidence_threshold <= 1.0:
            raise ValueError("confidence_threshold must be in the range (0, 1]")
        if self.scan_interval_seconds < 0.1:
            raise ValueError("scan_interval_seconds must be at least 0.1")
        if self.cooldown_seconds < 0:
            raise ValueError("cooldown_seconds cannot be negative")
        if self.rearm_after_misses < 1:
            raise ValueError("rearm_after_misses must be at least 1")
        if self.corner_threshold_pixels < 1:
            raise ValueError("corner_threshold_pixels must be at least 1")
        if not self.kiro_window_keywords:
            raise ValueError("kiro_window_keywords cannot be empty")
        if not self.template_scales or any(scale <= 0 for scale in self.template_scales):
            raise ValueError("template_scales must contain positive numbers")

    def resolved_hotkey(self) -> str:
        if self.toggle_hotkey.lower() != "auto":
            return self.toggle_hotkey
        return "<cmd>+<shift>+s" if platform.system() == "Darwin" else "<ctrl>+<shift>+s"
