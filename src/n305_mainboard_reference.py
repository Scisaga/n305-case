"""Parametric N305 motherboard reference in the project coordinate system.

This is a review model for enclosure design, not vendor CAD.  Measured board
dimensions, mounting holes, overall Z stack and PCB-aligned interface centers
are authoritative.  Hidden connector-body and cooling-detail geometry is a
documented conservative reconstruction.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import cadquery as cq

from n305_panel_reference import FACE_APERTURES, PCB_EDGE_SPAN_MM, PCB_THICKNESS_MM


PCB_X_MM = 100.0
PCB_Y_MM = PCB_EDGE_SPAN_MM
PCB_T_MM = PCB_THICKNESS_MM
PCB_CORNER_R_MM = 4.0
PCB_BOTTOM_Z_MM = 0.0
PCB_TOP_Z_MM = PCB_T_MM

PCB_BOTTOM_TO_LOWEST_MM = 10.25
PCB_TOP_TO_FAN_TOP_MM = 13.8
LOWEST_Z_MM = -PCB_BOTTOM_TO_LOWEST_MM
FAN_TOP_Z_MM = PCB_TOP_Z_MM + PCB_TOP_TO_FAN_TOP_MM
BARE_ASSEMBLY_Z_MM = FAN_TOP_Z_MM - LOWEST_Z_MM

MOUNT_HOLE_D_MM = 3.2
MOUNT_HOLE_POSITION_UNCERTAINTY_MM = 0.35
MOUNT_HOLES = (
    ("07_06", +45.387, +48.561),
    ("07_04", -44.982, +48.430),
    ("05_06", +44.895, -49.020),
    ("05_04", -45.107, -48.959),
)

# Photos 01/02 measure the 100.0 x 105.5 mm PCB plan, not a symmetric
# connector-front envelope.  Connector projection is therefore stored per
# reference instead of being reconstructed by splitting one total span.
# User rough measurements establish the two maxima currently needed by the
# enclosure review.  Other 04 noses remain an explicit visual proxy bounded by
# the 2.0 mm maximum; they must not be mistaken for individual measurements.
FACE_04_OTHER_PROJECTION_MM = 1.0
FACE_04_MAX_PROJECTION_MM = 2.0
FACE_06_USB_PROJECTION_MM = 1.0

FAN_CENTER_XY_MM = (-0.2, -3.45)
FAN_INLET_D_MM = 33.5
# PCB-rectified outline traced from photo 01.  It records the asymmetric
# volute and 04-facing outlet; estimated plan uncertainty is +/-1.0 mm.
FAN_SHELL_PROFILE_XY_MM = (
    (-29.15, +16.50),
    (-24.61, +16.50),
    (-20.06, +13.13),
    (-12.26, +17.40),
    (-2.20, +19.84),
    (+7.53, +18.91),
    (+16.28, +14.62),
    (+22.44, +7.29),
    (+25.35, -2.18),
    (+24.70, -11.96),
    (+20.80, -20.51),
    (+14.64, -27.23),
    (+8.80, -32.43),
    (+5.23, -33.95),
    (-29.18, -33.96),
)
FAN_PROFILE_UNCERTAINTY_MM = 1.0
FAN_HUB_D_MM = 20.5
FAN_BLADE_COUNT = 32
FIN_STACK_X_MM = 22.0
FIN_STACK_Y_MM = 84.0
# The 04-facing fin edge is flush with the PCB edge at X=-50.0.  With the
# existing 22 mm reconstructed span the stack therefore occupies -50..-28.
FIN_STACK_CENTER_X_MM = -PCB_X_MM / 2.0 + FIN_STACK_X_MM / 2.0
FIN_STACK_CENTER_Y_MM = 0.0

COOLING_DECK_BOTTOM_Z_MM = 9.55
COOLING_DECK_T_MM = 0.95
# 05 side measurement constrains the black blower housing itself to the fan-side
# maximum.  Do not reserve the measured top plane for an unsupported top bracket.
COOLING_SHELL_TOP_Z_MM = FAN_TOP_Z_MM
COOLING_FIN_BOTTOM_Z_MM = 7.9
COOLING_FIN_PITCH_MM = 3.0
COOLING_FIN_T_MM = 0.7


@dataclass(frozen=True)
class ConnectorReference:
    name: str
    face: str
    center_y_mm: float
    body_center_z_mm: float
    nose_shape: str
    nose_width_mm: float
    nose_height_mm: float
    body_width_mm: float
    body_height_mm: float
    body_depth_mm: float
    nose_center_z_offset_mm: float = 0.0
    nose_corner_radius_mm: float = 0.7
    confidence: str = "photo-estimated body; PCB-aligned center"
    front_projection_mm: float = 0.0
    projection_confidence: str = "unresolved"


def _aperture(face: str, name: str):
    return next(item for item in FACE_APERTURES[face] if item.name == name)


FACE_04_CONNECTORS = (
    ConnectorReference("dc", "04", _aperture("04", "dc").center_y_mm, -4.33, "circle", 5.5, 5.5, 10.5, 10.5, 13.0, front_projection_mm=FACE_04_OTHER_PROJECTION_MM, projection_confidence="provisional slight projection; bounded by user rough 2.0 mm maximum"),
    ConnectorReference("hdmi_1", "04", _aperture("04", "hdmi_1").center_y_mm, -5.02, "roundrect", 14.0, 4.8, 15.0, 6.4, 12.0, nose_corner_radius_mm=0.6, front_projection_mm=FACE_04_OTHER_PROJECTION_MM, projection_confidence="provisional slight projection; bounded by user rough 2.0 mm maximum"),
    ConnectorReference("headphone", "04", _aperture("04", "headphone").center_y_mm, +3.57, "circle", 5.0, 5.0, 8.0, 8.0, 11.0, front_projection_mm=FACE_04_OTHER_PROJECTION_MM, projection_confidence="provisional slight projection; bounded by user rough 2.0 mm maximum"),
    ConnectorReference("rj45", "04", _aperture("04", "rj45").center_y_mm, -3.55, "roundrect", 14.5, 8.3, 16.5, 13.5, 20.0, +0.85, 0.8, front_projection_mm=FACE_04_OTHER_PROJECTION_MM, projection_confidence="provisional slight projection; bounded by user rough 2.0 mm maximum"),
    ConnectorReference("stack_usb_upper", "04", _aperture("04", "stack_dual_usb").center_y_mm, +0.10, "roundrect", 12.0, 4.6, 14.0, 6.5, 16.0, nose_corner_radius_mm=0.6, front_projection_mm=FACE_04_MAX_PROJECTION_MM, projection_confidence="user rough measurement: about 2.0 mm; maximum on face 04"),
    ConnectorReference("stack_usb_lower", "04", _aperture("04", "stack_dual_usb").center_y_mm, -7.04, "roundrect", 12.0, 4.6, 14.0, 6.5, 16.0, nose_corner_radius_mm=0.6, front_projection_mm=FACE_04_MAX_PROJECTION_MM, projection_confidence="user rough measurement: about 2.0 mm; maximum on face 04"),
    ConnectorReference("hdmi_3", "04", _aperture("04", "hdmi_3").center_y_mm, -5.27, "roundrect", 14.0, 4.8, 15.0, 6.4, 12.0, nose_corner_radius_mm=0.6, front_projection_mm=FACE_04_OTHER_PROJECTION_MM, projection_confidence="provisional slight projection; bounded by user rough 2.0 mm maximum"),
)

FACE_06_CONNECTORS = (
    ConnectorReference("usb_05", "06", _aperture("06", "usb_05").center_y_mm, _aperture("06", "usb_05").center_z_mm, "roundrect", 12.0, 4.6, 14.0, 6.5, 16.0, nose_corner_radius_mm=0.6, front_projection_mm=FACE_06_USB_PROJECTION_MM, projection_confidence="user rough measurement: about 1.0 mm"),
    ConnectorReference("usb_07", "06", _aperture("06", "usb_07").center_y_mm, _aperture("06", "usb_07").center_z_mm, "roundrect", 12.0, 4.6, 14.0, 6.5, 16.0, nose_corner_radius_mm=0.6, front_projection_mm=FACE_06_USB_PROJECTION_MM, projection_confidence="user rough measurement: about 1.0 mm"),
)

ALL_CONNECTORS = FACE_04_CONNECTORS + FACE_06_CONNECTORS

SWITCH_CENTER_Y_MM = _aperture("06", "power_switch").center_y_mm
SWITCH_CENTER_Z_MM = _aperture("06", "power_switch").center_z_mm
SWITCH_BODY_W_MM = 4.5
SWITCH_BODY_H_MM = 4.5
SWITCH_BODY_DEPTH_MM = 5.0
SWITCH_ACTUATOR_D_MM = 1.8
SWITCH_ACTUATOR_PROJECTION_MM = 0.7
# Photo 03 shows the USB metal fronts as the outer 06-face datum.  The switch
# contact is about 1.2 mm farther inward, and the adjacent PCB outline steps
# inward again.  This plan-view estimate is provisional (+/-0.4 mm), but its
# ordering is reliable: USB front -> panel datum -> switch contact -> local PCB.
# It replaces the invalid proxy that placed the switch actuator inside the wall
# opening by measuring it from a fictitious straight X=50 PCB edge.
SWITCH_RECESS_BEHIND_USB_FRONT_MM = 1.2
SWITCH_PLAN_POSITION_UNCERTAINTY_MM = 0.4
SWITCH_ACTUATOR_TIP_X_MM = (
    PCB_X_MM / 2.0
    + FACE_06_USB_PROJECTION_MM
    - SWITCH_RECESS_BEHIND_USB_FRONT_MM
)
SWITCH_FACE_X_MM = SWITCH_ACTUATOR_TIP_X_MM - SWITCH_ACTUATOR_PROJECTION_MM


def compound(parts: list[cq.Workplane | cq.Shape]) -> cq.Shape:
    shapes: list[cq.Shape] = []
    for part in parts:
        shape = part.val() if isinstance(part, cq.Workplane) else part
        if isinstance(shape, cq.Compound):
            shapes.extend(shape.Solids())
        else:
            shapes.append(shape)
    return cq.Compound.makeCompound(shapes)


def rounded_plate_xy(width: float, depth: float, radius: float, height: float, z0: float) -> cq.Workplane:
    sketch = cq.Sketch().rect(width, depth).vertices().fillet(radius)
    return cq.Workplane("XY").placeSketch(sketch).extrude(height).translate((0.0, 0.0, z0))


def polygon_plate_xy(
    points: tuple[tuple[float, float], ...], height: float, z0: float
) -> cq.Workplane:
    return (
        cq.Workplane("XY")
        .polyline(points)
        .close()
        .extrude(height)
        .translate((0.0, 0.0, z0))
    )


def fan_shell_plate_xy(height: float, z0: float) -> cq.Workplane:
    """Extrude the traced outlet corners and smooth photographed volute arc."""
    points = FAN_SHELL_PROFILE_XY_MM
    return (
        cq.Workplane("XY")
        .moveTo(*points[0])
        .lineTo(*points[1])
        .lineTo(*points[2])
        .spline(list(points[3:14]), includeCurrent=True)
        .lineTo(*points[14])
        .close()
        .extrude(height)
        .translate((0.0, 0.0, z0))
    )


def cylinder_z(diameter: float, z0: float, z1: float, x: float, y: float) -> cq.Workplane:
    return (
        cq.Workplane("XY")
        .center(x, y)
        .circle(diameter / 2.0)
        .extrude(z1 - z0)
        .translate((0.0, 0.0, z0))
    )


def box_x(depth: float, width_y: float, height_z: float, x0: float, center_y: float, center_z: float) -> cq.Workplane:
    return (
        cq.Workplane("XY")
        .box(depth, width_y, height_z, centered=(False, True, True))
        .translate((x0, center_y, center_z))
    )


def profile_x(
    shape: str,
    width_y: float,
    height_z: float,
    depth_x: float,
    x0: float,
    center_y: float,
    center_z: float,
    corner_radius: float = 0.7,
) -> cq.Workplane:
    workplane = cq.Workplane("YZ").center(center_y, center_z)
    if shape == "circle":
        return workplane.circle(width_y / 2.0).extrude(depth_x).translate((x0, 0.0, 0.0))
    radius = min(corner_radius, width_y / 4.0, height_z / 4.0)
    sketch = cq.Sketch().rect(width_y, height_z).vertices().fillet(radius)
    return workplane.placeSketch(sketch).extrude(depth_x).translate((x0, 0.0, 0.0))


def make_pcb() -> cq.Shape:
    pcb = rounded_plate_xy(PCB_X_MM, PCB_Y_MM, PCB_CORNER_R_MM, PCB_T_MM, PCB_BOTTOM_Z_MM)
    for _, x, y in MOUNT_HOLES:
        pcb = pcb.cut(cylinder_z(MOUNT_HOLE_D_MM, -0.2, PCB_T_MM + 0.2, x, y))
    return pcb.val()


def make_connector(reference: ConnectorReference) -> cq.Shape:
    front_x = (
        -PCB_X_MM / 2.0 - reference.front_projection_mm
        if reference.face == "04"
        else +PCB_X_MM / 2.0 + reference.front_projection_mm
    )
    if reference.face == "04":
        body_x0 = front_x
        nose_x0 = front_x
    else:
        body_x0 = front_x - reference.body_depth_mm
        nose_x0 = front_x - 2.0
    body = box_x(
        reference.body_depth_mm,
        reference.body_width_mm,
        reference.body_height_mm,
        body_x0,
        reference.center_y_mm,
        reference.body_center_z_mm,
    )
    nose = profile_x(
        reference.nose_shape,
        reference.nose_width_mm,
        reference.nose_height_mm,
        2.0,
        nose_x0,
        reference.center_y_mm,
        reference.body_center_z_mm + reference.nose_center_z_offset_mm,
        reference.nose_corner_radius_mm,
    )
    return body.union(nose).val()


def make_board_switch() -> cq.Shape:
    body = box_x(
        SWITCH_BODY_DEPTH_MM,
        SWITCH_BODY_W_MM,
        SWITCH_BODY_H_MM,
        SWITCH_FACE_X_MM - SWITCH_BODY_DEPTH_MM,
        SWITCH_CENTER_Y_MM,
        SWITCH_CENTER_Z_MM,
    )
    actuator = profile_x(
        "circle",
        SWITCH_ACTUATOR_D_MM,
        SWITCH_ACTUATOR_D_MM,
        SWITCH_ACTUATOR_PROJECTION_MM,
        SWITCH_FACE_X_MM,
        SWITCH_CENTER_Y_MM,
        SWITCH_CENTER_Z_MM,
    )
    return body.union(actuator).val()


def make_connectors() -> cq.Shape:
    return compound([make_connector(item) for item in ALL_CONNECTORS])


def make_cold_plate_support() -> cq.Shape:
    """Conservative connected support below the photographed blower.

    Photo 01 does not support four exposed cylindrical fan feet.  The physical
    reference therefore uses a cold plate and central riser, both hidden below
    the fan deck, while preserving the measured PCB-to-fan Z stack.
    """
    cold_plate = (
        rounded_plate_xy(28.0, 26.0, 4.0, 2.8, PCB_TOP_Z_MM)
        .translate((-8.5, +4.5, 0.0))
    )
    riser_z0 = PCB_TOP_Z_MM + 2.65
    riser = (
        rounded_plate_xy(
            18.0,
            18.0,
            3.0,
            COOLING_DECK_BOTTOM_Z_MM - riser_z0 + 0.10,
            riser_z0,
        )
        .translate((-8.5, +4.5, 0.0))
    )
    return cold_plate.union(riser).val()


def make_cooling_deck() -> cq.Shape:
    return fan_shell_plate_xy(COOLING_DECK_T_MM, COOLING_DECK_BOTTOM_Z_MM).val()


def make_blower_shell() -> cq.Shape:
    fan_x, fan_y = FAN_CENTER_XY_MM
    blower_bottom = COOLING_DECK_BOTTOM_Z_MM + COOLING_DECK_T_MM - 0.10
    shell = fan_shell_plate_xy(
        COOLING_SHELL_TOP_Z_MM - blower_bottom,
        blower_bottom,
    )
    inlet = cylinder_z(
        FAN_INLET_D_MM,
        blower_bottom - 0.2,
        COOLING_SHELL_TOP_Z_MM + 0.2,
        fan_x,
        fan_y,
    )
    return shell.cut(inlet).val()


def make_fan_rotor() -> cq.Shape:
    fan_x, fan_y = FAN_CENTER_XY_MM
    rotor_z0 = COOLING_SHELL_TOP_Z_MM - 1.15
    rotor_h = 0.95
    parts: list[cq.Workplane | cq.Shape] = [
        cylinder_z(FAN_HUB_D_MM, rotor_z0, rotor_z0 + rotor_h, fan_x, fan_y)
    ]
    inner_r = FAN_HUB_D_MM / 2.0 - 0.15
    middle_r = (inner_r + FAN_INLET_D_MM / 2.0) / 2.0
    outer_r = FAN_INLET_D_MM / 2.0 - 0.35

    def point(radius: float, angle_deg: float) -> tuple[float, float]:
        angle = math.radians(angle_deg)
        return fan_x + radius * math.cos(angle), fan_y + radius * math.sin(angle)

    blade_points = (
        point(inner_r, +1.0),
        point(middle_r, -6.0),
        point(outer_r, -16.0),
        point(outer_r, -20.0),
        point(middle_r, -11.0),
        point(inner_r, -4.0),
    )
    base_blade = polygon_plate_xy(blade_points, rotor_h, rotor_z0)
    for index in range(FAN_BLADE_COUNT):
        parts.append(
            base_blade.rotate(
                (fan_x, fan_y, 0.0),
                (fan_x, fan_y, 1.0),
                index * 360.0 / FAN_BLADE_COUNT,
            )
        )
    return compound(parts)


def make_heat_bridge() -> cq.Shape:
    return (
        cq.Workplane("XY")
        .box(10.0, 50.0, 2.5, centered=(True, True, False))
        .translate((-29.0, -7.0, COOLING_FIN_BOTTOM_Z_MM + 0.35))
        .val()
    )


def make_fins() -> cq.Shape:
    fin_base = (
        cq.Workplane("XY")
        .box(FIN_STACK_X_MM, FIN_STACK_Y_MM, 1.0, centered=(True, True, False))
        .translate((FIN_STACK_CENTER_X_MM, FIN_STACK_CENTER_Y_MM, COOLING_FIN_BOTTOM_Z_MM))
    )
    fin_height = FAN_TOP_Z_MM - (COOLING_FIN_BOTTOM_Z_MM + 0.80)
    fin_count = int(FIN_STACK_Y_MM // COOLING_FIN_PITCH_MM) + 1
    first_y = FIN_STACK_CENTER_Y_MM - (fin_count - 1) * COOLING_FIN_PITCH_MM / 2.0
    fins: list[cq.Workplane | cq.Shape] = [fin_base]
    for index in range(fin_count):
        fins.append(
            cq.Workplane("XY")
            .box(FIN_STACK_X_MM, COOLING_FIN_T_MM, fin_height, centered=(True, True, False))
            .translate(
                (
                    FIN_STACK_CENTER_X_MM,
                    first_y + index * COOLING_FIN_PITCH_MM,
                    COOLING_FIN_BOTTOM_Z_MM + 0.80,
                )
            )
        )
    return compound(fins)


def make_cooling_keepout() -> cq.Shape:
    fan = fan_shell_plate_xy(
        FAN_TOP_Z_MM - PCB_TOP_Z_MM,
        PCB_TOP_Z_MM,
    )
    fins = (
        cq.Workplane("XY")
        .box(
            FIN_STACK_X_MM,
            FIN_STACK_Y_MM,
            FAN_TOP_Z_MM - PCB_TOP_Z_MM,
            centered=(True, True, False),
        )
        .translate((FIN_STACK_CENTER_X_MM, FIN_STACK_CENTER_Y_MM, PCB_TOP_Z_MM))
    )
    return compound([fan, fins])


def make_underside_keepouts() -> cq.Shape:
    return compound(
        [
            cq.Workplane("XY").box(68.0, 34.0, 6.5, centered=(True, True, False)).translate((0.0, +31.0, -6.5)),
            cq.Workplane("XY").box(62.0, 24.0, 4.2, centered=(True, True, False)).translate((+1.0, +1.0, -4.2)),
            cq.Workplane("XY").box(48.0, 18.0, 7.0, centered=(True, True, False)).translate((-4.0, -31.0, -7.0)),
        ]
    )


def make_mount_axes() -> cq.Shape:
    return compound(
        [
            cylinder_z(1.0, LOWEST_Z_MM - 2.0, FAN_TOP_Z_MM + 2.0, x, y)
            for _, x, y in MOUNT_HOLES
        ]
    )


def build_geometry() -> dict[str, cq.Shape]:
    pcb = make_pcb()
    connectors = make_connectors()
    switch = make_board_switch()
    cold_plate_support = make_cold_plate_support()
    deck = make_cooling_deck()
    blower = make_blower_shell()
    rotor = make_fan_rotor()
    bridge = make_heat_bridge()
    fins = make_fins()
    cooling = compound([cold_plate_support, deck, blower, rotor, bridge, fins])
    motherboard = compound([pcb, connectors, switch, cooling])
    return {
        "pcb": pcb,
        "connectors": connectors,
        "switch": switch,
        "cold_plate_support": cold_plate_support,
        "cooling_deck": deck,
        "blower_shell": blower,
        "fan_rotor": rotor,
        "heat_bridge": bridge,
        "fins": fins,
        "cooling_assembly": cooling,
        "motherboard_assembly": motherboard,
        "cooling_keepout": make_cooling_keepout(),
        "underside_keepouts": make_underside_keepouts(),
        "mount_axes": make_mount_axes(),
    }
