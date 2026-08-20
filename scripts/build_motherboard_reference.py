#!/usr/bin/env python3
"""Build, export, render and validate the N305 motherboard reference."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

import cadquery as cq
from cadquery import exporters


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from n305_mainboard_reference import (  # noqa: E402
    ALL_CONNECTORS,
    ASSEMBLY_X_ENVELOPE_MM,
    BARE_ASSEMBLY_Z_MM,
    FACE_04_CONNECTORS,
    FAN_BLADE_COUNT,
    FAN_CENTER_XY_MM,
    FAN_INLET_D_MM,
    FAN_PROFILE_UNCERTAINTY_MM,
    FAN_SHELL_PROFILE_XY_MM,
    FAN_TOP_Z_MM,
    LOWEST_Z_MM,
    MOUNT_HOLE_D_MM,
    MOUNT_HOLE_POSITION_UNCERTAINTY_MM,
    MOUNT_HOLES,
    PCB_CORNER_R_MM,
    PCB_T_MM,
    PCB_TOP_Z_MM,
    PCB_X_MM,
    PCB_Y_MM,
    SWITCH_CENTER_Y_MM,
    SWITCH_CENTER_Z_MM,
    build_geometry,
    rounded_plate_xy,
)
from n305_panel_reference import FACE_APERTURES  # noqa: E402


EXPORT_ROOT = ROOT / "exports" / "reference"
PHYSICAL_DIR = EXPORT_ROOT / "physical"
CLEARANCE_DIR = EXPORT_ROOT / "clearances"
PREVIEW_DIR = ROOT / "previews" / "reference"
VALIDATION_PATH = EXPORT_ROOT / "validation.json"
for directory in (EXPORT_ROOT, PHYSICAL_DIR, CLEARANCE_DIR, PREVIEW_DIR):
    directory.mkdir(parents=True, exist_ok=True)


def intersection_volume(left: cq.Shape, right: cq.Shape) -> float:
    volume = 0.0
    for left_solid in left.Solids():
        for right_solid in right.Solids():
            volume += left_solid.intersect(right_solid).Volume()
    return volume


def shape_stats(shape: cq.Shape) -> dict[str, object]:
    bounds = shape.BoundingBox()
    return {
        "solids": len(shape.Solids()),
        "volume_mm3": round(shape.Volume(), 3),
        "bounds_mm": {
            "x": [round(bounds.xmin, 3), round(bounds.xmax, 3)],
            "y": [round(bounds.ymin, 3), round(bounds.ymax, 3)],
            "z": [round(bounds.zmin, 3), round(bounds.zmax, 3)],
        },
        "size_mm": [round(bounds.xlen, 3), round(bounds.ylen, 3), round(bounds.zlen, 3)],
    }


def export_shape(shape: cq.Shape, directory: Path, basename: str) -> None:
    exporters.export(shape, str(directory / f"{basename}.step"))
    exporters.export(
        shape,
        str(directory / f"{basename}.stl"),
        tolerance=0.04,
        angularTolerance=0.12,
    )


def render_preview(
    parts: list[tuple[str, cq.Shape, str, float]],
    output: Path,
    title: str,
    elevation: float,
    azimuth: float,
    limits: tuple[tuple[float, float], tuple[float, float], tuple[float, float]],
    figure_size: tuple[float, float] = (12, 8),
    show_axes: bool = True,
    show_z_axis: bool = True,
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.patches import Patch
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    figure = plt.figure(figsize=figure_size, dpi=150, facecolor="#f4f7fa")
    axis = figure.add_subplot(111, projection="3d")
    axis.set_facecolor("#f4f7fa")
    legend_items: list[Patch] = []

    for label, shape, color, alpha in parts:
        vertices, triangles = shape.tessellate(0.18)
        coordinates = np.asarray([(vertex.x, vertex.y, vertex.z) for vertex in vertices], dtype=float)
        faces = coordinates[np.asarray(triangles, dtype=int)]
        mesh = Poly3DCollection(
            faces,
            facecolor=color,
            edgecolor=(0.10, 0.12, 0.14, 0.22),
            linewidth=0.18,
            alpha=alpha,
        )
        axis.add_collection3d(mesh)
        legend_items.append(Patch(facecolor=color, edgecolor="#343a40", label=label, alpha=alpha))

    (x_limits, y_limits, z_limits) = limits
    axis.set_xlim(*x_limits)
    axis.set_ylim(*y_limits)
    axis.set_zlim(*z_limits)
    axis.set_box_aspect(
        (
            x_limits[1] - x_limits[0],
            y_limits[1] - y_limits[0],
            z_limits[1] - z_limits[0],
        )
    )
    axis.view_init(elev=elevation, azim=azimuth)
    axis.set_proj_type("ortho")
    if show_axes:
        axis.set_xlabel("X axis: +06 / -04", labelpad=10)
        axis.set_ylabel("Y axis: +07 / -05", labelpad=10)
        if show_z_axis:
            axis.set_zlabel("Z: bottom  <---  --->  fan", labelpad=8)
        else:
            axis.set_zticks([])
    else:
        axis.set_axis_off()
    axis.set_title(title, fontsize=16, fontweight="bold", pad=18)
    axis.legend(handles=legend_items, loc="upper left", bbox_to_anchor=(0.0, 0.98), fontsize=8)
    figure.tight_layout()
    figure.savefig(output, bbox_inches="tight")
    plt.close(figure)


def render_previews(geometry: dict[str, cq.Shape]) -> None:
    physical_parts = [
        ("PCB", geometry["pcb"], "#2f8f46", 0.24),
        ("connectors", geometry["connectors"], "#aeb7c0", 0.98),
        ("board switch", geometry["switch"], "#f0f2f4", 1.0),
        ("cold plate / support", geometry["cold_plate_support"], "#6f7882", 0.98),
        ("fan deck", geometry["cooling_deck"], "#424a52", 0.98),
        ("photo-traced volute", geometry["blower_shell"], "#c3c8cc", 0.98),
        ("fan rotor", geometry["fan_rotor"], "#111418", 0.98),
        ("heat bridge", geometry["heat_bridge"], "#bd6f36", 0.98),
        ("fins", geometry["fins"], "#c8cdd2", 0.98),
    ]
    render_preview(
        physical_parts,
        PREVIEW_DIR / "motherboard-isometric.png",
        "N305 motherboard reference - fan-side isometric",
        35,
        -55,
        ((-60, 60), (-58, 58), (-12, 18)),
    )
    bottom_parts = [
        ("PCB", geometry["pcb"], "#2f8f46", 0.30),
        ("connectors", geometry["connectors"], "#aeb7c0", 1.0),
        ("board switch", geometry["switch"], "#f0f2f4", 1.0),
        ("cold plate / support", geometry["cold_plate_support"], "#6f7882", 0.35),
        ("fan deck", geometry["cooling_deck"], "#424a52", 0.25),
        ("photo-traced volute", geometry["blower_shell"], "#c3c8cc", 0.20),
        ("heat bridge", geometry["heat_bridge"], "#bd6f36", 0.30),
        ("fins", geometry["fins"], "#c8cdd2", 0.30),
    ]
    render_preview(
        bottom_parts,
        PREVIEW_DIR / "motherboard-bottom.png",
        "N305 motherboard reference - underside / connector view",
        -27,
        125,
        ((-60, 60), (-58, 58), (-12, 18)),
    )
    contact_parts = [
        ("PCB", geometry["pcb"], "#2f8f46", 0.28),
        ("cold plate / support", geometry["cold_plate_support"], "#6f7882", 1.0),
        ("fan deck", geometry["cooling_deck"], "#424a52", 1.0),
        ("photo-traced volute", geometry["blower_shell"], "#c3c8cc", 1.0),
        ("heat bridge", geometry["heat_bridge"], "#bd6f36", 1.0),
        ("fin stack", geometry["fins"], "#c8cdd2", 1.0),
    ]
    render_preview(
        contact_parts,
        PREVIEW_DIR / "cooling-contact-path.png",
        "Verified contact path: PCB -> cold plate/support -> deck -> heat bridge -> fins",
        0,
        -90,
        ((-56, 34), (-48, 48), (0, 17)),
        figure_size=(14, 5),
        show_axes=False,
    )
    plan_parts = [
        ("PCB", geometry["pcb"], "#2f8f46", 0.28),
        ("connectors", geometry["connectors"], "#aeb7c0", 1.0),
        ("fins", geometry["fins"], "#c8cdd2", 0.85),
        ("photo-traced volute", geometry["blower_shell"], "#c3c8cc", 0.90),
        ("32-blade rotor", geometry["fan_rotor"], "#111418", 1.0),
    ]
    render_preview(
        plan_parts,
        PREVIEW_DIR / "motherboard-plan.png",
        "N305 motherboard reference - fan-side orthographic plan",
        90,
        180,
        ((-55, 55), (-57, 57), (-12, 18)),
        figure_size=(10, 10),
        show_z_axis=False,
    )


def build_validation(geometry: dict[str, cq.Shape]) -> dict[str, object]:
    pcb = geometry["pcb"]
    motherboard = geometry["motherboard_assembly"]
    contact_probe = rounded_plate_xy(
        PCB_X_MM,
        PCB_Y_MM,
        PCB_CORNER_R_MM,
        0.04,
        PCB_TOP_Z_MM - 0.02,
    ).val()
    motherboard_bounds = motherboard.BoundingBox()
    face_04_names = tuple(item.name for item in FACE_APERTURES["04"])
    face_06_usb_apertures = tuple(
        item for item in FACE_APERTURES["06"] if item.name.startswith("usb_")
    )
    face_06_switch = next(
        item for item in FACE_APERTURES["06"] if item.name == "power_switch"
    )

    contact_checks = {
        "pcb_to_cold_plate_distance_mm": round(
            pcb.distance(geometry["cold_plate_support"]), 6
        ),
        "pcb_top_contact_probe_intersection_mm3": round(
            intersection_volume(contact_probe, geometry["cold_plate_support"]), 6
        ),
        "cold_plate_to_deck_distance_mm": round(
            geometry["cold_plate_support"].distance(geometry["cooling_deck"]), 6
        ),
        "cold_plate_deck_overlap_mm3": round(
            intersection_volume(geometry["cold_plate_support"], geometry["cooling_deck"]), 6
        ),
        "deck_to_blower_distance_mm": round(
            geometry["cooling_deck"].distance(geometry["blower_shell"]), 6
        ),
        "deck_blower_overlap_mm3": round(
            intersection_volume(geometry["cooling_deck"], geometry["blower_shell"]), 6
        ),
        "deck_to_heat_bridge_distance_mm": round(
            geometry["cooling_deck"].distance(geometry["heat_bridge"]), 6
        ),
        "deck_heat_bridge_overlap_mm3": round(
            intersection_volume(geometry["cooling_deck"], geometry["heat_bridge"]), 6
        ),
        "heat_bridge_to_fins_distance_mm": round(
            geometry["heat_bridge"].distance(geometry["fins"]), 6
        ),
        "heat_bridge_fins_overlap_mm3": round(
            intersection_volume(geometry["heat_bridge"], geometry["fins"]), 6
        ),
    }
    all_contacts_pass = (
        contact_checks["pcb_to_cold_plate_distance_mm"] == 0.0
        and contact_checks["pcb_top_contact_probe_intersection_mm3"] > 0.0
        and contact_checks["cold_plate_to_deck_distance_mm"] == 0.0
        and contact_checks["cold_plate_deck_overlap_mm3"] > 0.0
        and contact_checks["deck_to_blower_distance_mm"] == 0.0
        and contact_checks["deck_blower_overlap_mm3"] > 0.0
        and contact_checks["deck_to_heat_bridge_distance_mm"] == 0.0
        and contact_checks["deck_heat_bridge_overlap_mm3"] > 0.0
        and contact_checks["heat_bridge_to_fins_distance_mm"] == 0.0
        and contact_checks["heat_bridge_fins_overlap_mm3"] > 0.0
    )

    return {
        "scope": "motherboard reference only; no enclosure geometry generated",
        "coordinate_frame": "+X=06, -X=04, +Y=07, -Y=05, +Z=fan side; PCB bottom Z=0",
        "data_sources": {
            "workflow": "AGENTS.md and docs/modeling-workflow.md",
            "panel_centers": "src/n305_panel_reference.py",
            "measured_photo_index": "pics/README.md",
            "component_plan_trace": "docs/component-calibration.json",
            "geometry": "src/n305_mainboard_reference.py",
        },
        "pcb": {
            "size_mm": [PCB_X_MM, PCB_Y_MM, PCB_T_MM],
            "corner_radius_mm": PCB_CORNER_R_MM,
            "mount_hole_diameter_mm": MOUNT_HOLE_D_MM,
            "mount_hole_position_uncertainty_mm": MOUNT_HOLE_POSITION_UNCERTAINTY_MM,
            "mount_holes": [
                {"name": name, "x_mm": x, "y_mm": y}
                for name, x, y in MOUNT_HOLES
            ],
        },
        "plan_envelope": {
            "pcb_x_mm": PCB_X_MM,
            "assembly_04_06_mm": ASSEMBLY_X_ENVELOPE_MM,
            "nominal_projection_each_face_mm": round(
                (ASSEMBLY_X_ENVELOPE_MM - PCB_X_MM) / 2.0, 3
            ),
            "generated_bounds_x_mm": [
                round(motherboard_bounds.xmin, 3),
                round(motherboard_bounds.xmax, 3),
            ],
        },
        "z_stack": {
            "lowest_z_mm": LOWEST_Z_MM,
            "fan_top_z_mm": FAN_TOP_Z_MM,
            "bare_assembly_thickness_mm": BARE_ASSEMBLY_Z_MM,
            "generated_bounds_z_mm": [
                round(motherboard_bounds.zmin, 3),
                round(motherboard_bounds.zmax, 3),
            ],
            "generated_thickness_mm": round(motherboard_bounds.zlen, 3),
        },
        "fan": {
            "center_xy_mm": list(FAN_CENTER_XY_MM),
            "inlet_diameter_mm": FAN_INLET_D_MM,
            "volute_profile_xy_mm": [list(point) for point in FAN_SHELL_PROFILE_XY_MM],
            "profile_uncertainty_mm": FAN_PROFILE_UNCERTAINTY_MM,
            "blade_count": FAN_BLADE_COUNT,
            "two_hole_top_bar": "not modeled; 05 side view does not support it above the blower",
        },
        "interfaces": [asdict(item) for item in ALL_CONNECTORS],
        "board_switch": {
            "face": "06",
            "center_y_mm": SWITCH_CENTER_Y_MM,
            "center_z_mm": SWITCH_CENTER_Z_MM,
        },
        "checks": {
            "pcb_bounds_match_measured": all(
                abs(actual - expected) <= 0.01
                for actual, expected in zip(
                    shape_stats(pcb)["size_mm"],
                    [100.0, 105.5, 1.5],
                )
            ),
            "mount_hole_count_is_four": len(MOUNT_HOLES) == 4,
            "assembly_x_envelope_matches_103p4": abs(
                motherboard_bounds.xlen - ASSEMBLY_X_ENVELOPE_MM
            )
            <= 0.02,
            "bare_assembly_thickness_matches_25p6": abs(motherboard_bounds.zlen - 25.6) <= 0.02,
            "cooling_contact_path_complete": all_contacts_pass,
            "blower_is_asymmetric_photo_trace": len(FAN_SHELL_PROFILE_XY_MM) >= 12
            and min(x for x, _ in FAN_SHELL_PROFILE_XY_MM) < -29.0
            and max(x for x, _ in FAN_SHELL_PROFILE_XY_MM) < 26.0
            and min(y for _, y in FAN_SHELL_PROFILE_XY_MM) < -33.0
            and max(y for _, y in FAN_SHELL_PROFILE_XY_MM) < 21.0,
            "fan_rotor_has_32_blades": FAN_BLADE_COUNT == 32
            and len(geometry["fan_rotor"].Solids()) == FAN_BLADE_COUNT + 1,
            "unsupported_fan_top_bar_removed": "fan_bracket" not in geometry,
            "face_04_order_and_semantics_preserved": face_04_names
            == ("dc", "hdmi_1", "headphone", "rj45", "stack_dual_usb", "hdmi_3")
            and {item.name for item in FACE_04_CONNECTORS}
            >= {"stack_usb_upper", "stack_usb_lower", "hdmi_1", "hdmi_3"},
            "face_06_apertures_match_measured": all(
                abs(item.width_mm - 12.8) < 1e-9
                and abs(item.height_mm - 5.5) < 1e-9
                and abs(item.corner_radius_mm - 0.7) < 1e-9
                for item in face_06_usb_apertures
            )
            and len(face_06_usb_apertures) == 2
            and abs(face_06_switch.width_mm - 9.4) < 1e-9,
            "face_06_usb_profiles_horizontal": all(
                item.face != "06"
                or (item.nose_shape == "roundrect" and item.nose_width_mm > item.nose_height_mm)
                for item in ALL_CONNECTORS
            ),
            "enclosure_geometry_generated": False,
        },
        "contact_checks": contact_checks,
        "parts": {
            name: shape_stats(shape)
            for name, shape in geometry.items()
        },
    }


def main() -> None:
    geometry = build_geometry()
    # STEP/STL export and preview tessellation attach meshes to OCCT shapes and
    # can expand later bounding-box queries by the mesh deflection.  Validate
    # the untouched parametric geometry first so measured envelopes are checked
    # against B-rep geometry, not renderer tolerances.
    validation = build_validation(geometry)
    physical_outputs = {
        "n305_motherboard_reference": geometry["motherboard_assembly"],
        "n305_pcb": geometry["pcb"],
        "n305_connectors_and_switch": cq.Compound.makeCompound(
            [*geometry["connectors"].Solids(), *geometry["switch"].Solids()]
        ),
        "n305_cooling_assembly": geometry["cooling_assembly"],
    }
    clearance_outputs = {
        "n305_cooling_keepout": geometry["cooling_keepout"],
        "n305_underside_keepouts": geometry["underside_keepouts"],
        "n305_mount_axes": geometry["mount_axes"],
    }
    for basename, shape in physical_outputs.items():
        export_shape(shape, PHYSICAL_DIR, basename)
    for basename, shape in clearance_outputs.items():
        export_shape(shape, CLEARANCE_DIR, basename)

    render_previews(geometry)
    VALIDATION_PATH.write_text(
        json.dumps(validation, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if not all(
        value is True or key == "enclosure_geometry_generated"
        for key, value in validation["checks"].items()
        if isinstance(value, bool)
    ):
        raise RuntimeError(f"motherboard validation failed: {validation['checks']}")
    print(f"Exported motherboard reference to {EXPORT_ROOT}")
    print(json.dumps(validation["checks"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
