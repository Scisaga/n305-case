#!/usr/bin/env python3
"""Export the authorized N305 V2 fit-check enclosure prototype.

The two shell solids come directly from the reviewed enclosure parameter source.
This exporter deliberately labels the result as a prototype and writes every
non-authoritative parameter and unresolved item beside the CAD files.
"""

from __future__ import annotations

import hashlib
import json
import struct
import sys
from dataclasses import asdict
from pathlib import Path

import cadquery as cq
from cadquery import exporters, importers


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from n305_enclosure_structure import (  # noqa: E402
    BOTTOM_PLATE_T_MM,
    FACE_OWNERSHIP,
    INNER_X_MAX_MM,
    INNER_X_MIN_MM,
    INNER_Y_MAX_MM,
    INNER_Y_MIN_MM,
    LOWER_SCREW_CLEARANCE_D_MM,
    MOUNT_HOLES,
    OUTER_PLAN_CORNER_R_MM,
    OUTER_X_MAX_MM,
    OUTER_X_MIN_MM,
    OUTER_X_MM,
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
    REINFORCEMENT_COMPONENT_CLEARANCE_MM,
    REINFORCEMENT_RIB_HEIGHT_MM,
    REINFORCEMENT_RIB_WIDTH_MM,
    REVIEW_PARAMETERS,
    SIDE_WALL_T_MM,
    TOP_PLATE_T_MM,
    UPPER_THREAD_PILOT_D_MM,
    build_coverage_report,
    build_review_geometry,
    make_reinforcement_review_geometry,
    structure_definition,
)


RELEASE_ID = "v2-prototype-2026-08-21-ribbed"
EXPORT_DIR = ROOT / "exports" / "enclosure" / "v2-prototype"
PREVIEW_DIR = ROOT / "previews" / "enclosure"
STRUCTURE_JSON = ROOT / "docs" / "enclosure-structure.json"
MANIFEST_PATH = EXPORT_DIR / "manifest.json"
VALIDATION_PATH = EXPORT_DIR / "validation.json"
README_PATH = EXPORT_DIR / "README.md"
PREVIEW_PATH = PREVIEW_DIR / "v2-prototype-parts.png"

STL_LINEAR_TOLERANCE_MM = 0.04
STL_ANGULAR_TOLERANCE_RAD = 0.12

CAD_OUTPUTS = {
    "upper_shell": "n305_v2_upper_shell",
    "lower_shell": "n305_v2_lower_shell",
    "enclosure_assembly": "n305_v2_enclosure_assembly",
}


def shape_stats(shape: cq.Shape) -> dict[str, object]:
    bounds = shape.BoundingBox()
    return {
        "valid": shape.isValid(),
        "solids": len(shape.Solids()),
        "volume_mm3": round(sum(solid.Volume() for solid in shape.Solids()), 3),
        "bounds_mm": {
            "x": [round(bounds.xmin, 3), round(bounds.xmax, 3)],
            "y": [round(bounds.ymin, 3), round(bounds.ymax, 3)],
            "z": [round(bounds.zmin, 3), round(bounds.zmax, 3)],
        },
        "size_mm": [round(bounds.xlen, 3), round(bounds.ylen, 3), round(bounds.zlen, 3)],
    }


def intersection_volume(left: cq.Shape, right: cq.Shape) -> float:
    return sum(
        left_solid.intersect(right_solid).Volume()
        for left_solid in left.Solids()
        for right_solid in right.Solids()
    )


