from pathlib import Path

import cv2
import numpy as np

from kiro_click.vision import TemplateMatcher


def test_finds_exact_template(tmp_path: Path):
    template = np.zeros((24, 60, 3), dtype=np.uint8)
    template[:] = (210, 210, 210)
    cv2.rectangle(template, (0, 0), (59, 23), (255, 255, 255), 2)
    cv2.putText(template, "Run", (13, 17), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (20, 20, 20), 1)
    cv2.imwrite(str(tmp_path / "run_button.png"), template)

    frame = np.full((150, 240, 3), 35, dtype=np.uint8)
    frame[70:94, 120:180] = template

    matcher = TemplateMatcher(tmp_path, (1.0,))
    assert matcher.reload() == 1
    result = matcher.find_best(frame)
    assert result is not None
    assert result.confidence > 0.99
    assert (result.left, result.top, result.width, result.height) == (120, 70, 60, 24)


def test_empty_template_folder_returns_no_match(tmp_path: Path):
    matcher = TemplateMatcher(tmp_path, (1.0,))
    assert matcher.reload() == 0
    assert matcher.find_best(np.zeros((50, 50, 3), dtype=np.uint8)) is None


def test_auto_crops_run_button_from_full_screenshot(tmp_path: Path):
    screenshot = np.full((190, 650), 30, dtype=np.uint8)
    cv2.rectangle(screenshot, (505, 20), (555, 48), 100, -1)
    cv2.rectangle(screenshot, (568, 20), (611, 48), 190, -1)
    cv2.putText(screenshot, "Run", (576, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.45, 20, 1)
    cv2.imwrite(str(tmp_path / "run_button.png"), screenshot)

    matcher = TemplateMatcher(tmp_path, (1.0,))
    assert matcher.reload() == 1
    loaded = matcher.templates[0].gray
    assert loaded.shape[1] < 60
    assert loaded.shape[0] < 40
