from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Rect:
    left: int
    top: int
    width: int
    height: int

    @property
    def right(self) -> int:
        return self.left + self.width

    @property
    def bottom(self) -> int:
        return self.top + self.height

    def is_valid(self) -> bool:
        return self.width > 0 and self.height > 0


@dataclass(frozen=True)
class WindowInfo:
    title: str
    bounds: Rect


@dataclass(frozen=True)
class Match:
    template_name: str
    confidence: float
    left: int
    top: int
    width: int
    height: int

    @property
    def center(self) -> tuple[float, float]:
        return (self.left + self.width / 2, self.top + self.height / 2)


@dataclass(frozen=True)
class ControllerSnapshot:
    active: bool
    template_count: int
    status_detail: str
    click_count: int
    last_click_text: str
    hotkey: str
    stopping: bool
    dry_run: bool = False
    recent_events: tuple[str, ...] = ()