def export_part(shape: cq.Shape, basename: str) -> tuple[Path, Path]:
    step_path = EXPORT_DIR / f"{basename}.step"
    stl_path = EXPORT_DIR / f"{basename}.stl"
    exporters.export(shape, str(step_path))
    exporters.export(
        shape,
        str(stl_path),
        tolerance=STL_LINEAR_TOLERANCE_MM,
        angularTolerance=STL_ANGULAR_TOLERANCE_RAD,
    )
    return step_path, stl_path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stl_stats(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    binary = False
    triangles = 0
    if len(data) >= 84:
        declared = struct.unpack("<I", data[80:84])[0]
        binary = len(data) == 84 + 50 * declared
        if binary:
            triangles = declared
    if not binary:
        triangles = data.lower().count(b"facet normal")
    return {
        "format": "binary" if binary else "ascii",
        "triangles": triangles,
        "bytes": len(data),
    }


def import_step_stats(path: Path) -> dict[str, object]:
    imported = importers.importStep(str(path)).val()
    return shape_stats(imported)


def add_shape(axis, shape: cq.Shape, color: str, alpha: float) -> None:
    import numpy as np
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    vertices, triangles = shape.tessellate(0.18)
    coordinates = np.asarray([(point.x, point.y, point.z) for point in vertices])
    mesh = Poly3DCollection(
        coordinates[np.asarray(triangles, dtype=int)],
        facecolor=color,
        edgecolor="none",
        linewidth=0.0,
        alpha=alpha,
    )
    axis.add_collection3d(mesh)


def add_edges(axis, shape: cq.Shape, color: str) -> None:
    for edge in shape.Edges():
        try:
            points, _ = edge.sample(0.22)
        except (ValueError, ZeroDivisionError):
            points, _ = edge.sample(16)
        if len(points) < 2:
            continue
        axis.plot3D(
            [point.x for point in points],
            [point.y for point in points],
            [point.z for point in points],
            color=color,
            linewidth=0.85,
            alpha=0.92,
        )


def format_axis(axis, z_limits: tuple[float, float]) -> None:
    axis.set_xlim(OUTER_X_MIN_MM - 5.0, OUTER_X_MAX_MM + 5.0)
    axis.set_ylim(OUTER_Y_MIN_MM - 5.0, OUTER_Y_MAX_MM + 5.0)
    axis.set_zlim(*z_limits)
    axis.set_box_aspect((OUTER_X_MM, OUTER_Y_MM, z_limits[1] - z_limits[0]))
    axis.set_xlabel("X: +06 / -04")
    axis.set_ylabel("Y: +07 / -05")
    axis.set_zlabel("Z: fan / bottom")
    axis.set_proj_type("ortho")
    axis.view_init(elev=27, azim=-52)


def render_preview(upper: cq.Shape, lower: cq.Shape) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    figure = plt.figure(figsize=(16, 8), dpi=160, facecolor="#f4f7fa")
    assembled = figure.add_subplot(121, projection="3d")
    exploded = figure.add_subplot(122, projection="3d")

    add_shape(assembled, upper, "#4f8edc", 0.70)
    add_shape(assembled, lower, "#e59b48", 0.76)
    add_edges(assembled, upper, "#173f6b")
    add_edges(assembled, lower, "#754411")
    format_axis(assembled, (OUTER_Z_MIN_MM - 3.0, OUTER_Z_MAX_MM + 3.0))
    assembled.set_title("V2 prototype — assembled", fontweight="bold")

    upper_exploded = upper.translate((0.0, 0.0, 18.0))
    lower_exploded = lower.translate((0.0, 0.0, -18.0))
    add_shape(exploded, upper_exploded, "#4f8edc", 0.78)
    add_shape(exploded, lower_exploded, "#e59b48", 0.82)
    add_edges(exploded, upper_exploded, "#173f6b")
    add_edges(exploded, lower_exploded, "#754411")
    format_axis(exploded, (OUTER_Z_MIN_MM - 22.0, OUTER_Z_MAX_MM + 22.0))
    exploded.set_title("Two printed parts; original button reused", fontweight="bold")

    figure.legend(
        handles=[
            Patch(facecolor="#4f8edc", edgecolor="#173f6b", label="upper: top + 06 + 05"),
            Patch(facecolor="#e59b48", edgecolor="#754411", label="lower: bottom + 04 + 07"),
        ],
        loc="lower center",
        ncol=2,
        bbox_to_anchor=(0.5, 0.02),
    )
    figure.suptitle(
        "N305 V2 fit-check enclosure — provisional manufacturing output",
        fontsize=18,
        fontweight="bold",
    )
    figure.text(
        0.5,
        0.075,
        f"Envelope {OUTER_X_MM:g} × {OUTER_Y_MM:g} × {OUTER_Z_MM:g} mm; "
        f"top/bottom {TOP_PLATE_T_MM:g} mm; side wall {SIDE_WALL_T_MM:g} mm; "
        f"internal ribs {REINFORCEMENT_RIB_WIDTH_MM:g} W × {REINFORCEMENT_RIB_HEIGHT_MM:g} H mm.",
        ha="center",
        color="#4d5965",
        fontsize=10,
    )
    figure.tight_layout(rect=(0.0, 0.10, 1.0, 0.93))
    figure.savefig(PREVIEW_PATH, bbox_inches="tight")
    plt.close(figure)


def is_provisional_status(status: str) -> bool:
    return status not in {
        "confirmed",
        "measured",
        "measured/generated",
        "derived",
        "confirmed/derived",
    }


def markdown_value(value: object) -> str:
    if isinstance(value, (tuple, list)):
        return " × ".join(str(item) for item in value)
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value)


