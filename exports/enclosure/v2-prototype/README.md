# N305 V2 试装版外壳

发布日期：2026-08-21
版本：`v2-prototype-2026-08-21-ribbed`
状态：**用于尺寸、接口和装配试装，不是最终量产版。**

材料选择、国内平台下单、切片方向、螺钉和收货验收见 [V2 外壳打印、下单与试装指南](../../../docs/v2-printing-guide.md)。

> 若已经把同名 STL 上传到打印平台，必须删除旧文件并重新上传本次生成文件。当前含筋版预览体积应约为：上壳 `24.13 cm³`、下壳 `23.02 cm³`；文件同名不表示平台中的旧上传已经更新。

## 文件

- `n305_v2_upper_shell.step/.stl`：上壳，顶面 + 06 + 05。
- `n305_v2_lower_shell.step/.stl`：下壳，底面 + 04 + 07。
- `n305_v2_enclosure_assembly.step/.stl`：上下壳闭合位置，仅用于总体检查；打印时使用两个独立 STL。
- `manifest.json`：完整参数、文件哈希和数据来源。
- `validation.json`：源实体、导入 STEP、STL 网格和装配检查。

所有 CAD 均为毫米，保留项目装配坐标：`+X=06, -X=04, +Y=07, -Y=05, +Z=风扇面`。原机圆形按钮作为复用件，不生成未经测量的按钮 STL。

## 当前试装结构

- 外包络：`106.6 × 109.5 × 28 mm`。
- 上下板厚均为 `1.2 mm`；没有额外风扇顶部避让。
- 顶板/底板内侧已融合 `1.5 × 0.8 mm` 稀疏加强筋；局部总厚度为 `2 mm`，外包络不变。顶筋绕过完整风扇/鳍片包络，底筋绕过 04 堆叠双 USB 和当前完整主板参考。
- 04/06 是连续实体墙；原壳实测内跨距约 `103.0 mm`，结合接口突出量暂分配为 04 侧 `2.0 mm`、06 侧 `1.0 mm`。
- 05/07 各保留 `0.20 mm` 紧凑试装余量；原壳约 `110.5 mm` 的内跨距包含额外留空，不复制到本版。
- 四周侧壁采用原壳实测 `1.8 mm`；这些侧面仍不承担主板主要定位，主板由原四孔/螺柱定位。
- 使用主板原有四孔夹紧上下壳；没有增加外壳专用螺钉轴。
- 04 面保留连续鳍片出风包络；05/07 不开侧向接口孔。
- STL 网格：线性公差 `0.04 mm`，角公差 `0.12 rad`。

## 全部 provisional / 试制参数

