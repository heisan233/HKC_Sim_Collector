#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_ROOT}"

docker compose run --rm robotwin bash -lc '
set -Eeuo pipefail
echo "=== NVIDIA GPU ==="
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader

echo "=== Vulkan ==="
vulkaninfo --summary | sed -n "1,100p"

echo "=== Python / CUDA / SAPIEN / CuRobo ==="
python3.10 - <<"PY"
import torch
import sapien.core as sapien
from sapien.render import set_global_config
from curobo.types.base import TensorDeviceType

assert torch.cuda.is_available(), "PyTorch cannot access CUDA"
assert torch.cuda.get_device_capability() == (8, 9)
set_global_config(max_num_materials=1024, max_num_textures=1024)
engine = sapien.Engine()
renderer = sapien.SapienRenderer()
engine.set_renderer(renderer)
scene = engine.create_scene(sapien.SceneConfig())
assert scene is not None
tensor_args = TensorDeviceType()
assert tensor_args.device.type == "cuda"
print("torch", torch.__version__)
print("cuda", torch.version.cuda)
print("gpu", torch.cuda.get_device_name(0))
print("SAPIEN renderer: OK")
print("CuRobo CUDA device:", tensor_args.device)
PY
'
