import json

import pytest

from kiro_click.settings import Settings


def test_load_and_resolve_settings(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"confidence_threshold": 0.9}), encoding="utf-8")
    settings = Settings.load(path)
    assert settings.confidence_threshold == 0.9
    assert settings.scan_interval_seconds == 0.5
    assert settings.show_status_window is True
    assert settings.monitor_kiro_in_background is True


def test_rejects_invalid_threshold(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"confidence_threshold": 1.1}), encoding="utf-8")
    with pytest.raises(ValueError, match="confidence_threshold"):
        Settings.load(path)


def test_rejects_unknown_options(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"mystery": True}), encoding="utf-8")
    with pytest.raises(ValueError, match="Unknown config"):
        Settings.load(path)
