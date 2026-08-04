from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from .models import Match

LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class Template:
    name: str
    gray: np.ndarray


class TemplateMatcher:
    def __init__(self, templates_dir: Path, scales: tuple[float, ...]) -> None:
        self.templates_dir = templates_dir
        self.scales = scales
        self.templates: list[Template] = []

    def reload(self) -> int:
        self.templates.clear()
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        paths = sorted(
            path
            for path in self.templates_dir.iterdir()
            if path.is_file() and path.suffix.casefold() in {".png", ".jpg", ".jpeg"}
        )
        for path in paths:
            raw = np.fromfile(path, dtype=np.uint8)
            image = cv2.imdecode(raw, cv2.IMREAD_GRAYSCALE)
            if image is None or min(image.shape[:2]) < 5:
                LOG.warning("Ignoring unreadable or tiny template: %s", path.name)
                continue
            self.templates.append(Template(path.name, self._prepare_template(path.name, image)))
        LOG.info("Loaded %d button template(s) from %s", len(self.templates), self.templates_dir)
        return len(self.templates)

    @staticmethod
    def _prepare_template(name: str, image: np.ndarray) -> np.ndarray:
        """Accept a full screenshot and isolate its rightmost bright Run button."""
        height, width = image.shape[:2]
        if width <= 200 and height <= 100:
            return image

        _, bright = cv2.threshold(image, 130, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(bright, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        candidates: list[tuple[int, int, int, int]] = []
        for contour in contours:
            x, y, box_width, box_height = cv2.boundingRect(contour)
            if (
                30 <= box_width <= 180
                and 18 <= box_height <= 70
                and y < height * 0.7
                and cv2.contourArea(contour) >= 200
            ):
                candidates.append((x, y, box_width, box_height))
        if not candidates:
            LOG.warning(
                "%s looks like a full screenshot and no button could be isolated; crop it more tightly",
                name,
            )
            return image

        x, y, box_width, box_height = max(candidates, key=lambda box: box[0])
        padding = 2
        x1, y1 = max(0, x - padding), max(0, y - padding)
        x2, y2 = min(width, x + box_width + padding), min(height, y + box_height + padding)
        cropped = image[y1:y2, x1:x2]
        LOG.info(
            "Auto-cropped %s from full screenshot (%dx%d -> %dx%d)",
            name,
            width,
            height,
            cropped.shape[1],
            cropped.shape[0],
        )
        return cropped

    def find_best(self, image_bgr: np.ndarray) -> Match | None:
        if not self.templates or image_bgr.size == 0:
            return None
        frame_gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        frame_height, frame_width = frame_gray.shape[:2]
        best: Match | None = None

        for template in self.templates:
            for scale in self.scales:
                if scale == 1.0:
                    candidate = template.gray
                else:
                    interpolation = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_CUBIC
                    candidate = cv2.resize(template.gray, None, fx=scale, fy=scale, interpolation=interpolation)
                height, width = candidate.shape[:2]
                if width > frame_width or height > frame_height or min(width, height) < 5:
                    continue
                result = cv2.matchTemplate(frame_gray, candidate, cv2.TM_CCOEFF_NORMED)
                _, confidence, _, location = cv2.minMaxLoc(result)
                match = Match(template.name, float(confidence), location[0], location[1], width, height)
                if best is None or match.confidence > best.confidence:
                    best = match
        return best
