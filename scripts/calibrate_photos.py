#!/usr/bin/env python3
"""Create review evidence for the original case's 04 and 06 panels.

This script intentionally does one job. It traces the original case photo in
its own image plane. It does not mix motherboard-side coordinates, PCB datums,
or independently generated CAD geometry into the photograph.
"""

from __future__ import annotations

import copy
import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from n305_photo_reference import (  # noqa: E402
    CASE_04_CROP_PX,
    CASE_04_PHOTO_TRACES,
    CASE_04_SOURCE,
    CASE_06_CROP_PX,
    CASE_06_PHOTO_TRACES,
    CASE_06_SOURCE,
)


OUT_DIR = ROOT / "previews" / "calibration"
DATA_PATH = ROOT / "docs" / "photo-calibration.json"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def font(size: int = 18, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    filename = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    try:
        return ImageFont.truetype(filename, size)
    except OSError:
        return ImageFont.load_default()


LABEL_FONT = font(18)
NOTICE_FONT = font(22, bold=True)


def label(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    color: tuple[int, int, int] = (255, 230, 90),
    use_font: ImageFont.FreeTypeFont | ImageFont.ImageFont = LABEL_FONT,
) -> None:
    x, y = xy
    box = draw.textbbox((x, y), text, font=use_font)
    draw.rectangle((box[0] - 3, box[1] - 2, box[2] + 3, box[3] + 2), fill=(15, 15, 15))
    draw.text((x, y), text, fill=color, font=use_font)


def local_scale(trace: dict[str, object]) -> tuple[float, float]:
    x0, y0, x1, y1 = trace["bbox_px"]
    width_mm, height_mm = trace["confirmed_size_mm"]
    return (x1 - x0) / width_mm, (y1 - y0) / height_mm


def rj45_relief_bbox(trace: dict[str, object]) -> tuple[float, float, float, float]:
    """Return the additional relief below the 15 x 10 mm RJ45 main window."""
    x0, _, x1, y1 = trace["bbox_px"]
    scale_x, scale_y = local_scale(trace)
    relief_w, relief_h = trace["relief_size_mm"]
    center_x = (x0 + x1) / 2.0
    half_relief_w = relief_w * scale_x / 2.0
    return center_x - half_relief_w, y1, center_x + half_relief_w, y1 + relief_h * scale_y


def draw_local_grid(
    draw: ImageDraw.ImageDraw,
    trace: dict[str, object],
    scale_x: float,
    scale_y: float,
) -> None:
    x0, y0, x1, y1 = trace["bbox_px"]
    center_x = (x0 + x1) / 2.0
    center_y = (y0 + y1) / 2.0
    width_mm = (x1 - x0) / scale_x
    height_mm = (y1 - y0) / scale_y
    top_mm = height_mm / 2.0 + 1.25
    bottom_mm = height_mm / 2.0 + 1.25
    if trace["shape"] == "rj45_main_plus_relief":
        bottom_mm += float(trace["relief_size_mm"][1])
    left = center_x - (width_mm / 2.0 + 1.25) * scale_x
    right = center_x + (width_mm / 2.0 + 1.25) * scale_x
    top = center_y - top_mm * scale_y
    bottom = center_y + bottom_mm * scale_y

    for offset in range(math.ceil(-width_mm / 2.0 - 1.25), math.floor(width_mm / 2.0 + 1.25) + 1):
        x = center_x + offset * scale_x
        draw.line((x, top, x, bottom), fill=(0, 210, 235), width=1)
    for offset in range(math.ceil(-top_mm), math.floor(bottom_mm) + 1):
        y = center_y + offset * scale_y
        draw.line((left, y, right, y), fill=(0, 210, 235), width=1)
    draw.line((center_x, top, center_x, bottom), fill=(255, 215, 35), width=3)
    draw.line((left, center_y, right, center_y), fill=(255, 215, 35), width=3)


def draw_photo_trace(draw: ImageDraw.ImageDraw, trace: dict[str, object]) -> None:
    """Draw only the manually reviewed photo-plane outline."""
    magenta = (235, 20, 170)
    bbox = trace["bbox_px"]
    if trace["shape"] == "circle":
        draw.ellipse(bbox, outline=magenta, width=5)
    elif trace["shape"] == "photo_polygon":
        points = list(trace["vertices_px"])
        draw.line(points + [points[0]], fill=magenta, width=5, joint="curve")
    elif trace["shape"] == "roundrect":
        scale_x, scale_y = local_scale(trace)
        radius = int(round(float(trace["corner_radius_mm"]) * (scale_x + scale_y) / 2.0))
        draw.rounded_rectangle(bbox, radius=radius, outline=magenta, width=5)
    elif trace["shape"] == "photo_roundrect":
        points = rounded_polygon(
            list(trace["vertices_px"]),
            radius=float(trace["corner_radius_px"]),
        )
        draw.line(points + [points[0]], fill=magenta, width=5, joint="curve")
    elif trace["shape"] == "rj45_main_plus_relief":
        scale_x, scale_y = local_scale(trace)
        radius = int(round(0.6 * (scale_x + scale_y) / 2.0))
        relief = rj45_relief_bbox(trace)
        draw.rounded_rectangle(bbox, radius=radius, outline=magenta, width=5)
        draw.rounded_rectangle(relief, radius=max(3, int(round(0.2 * scale_y))), outline=magenta, width=5)
        # Hide the shared boundary so the two parts read as one aperture.
        draw.line((relief[0] + 5, relief[1], relief[2] - 5, relief[1]), fill=(15, 15, 15), width=7)
    else:
        raise ValueError(f"unsupported photo trace: {trace['shape']}")


def rounded_polygon(
    points: list[tuple[float, float]],
    radius: float,
    samples: int = 8,
) -> list[tuple[float, float]]:
    """Round the corners of a photographed quadrilateral without rectifying it."""
    result: list[tuple[float, float]] = []
    count = len(points)
    for index, current in enumerate(points):
        previous = points[(index - 1) % count]
        following = points[(index + 1) % count]

        def toward(origin: tuple[float, float], target: tuple[float, float]) -> tuple[float, float]:
            dx = target[0] - origin[0]
            dy = target[1] - origin[1]
            length = math.hypot(dx, dy)
            amount = min(radius, length / 3.0) / length
            return origin[0] + dx * amount, origin[1] + dy * amount

        entry = toward(current, previous)
        exit_point = toward(current, following)
        for sample in range(samples + 1):
            t = sample / samples
            one_minus = 1.0 - t
            result.append(
                (
                    one_minus * one_minus * entry[0]
                    + 2.0 * one_minus * t * current[0]
                    + t * t * exit_point[0],
                    one_minus * one_minus * entry[1]
                    + 2.0 * one_minus * t * current[1]
                    + t * t * exit_point[1],
                )
            )
    return result


def calibrate_original_case(
    face: str,
    source_path: str,
    crop_px: tuple[int, int, int, int],
    photo_traces: tuple[dict[str, object], ...],
    view: str,
) -> dict[str, object]:
    source = ImageOps.exif_transpose(Image.open(ROOT / source_path)).convert("RGB")
    image = source.copy()
    draw = ImageDraw.Draw(image)
    traces = [copy.deepcopy(item) for item in photo_traces]
    by_name = {item["name"]: item for item in traces}

    fallback_scale = local_scale(by_name["hdmi_1"]) if "hdmi_1" in by_name else None
    results: list[dict[str, object]] = []
    for trace in traces:
        x0, y0, x1, y1 = trace["bbox_px"]
        if "confirmed_size_mm" in trace:
            scale_x, scale_y = local_scale(trace)
            width_mm, height_mm = trace["confirmed_size_mm"]
            if trace["shape"] == "circle" and width_mm == height_mm:
                size_note = f"known DIA {width_mm:.1f} mm"
            else:
                size_note = f"known {width_mm:.1f} x {height_mm:.1f} mm"
        else:
            if fallback_scale is None:
                raise ValueError(f"{face} has no scale source for {trace['name']}")
            scale_x, scale_y = fallback_scale
            measured_x = (x1 - x0) / scale_x
            measured_y = (y1 - y0) / scale_y
            trace["photo_measurement_mm"] = (round(measured_x, 2), round(measured_y, 2))
            trace["equivalent_diameter_mm"] = round(math.sqrt(measured_x * measured_y), 2)
            size_note = f"photo-derived {measured_x:.2f} x {measured_y:.2f} mm; physical check pending"

        draw_local_grid(draw, trace, scale_x, scale_y)
        draw.rectangle(trace["bbox_px"], outline=(255, 150, 20), width=3)
        if trace["shape"] == "rj45_main_plus_relief":
            draw.rectangle(rj45_relief_bbox(trace), outline=(255, 150, 20), width=3)
            size_note = "main 15.0 x 10.0 mm + bottom relief 4.5 x 1.0 mm"
        draw_photo_trace(draw, trace)
        label(
            draw,
            (x0, max(crop_px[1] + 35, y0 - 28)),
            f"{trace['name']}  {size_note}; local grid {scale_x:.2f}/{scale_y:.2f} px/mm",
        )

        raw_name = f"original-case-{face}-{trace['name']}-raw.png"
        crop = (
            max(0, x0 - 120),
            max(0, y0 - 100),
            min(source.width, x1 + 120),
            min(source.height, y1 + 150),
        )
        source.crop(crop).save(OUT_DIR / raw_name)
        results.append(
            {
                **trace,
                "local_grid_px_per_mm": [round(scale_x, 4), round(scale_y, 4)],
                "raw_crop": f"previews/calibration/{raw_name}",
            }
        )

    label(
        draw,
        (crop_px[0] + 10, crop_px[1] + 5),
        "LOCAL SIZE GRIDS ONLY - positions remain in the original photograph's image plane",
        (255, 235, 90),
        NOTICE_FONT,
    )
    output = OUT_DIR / f"original-case-{face}-1mm-grid.png"
    image.crop(crop_px).save(output)
    result = {
        "source": source_path,
        "source_resolution_px": list(source.size),
        "view": view,
        "scope": "photo-plane aperture outlines and local size grids only",
        "warning": "local grids do not establish a shared motherboard coordinate system or PCB datum",
        "features": results,
        "overlay": f"previews/calibration/original-case-{face}-1mm-grid.png",
    }
    if face == "04":
        result["rj45_semantics"] = (
            "15 x 10 mm is the main window; 4.5 x 1 mm is an additional bottom relief"
        )
    if face == "06":
        result["position_semantics"] = (
            "USB openings retain separate photo-plane vertical positions; no common PCB baseline"
        )
    return result


def main() -> None:
    data = {
        "status": "04 and 06 original-case photo traces only",
        "original_case_04": calibrate_original_case(
            "04",
            CASE_04_SOURCE,
            CASE_04_CROP_PX,
            CASE_04_PHOTO_TRACES,
            "original case exterior 04 face; left is 07, right is 05",
        ),
        "original_case_06": calibrate_original_case(
            "06",
            CASE_06_SOURCE,
            CASE_06_CROP_PX,
            CASE_06_PHOTO_TRACES,
            "original case exterior 06 face; left/right refer only to this photograph",
        ),
    }
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {DATA_PATH}")
    print(f"Wrote {OUT_DIR / 'original-case-04-1mm-grid.png'}")
    print(f"Wrote {OUT_DIR / 'original-case-06-1mm-grid.png'}")


if __name__ == "__main__":
    main()
