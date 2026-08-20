#!/usr/bin/env python3
"""Trace PCB-aligned component-side evidence without generating CAD."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from n305_mainboard_reference import (  # noqa: E402
    FAN_CENTER_XY_MM,
    FAN_PROFILE_UNCERTAINTY_MM,
    FAN_SHELL_PROFILE_XY_MM,
    PCB_X_MM,
    PCB_Y_MM,
)
from n305_photo_reference import (  # noqa: E402
    BOARD_01_BLOWER_OUTLINE_PX,
    BOARD_01_CROP_PX,
    BOARD_01_FAN_CENTER_PX,
    BOARD_01_PCB_QUAD_PX,
    BOARD_01_SOURCE,
)


OUT_DIR = ROOT / "previews" / "calibration"
DATA_PATH = ROOT / "docs" / "component-calibration.json"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    filename = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    try:
        return ImageFont.truetype(filename, size)
    except OSError:
        return ImageFont.load_default()


LABEL_FONT = font(22, True)
SMALL_FONT = font(18)


def photo_to_pcb_homography() -> np.ndarray:
    source = np.asarray(BOARD_01_PCB_QUAD_PX, dtype=float)
    target = np.asarray(
        ((-50.0, +52.75), (+50.0, +52.75), (+50.0, -52.75), (-50.0, -52.75)),
        dtype=float,
    )
    rows: list[list[float]] = []
    values: list[float] = []
    for (x_px, y_px), (x_mm, y_mm) in zip(source, target):
        rows.extend(
            (
                [x_px, y_px, 1.0, 0.0, 0.0, 0.0, -x_mm * x_px, -x_mm * y_px],
                [0.0, 0.0, 0.0, x_px, y_px, 1.0, -y_mm * x_px, -y_mm * y_px],
            )
        )
        values.extend((x_mm, y_mm))
    coefficients = np.linalg.solve(np.asarray(rows), np.asarray(values))
    return np.append(coefficients, 1.0).reshape(3, 3)


def transform_point(matrix: np.ndarray, point: tuple[int, int]) -> tuple[float, float]:
    transformed = matrix @ np.asarray((point[0], point[1], 1.0), dtype=float)
    return transformed[0] / transformed[2], transformed[1] / transformed[2]


def draw_label(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str) -> None:
    bounds = draw.textbbox(xy, text, font=LABEL_FONT)
    draw.rectangle(
        (bounds[0] - 5, bounds[1] - 3, bounds[2] + 5, bounds[3] + 3),
        fill=(16, 20, 24),
    )
    draw.text(xy, text, fill=(255, 238, 110), font=LABEL_FONT)


def main() -> None:
    source = ImageOps.exif_transpose(Image.open(ROOT / BOARD_01_SOURCE)).convert("RGB")
    overlay = source.copy()
    draw = ImageDraw.Draw(overlay)

    pcb_points = list(BOARD_01_PCB_QUAD_PX)
    blower_points = list(BOARD_01_BLOWER_OUTLINE_PX)
    draw.line(pcb_points + [pcb_points[0]], fill=(0, 220, 235), width=5, joint="curve")
    draw.line(blower_points + [blower_points[0]], fill=(238, 25, 170), width=7, joint="curve")

    center_x, center_y = BOARD_01_FAN_CENTER_PX
    draw.ellipse(
        (center_x - 14, center_y - 14, center_x + 14, center_y + 14),
        outline=(255, 220, 30),
        width=5,
    )
    draw.line((center_x - 28, center_y, center_x + 28, center_y), fill=(255, 220, 30), width=3)
    draw.line((center_x, center_y - 28, center_x, center_y + 28), fill=(255, 220, 30), width=3)

    crop_x0, crop_y0, crop_x1, crop_y1 = BOARD_01_CROP_PX
    draw_label(draw, (crop_x0 + 20, crop_y0 + 20), "01 PCB-aligned component trace")
    draw_label(draw, (crop_x0 + 20, crop_y0 + 60), "cyan=PCB datum; magenta=blower outline; yellow=fan center")
    draw.text((790, 1420), "04 / -X", fill=(255, 238, 110), font=SMALL_FONT)
    draw.text((2300, 1420), "06 / +X", fill=(255, 238, 110), font=SMALL_FONT)
    draw.text((1510, 930), "07 / +Y", fill=(255, 238, 110), font=SMALL_FONT)
    draw.text((1510, 2600), "05 / -Y", fill=(255, 238, 110), font=SMALL_FONT)

    overlay_path = OUT_DIR / "01-blower-profile-trace.png"
    overlay.crop(BOARD_01_CROP_PX).save(overlay_path)

    matrix = photo_to_pcb_homography()
    converted_profile = [transform_point(matrix, point) for point in BOARD_01_BLOWER_OUTLINE_PX]
    converted_center = transform_point(matrix, BOARD_01_FAN_CENTER_PX)
    point_errors = [
        math.dist(converted, model)
        for converted, model in zip(converted_profile, FAN_SHELL_PROFILE_XY_MM)
    ]
    data = {
        "status": "component-side photo evidence converted to PCB coordinates; no CAD generated",
        "source": BOARD_01_SOURCE,
        "source_resolution_px": list(source.size),
        "coordinate_frame": "+X=06, -X=04, +Y=07, -Y=05",
        "pcb_quad_px": [list(point) for point in BOARD_01_PCB_QUAD_PX],
        "blower_outline_px": [list(point) for point in BOARD_01_BLOWER_OUTLINE_PX],
        "blower_outline_xy_mm": [
            [round(x_mm, 3), round(y_mm, 3)] for x_mm, y_mm in converted_profile
        ],
        "fan_center_px": list(BOARD_01_FAN_CENTER_PX),
        "fan_center_xy_mm_from_trace": [round(value, 3) for value in converted_center],
        "fan_center_xy_mm_model": list(FAN_CENTER_XY_MM),
        "profile_uncertainty_mm": FAN_PROFILE_UNCERTAINTY_MM,
        "model_rounding_max_error_mm": round(max(point_errors), 4),
        "caliper_measurements_mm": {
            "photo_01_pcb_width_x": PCB_X_MM,
            "photo_02_pcb_depth_y": PCB_Y_MM,
        },
        "caliper_scope_note": (
            "Photos 01/02 clamp the PCB plan near its corner regions; they do not "
            "measure a symmetric connector-front envelope."
        ),
        "overlay": "previews/calibration/01-blower-profile-trace.png",
        "warning": "the CAD model reads the reviewed millimetre profile, never these PNG pixels",
    }
    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {overlay_path}")
    print(f"Wrote {DATA_PATH}")


if __name__ == "__main__":
    main()
