from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import replace
from pathlib import Path


def application_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Automatically click Kiro IDE Run buttons.")
    parser.add_argument("--config", type=Path, help="Path to config.json")
    parser.add_argument("--no-tray", action="store_true", help="Use console status only")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report matches without clicking (overrides the dry_run config option)",
    )
    return parser.parse_args()


def main() -> int:
    # DPI awareness must be enabled before desktop coordinates are queried.
    from kiro_click.windowing import enable_dpi_awareness

    enable_dpi_awareness()
    args = parse_args()
    base_dir = application_dir()
    config_path = args.config.resolve() if args.config else base_dir / "config.json"

    from kiro_click.controller import AutoClickController
    from kiro_click.settings import Settings

    try:
        settings = Settings.load(config_path)
    except (OSError, ValueError) as error:
        print(f"Configuration error: {error}", file=sys.stderr)
        return 2
    if args.dry_run and not settings.dry_run:
        settings = replace(settings, dry_run=True)

    logging.basicConfig(
        level=logging.DEBUG if settings.debug else logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
    )
    try:
        AutoClickController(settings, base_dir, no_tray=args.no_tray).run()
    except Exception:
        logging.exception("KiroClick could not start")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

