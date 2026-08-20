# 主板参考导出

本目录由 `scripts/build_motherboard_reference.py` 生成。所有模型使用毫米和项目唯一坐标系：`+X=06`、`-X=04`、`+Y=07`、`-Y=05`、`+Z=风扇面`，PCB 底面为 `Z=0`。

## physical

- `n305_motherboard_reference.step/.stl`：PCB、接口、板载开关和散热组件的总装参考。
- `n305_pcb.step/.stl`：带四个安装孔的 PCB。
- `n305_connectors_and_switch.step/.stl`：04/06 接口实体和板载电源开关。
- `n305_cooling_assembly.step/.stl`：冷板支撑、风扇托板、照片描摩蜗壳、32 片叶轮、热桥和鳍片；不含缺少侧视高度证据的双孔长条。

这些文件是用于机壳设计的物理参考，不是厂商制造模型。连接器隐藏壳体和散热组件细节含照片估计。

## clearances

- `n305_cooling_keepout.step/.stl`：风扇与鳍片上方保守包络。
- `n305_underside_keepouts.step/.stl`：底面器件的保守避让包络。
- `n305_mount_axes.step/.stl`：四个 PCB 孔的装配轴线。

避让体不能与 `physical` 文件合并后当作实物体积使用。

## validation.json

记录数据源、PCB/孔位、Z 包络、接口参数、各零件边界和散热接触检查。当前检查必须全部通过，且 `enclosure_geometry_generated` 必须为 `false`。

重新生成：

```bash
PYTHONPATH=src .venv/bin/python scripts/build_motherboard_reference.py
```
