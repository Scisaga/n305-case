#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
N305 小主机超薄半开放机箱 V0.1

设计路线：
- 底部骨架托盘 + 中央保护底板；
- 四角 M2.5 安装柱；
- 独立超薄顶部防撞框；
- 风扇主体与散热鳍片外露；
- 风扇区域仅采用“薄网 + 低矮网框”（方案 A）；
- 底部中央区域无加强柱，给 M.2 SSD 保留连续避让空间；
- 电源按钮采用大孔位、可微调的独立滑动按钮。

注意：
1. PCB、厚度和孔位使用用户实测数据；
2. 风扇中心由正投影照片标定，仅用于装配参考，风扇网框本身是独立粘贴件；
3. 电源开关位置由侧视照片估计，并使用 12 x 5.5 mm 调节孔吸收误差；
4. STEP/STL 可直接加工，但首次昂贵工艺（SLS/CNC）前仍建议先用廉价 FDM 检查装配。
"""

from __future__ import annotations

import math
from pathlib import Path
import cadquery as cq
from cadquery import exporters

OUT_DIR = Path(__file__).resolve().parent / "n305_half_open_case_v01"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# 1. 用户实测参数（单位：mm）
# -----------------------------------------------------------------------------
PCB_X = 100.0          # 照片水平方向
PCB_Y = 105.5          # 照片竖直方向
PCB_T = 1.5
TOTAL_Z = 25.6
PCB_TOP_TO_FAN_TOP = 13.8
PCB_BOTTOM_TO_LOWEST = TOTAL_Z - PCB_T - PCB_TOP_TO_FAN_TOP  # 10.3

HOLE_D = 3.2
HOLE_EDGE_X = 3.8      # 左/右边到孔中心
HOLE_EDGE_Y = 4.1      # 上/下边到孔中心

FAN_INLET_D = 33.5
# 根据带标尺正投影照片拟合出的风扇进风口中心（相对 PCB 左上角）
FAN_CENTER_FROM_LEFT = 49.8
FAN_CENTER_FROM_TOP = 56.2

# -----------------------------------------------------------------------------
# 2. 设计参数
# -----------------------------------------------------------------------------
OUTER_X = 107.0
OUTER_Y = 110.0
OUTER_R = 6.5

# 底部最低平面比最低接口低约 0.3 mm，从而保护接口又不显著增加厚度
LOWEST_CLEARANCE = 0.3
BOARD_BOTTOM_Z = PCB_BOTTOM_TO_LOWEST + LOWEST_CLEARANCE  # 10.6
BOARD_TOP_Z = BOARD_BOTTOM_Z + PCB_T                      # 12.1
FAN_TOP_Z = BOARD_TOP_Z + PCB_TOP_TO_FAN_TOP              # 25.9

BOTTOM_RING_T = 1.4
BOTTOM_RING_INNER_X = 102.0
BOTTOM_RING_INNER_Y = 106.0
BOTTOM_RING_INNER_R = 4.5

CENTRAL_FLOOR_X = 74.0
CENTRAL_FLOOR_Y = 80.0
CENTRAL_FLOOR_R = 5.0
CENTRAL_FLOOR_T = 1.0
RIB_W = 6.0
RIB_T = 1.4

STANDOFF_OD = 7.0
STANDOFF_PILOT_D = 2.2       # M2.5 自攻/成型螺纹底孔
STANDOFF_PILOT_BOTTOM_Z = 2.2
LOCATOR_OD = 0.0             # V0.1 不使用定位凸台，以吸收四孔对称假设带来的少量误差
LOCATOR_H = 0.0

# 顶部防撞框略高于风扇网框，保护风扇和鳍片免受平面直接挤压
TOP_FRAME_TOP_Z = 26.8
TOP_RING_T = 1.0
TOP_RING_BOTTOM_Z = TOP_FRAME_TOP_Z - TOP_RING_T
TOP_RING_INNER_X = 104.0
TOP_RING_INNER_Y = 107.0
TOP_RING_INNER_R = 5.0

TOP_PAD_OD = 9.0
TOP_PAD_T = 2.0
TOP_PAD_BOTTOM_Z = TOP_FRAME_TOP_Z - TOP_PAD_T
TOP_SLEEVE_OD = 5.8
TOP_CLEARANCE_D = 3.4
TOP_COUNTERBORE_D = 5.2
TOP_COUNTERBORE_DEPTH = 1.2

# 电源按钮：照片估计为距 PCB 左边约 32 mm，底边侧向按压
BUTTON_FROM_LEFT = 32.0
BUTTON_SLOT_W = 12.0
BUTTON_SLOT_H = 5.5
BUTTON_SLOT_CENTER_Z = 6.5
BUTTON_WALL_W = 20.0
BUTTON_WALL_T = 1.8
BUTTON_WALL_TOP_Z = 10.3

# 风扇方案 A：金属网片 + 超薄粘贴网框
FAN_GUARD_OUTER_D = 43.5
FAN_GUARD_OPEN_D = 37.5
FAN_GUARD_T = 0.8
FAN_MESH_POCKET_D = 41.5
FAN_MESH_POCKET_DEPTH = 0.25

# -----------------------------------------------------------------------------
# 3. 坐标
# -----------------------------------------------------------------------------
BOARD_X0 = -PCB_X / 2.0
BOARD_Y_TOP = PCB_Y / 2.0

HOLES = [
    (BOARD_X0 + HOLE_EDGE_X,  BOARD_Y_TOP - HOLE_EDGE_Y),
    (-BOARD_X0 - HOLE_EDGE_X, BOARD_Y_TOP - HOLE_EDGE_Y),
    (BOARD_X0 + HOLE_EDGE_X, -BOARD_Y_TOP + HOLE_EDGE_Y),
    (-BOARD_X0 - HOLE_EDGE_X, -BOARD_Y_TOP + HOLE_EDGE_Y),
]

FAN_CENTER = (
    BOARD_X0 + FAN_CENTER_FROM_LEFT,
    BOARD_Y_TOP - FAN_CENTER_FROM_TOP,
)

BUTTON_X = BOARD_X0 + BUTTON_FROM_LEFT
BUTTON_Y = -OUTER_Y / 2.0 + BUTTON_WALL_T / 2.0

# -----------------------------------------------------------------------------
# 4. CAD 辅助函数
# -----------------------------------------------------------------------------
def rounded_plate(width: float, height: float, radius: float, thickness: float, z0: float = 0.0) -> cq.Workplane:
    sketch = cq.Sketch().rect(width, height).vertices().fillet(radius)
    return cq.Workplane("XY").placeSketch(sketch).extrude(thickness).translate((0, 0, z0))


def rounded_ring(
    outer_x: float,
    outer_y: float,
    outer_r: float,
    inner_x: float,
    inner_y: float,
    inner_r: float,
    thickness: float,
    z0: float = 0.0,
) -> cq.Workplane:
    outer = rounded_plate(outer_x, outer_y, outer_r, thickness, z0)
    inner = rounded_plate(inner_x, inner_y, inner_r, thickness + 0.4, z0 - 0.2)
    return outer.cut(inner)


def beam_between(p1: tuple[float, float], p2: tuple[float, float], width: float, thickness: float, z0: float = 0.0) -> cq.Workplane:
    x1, y1 = p1
    x2, y2 = p2
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    angle = math.degrees(math.atan2(dy, dx))
    mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
    beam = cq.Workplane("XY").box(length, width, thickness, centered=(True, True, False))
    beam = beam.rotate((0, 0, 0), (0, 0, 1), angle).translate((mx, my, z0))
    return beam


def export_part(part: cq.Workplane, basename: str) -> None:
    exporters.export(part, str(OUT_DIR / f"{basename}.step"))
    exporters.export(
        part,
        str(OUT_DIR / f"{basename}.stl"),
        tolerance=0.03,
        angularTolerance=0.12,
    )

# -----------------------------------------------------------------------------
# 5. 底壳骨架
# -----------------------------------------------------------------------------
def make_bottom() -> cq.Workplane:
    # 外围低矮防护环：位于所有接口包络之外
    bottom = rounded_ring(
        OUTER_X, OUTER_Y, OUTER_R,
        BOTTOM_RING_INNER_X, BOTTOM_RING_INNER_Y, BOTTOM_RING_INNER_R,
        BOTTOM_RING_T, 0.0,
    )

    # 中央底板：边缘留“环形悬空区”，接口可以向下伸出而不与底板碰撞
    central = rounded_plate(
        CENTRAL_FLOOR_X, CENTRAL_FLOOR_Y, CENTRAL_FLOOR_R,
        CENTRAL_FLOOR_T, 0.0,
    )
    bottom = bottom.union(central)

    # 四角安装柱与中央底板之间用短斜肋连接；中央大区域不设凸起，给 SSD 连续避让
    central_corner_x = CENTRAL_FLOOR_X / 2.0 - 2.5
    central_corner_y = CENTRAL_FLOOR_Y / 2.0 - 2.5
    for hx, hy in HOLES:
        sx = math.copysign(central_corner_x, hx)
        sy = math.copysign(central_corner_y, hy)
        bottom = bottom.union(beam_between((sx, sy), (hx, hy), RIB_W, RIB_T, 0.0))

        # 安装柱向上/下外框做短连接，保证底壳为单一实体；连接位位于安装孔附近，避开接口主体
        outer_y_target = math.copysign(OUTER_Y / 2.0 - 0.7, hy)
        bottom = bottom.union(beam_between((hx, hy), (hx, outer_y_target), 5.5, RIB_T, 0.0))

        post = cq.Workplane("XY").center(hx, hy).circle(STANDOFF_OD / 2.0).extrude(BOARD_BOTTOM_Z)
        # 不做进入 PCB 孔的定位凸台，靠 3.2 mm 孔与螺钉间隙吸收少量孔位误差
        bottom = bottom.union(post)

    # 安装柱盲孔；保留约 2.2 mm 底部材料
    for hx, hy in HOLES:
        pilot = (
            cq.Workplane("XY")
            .center(hx, hy)
            .circle(STANDOFF_PILOT_D / 2.0)
            .extrude(BOARD_BOTTOM_Z - STANDOFF_PILOT_BOTTOM_Z)
            .translate((0, 0, STANDOFF_PILOT_BOTTOM_Z))
        )
        bottom = bottom.cut(pilot)

    # 电源按钮局部支架；其余接口边保持开放
    wall_h = BUTTON_WALL_TOP_Z - BOTTOM_RING_T
    button_wall = (
        cq.Workplane("XY")
        .box(BUTTON_WALL_W, BUTTON_WALL_T, wall_h, centered=(True, True, False))
        .translate((BUTTON_X, BUTTON_Y, BOTTOM_RING_T))
    )
    bottom = bottom.union(button_wall)

    # 大号可调孔：按钮可横向和纵向微调后固定
    slot = (
        cq.Workplane("XY")
        .box(BUTTON_SLOT_W, BUTTON_WALL_T + 1.0, BUTTON_SLOT_H, centered=(True, True, True))
        .translate((BUTTON_X, BUTTON_Y, BUTTON_SLOT_CENTER_Z))
    )
    bottom = bottom.cut(slot)

    return bottom.clean()

# -----------------------------------------------------------------------------
# 6. 顶部超薄防撞框
# -----------------------------------------------------------------------------
def make_top_frame() -> cq.Workplane:
    top = rounded_ring(
        OUTER_X, OUTER_Y, OUTER_R,
        TOP_RING_INNER_X, TOP_RING_INNER_Y, TOP_RING_INNER_R,
        TOP_RING_T, TOP_RING_BOTTOM_Z,
    )

    for hx, hy in HOLES:
        pad = (
            cq.Workplane("XY")
            .center(hx, hy)
            .circle(TOP_PAD_OD / 2.0)
            .extrude(TOP_PAD_T)
            .translate((0, 0, TOP_PAD_BOTTOM_Z))
        )
        sleeve_h = TOP_PAD_BOTTOM_Z - BOARD_TOP_Z + 0.2
        sleeve = (
            cq.Workplane("XY")
            .center(hx, hy)
            .circle(TOP_SLEEVE_OD / 2.0)
            .extrude(sleeve_h)
            .translate((0, 0, BOARD_TOP_Z - 0.2))
        )
        # 安装垫向顶部/底部外框做短桥接，使整个顶框为单一零件
        outer_y_target = math.copysign(OUTER_Y / 2.0 - 0.7, hy)
        bridge = beam_between((hx, hy), (hx, outer_y_target), 5.5, TOP_PAD_T, TOP_PAD_BOTTOM_Z)
        top = top.union(pad).union(sleeve).union(bridge)

    # M2.5 通孔及低头螺钉沉孔
    for hx, hy in HOLES:
        through = (
            cq.Workplane("XY")
            .center(hx, hy)
            .circle(TOP_CLEARANCE_D / 2.0)
            .extrude(TOP_FRAME_TOP_Z - BOARD_TOP_Z + 2.0)
            .translate((0, 0, BOARD_TOP_Z - 1.0))
        )
        counterbore = (
            cq.Workplane("XY")
            .center(hx, hy)
            .circle(TOP_COUNTERBORE_D / 2.0)
            .extrude(TOP_COUNTERBORE_DEPTH + 0.2)
            .translate((0, 0, TOP_FRAME_TOP_Z - TOP_COUNTERBORE_DEPTH))
        )
        top = top.cut(through).cut(counterbore)

    return top.clean()

# -----------------------------------------------------------------------------
# 7. 风扇方案 A：薄网框
# -----------------------------------------------------------------------------
def make_fan_guard() -> cq.Workplane:
    guard = cq.Workplane("XY").circle(FAN_GUARD_OUTER_D / 2.0).extrude(FAN_GUARD_T)
    opening = (
        cq.Workplane("XY")
        .circle(FAN_GUARD_OPEN_D / 2.0)
        .extrude(FAN_GUARD_T + 0.4)
        .translate((0, 0, -0.2))
    )
    guard = guard.cut(opening)

    # 顶部网片浅槽：建议嵌入直径 41.0~41.3 mm、厚 0.2~0.3 mm 的金属网
    pocket = (
        cq.Workplane("XY")
        .circle(FAN_MESH_POCKET_D / 2.0)
        .extrude(FAN_MESH_POCKET_DEPTH + 0.1)
        .translate((0, 0, FAN_GUARD_T - FAN_MESH_POCKET_DEPTH))
    )
    guard = guard.cut(pocket)
    return guard.clean()

# -----------------------------------------------------------------------------
# 8. 可调小电源按钮
# -----------------------------------------------------------------------------
def make_power_button() -> cq.Workplane:
    # 先沿 Z 轴建模，最终旋转为沿 Y 轴运动
    cap = cq.Workplane("XY").circle(2.5).extrude(1.4)
    stem = (
        cq.Workplane("XY")
        .box(2.2, 2.2, 3.2, centered=(True, True, False))
        .translate((0, 0, 1.4))
    )
    flange = (
        cq.Workplane("XY")
        .box(12.5, 7.0, 1.0, centered=(True, True, False))
        .translate((0, 0, 4.6))
    )
    button = cap.union(stem).union(flange)
    # Z -> Y；圆形帽朝机箱外侧
    return button.rotate((0, 0, 0), (1, 0, 0), -90).clean()

# -----------------------------------------------------------------------------
# 9. 参考包络（不参与打印）
# -----------------------------------------------------------------------------
def make_board_reference() -> cq.Workplane:
    pcb = (
        cq.Workplane("XY")
        .box(PCB_X, PCB_Y, PCB_T, centered=(True, True, False))
        .translate((0, 0, BOARD_BOTTOM_Z))
    )
    # 近似风扇主体，供装配审阅；不是精确零件模型
    fan_body = (
        cq.Workplane("XY")
        .box(58.0, 57.0, PCB_TOP_TO_FAN_TOP, centered=(True, True, False))
        .translate((FAN_CENTER[0], FAN_CENTER[1], BOARD_TOP_Z))
    )
    # 散热鳍片近似包络（照片标定约 22 x 84 mm）
    heatsink = (
        cq.Workplane("XY")
        .box(22.0, 84.0, PCB_TOP_TO_FAN_TOP, centered=(True, True, False))
        .translate((-40.0, 0.0, BOARD_TOP_Z))
    )
    # 通用 M.2 2280 SSD 避让参考：中央底部至少 9.6 mm 净高，且无加强柱
    ssd_keepout = (
        cq.Workplane("XY")
        .box(22.5, 82.0, 7.0, centered=(True, True, False))
        .translate((-18.0, 0.0, BOARD_BOTTOM_Z - 7.0))
    )
    return pcb.union(fan_body).union(heatsink).union(ssd_keepout).clean()


def make_mesh_cut_guide() -> cq.Workplane:
    # 仅作为 2D 切割轮廓；推荐金属网实际裁切直径 41.0~41.3 mm
    return cq.Workplane("XY").circle(41.2 / 2.0)

# -----------------------------------------------------------------------------
# 10. 导出
# -----------------------------------------------------------------------------
def main() -> None:
    bottom = make_bottom()
    top = make_top_frame()
    fan_guard = make_fan_guard()
    button = make_power_button()
    board_ref = make_board_reference()

    export_part(bottom, "n305_case_bottom")
    export_part(top, "n305_case_top_bumper_frame")
    export_part(fan_guard, "n305_fan_mesh_frame_A")
    export_part(button, "n305_power_button_adjustable")
    exporters.export(board_ref, str(OUT_DIR / "n305_board_keepout_reference.step"))
    exporters.export(board_ref, str(OUT_DIR / "n305_board_keepout_reference.stl"), tolerance=0.05, angularTolerance=0.15)

    # 金属网裁切模板
    mesh_guide = make_mesh_cut_guide()
    exporters.export(mesh_guide, str(OUT_DIR / "fan_mesh_cut_41p2mm.dxf"))

    # 装配 STEP：包含外壳零件；参考包络单独导出，避免加工时误选
    assy = cq.Assembly(name="N305_half_open_case_v01")
    assy.add(bottom, name="bottom")
    assy.add(top, name="top_bumper")
    assy.add(
        fan_guard,
        name="fan_mesh_frame_A",
        loc=cq.Location(cq.Vector(FAN_CENTER[0], FAN_CENTER[1], FAN_TOP_Z)),
    )
    # 按钮按装配方向置于前侧；最终位置可在大孔内微调
    button_loc = cq.Location(cq.Vector(BUTTON_X, -OUTER_Y / 2.0 - 1.4, BUTTON_SLOT_CENTER_Z))
    assy.add(button, name="power_button", loc=button_loc)
    assy.save(str(OUT_DIR / "n305_half_open_case_v01_assembly.step"))

    # 参数摘要
    summary = f"""# N305 超薄半开放机箱 V0.1 — 参数摘要

