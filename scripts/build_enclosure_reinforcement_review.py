#!/usr/bin/env python3
"""Render the approved internal rib plans and collision checks.

This script never writes enclosure STEP/STL.  It visualizes the approved rib
centerlines stored in ``n305_enclosure_structure`` and verifies them
against the top cooling keepout, the face-04 stacked dual USB connector and
the complete current motherboard reference.
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
    BOTTOM_REINFORCEMENT_SEGMENTS,
    FAN_CENTER_XY_MM,
    FAN_INTAKE_D_MM,
    INNER_X_MAX_MM,
    INNER_X_MIN_MM,
    INNER_Y_MAX_MM,
    INNER_Y_MIN_MM,
    INNER_Z_MAX_MM,
    INNER_Z_MIN_MM,
    MOUNT_HOLES,
    OUTER_PLAN_CENTER_X_MM,
    OUTER_PLAN_CENTER_Y_MM,
    OUTER_PLAN_CORNER_R_MM,
    OUTER_X_MAX_MM,
    OUTER_X_MIN_MM,
    OUTER_X_MM,
    OUTER_Y_MAX_MM,
    OUTER_Y_MIN_MM,
    OUTER_Y_MM,
    PCB_CORNER_R_MM,
    PCB_X_MM,
    PCB_Y_MM,
    REINFORCEMENT_COMPONENT_CLEARANCE_MM,
    REINFORCEMENT_REVIEW_STATUS,
    REINFORCEMENT_RIB_HEIGHT_MM,
    REINFORCEMENT_RIB_WIDTH_MM,
    TOP_REINFORCEMENT_SEGMENTS,
    make_face_solids,
    make_reinforcement_review_geometry,
)
from n305_mainboard_reference import (  # noqa: E402
    FAN_PROFILE_UNCERTAINTY_MM,
    FAN_SHELL_PROFILE_XY_MM,
    FIN_STACK_CENTER_X_MM,
    FIN_STACK_CENTER_Y_MM,
    FIN_STACK_X_MM,
    FIN_STACK_Y_MM,
)


PREVIEW_DIR = ROOT / "previews" / "enclosure"
DOCS_DIR = ROOT / "docs"
PLAN_PNG = PREVIEW_DIR / "reinforcement-inner-plan.png"
COLLISION_PNG = PREVIEW_DIR / "reinforcement-collision-check.png"
REVIEW_MD = DOCS_DIR / "enclosure-reinforcement-review.md"
VALIDATION_JSON = DOCS_DIR / "enclosure-reinforcement-validation.json"

RIB_COLOR = "#276fbf"
TOP_PLATE_COLOR = "#8bb8eb"
BOTTOM_PLATE_COLOR = "#f0b66f"
PCB_COLOR = "#65a86f"
KEEP_OUT_COLOR = "#d94b54"
SECONDARY_KEEP_OUT_COLOR = "#d18c32"
POST_COLOR = "#38434e"
GRID_COLOR = "#d8dee7"


def intersection_volume(left: cq.Shape, right: cq.Shape) -> float:
    return sum(
        left_solid.intersect(right_solid).Volume()
        for left_solid in left.Solids()
        for right_solid in right.Solids()
    )


def minimum_distance(left: cq.Shape, right: cq.Shape) -> float:
    distances = [
        left_solid.distance(right_solid)
        for left_solid in left.Solids()
        for right_solid in right.Solids()
    ]
    return min(distances) if distances else math.inf


def segment_polygon(segment, width: float) -> list[tuple[float, float]]:
    x0, y0 = segment.start_xy_mm
    x1, y1 = segment.end_xy_mm
    length = math.hypot(x1 - x0, y1 - y0)
    nx = -(y1 - y0) / length * width / 2.0
    ny = +(x1 - x0) / length * width / 2.0
    return [
        (x0 + nx, y0 + ny),
        (x1 + nx, y1 + ny),
        (x1 - nx, y1 - ny),
        (x0 - nx, y0 - ny),
    ]


def add_plan_outline(axis, face_color: str) -> None:
    from matplotlib.patches import FancyBboxPatch

    axis.add_patch(FancyBboxPatch(
        (OUTER_X_MIN_MM, OUTER_Y_MIN_MM),
        OUTER_X_MM,
        OUTER_Y_MM,
        boxstyle=f"round,pad=0,rounding_size={OUTER_PLAN_CORNER_R_MM}",
        facecolor=face_color,
        edgecolor="#24303a",
        linewidth=2.0,
        alpha=0.30,
    ))
    axis.add_patch(FancyBboxPatch(
        (-PCB_X_MM / 2.0, -PCB_Y_MM / 2.0),
        PCB_X_MM,
        PCB_Y_MM,
        boxstyle=f"round,pad=0,rounding_size={PCB_CORNER_R_MM}",
        facecolor="none",
        edgecolor=PCB_COLOR,
        linewidth=1.6,
        linestyle=(0, (5, 3)),
    ))


def add_ribs(axis, segments) -> None:
    from matplotlib.patches import Polygon

    for segment in segments:
        axis.add_patch(Polygon(
            segment_polygon(segment, REINFORCEMENT_RIB_WIDTH_MM),
            closed=True,
            facecolor=RIB_COLOR,
            edgecolor="#154978",
            linewidth=0.8,
            alpha=0.92,
        ))


def add_mount_holes(axis) -> None:
    from matplotlib.patches import Circle

    for name, x, y in MOUNT_HOLES:
        axis.add_patch(Circle((x, y), 3.2, facecolor="#ffffff", edgecolor=POST_COLOR, linewidth=1.4))
        axis.add_patch(Circle((x, y), 1.6, facecolor="none", edgecolor="#101820", linewidth=1.0))
        axis.text(x, y + 4.2, name, ha="center", va="bottom", fontsize=7.5, color="#25313b")


def format_plan_axis(axis, title: str) -> None:
    axis.set_xlim(OUTER_X_MIN_MM - 4.0, OUTER_X_MAX_MM + 4.0)
    axis.set_ylim(OUTER_Y_MIN_MM - 4.0, OUTER_Y_MAX_MM + 4.0)
    axis.set_aspect("equal", adjustable="box")
    axis.set_xlabel("CAD X / mm   (-04  ←  →  +06)")
    axis.set_ylabel("CAD Y / mm   (-05  ←  →  +07)")
    axis.grid(True, color=GRID_COLOR, linewidth=0.7)
    axis.set_title(title, fontsize=14, fontweight="bold")


def render_plan(geometry: dict[str, object], metrics: dict[str, float]) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.patches import Circle, Patch, Polygon, Rectangle

    figure, (top_axis, bottom_axis) = plt.subplots(1, 2, figsize=(18, 9), dpi=170, facecolor="#f4f7fa")
    figure.suptitle(
        "Approved internal reinforcement plan — base plates remain 1.2 mm",
        fontsize=19,
        fontweight="bold",
    )

    add_plan_outline(top_axis, TOP_PLATE_COLOR)
    add_ribs(top_axis, TOP_REINFORCEMENT_SEGMENTS)
    add_mount_holes(top_axis)
    top_axis.add_patch(Polygon(
        FAN_SHELL_PROFILE_XY_MM,
        closed=True,
        facecolor=KEEP_OUT_COLOR,
        edgecolor="#7f1720",
        linewidth=1.5,
        alpha=0.38,
    ))
    top_axis.add_patch(Rectangle(
        (FIN_STACK_CENTER_X_MM - FIN_STACK_X_MM / 2.0, FIN_STACK_CENTER_Y_MM - FIN_STACK_Y_MM / 2.0),
        FIN_STACK_X_MM,
        FIN_STACK_Y_MM,
        facecolor=SECONDARY_KEEP_OUT_COLOR,
        edgecolor="#7c5017",
        linewidth=1.5,
        alpha=0.38,
    ))
    top_axis.add_patch(Circle(
        FAN_CENTER_XY_MM,
        FAN_INTAKE_D_MM / 2.0,
        facecolor="white",
        edgecolor="#7f1720",
        linewidth=1.3,
        alpha=0.85,
    ))
    top_env = geometry["top_clearance_envelope"].BoundingBox()
    top_axis.add_patch(Rectangle(
        (top_env.xmin, top_env.ymin),
        top_env.xlen,
        top_env.ylen,
        fill=False,
        edgecolor=KEEP_OUT_COLOR,
        linewidth=1.6,
        linestyle=(0, (6, 3)),
    ))
    top_axis.text(
        49.5,
        -49.5,
        f"rib {REINFORCEMENT_RIB_WIDTH_MM:.1f} W × {REINFORCEMENT_RIB_HEIGHT_MM:.1f} H mm\n"
        f"cooling collision = {metrics['top_ribs_vs_cooling_mm3']:.3f} mm³",
        ha="right",
        va="bottom",
        fontsize=9.5,
        bbox=dict(boxstyle="round,pad=0.4", facecolor="#e8f5ea", edgecolor="#4e8d58"),
    )
    format_plan_axis(top_axis, "Upper-shell inner face: bypass blower and complete fin stack")

    add_plan_outline(bottom_axis, BOTTOM_PLATE_COLOR)
    add_ribs(bottom_axis, BOTTOM_REINFORCEMENT_SEGMENTS)
    add_mount_holes(bottom_axis)
    for solid in geometry["underside_keepouts"].Solids():
        bounds = solid.BoundingBox()
        bottom_axis.add_patch(Rectangle(
            (bounds.xmin, bounds.ymin),
            bounds.xlen,
            bounds.ylen,
            facecolor="#7a858e",
            edgecolor="#4b565f",
            linewidth=0.9,
            alpha=0.16,
        ))
    for name, shape in geometry["low_connectors"].items():
        bounds = shape.BoundingBox()
        is_dual_usb = name.startswith("stack_usb")
        bottom_axis.add_patch(Rectangle(
            (bounds.xmin, bounds.ymin),
            bounds.xlen,
            bounds.ylen,
            facecolor=KEEP_OUT_COLOR if is_dual_usb else SECONDARY_KEEP_OUT_COLOR,
            edgecolor="#7f1720" if is_dual_usb else "#7c5017",
            linewidth=1.2,
            alpha=0.40 if is_dual_usb else 0.24,
        ))
    usb_env = geometry["bottom_usb_clearance_envelope"].BoundingBox()
    bottom_axis.add_patch(Rectangle(
        (usb_env.xmin, usb_env.ymin),
        usb_env.xlen,
        usb_env.ylen,
        fill=False,
        edgecolor=KEEP_OUT_COLOR,
        linewidth=1.8,
        linestyle=(0, (6, 3)),
    ))
    bottom_axis.annotate(
        "stacked dual USB hard keepout\nlower body reaches Z ≈ -10.29",
        xy=(usb_env.xmax, (usb_env.ymin + usb_env.ymax) / 2.0),
        xytext=(-15.0, -8.0),
        arrowprops=dict(arrowstyle="->", color="#7f1720", linewidth=1.3),
        fontsize=9.5,
        color="#66151c",
    )
    bottom_axis.text(
        49.5,
        -43.0,
        f"rib {REINFORCEMENT_RIB_WIDTH_MM:.1f} W × {REINFORCEMENT_RIB_HEIGHT_MM:.1f} H mm\n"
        f"dual-USB collision = {metrics['bottom_ribs_vs_dual_usb_mm3']:.3f} mm³",
        ha="right",
        va="bottom",
        fontsize=9.5,
        bbox=dict(boxstyle="round,pad=0.4", facecolor="#e8f5ea", edgecolor="#4e8d58"),
    )
    format_plan_axis(bottom_axis, "Lower-shell inner face: bypass deepest face-04 connector bodies")

    legend_items = [
        Patch(facecolor=RIB_COLOR, edgecolor="#154978", label="approved rib footprint"),
        Patch(facecolor=KEEP_OUT_COLOR, edgecolor="#7f1720", alpha=0.45, label="mandatory fan / dual-USB keepout"),
        Patch(facecolor=SECONDARY_KEEP_OUT_COLOR, edgecolor="#7c5017", alpha=0.40, label="fins / other low connector"),
        Patch(facecolor="#7a858e", edgecolor="#4b565f", alpha=0.20, label="underside proxy (vertically clear)"),
        Line2D([0], [0], color=PCB_COLOR, linestyle=(0, (5, 3)), label="PCB plan boundary"),
    ]
    figure.legend(handles=legend_items, loc="lower center", ncol=5, frameon=True, bbox_to_anchor=(0.5, 0.015))
    figure.text(
        0.5,
        0.055,
        "Inside-cavity view in the project CAD frame. Dashed red boundary includes the provisional 1.0 mm review clearance.",
        ha="center",
        fontsize=10,
        color="#3e4952",
    )
    figure.tight_layout(rect=(0.02, 0.09, 0.98, 0.94))
    figure.savefig(PLAN_PNG, bbox_inches="tight")
    plt.close(figure)


def add_shape(axis, shape: cq.Shape, color: str, alpha: float, edge_alpha: float = 0.10) -> None:
    import numpy as np
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    vertices, triangles = shape.tessellate(0.18)
    coordinates = np.asarray([(point.x, point.y, point.z) for point in vertices], dtype=float)
    faces = coordinates[np.asarray(triangles, dtype=int)]
    axis.add_collection3d(Poly3DCollection(
        faces,
        facecolor=color,
        edgecolor=(0.05, 0.07, 0.09, edge_alpha),
        linewidth=0.12,
        alpha=alpha,
    ))


def add_topology_edges(axis, shape: cq.Shape, color: str) -> None:
    for edge in shape.Edges():
        try:
            points, _ = edge.sample(0.3)
        except (ValueError, ZeroDivisionError):
            points, _ = edge.sample(16)
        if len(points) < 2:
            continue
        axis.plot3D(
            [point.x for point in points],
            [point.y for point in points],
            [point.z for point in points],
            color=color,
            linewidth=0.75,
            alpha=0.88,
        )


def z_slice(shape: cq.Shape, z0: float, z1: float) -> cq.Shape:
    slab = (
        cq.Workplane("XY")
        .box(140.0, 140.0, z1 - z0, centered=(True, True, False))
        .translate((0.0, 0.0, z0))
        .val()
    )
    return shape.intersect(slab)


def format_3d_axis(axis, z_limits: tuple[float, float], title: str) -> None:
    axis.set_xlim(OUTER_X_MIN_MM - 4.0, OUTER_X_MAX_MM + 4.0)
    axis.set_ylim(OUTER_Y_MIN_MM - 4.0, OUTER_Y_MAX_MM + 4.0)
    axis.set_zlim(*z_limits)
    axis.set_box_aspect((OUTER_X_MM, OUTER_Y_MM, 16.0))
    axis.set_xlabel("X: +06 / -04", labelpad=7)
    axis.set_ylabel("Y: +07 / -05", labelpad=7)
    axis.set_zlabel("Z / mm", labelpad=7)
    axis.set_title(title, fontsize=14, fontweight="bold")
    axis.grid(True, color=GRID_COLOR)
    axis.set_proj_type("ortho")
    axis.view_init(elev=28, azim=-54)


def render_collision(geometry: dict[str, object], metrics: dict[str, float]) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    faces = make_face_solids()
    figure = plt.figure(figsize=(18, 9), dpi=170, facecolor="#f4f7fa")
    top_axis = figure.add_subplot(121, projection="3d")
    bottom_axis = figure.add_subplot(122, projection="3d")
    figure.suptitle(
        "Reinforcement collision audit — exact solids, not a pixel overlay",
        fontsize=19,
        fontweight="bold",
    )

    top_cooling_slice = z_slice(geometry["cooling_keepout"], INNER_Z_MAX_MM - 1.2, INNER_Z_MAX_MM + 0.1)
    add_shape(top_axis, faces["top"], TOP_PLATE_COLOR, 0.20)
    add_shape(top_axis, geometry["top_ribs"], RIB_COLOR, 0.95)
    add_shape(top_axis, top_cooling_slice, KEEP_OUT_COLOR, 0.62)
    add_topology_edges(top_axis, geometry["top_ribs"], "#123f69")
    add_topology_edges(top_axis, top_cooling_slice, "#7f1720")
    format_3d_axis(top_axis, (INNER_Z_MAX_MM - 1.5, INNER_Z_MAX_MM + 1.8), "Upper: ribs remain outside blower + fins")
    top_axis.text2D(
        0.03,
        0.04,
        "PASS\n"
        f"solid overlap: {metrics['top_ribs_vs_cooling_mm3']:.3f} mm³\n"
        f"1.0 mm envelope overlap: {metrics['top_ribs_vs_cooling_envelope_mm3']:.3f} mm³\n"
        f"minimum exact-solid distance: {metrics['top_ribs_to_cooling_mm']:.2f} mm",
        transform=top_axis.transAxes,
        fontsize=10,
        color="#245f30",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#e8f5ea", edgecolor="#4e8d58"),
    )

    bottom_usb_slice = z_slice(geometry["dual_usb"], INNER_Z_MIN_MM - 0.1, INNER_Z_MIN_MM + 1.2)
    add_shape(bottom_axis, faces["bottom"], BOTTOM_PLATE_COLOR, 0.20)
    add_shape(bottom_axis, geometry["bottom_ribs"], RIB_COLOR, 0.95)
    add_shape(bottom_axis, bottom_usb_slice, KEEP_OUT_COLOR, 0.75)
    for name, connector in geometry["low_connectors"].items():
        if name.startswith("stack_usb"):
            continue
        connector_slice = z_slice(connector, INNER_Z_MIN_MM - 0.1, INNER_Z_MIN_MM + 1.2)
        if connector_slice.Solids():
            add_shape(bottom_axis, connector_slice, SECONDARY_KEEP_OUT_COLOR, 0.48)
    add_topology_edges(bottom_axis, geometry["bottom_ribs"], "#123f69")
    add_topology_edges(bottom_axis, bottom_usb_slice, "#7f1720")
    format_3d_axis(bottom_axis, (INNER_Z_MIN_MM - 1.6, INNER_Z_MIN_MM + 1.6), "Lower: ribs bypass the stacked dual USB")
    bottom_axis.text2D(
        0.03,
        0.04,
        "PASS\n"
        f"dual-USB overlap: {metrics['bottom_ribs_vs_dual_usb_mm3']:.3f} mm³\n"
        f"1.0 mm USB-envelope overlap: {metrics['bottom_ribs_vs_usb_envelope_mm3']:.3f} mm³\n"
        f"full motherboard overlap: {metrics['bottom_ribs_vs_motherboard_mm3']:.3f} mm³\n"
        f"minimum dual-USB distance: {metrics['bottom_ribs_to_dual_usb_mm']:.2f} mm",
        transform=bottom_axis.transAxes,
        fontsize=10,
        color="#245f30",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#e8f5ea", edgecolor="#4e8d58"),
    )

    figure.legend(
        handles=[
            Patch(facecolor=RIB_COLOR, label="review rib"),
            Patch(facecolor=KEEP_OUT_COLOR, label="mandatory keepout"),
            Patch(facecolor=SECONDARY_KEEP_OUT_COLOR, label="other lowest connector"),
            Patch(facecolor=TOP_PLATE_COLOR, alpha=0.3, label="1.2 mm base plate"),
        ],
        loc="lower center",
        ncol=4,
        bbox_to_anchor=(0.5, 0.01),
    )
    figure.text(
        0.5,
        0.065,
        "Only the top/bottom contact layer is shown for keepouts. The same checked ribs are fused into the regenerated V2 export.",
        ha="center",
        fontsize=10,
        color="#3e4952",
    )
    figure.tight_layout(rect=(0.02, 0.09, 0.98, 0.94))
    figure.savefig(COLLISION_PNG, bbox_inches="tight")
    plt.close(figure)


def write_review(metrics: dict[str, float], checks: dict[str, bool]) -> None:
    validation = {
        "scope": "approved internal reinforcement; included in regenerated V2 STEP/STL",
        "status": REINFORCEMENT_REVIEW_STATUS,
        "parameters_mm": {
            "base_top_plate": 1.2,
            "base_bottom_plate": 1.2,
            "rib_width": REINFORCEMENT_RIB_WIDTH_MM,
            "rib_height": REINFORCEMENT_RIB_HEIGHT_MM,
            "review_clearance": REINFORCEMENT_COMPONENT_CLEARANCE_MM,
        },
        "top_segments": [segment.__dict__ for segment in TOP_REINFORCEMENT_SEGMENTS],
        "bottom_segments": [segment.__dict__ for segment in BOTTOM_REINFORCEMENT_SEGMENTS],
        "metrics": metrics,
        "checks": checks,
        "all_checks_pass": all(checks.values()),
    }
    VALIDATION_JSON.write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    review = f"""# N305 外壳内侧加强筋审阅

