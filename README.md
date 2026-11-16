# HKC Sim Collector

HKC 仿真数据采集项目。第一阶段基于 RoboTwin 2.0，在独立 Docker 容器中完成仿真、原始数据保存和 LeRobot v3 转换；现有 VLA 数据平台不放入本仓库，也不由本项目修改。

## 当前状态

当前仅完成独立项目骨架。Dockerfile 还是占位版本，尚未锁定 RoboTwin、XPolicyLab、CuRobo、SAPIEN、PyTorch、CUDA 和 LeRobot 版本，因此暂时不要用于正式采集。

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

## 下一步

1. 锁定上游源码和依赖版本。
2. 替换占位 Dockerfile。
3. 下载最小机器人与任务资产。
4. 在 RTX 4060 上执行 1～3 个 Episode 的最小验证。
5. 验证通过后再制作服务器离线部署包。

