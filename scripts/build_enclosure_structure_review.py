#!/usr/bin/env python3
"""Build review diagrams and reports for the enclosure structure definition.

No enclosure STEP or STL is written by this script.  The generated CadQuery
solids exist only in memory so face ownership, seams, clamping and aperture
coverage can be reviewed before the manufacturing-CAD gate is opened.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import cadquery as cq


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from n305_enclosure_structure import (  # noqa: E402
    ASSEMBLY_SEQUENCE,
    BOTTOM_PLATE_T_MM,
    BUTTON_INNER_GAP_RANGE_MM,
    BUTTON_INNER_WALL_TO_SWITCH_TIP_MM,
    BUTTON_OUTER_WALL_TO_SWITCH_TIP_MM,
    CLAMP_POST_OD_MM,
    CONNECTOR_FRONT_SPAN_X_MM,
    FACE_OWNERSHIP,
    FAN_CENTER_XY_MM,
    FAN_INTAKE_D_MM,
    FIN_EXHAUST_CENTER_Z_MM,
    FIN_EXHAUST_HEIGHT_Z_MM,
    FIN_EXHAUST_WIDTH_Y_MM,
    INNER_X_MAX_MM,
    INNER_X_MIN_MM,
    INNER_PLAN_CENTER_X_MM,
    INNER_PLAN_CENTER_Y_MM,
    INNER_PLAN_CORNER_R_MM,
    INNER_Y_MAX_MM,
    INNER_Y_MIN_MM,
    INNER_Z_MAX_MM,
    INNER_Z_MIN_MM,
    LOWER_SCREW_CLEARANCE_D_MM,
    MOUNT_HOLE_D_MM,
    MOUNT_HOLES,
    NOMINAL_SEAM_GAP_MM,
    OUTER_X_MAX_MM,
    OUTER_X_MIN_MM,
    OUTER_X_MM,
    OUTER_PLAN_CENTER_X_MM,
    OUTER_PLAN_CENTER_Y_MM,
    OUTER_PLAN_CORNER_R_MM,
    OUTER_Y_MAX_MM,
    OUTER_Y_MIN_MM,
    OUTER_Y_MM,
    OUTER_Z_MAX_MM,
    OUTER_Z_MIN_MM,
    OUTER_Z_MM,
    PCB_CLEARANCE_04_MM,
    PCB_CLEARANCE_05_MM,
    PCB_CLEARANCE_06_MM,
    PCB_CLEARANCE_07_MM,
    PCB_T_MM,
    PCB_CORNER_R_MM,
    PCB_X_MM,
    PCB_Y_MM,
    REVIEW_PARAMETERS,
    SEAM_PATH,
    SIDE_WALL_T_MM,
    SWITCH_ACTUATOR_TIP_X_MM,
    TOP_PLATE_T_MM,
    UPPER_THREAD_PILOT_D_MM,
    aperture_signed_clearance,
    build_coverage_report,
    build_review_geometry,
    coverage_targets,
    make_aperture_cutter,
    make_rounded_wall_ring,
    rounded_plate_xy,
    structure_definition,
)
from n305_panel_reference import FACE_APERTURES, PanelApertureReference  # noqa: E402


PREVIEW_DIR = ROOT / "previews" / "enclosure"
DOCS_DIR = ROOT / "docs"
STRUCTURE_JSON = DOCS_DIR / "enclosure-structure.json"
COVERAGE_JSON = DOCS_DIR / "enclosure-aperture-coverage.json"
VALIDATION_JSON = DOCS_DIR / "enclosure-structure-validation.json"
V2_EXPORT_DIR = ROOT / "exports" / "enclosure" / "v2-prototype"
V2_EXPECTED_CAD = (
    "n305_v2_upper_shell.step",
    "n305_v2_upper_shell.stl",
    "n305_v2_lower_shell.step",
    "n305_v2_lower_shell.stl",
    "n305_v2_enclosure_assembly.step",
    "n305_v2_enclosure_assembly.stl",
)
for directory in (PREVIEW_DIR, DOCS_DIR):
    directory.mkdir(parents=True, exist_ok=True)

UPPER_COLOR = "#4f8edc"
LOWER_COLOR = "#e59b48"
PCB_COLOR = "#4ca36c"
SEAM_COLOR = "#d6274f"
APERTURE_COLOR = "#d12d91"
TARGET_COLOR = "#566573"
FAIL_COLOR = "#c83349"
UNEVALUATED_COLOR = "#8a6d1d"
GRID_COLOR = "#d9dfe6"


def intersection_volume(left: cq.Shape, right: cq.Shape) -> float:
    return sum(
        left_solid.intersect(right_solid).Volume()
        for left_solid in left.Solids()
        for right_solid in right.Solids()
    )


def difference_volume(left: cq.Shape, right: cq.Shape) -> float:
    try:
        return left.cut(right).Volume()
    except ValueError as error:
        if "Null TopoDS_Shape" in str(error):
            return 0.0
        raise


def add_shape(
    axis,
    shape: cq.Shape,
    color: str,
    alpha: float,
    label: str | None = None,
    show_mesh_edges: bool = True,
) -> None:
    import numpy as np
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    vertices, triangles = shape.tessellate(0.20)
    coordinates = np.asarray([(item.x, item.y, item.z) for item in vertices], dtype=float)
    faces = coordinates[np.asarray(triangles, dtype=int)]
    mesh = Poly3DCollection(
        faces,
        facecolor=color,
        edgecolor=(0.08, 0.10, 0.13, 0.16) if show_mesh_edges else "none",
        linewidth=0.12 if show_mesh_edges else 0.0,
        alpha=alpha,
        label=label,
    )
    axis.add_collection3d(mesh)


def add_topology_edges(
    axis,
    shape: cq.Shape,
    color: str,
    linewidth: float = 0.8,
    alpha: float = 0.85,
    deflection: float = 0.25,
) -> None:
    """Draw CAD feature edges without exposing triangulation mesh edges."""
    for edge in shape.Edges():
        try:
            points, _ = edge.sample(deflection)
        except (ValueError, ZeroDivisionError):
            points, _ = edge.sample(16)
        if len(points) < 2:
            continue
        axis.plot3D(
            [point.x for point in points],
            [point.y for point in points],
            [point.z for point in points],
            color=color,
            linewidth=linewidth,
            alpha=alpha,
            solid_capstyle="round",
            zorder=8,
        )


def add_mount_axes(
    axis,
    z_min: float,
    z_max: float,
    z_offset: float = 0.0,
) -> None:
    """Show the four original PCB mounting axes as construction centerlines."""
    for _, x, y in MOUNT_HOLES:
        axis.plot3D(
            [x, x],
            [y, y],
            [z_min + z_offset, z_max + z_offset],
            color="#2f3740",
            linewidth=1.15,
            linestyle=(0, (4, 3)),
            alpha=0.78,
            zorder=11,
        )


def format_3d_axis(axis, z_limits: tuple[float, float]) -> None:
    axis.set_xlim(OUTER_X_MIN_MM - 5.0, OUTER_X_MAX_MM + 5.0)
    axis.set_ylim(OUTER_Y_MIN_MM - 5.0, OUTER_Y_MAX_MM + 5.0)
    axis.set_zlim(*z_limits)
    axis.set_box_aspect((OUTER_X_MM, OUTER_Y_MM, z_limits[1] - z_limits[0]))
    axis.set_xlabel("X: +06 / -04", labelpad=8)
    axis.set_ylabel("Y: +07 / -05", labelpad=8)
    axis.set_zlabel("Z: fan / bottom", labelpad=8)
    axis.grid(True, color=GRID_COLOR)
    axis.set_proj_type("ortho")


def render_assembly(geometry: dict[str, cq.Shape]) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch

    figure = plt.figure(figsize=(18, 9), dpi=160, facecolor="#f4f7fa")
    assembled = figure.add_subplot(121, projection="3d")
    exploded = figure.add_subplot(122, projection="3d")

    add_shape(assembled, geometry["motherboard"], PCB_COLOR, 0.22, "motherboard reference")
    add_shape(assembled, geometry["upper_shell_review"], UPPER_COLOR, 0.78, "upper: top + 06 + 05", False)
    add_shape(assembled, geometry["lower_shell_review"], LOWER_COLOR, 0.84, "lower: bottom + 04 + 07", False)
    for face in ("top", "06", "05"):
        add_topology_edges(assembled, geometry[face], "#173f6b", 0.95, 0.92)
    for face in ("bottom", "04", "07"):
        add_topology_edges(assembled, geometry[face], "#754411", 0.95, 0.92)
    add_shape(assembled, geometry["upper_posts"], "#2f6eb2", 0.48, None, False)
    add_shape(assembled, geometry["lower_posts"], "#c37628", 0.52, None, False)
    add_topology_edges(assembled, geometry["upper_posts"], "#092f59", 1.35, 1.0, 0.15)
    add_topology_edges(assembled, geometry["lower_posts"], "#603405", 1.35, 1.0, 0.15)
    add_topology_edges(assembled, geometry["motherboard_pcb"], "#245d39", 0.85, 0.90)
    add_mount_axes(assembled, OUTER_Z_MIN_MM, OUTER_Z_MAX_MM)
    for segment in SEAM_PATH:
        seam_points = segment.path_xyz_mm or (
            segment.start_xyz_mm,
            segment.end_xyz_mm,
        )
        assembled.plot3D(
            [point[0] for point in seam_points],
            [point[1] for point in seam_points],
            [point[2] for point in seam_points],
            color=SEAM_COLOR,
            linewidth=3.0,
            zorder=12,
        )
    assembled.view_init(elev=28, azim=-52)
    format_3d_axis(assembled, (OUTER_Z_MIN_MM - 3.0, OUTER_Z_MAX_MM + 3.0))
    assembled.set_title("Assembled structure: one closed six-segment seam", fontsize=14, fontweight="bold")

    upper_exploded = geometry["upper_shell_review"].translate((0.0, 0.0, +20.0))
    lower_exploded = geometry["lower_shell_review"].translate((0.0, 0.0, -20.0))
    add_shape(exploded, upper_exploded, UPPER_COLOR, 0.68, "upper shell", False)
    add_shape(exploded, geometry["motherboard"], PCB_COLOR, 0.78, "motherboard")
    add_shape(exploded, lower_exploded, LOWER_COLOR, 0.72, "lower shell", False)
    upper_posts_exploded = geometry["upper_posts"].translate((0.0, 0.0, +20.0))
    lower_posts_exploded = geometry["lower_posts"].translate((0.0, 0.0, -20.0))
    add_shape(exploded, upper_posts_exploded, "#2f6eb2", 0.60, None, False)
    add_shape(exploded, lower_posts_exploded, "#c37628", 0.62, None, False)
    for face in ("top", "06", "05"):
        add_topology_edges(
            exploded,
            geometry[face].translate((0.0, 0.0, +20.0)),
            "#173f6b",
            1.05,
            0.96,
        )
    for face in ("bottom", "04", "07"):
        add_topology_edges(
            exploded,
            geometry[face].translate((0.0, 0.0, -20.0)),
            "#754411",
            1.05,
            0.96,
        )
    add_topology_edges(exploded, geometry["motherboard_pcb"], "#245d39", 0.75, 0.85)
    add_topology_edges(exploded, upper_posts_exploded, "#092f59", 1.45, 1.0, 0.15)
    add_topology_edges(exploded, lower_posts_exploded, "#603405", 1.45, 1.0, 0.15)
    add_mount_axes(exploded, OUTER_Z_MIN_MM - 20.0, OUTER_Z_MAX_MM + 20.0)
    for x, y in ((-35.0, -35.0), (+35.0, +35.0)):
        exploded.quiver(x, y, -28.0, 0.0, 0.0, 14.0, color="#343a40", linewidth=1.8, arrow_length_ratio=0.18)
    exploded.text(-34.0, -35.0, -30.0, "lower +Z", color="#343a40", fontsize=9)
    exploded.text(+30.0, +35.0, -4.0, "board +Z into upper", color="#343a40", fontsize=9)
    exploded.view_init(elev=25, azim=-52)
    format_3d_axis(exploded, (-35.0, 40.0))
    exploded.set_title("Assembly sequence: board first, lower shell second", fontsize=14, fontweight="bold")

    legend = [
        Patch(facecolor=UPPER_COLOR, edgecolor="#324f73", label="upper shell: top + 06 + 05", alpha=0.55),
        Patch(facecolor=LOWER_COLOR, edgecolor="#7f5227", label="lower shell: bottom + 04 + 07", alpha=0.60),
        Patch(facecolor=PCB_COLOR, edgecolor="#315f40", label="motherboard reference", alpha=0.75),
        Line2D([0], [0], color=SEAM_COLOR, lw=3, label="upper/lower seam path"),
        Line2D([0], [0], color="#2f3740", lw=1.4, linestyle=(0, (4, 3)), label="4 original PCB clamp axes"),
    ]
    figure.legend(handles=legend, loc="lower center", ncol=5, bbox_to_anchor=(0.5, 0.02), fontsize=9)
    figure.suptitle(
        "N305 enclosure structure review — preview geometry only, no STEP/STL",
        fontsize=19,
        fontweight="bold",
        y=0.98,
    )
    figure.text(
        0.5,
        0.075,
        f"Top/bottom are exactly {TOP_PLATE_T_MM:g} mm; inner Z touches the measured motherboard envelope. "
        f"Inner plan is {INNER_X_MAX_MM - INNER_X_MIN_MM:.1f} x {INNER_Y_MAX_MM - INNER_Y_MIN_MM:.1f} mm with independent 04/06 clearances of {PCB_CLEARANCE_04_MM:g}/{PCB_CLEARANCE_06_MM:g} mm; outer corners R{OUTER_PLAN_CORNER_R_MM:g}. "
        f"Dark lines are CAD feature edges; dashed lines are 4 PCB clamp axes. Post bores: upper {UPPER_THREAD_PILOT_D_MM:g} mm pilot, lower {LOWER_SCREW_CLEARANCE_D_MM:g} mm through.",
        ha="center",
        fontsize=10,
        color="#4d5965",
    )
    figure.tight_layout(rect=(0.0, 0.10, 1.0, 0.95))
    figure.savefig(PREVIEW_DIR / "enclosure-assembly-and-exploded.png", bbox_inches="tight")
    plt.close(figure)


def render_face_ownership_and_seam() -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch, Rectangle

    figure, (net_axis, seam_axis) = plt.subplots(1, 2, figsize=(16, 8), dpi=160, facecolor="#f4f7fa")
    for axis in (net_axis, seam_axis):
        axis.set_facecolor("#f4f7fa")

    cells = {
        "top": (2, 2),
        "06": (2, 4),
        "04": (2, 0),
        "07": (0, 2),
        "05": (4, 2),
        "bottom": (2, -2),
    }
    for face, (x, y) in cells.items():
        owner = FACE_OWNERSHIP[face]
        color = UPPER_COLOR if owner == "upper" else LOWER_COLOR
        net_axis.add_patch(Rectangle((x, y), 2, 2, facecolor=color, edgecolor="#2f3943", linewidth=2.0, alpha=0.78))
        net_axis.text(x + 1, y + 1.15, face.upper(), ha="center", va="center", fontsize=16, fontweight="bold")
        net_axis.text(x + 1, y + 0.60, owner, ha="center", va="center", fontsize=11, color="#26313a")
    net_axis.annotate("+X / 06", xy=(3, 6.25), ha="center", fontsize=11)
    net_axis.annotate("+Y / 07", xy=(-0.2, 3), va="center", rotation=90, fontsize=11)
    net_axis.annotate("-Y / 05", xy=(6.3, 3), va="center", rotation=-90, fontsize=11)
    net_axis.set_xlim(-0.7, 6.7)
    net_axis.set_ylim(-2.4, 6.7)
    net_axis.set_aspect("equal")
    net_axis.axis("off")
    net_axis.set_title("Six-face ownership (unfolded topology)", fontsize=15, fontweight="bold")

    loop_faces = ("top", "04", "05", "bottom", "06", "07")
    angles = [90 - index * 60 for index in range(6)]
    points = [(3.0 * __import__("math").cos(__import__("math").radians(a)), 3.0 * __import__("math").sin(__import__("math").radians(a))) for a in angles]
    for index, face in enumerate(loop_faces):
        next_index = (index + 1) % len(loop_faces)
        seam_axis.plot(
            [points[index][0], points[next_index][0]],
            [points[index][1], points[next_index][1]],
            color=SEAM_COLOR,
            linewidth=4.0,
            zorder=1,
        )
        owner = FACE_OWNERSHIP[face]
        seam_axis.scatter(
            [points[index][0]],
            [points[index][1]],
            s=1150,
            color=UPPER_COLOR if owner == "upper" else LOWER_COLOR,
            edgecolor="#2f3943",
            linewidth=2,
            zorder=2,
        )
        seam_axis.text(
            *points[index],
            face.upper(),
            ha="center",
            va="center",
            fontsize=8 if face == "bottom" else 12,
            fontweight="bold",
            zorder=3,
        )
    seam_axis.text(0, 0.35, "ONE CLOSED", ha="center", fontsize=16, fontweight="bold", color=SEAM_COLOR)
    seam_axis.text(0, -0.15, "6-segment seam", ha="center", fontsize=13, color=SEAM_COLOR)
    seam_axis.text(
        0,
        -0.75,
        "rounded arcs remain whole\n"
        "06/07 corner: upper; 04/05 corner: lower\n"
        "vertical seams: straight-face tangencies",
        ha="center",
        va="top",
        fontsize=10,
        color="#4d5965",
    )
    seam_axis.set_xlim(-4.3, 4.3)
    seam_axis.set_ylim(-4.3, 4.3)
    seam_axis.set_aspect("equal")
    seam_axis.axis("off")
    seam_axis.set_title(
        f"Seam adjacency and path (outer XY corners R{OUTER_PLAN_CORNER_R_MM:g})",
        fontsize=15,
        fontweight="bold",
    )

    figure.legend(
        handles=[
            Patch(facecolor=UPPER_COLOR, edgecolor="#2f3943", label="upper integral three-face shell"),
            Patch(facecolor=LOWER_COLOR, edgecolor="#2f3943", label="lower integral three-face shell"),
            Patch(facecolor=SEAM_COLOR, edgecolor=SEAM_COLOR, label=f"nominal seam gap {NOMINAL_SEAM_GAP_MM:.1f} mm"),
        ],
        loc="lower center",
        ncol=3,
        bbox_to_anchor=(0.5, 0.015),
    )
    figure.suptitle("Face ownership and assembly seam — no continuous tongue, groove or separate frame", fontsize=18, fontweight="bold")
    figure.tight_layout(rect=(0.0, 0.09, 1.0, 0.94))
    figure.savefig(PREVIEW_DIR / "face-ownership-and-seam.png", bbox_inches="tight")
    plt.close(figure)


def render_rounded_corner_seam_detail() -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch, Polygon, Rectangle

    figure, (assembled_axis, exploded_axis) = plt.subplots(
        1,
        2,
        figsize=(14, 6.5),
        dpi=160,
        facecolor="#f4f7fa",
    )
    outer_radius = OUTER_PLAN_CORNER_R_MM
    inner_radius = INNER_PLAN_CORNER_R_MM
    outer_center_x = OUTER_X_MAX_MM - outer_radius
    outer_center_y = OUTER_Y_MAX_MM - outer_radius
    inner_center_x = INNER_X_MAX_MM - inner_radius
    inner_center_y = INNER_Y_MAX_MM - inner_radius
    inner_local_x = inner_center_x - outer_center_x
    inner_local_y = inner_center_y - outer_center_y
    inner_top_y = inner_local_y + inner_radius
    inner_right_x = inner_local_x + inner_radius
    pcb_center_x = PCB_X_MM / 2.0 - PCB_CORNER_R_MM
    pcb_center_y = PCB_Y_MM / 2.0 - PCB_CORNER_R_MM
    pcb_local_x = pcb_center_x - outer_center_x
    pcb_local_y = pcb_center_y - outer_center_y
    pcb_top_y = pcb_local_y + PCB_CORNER_R_MM
    pcb_right_x = pcb_local_x + PCB_CORNER_R_MM

    outer_arc = [
        (
            outer_radius * math.cos(math.radians(angle)),
            outer_radius * math.sin(math.radians(angle)),
        )
        for angle in range(0, 91, 2)
    ]
    inner_arc = [
        (
            inner_local_x + inner_radius * math.cos(math.radians(angle)),
            inner_local_y + inner_radius * math.sin(math.radians(angle)),
        )
        for angle in range(90, -1, -2)
    ]
    pcb_arc = [
        (
            pcb_local_x + PCB_CORNER_R_MM * math.cos(math.radians(angle)),
            pcb_local_y + PCB_CORNER_R_MM * math.sin(math.radians(angle)),
        )
        for angle in range(90, -1, -2)
    ]
    full_corner = outer_arc + [
        (0.0, inner_top_y),
        (inner_local_x, inner_top_y),
        *inner_arc,
        (inner_right_x, 0.0),
    ]

    def shifted(points, dx: float, dy: float):
        return [(x + dx, y + dy) for x, y in points]

    straight_length = outer_radius + 1.5
    pcb_corner = [
        (-straight_length, -2.0),
        (pcb_right_x, -2.0),
        (pcb_right_x, pcb_local_y),
        *reversed(pcb_arc),
        (-straight_length, pcb_top_y),
    ]
    assembled_axis.add_patch(
        Polygon(
            pcb_corner,
            closed=True,
            facecolor=PCB_COLOR,
            edgecolor="#315f40",
            linewidth=1.2,
            alpha=0.62,
        )
    )
    assembled_axis.add_patch(
        Rectangle(
            (-straight_length, inner_top_y),
            straight_length,
            outer_radius - inner_top_y,
            facecolor=LOWER_COLOR,
            edgecolor="#303942",
            linewidth=1.4,
            alpha=0.86,
        )
    )
    assembled_axis.add_patch(
        Polygon(
            full_corner,
            closed=True,
            facecolor=UPPER_COLOR,
            edgecolor="#303942",
            linewidth=1.4,
            alpha=0.86,
        )
    )
    assembled_axis.plot([0.0, 0.0], [inner_top_y, outer_radius], color=SEAM_COLOR, linewidth=2.5)
    assembled_axis.annotate(
        "vertical seam on straight +Y tangent",
        xy=(0.0, (inner_top_y + outer_radius) / 2.0),
        xytext=(-6.0, 2.8),
        arrowprops=dict(arrowstyle="->", color=SEAM_COLOR, lw=1.4),
        fontsize=10,
        color="#313b44",
    )
    assembled_axis.text(3.15, 3.25, "complete curved corner\nowned by upper shell", ha="center", fontsize=9, fontweight="bold")
    assembled_axis.text(-3.3, (inner_top_y + outer_radius) / 2.0, "straight 07 face / lower", ha="center", fontsize=9, fontweight="bold")
    assembled_axis.text(
        0.25,
        1.55,
        f"PCB reference R4 (provisional)\n+X / 06 clearance {PCB_CLEARANCE_06_MM:g} mm; +Y / 07 reference {PCB_CLEARANCE_07_MM:g} mm",
        ha="center",
        fontsize=9,
        color="#244b34",
        fontweight="bold",
    )
    assembled_axis.text(
        2.6, outer_radius + 1.0,
        f"outer R{outer_radius:g} = inner R{inner_radius:g} + wall {SIDE_WALL_T_MM:g}",
        ha="center",
        fontsize=10,
    )
    assembled_axis.text(
        0.3, -0.65,
        f"constant cavity-wall offset = {SIDE_WALL_T_MM:g} mm\nPCB is contained inside the expanded cavity",
        ha="center",
        va="top",
        fontsize=10,
        color="#244b34",
        fontweight="bold",
    )
    assembled_axis.set_title("Assembled: full corner meets a straight face", fontsize=14, fontweight="bold")

    upper_offset = (+0.9, -0.4)
    lower_offset = (-0.9, +1.0)
    exploded_axis.add_patch(
        Polygon(
            shifted(full_corner, *upper_offset),
            closed=True,
            facecolor=UPPER_COLOR,
            edgecolor="#303942",
            linewidth=1.4,
            alpha=0.86,
        )
    )
    exploded_axis.add_patch(
        Rectangle(
            (-straight_length + lower_offset[0], inner_top_y + lower_offset[1]),
            straight_length,
            outer_radius - inner_top_y,
            facecolor=LOWER_COLOR,
            edgecolor="#303942",
            linewidth=1.4,
            alpha=0.86,
        )
    )
    exploded_axis.annotate(
        "rounded corner remains\none complete feature",
        xy=(3.8 + upper_offset[0], 1.4 + upper_offset[1]),
        xytext=(2.3, -1.0),
        arrowprops=dict(arrowstyle="->", color="#315f84"),
        fontsize=10,
        ha="center",
    )
    exploded_axis.annotate(
        "only the straight 07 segment separates",
        xy=(-3.2 + lower_offset[0], (inner_top_y + outer_radius) / 2.0 + lower_offset[1]),
        xytext=(-6.2, outer_radius + 2.0),
        arrowprops=dict(arrowstyle="->", color="#875824"),
        fontsize=10,
    )
    exploded_axis.text(
        1.8, outer_radius + 1.15,
        "04/05 is mirrored:\nfull rounded corner belongs to lower shell",
        ha="center",
        fontsize=11,
        color="#4d5965",
        fontweight="bold",
    )
    exploded_axis.set_title("Exploded: the rounded feature stays intact", fontsize=14, fontweight="bold")

    for axis in (assembled_axis, exploded_axis):
        axis.set_xlim(-straight_length - 1.0, outer_radius + 1.8)
        axis.set_ylim(-1.5, outer_radius + 2.7)
        axis.set_aspect("equal")
        axis.grid(True, color=GRID_COLOR, linewidth=0.6)
        axis.set_xlabel("local X / mm")
        axis.set_ylabel("local Y / mm")

    figure.legend(
        handles=[
            Patch(facecolor=UPPER_COLOR, edgecolor="#303942", label="upper-shell complete 06/07 corner"),
            Patch(facecolor=LOWER_COLOR, edgecolor="#303942", label="lower-shell straight 07 face"),
            Patch(facecolor=PCB_COLOR, edgecolor="#315f40", label="PCB: four side clearances; four holes locate XY"),
            Patch(facecolor=SEAM_COLOR, edgecolor=SEAM_COLOR, label="nominal zero-gap seam"),
        ],
        loc="lower center",
        ncol=4,
        bbox_to_anchor=(0.5, 0.015),
    )
    figure.suptitle(
        "Rounded-corner joint detail — no seam lies on the curved surface",
        fontsize=18,
        fontweight="bold",
    )
    figure.tight_layout(rect=(0.0, 0.10, 1.0, 0.93))
    figure.savefig(PREVIEW_DIR / "rounded-corner-seam-detail.png", bbox_inches="tight")
    plt.close(figure)


def _add_profile_patch(axis, shape: str, center_y: float, center_z: float, width: float, height: float, radius: float, feature_width: float, feature_height: float, **style) -> None:
    from matplotlib.patches import Circle, FancyBboxPatch, Polygon, Rectangle

    if shape == "circle":
        axis.add_patch(Circle((center_y, center_z), width / 2.0, **style))
    elif shape == "roundrect":
        axis.add_patch(
            FancyBboxPatch(
                (center_y - width / 2.0, center_z - height / 2.0),
                width,
                height,
                boxstyle=f"round,pad=0,rounding_size={radius}",
                **style,
            )
        )
    elif shape == "case_hdmi_hex":
        half_w = width / 2.0
        half_h = height / 2.0
        half_top = feature_width / 2.0
        axis.add_patch(
            Polygon(
                [
                    (center_y - half_top, center_z + half_h),
                    (center_y + half_top, center_z + half_h),
                    (center_y + half_w, center_z + half_h - feature_height),
                    (center_y + half_w, center_z - half_h),
                    (center_y - half_w, center_z - half_h),
                    (center_y - half_w, center_z + half_h - feature_height),
                ],
                closed=True,
                **style,
            )
        )
    elif shape == "rj45_main_plus_relief":
        axis.add_patch(
            FancyBboxPatch(
                (center_y - width / 2.0, center_z - height / 2.0),
                width,
                height,
                boxstyle=f"round,pad=0,rounding_size={radius}",
                **style,
            )
        )
        axis.add_patch(
            Rectangle(
                (center_y - feature_width / 2.0, center_z - height / 2.0 - feature_height),
                feature_width,
                feature_height,
                **style,
            )
        )
    elif shape == "rectangle":
        axis.add_patch(Rectangle((center_y - width / 2.0, center_z - height / 2.0), width, height, **style))
    else:
        raise ValueError(shape)


def _aperture_dimension_label(aperture: PanelApertureReference) -> str:
    if aperture.shape == "circle":
        return f"DIA {aperture.width_mm:g}"
    if aperture.shape == "case_hdmi_hex":
        return f"{aperture.width_mm:g} x {aperture.height_mm:g} hex"
    if aperture.shape == "rj45_main_plus_relief":
        return (
            f"{aperture.width_mm:g} x {aperture.height_mm:g}"
            f" + {aperture.feature_width_mm:g} x {aperture.feature_height_mm:g} relief"
        )
    return f"{aperture.width_mm:g} x {aperture.height_mm:g}"


def render_coverage(report: list[dict[str, object]]) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.patches import Circle, FancyBboxPatch, Rectangle

    figure = plt.figure(figsize=(18, 11), dpi=160, facecolor="#f4f7fa", layout="constrained")
    grid = figure.add_gridspec(
        2,
        2,
        height_ratios=(0.48, 1.0),
        width_ratios=(1.35, 1.0),
        hspace=0.18,
        wspace=0.10,
    )
    face_04_axis = figure.add_subplot(grid[0, 0])
    face_06_axis = figure.add_subplot(grid[0, 1])
    fan_axis = figure.add_subplot(grid[1, 0])
    table_axis = figure.add_subplot(grid[1, 1])

    report_map = {(row["aperture"]["face"], row["aperture"]["name"]): row for row in report}
    group_map = {(aperture.face, aperture.name): (aperture, targets) for aperture, targets in coverage_targets()}

    for face, axis in (("04", face_04_axis), ("06", face_06_axis)):
        axis.set_facecolor("#f9fbfc")
        axis.add_patch(
            Rectangle(
                (OUTER_Y_MIN_MM, INNER_Z_MIN_MM),
                OUTER_Y_MM,
                INNER_Z_MAX_MM - INNER_Z_MIN_MM,
                facecolor="#edf1f5",
                edgecolor="#53606b",
                linewidth=1.8,
            )
        )
        axis.axhspan(0.0, PCB_T_MM, color="#c8e6cf", alpha=0.75, label="PCB thickness")
        for pcb_edge_y in (-PCB_Y_MM / 2.0, +PCB_Y_MM / 2.0):
            axis.axvline(
                pcb_edge_y,
                color="#2f7d4b",
                linestyle="--",
                linewidth=1.1,
                alpha=0.9,
                zorder=2,
            )
        apertures = list(FACE_APERTURES[face])
        if face == "04":
            apertures.append(group_map[("04", "fin_exhaust")][0])
        for aperture in apertures:
            row = report_map[(aperture.face, aperture.name)]
            _add_profile_patch(
                axis,
                aperture.shape,
                aperture.center_y_mm,
                aperture.center_z_mm,
                aperture.width_mm,
                aperture.height_mm,
                aperture.corner_radius_mm,
                aperture.feature_width_mm,
                aperture.feature_height_mm,
                facecolor="none",
                edgecolor=APERTURE_COLOR,
                linewidth=2.2,
                zorder=4,
            )
            _, targets = group_map[(aperture.face, aperture.name)]
            coverage_pass = row["geometric_coverage_pass"]
            target_color = TARGET_COLOR if coverage_pass is not False else FAIL_COLOR
            for target in targets:
                _add_profile_patch(
                    axis,
                    target.shape,
                    target.center_y_mm,
                    target.center_z_mm,
                    target.width_mm,
                    target.height_mm,
                    target.corner_radius_mm,
                    0.0,
                    0.0,
                    facecolor=target_color,
                    edgecolor="#26313a",
                    linewidth=1.0,
                    alpha=0.62,
                    zorder=3,
                )
            if coverage_pass is None:
                result = "NOT MODELED"
                clearance_label = "N/A"
                result_color = UNEVALUATED_COLOR
            elif coverage_pass:
                result = "PASS"
                clearance_label = f"{row['minimum_nominal_clearance_mm']:+.2f} mm"
                result_color = "#29343d"
            else:
                result = "REVIEW"
                clearance_label = f"{row['minimum_nominal_clearance_mm']:+.2f} mm"
                result_color = FAIL_COLOR
            label_z = (
                aperture.center_z_mm
                if aperture.name == "fin_exhaust"
                else aperture.center_z_mm + aperture.height_mm / 2.0 + 0.65
            )
            axis.text(
                aperture.center_y_mm,
                label_z,
                f"{aperture.name}  {_aperture_dimension_label(aperture)}\n"
                f"{result} {clearance_label}",
                ha="center",
                va="center" if aperture.name == "fin_exhaust" else "bottom",
                fontsize=7.5,
                color=result_color,
                fontweight="bold",
            )
        axis.set_xlim(OUTER_Y_MIN_MM - 2.0, OUTER_Y_MAX_MM + 2.0)
        axis.set_ylim(INNER_Z_MIN_MM - 1.0, OUTER_Z_MAX_MM + 1.0)
        axis.set_aspect("equal")
        axis.grid(True, color=GRID_COLOR, linewidth=0.6)
        axis.set_ylabel("Z mm (fan side +)")
        if face == "04":
            axis.invert_xaxis()
            axis.set_xlabel("04 exterior view: 07 / +Y  <-  Y  ->  05 / -Y")
        else:
            axis.set_xlabel("06 exterior view: 05 / -Y  <-  Y  ->  07 / +Y")
        axis.set_title(f"{face} nominal apertures vs functional connector profiles", fontsize=13, fontweight="bold")

    fan_axis.set_facecolor("#f9fbfc")
    fan_axis.add_patch(
        FancyBboxPatch(
            (OUTER_Y_MIN_MM, OUTER_X_MIN_MM),
            OUTER_Y_MM,
            OUTER_X_MM,
            boxstyle=f"round,pad=0,rounding_size={OUTER_PLAN_CORNER_R_MM}",
            facecolor="#edf1f5",
            edgecolor="#53606b",
            linewidth=1.8,
        )
    )
    fan_display_x = -FAN_CENTER_XY_MM[1]
    fan_axis.add_patch(
        FancyBboxPatch(
            (-PCB_Y_MM / 2.0, -PCB_X_MM / 2.0),
            PCB_Y_MM,
            PCB_X_MM,
            boxstyle=f"round,pad=0,rounding_size={PCB_CORNER_R_MM}",
            facecolor="none",
            edgecolor="#2f7d4b",
            linestyle="--",
            linewidth=1.2,
        )
    )
    fan_axis.add_patch(Circle((fan_display_x, FAN_CENTER_XY_MM[0]), FAN_INTAKE_D_MM / 2.0, fill=False, edgecolor=APERTURE_COLOR, linewidth=2.8))
    fan_axis.add_patch(Circle((fan_display_x, FAN_CENTER_XY_MM[0]), FAN_INTAKE_D_MM / 2.0, facecolor=TARGET_COLOR, edgecolor="#26313a", alpha=0.42))
    fan_axis.text(
        fan_display_x,
        FAN_CENTER_XY_MM[0],
        f"fan intake / inlet\nDIA {FAN_INTAKE_D_MM:.1f}\nexact boundary",
        ha="center",
        va="center",
        fontsize=11,
        fontweight="bold",
    )
    for name, x, y in MOUNT_HOLES:
        fan_axis.add_patch(Circle((-y, x), MOUNT_HOLE_D_MM / 2.0, facecolor="white", edgecolor="#42505c", linewidth=1.0))
    fan_axis.set_xlim(-OUTER_Y_MAX_MM - 2.0, -OUTER_Y_MIN_MM + 2.0)
    fan_axis.set_ylim(OUTER_X_MIN_MM - 2.0, OUTER_X_MAX_MM + 2.0)
    fan_axis.set_aspect("equal")
    fan_axis.grid(True, color=GRID_COLOR, linewidth=0.6)
    fan_axis.set_xlabel("top view: 07 / +Y left, 05 / -Y right")
    fan_axis.set_ylabel("X mm: 06 up, 04 down")
    fan_axis.set_title("Top fan opening: no added fan clearance", fontsize=13, fontweight="bold")

    table_axis.axis("off")
    table_axis.set_title("Coverage result and review meaning", fontsize=13, fontweight="bold", pad=14)
    lines = []
    for row in report:
        aperture = row["aperture"]
        coverage_pass = row["geometric_coverage_pass"]
        if coverage_pass is None:
            mark = "N/A"
            clearance = "not modeled"
        else:
            mark = "PASS" if coverage_pass else "REVIEW"
            clearance = f"min {row['minimum_nominal_clearance_mm']:+.3f} mm"
        lines.append(f"{aperture['face']:>3}  {aperture['name']:<18} {mark:<6} {clearance}")
    lines.extend(
        [
            "",
            "Magenta: measured/reviewed panel aperture",
            "Gray: current connector/airflow functional profile",
            "Green dashed: PCB boundary",
            "N/A: exact functional front profile is not modeled",
            "",
            "No print clearance has been added.",
            "Unknown geometry is never replaced with a generic proxy.",
        ]
    )
    table_axis.text(
        0.02,
        0.96,
        "\n".join(lines),
        va="top",
        family="DejaVu Sans Mono",
        fontsize=10.2,
        color="#25313a",
    )
    figure.suptitle(
        "All enclosure openings — nominal coverage audit",
        fontsize=19,
        fontweight="bold",
        y=1.045,
    )
    figure.savefig(PREVIEW_DIR / "aperture-coverage-review.png", bbox_inches="tight")
    plt.close(figure)


def _add_hollow_vertical(axis, x_outer: float, x_inner: float, z0: float, z1: float, color: str, alpha: float = 0.85) -> None:
    from matplotlib.patches import Rectangle

    axis.add_patch(Rectangle((-x_outer, z0), x_outer - x_inner, z1 - z0, facecolor=color, edgecolor="#2f3943", alpha=alpha))
    axis.add_patch(Rectangle((x_inner, z0), x_outer - x_inner, z1 - z0, facecolor=color, edgecolor="#2f3943", alpha=alpha))


def render_clamp_section() -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, FancyBboxPatch, Patch, Rectangle

    figure, (plan_axis, section_axis) = plt.subplots(1, 2, figsize=(16, 9), dpi=160, facecolor="#f4f7fa")

    # Canonical fan-side plan: horizontal screen coordinate is -Y, vertical is X.
    plan_axis.add_patch(
        FancyBboxPatch(
            (-OUTER_Y_MAX_MM, OUTER_X_MIN_MM),
            OUTER_Y_MM,
            OUTER_X_MM,
            boxstyle=f"round,pad=0,rounding_size={OUTER_PLAN_CORNER_R_MM}",
            facecolor="#eef2f5",
            edgecolor="#33404a",
            linewidth=2.0,
        )
    )
    plan_axis.add_patch(
        FancyBboxPatch(
            (-PCB_Y_MM / 2.0, -PCB_X_MM / 2.0),
            PCB_Y_MM,
            PCB_X_MM,
            boxstyle=f"round,pad=0,rounding_size={PCB_CORNER_R_MM}",
            facecolor=PCB_COLOR,
            edgecolor="#315f40",
            linewidth=1.5,
            alpha=0.42,
        )
    )
    for name, x, y in MOUNT_HOLES:
        display_x = -y
        display_y = x
        plan_axis.add_patch(Circle((display_x, display_y), CLAMP_POST_OD_MM / 2.0, facecolor=UPPER_COLOR, edgecolor="#2f3943", alpha=0.72))
        plan_axis.add_patch(Circle((display_x, display_y), MOUNT_HOLE_D_MM / 2.0, facecolor="white", edgecolor="#2f3943"))
        plan_axis.text(display_x, display_y - 5.0, name, ha="center", va="top", fontsize=9)
    plan_axis.annotate("06 / +X", xy=(0, OUTER_X_MAX_MM + 2), ha="center", fontsize=11, fontweight="bold")
    plan_axis.annotate("04 / -X", xy=(0, OUTER_X_MIN_MM - 4), ha="center", fontsize=11, fontweight="bold")
    plan_axis.annotate("07 / +Y", xy=(-OUTER_Y_MAX_MM - 2, 0), va="center", rotation=90, fontsize=11, fontweight="bold")
    plan_axis.annotate("05 / -Y", xy=(OUTER_Y_MAX_MM + 5, 0), va="center", rotation=-90, fontsize=11, fontweight="bold")
    plan_axis.set_xlim(-OUTER_Y_MAX_MM - 8, OUTER_Y_MAX_MM + 8)
    plan_axis.set_ylim(OUTER_X_MIN_MM - 8, OUTER_X_MAX_MM + 8)
    plan_axis.set_aspect("equal")
    plan_axis.grid(True, color=GRID_COLOR)
    plan_axis.set_title("Four original PCB axes — no additional shell screws", fontsize=14, fontweight="bold")
    plan_axis.set_xlabel("screen horizontal = -Y")
    plan_axis.set_ylabel("screen vertical = X")

    section_axis.set_facecolor("#f9fbfc")
    # Plates and PCB are split around the central passage so the load path is visible.
    section_axis.add_patch(Rectangle((-10, INNER_Z_MAX_MM), 20, TOP_PLATE_T_MM, facecolor=UPPER_COLOR, edgecolor="#2f3943", alpha=0.82))
    _add_hollow_vertical(section_axis, CLAMP_POST_OD_MM / 2.0, UPPER_THREAD_PILOT_D_MM / 2.0, PCB_T_MM, INNER_Z_MAX_MM, UPPER_COLOR)
    section_axis.add_patch(Rectangle((-10, 0.0), 10 - MOUNT_HOLE_D_MM / 2.0, PCB_T_MM, facecolor=PCB_COLOR, edgecolor="#315f40", alpha=0.75))
    section_axis.add_patch(Rectangle((MOUNT_HOLE_D_MM / 2.0, 0.0), 10 - MOUNT_HOLE_D_MM / 2.0, PCB_T_MM, facecolor=PCB_COLOR, edgecolor="#315f40", alpha=0.75))
    _add_hollow_vertical(section_axis, CLAMP_POST_OD_MM / 2.0, LOWER_SCREW_CLEARANCE_D_MM / 2.0, INNER_Z_MIN_MM, 0.0, LOWER_COLOR)
    section_axis.add_patch(Rectangle((-10, OUTER_Z_MIN_MM), 10 - LOWER_SCREW_CLEARANCE_D_MM / 2.0, BOTTOM_PLATE_T_MM, facecolor=LOWER_COLOR, edgecolor="#2f3943", alpha=0.86))
    section_axis.add_patch(Rectangle((LOWER_SCREW_CLEARANCE_D_MM / 2.0, OUTER_Z_MIN_MM), 10 - LOWER_SCREW_CLEARANCE_D_MM / 2.0, BOTTOM_PLATE_T_MM, facecolor=LOWER_COLOR, edgecolor="#2f3943", alpha=0.86))
    section_axis.add_patch(
        Rectangle(
            (-1.5, OUTER_Z_MIN_MM - 0.8),
            3.0,
            PCB_T_MM - OUTER_Z_MIN_MM + 5.0,
            facecolor="#7b858e",
            edgecolor="#303940",
            linestyle="--",
            linewidth=1.2,
            alpha=0.42,
            zorder=4,
        )
    )
    section_axis.plot([0, 0], [OUTER_Z_MIN_MM - 1.0, INNER_Z_MAX_MM - 1.0], linestyle="--", color="#20272d", linewidth=1.5, zorder=5)
    section_axis.annotate("fastener shank aligns PCB hole", xy=(0, 0.75), xytext=(6.3, -8.5), arrowprops=dict(arrowstyle="->", lw=1.6), fontsize=10)
    section_axis.annotate("upper post / thread or insert pending", xy=(3.2, 8.0), xytext=(7.0, 10.8), arrowprops=dict(arrowstyle="->"), fontsize=9)
    section_axis.annotate("flat post shoulder; no printed nose", xy=(2.0, 1.5), xytext=(6.2, 3.2), arrowprops=dict(arrowstyle="->"), fontsize=9)
    section_axis.annotate("lower sleeve", xy=(3.2, -5.0), xytext=(7.0, -3.0), arrowprops=dict(arrowstyle="->"), fontsize=9)
    section_axis.annotate(f"top {TOP_PLATE_T_MM:g}", xy=(-9.0, OUTER_Z_MAX_MM), xytext=(-11.0, 18.0), arrowprops=dict(arrowstyle="-[", lw=1.2), fontsize=9)
    section_axis.annotate(f"bottom {BOTTOM_PLATE_T_MM:g}", xy=(-9.0, OUTER_Z_MIN_MM), xytext=(-11.0, -13.0), arrowprops=dict(arrowstyle="-[", lw=1.2), fontsize=9)
    section_axis.text(-11.5, 8.3, "upper shell carries/supports PCB\nwhen placed exterior-top-down", fontsize=9, color="#315f84")
    section_axis.text(-11.5, -7.3, "lower shell closes second\nand supplies clamp reaction", fontsize=9, color="#875824")
    section_axis.set_xlim(-12.5, 14.0)
    section_axis.set_ylim(OUTER_Z_MIN_MM - 2.0, OUTER_Z_MAX_MM + 2.5)
    section_axis.set_aspect("equal")
    section_axis.grid(True, color=GRID_COLOR)
    section_axis.set_xlabel("local radial section through one mounting hole / mm")
    section_axis.set_ylabel("project Z / mm")
    section_axis.set_title("Typical clamp section (repeated at all four measured axes)", fontsize=14, fontweight="bold")

    figure.legend(
        handles=[
            Patch(facecolor=UPPER_COLOR, edgecolor="#2f3943", label="upper shell/post"),
            Patch(facecolor=LOWER_COLOR, edgecolor="#2f3943", label="lower shell/sleeve"),
            Patch(facecolor=PCB_COLOR, edgecolor="#315f40", label="PCB"),
        ],
        loc="lower center",
        ncol=3,
        bbox_to_anchor=(0.5, 0.015),
    )
    figure.suptitle("Four-hole clamp chain — same PCB axes locate the board and close both shells", fontsize=18, fontweight="bold")
    figure.text(
        0.5,
        0.065,
        "Two diagonal fastener shanks provide temporary alignment. Head/thread form remains provisional; no printed nose or extra axes.",
        ha="center",
        fontsize=10,
        color="#4d5965",
    )
    figure.tight_layout(rect=(0.0, 0.09, 1.0, 0.94))
    figure.savefig(PREVIEW_DIR / "four-hole-clamp-section.png", bbox_inches="tight")
    plt.close(figure)


def build_validation(geometry: dict[str, cq.Shape], coverage: list[dict[str, object]]) -> dict[str, object]:
    seam_closed = all(
        max(
            abs(end_value - start_value)
            for end_value, start_value in zip(
                segment.end_xyz_mm,
                SEAM_PATH[(index + 1) % len(SEAM_PATH)].start_xyz_mm,
            )
        )
        <= 1e-6
        for index, segment in enumerate(SEAM_PATH)
    )
    aperture_residuals: dict[str, float] = {}
    for face in ("04", "06"):
        for aperture in FACE_APERTURES[face]:
            residual = intersection_volume(geometry[face], make_aperture_cutter(aperture))
            aperture_residuals[f"{face}:{aperture.name}"] = round(residual, 6)
    aperture_residuals["04:fin_exhaust"] = round(
        intersection_volume(geometry["04"], geometry["fin_exhaust_cutter"]), 6
    )

    part_interference = {
        "upper_posts_vs_connectors_mm3": round(intersection_volume(geometry["upper_posts"], geometry["motherboard_connectors"]), 6),
        "upper_posts_vs_cooling_mm3": round(intersection_volume(geometry["upper_posts"], geometry["motherboard_cooling"]), 6),
        "lower_posts_vs_connectors_mm3": round(intersection_volume(geometry["lower_posts"], geometry["motherboard_connectors"]), 6),
        "lower_posts_vs_underside_keepouts_mm3": round(intersection_volume(geometry["lower_posts"], geometry["motherboard_underside_keepouts"]), 6),
        "six_faces_vs_motherboard_mm3": {
            face: round(intersection_volume(geometry[face], geometry["motherboard"]), 6)
            for face in ("top", "bottom", "04", "05", "06", "07")
        },
    }
    part_interference["six_faces_vs_pcb_only_mm3"] = {
        face: round(intersection_volume(geometry[face], geometry["motherboard_pcb"]), 6)
        for face in ("top", "bottom", "04", "05", "06", "07")
    }

    # Containment is distinct from non-intersection.  Compare the PCB against
    # the deliberately expanded inner cavity, then compare the outer plan with
    # the exact constant-thickness offset of that cavity (not of the PCB).
    plan_probe_height = 1.0
    pcb_plan = rounded_plate_xy(
        PCB_X_MM,
        PCB_Y_MM,
        PCB_CORNER_R_MM,
        plan_probe_height,
        0.0,
    ).val()
    inner_plan = rounded_plate_xy(
        INNER_X_MAX_MM - INNER_X_MIN_MM,
        INNER_Y_MAX_MM - INNER_Y_MIN_MM,
        INNER_PLAN_CORNER_R_MM,
        plan_probe_height,
        0.0,
    ).translate((INNER_PLAN_CENTER_X_MM, INNER_PLAN_CENTER_Y_MM, 0.0)).val()
    outer_plan = rounded_plate_xy(
        OUTER_X_MM,
        OUTER_Y_MM,
        OUTER_PLAN_CORNER_R_MM,
        plan_probe_height,
        0.0,
    ).translate((OUTER_PLAN_CENTER_X_MM, OUTER_PLAN_CENTER_Y_MM, 0.0)).val()
    exact_offset_plan = rounded_plate_xy(
        INNER_X_MAX_MM - INNER_X_MIN_MM + 2.0 * SIDE_WALL_T_MM,
        INNER_Y_MAX_MM - INNER_Y_MIN_MM + 2.0 * SIDE_WALL_T_MM,
        INNER_PLAN_CORNER_R_MM + SIDE_WALL_T_MM,
        plan_probe_height,
        0.0,
    ).translate((INNER_PLAN_CENTER_X_MM, INNER_PLAN_CENTER_Y_MM, 0.0)).val()
    plan_fit_validation = {
        "pcb_volume_outside_inner_cavity_mm3": round(
            difference_volume(pcb_plan, inner_plan),
            6,
        ),
        "pcb_volume_outside_outer_plan_mm3": round(
            difference_volume(pcb_plan, outer_plan),
            6,
        ),
        "exact_offset_volume_missing_from_outer_plan_mm3": round(
            difference_volume(exact_offset_plan, outer_plan),
            6,
        ),
        "outer_plan_volume_excess_over_exact_offset_mm3": round(
            difference_volume(outer_plan, exact_offset_plan),
            6,
        ),
        "straight_wall_thickness_mm": SIDE_WALL_T_MM,
        "corner_radial_wall_thickness_mm": round(
            OUTER_PLAN_CORNER_R_MM - INNER_PLAN_CORNER_R_MM,
            6,
        ),
    }

    # A mid-wall slice avoids the deliberate interface apertures, top/bottom
    # fastener holes and plate overlaps.  It directly detects any missing wedge
    # caused by the four face-ownership splits at the rounded corners.
    corner_expected = make_rounded_wall_ring(2.0, 7.0)
    corner_actual = (
        geometry["04"]
        .fuse(geometry["05"])
        .fuse(geometry["06"])
        .fuse(geometry["07"])
    )
    rounded_corner_missing: dict[str, float] = {}
    rounded_corner_owner_missing: dict[str, float] = {}
    for name, sign_x, sign_y in (
        ("06_07", +1.0, +1.0),
        ("04_05", -1.0, -1.0),
        ("06_05", +1.0, -1.0),
        ("04_07", -1.0, +1.0),
    ):
        corner_probe_size = OUTER_PLAN_CORNER_R_MM
        probe = (
            cq.Workplane("XY")
            .box(corner_probe_size, corner_probe_size, 5.0, centered=(True, True, False))
            .translate(
                (
                    (OUTER_X_MAX_MM - corner_probe_size / 2.0)
                    if sign_x > 0.0
                    else (OUTER_X_MIN_MM + corner_probe_size / 2.0),
                    (OUTER_Y_MAX_MM - corner_probe_size / 2.0)
                    if sign_y > 0.0
                    else (OUTER_Y_MIN_MM + corner_probe_size / 2.0),
                    2.0,
                )
            )
            .val()
        )
        expected_probe = corner_expected.intersect(probe)
        actual_probe = corner_actual.intersect(probe)
        rounded_corner_missing[name] = round(
            difference_volume(expected_probe, actual_probe),
            6,
        )
        owner_face = "06" if sign_x > 0.0 else "04"
        owner_probe = geometry[owner_face].intersect(probe)
        rounded_corner_owner_missing[name] = round(
            difference_volume(expected_probe, owner_probe),
            6,
        )
    coverage_failures = [
        f"{row['aperture']['face']}:{row['aperture']['name']}"
        for row in coverage
        if row["geometric_coverage_pass"] is False
    ]
    coverage_not_evaluated = [
        f"{row['aperture']['face']}:{row['aperture']['name']}"
        for row in coverage
        if row["geometric_coverage_pass"] is None
    ]
    generated_enclosure_cad = sorted(
        str(path.relative_to(ROOT))
        for path in ROOT.glob("exports/**/*")
        if path.is_file()
        and path.suffix.lower() in {".step", ".stp", ".stl"}
        and any(token in path.name.lower() for token in ("case", "enclosure", "shell"))
    )
    v2_prototype_complete = all((V2_EXPORT_DIR / name).is_file() for name in V2_EXPECTED_CAD)
    checks = {
        "face_ownership_is_two_integral_three_face_shells": FACE_OWNERSHIP
        == {"top": "upper", "06": "upper", "05": "upper", "bottom": "lower", "04": "lower", "07": "lower"},
        "upper_and_lower_are_each_one_fused_solid": (
            len(geometry["upper_shell_review"].Solids()) == 1
            and len(geometry["lower_shell_review"].Solids()) == 1
        ),
        "top_and_bottom_are_exactly_1p2mm": TOP_PLATE_T_MM == 1.2 and BOTTOM_PLATE_T_MM == 1.2,
        "outer_body_z_is_28p0_without_extra_fan_gap": abs(OUTER_Z_MM - 28.0) < 1e-9,
        "rounded_plan_corners_are_present": (
            OUTER_PLAN_CORNER_R_MM > 0.0
            and INNER_PLAN_CORNER_R_MM > 0.0
            and OUTER_PLAN_CORNER_R_MM > INNER_PLAN_CORNER_R_MM
        ),
        "rounded_corner_midwall_has_no_geometric_gap": all(
            value <= 1e-5 for value in rounded_corner_missing.values()
        ),
        "each_rounded_corner_is_wholly_owned_by_one_shell": all(
            value <= 1e-5 for value in rounded_corner_owner_missing.values()
        ),
        "pcb_plan_has_reviewed_face_clearances": (
            abs(INNER_X_MIN_MM - (-PCB_X_MM / 2.0 - PCB_CLEARANCE_04_MM)) <= 1e-9
            and abs(INNER_X_MAX_MM - (+PCB_X_MM / 2.0 + PCB_CLEARANCE_06_MM)) <= 1e-9
            and abs(INNER_Y_MIN_MM - (-PCB_Y_MM / 2.0 - PCB_CLEARANCE_05_MM)) <= 1e-9
            and abs(INNER_Y_MAX_MM - (+PCB_Y_MM / 2.0 + PCB_CLEARANCE_07_MM)) <= 1e-9
            and abs(INNER_PLAN_CORNER_R_MM - PCB_CORNER_R_MM) <= 1e-9
        ),
        "original_case_04_06_inner_span_matches_user_measurement": (
            abs((INNER_X_MAX_MM - INNER_X_MIN_MM) - 103.0) <= 1e-9
        ),
        "05_07_use_compact_0p2mm_fit_allowance_not_original_extra_space": (
            abs(PCB_CLEARANCE_05_MM - 0.2) <= 1e-9
            and abs(PCB_CLEARANCE_07_MM - 0.2) <= 1e-9
        ),
        "side_wall_is_user_measured_1p8mm": abs(SIDE_WALL_T_MM - 1.8) <= 1e-9,
        "face_06_inner_wall_uses_usb_front_plane": (
            abs(INNER_X_MAX_MM - (PCB_X_MM / 2.0 + 1.0)) <= 1e-9
        ),
        "connector_front_span_closes_measured_103mm_inner_width": (
            abs(CONNECTOR_FRONT_SPAN_X_MM - 103.0) <= 1e-9
        ),
        "button_axial_stack_is_wall_plus_recessed_switch_gap": (
            abs(
                BUTTON_OUTER_WALL_TO_SWITCH_TIP_MM
                - SIDE_WALL_T_MM
                - BUTTON_INNER_WALL_TO_SWITCH_TIP_MM
            ) <= 1e-9
            and BUTTON_INNER_GAP_RANGE_MM[0] > 0.0
        ),
        "pcb_plan_is_fully_contained_by_inner_cavity": (
            plan_fit_validation["pcb_volume_outside_inner_cavity_mm3"] <= 1e-5
        ),
        "pcb_plan_is_fully_contained_by_outer_enclosure_plan": (
            plan_fit_validation["pcb_volume_outside_outer_plan_mm3"] <= 1e-5
        ),
        "outer_plan_is_exact_constant_thickness_offset_of_inner_cavity": (
            plan_fit_validation["exact_offset_volume_missing_from_outer_plan_mm3"] <= 1e-5
            and plan_fit_validation["outer_plan_volume_excess_over_exact_offset_mm3"] <= 1e-5
            and abs(
                plan_fit_validation["corner_radial_wall_thickness_mm"]
                - SIDE_WALL_T_MM
            ) <= 1e-9
        ),
        "seam_is_one_closed_six_segment_path": len(SEAM_PATH) == 6 and seam_closed,
        "nominal_seam_has_no_unreviewed_gap": NOMINAL_SEAM_GAP_MM == 0.0,
        "only_four_original_pcb_axes_used": len(MOUNT_HOLES) == 4,
        "upper_posts_end_flat_at_pcb_top_without_locator_noses": all(
            abs(solid.BoundingBox().zmin - PCB_T_MM) <= 1e-6
            for solid in geometry["upper_posts"].Solids()
        ),
        "lower_sleeves_end_at_pcb_bottom": all(
            abs(solid.BoundingBox().zmax) <= 1e-6
            for solid in geometry["lower_posts"].Solids()
        ),
        "all_face_and_post_review_shapes_valid": all(
            geometry[name].isValid()
            for name in ("top", "bottom", "04", "05", "06", "07", "upper_posts", "lower_posts")
        ),
        "04_and_06_are_each_continuous_planar_wall_solids_after_openings": (
            len(geometry["04"].Solids()) == 1 and len(geometry["06"].Solids()) == 1
        ),
        "all_cutters_fully_remove_panel_material": all(value <= 1e-5 for value in aperture_residuals.values()),
        "clamp_posts_clear_current_component_and_keepout_models": all(
            value <= 1e-5
            for key, value in part_interference.items()
            if key not in {"six_faces_vs_motherboard_mm3", "six_faces_vs_pcb_only_mm3"}
        ),
        "all_six_faces_have_zero_volume_overlap_with_pcb_body": all(
            value <= 1e-5 for value in part_interference["six_faces_vs_pcb_only_mm3"].values()
        ),
        "board_switch_remains_behind_face_06_inner_wall": (
            SWITCH_ACTUATOR_TIP_X_MM <= INNER_X_MAX_MM + 1e-9
        ),
        "non_interface_faces_clear_current_motherboard_model": all(
            part_interference["six_faces_vs_motherboard_mm3"][face] <= 1e-5
            for face in ("top", "bottom", "05", "07")
        ),
        "05_and_07_have_no_apertures": True,
        "v2_prototype_step_stl_complete": v2_prototype_complete,
    }
    internal_pass = all(
        value is True
        for key, value in checks.items()
        if key != "v2_prototype_step_stl_complete"
    )
    return {
        "scope": "enclosure structure and V2 prototype-source validation",
        "checks": checks,
        "internal_structure_checks_pass": internal_pass,
        "nominal_aperture_coverage_failures": coverage_failures,
        "aperture_coverage_not_evaluated": coverage_not_evaluated,
        "review_gate": (
            "V2 fit-check prototype authorized and generated; provisional parameters prevent final-production designation"
            if v2_prototype_complete
            else "V2 fit-check prototype authorized; CAD output not yet complete"
        ),
        "aperture_cutter_residuals_mm3": aperture_residuals,
        "part_interference": part_interference,
        "interface_body_proxy_note": (
            "Faces 04/06 are outward-offset continuous planar walls. Full connector-body boxes remain conservative hidden proxies; "
            "reported proxy intersections cannot enlarge or reshape the reviewed exterior apertures. PCB containment, through-cut apertures and qualified front-profile coverage are the pass criteria."
        ),
        "plan_fit_validation": plan_fit_validation,
        "rounded_corner_midwall_missing_mm3": rounded_corner_missing,
        "rounded_corner_owner_missing_mm3": rounded_corner_owner_missing,
        "detected_enclosure_cad_files": generated_enclosure_cad,
    }


def main() -> None:
    geometry = build_review_geometry()
    coverage = build_coverage_report()
    v2_prototype_complete = all((V2_EXPORT_DIR / name).is_file() for name in V2_EXPECTED_CAD)
    definition = structure_definition(
        output_stage="v2-prototype" if v2_prototype_complete else "structure-review",
        enclosure_step_stl_generated=v2_prototype_complete,
    )
    validation = build_validation(geometry, coverage)

    STRUCTURE_JSON.write_text(json.dumps(definition, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    COVERAGE_JSON.write_text(
        json.dumps(
            {
                "status": "nominal geometry coverage; no print/process clearance",
                "rule": (
                    "Only measured or explicitly qualified functional profiles are compared. "
                    "Unknown profiles remain not evaluated; measured apertures are never changed from a generic proxy."
                ),
                "results": coverage,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    VALIDATION_JSON.write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    render_assembly(geometry)
    render_face_ownership_and_seam()
    render_rounded_corner_seam_detail()
    render_clamp_section()
    render_coverage(coverage)

    if not validation["internal_structure_checks_pass"]:
        raise RuntimeError(f"enclosure structure validation failed: {validation['checks']}")
    print(f"Wrote structure review diagrams to {PREVIEW_DIR}")
    print(f"Wrote {STRUCTURE_JSON}")
    print(f"Wrote {COVERAGE_JSON}")
    print(f"Wrote {VALIDATION_JSON}")
    print(json.dumps(validation["checks"], ensure_ascii=False, indent=2))
    print(f"Nominal coverage failures: {validation['nominal_aperture_coverage_failures']}")
    print(f"Coverage not evaluated: {validation['aperture_coverage_not_evaluated']}")


if __name__ == "__main__":
    main()
