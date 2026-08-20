"""Review-only structural definition for the N305 two-shell enclosure.

This module is the single geometry and parameter source shared by the enclosure
structure review and the explicitly authorized V2 prototype exporter.  It does
not write files by itself.  Confirmed dimensions, prototype assumptions and
unresolved manufacturing choices remain separate in every consuming output.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import cadquery as cq

from n305_mainboard_reference import (
    ALL_CONNECTORS,
    FACE_04_CONNECTORS,
    FACE_04_OTHER_PROJECTION_MM,
    FACE_04_MAX_PROJECTION_MM,
    FACE_06_USB_PROJECTION_MM,
    FAN_CENTER_XY_MM,
    FAN_INLET_D_MM,
    FAN_PROFILE_UNCERTAINTY_MM,
    FAN_SHELL_PROFILE_XY_MM,
    FAN_TOP_Z_MM,
    FIN_STACK_CENTER_X_MM,
    FIN_STACK_CENTER_Y_MM,
    FIN_STACK_X_MM,
    FIN_STACK_Y_MM,
    LOWEST_Z_MM,
    MOUNT_HOLE_D_MM,
    MOUNT_HOLES,
    PCB_CORNER_R_MM,
    PCB_T_MM,
    PCB_X_MM,
    PCB_Y_MM,
    SWITCH_ACTUATOR_TIP_X_MM,
    SWITCH_CENTER_Y_MM,
    SWITCH_CENTER_Z_MM,
    SWITCH_PLAN_POSITION_UNCERTAINTY_MM,
    build_geometry as build_motherboard_geometry,
    compound,
    cylinder_z,
    make_connector,
    rounded_plate_xy,
)
from n305_panel_reference import FACE_APERTURES, PanelApertureReference


@dataclass(frozen=True)
class ReviewParameter:
    name: str
    value: object
    unit: str
    status: str
    source: str
    note: str = ""


@dataclass(frozen=True)
class SeamSegment:
    name: str
    faces: tuple[str, str]
    start_xyz_mm: tuple[float, float, float]
    end_xyz_mm: tuple[float, float, float]
    joint: str
    path_xyz_mm: tuple[tuple[float, float, float], ...] = ()


@dataclass(frozen=True)
class CoverageTarget:
    name: str
    face: str
    aperture_name: str
    center_y_mm: float
    center_z_mm: float
    shape: str
    width_mm: float
    height_mm: float
    corner_radius_mm: float
    source: str


@dataclass(frozen=True)
class RibSegment:
    """One centerline segment in the reviewed internal rib layout."""

    name: str
    start_xy_mm: tuple[float, float]
    end_xy_mm: tuple[float, float]


# Confirmed Z rule: no additional fan-side or underside avoidance gap.  The
# generated board envelope rounds to -10.3 ... +15.3 mm (25.6 mm total).
INNER_Z_MIN_MM = -10.3
INNER_Z_MAX_MM = FAN_TOP_Z_MM
TOP_PLATE_T_MM = 1.2
BOTTOM_PLATE_T_MM = 1.2
OUTER_Z_MIN_MM = INNER_Z_MIN_MM - BOTTOM_PLATE_T_MM
OUTER_Z_MAX_MM = INNER_Z_MAX_MM + TOP_PLATE_T_MM
OUTER_Z_MM = OUTER_Z_MAX_MM - OUTER_Z_MIN_MM

# Faces 04 and 06 remain complete planar walls with only the reviewed openings
# cut through them.  The user measured the original case at 103.0 mm between
# faces 04/06, with 1.8 mm side walls.  The reported 110.5 mm original-case
# span at faces 05/07 includes extra unused space and is deliberately not copied
# into this compact enclosure.
# The X allocation is constrained by the independently reported maximum USB
# projections: 2.0 mm at face 04 and 1.0 mm at face 06.  This places the inner
# wall planes at the USB fronts instead of at the recessed board switch.  Faces
# 05/07 retain the previously requested 0.20 mm fit-check allowance per side.
# The four PCB mounting axes, not the side walls, provide the primary XY location.
ORIGINAL_CASE_INNER_X_MM = 103.0
SIDE_WALL_T_MM = 1.8
PCB_CLEARANCE_04_MM = FACE_04_MAX_PROJECTION_MM
PCB_CLEARANCE_06_MM = ORIGINAL_CASE_INNER_X_MM - PCB_X_MM - PCB_CLEARANCE_04_MM
PCB_CLEARANCE_05_MM = 0.2
PCB_CLEARANCE_07_MM = 0.2
INNER_X_MIN_MM = -PCB_X_MM / 2.0 - PCB_CLEARANCE_04_MM
INNER_X_MAX_MM = +PCB_X_MM / 2.0 + PCB_CLEARANCE_06_MM
OUTER_X_MIN_MM = round(INNER_X_MIN_MM - SIDE_WALL_T_MM, 3)
OUTER_X_MAX_MM = round(INNER_X_MAX_MM + SIDE_WALL_T_MM, 3)
OUTER_X_MM = round(OUTER_X_MAX_MM - OUTER_X_MIN_MM, 3)
INNER_Y_MIN_MM = -PCB_Y_MM / 2.0 - PCB_CLEARANCE_05_MM
INNER_Y_MAX_MM = +PCB_Y_MM / 2.0 + PCB_CLEARANCE_07_MM
OUTER_Y_MIN_MM = INNER_Y_MIN_MM - SIDE_WALL_T_MM
OUTER_Y_MAX_MM = INNER_Y_MAX_MM + SIDE_WALL_T_MM
OUTER_Y_MM = round(OUTER_Y_MAX_MM - OUTER_Y_MIN_MM, 3)
INNER_PLAN_CENTER_X_MM = (INNER_X_MIN_MM + INNER_X_MAX_MM) / 2.0
INNER_PLAN_CENTER_Y_MM = (INNER_Y_MIN_MM + INNER_Y_MAX_MM) / 2.0
OUTER_PLAN_CENTER_X_MM = (OUTER_X_MIN_MM + OUTER_X_MAX_MM) / 2.0
OUTER_PLAN_CENTER_Y_MM = (OUTER_Y_MIN_MM + OUTER_Y_MAX_MM) / 2.0

# Axial closure derived from the same PCB coordinate system used by the four
# clamp axes.  Once those axes engage the PCB holes, the board cannot translate
# in X to invalidate these wall distances.  The 04/06 connector-front span
# closes the measured 103.0 mm cavity exactly at the current rough projections.
CONNECTOR_FRONT_SPAN_X_MM = (
    PCB_X_MM + FACE_04_MAX_PROJECTION_MM + FACE_06_USB_PROJECTION_MM
)
FACE_04_MOUNT_AXIS_TO_INNER_WALL_MM = tuple(
    round(x - INNER_X_MIN_MM, 3) for _, x, _ in MOUNT_HOLES if x < 0.0
)
FACE_06_MOUNT_AXIS_TO_INNER_WALL_MM = tuple(
    round(INNER_X_MAX_MM - x, 3) for _, x, _ in MOUNT_HOLES if x > 0.0
)
BUTTON_INNER_WALL_TO_SWITCH_TIP_MM = round(
    INNER_X_MAX_MM - SWITCH_ACTUATOR_TIP_X_MM, 3
)
BUTTON_OUTER_WALL_TO_SWITCH_TIP_MM = round(
    OUTER_X_MAX_MM - SWITCH_ACTUATOR_TIP_X_MM, 3
)
BUTTON_INNER_GAP_RANGE_MM = (
    round(BUTTON_INNER_WALL_TO_SWITCH_TIP_MM - SWITCH_PLAN_POSITION_UNCERTAINTY_MM, 3),
    round(BUTTON_INNER_WALL_TO_SWITCH_TIP_MM + SWITCH_PLAN_POSITION_UNCERTAINTY_MM, 3),
)
BUTTON_OUTER_STACK_RANGE_MM = (
    round(BUTTON_OUTER_WALL_TO_SWITCH_TIP_MM - SWITCH_PLAN_POSITION_UNCERTAINTY_MM, 3),
    round(BUTTON_OUTER_WALL_TO_SWITCH_TIP_MM + SWITCH_PLAN_POSITION_UNCERTAINTY_MM, 3),
)

# The inner R4 remains provisional until the physical corner is measured.  It
# belongs to the expanded cavity, not to a claim of four-edge PCB contact.  The
# outer radius is the constant-thickness offset of this cavity.
INNER_PLAN_CORNER_R_MM = PCB_CORNER_R_MM
OUTER_PLAN_CORNER_R_MM = INNER_PLAN_CORNER_R_MM + SIDE_WALL_T_MM
SEAM_06_07_TANGENT_X_MM = OUTER_X_MAX_MM - OUTER_PLAN_CORNER_R_MM
SEAM_04_05_TANGENT_X_MM = OUTER_X_MIN_MM + OUTER_PLAN_CORNER_R_MM

# No process clearance is applied at this review stage.  A future value can be
# introduced only after print process/material and user approval are known.
NOMINAL_SEAM_GAP_MM = 0.0
MANUFACTURING_SEAM_CLEARANCE_MM = 0.0

# Four existing PCB axes are reused.  The dimensions below are a review proposal
# derived from the 3.2 mm board holes; screw head, thread and insert style remain
# unresolved and are intentionally not modeled as final fastener geometry.
CLAMP_POST_OD_MM = 6.4
UPPER_THREAD_PILOT_D_MM = 2.5
LOWER_SCREW_CLEARANCE_D_MM = 3.4
ORIGINAL_BUTTON_THROUGH_D_MM = 9.2

# Internal reinforcement approved after plan and collision review.  The base
# top/bottom skins remain exactly 1.2 mm; 0.8 mm is added only along the rib
# paths.  It replaces the earlier 0.5 mm draft because it is more reliably
# resolved by the intended MJF/SLS process while retaining collision clearance.
REINFORCEMENT_REVIEW_STATUS = "approved and applied to V2 CAD"
REINFORCEMENT_RIB_HEIGHT_MM = 0.8
REINFORCEMENT_RIB_WIDTH_MM = 1.5
REINFORCEMENT_COMPONENT_CLEARANCE_MM = 1.0
REINFORCEMENT_ROOT_FILLET_MM = 0.0

# The upper layout routes entirely around the photo-traced blower envelope and
# the complete 84 x 22 mm fin footprint.  The lower layout crosses the plate in
# corridors that stay behind the deepest 04-side connector bodies, especially
# the lower member of the stacked dual USB reference at Z=-10.29 mm.
TOP_REINFORCEMENT_SEGMENTS = (
    RibSegment("top_07_cross", (-52.0, +45.0), (+51.0, +45.0)),
    RibSegment("top_06_spine", (+28.5, -52.95), (+28.5, +52.95)),
    RibSegment("top_fan_upper_bypass", (-26.0, +24.0), (+51.0, +24.0)),
    RibSegment("top_fan_lower_bypass", (-26.0, -37.0), (+51.0, -37.0)),
    RibSegment("top_fin_upper_return", (-25.5, +24.0), (-25.5, +45.0)),
    RibSegment("top_fin_lower_return", (-25.5, -52.95), (-25.5, -37.0)),
)
BOTTOM_REINFORCEMENT_SEGMENTS = (
    RibSegment("bottom_04_spine", (-28.5, -52.95), (-28.5, +52.95)),
    RibSegment("bottom_06_spine", (+28.5, -52.95), (+28.5, +52.95)),
    RibSegment("bottom_05_edge", (-52.0, -47.0), (+51.0, -47.0)),
    RibSegment("bottom_usb_lower_bypass", (-52.0, -30.0), (+51.0, -30.0)),
    RibSegment("bottom_usb_upper_bypass", (-52.0, +25.0), (+51.0, +25.0)),
    RibSegment("bottom_07_edge", (-52.0, +47.0), (+51.0, +47.0)),
)

FAN_INTAKE_D_MM = FAN_INLET_D_MM
FIN_EXHAUST_WIDTH_Y_MM = FIN_STACK_Y_MM
FIN_EXHAUST_Z_MIN_MM = 7.9
FIN_EXHAUST_Z_MAX_MM = FAN_TOP_Z_MM
FIN_EXHAUST_HEIGHT_Z_MM = FIN_EXHAUST_Z_MAX_MM - FIN_EXHAUST_Z_MIN_MM
FIN_EXHAUST_CENTER_Z_MM = (FIN_EXHAUST_Z_MIN_MM + FIN_EXHAUST_Z_MAX_MM) / 2.0


FACE_OWNERSHIP = {
    "top": "upper",
    "06": "upper",
    "05": "upper",
    "bottom": "lower",
    "04": "lower",
    "07": "lower",
}

ASSEMBLY_SEQUENCE = (
    "Place the upper shell exterior-top-down with its interior open toward -Z.",
    "Lay the motherboard on the four flat upper-post shoulders; no printed feature enters a PCB hole.",
    "Pre-insert two diagonal fasteners through the lower sleeves so their shanks/tips enter the original PCB holes and align the lower shell.",
    "Start all four fasteners loosely, close all six butt seams, then tighten evenly from the bottom side.",
)


REVIEW_PARAMETERS = (
    ReviewParameter("top_plate_thickness", TOP_PLATE_T_MM, "mm", "confirmed", "user"),
    ReviewParameter("bottom_plate_thickness", BOTTOM_PLATE_T_MM, "mm", "confirmed", "user"),
    ReviewParameter("inner_z_min", INNER_Z_MIN_MM, "mm", "measured/generated", "motherboard validation"),
    ReviewParameter("inner_z_max", INNER_Z_MAX_MM, "mm", "measured", "05 side measurement"),
    ReviewParameter("outer_body_thickness", OUTER_Z_MM, "mm", "derived", "25.6 mm assembly + two 1.2 mm plates"),
    ReviewParameter("inner_x_at_04_06", INNER_X_MAX_MM - INNER_X_MIN_MM, "mm", "user approximate measurement", "original case: face 04 inner wall to face 06 inner wall"),
    ReviewParameter("inner_y_at_05_07", INNER_Y_MAX_MM - INNER_Y_MIN_MM, "mm", "fit-check design", "PCB 105.5 + 0.2 mm allowance at faces 05 and 07; original-case 110.5 mm span deliberately not copied"),
    ReviewParameter("outer_x", OUTER_X_MM, "mm", "derived", "103.0 mm measured inner X + 2 x 1.8 mm measured side wall"),
    ReviewParameter("outer_y", OUTER_Y_MM, "mm", "derived", "105.9 mm compact inner Y + 2 x 1.8 mm measured side wall"),
    ReviewParameter("side_wall_thickness", SIDE_WALL_T_MM, "mm", "user measured", "original case side wall", "Not applied to panel aperture sizes."),
    ReviewParameter("outer_plan_corner_radius", OUTER_PLAN_CORNER_R_MM, "mm", "derived provisional", "inner PCB radius + side-wall thickness", "Constant-thickness XY offset; replaces the invalid R10 corner."),
    ReviewParameter("inner_plan_corner_radius", INNER_PLAN_CORNER_R_MM, "mm", "provisional", "photo-reconstructed motherboard corner radius", "Must be replaced if a physical corner measurement differs."),
    ReviewParameter("pcb_clearance_face_04", PCB_CLEARANCE_04_MM, "mm", "derived provisional allocation", "2.0 mm maximum 04 USB projection and 103.0 mm measured inner span", "Inner wall coincides nominally with the maximum USB front plane; it is not a PCB locating face."),
    ReviewParameter("pcb_clearance_face_06", PCB_CLEARANCE_06_MM, "mm", "derived provisional allocation", "remaining 1.0 mm of the measured 103.0 mm inner span", "Matches the 1.0 mm USB projection; the recessed switch is not the wall datum."),
    ReviewParameter("pcb_clearance_face_05", PCB_CLEARANCE_05_MM, "mm", "user-requested fit-check allowance", "compact non-locating clearance; original-case 110.5 mm span includes unnecessary extra space"),
    ReviewParameter("pcb_clearance_face_07", PCB_CLEARANCE_07_MM, "mm", "user-requested fit-check allowance", "compact non-locating clearance; original-case 110.5 mm span includes unnecessary extra space"),
    ReviewParameter("original_button_through_diameter", ORIGINAL_BUTTON_THROUGH_D_MM, "mm", "user measured", "diameter of the original button portion that passes through the panel"),
    ReviewParameter("face_06_switch_tip_to_inner_wall", round(INNER_X_MAX_MM - SWITCH_ACTUATOR_TIP_X_MM, 3), "mm", "photo-derived provisional", "photo 03 places the switch behind the USB-defined wall datum; positive means no switch/wall penetration"),
    ReviewParameter("connector_front_span_04_to_06", CONNECTOR_FRONT_SPAN_X_MM, "mm", "derived cross-check", "PCB 100.0 + face-04 USB projection 2.0 + face-06 USB projection 1.0; equals the measured inner span"),
    ReviewParameter("mount_axes_to_face_04_inner_wall", FACE_04_MOUNT_AXIS_TO_INNER_WALL_MM, "mm", "derived", "two negative-X PCB mounting axes; these axes fix the board against X translation"),
    ReviewParameter("mount_axes_to_face_06_inner_wall", FACE_06_MOUNT_AXIS_TO_INNER_WALL_MM, "mm", "derived", "two positive-X PCB mounting axes; these axes fix the board against X translation"),
    ReviewParameter("button_inner_wall_to_switch_tip_range", BUTTON_INNER_GAP_RANGE_MM, "mm", "photo-derived estimated range", "nominal 1.2 mm with +/-0.4 mm switch-plan uncertainty; excludes unquantified USB rough-measurement error"),
    ReviewParameter("button_outer_wall_to_switch_tip_range", BUTTON_OUTER_STACK_RANGE_MM, "mm", "derived estimated range", "1.8 mm measured wall plus the inner-wall-to-switch range; original button must bridge this axial stack"),
    ReviewParameter("face_04_max_connector_projection", FACE_04_MAX_PROJECTION_MM, "mm", "user rough measurement", "stacked dual USB maximum; not shared by every 04 connector"),
    ReviewParameter("face_04_other_connector_projection_proxy", FACE_04_OTHER_PROJECTION_MM, "mm", "provisional", "unmeasured 04 connector noses", "Visual proxy only; DC, HDMI, headphone and RJ45 front projections are not individually measured."),
    ReviewParameter("face_06_usb_projection", FACE_06_USB_PROJECTION_MM, "mm", "user rough measurement", "two USB front faces; independent from face 04"),
    ReviewParameter("nominal_seam_gap", NOMINAL_SEAM_GAP_MM, "mm", "design intent", "flush review geometry"),
    ReviewParameter("manufacturing_seam_clearance", MANUFACTURING_SEAM_CLEARANCE_MM, "mm", "not applied", "no manufacturing gap is embedded in the review geometry; any future process compensation must be a separate parameter"),
    ReviewParameter("fan_intake", FAN_INTAKE_D_MM, "mm diameter", "confirmed/derived", "measured fan inlet; no added clearance"),
    ReviewParameter("fin_exhaust", (FIN_EXHAUST_WIDTH_Y_MM, FIN_EXHAUST_HEIGHT_Z_MM), "mm", "functional envelope", "current fin-stack projection; grille segmentation pending"),
    ReviewParameter("internal_reinforcement_rib_height", REINFORCEMENT_RIB_HEIGHT_MM, "mm", "fit-check design", "selected after PA12 manufacturability and collision review", "Added locally to the 1.2 mm inner plate faces; does not change the base plate thickness."),
    ReviewParameter("internal_reinforcement_rib_width", REINFORCEMENT_RIB_WIDTH_MM, "mm", "fit-check design", "reviewed sparse rib paths", "Upper paths bypass the blower/fins; lower paths bypass the stacked dual USB and complete motherboard reference."),
    ReviewParameter("clamp_post_od", CLAMP_POST_OD_MM, "mm", "provisional", "review proposal"),
    ReviewParameter("upper_thread_pilot_diameter", UPPER_THREAD_PILOT_D_MM, "mm", "provisional", "review proposal", "Thread, heat-set insert or self-tapping strategy is not selected."),
    ReviewParameter("lower_screw_clearance_diameter", LOWER_SCREW_CLEARANCE_D_MM, "mm", "provisional", "review proposal", "No screw-head counterbore or countersink is included."),
    ReviewParameter("printed_hole_locator_nose", False, "", "review recommendation", "removed: 3.0 OD around 2.5 pilot leaves only 0.25 mm radial wall"),
    ReviewParameter("fastener_family", "M3-class", "", "provisional", "inferred from 3.2 mm PCB hole", "Head, insert and thread form pending."),
)


def _corner_arc_xy(
    center_x: float,
    center_y: float,
    start_deg: float,
    end_deg: float,
    samples: int = 10,
) -> tuple[tuple[float, float], ...]:
    return tuple(
        (
            round(center_x + OUTER_PLAN_CORNER_R_MM * math.cos(math.radians(angle)), 6),
            round(center_y + OUTER_PLAN_CORNER_R_MM * math.sin(math.radians(angle)), 6),
        )
        for angle in (
            start_deg + (end_deg - start_deg) * index / samples
            for index in range(samples + 1)
        )
    )


def _path_at_z(
    points_xy: tuple[tuple[float, float], ...], z: float
) -> tuple[tuple[float, float, float], ...]:
    return tuple((x, y, z) for x, y in points_xy)


def _build_seam_path() -> tuple[SeamSegment, ...]:
    """Return the closed boundary with vertical seams off the curved surfaces."""
    radius = OUTER_PLAN_CORNER_R_MM
    x_min = OUTER_X_MIN_MM
    x_max = OUTER_X_MAX_MM
    y_min = OUTER_Y_MIN_MM
    y_max = OUTER_Y_MAX_MM
    lower_left = (x_min + radius, y_min + radius)
    upper_left = (x_min + radius, y_max - radius)
    upper_right = (x_max - radius, y_max - radius)
    lower_right = (x_max - radius, y_min + radius)

    top_04_xy = (
        _corner_arc_xy(*lower_left, 270.0, 180.0)
        + ((x_min, y_max - radius),)
        + _corner_arc_xy(*upper_left, 180.0, 90.0)[1:]
    )
    top_07_xy = (
        ((SEAM_04_05_TANGENT_X_MM, y_max),)
        + ((SEAM_06_07_TANGENT_X_MM, y_max),)
    )
    bottom_06_xy = (
        _corner_arc_xy(*upper_right, 90.0, 0.0)
        + ((x_max, y_min + radius),)
        + _corner_arc_xy(*lower_right, 0.0, -90.0)[1:]
    )
    bottom_05_xy = (
        ((SEAM_06_07_TANGENT_X_MM, y_min),)
        + ((SEAM_04_05_TANGENT_X_MM, y_min),)
    )

    top_04 = _path_at_z(top_04_xy, INNER_Z_MAX_MM)
    top_07 = _path_at_z(top_07_xy, INNER_Z_MAX_MM)
    bottom_06 = _path_at_z(bottom_06_xy, INNER_Z_MIN_MM)
    bottom_05 = _path_at_z(bottom_05_xy, INNER_Z_MIN_MM)
    corner_06_07 = top_07[-1][:2]
    corner_04_05 = top_04[0][:2]
    vertical_06_07 = (
        (*corner_06_07, INNER_Z_MAX_MM),
        (*corner_06_07, INNER_Z_MIN_MM),
    )
    vertical_04_05 = (
        (*corner_04_05, INNER_Z_MIN_MM),
        (*corner_04_05, INNER_Z_MAX_MM),
    )

    def segment(
        name: str,
        faces: tuple[str, str],
        path: tuple[tuple[float, float, float], ...],
        joint: str,
    ) -> SeamSegment:
        return SeamSegment(name, faces, path[0], path[-1], joint, path)

    return (
        segment("top_04", ("top", "04"), top_04, "flush butt along rounded perimeter"),
        segment("top_07", ("top", "07"), top_07, "flush butt along rounded perimeter"),
        segment("06_07", ("06", "07"), vertical_06_07, "straight tangent-plane butt; rounded corner owned by upper shell"),
        segment("bottom_06", ("bottom", "06"), bottom_06, "flush butt along rounded perimeter"),
        segment("bottom_05", ("bottom", "05"), bottom_05, "flush butt along rounded perimeter"),
        segment("04_05", ("04", "05"), vertical_04_05, "straight tangent-plane butt; rounded corner owned by lower shell"),
    )


SEAM_PATH = _build_seam_path()


def _polygon_prism_z(points: tuple[tuple[float, float], ...], z0: float, z1: float) -> cq.Shape:
    return (
        cq.Workplane("XY")
        .polyline(points)
        .close()
        .extrude(z1 - z0)
        .translate((0.0, 0.0, z0))
        .val()
    )


def _profile_x(
    shape: str,
    width_y: float,
    height_z: float,
    depth_x: float,
    x0: float,
    center_y: float,
    center_z: float,
    corner_radius: float = 0.0,
    feature_width: float = 0.0,
    feature_height: float = 0.0,
) -> cq.Shape:
    workplane = cq.Workplane("YZ").center(center_y, center_z)
    if shape == "circle":
        return workplane.circle(width_y / 2.0).extrude(depth_x).translate((x0, 0.0, 0.0)).val()
    if shape == "roundrect":
        radius = min(corner_radius, width_y / 2.0, height_z / 2.0)
        sketch = cq.Sketch().rect(width_y, height_z).vertices().fillet(radius)
        return workplane.placeSketch(sketch).extrude(depth_x).translate((x0, 0.0, 0.0)).val()
    if shape == "case_hdmi_hex":
        half_w = width_y / 2.0
        half_h = height_z / 2.0
        half_top = feature_width / 2.0
        points = (
            (-half_top, +half_h),
            (+half_top, +half_h),
            (+half_w, +half_h - feature_height),
            (+half_w, -half_h),
            (-half_w, -half_h),
            (-half_w, +half_h - feature_height),
        )
        return (
            workplane.polyline(points)
            .close()
            .extrude(depth_x)
            .translate((x0, 0.0, 0.0))
            .val()
        )
    if shape == "rj45_main_plus_relief":
        radius = min(corner_radius, width_y / 2.0, height_z / 2.0)
        main = workplane.placeSketch(
            cq.Sketch().rect(width_y, height_z).vertices().fillet(radius)
        ).extrude(depth_x)
        relief_center_z = -height_z / 2.0 - feature_height / 2.0
        relief = (
            workplane.center(0.0, relief_center_z)
            .rect(feature_width, feature_height)
            .extrude(depth_x)
        )
        return main.union(relief).translate((x0, 0.0, 0.0)).val()
    if shape == "rectangle":
        return workplane.rect(width_y, height_z).extrude(depth_x).translate((x0, 0.0, 0.0)).val()
    raise ValueError(f"unsupported review profile: {shape}")


def make_aperture_cutter(aperture: PanelApertureReference) -> cq.Shape:
    x0 = OUTER_X_MIN_MM - 0.5 if aperture.face == "04" else INNER_X_MAX_MM - 0.5
    return _profile_x(
        aperture.shape,
        aperture.width_mm,
        aperture.height_mm,
        SIDE_WALL_T_MM + 1.0,
        x0,
        aperture.center_y_mm,
        aperture.center_z_mm,
        aperture.corner_radius_mm,
        aperture.feature_width_mm,
        aperture.feature_height_mm,
    )


def make_rounded_wall_ring(z0: float, z1: float) -> cq.Shape:
    outer_wall = rounded_plate_xy(
        OUTER_X_MM,
        OUTER_Y_MM,
        OUTER_PLAN_CORNER_R_MM,
        z1 - z0,
        z0,
    ).translate((OUTER_PLAN_CENTER_X_MM, OUTER_PLAN_CENTER_Y_MM, 0.0))
    inner_void = rounded_plate_xy(
        INNER_X_MAX_MM - INNER_X_MIN_MM,
        INNER_Y_MAX_MM - INNER_Y_MIN_MM,
        INNER_PLAN_CORNER_R_MM,
        z1 - z0 + 0.4,
        z0 - 0.2,
    ).translate((INNER_PLAN_CENTER_X_MM, INNER_PLAN_CENTER_Y_MM, 0.0))
    return outer_wall.cut(inner_void).val()


def make_face_solids() -> dict[str, cq.Shape]:
    top = (
        rounded_plate_xy(
            OUTER_X_MM,
            OUTER_Y_MM,
            OUTER_PLAN_CORNER_R_MM,
            TOP_PLATE_T_MM,
            INNER_Z_MAX_MM,
        )
        .translate((OUTER_PLAN_CENTER_X_MM, OUTER_PLAN_CENTER_Y_MM, 0.0))
        .cut(
            cylinder_z(
                FAN_INTAKE_D_MM,
                INNER_Z_MAX_MM - 0.2,
                OUTER_Z_MAX_MM + 0.2,
                *FAN_CENTER_XY_MM,
            )
        )
        .val()
    )
    bottom = rounded_plate_xy(
        OUTER_X_MM,
        OUTER_Y_MM,
        OUTER_PLAN_CORNER_R_MM,
        BOTTOM_PLATE_T_MM,
        OUTER_Z_MIN_MM,
    ).translate((OUTER_PLAN_CENTER_X_MM, OUTER_PLAN_CENTER_Y_MM, 0.0))
    for _, x, y in MOUNT_HOLES:
        bottom = bottom.cut(
            cylinder_z(
                LOWER_SCREW_CLEARANCE_D_MM,
                OUTER_Z_MIN_MM - 0.2,
                INNER_Z_MIN_MM + 0.2,
                x,
                y,
            )
        )

    rounded_wall_ring = make_rounded_wall_ring(OUTER_Z_MIN_MM, OUTER_Z_MAX_MM)

    # Intersect the common rounded wall ring with four disjoint ownership zones.
    # Face 06 owns both right-hand rounded arcs and face 04 owns both left-hand
    # rounded arcs.  The two cross-shell vertical seams therefore lie on the
    # straight 07/05 wall tangencies and never split a curved exterior surface.
    face_06 = rounded_wall_ring.intersect(_polygon_prism_z(
        (
            (SEAM_06_07_TANGENT_X_MM, OUTER_Y_MIN_MM),
            (OUTER_X_MAX_MM, OUTER_Y_MIN_MM),
            (OUTER_X_MAX_MM, OUTER_Y_MAX_MM),
            (SEAM_06_07_TANGENT_X_MM, OUTER_Y_MAX_MM),
        ),
        INNER_Z_MIN_MM,
        OUTER_Z_MAX_MM,
    ))
    face_05 = rounded_wall_ring.intersect(_polygon_prism_z(
        (
            (SEAM_04_05_TANGENT_X_MM, OUTER_Y_MIN_MM),
            (SEAM_06_07_TANGENT_X_MM, OUTER_Y_MIN_MM),
            (SEAM_06_07_TANGENT_X_MM, 0.0),
            (SEAM_04_05_TANGENT_X_MM, 0.0),
        ),
        INNER_Z_MIN_MM,
        OUTER_Z_MAX_MM,
    ))
    face_04 = rounded_wall_ring.intersect(_polygon_prism_z(
        (
            (OUTER_X_MIN_MM, OUTER_Y_MIN_MM),
            (SEAM_04_05_TANGENT_X_MM, OUTER_Y_MIN_MM),
            (SEAM_04_05_TANGENT_X_MM, OUTER_Y_MAX_MM),
            (OUTER_X_MIN_MM, OUTER_Y_MAX_MM),
        ),
        OUTER_Z_MIN_MM,
        INNER_Z_MAX_MM,
    ))
    face_07 = rounded_wall_ring.intersect(_polygon_prism_z(
        (
            (SEAM_04_05_TANGENT_X_MM, 0.0),
            (SEAM_06_07_TANGENT_X_MM, 0.0),
            (SEAM_06_07_TANGENT_X_MM, OUTER_Y_MAX_MM),
            (SEAM_04_05_TANGENT_X_MM, OUTER_Y_MAX_MM),
        ),
        OUTER_Z_MIN_MM,
        INNER_Z_MAX_MM,
    ))

    for aperture in FACE_APERTURES["06"]:
        face_06 = face_06.cut(make_aperture_cutter(aperture))
    for aperture in FACE_APERTURES["04"]:
        face_04 = face_04.cut(make_aperture_cutter(aperture))

    # This is a functional no-obstruction envelope, not a guessed final grille.
    fin_exhaust = _profile_x(
        "rectangle",
        FIN_EXHAUST_WIDTH_Y_MM,
        FIN_EXHAUST_HEIGHT_Z_MM,
        SIDE_WALL_T_MM + 1.0,
        OUTER_X_MIN_MM - 0.5,
        FIN_STACK_CENTER_Y_MM,
        FIN_EXHAUST_CENTER_Z_MM,
    )
    face_04 = face_04.cut(fin_exhaust)

    return {
        "top": top,
        "bottom": bottom.val(),
        "06": face_06,
        "05": face_05,
        "04": face_04,
        "07": face_07,
        "fin_exhaust_cutter": fin_exhaust,
    }


def make_upper_clamp_posts() -> cq.Shape:
    posts: list[cq.Shape | cq.Workplane] = []
    for _, x, y in MOUNT_HOLES:
        post = cylinder_z(CLAMP_POST_OD_MM, PCB_T_MM, INNER_Z_MAX_MM + 0.05, x, y)
        post = post.cut(
            cylinder_z(
                UPPER_THREAD_PILOT_D_MM,
                -0.2,
                INNER_Z_MAX_MM - 1.0,
                x,
                y,
            )
        )
        posts.append(post)
    return compound(posts)


def make_lower_clamp_posts() -> cq.Shape:
    posts: list[cq.Shape | cq.Workplane] = []
    for _, x, y in MOUNT_HOLES:
        post = cylinder_z(CLAMP_POST_OD_MM, OUTER_Z_MIN_MM, 0.0, x, y)
        post = post.cut(
            cylinder_z(
                LOWER_SCREW_CLEARANCE_D_MM,
                OUTER_Z_MIN_MM - 0.2,
                0.2,
                x,
                y,
            )
        )
        posts.append(post)
    return compound(posts)


def _make_review_rib_segment(
    segment: RibSegment,
    z0: float,
    height: float = REINFORCEMENT_RIB_HEIGHT_MM,
    width: float = REINFORCEMENT_RIB_WIDTH_MM,
) -> cq.Shape:
    x0, y0 = segment.start_xy_mm
    x1, y1 = segment.end_xy_mm
    length = math.hypot(x1 - x0, y1 - y0)
    angle = math.degrees(math.atan2(y1 - y0, x1 - x0))
    return (
        cq.Workplane("XY")
        .box(length, width, height, centered=(True, True, False))
        .rotate((0.0, 0.0, 0.0), (0.0, 0.0, 1.0), angle)
        .translate(((x0 + x1) / 2.0, (y0 + y1) / 2.0, z0))
        .val()
    )


def _make_review_rib_network(
    segments: tuple[RibSegment, ...],
    z0: float,
    hole_diameter: float,
) -> cq.Shape:
    parts = [_make_review_rib_segment(segment, z0) for segment in segments]
    result = parts[0]
    for part in parts[1:]:
        result = result.fuse(part)

    plan_mask = rounded_plate_xy(
        OUTER_X_MM,
        OUTER_Y_MM,
        OUTER_PLAN_CORNER_R_MM,
        REINFORCEMENT_RIB_HEIGHT_MM,
        z0,
    ).translate((OUTER_PLAN_CENTER_X_MM, OUTER_PLAN_CENTER_Y_MM, 0.0)).val()
    result = result.intersect(plan_mask)
    for _, x, y in MOUNT_HOLES:
        result = result.cut(
            cylinder_z(
                hole_diameter,
                z0 - 0.2,
                z0 + REINFORCEMENT_RIB_HEIGHT_MM + 0.2,
                x,
                y,
            ).val()
        )
    return result.clean()


def make_top_reinforcement_ribs() -> cq.Shape:
    return _make_review_rib_network(
        TOP_REINFORCEMENT_SEGMENTS,
        INNER_Z_MAX_MM - REINFORCEMENT_RIB_HEIGHT_MM,
        UPPER_THREAD_PILOT_D_MM,
    )


def make_bottom_reinforcement_ribs() -> cq.Shape:
    return _make_review_rib_network(
        BOTTOM_REINFORCEMENT_SEGMENTS,
        INNER_Z_MIN_MM,
        LOWER_SCREW_CLEARANCE_D_MM,
    )


def make_reinforcement_review_geometry() -> dict[str, cq.Shape | dict[str, cq.Shape]]:
    """Build the approved ribs and their independent collision targets."""

    top_z0 = INNER_Z_MAX_MM - REINFORCEMENT_RIB_HEIGHT_MM
    bottom_z0 = INNER_Z_MIN_MM
    top_ribs = make_top_reinforcement_ribs()
    bottom_ribs = make_bottom_reinforcement_ribs()

    motherboard = build_motherboard_geometry()
    dual_usb_references = tuple(
        reference
        for reference in FACE_04_CONNECTORS
        if reference.name in {"stack_usb_upper", "stack_usb_lower"}
    )
    dual_usb_parts = [make_connector(reference) for reference in dual_usb_references]
    dual_usb = compound(dual_usb_parts)

    low_connector_parts: dict[str, cq.Shape] = {}
    bottom_rib_top = bottom_z0 + REINFORCEMENT_RIB_HEIGHT_MM
    for reference in FACE_04_CONNECTORS:
        shape = make_connector(reference)
        if shape.BoundingBox().zmin <= bottom_rib_top + REINFORCEMENT_COMPONENT_CLEARANCE_MM:
            low_connector_parts[reference.name] = shape

    fan_x_values = [point[0] for point in FAN_SHELL_PROFILE_XY_MM]
    fan_y_values = [point[1] for point in FAN_SHELL_PROFILE_XY_MM]
    clearance = REINFORCEMENT_COMPONENT_CLEARANCE_MM
    fan_x0 = min(fan_x_values) - FAN_PROFILE_UNCERTAINTY_MM - clearance
    fan_x1 = max(fan_x_values) + FAN_PROFILE_UNCERTAINTY_MM + clearance
    fan_y0 = min(fan_y_values) - FAN_PROFILE_UNCERTAINTY_MM - clearance
    fan_y1 = max(fan_y_values) + FAN_PROFILE_UNCERTAINTY_MM + clearance
    envelope_z0 = top_z0 - 0.1
    envelope_h = REINFORCEMENT_RIB_HEIGHT_MM + 0.2
    fan_clearance_envelope = (
        cq.Workplane("XY")
        .box(fan_x1 - fan_x0, fan_y1 - fan_y0, envelope_h, centered=(True, True, False))
        .translate(((fan_x0 + fan_x1) / 2.0, (fan_y0 + fan_y1) / 2.0, envelope_z0))
        .val()
    )
    fin_clearance_envelope = (
        cq.Workplane("XY")
        .box(
            FIN_STACK_X_MM + 2.0 * clearance,
            FIN_STACK_Y_MM + 2.0 * clearance,
            envelope_h,
            centered=(True, True, False),
        )
        .translate((FIN_STACK_CENTER_X_MM, FIN_STACK_CENTER_Y_MM, envelope_z0))
        .val()
    )
    top_clearance_envelope = compound([fan_clearance_envelope, fin_clearance_envelope])

    usb_bounds = dual_usb.BoundingBox()
    bottom_usb_clearance_envelope = (
        cq.Workplane("XY")
        .box(
            usb_bounds.xlen + 2.0 * clearance,
            usb_bounds.ylen + 2.0 * clearance,
            REINFORCEMENT_RIB_HEIGHT_MM + 0.2,
            centered=(True, True, False),
        )
        .translate((
            (usb_bounds.xmin + usb_bounds.xmax) / 2.0,
            (usb_bounds.ymin + usb_bounds.ymax) / 2.0,
            bottom_z0 - 0.1,
        ))
        .val()
    )

    return {
        "top_ribs": top_ribs,
        "bottom_ribs": bottom_ribs,
        "cooling_keepout": motherboard["cooling_keepout"],
        "cooling_assembly": motherboard["cooling_assembly"],
        "motherboard": motherboard["motherboard_assembly"],
        "underside_keepouts": motherboard["underside_keepouts"],
        "dual_usb": dual_usb,
        "low_connectors": low_connector_parts,
        "top_clearance_envelope": top_clearance_envelope,
        "bottom_usb_clearance_envelope": bottom_usb_clearance_envelope,
    }


def _fuse_review_part(parts: tuple[cq.Shape, ...]) -> cq.Shape:
    result = parts[0]
    for part in parts[1:]:
        result = result.fuse(part)
    return result.clean()


def build_review_geometry() -> dict[str, cq.Shape]:
    faces = make_face_solids()
    upper_posts = make_upper_clamp_posts()
    lower_posts = make_lower_clamp_posts()
    top_reinforcement_ribs = make_top_reinforcement_ribs()
    bottom_reinforcement_ribs = make_bottom_reinforcement_ribs()
    # These are integral three-face parts, not assemblies of coincident visual
    # shells.  Boolean fusion removes internal/copied faces that otherwise cause
    # transparent preview z-fighting and can look like a physical corner gap.
    upper = _fuse_review_part((
        faces["top"],
        faces["06"],
        faces["05"],
        upper_posts,
        top_reinforcement_ribs,
    ))
    lower = _fuse_review_part((
        faces["bottom"],
        faces["04"],
        faces["07"],
        lower_posts,
        bottom_reinforcement_ribs,
    ))
    motherboard_geometry = build_motherboard_geometry()
    return {
        **faces,
        "upper_posts": upper_posts,
        "lower_posts": lower_posts,
        "top_reinforcement_ribs": top_reinforcement_ribs,
        "bottom_reinforcement_ribs": bottom_reinforcement_ribs,
        "upper_shell_review": upper,
        "lower_shell_review": lower,
        "motherboard": motherboard_geometry["motherboard_assembly"],
        "motherboard_pcb": motherboard_geometry["pcb"],
        "motherboard_connectors": motherboard_geometry["connectors"],
        "motherboard_cooling": motherboard_geometry["cooling_assembly"],
        "motherboard_underside_keepouts": motherboard_geometry["underside_keepouts"],
    }


def _rounded_rect_perimeter(
    width: float, height: float, radius: float, samples_per_corner: int = 40
) -> list[tuple[float, float]]:
    radius = min(radius, width / 2.0, height / 2.0)
    if radius <= 0.0:
        return [
            (-width / 2.0, -height / 2.0),
            (+width / 2.0, -height / 2.0),
            (+width / 2.0, +height / 2.0),
            (-width / 2.0, +height / 2.0),
        ]
    points: list[tuple[float, float]] = []
    centers = (
        (+width / 2.0 - radius, +height / 2.0 - radius, 0.0),
        (-width / 2.0 + radius, +height / 2.0 - radius, 90.0),
        (-width / 2.0 + radius, -height / 2.0 + radius, 180.0),
        (+width / 2.0 - radius, -height / 2.0 + radius, 270.0),
    )
    for center_x, center_y, start_deg in centers:
        for index in range(samples_per_corner + 1):
            angle = math.radians(start_deg + index * 90.0 / samples_per_corner)
            points.append((center_x + radius * math.cos(angle), center_y + radius * math.sin(angle)))
    return points


def _target_perimeter(target: CoverageTarget) -> list[tuple[float, float]]:
    if target.shape == "circle":
        return [
            (
                target.width_mm / 2.0 * math.cos(2.0 * math.pi * index / 360.0),
                target.height_mm / 2.0 * math.sin(2.0 * math.pi * index / 360.0),
            )
            for index in range(360)
        ]
    if target.shape == "roundrect":
        return _rounded_rect_perimeter(
            target.width_mm,
            target.height_mm,
            target.corner_radius_mm,
        )
    if target.shape == "rectangle":
        return _rounded_rect_perimeter(target.width_mm, target.height_mm, 0.0)
    raise ValueError(target.shape)


def _point_segment_distance(
    point: tuple[float, float], start: tuple[float, float], end: tuple[float, float]
) -> float:
    px, py = point
    sx, sy = start
    ex, ey = end
    dx = ex - sx
    dy = ey - sy
    if dx == 0.0 and dy == 0.0:
        return math.hypot(px - sx, py - sy)
    t = max(0.0, min(1.0, ((px - sx) * dx + (py - sy) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (sx + t * dx), py - (sy + t * dy))


def _polygon_signed_clearance(point: tuple[float, float], polygon: list[tuple[float, float]]) -> float:
    x, y = point
    inside = False
    for index, start in enumerate(polygon):
        end = polygon[(index + 1) % len(polygon)]
        if ((start[1] > y) != (end[1] > y)) and (
            x < (end[0] - start[0]) * (y - start[1]) / (end[1] - start[1]) + start[0]
        ):
            inside = not inside
    distance = min(
        _point_segment_distance(point, polygon[index], polygon[(index + 1) % len(polygon)])
        for index in range(len(polygon))
    )
    return distance if inside or distance <= 1e-9 else -distance


def _roundrect_signed_clearance(
    point: tuple[float, float], width: float, height: float, radius: float
) -> float:
    radius = min(radius, width / 2.0, height / 2.0)
    qx = abs(point[0]) - (width / 2.0 - radius)
    qy = abs(point[1]) - (height / 2.0 - radius)
    signed_distance = (
        math.hypot(max(qx, 0.0), max(qy, 0.0))
        + min(max(qx, qy), 0.0)
        - radius
    )
    return -signed_distance


def aperture_signed_clearance(
    aperture: PanelApertureReference, point_yz_mm: tuple[float, float]
) -> float:
    local = (
        point_yz_mm[0] - aperture.center_y_mm,
        point_yz_mm[1] - aperture.center_z_mm,
    )
    if aperture.shape == "circle":
        return aperture.width_mm / 2.0 - math.hypot(*local)
    if aperture.shape == "roundrect":
        return _roundrect_signed_clearance(
            local,
            aperture.width_mm,
            aperture.height_mm,
            aperture.corner_radius_mm,
        )
    if aperture.shape == "case_hdmi_hex":
        half_w = aperture.width_mm / 2.0
        half_h = aperture.height_mm / 2.0
        half_top = aperture.feature_width_mm / 2.0
        polygon = [
            (-half_top, +half_h),
            (+half_top, +half_h),
            (+half_w, +half_h - aperture.feature_height_mm),
            (+half_w, -half_h),
            (-half_w, -half_h),
            (-half_w, +half_h - aperture.feature_height_mm),
        ]
        return _polygon_signed_clearance(local, polygon)
    if aperture.shape == "rj45_main_plus_relief":
        main = _roundrect_signed_clearance(
            local,
            aperture.width_mm,
            aperture.height_mm,
            aperture.corner_radius_mm,
        )
        relief_center_z = -aperture.height_mm / 2.0 - aperture.feature_height_mm / 2.0
        relief = _roundrect_signed_clearance(
            (local[0], local[1] - relief_center_z),
            aperture.feature_width_mm,
            aperture.feature_height_mm,
            0.0,
        )
        return max(main, relief)
    if aperture.shape == "rectangle":
        return _roundrect_signed_clearance(local, aperture.width_mm, aperture.height_mm, 0.0)
    raise ValueError(aperture.shape)


def coverage_targets() -> tuple[tuple[PanelApertureReference, tuple[CoverageTarget, ...]], ...]:
    connectors = {connector.name: connector for connector in ALL_CONNECTORS}
    groups: list[tuple[PanelApertureReference, tuple[CoverageTarget, ...]]] = []
    for face in ("04", "06"):
        for aperture in FACE_APERTURES[face]:
            if aperture.name in {"hdmi_1", "hdmi_3"}:
                # The 14 x 4.8 mm rounded rectangle in the motherboard model is
                # only a generic hidden-body/nose placeholder.  It is not a
                # measured HDMI front profile and must not be compared against,
                # or overrule, the confirmed original-case hex aperture.
                groups.append((aperture, ()))
                continue
            if aperture.name == "stack_dual_usb":
                names = ("stack_usb_upper", "stack_usb_lower")
            elif aperture.name == "power_switch":
                groups.append(
                    (
                        aperture,
                        (
                            CoverageTarget(
                                "original_button_through_body",
                                "06",
                                aperture.name,
                                SWITCH_CENTER_Y_MM,
                                SWITCH_CENTER_Z_MM,
                                "circle",
                                ORIGINAL_BUTTON_THROUGH_D_MM,
                                ORIGINAL_BUTTON_THROUGH_D_MM,
                                0.0,
                                "user-measured original button through-body; board switch remains behind the panel",
                            ),
                        ),
                    )
                )
                continue
            else:
                names = (aperture.name,)
            targets: list[CoverageTarget] = []
            for name in names:
                connector = connectors[name]
                targets.append(
                    CoverageTarget(
                        connector.name,
                        connector.face,
                        aperture.name,
                        connector.center_y_mm,
                        connector.body_center_z_mm + connector.nose_center_z_offset_mm,
                        connector.nose_shape,
                        connector.nose_width_mm,
                        connector.nose_height_mm,
                        connector.nose_corner_radius_mm,
                        connector.confidence,
                    )
                )
            groups.append((aperture, tuple(targets)))

    fan_aperture = PanelApertureReference(
        "fan_intake",
        "top",
        FAN_CENTER_XY_MM[1],
        FAN_CENTER_XY_MM[0],
        "circle",
        FAN_INTAKE_D_MM,
        FAN_INTAKE_D_MM,
        "measured fan inlet; no added clearance",
        "PCB-aligned fan center",
    )
    fan_target = CoverageTarget(
        "fan_inlet",
        "top",
        "fan_intake",
        FAN_CENTER_XY_MM[1],
        FAN_CENTER_XY_MM[0],
        "circle",
        FAN_INLET_D_MM,
        FAN_INLET_D_MM,
        0.0,
        "measured fan inlet",
    )
    exhaust_aperture = PanelApertureReference(
        "fin_exhaust",
        "04",
        FIN_STACK_CENTER_Y_MM,
        FIN_EXHAUST_CENTER_Z_MM,
        "rectangle",
        FIN_EXHAUST_WIDTH_Y_MM,
        FIN_EXHAUST_HEIGHT_Z_MM,
        "functional no-obstruction envelope",
        "fin-stack projection",
    )
    exhaust_target = CoverageTarget(
        "fin_stack_outlet",
        "04",
        "fin_exhaust",
        FIN_STACK_CENTER_Y_MM,
        FIN_EXHAUST_CENTER_Z_MM,
        "rectangle",
        FIN_STACK_Y_MM,
        FIN_EXHAUST_HEIGHT_Z_MM,
        0.0,
        "current fin-stack projection; grille segmentation pending",
    )
    groups.extend(((fan_aperture, (fan_target,)), (exhaust_aperture, (exhaust_target,))))
    return tuple(groups)


def build_coverage_report() -> list[dict[str, object]]:
    report: list[dict[str, object]] = []
    for aperture, targets in coverage_targets():
        target_results: list[dict[str, object]] = []
        if not targets:
            report.append(
                {
                    "aperture": asdict(aperture),
                    "targets": [],
                    "minimum_nominal_clearance_mm": None,
                    "geometric_coverage_pass": None,
                    "review_status": (
                        "authoritative original-case hex aperture retained; "
                        "exact HDMI connector-front profile is not modeled, so proxy comparison is omitted"
                    ),
                }
            )
            continue
        minimum = math.inf
        for target in targets:
            clearances = []
            for local_y, local_z in _target_perimeter(target):
                point = (target.center_y_mm + local_y, target.center_z_mm + local_z)
                clearances.append(aperture_signed_clearance(aperture, point))
            target_minimum = min(clearances)
            minimum = min(minimum, target_minimum)
            target_results.append(
                {
                    **asdict(target),
                    "minimum_nominal_clearance_mm": round(target_minimum, 3),
                    "covered": target_minimum >= -0.01,
                }
            )
        if aperture.name == "power_switch":
            review_status = "nominal 9.4 hole covers measured 9.2 button body; switch actuator stays behind the panel and travel remains pending"
        elif aperture.name == "headphone":
            review_status = "geometry passes against provisional connector proxy; aperture diameter pending physical check"
        elif minimum < -0.01:
            review_status = "FAIL against current connector proxy; do not change measured aperture without review"
        elif minimum <= 0.01:
            review_status = "exact functional boundary; no manufacturing clearance added by requirement"
        else:
            review_status = "nominal coverage pass; no manufacturing clearance added"
        report.append(
            {
                "aperture": asdict(aperture),
                "targets": target_results,
                "minimum_nominal_clearance_mm": round(minimum, 3),
                "geometric_coverage_pass": minimum >= -0.01,
                "review_status": review_status,
            }
        )
    return report


def structure_definition(
    *,
    output_stage: str = "structure-review",
    enclosure_step_stl_generated: bool = False,
) -> dict[str, object]:
    if output_stage == "v2-prototype":
        status = "V2 fit-check prototype STEP/STL generated; provisional parameters remain"
    else:
        status = "structure-definition review; enclosure STEP/STL not yet generated"
    return {
        "status": status,
        "output_stage": output_stage,
        "coordinate_frame": "+X=06, -X=04, +Y=07, -Y=05, +Z=fan side; PCB bottom Z=0",
        "part_definition": {
            "new_parts": ["upper_shell", "lower_shell"],
            "reused_part": "original round power button",
            "upper_shell_faces": ["top", "06", "05"],
            "lower_shell_faces": ["bottom", "04", "07"],
        },
        "face_ownership": FACE_OWNERSHIP,
        "parameters": [asdict(parameter) for parameter in REVIEW_PARAMETERS],
        "outer_envelope_mm": {
            "x_04_06": OUTER_X_MM,
            "y_05_07": OUTER_Y_MM,
            "z_bottom_top": OUTER_Z_MM,
            "bounds": {
                "x": [OUTER_X_MIN_MM, OUTER_X_MAX_MM],
                "y": [OUTER_Y_MIN_MM, OUTER_Y_MAX_MM],
                "z": [OUTER_Z_MIN_MM, OUTER_Z_MAX_MM],
            },
            "plan_corner_radii": {
                "outer_xy_mm": OUTER_PLAN_CORNER_R_MM,
                "inner_cavity_xy_mm": INNER_PLAN_CORNER_R_MM,
                "outer_status": "derived as inner radius + side-wall thickness",
                "inner_status": "provisional photo reconstruction of motherboard corner",
            },
        },
        "assembly_sequence": list(ASSEMBLY_SEQUENCE),
        "clamp_chain": {
            "axes": [
                {"name": name, "x_mm": x, "y_mm": y}
                for name, x, y in MOUNT_HOLES
            ],
            "load_path": "bottom fastener -> lower sleeve -> PCB underside -> PCB -> upper post -> upper top",
            "assembly_alignment": "two diagonal fastener shanks/tips through the original PCB holes; no printed locator nose",
            "additional_enclosure_fastener_axes": 0,
        },
        "seam": {
            "path_type": "one closed six-segment boundary",
            "continuous_tongue_or_groove": False,
            "nominal_gap_mm": NOMINAL_SEAM_GAP_MM,
            "manufacturing_clearance_applied": False,
            "segments": [asdict(segment) for segment in SEAM_PATH],
        },
        "corner_ownership": {
            "06_07_rounded_corner": "upper shell owns the complete rounded arc; seam is on the straight +Y tangency",
            "04_05_rounded_corner": "lower shell owns the complete rounded arc; seam is on the straight -Y tangency",
            "curved_surface_split": False,
            "tangent_seam_x_mm": {
                "06_07": SEAM_06_07_TANGENT_X_MM,
                "04_05": SEAM_04_05_TANGENT_X_MM,
            },
        },
        "pcb_plan_fit": {
            "nominal_clearance_mm": {
                "04": PCB_CLEARANCE_04_MM,
                "06": PCB_CLEARANCE_06_MM,
                "05": PCB_CLEARANCE_05_MM,
                "07": PCB_CLEARANCE_07_MM,
            },
            "inner_width_x_mm": INNER_X_MAX_MM - INNER_X_MIN_MM,
            "inner_width_y_mm": INNER_Y_MAX_MM - INNER_Y_MIN_MM,
            "inner_corner_radius_mm": INNER_PLAN_CORNER_R_MM,
            "rule": "faces 04/06 are outward-offset continuous planar walls; all four side faces are non-locating, and the four PCB holes provide primary XY location",
        },
        "side_wall_construction": {
            "04": "one continuous planar wall solid after subtracting reviewed interface apertures and fin exhaust",
            "06": "one continuous planar wall solid after subtracting reviewed USB and power-button apertures",
            "05": "closed wall; no side-facing connector aperture",
            "07": "closed wall; no side-facing connector aperture",
            "rule": "wall continuity is a manufacturing requirement; an interface projection changes its through-opening, never the PCB cavity datum",
        },
        "internal_reinforcement": {
            "status": REINFORCEMENT_REVIEW_STATUS,
            "base_plate_thickness_mm": {
                "top": TOP_PLATE_T_MM,
                "bottom": BOTTOM_PLATE_T_MM,
            },
            "rib_height_mm": REINFORCEMENT_RIB_HEIGHT_MM,
            "rib_width_mm": REINFORCEMENT_RIB_WIDTH_MM,
            "upper_path_rule": "bypass the complete blower and fin-stack XY envelopes",
            "lower_path_rule": "bypass the deepest stacked dual USB and clear the complete motherboard reference",
            "top_segments": [asdict(segment) for segment in TOP_REINFORCEMENT_SEGMENTS],
            "bottom_segments": [asdict(segment) for segment in BOTTOM_REINFORCEMENT_SEGMENTS],
        },
        "openings": {
            "04": [asdict(item) for item in FACE_APERTURES["04"]]
            + [
                {
                    "name": "fin_exhaust",
                    "shape": "continuous functional envelope; final grille pending",
                    "center_y_mm": FIN_STACK_CENTER_Y_MM,
                    "center_z_mm": FIN_EXHAUST_CENTER_Z_MM,
                    "width_mm": FIN_EXHAUST_WIDTH_Y_MM,
                    "height_mm": FIN_EXHAUST_HEIGHT_Z_MM,
                }
            ],
            "06": [asdict(item) for item in FACE_APERTURES["06"]],
            "05": "closed",
            "07": "closed",
            "top": {
                "name": "fan_intake",
                "center_x_mm": FAN_CENTER_XY_MM[0],
                "center_y_mm": FAN_CENTER_XY_MM[1],
                "diameter_mm": FAN_INTAKE_D_MM,
            },
            "bottom": "four fastener passages only, coincident with the original PCB axes",
        },
        "explicitly_unresolved": [
            "04/06 allocation is provisionally 2.0/1.0 mm from USB projections",
            "exact photo-derived contour of the local PCB step beside the face-06 switch; the current full PCB envelope is conservative for wall clearance",
            "physical confirmation of the provisional PCB R4 corner reference",
            "additional print/process compensation, if later required, must remain separate from the reviewed structural clearance",
            "M3-class screw head, insert and thread form",
            "reused external button cap geometry and effective travel",
            "headphone aperture physical diameter confirmation",
            "exact HDMI connector-front profile; generic motherboard proxy is excluded from aperture coverage",
            "04 fin-exhaust grille segmentation inside the no-obstruction envelope",
        ],
        "enclosure_step_stl_generated": enclosure_step_stl_generated,
    }
