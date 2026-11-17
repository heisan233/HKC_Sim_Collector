# Docker 目录

本目录维护两套独立环境：

- `Dockerfile`：RoboTwin、SAPIEN、CuRobo 与 XPolicyLab，用于仿真和 HDF5 采集；
- `Dockerfile.lerobot`：LeRobot 0.6.2 与 XPolicyLab 转换工具，用于生成并校验 LeRobot v3。

关键版本固定在 `versions.lock.json`，兼容性理由记录在 `../docs/version-compatibility.md`。两个镜像不共享 Python 环境，只通过 `runtime/` 交换数据。

本机已验证：

- `hkc-sim-collector:robotwin-2.0`：GPU、Vulkan、SAPIEN、CuRobo 和 HDF5 采集正常；
- `hkc-sim-collector:lerobot-v0.6.2`：GPU、PyTorch、HDF5 读取、四路软件 H.264 与 LeRobot v3 加载正常。

转换镜像使用软件 H.264 编码四路视频。单路 NVENC 可用，但消费级 GPU 的并发编码会话不适合作为可移植的默认方案。

