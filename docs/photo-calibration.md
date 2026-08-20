# 04/06 原壳面板照片描摩记录

更新日期：2026-08-20

本文档记录 [机箱盒子04.jpg](../pics/机箱盒子04.jpg) 和 [机箱盒子06.jpg](../pics/机箱盒子06.jpg) 中可见的面板开孔。机器可读数据见 [photo-calibration.json](./photo-calibration.json)，复现脚本是 [calibrate_photos.py](../scripts/calibrate_photos.py)。

## 方法边界

- 粉红线直接描摩原壳照片中的开孔轮廓。
- 黄色框是手工复核的像素包围框。
- 青色网格只在单个开孔附近表示 1 mm 尺寸，比例由该孔已确认的宽/高反求。
- 不同孔的局部网格不是同一个坐标系，不能用来换算孔间距或 PCB 坐标。
- 照片网格叠图保留照片透视，**只作轮廓证据**，不是后续 CAD 的孔位输入。
- `04/06-interface-reference.png` 已与照片叠图分离：它们使用 PCB 基准、正投影和统一毫米比例。

照片像素数据保存在 [n305_photo_reference.py](../src/n305_photo_reference.py)；机械开孔数据独立保存在 [n305_panel_reference.py](../src/n305_panel_reference.py)。

## 04 孔边像素记录

| 开孔 | 主包围框 `(x0,y0,x1,y1)` / px | 尺寸 / mm | 说明 |
| --- | --- | ---: | --- |
| DC | `(602,1890,801,2089)` | Ø5.9 | 用户确认 |
| HDMI 1 | `(953,1908,1465,2095)` | 16.5 × 5.8 | 用户确认；六边轮廓直接描摩 |
| 耳机孔 | `(1132,1625,1301,1797)` | 约 Ø5.4 | 借用相邻 HDMI 1 局部像素比例，待实物确认 |
| RJ45 主窗 | `(1586,1785,2047,2093)` | 15.0 × 10.0 | 用户确认 |
| RJ45 底部 relief | 由主窗中心向下构造 | 4.5 × 1.0 | **在主窗下方额外增加** |
| 叠层双 USB | `(2179,1698,2614,2150)` | 14.0 × 14.5 | 用户确认 |
| HDMI 3 | `(2778,1925,3308,2113)` | 16.5 × 5.8 | 用户确认；六边轮廓直接描摩 |

## RJ45 修正

旧图把 1 mm relief 包含在 10 mm 总高内，等价于把主窗压缩成 9 mm，这是错的。

当前语义是：

```text
15.0 x 10.0 mm RJ45 主窗
          +
主窗下方 4.5 x 1.0 mm relief

总包围高度 = 11.0 mm
```

原始放大图：[RJ45 raw crop](../previews/calibration/original-case-04-rj45-raw.png)。

## 与正投影开孔参考的关系

[04-interface-reference.png](../previews/reference/04-interface-reference.png) 不再使用照片包围框进行孔位排布或显示缩放。它使用：

- PCB `105.5 × 1.5 mm` 边界作为 Y/Z 基准；
- 已记录的 PCB 对齐 03 平面中心 Y；
- 04 实测侧视标定中心 Z；
- 用户确认的毫米孔尺寸；
- 原壳照片中的 HDMI 六边形、RJ45 relief 等形状证据。

因此照片决定“是什么轮廓”，但不决定“在机械图上有多大或是否倾斜”。

## 06 孔边像素记录

06 照片轮廓数据来自 [机箱盒子06.jpg](../pics/机箱盒子06.jpg) 的 4096 × 3072 原始像素。这些数据只用来确认“两个圆角 USB 孔 + 一个圆形按钮孔”，不把透视斜度传入 CAD 参考。

| 开孔 | 主包围框 `(x0,y0,x1,y1)` / px | 尺寸 / mm | 轮廓处理 |
| --- | --- | ---: | --- |
| 照片左侧 USB | `(1235,1674,1650,1865)` | 12.8 × 5.5 | 照片四边形 + 照片圆角 |
| 照片右侧 USB | `(1851,1689,2262,1876)` | 12.8 × 5.5 | 独立照片四边形 + 照片圆角 |
| 电源开关孔 | `(2722,1657,3032,1962)` | Ø9.4 | 照片中的椭圆投影，物理语义为圆孔 |

照片中两个 USB 包围框顶边相差 15 px，这是透视、镜头和面板姿态共同造成的投影差，不能当作机械高度差。两只相同 USB 焊接在同一 PCB 基准面，正投影参考强制共用 `Z=-3.14 mm`；该值只是原两项照片估计的平均值，保留整体孔组位置，不声称是独立实测。两个孔均为水平 `12.8 × 5.5 mm`、R0.7 圆角矩形。

测量规则：相同器件位于同一安装层时，默认共享相同的机械高度参数。只有卡尺、深度尺、正投影标定或明确的器件料号/封装差异才能打破该约束；单张斜拍照片中的像素高差只能记录为透视观测，不得直接写入 CAD 参数。

审图文件：

- [06 原壳局部 1 mm 网格](../previews/calibration/original-case-06-1mm-grid.png)
- [06 面板正投影 CAD 参考](../previews/reference/06-interface-reference.png)
- [左侧 USB 原始裁图](../previews/calibration/original-case-06-usb_left-raw.png)
- [右侧 USB 原始裁图](../previews/calibration/original-case-06-usb_right-raw.png)
- [电源开关孔原始裁图](../previews/calibration/original-case-06-power_switch-raw.png)

## 复现

```bash
python scripts/calibrate_photos.py
python scripts/render_mainboard_reference.py
```

命令生成 04/06 的 PNG/JSON，不生成 STEP/STL。
