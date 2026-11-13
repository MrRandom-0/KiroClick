from datetime import datetime

import pytest

from kiro_click.history import ClickEvent, ClickHistory


def make_event(name="run_button.png", confidence=0.91, **kwargs):
    return ClickEvent(
        when=datetime(2026, 1, 2, 15, 4, 5),
        template_name=name,
        confidence=confidence,
        x=120,
        y=80,
        **kwargs,
    )


def test_counts_clicks_and_dry_runs_separately():
    history = ClickHistory()
    history.record(make_event())
    history.record(make_event(dry_run=True))
    history.record(make_event(background=True))
    assert history.total == 3
    assert history.clicks == 2
    assert history.would_clicks == 1


def test_latest_and_recent_order():
    history = ClickHistory()
    assert history.latest() is None
    assert history.recent() == ()
    first = make_event(name="first.png")
    second = make_event(name="second.png")
    history.record(first)
    history.record(second)
    assert history.latest() is second
    assert history.recent() == (second, first)
    assert history.recent(1) == (second,)


def test_history_is_bounded():
    history = ClickHistory(capacity=2)
    for index in range(4):
        history.record(make_event(name=f"t{index}.png"))
    assert history.total == 2
    assert history.latest().template_name == "t3.png"
    with pytest.raises(ValueError, match="capacity"):
        ClickHistory(capacity=0)


def test_describe_marks_dry_run_and_background():
    plain = make_event().describe()
    assert "run_button.png" in plain
    assert "91%" in plain
    assert "dry run" not in plain
    dry = make_event(dry_run=True).describe()
    assert "dry run — not clicked" in dry
    background = make_event(background=True).describe()
    assert background.endswith("background")
