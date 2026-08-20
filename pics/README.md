# N305 主板照片的视图与空间关系

本文说明本目录照片之间的空间关系，并为照片标定、尺寸提取和 CAD 建模提供统一方向。照片拍摄时存在旋转，**照片画面的上、下、左、右不等于主板的统一物理方位**；判断空间关系时以本页的“风扇面基准视图”为准。

## 1. 已确认的风扇面基准视图

正对风扇、热管和散热模组所在的元件面，并将散热鳍片转到下方。此时四条边的位置已经确认如下：

```text
                         上：06（双 USB 边）
                                CAD +X
                                   ↑
                                   │
 左：07（左边侧视）   CAD +Y  ←── 主板 ──→  CAD -Y   右：05（右边侧视）
                                   │
                                   ↓
                                CAD -X
                 下：04（后置 I/O、散热鳍片/出风边）

 +Z：离开 PCB，朝向观察者、风扇和热管
 -Z：穿过 PCB，朝向底面器件、M.2/内存插槽一侧
```

最重要的方位关系是：

- 左边是 07，上边是 06，右边是 05，下边是 04。
- 散热鳍片位于下方，即 04 所在边；04 同时是主要后置 I/O 边。
- 04 与 06 互为对边，05 与 07 互为对边。

### 与现有 CAD 坐标的关系

旧模型曾沿用原始照片方向，相对上述基准视图旋转了 90°。当前统一使用下列 CAD 坐标，不再保留旧生成器：

- CAD +X 指向基准视图上方的 06，CAD -X 指向下方的 04。
- CAD +Y 指向基准视图左方的 07，CAD -Y 指向右方的 05。
- `PCB_X = 100.0 mm` 对应基准视图的上下方向，即 06—04 方向。
- `PCB_Y = 105.5 mm` 对应基准视图的左右方向，即 07—05 方向。
- CAD +Z 指向风扇面，CAD -Z 指向主板底面。

坐标原点可取 PCB 平面中心；PCB 上、下表面的具体 Z 值由装配基准决定。

## 2. 六个面的对应关系

| 面或边 | 在风扇面基准视图中的位置 | 相机所在方向 | 观察方向 | 对面 | 识别特征 |
| --- | --- | --- | --- | --- | --- |
| 元件/风扇面 | 正面 | +Z | 沿 -Z 俯视 | PCB 底面 | 鼓风机、热管、长条散热鳍片 |
| PCB 底面 | 背面 | -Z | 沿 +Z 仰视 | 元件/风扇面 | M.2/内存插槽、纽扣电池及底面器件 |
| 04 边 | 下 | -X | 沿 +X 观察 | 06 边 | 后置 I/O 集中；散热鳍片和主要出风口位于此边 |
| 06 边 | 上 | +X | 沿 -X 观察 | 04 边 | 两个蓝色 USB-A 接口是最明显标志 |
| 05 边 | 右 | -Y | 沿 +Y 观察 | 07 边 | 主板右边的高度和侧面轮廓 |
| 07 边 | 左 | +Y | 沿 -Y 观察 | 05 边 | 主板左边的高度和侧面轮廓 |

因此有三组严格相反的观察方向：

- 元件/风扇面（+Z）与 PCB 底面（-Z）。
- 下边 04（-X）与上边 06（+X）。
- 右边 05（-Y）与左边 07（+Y）。

从风扇面翻到 PCB 底面后，左右关系会镜像。用底面照片标定孔位或器件位置时，应先通过四条已编号的边重新定向，不能直接沿用风扇面照片的画面左右坐标。

## 3. 照片与观察方向

