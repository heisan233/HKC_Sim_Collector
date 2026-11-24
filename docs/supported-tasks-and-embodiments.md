# 当前支持的任务与机型

更新时间：2026-11-19

本文记录当前锁定版本中可发现的 RoboTwin 任务、机型资产，以及已经完成的真实验收结果。这里的“镜像内存在”不等于“已经稳定支持”；只有完成相应测试的组合才列入已验证清单。

## 支持状态定义

| 状态 | 含义 |
| --- | --- |
| 端到端已验证 | 已完成仿真采集、HDF5 输出、LeRobot v3 转换和数据集加载验证。 |
| 采集已验证 | 已成功生成有效 HDF5，但尚未完成 LeRobot v3 转换验证。 |
| 可选但未验证 | 锁定的 RoboTwin 镜像中存在相应任务代码或机型资产，尚未完成真实验收。 |
| 暂不可直接使用 | 资产存在，但当前 HKC 启动脚本的配置方式尚不适配。 |

## 已验证组合

| 机型参数 | 任务参数 | Episode | 验证范围 | 当前状态 |
| --- | --- | ---: | --- | --- |
| `aloha-agilex` | `beat_block_hammer` | 1 | 可视/离屏采集、HDF5、四路视频、LeRobot v3、首帧加载 | 端到端已验证 |
| `aloha-agilex` | `grab_roller` | 1 | 可视采集、HDF5 | 采集已验证 |

`grab_roller` 在完成 LeRobot v3 转换并通过加载验证前，不升级为端到端已验证。

## 当前机型

| 显示名称 | `--embodiment` 参数 | 当前状态 | 说明 |
| --- | --- | --- | --- |
| Aloha AgileX | `aloha-agilex` | 已验证 | 整体双臂资产，当前脚本可直接使用。 |
| Franka Panda | `franka-panda` | 暂不可直接使用 | 属于单臂资产；双臂运行需要两个 Franka 配置和臂间距，当前脚本尚未适配。 |
| Piper | `piper` | 暂不可直接使用 | 与 Franka 相同，需要单臂组合配置和臂间距。 |
| ARX X5 | `ARX-X5` | 暂不可直接使用 | 与 Franka 相同，需要单臂组合配置和臂间距。参数大小写必须保持一致。 |
| UR5 + WSG | `ur5-wsg` | 暂不可直接使用 | 与 Franka 相同，需要单臂组合配置和臂间距。 |

当前请优先使用 `aloha-agilex` 测试不同任务。不要把另外四种机型仅因资产已经下载就视为正式支持。

## 镜像内可发现的任务

锁定镜像中共有 50 个任务模块。除上方已验证组合外，其余任务均为“可选但未验证”。命令中必须使用以下准确名称：

```text
adjust_bottle
beat_block_hammer
blocks_ranking_rgb
blocks_ranking_size
click_alarmclock
click_bell
dump_bin_bigbin
grab_roller
handover_block
handover_mic
hanging_mug
lift_pot
move_can_pot
move_pillbottle_pad
move_playingcard_away
move_stapler_pad
open_laptop
open_microwave
pick_diverse_bottles
pick_dual_bottles
place_a2b_left
place_a2b_right
place_bread_basket
place_bread_skillet
place_burger_fries
place_can_basket
place_cans_plasticbox
place_container_plate
place_dual_shoes
place_empty_cup
place_fan
place_mouse_pad
place_object_basket
place_object_scale
place_object_stand
place_phone_stand
place_shoe
press_stapler
put_bottles_dustbin
put_object_cabinet
rotate_qrcode
scan_object
shake_bottle
shake_bottle_horizontally
stack_blocks_three
stack_blocks_two
stack_bowls_three
stack_bowls_two
stamp_seal
turn_switch
```

任务代码存在不代表它和所有机型的组合都能成功规划。每个新组合都需要至少完成一次真实采集验收。

## 已验证用法

### 统一完成采集、转换和校验

```bash
./scripts/collect_and_convert.sh \
  --dataset pipeline-beat-block-001 \
  --task beat_block_hammer \
  --episodes 1 \
  --embodiment aloha-agilex \
  --gpu 0
```

需要显示仿真窗口时增加 `--show-window`。该统一入口当前等待人工完成一次真实
端到端验收；下面的独立采集和转换入口继续保留。

### 可视化采集

每次使用新的数据集名称：

```bash
./scripts/collect_windows.sh \
  --dataset test-beat-block-004 \
  --task beat_block_hammer \
  --episodes 1 \
  --embodiment aloha-agilex \
  --gpu 0
```

离屏采集时将 `collect_windows.sh` 改为 `collect.sh`。

### 转换为 LeRobot v3

```bash
./scripts/convert_to_lerobot.sh \
  --source test-beat-block-004 \
  --output test-beat-block-004-lerobot-v3
```

转换命令会自动检查元数据、Parquet、视频和 LeRobotDataset 首帧加载。只有命令正常完成并生成 `runtime/lerobot/<输出名称>/`，才算端到端验证通过。

## 当前限制

- 单次验收脚本只接受 1～3 个 Episode。
- 已存在的正式数据集名称不会被覆盖。
- 当前没有自动判断“任务 × 机型”兼容性的矩阵。
- Franka、Piper、ARX-X5 和 UR5 需要后续增加双单臂组合参数及 `arm distance` 支持。
- 规划阶段某个 seed 失败后找到成功 seed 属于正常重试；缺文件或对象未初始化则属于配置错误，应立即停止。

## 新组合的验收规则

一个新组合至少满足以下条件后，才能加入“采集已验证”：

1. 仿真规划最终成功；
2. 正式采集完成指定 Episode；
3. 生成非空 HDF5 和预览视频；
4. `manifest.json` 中的任务、机型和 Episode 数正确；
5. 没有把缺文件、初始化失败等确定性错误当作 seed 重试。

完成 LeRobot v3 转换、自动校验和首帧加载后，才可升级为“端到端已验证”。
