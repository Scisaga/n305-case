#!/usr/bin/env python3
"""Render orthographic, uniformly scaled 04/06 panel references.

These drawings are CAD-input references.  Original-case photographs inform
profile details only; photo perspective and photo pixel spacing never control
mechanical dimensions or aperture orientation here.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from n305_panel_reference import (  # noqa: E402
    FACE_APERTURES,
    PCB_EDGE_SPAN_MM,
    PCB_THICKNESS_MM,
    POSITION_REVIEW_UNCERTAINTY_MM,
    PanelApertureReference,
)


PREVIEW_DIR = ROOT / "previews" / "reference"
PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
REFERENCE_JSON = ROOT / "docs" / "panel-apertures.json"

CANVAS_W = 1800
CANVAS_H = 1100
MM_SCALE = 12.0
ORIGIN_X = CANVAS_W / 2.0
PCB_BOTTOM_SCREEN_Y = 355.0

BACKGROUND = (244, 247, 250)
TEXT = (28, 36, 45)
MUTED = (70, 79, 88)
GRID_1 = (231, 235, 239)
GRID_5 = (210, 217, 224)
PCB_FILL = (204, 232, 211)
PCB_OUTLINE = (50, 126, 75)
APERTURE_FILL = (244, 180, 220)
APERTURE_OUTLINE = (205, 28, 139)
CENTER_MARK = (92, 49, 83)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    filename = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    try:
        return ImageFont.truetype(filename, size)
    except OSError:
        return ImageFont.load_default()


TITLE_FONT = font(38, bold=True)
SUBTITLE_FONT = font(21)
BODY_FONT = font(19)
SMALL_FONT = font(16)
SMALL_BOLD_FONT = font(16, bold=True)
TABLE_FONT = font(17)
TABLE_BOLD_FONT = font(17, bold=True)


def screen_x(center_y_mm: float, face: str) -> float:
    """Map common +Y (toward 07) into each exterior face view."""
    direction = -1.0 if face == "04" else +1.0
    return ORIGIN_X + direction * center_y_mm * MM_SCALE


def screen_z(z_mm: float) -> float:
    return PCB_BOTTOM_SCREEN_Y - z_mm * MM_SCALE


def centered_text(
    draw: ImageDraw.ImageDraw,
    center_x: float,
    top_y: float,
    value: str,
    use_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: tuple[int, int, int] = TEXT,
) -> None:
    box = draw.textbbox((0, 0), value, font=use_font)
    draw.text((center_x - (box[2] - box[0]) / 2.0, top_y), value, font=use_font, fill=fill)


def aperture_bbox(aperture: PanelApertureReference, face: str) -> tuple[float, float, float, float]:
    center_x = screen_x(aperture.center_y_mm, face)
    center_y = screen_z(aperture.center_z_mm)
    half_width = aperture.width_mm * MM_SCALE / 2.0
    half_height = aperture.height_mm * MM_SCALE / 2.0
    return (
        center_x - half_width,
        center_y - half_height,
        center_x + half_width,
        center_y + half_height,
    )


def draw_center_mark(draw: ImageDraw.ImageDraw, aperture: PanelApertureReference, face: str) -> None:
    x = screen_x(aperture.center_y_mm, face)
    y = screen_z(aperture.center_z_mm)
    draw.line((x - 5, y, x + 5, y), fill=CENTER_MARK, width=1)
    draw.line((x, y - 5, x, y + 5), fill=CENTER_MARK, width=1)


def draw_aperture(draw: ImageDraw.ImageDraw, aperture: PanelApertureReference, face: str) -> None:
    box = aperture_bbox(aperture, face)
    if aperture.shape == "circle":
        draw.ellipse(box, fill=APERTURE_FILL, outline=APERTURE_OUTLINE, width=4)
    elif aperture.shape == "roundrect":
        radius = round(aperture.corner_radius_mm * MM_SCALE)
        draw.rounded_rectangle(box, radius=radius, fill=APERTURE_FILL, outline=APERTURE_OUTLINE, width=4)
    elif aperture.shape == "case_hdmi_hex":
        center_x = screen_x(aperture.center_y_mm, face)
        center_y = screen_z(aperture.center_z_mm)
        half_width = aperture.width_mm * MM_SCALE / 2.0
        half_height = aperture.height_mm * MM_SCALE / 2.0
        half_top = aperture.feature_width_mm * MM_SCALE / 2.0
        chamfer_height = aperture.feature_height_mm * MM_SCALE
        points = [
            (center_x - half_top, center_y - half_height),
            (center_x + half_top, center_y - half_height),
            (center_x + half_width, center_y - half_height + chamfer_height),
            (center_x + half_width, center_y + half_height),
            (center_x - half_width, center_y + half_height),
            (center_x - half_width, center_y - half_height + chamfer_height),
        ]
        draw.polygon(points, fill=APERTURE_FILL)
        draw.line(points + [points[0]], fill=APERTURE_OUTLINE, width=4, joint="curve")
    elif aperture.shape == "rj45_main_plus_relief":
        radius = round(aperture.corner_radius_mm * MM_SCALE)
        draw.rounded_rectangle(box, radius=radius, fill=APERTURE_FILL, outline=APERTURE_OUTLINE, width=4)
        center_x = screen_x(aperture.center_y_mm, face)
        main_bottom_z = aperture.center_z_mm - aperture.height_mm / 2.0
        relief_center_z = main_bottom_z - aperture.feature_height_mm / 2.0
        relief_half_width = aperture.feature_width_mm * MM_SCALE / 2.0
        relief_half_height = aperture.feature_height_mm * MM_SCALE / 2.0
        relief_center_y = screen_z(relief_center_z)
        relief_box = (
            center_x - relief_half_width,
            relief_center_y - relief_half_height,
            center_x + relief_half_width,
            relief_center_y + relief_half_height,
        )
        draw.rounded_rectangle(
            relief_box,
            radius=max(2, round(0.2 * MM_SCALE)),
            fill=APERTURE_FILL,
            outline=APERTURE_OUTLINE,
            width=4,
        )
        draw.line(
            (relief_box[0] + 4, relief_box[1], relief_box[2] - 4, relief_box[1]),
            fill=APERTURE_FILL,
            width=6,
        )
    else:
        raise ValueError(f"unsupported aperture shape: {aperture.shape}")
    draw_center_mark(draw, aperture, face)


def profile_text(aperture: PanelApertureReference) -> str:
    if aperture.shape == "circle":
        return f"DIA {aperture.width_mm:.1f}"
    if aperture.shape == "roundrect":
        return f"{aperture.width_mm:.1f} x {aperture.height_mm:.1f}  R{aperture.corner_radius_mm:.1f}"
    if aperture.shape == "case_hdmi_hex":
        return (
            f"{aperture.width_mm:.1f} x {aperture.height_mm:.1f}; "
            f"top {aperture.feature_width_mm:.1f}; chamfer H {aperture.feature_height_mm:.1f}"
        )
    if aperture.shape == "rj45_main_plus_relief":
        return (
            f"main {aperture.width_mm:.1f} x {aperture.height_mm:.1f}; "
            f"bottom +{aperture.feature_width_mm:.1f} x {aperture.feature_height_mm:.1f}"
        )
    raise ValueError(aperture.shape)


def compact_dimension_source(aperture: PanelApertureReference) -> str:
    if aperture.name == "headphone":
        return "photo-derived; verify"
    if aperture.name == "power_switch":
        return "measured; original button"
    if aperture.shape == "case_hdmi_hex":
        return "measured + case photo profile"
    return "user measured"


def compact_position_source(face: str) -> str:
    return f"PCB-aligned 03 + {face} side"


def draw_grid_and_pcb(draw: ImageDraw.ImageDraw, face: str) -> tuple[float, float]:
    board_left = ORIGIN_X - PCB_EDGE_SPAN_MM * MM_SCALE / 2.0
    board_right = ORIGIN_X + PCB_EDGE_SPAN_MM * MM_SCALE / 2.0
    z_top = 8
    z_bottom = -13

    for y_mm in range(-52, 53):
        x = screen_x(float(y_mm), face)
        color = GRID_5 if y_mm % 5 == 0 else GRID_1
        width = 2 if y_mm % 5 == 0 else 1
        draw.line((x, screen_z(z_top), x, screen_z(z_bottom)), fill=color, width=width)
    for z_mm in range(z_bottom, z_top + 1):
        y = screen_z(float(z_mm))
        color = GRID_5 if z_mm % 5 == 0 else GRID_1
        width = 2 if z_mm % 5 == 0 else 1
        draw.line((board_left, y, board_right, y), fill=color, width=width)

    pcb_box = (
        board_left,
        screen_z(PCB_THICKNESS_MM),
        board_right,
        screen_z(0.0),
    )
    draw.rectangle(pcb_box, fill=PCB_FILL, outline=PCB_OUTLINE, width=3)
    draw.line((ORIGIN_X, screen_z(z_top), ORIGIN_X, screen_z(z_bottom)), fill=(117, 143, 166), width=2)
    draw.line((board_left, screen_z(0.0), board_right, screen_z(0.0)), fill=PCB_OUTLINE, width=3)

    dimension_y = 205
    draw.line((board_left, dimension_y, board_right, dimension_y), fill=MUTED, width=2)
    draw.line((board_left, dimension_y - 10, board_left, dimension_y + 10), fill=MUTED, width=2)
    draw.line((board_right, dimension_y - 10, board_right, dimension_y + 10), fill=MUTED, width=2)
    centered_text(
        draw,
        ORIGIN_X,
        170,
        f"PCB edge span {PCB_EDGE_SPAN_MM:.1f} mm   |   PCB thickness {PCB_THICKNESS_MM:.1f} mm",
        BODY_FONT,
        MUTED,
    )

    if face == "04":
        left_label, right_label = "07 / +Y", "05 / -Y"
    else:
        left_label, right_label = "05 / -Y", "07 / +Y"
    draw.text((board_left, 225), left_label, font=SMALL_BOLD_FONT, fill=MUTED)
    right_box = draw.textbbox((0, 0), right_label, font=SMALL_BOLD_FONT)
    draw.text((board_right - (right_box[2] - right_box[0]), 225), right_label, font=SMALL_BOLD_FONT, fill=MUTED)
    draw.text((board_left + 12, screen_z(PCB_THICKNESS_MM) - 26), "PCB", font=SMALL_BOLD_FONT, fill=PCB_OUTLINE)
    draw.text((ORIGIN_X + 8, screen_z(z_top)), "Y=0", font=SMALL_FONT, fill=MUTED)
    draw.text((board_right + 12, screen_z(0.0) - 10), "Z=0 PCB bottom", font=SMALL_FONT, fill=PCB_OUTLINE)
    return board_left, board_right


def draw_aperture_labels(draw: ImageDraw.ImageDraw, face: str) -> None:
    short_labels = {
        "dc": "DC",
        "hdmi_1": "H1",
        "headphone": "AU",
        "rj45": "RJ",
        "stack_dual_usb": "2USB",
        "hdmi_3": "H3",
        "usb_05": "USB05",
        "usb_07": "USB07",
        "power_switch": "SW",
    }
    for aperture in FACE_APERTURES[face]:
        centered_text(
            draw,
            screen_x(aperture.center_y_mm, face),
            screen_z(aperture.center_z_mm) - 9,
            short_labels[aperture.name],
            SMALL_BOLD_FONT,
            TEXT,
        )


def draw_table(draw: ImageDraw.ImageDraw, face: str) -> None:
    apertures = FACE_APERTURES[face]
    table_x = 65
    table_y = 610
    row_h = 48
    columns = [70, 235, 150, 150, 390, 315, 360]
    headers = ["ID", "aperture", "center Y", "center Z", "nominal profile", "size source", "position source"]
    names = {
        "dc": "DC",
        "hdmi_1": "HDMI 1",
        "headphone": "headphone",
        "rj45": "RJ45",
        "stack_dual_usb": "stacked dual USB",
        "hdmi_3": "HDMI 3",
        "usb_05": "USB toward 05",
        "usb_07": "USB toward 07",
        "power_switch": "power switch hole",
    }

    draw.text((table_x, table_y - 38), "CAD aperture table (all dimensions in mm)", font=BODY_FONT, fill=TEXT)
    x = table_x
    for width, header in zip(columns, headers):
        draw.rectangle((x, table_y, x + width, table_y + row_h), fill=(222, 228, 234), outline=(173, 181, 190))
        draw.text((x + 8, table_y + 13), header, font=TABLE_BOLD_FONT, fill=TEXT)
        x += width

    for index, aperture in enumerate(apertures, start=1):
        y = table_y + index * row_h
        row_fill = (249, 250, 252) if index % 2 else (238, 242, 246)
        values = [
            str(index),
            names[aperture.name],
            f"{aperture.center_y_mm:+.2f}",
            f"{aperture.center_z_mm:+.2f}",
            profile_text(aperture),
            compact_dimension_source(aperture),
            compact_position_source(face),
        ]
        x = table_x
        for width, value in zip(columns, values):
            draw.rectangle((x, y, x + width, y + row_h), fill=row_fill, outline=(195, 202, 210))
            draw.text((x + 8, y + 13), value, font=TABLE_FONT, fill=TEXT)
            x += width

    note_y = table_y + (len(apertures) + 1) * row_h + 25
    draw.text(
        (table_x, note_y),
        "Uniform scale: 12 px/mm. Nominal apertures only; no print/process clearance has been added.",
        font=BODY_FONT,
        fill=MUTED,
    )
    draw.text(
        (table_x, note_y + 32),
        f"Center positions are the current PCB-aligned review baseline (estimated review uncertainty +/-{POSITION_REVIEW_UNCERTAINTY_MM:.1f} mm).",
        font=SMALL_FONT,
        fill=MUTED,
    )


def render_interface_diagram(face: str) -> None:
    if face not in FACE_APERTURES:
        raise ValueError(f"unsupported interface face: {face}")

    image = Image.new("RGB", (CANVAS_W, CANVAS_H), BACKGROUND)
    draw = ImageDraw.Draw(image)
    draw.text((64, 42), f"{face} panel apertures - orthographic CAD reference", fill=TEXT, font=TITLE_FONT)
    draw.text(
        (64, 100),
        "UNIFORM MILLIMETRE SCALE   photo supplies profile evidence only   PCB boundary is the placement datum",
        fill=(46, 75, 103),
        font=SUBTITLE_FONT,
    )

    draw_grid_and_pcb(draw, face)
    for aperture in FACE_APERTURES[face]:
        draw_aperture(draw, aperture, face)
    draw_aperture_labels(draw, face)
    draw_table(draw, face)
    image.save(PREVIEW_DIR / f"{face}-interface-reference.png")


def write_reference_json() -> None:
    data = {
        "status": "orthographic CAD-input review baseline; no print clearance",
        "coordinate_frame": {
            "Y": "+Y points toward 07; -Y points toward 05",
            "Z": "Z=0 is PCB bottom; +Z points toward fan side",
            "face_04_exterior_screen": "left=07/+Y, right=05/-Y",
            "face_06_exterior_screen": "left=05/-Y, right=07/+Y",
        },
        "pcb_edge_reference_mm": {
            "span_y": PCB_EDGE_SPAN_MM,
            "thickness_z": PCB_THICKNESS_MM,
            "y_min": -PCB_EDGE_SPAN_MM / 2.0,
            "y_max": +PCB_EDGE_SPAN_MM / 2.0,
            "z_bottom": 0.0,
            "z_top": PCB_THICKNESS_MM,
        },
        "position_review_uncertainty_mm": POSITION_REVIEW_UNCERTAINTY_MM,
        "faces": {
            face: [asdict(aperture) for aperture in FACE_APERTURES[face]]
            for face in ("04", "06")
        },
    }
    REFERENCE_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    for face in ("04", "06"):
        render_interface_diagram(face)
        print(f"Rendered {PREVIEW_DIR / f'{face}-interface-reference.png'}")
    write_reference_json()
    print(f"Wrote {REFERENCE_JSON}")


if __name__ == "__main__":
    main()
