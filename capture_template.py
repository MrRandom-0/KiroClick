from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import cv2

from kiro_click.capture import grab_region
from kiro_click.windowing import active_window, enable_dpi_awareness, primary_screen_rect, title_matches


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Crop a Kiro Run button reference image.")
    parser.add_argument("--output", default="run_button.png", help="Output filename inside templates/")
    parser.add_argument("--delay", type=int, default=5, help="Seconds allowed to switch to Kiro")
    parser.add_argument("--screen", action="store_true", help="Capture the primary screen instead of Kiro window")
    return parser.parse_args()


def main() -> int:
    enable_dpi_awareness()
    args = parse_args()
    output_name = Path(args.output).name
    if Path(output_name).suffix.casefold() not in {".png", ".jpg", ".jpeg"}:
        print("Output must end in .png, .jpg, or .jpeg", file=sys.stderr)
        return 2

    print("Make the Run / Run Task button visible, then switch to Kiro.")
    for remaining in range(max(0, args.delay), 0, -1):
        print(f"Capturing in {remaining}...", flush=True)
        time.sleep(1)

    window = active_window()
    if not args.screen and window is not None and title_matches(window.title, ("kiro",)):
        region = window.bounds
        print(f"Captured foreground Kiro window: {window.title}")
    else:
        region = primary_screen_rect()
        if not args.screen:
            print("Kiro was not foreground; captured the primary screen instead.")

    frame = grab_region(region)
    instructions = "Drag tightly around the Run button, then press ENTER (ESC cancels)"
    x, y, width, height = cv2.selectROI(instructions, frame.image_bgr, showCrosshair=True, fromCenter=False)
    cv2.destroyAllWindows()
    if width <= 0 or height <= 0:
        print("Selection cancelled; no file was written.")
        return 1

    crop = frame.image_bgr[y : y + height, x : x + width]
    output_dir = Path(__file__).resolve().parent / "templates"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / output_name
    if not cv2.imwrite(str(output_path), crop):
        print(f"Could not save {output_path}", file=sys.stderr)
        return 1
    print(f"Saved template: {output_path}")
    print("Tip: capture both run_button.png and run_task_button.png if Kiro shows both labels.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

