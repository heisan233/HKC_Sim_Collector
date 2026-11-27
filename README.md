# HKC Sim Collector

HKC 仿真数据采集项目。项目使用两个相互隔离的 Docker 镜像完成：

1. RoboTwin 2.0 仿真和 XPolicyLab HDF5 采集；
2. HDF5 到 LeRobot v3.0 的转换与校验。

现有 VLA 数据平台不放入本仓库，也不由本项目修改。

## 当前状态

本机端到端最小流程已于 2026-11-17 验证通过：

- RoboTwin 仿真采集 1 个 Episode；
- 输出有效 XPolicyLab HDF5 和预览视频；
- 转换得到 LeRobot v3.0：114 帧、1 个任务、4 路视频；
- LeRobot 0.6.2 能加载数据集和首帧；
- 动作与状态均为 14 维。

固定版本见 `docker/versions.lock.json`，兼容性说明见 `docs/version-compatibility.md`。

## 目录说明

```text
configs/          机器人、任务和采集参数
docker/           仿真镜像与容器说明
scripts/          构建、启动、采集、转换和校验脚本
src/              HKC 自己维护的封装代码
tests/            不依赖真实大数据的最小测试
docs/             架构、部署和使用说明
manifests/        采集来源记录的结构说明；生成记录不提交 Git
compose.yaml      本地与服务器共用的容器入口
```

## 数据边界

以下内容不得提交 Git：

- RoboTwin 大型资产；
- 仿真原始 HDF5；
- LeRobot 数据集；
- 视频、模型权重、缓存和日志；
- 每次运行自动生成的 manifest。

默认运行数据放在被 Git 忽略的 `runtime/` 中。服务器部署时会通过环境变量将它改到 `/srv/hkc-ai/simulation/robotwin/`。

## RoboTwin 采集

离屏采集速度更快，结果会写入 HDF5 和 MP4：

```bash
./scripts/collect.sh \
  --dataset test-beat-block-001 \
  --task beat_block_hammer \
  --episodes 1 \
  --embodiment aloha-agilex \
  --gpu 0
```

需要同时观看规划和正式采集窗口时使用独立脚本：

```bash
./scripts/collect_windows.sh \
  --dataset test-beat-block-window-001 \
  --task beat_block_hammer \
  --episodes 1 \
  --embodiment aloha-agilex \
  --gpu 0
```

窗口模式必须从 Ubuntu 图形桌面的终端运行。两种模式都不会覆盖已有数据集，结果位于 `runtime/raw/<数据集名称>/`。

## LeRobot v3 转换

构建转换镜像：

```bash
./scripts/build_converter.sh
```

网络受限时，可在 `.env` 中设置 `LEROBOT_BASE_IMAGE`、`LEROBOT_GIT_URL` 和 `PIP_INDEX_URL`，不会改变锁定的源码提交与依赖版本。

转换已采集的数据集：

```bash
./scripts/convert_to_lerobot.sh \
  --source test-beat-block-002 \
  --output test-beat-block-002-lerobot-v3
```

转换流程会：

- 拒绝覆盖已有目标；
- 先写入 `runtime/staging/`；
- 将采集 manifest 的真实 `embodiment` 写入 `meta/info.json.robot_type`；
- 使用离线视频编码，避免流式队列满时丢帧；
- 验证 v3 元数据、Parquet、每路视频帧数和首帧加载；
- 验证通过后原子发布到 `runtime/lerobot/<输出名称>/`；
- 写入 `runtime/manifests/<输出名称>.json` 转换来源记录。

### 预览 MP4 与训练帧数

RoboTwin 原始采集目录中的预览 MP4 只供人工查看，可能比 HDF5 和正式训练数据多
1 帧。这是因为预览视频保存全部观测画面，而训练数据按“当前状态 → 下一步动作”
组成时间步：采集到 `N` 个观测时，通常只能组成 `N-1` 组状态—动作转移。

例如预览 MP4 为 119 帧时，HDF5、LeRobot v3 Parquet 和 LeRobot 正式相机视频
可能均为 118 帧。这不是视频编码丢帧，也不会影响训练。训练数据是否有效，应以
HDF5 时间步、Parquet 行数以及 `runtime/lerobot/` 下每路正式视频的帧数校验结果
为准，不应使用原始预览 MP4 的帧数判断。

## 一条命令完成采集与转换

完成镜像构建和资产下载后，可以使用统一入口顺序执行采集、转换和校验：

```bash
./scripts/collect_and_convert.sh \
  --dataset pipeline-beat-block-001 \
  --task beat_block_hammer \
  --episodes 1 \
  --embodiment aloha-agilex \
  --gpu 0
```

`--episodes` 接受任意正整数，不设置固定上限。正式批量采集前应先确认 GPU、磁盘空间、任务成功率和预计运行时间；同名数据集仍会拒绝覆盖。

统一入口会自动读取项目根目录 `.env`。如果调用命令前已经显式设置同名环境变量，
显式设置优先；也可以通过 `HKC_SIM_ENV_FILE=/path/to/file` 指定其他配置文件。

独立入口 `collect.sh`、`collect_windows.sh` 和 `convert_to_lerobot.sh` 使用同一规则，
也会自动读取 `.env`，单独调试时不需要先执行 `source .env`。

需要观看规划和正式采集窗口时增加 `--show-window`。默认输出名称为
`<数据集名称>-lerobot-v3`，也可通过 `--output` 指定。

统一入口不会合并两个镜像：RoboTwin 镜像仍负责 HDF5 采集，LeRobot 镜像仍负责
转换与验证。采集失败时不会开始转换；转换失败时保留已经完成的原始 HDF5，便于
修复后单独重试。完整日志写入 `runtime/logs/<数据集名称>-pipeline.log`。

平台上传时，仿真机器人档案的类型必须与采集使用的 `--embodiment` 完全一致。
例如 `--embodiment aloha-agilex` 会生成 `robot_type="aloha-agilex"`。

## 数据位置

```text
runtime/raw/        RoboTwin HDF5 原始采集结果
runtime/lerobot/    已验证的 LeRobot v3 数据集
runtime/staging/    采集或转换暂存目录
runtime/manifests/  转换来源记录
runtime/assets/     RoboTwin 大型资产
runtime/cache/      下载缓存
```

## 下一步

1. 由用户验收本机统一采集与转换入口；
2. 在服务器完成 GPU、图形桌面、采集和转换复验；
3. 再接入 VLA 数据平台上传工具。