def build_readme(
    provisional_parameters: list[dict[str, object]],
    unresolved: list[str],
    validation: dict[str, object],
) -> str:
    rows = []
    for item in provisional_parameters:
        note = str(item.get("note") or "")
        source = str(item.get("source") or "")
        explanation = source if not note else f"{source}; {note}"
        rows.append(
            f"| `{item['name']}` | {markdown_value(item['value'])} {item['unit']} | "
            f"{item['status']} | {explanation} |"
        )
    unresolved_rows = "\n".join(f"- {item}" for item in unresolved)
    checks = validation["checks"]
    upper_volume_cm3 = validation["source_shape_stats"]["upper_shell"]["volume_mm3"] / 1000.0
    lower_volume_cm3 = validation["source_shape_stats"]["lower_shell"]["volume_mm3"] / 1000.0
    return f"""# N305 V2 试装版外壳

发布日期：2026-08-21
版本：`{RELEASE_ID}`
状态：**用于尺寸、接口和装配试装，不是最终量产版。**

材料选择、国内平台下单、切片方向、螺钉和收货验收见 [V2 外壳打印、下单与试装指南](../../../docs/v2-printing-guide.md)。

> 若已经把同名 STL 上传到打印平台，必须删除旧文件并重新上传本次生成文件。当前含筋版预览体积应约为：上壳 `{upper_volume_cm3:.2f} cm³`、下壳 `{lower_volume_cm3:.2f} cm³`；文件同名不表示平台中的旧上传已经更新。

## 文件

- `n305_v2_upper_shell.step/.stl`：上壳，顶面 + 06 + 05。
- `n305_v2_lower_shell.step/.stl`：下壳，底面 + 04 + 07。
- `n305_v2_enclosure_assembly.step/.stl`：上下壳闭合位置，仅用于总体检查；打印时使用两个独立 STL。
- `manifest.json`：完整参数、文件哈希和数据来源。
- `validation.json`：源实体、导入 STEP、STL 网格和装配检查。

所有 CAD 均为毫米，保留项目装配坐标：`+X=06, -X=04, +Y=07, -Y=05, +Z=风扇面`。原机圆形按钮作为复用件，不生成未经测量的按钮 STL。

## 当前试装结构

- 外包络：`{OUTER_X_MM:g} × {OUTER_Y_MM:g} × {OUTER_Z_MM:g} mm`。
- 上下板厚均为 `1.2 mm`；没有额外风扇顶部避让。
- 顶板/底板内侧已融合 `{REINFORCEMENT_RIB_WIDTH_MM:g} × {REINFORCEMENT_RIB_HEIGHT_MM:g} mm` 稀疏加强筋；局部总厚度为 `{TOP_PLATE_T_MM + REINFORCEMENT_RIB_HEIGHT_MM:g} mm`，外包络不变。顶筋绕过完整风扇/鳍片包络，底筋绕过 04 堆叠双 USB 和当前完整主板参考。
- 04/06 是连续实体墙；原壳实测内跨距约 `103.0 mm`，结合接口突出量暂分配为 04 侧 `2.0 mm`、06 侧 `1.0 mm`。
- 05/07 各保留 `0.20 mm` 紧凑试装余量；原壳约 `110.5 mm` 的内跨距包含额外留空，不复制到本版。
- 四周侧壁采用原壳实测 `1.8 mm`；这些侧面仍不承担主板主要定位，主板由原四孔/螺柱定位。
- 使用主板原有四孔夹紧上下壳；没有增加外壳专用螺钉轴。
- 04 面保留连续鳍片出风包络；05/07 不开侧向接口孔。
- STL 网格：线性公差 `{STL_LINEAR_TOLERANCE_MM:g} mm`，角公差 `{STL_ANGULAR_TOLERANCE_RAD:g} rad`。

## 全部 provisional / 试制参数

| 参数 | 当前值 | 状态 | 来源与限制 |
| --- | ---: | --- | --- |
{chr(10).join(rows)}

## 尚未解决、必须通过实物试装确认

{unresolved_rows}

补充说明：两个 HDMI 沿用已审阅的原壳六边形贯通孔。由于真实 HDMI 金属鼻端轮廓尚未测量，它们不参与“通用鼻端代理”的覆盖判定，但也没有因此改变孔形。

## 自动验证摘要

- 上壳、下壳各为一个有效实体：`{checks['upper_and_lower_are_single_valid_solids']}`。
- 上下壳体积重叠为零：`{checks['upper_lower_have_zero_volume_overlap']}`。
- 两壳与 PCB 实体体积重叠为零：`{checks['shells_have_zero_volume_overlap_with_pcb']}`。
- 04/06 开孔后仍为连续墙体：`{checks['04_and_06_remain_single_wall_solids']}`。
- 内侧加强筋已完整融合且无主板碰撞：`{checks['reinforcement_ribs_are_fully_fused_and_collision_free']}`。
- STEP 回读实体数与体积一致：`{checks['step_roundtrip_matches_source_solids_and_volume']}`。
- STL 文件可解析且包含三角形：`{checks['stl_meshes_are_parseable_and_nonempty']}`。
- 名义开孔覆盖失败：`{validation['nominal_aperture_coverage_failures']}`。
- 未计算覆盖：`{validation['aperture_coverage_not_evaluated']}`。

## 试装建议

1. 本目录未提供独立测试片；下单时打印上、下壳两个独立 STL，不打印装配 STL。
2. 上壳建议外顶面朝打印平台；下壳建议外底面朝打印平台。支撑策略取决于材料和切片软件。
3. 不要先强行攻丝。先测量实际 M3 紧固件、打印孔收缩和原按钮行程，再决定扩孔、热熔螺母或自攻方案。
4. 试装反馈应分别记录 04/06 间隙、05/07 插入阻力、四孔同轴性、按钮回弹和每个插头的插拔空间。
"""