| 照片 | 观察方向 | 内容与用途 |
| --- | --- | --- |
| [01-n305-mainboard-component-side-overall-width-measurement.jpg](./01-n305-mainboard-component-side-overall-width-measurement.jpg) | +Z → -Z | 风扇面整体尺寸；CAD X / 基准视图上下方向测量 |
| [02-n305-mainboard-component-side-overall-depth-measurement.jpg](./02-n305-mainboard-component-side-overall-depth-measurement.jpg) | +Z → -Z | 风扇面整体尺寸；CAD Y / 基准视图左右方向测量 |
| [03-n305-mainboard-bottom-side-overview.jpg](./03-n305-mainboard-bottom-side-overview.jpg) | -Z → +Z | PCB 底面总览；与风扇面互为正反面 |
| [04-n305-mainboard-bottom-rear-io-heatsink-edge-height-measurement.jpg](./04-n305-mainboard-bottom-rear-io-heatsink-edge-height-measurement.jpg) | -X → +X | 基准视图下边侧视；后置 I/O、鳍片/出风边及 Z 向高度 |
| [05-n305-mainboard-right-edge-height-measurement.jpg](./05-n305-mainboard-right-edge-height-measurement.jpg) | -Y → +Y | 基准视图右边侧视和 Z 向高度；与 07 相对 |
| [06-n305-mainboard-top-dual-usb-edge-height-measurement.jpg](./06-n305-mainboard-top-dual-usb-edge-height-measurement.jpg) | +X → -X | 基准视图上边侧视；双 USB 边及 Z 向高度；与 04 相对 |
| [07-n305-mainboard-left-edge-profile.jpg](./07-n305-mainboard-left-edge-profile.jpg) | +Y → -Y | 基准视图左边侧视和侧面轮廓；与 05 相对 |
| [08-n305-mainboard-component-side-blower-span-measurement.jpg](./08-n305-mainboard-component-side-blower-span-measurement.jpg) | +Z → -Z | 风扇面局部尺寸，记录鼓风机区域跨度 |
| [09-n305-mainboard-component-side-heatsink-span-measurement.jpg](./09-n305-mainboard-component-side-heatsink-span-measurement.jpg) | +Z → -Z | 风扇面局部尺寸，记录散热模组跨度 |
| [10-n305-mainboard-component-side-fin-stack-span-measurement-01.jpg](./10-n305-mainboard-component-side-fin-stack-span-measurement-01.jpg) | +Z → -Z | 鳍片区域跨度测量，第一张读数参考 |
| [11-n305-mainboard-component-side-fin-stack-span-measurement-02.jpg](./11-n305-mainboard-component-side-fin-stack-span-measurement-02.jpg) | +Z → -Z | 同一区域的第二张读数参考，用于交叉检查 |
| [机箱盒子04.jpg](./机箱盒子04.jpg) | 04 原机面板的一侧 | 反查 HDMI、RJ45、叠层窗口和 DC 的实际壳体开孔；其画面水平方向与产品外观图镜像 |
| [机箱盒子06.jpg](./机箱盒子06.jpg) | 06 原机外侧 | 反查两个 USB 开孔和已安装圆形按钮的位置/可见直径 |
| [机箱按钮-1.jpg](./机箱按钮-1.jpg) | 原机按钮正面 | 恢复圆帽与止挡法兰直径比例 |
| [机箱按钮-2.jpg](./机箱按钮-2.jpg) | 原机按钮侧面 | 恢复圆帽凸出和法兰厚度；后端推杆被便签遮挡 |

08～11 都是从 +Z 方向拍摄的局部测量照片，不是新增的独立表面。

## 4. Z 向堆叠关系

从 +Z 到 -Z，主板组件大致按以下顺序排列：

```text
最高处：风扇壳体、散热模组                 +Z
        热管、风扇、鳍片
        PCB 元件面
        PCB，厚约 1.5 mm
        PCB 底面器件、插槽及 SSD 避让区
最低处：底面最大下探器件                   -Z
```

当前项目使用的实测/建模值为：

- PCB 元件面至风扇最高面约 13.8 mm。
- PCB 厚度约 1.5 mm。
- PCB 底面至最低器件为 10.25 mm（04 原图换算值 10.246 mm）。
- 裸组件建模厚度为 25.55 mm，卡尺读数约 25.6 mm。
- 04—06 方向含接口/散热件的最大平面包络为 103.4 mm；相对 100 mm PCB，当前模型两端各只允许约 1.7 mm 外伸。

散热气流的主要空间关系是：鼓风机从 +Z 侧吸气，经鳍片后朝基准视图下方的 04 边排出；在 CAD 中该方向为 -X。因此 V0.2 顶面圆孔直接对准风扇进气口，04 面设置与鳍片对齐的宽排风窗口；出风路径上不设置封闭横梁或小孔阵列。

01 照片中的风扇外壳已按 PCB 四角校正后描摩为非对称蜗壳，原始轮廓证据见 [01-blower-profile-trace.png](../previews/calibration/01-blower-profile-trace.png)，机器转换记录见 [component-calibration.json](../docs/component-calibration.json)。旧版 58 × 57 mm 圆角矩形风扇壳和三根叶轮示意杆作废。

## 5. 建模和照片标定规则