| 参数 | 当前值 | 状态 | 来源与限制 |
| --- | ---: | --- | --- |
| `inner_x_at_04_06` | 103.0 mm | user approximate measurement | original case: face 04 inner wall to face 06 inner wall |
| `inner_y_at_05_07` | 105.9 mm | fit-check design | PCB 105.5 + 0.2 mm allowance at faces 05 and 07; original-case 110.5 mm span deliberately not copied |
| `side_wall_thickness` | 1.8 mm | user measured | original case side wall; Not applied to panel aperture sizes. |
| `outer_plan_corner_radius` | 5.8 mm | derived provisional | inner PCB radius + side-wall thickness; Constant-thickness XY offset; replaces the invalid R10 corner. |
| `inner_plan_corner_radius` | 4.0 mm | provisional | photo-reconstructed motherboard corner radius; Must be replaced if a physical corner measurement differs. |
| `pcb_clearance_face_04` | 2.0 mm | derived provisional allocation | 2.0 mm maximum 04 USB projection and 103.0 mm measured inner span; Inner wall coincides nominally with the maximum USB front plane; it is not a PCB locating face. |
| `pcb_clearance_face_06` | 1.0 mm | derived provisional allocation | remaining 1.0 mm of the measured 103.0 mm inner span; Matches the 1.0 mm USB projection; the recessed switch is not the wall datum. |
| `pcb_clearance_face_05` | 0.2 mm | user-requested fit-check allowance | compact non-locating clearance; original-case 110.5 mm span includes unnecessary extra space |
| `pcb_clearance_face_07` | 0.2 mm | user-requested fit-check allowance | compact non-locating clearance; original-case 110.5 mm span includes unnecessary extra space |
| `original_button_through_diameter` | 9.2 mm | user measured | diameter of the original button portion that passes through the panel |
| `face_06_switch_tip_to_inner_wall` | 1.2 mm | photo-derived provisional | photo 03 places the switch behind the USB-defined wall datum; positive means no switch/wall penetration |
| `connector_front_span_04_to_06` | 103.0 mm | derived cross-check | PCB 100.0 + face-04 USB projection 2.0 + face-06 USB projection 1.0; equals the measured inner span |
| `button_inner_wall_to_switch_tip_range` | 0.8 × 1.6 mm | photo-derived estimated range | nominal 1.2 mm with +/-0.4 mm switch-plan uncertainty; excludes unquantified USB rough-measurement error |
| `button_outer_wall_to_switch_tip_range` | 2.6 × 3.4 mm | derived estimated range | 1.8 mm measured wall plus the inner-wall-to-switch range; original button must bridge this axial stack |
| `face_04_max_connector_projection` | 2.0 mm | user rough measurement | stacked dual USB maximum; not shared by every 04 connector |
| `face_04_other_connector_projection_proxy` | 1.0 mm | provisional | unmeasured 04 connector noses; Visual proxy only; DC, HDMI, headphone and RJ45 front projections are not individually measured. |
| `face_06_usb_projection` | 1.0 mm | user rough measurement | two USB front faces; independent from face 04 |
| `nominal_seam_gap` | 0.0 mm | design intent | flush review geometry |
| `manufacturing_seam_clearance` | 0.0 mm | not applied | no manufacturing gap is embedded in the review geometry; any future process compensation must be a separate parameter |
| `fin_exhaust` | 84.0 × 7.4 mm | functional envelope | current fin-stack projection; grille segmentation pending |
| `internal_reinforcement_rib_height` | 0.8 mm | fit-check design | selected after PA12 manufacturability and collision review; Added locally to the 1.2 mm inner plate faces; does not change the base plate thickness. |
| `internal_reinforcement_rib_width` | 1.5 mm | fit-check design | reviewed sparse rib paths; Upper paths bypass the blower/fins; lower paths bypass the stacked dual USB and complete motherboard reference. |
| `clamp_post_od` | 6.4 mm | provisional | review proposal |
| `upper_thread_pilot_diameter` | 2.5 mm | provisional | review proposal; Thread, heat-set insert or self-tapping strategy is not selected. |
| `lower_screw_clearance_diameter` | 3.4 mm | provisional | review proposal; No screw-head counterbore or countersink is included. |
| `printed_hole_locator_nose` | no  | review recommendation | removed: 3.0 OD around 2.5 pilot leaves only 0.25 mm radial wall |
| `fastener_family` | M3-class  | provisional | inferred from 3.2 mm PCB hole; Head, insert and thread form pending. |

## 尚未解决、必须通过实物试装确认

- 04/06 allocation is provisionally 2.0/1.0 mm from USB projections
- exact photo-derived contour of the local PCB step beside the face-06 switch; the current full PCB envelope is conservative for wall clearance
- physical confirmation of the provisional PCB R4 corner reference
- additional print/process compensation, if later required, must remain separate from the reviewed structural clearance
- M3-class screw head, insert and thread form
- reused external button cap geometry and effective travel
- headphone aperture physical diameter confirmation
- exact HDMI connector-front profile; generic motherboard proxy is excluded from aperture coverage
- 04 fin-exhaust grille segmentation inside the no-obstruction envelope

补充说明：两个 HDMI 沿用已审阅的原壳六边形贯通孔。由于真实 HDMI 金属鼻端轮廓尚未测量，它们不参与“通用鼻端代理”的覆盖判定，但也没有因此改变孔形。

## 自动验证摘要

- 上壳、下壳各为一个有效实体：`True`。
- 上下壳体积重叠为零：`True`。
- 两壳与 PCB 实体体积重叠为零：`True`。
- 04/06 开孔后仍为连续墙体：`True`。
- 内侧加强筋已完整融合且无主板碰撞：`True`。
- STEP 回读实体数与体积一致：`True`。
- STL 文件可解析且包含三角形：`True`。
- 名义开孔覆盖失败：`[]`。
- 未计算覆盖：`['04:hdmi_1', '04:hdmi_3']`。

## 试装建议

1. 本目录未提供独立测试片；下单时打印上、下壳两个独立 STL，不打印装配 STL。
2. 上壳建议外顶面朝打印平台；下壳建议外底面朝打印平台。支撑策略取决于材料和切片软件。
3. 不要先强行攻丝。先测量实际 M3 紧固件、打印孔收缩和原按钮行程，再决定扩孔、热熔螺母或自攻方案。
4. 试装反馈应分别记录 04/06 间隙、05/07 插入阻力、四孔同轴性、按钮回弹和每个插头的插拔空间。
