from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
from PIL import ImageGrab

from .models import Rect


@dataclass(frozen=True)
class CapturedFrame:
    image_bgr: np.ndarray
    logical_region: Rect

    def image_to_screen(self, image_x: float, image_y: float) -> tuple[int, int]:
        """Map image pixels to OS input coordinates (also handles macOS Retina)."""
        image_height, image_width = self.image_bgr.shape[:2]
        scale_x = self.logical_region.width / image_width
        scale_y = self.logical_region.height / image_height
        return (
            int(round(self.logical_region.left + image_x * scale_x)),
            int(round(self.logical_region.top + image_y * scale_y)),
        )


def grab_region(region: Rect) -> CapturedFrame:
    if not region.is_valid():
        raise ValueError(f"Cannot capture invalid region: {region}")
    image = ImageGrab.grab(
        bbox=(region.left, region.top, region.right, region.bottom),
        all_screens=True,
    )
    rgb = np.asarray(image.convert("RGB"))
    return CapturedFrame(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), region)

