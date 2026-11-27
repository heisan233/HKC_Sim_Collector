# 脚本目录

后续脚本按职责拆分：

- 环境与 GPU/Vulkan 预检查；
- 镜像构建；
- 运行目录初始化；
- 单任务采集；
- HDF5 转换为 LeRobot v3；
- 使用 `collect_and_convert.sh` 串联采集、转换和校验；
- 数据结构校验；
- 将四相机 LeRobot v3 派生为 `image/image2/image3` 三相机训练数据集；
- 离线部署包生成。

三相机派生数据集使用：

```bash
./scripts/prepare_three_camera_dataset.sh \
  --source <runtime/lerobot 下的数据集名称> \
  --output <新数据集名称>
```

结果写入 `runtime/update_data/<新数据集名称>`。原数据集不会修改，
`cam_third_view` 不进入派生版本，上传完成标记也不会复制。