## 已生成文件

- `n305_case_bottom.step/.stl`
- `n305_case_top_bumper_frame.step/.stl`
- `n305_fan_mesh_frame_A.step/.stl`
- `n305_power_button_adjustable.step/.stl`
- `n305_half_open_case_v01_assembly.step`
- `n305_board_keepout_reference.step/.stl`（仅参考，不要打印）
- `fan_mesh_cut_41p2mm.dxf`
- `n305_half_open_case_v01.py`

## 外形

- 顶/底框平面包络：{OUTER_Y:.1f} × {OUTER_X:.1f} mm
- 顶部防撞框最高面：{TOP_FRAME_TOP_Z:.1f} mm
- 裸组件实测厚度：{TOTAL_Z:.1f} mm
- 风扇网框安装后最高面：{FAN_TOP_Z + FAN_GUARD_T:.1f} mm

因此完整装配的理论最大包络约为：

**{OUTER_Y:.1f} × {OUTER_X:.1f} × {TOP_FRAME_TOP_Z:.1f} mm**

## SSD 避让

- PCB 底面到中央底板顶面净高：{BOARD_BOTTOM_Z - CENTRAL_FLOOR_T:.1f} mm
- 中央区域不设置安装柱或加强筋；仅四角孔位附近有支撑
- 参考包络按 M.2 2280：22.5 × 82 × 7 mm 建立