状态：**路径和高度已经审阅，并已进入重新生成的 V2 STEP/STL。**

## 输出

- [顶板/底板内侧平面图](../previews/enclosure/reinforcement-inner-plan.png)
- [三维碰撞检查图](../previews/enclosure/reinforcement-collision-check.png)
- [机器验证结果](enclosure-reinforcement-validation.json)

## 当前设计

- 顶板、底板基础厚度继续保持 `1.2 mm`。
- 筋宽 `{REINFORCEMENT_RIB_WIDTH_MM:.1f} mm`，筋高 `{REINFORCEMENT_RIB_HEIGHT_MM:.1f} mm`；已选择 `0.8 mm` 而不是初稿 `0.5 mm`，以提高 PA12 MJF/SLS 成型稳定性。
- 顶筋绕过照片重建的完整风扇蜗壳和 `84 × 22 mm` 鳍片投影。
- 底筋绕过 04 面堆叠双 USB；下层 USB 最低约 `Z=-10.29 mm`，与底板内表面 `Z=-10.30 mm` 基本齐平，不能依赖高度错开。
- 同时检查当前完整主板实体及其他接近底板的接口代理，不能为了满足单一 USB 避让而制造新的干涉。
- `1.0 mm` 是本审阅使用的保守 XY 包络，不是已写入外壳的制造间隙。

