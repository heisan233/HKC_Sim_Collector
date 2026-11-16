# 初始架构

```text
Ubuntu host
├── NVIDIA driver
├── Docker + NVIDIA Container Toolkit
├── X11 display
└── hkc-sim-collector container
    ├── RoboTwin / XPolicyLab
    ├── SAPIEN / CuRobo / PyTorch / CUDA userspace
    ├── HKC collection wrappers
    └── mounted assets and outputs
```

源码和配置进入 Git。大型资产、采集输出、转换结果、缓存和日志通过 bind mount 放在仓库之外或被忽略的 `runtime/` 中。

第一阶段不改动 VLA 平台。仿真数据完成 LeRobot v3 转换后，再使用平台既有上传工具导入。

