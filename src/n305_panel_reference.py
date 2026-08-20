"""Current orthographic panel-aperture reference data.

The data chain is intentionally explicit:

* measured PCB dimensions define the datum and drawing scale;
* the earlier PCB-aligned 03/04/06 calibration defines aperture centers;
* user-confirmed measurements define aperture width and height;
* original-case photographs define only non-rectangular profile details.

Photo pixels are never used as a global mechanical scale in this module.
"""

from __future__ import annotations

from dataclasses import dataclass


PCB_EDGE_SPAN_MM = 105.5
PCB_THICKNESS_MM = 1.5
PCB_Y_MIN_MM = -PCB_EDGE_SPAN_MM / 2.0
PCB_Y_MAX_MM = +PCB_EDGE_SPAN_MM / 2.0

# Positions were already recorded by the PCB-aligned calibration before the
# invalid photo-perspective reference render was introduced.  Y is measured
# along the 04/06 PCB edge: +Y points toward face 07 and -Y toward face 05.
# Z=0 is the PCB bottom surface and +Z points toward the fan side.
POSITION_REVIEW_UNCERTAINTY_MM = 0.7


@dataclass(frozen=True)
class PanelApertureReference:
    name: str
    face: str
    center_y_mm: float
    center_z_mm: float
    shape: str
    width_mm: float
    height_mm: float
    dimension_source: str
    position_source: str
    corner_radius_mm: float = 0.0
    feature_width_mm: float = 0.0
    feature_height_mm: float = 0.0


FACE_04_APERTURES = (
    PanelApertureReference(
        "dc", "04", +39.83, -4.33, "circle", 5.9, 5.9,
        "user measured", "03 plan + 04 measured side calibration",
    ),
    PanelApertureReference(
        "hdmi_1", "04", +23.75, -5.02, "case_hdmi_hex", 16.5, 5.8,
        "user measured; original-case hex profile",
        "03 plan + 04 measured side calibration",
        feature_width_mm=10.7,
        feature_height_mm=1.9,
    ),
    PanelApertureReference(
        "headphone", "04", +23.75, +3.57, "circle", 5.4, 5.4,
        "photo-derived; physical check pending",
        "04 measured side calibration",
    ),
    PanelApertureReference(
        "rj45", "04", +3.75, -3.55, "rj45_main_plus_relief", 15.0, 10.0,
        "user measured; relief is additional",
        "03 plan + 04 measured side calibration",
        corner_radius_mm=0.6,
        feature_width_mm=4.5,
        feature_height_mm=1.0,
    ),
    PanelApertureReference(
        "stack_dual_usb", "04", -14.25, -3.47, "roundrect", 14.0, 14.5,
        "user measured", "03 plan + 04 measured side calibration",
        corner_radius_mm=0.7,
    ),
    PanelApertureReference(
        "hdmi_3", "04", -36.08, -5.27, "case_hdmi_hex", 16.5, 5.8,
        "user measured; original-case hex profile",
        "03 plan + 04 measured side calibration",
        feature_width_mm=10.7,
        feature_height_mm=1.9,
    ),
)


# Exterior 06 view reads from screen left to right as 05 -> 07.  The two USB
# apertures are true horizontal rounded rectangles.  Their independently
# calibrated center heights differ by 0.10 mm; that does not tilt either cut.
FACE_06_APERTURES = (
    PanelApertureReference(
        "usb_05", "06", -15.25, -3.09, "roundrect", 12.8, 5.5,
        "user measured", "03 plan + 06 measured side calibration",
        corner_radius_mm=0.7,
    ),
    PanelApertureReference(
        "usb_07", "06", +4.75, -3.19, "roundrect", 12.8, 5.5,
        "user measured", "03 plan + 06 measured side calibration",
        corner_radius_mm=0.7,
    ),
    PanelApertureReference(
        "power_switch", "06", +29.50, -4.20, "circle", 9.4, 9.4,
        "user measured; original button reused",
        "03 plan + 06 measured side calibration",
    ),
)


FACE_APERTURES = {
    "04": FACE_04_APERTURES,
    "06": FACE_06_APERTURES,
}

