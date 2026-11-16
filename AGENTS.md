# HKC Sim Collector development rules

- 本项目必须保持为独立 Git 仓库，不修改相邻的 VLA 数据平台仓库。
- RoboTwin、XPolicyLab、CuRobo、SAPIEN、PyTorch、CUDA 和 LeRobot 必须锁定版本或提交，不直接追随未固定的最新版。
- 大型资产、数据集、视频、模型、缓存、日志和运行 manifest 不得提交 Git。
- 采集输出先写入 staging；同名正式数据集已存在时必须拒绝覆盖。
- 本地只做小规模验证；服务器批量运行前必须获得用户明确确认，并确认 GPU 空闲。
- 遇到软件源、镜像仓库、GitHub 或资产下载网络问题时停止，让用户先处理网络。
- 不得在未经确认的情况下部署服务器、删除数据、清理镜像或改动现有平台容器。
- 脚本应使用明确参数、失败即退出，并为危险操作提供预检查。