def main() -> None:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)

    geometry = build_review_geometry()
    reinforcement_geometry = make_reinforcement_review_geometry()
    upper = geometry["upper_shell_review"]
    lower = geometry["lower_shell_review"]
    assembly = cq.Compound.makeCompound([upper, lower])
    sources = {
        "upper_shell": upper,
        "lower_shell": lower,
        "enclosure_assembly": assembly,
    }

    source_stats = {name: shape_stats(shape) for name, shape in sources.items()}
    coverage = build_coverage_report()
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

    pre_export_checks = {
        "upper_and_lower_are_single_valid_solids": (
            source_stats["upper_shell"]["valid"]
            and source_stats["lower_shell"]["valid"]
            and source_stats["upper_shell"]["solids"] == 1
            and source_stats["lower_shell"]["solids"] == 1
        ),
        "assembly_contains_two_solids": source_stats["enclosure_assembly"]["solids"] == 2,
        "upper_lower_have_zero_volume_overlap": intersection_volume(upper, lower) <= 1e-5,
        "shells_have_zero_volume_overlap_with_pcb": (
            intersection_volume(upper, geometry["motherboard_pcb"]) <= 1e-5
            and intersection_volume(lower, geometry["motherboard_pcb"]) <= 1e-5
        ),
        "04_and_06_remain_single_wall_solids": (
            len(geometry["04"].Solids()) == 1 and len(geometry["06"].Solids()) == 1
        ),
        "two_integral_three_face_parts_preserved": FACE_OWNERSHIP
        == {"top": "upper", "06": "upper", "05": "upper", "bottom": "lower", "04": "lower", "07": "lower"},
        "only_four_original_mount_axes": len(MOUNT_HOLES) == 4,
        "top_and_bottom_are_exactly_1p2mm": TOP_PLATE_T_MM == 1.2 and BOTTOM_PLATE_T_MM == 1.2,
        "nominal_aperture_coverage_has_no_failures": not coverage_failures,
        "original_button_is_reused_not_invented": "button" not in CAD_OUTPUTS,
        "reinforcement_ribs_are_fully_fused_and_collision_free": (
            reinforcement_geometry["top_ribs"].cut(upper).Volume() <= 1e-5
            and reinforcement_geometry["bottom_ribs"].cut(lower).Volume() <= 1e-5
            and intersection_volume(
                reinforcement_geometry["top_ribs"],
                reinforcement_geometry["cooling_keepout"],
            ) <= 1e-5
            and intersection_volume(
                reinforcement_geometry["top_ribs"],
                reinforcement_geometry["motherboard"],
            ) <= 1e-5
            and intersection_volume(
                reinforcement_geometry["bottom_ribs"],
                reinforcement_geometry["dual_usb"],
            ) <= 1e-5
            and intersection_volume(
                reinforcement_geometry["bottom_ribs"],
                reinforcement_geometry["motherboard"],
            ) <= 1e-5
        ),
    }
    if not all(pre_export_checks.values()):
        raise RuntimeError(f"V2 source validation failed: {pre_export_checks}")

    exported_paths: dict[str, tuple[Path, Path]] = {}
    for name, shape in sources.items():
        exported_paths[name] = export_part(shape, CAD_OUTPUTS[name])

    step_stats = {
        name: import_step_stats(paths[0]) for name, paths in exported_paths.items()
    }
    stl_mesh_stats = {
        name: stl_stats(paths[1]) for name, paths in exported_paths.items()
    }
    step_roundtrip_ok = all(
        step_stats[name]["valid"]
        and step_stats[name]["solids"] == source_stats[name]["solids"]
        and abs(step_stats[name]["volume_mm3"] - source_stats[name]["volume_mm3"]) <= 0.01
        for name in sources
    )
    stl_meshes_ok = all(
        stats["bytes"] > 1024 and stats["triangles"] > 0
        for stats in stl_mesh_stats.values()
    )

    checks = {
        **pre_export_checks,
        "step_roundtrip_matches_source_solids_and_volume": step_roundtrip_ok,
        "stl_meshes_are_parseable_and_nonempty": stl_meshes_ok,
        "all_six_cad_outputs_exist": all(
            path.is_file() and path.stat().st_size > 1024
            for paths in exported_paths.values()
            for path in paths
        ),
    }
    if not all(checks.values()):
        raise RuntimeError(f"V2 export validation failed: {checks}")

    render_preview(upper, lower)

    definition = structure_definition(
        output_stage="v2-prototype",
        enclosure_step_stl_generated=True,
    )
    all_parameters = [asdict(parameter) for parameter in REVIEW_PARAMETERS]
    provisional_parameters = [
        item for item in all_parameters if is_provisional_status(str(item["status"]))
    ]
    unresolved = list(definition["explicitly_unresolved"])

    file_records = []
    for name, paths in exported_paths.items():
        for path in paths:
            file_records.append(
                {
                    "role": name,
                    "path": str(path.relative_to(ROOT)),
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path),
                }
            )

    validation = {
        "release_id": RELEASE_ID,
        "designation": "fit-check prototype; not final-production CAD",
        "checks": checks,
        "all_checks_pass": all(checks.values()),
        "source_shape_stats": source_stats,
        "step_roundtrip_stats": step_stats,
        "stl_mesh_stats": stl_mesh_stats,
        "upper_lower_intersection_volume_mm3": round(intersection_volume(upper, lower), 6),
        "upper_pcb_intersection_volume_mm3": round(
            intersection_volume(upper, geometry["motherboard_pcb"]), 6
        ),
        "lower_pcb_intersection_volume_mm3": round(
            intersection_volume(lower, geometry["motherboard_pcb"]), 6
        ),
        "reinforcement": {
            "rib_width_mm": REINFORCEMENT_RIB_WIDTH_MM,
            "rib_height_mm": REINFORCEMENT_RIB_HEIGHT_MM,
            "review_clearance_mm": REINFORCEMENT_COMPONENT_CLEARANCE_MM,
            "top_ribs_vs_cooling_mm3": round(intersection_volume(
                reinforcement_geometry["top_ribs"],
                reinforcement_geometry["cooling_keepout"],
            ), 6),
            "top_ribs_vs_complete_motherboard_mm3": round(intersection_volume(
                reinforcement_geometry["top_ribs"],
                reinforcement_geometry["motherboard"],
            ), 6),
            "bottom_ribs_vs_dual_usb_mm3": round(intersection_volume(
                reinforcement_geometry["bottom_ribs"],
                reinforcement_geometry["dual_usb"],
            ), 6),
            "bottom_ribs_vs_complete_motherboard_mm3": round(intersection_volume(
                reinforcement_geometry["bottom_ribs"],
                reinforcement_geometry["motherboard"],
            ), 6),
        },
        "nominal_aperture_coverage_failures": coverage_failures,
        "aperture_coverage_not_evaluated": coverage_not_evaluated,
    }
    manifest = {
        "release_id": RELEASE_ID,
        "designation": "V2 fit-check prototype",
        "units": "mm",
        "coordinate_frame": "+X=06, -X=04, +Y=07, -Y=05, +Z=fan side; PCB bottom Z=0",
        "printed_parts": ["upper_shell", "lower_shell"],
        "reused_nonprinted_part": "original round power button",
        "outer_envelope_mm": {
            "size": [OUTER_X_MM, OUTER_Y_MM, OUTER_Z_MM],
            "x_bounds": [OUTER_X_MIN_MM, OUTER_X_MAX_MM],
            "y_bounds": [OUTER_Y_MIN_MM, OUTER_Y_MAX_MM],
            "z_bounds": [OUTER_Z_MIN_MM, OUTER_Z_MAX_MM],
            "outer_corner_radius": OUTER_PLAN_CORNER_R_MM,
        },
        "inner_plan_mm": {
            "size": [INNER_X_MAX_MM - INNER_X_MIN_MM, INNER_Y_MAX_MM - INNER_Y_MIN_MM],
            "pcb_clearance_by_face": {
                "04": PCB_CLEARANCE_04_MM,
                "06": PCB_CLEARANCE_06_MM,
                "05": PCB_CLEARANCE_05_MM,
                "07": PCB_CLEARANCE_07_MM,
            },
        },
        "clamp_interface_mm": {
            "upper_pilot_diameter": UPPER_THREAD_PILOT_D_MM,
            "lower_clearance_diameter": LOWER_SCREW_CLEARANCE_D_MM,
        },
        "internal_reinforcement_mm": {
            "base_top_plate": TOP_PLATE_T_MM,
            "base_bottom_plate": BOTTOM_PLATE_T_MM,
            "rib_width": REINFORCEMENT_RIB_WIDTH_MM,
            "rib_height": REINFORCEMENT_RIB_HEIGHT_MM,
            "local_total_thickness": TOP_PLATE_T_MM + REINFORCEMENT_RIB_HEIGHT_MM,
            "top_rule": "bypass complete blower and fin-stack envelopes",
            "bottom_rule": "bypass stacked dual USB and clear complete motherboard reference",
        },
        "stl_meshing": {
            "linear_tolerance_mm": STL_LINEAR_TOLERANCE_MM,
            "angular_tolerance_rad": STL_ANGULAR_TOLERANCE_RAD,
        },
        "all_parameters": all_parameters,
        "provisional_parameters": provisional_parameters,
        "explicitly_unresolved": unresolved,
        "files": file_records,
        "validation": "exports/enclosure/v2-prototype/validation.json",
        "preview": "previews/enclosure/v2-prototype-parts.png",
    }

    STRUCTURE_JSON.write_text(
        json.dumps(definition, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    VALIDATION_PATH.write_text(
        json.dumps(validation, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    README_PATH.write_text(
        build_readme(provisional_parameters, unresolved, validation),
        encoding="utf-8",
    )

    print(f"Exported V2 prototype enclosure to {EXPORT_DIR}")
    print(f"Wrote {PREVIEW_PATH}")
    print(json.dumps(checks, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