## 风扇方案 A

- 实测进风口：Ø{FAN_INLET_D:.1f} mm
- 网框通风孔：Ø{FAN_GUARD_OPEN_D:.1f} mm
- 金属网建议裁切：Ø41.0~41.3 mm
- 网框厚度：{FAN_GUARD_T:.1f} mm
- 金属网建议厚度：0.2~0.3 mm

## 固定件

建议使用：

- 4 × M2.5 × 20 mm 低头螺钉或沉头螺钉
- 4 × M2.5 尼龙薄垫片（位于顶部套筒与 PCB 铜环之间）

底柱为 Ø{STANDOFF_PILOT_D:.1f} mm 盲孔，按 PETG/ABS 的 M2.5 成型螺纹设计。首次锁紧请勿过度用力。

## 打印建议

- 材料：PETG 验证；正式版 ASA / ABS / PA12
- 层高：0.16~0.20 mm
- 喷嘴：0.4 mm
- 壁线：至少 3 道
- 底壳：正常朝向打印
- 顶框：平放打印
- 风扇网框：平放打印；若 FDM 无法稳定打印 0.8 mm，可把 `FAN_GUARD_T` 改成 1.0 mm
- 按钮：侧放或帽面朝下打印

## 当前照片推导项

电源开关中心按距 PCB 左边约 {BUTTON_FROM_LEFT:.1f} mm 建模。机箱使用 {BUTTON_SLOT_W:.1f} × {BUTTON_SLOT_H:.1f} mm 可调孔，允许按钮在孔内对准后用少量硅胶或 UV 胶固定。
"""
    (OUT_DIR / "README.md").write_text(summary, encoding="utf-8")

    print(f"Generated in: {OUT_DIR}")
    for path in sorted(OUT_DIR.iterdir()):
        print(path.name, path.stat().st_size)


if __name__ == "__main__":
    main()