1. 先把风扇面照片旋转到“鳍片朝下”的基准姿态，再判断左 07、上 06、右 05、下 04。
2. 把基准视图方位录入现有 CAD 时使用转换关系：上/下对应 ±X，左/右对应 ±Y。
3. 使用底面照片时先做镜像关系检查，再通过接口组合或鳍片位置确认方向。
4. 两个相对侧视图的画面水平方向天然相反；比较接口位置时必须转换到同一个坐标系。
5. 03 底面照片先按 PCB 四条理论直边做透视校正，负责孔位和所有接口 XY；04、06 只负责 Z、接口正面形状和顺序。侧照片中的板边投影与接口不在同一深度，不能再拿来直接换算 Y。
6. 卡尺存在遮挡和透视误差；01、02 用于整体包络，08～11 用于局部尺寸和交叉验证。
7. 后续新增照片时，文件名应写明此基准下的方位和稳定特征，例如 `top-dual-usb-edge`、`bottom-rear-io-heatsink-edge`。
8. 完整像素坐标、换算式和辅助线叠图见 [../docs/photo-calibration.md](../docs/photo-calibration.md)。

## 6. 电源开关照片标定

03 底面照片透视校正并用 06 侧照片复核后，当前审阅基准为：

- 开关位于 06 边，与两个蓝色 USB-A 位于同一面。
- 开关中心为 `Y≈+29.5 mm`，沿 06 边距 07/06 角约 23.3 mm。
- 等价地，距 05/06 角约 82.3 mm。
- 开关中心约在 PCB 底面以下 4.2 mm。
- 可见开关正面约 4.5 × 4.5 mm，中央触点约 1.6～2.0 mm。

静态照片不能测得真实触发行程。原机 06 面照片和按钮照片支持恢复圆形按钮：可见帽约 Ø10.0 mm、止挡法兰约 Ø12.5 mm；用户实测面板配合孔为 **Ø9.4 mm**。后端推杆、静止间隙和限位仍须在后续按钮实体重建时核验。

该标定取代早期“开关位于 05 边、距照片左边约 32 mm”的错误假设。

两只 USB-A 中心分别为 `Y≈+4.75 mm` 与 `Y≈-15.25 mm`，实测中心 Z 分别为 `-3.19 mm` 与 `-3.09 mm`。两个面板孔均采用用户确认的 **12.8 × 5.5 mm、R0.7** 水平圆角矩形；旧版 13.3/13.4 × 6.0 mm 以及 15.4 × 7.8 mm 孔作废。

## 7. 04 接口面的逐像素结论

[04-n305-mainboard-bottom-rear-io-heatsink-edge-height-measurement.jpg](./04-n305-mainboard-bottom-rear-io-heatsink-edge-height-measurement.jpg) 的卡尺主刻线拟合比例是 20.3 px/mm。结合主板照片与原机面板上方的接口图标，沿边组合确认是：DC、HDMI、RJ45、上下叠层双 USB-A、HDMI；此前把下层误认作 HDMI 的结论作废。

03 校正平面给出的中心 Y 为 `+39.83 / +23.75 / +3.75 / -14.25 / -36.08 mm`。这些中心对原机 04 面板五孔的线性拟合最大残差为 0.634 mm，所以中心位置保留。面板孔尺寸采用用户后续确认的实测值：DC **Ø5.9**；两只 HDMI **16.5 × 5.8** 原壳六边形，顶边 10.7、倒角高 1.9；叠层双 USB 共用 **14.0 × 14.5、R0.7** 圆角窗口；RJ45 主窗 **15.0 × 10.0**，其下方另加 **4.5 × 1.0** relief。原壳照片只用于确认非矩形轮廓，没有使用通用 HDMI 标准轮廓。

05、07 照片没有显示侧向插拔的用户接口，因此这两面保持封闭。

## 8. 与 V0.2 分壳的关系

V0.2 使用两个由三相邻面构成的互补角壳：

- 上壳：顶面、06、05，包含双 USB 和按键。
- 下壳：底面、04、07，包含后置接口和排风开口。

装板时先把 06 边 USB 斜向送入上壳窗口，再放平主板和安装下壳。四个 PCB 安装孔轴同时连接主板及两壳，不设置额外壳体螺丝位。连续内搭边和连续卡槽已经从方案中取消，六段异件边采用平面对接；详细结构见 [../docs/v0.2-reference-review.md](../docs/v0.2-reference-review.md)。

## 9. 关系确认状态

- 风扇面与 PCB 底面的正反关系：已确认。
- 风扇面基准视图中的左 07、上 06、右 05、下 04：已由实物方位确认。
- 散热鳍片位于下方 04 边，04 与 06 相对：已确认。
- 05 与 07 相对：已确认。
- 板载电源开关位于 06 边且偏向 07/06 一侧，当前中心 `Y≈+29.5 mm`：已由 03 校正平面与 06 局部比例交叉检查；像素标定中心误差估计约 ±0.35 mm。
- “后置 I/O”是本项目采用的功能名称；若厂商资料使用其他前后命名，编号 04～07 和上述空间关系仍保持不变。
