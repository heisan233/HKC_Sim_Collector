# 脚本目录

后续脚本按职责拆分：

- 环境与 GPU/Vulkan 预检查；
- 镜像构建；
- 运行目录初始化；
- 单任务采集；
- HDF5 转换为 LeRobot v3；
- 使用 `collect_and_convert.sh` 串联采集、转换和校验；
- 数据结构校验；
- 离线部署包生成。

