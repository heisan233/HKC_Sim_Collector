# 版本兼容矩阵

## 结论

本项目固定为两个独立镜像，而不是把所有依赖安装到同一个 Python 环境：

1. `robotwin`：运行 RoboTwin、SAPIEN、CuRobo 和 XPolicyLab，负责仿真与原始 HDF5 采集。
2. `converter`：运行 LeRobot 0.6.2 与 XPolicyLab 转换脚本，负责把 HDF5 转换为 LeRobot v3。

原因是 RoboTwin 官方环境使用 Python 3.10、CUDA 12.1 和 PyTorch 2.4.1；LeRobot 0.6.2 要求 Python 3.12，并由其 `uv.lock` 解析到 CUDA 12.8 的 PyTorch 2.11.0。强行合并会产生 Python、NumPy、PyTorch 和 CUDA 依赖冲突。

所有机器可读版本均以 [`docker/versions.lock.json`](../docker/versions.lock.json) 为准。

## 仿真采集镜像

| 组件 | 固定版本 |
| --- | --- |
| 系统 / CUDA | Ubuntu 22.04 / CUDA 12.1.1 |
| Python | 3.10 |
| PyTorch / TorchVision | 2.4.1+cu121 / 0.19.1+cu121 |
| RoboTwin | `ea8b21121ebb3cd201ff5b3fe361944ac94eda3f` |
| XPolicyLab | `fa431ecd893ee706883e64fe5fe1464ec8cd928d` |
| CuRobo | `v0.7.8` / `d64c4b005459db10c5dd867d8b30a87d5bda9bdb` |
| PyTorch3D | `stable` / `75ebeeaea0908c5527e7b1e305fbc7681382db47` |
| SAPIEN / mplib | 3.0.0b1 / 0.2.1 |
| NumPy | 1.26.4 |

RoboTwin 固定提交内已经把 XPolicyLab 固定为上述 Git 子模块提交，构建时必须使用 `git submodule update --init --recursive`，不得更新到子模块的最新 `main`。

## LeRobot v3 转换镜像

| 组件 | 固定版本 |
| --- | --- |
| 系统 / CUDA | Ubuntu 24.04 / CUDA 12.8.1 |
| Python | 3.12 |
| LeRobot | 包版本 0.6.2，提交 `dc0cee9c75e3cc684e4756013e214888176f2c15` |
| PyTorch / TorchVision | 2.11.0+cu128 / 0.26.0+cu128 |
| NumPy | 2.2.6 |
| OpenCV headless | 4.13.0.92 |
| PyAV | 15.1.0 |
| h5py | 3.11.0 |
| 视频编码 | PyAV / H.264 / CRF 18 |
| 转换脚本来源 | XPolicyLab `fa431ecd893ee706883e64fe5fe1464ec8cd928d` |

LeRobot 仓库没有 `v0.6.2` Git 标签。这里锁定的是其 `pyproject.toml` 首次声明 `version = "0.6.2"` 的确切提交，并在构建时使用该提交自带的 `uv.lock`，不能只执行未锁定的 `pip install lerobot`。

## 已确认的接口兼容性

XPolicyLab 的 `transform_lerobot_v30_format.py` 使用以下 LeRobot API：

- `LeRobotDataset.create`
- `LeRobotDataset.add_frame`
- `LeRobotDataset.save_episode`
- `LeRobotDataset.finalize`

这些 API 在锁定的 LeRobot 0.6.2 提交中均存在，但 XPolicyLab 脚本仍使用旧的流式编码器内部属性。本项目在镜像构建时执行严格的一次性文本匹配补丁：

- 适配 `dataset.writer._streaming_encoder`；
- 通过 `RGBEncoderConfig` 配置编码器；
- 保留 RoboTwin 的 `cam_third_view` 第四路视频；
- 使用软件 H.264，避免消费级 GPU 多路 NVENC 会话限制；
- 补充 XPolicyLab HDF5 加载所需的 h5py 3.11.0。

2026-11-17 已完成真实端到端验证：1 个 Episode、114 帧、1 个任务、4 路视频，LeRobotDataset 能加载首帧，动作和状态均为 14 维。

## GPU 与宿主机条件

- 本机 RTX 4060 和服务器 RTX 4090 都是 CUDA Compute Capability 8.9。
- 宿主机只提供 NVIDIA 驱动、NVIDIA Container Toolkit、Vulkan/X11；Python、CUDA 用户态库、PyTorch、SAPIEN 和 CuRobo 全部放入独立镜像。
- 容器启动时需要 `NVIDIA_DRIVER_CAPABILITIES=compute,utility,graphics,display`；缺少 `graphics` 可能导致 Vulkan/SAPIEN 失败。

## 构建约束

- 禁止使用 `main`、`latest` 或浮动 Git 标签作为最终来源。
- 基础镜像同时锁定标签、清单摘要和 amd64 子清单摘要。
- 上游源码必须校验实际 `HEAD` 等于锁定提交。
- LeRobot 依赖严格使用上游 `uv.lock`；额外的 h5py 明确固定为 3.11.0。
- 任何版本升级都必须新建兼容性验证记录，不能直接覆盖本文件中的版本。

## 官方依据

- RoboTwin 安装文档：Python 3.10、推荐 CUDA 12.1，并要求 Docker 启用 NVIDIA graphics capability。
- RoboTwin 固定提交中的 `scripts/requirements.txt` 和 `scripts/_install.sh`。
- PyTorch 官方历史版本表：PyTorch 2.4.1 对应 TorchVision 0.19.1，并提供 CUDA 12.1 wheel。
- LeRobot 固定提交中的 `pyproject.toml`、`uv.lock` 与 `docker/Dockerfile.internal`。
- XPolicyLab 固定提交中的 `scripts/transform_lerobot_v30_format.py`。

参考链接：

- https://robotwin-platform.github.io/doc/usage/robotwin-install.html
- https://github.com/RoboTwin-Platform/RoboTwin
- https://github.com/XPolicyLab/XPolicyLab
- https://pytorch.org/get-started/previous-versions/
- https://github.com/huggingface/lerobot