## 碰撞结果

| 检查 | 结果 |
| --- | ---: |
| 顶筋 vs 风扇/鳍片实体 | `{metrics['top_ribs_vs_cooling_mm3']:.3f} mm³` |
| 顶筋 vs 1.0 mm 散热审阅包络 | `{metrics['top_ribs_vs_cooling_envelope_mm3']:.3f} mm³` |
| 顶筋 vs 完整主板参考 | `{metrics['top_ribs_vs_motherboard_mm3']:.3f} mm³` |
| 底筋 vs 堆叠双 USB | `{metrics['bottom_ribs_vs_dual_usb_mm3']:.3f} mm³` |
| 底筋 vs 1.0 mm 双 USB 审阅包络 | `{metrics['bottom_ribs_vs_usb_envelope_mm3']:.3f} mm³` |
| 底筋 vs 完整主板参考 | `{metrics['bottom_ribs_vs_motherboard_mm3']:.3f} mm³` |
| 顶筋至散热实体最短距离 | `{metrics['top_ribs_to_cooling_mm']:.2f} mm` |
| 底筋至双 USB 实体最短距离 | `{metrics['bottom_ribs_to_dual_usb_mm']:.2f} mm` |

当前全部布置检查通过：`{all(checks.values())}`。

## 已确认的制造取舍

