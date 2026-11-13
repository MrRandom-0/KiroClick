from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ClickEvent:
    """One detected button: either a click that was sent or a dry-run match."""

    when: datetime
    template_name: str
    confidence: float
    x: int
    y: int
    dry_run: bool = False
    background: bool = False

    def describe(self) -> str:
        text = (
            f"{self.template_name}  •  {self.confidence:.0%}  •  "
            f"{self.when.strftime('%I:%M:%S %p')}"
        )
        if self.dry_run:
            text += "  •  dry run — not clicked"
        if self.background:
            text += "  •  background"
        return text


class ClickHistory:
    """Bounded in-memory record of recent click activity for one session."""

    def __init__(self, capacity: int = 50) -> None:
        if capacity < 1:
            raise ValueError("capacity must be at least 1")
        self._events: deque[ClickEvent] = deque(maxlen=capacity)

    def record(self, event: ClickEvent) -> None:
        self._events.append(event)

    @property
    def total(self) -> int:
        return len(self._events)

    @property
    def clicks(self) -> int:
        """Clicks actually sent (dry-run matches are not clicks)."""
        return sum(1 for event in self._events if not event.dry_run)

    @property
    def would_clicks(self) -> int:
        """Dry-run matches that would have been clicked."""
        return sum(1 for event in self._events if event.dry_run)

    def latest(self) -> ClickEvent | None:
        return self._events[-1] if self._events else None

    def recent(self, limit: int = 5) -> tuple[ClickEvent, ...]:
        """Most recent events first."""
        return tuple(reversed(self._events))[:limit]