筋高最终采用 `0.8 mm`。基础顶板/底板仍是 `1.2 mm`；只有筋路位置的局部总厚度为 `2.0 mm`。路径或高度以后若再次变化，仍必须重新执行实体碰撞检查和 STEP/STL 回读验证。

本设计没有增加外部包络、没有改变风扇进气孔，也没有改变顶板/底板的基础厚度。
"""
    REVIEW_MD.write_text(review, encoding="utf-8")


def main() -> None:
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    geometry = make_reinforcement_review_geometry()

    metrics = {
        "top_ribs_vs_cooling_mm3": round(intersection_volume(geometry["top_ribs"], geometry["cooling_keepout"]), 6),
        "top_ribs_vs_cooling_envelope_mm3": round(intersection_volume(geometry["top_ribs"], geometry["top_clearance_envelope"]), 6),
        "top_ribs_vs_motherboard_mm3": round(intersection_volume(geometry["top_ribs"], geometry["motherboard"]), 6),
        "bottom_ribs_vs_dual_usb_mm3": round(intersection_volume(geometry["bottom_ribs"], geometry["dual_usb"]), 6),
        "bottom_ribs_vs_usb_envelope_mm3": round(intersection_volume(geometry["bottom_ribs"], geometry["bottom_usb_clearance_envelope"]), 6),
        "bottom_ribs_vs_motherboard_mm3": round(intersection_volume(geometry["bottom_ribs"], geometry["motherboard"]), 6),
        "bottom_ribs_vs_underside_keepouts_mm3": round(intersection_volume(geometry["bottom_ribs"], geometry["underside_keepouts"]), 6),
        "top_ribs_to_cooling_mm": round(minimum_distance(geometry["top_ribs"], geometry["cooling_keepout"]), 3),
        "bottom_ribs_to_dual_usb_mm": round(minimum_distance(geometry["bottom_ribs"], geometry["dual_usb"]), 3),
    }
    checks = {
        "reinforcement_status_is_approved": REINFORCEMENT_REVIEW_STATUS.startswith("approved"),
        "top_ribs_clear_cooling_solids": metrics["top_ribs_vs_cooling_mm3"] <= 1e-5,
        "top_ribs_clear_1mm_cooling_review_envelope": metrics["top_ribs_vs_cooling_envelope_mm3"] <= 1e-5,
        "top_ribs_clear_complete_motherboard": metrics["top_ribs_vs_motherboard_mm3"] <= 1e-5,
        "bottom_ribs_clear_dual_usb": metrics["bottom_ribs_vs_dual_usb_mm3"] <= 1e-5,
        "bottom_ribs_clear_1mm_dual_usb_review_envelope": metrics["bottom_ribs_vs_usb_envelope_mm3"] <= 1e-5,
        "bottom_ribs_clear_complete_motherboard": metrics["bottom_ribs_vs_motherboard_mm3"] <= 1e-5,
        "bottom_ribs_clear_underside_keepouts": metrics["bottom_ribs_vs_underside_keepouts_mm3"] <= 1e-5,
        "mount_hole_count_is_four": len(MOUNT_HOLES) == 4,
    }
    render_plan(geometry, metrics)
    render_collision(geometry, metrics)
    write_review(metrics, checks)

    if not all(checks.values()):
        raise SystemExit(f"reinforcement review validation failed: {checks}")
    print(f"wrote {PLAN_PNG.relative_to(ROOT)}")
    print(f"wrote {COLLISION_PNG.relative_to(ROOT)}")
    print(f"wrote {REVIEW_MD.relative_to(ROOT)}")
    print(f"wrote {VALIDATION_JSON.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
