ARG ROBOTWIN_BASE_IMAGE=nvidia/cuda:12.1.1-devel-ubuntu22.04@sha256:7012e535a47883527d402da998384c30b936140c05e2537158c80b8143ee7425
FROM ${ROBOTWIN_BASE_IMAGE}

ARG APP_UID=1000
ARG APP_GID=1000
ARG PIP_INDEX_URL=https://pypi.org/simple
ARG ROBOTWIN_COMMIT=ea8b21121ebb3cd201ff5b3fe361944ac94eda3f
ARG XPOLICYLAB_COMMIT=fa431ecd893ee706883e64fe5fe1464ec8cd928d
ARG CUROBO_COMMIT=d64c4b005459db10c5dd867d8b30a87d5bda9bdb
ARG PYTORCH3D_COMMIT=75ebeeaea0908c5527e7b1e305fbc7681382db47

LABEL org.opencontainers.image.title="HKC RoboTwin Collector"
LABEL org.opencontainers.image.description="Pinned RoboTwin 2.0 simulation and XPolicyLab HDF5 collection runtime"
LABEL org.opencontainers.image.revision="${ROBOTWIN_COMMIT}"

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_INDEX_URL=${PIP_INDEX_URL} \
    CUDA_HOME=/usr/local/cuda \
    TORCH_CUDA_ARCH_LIST=8.9 \
    MAX_JOBS=4 \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility,graphics,display \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential ca-certificates cmake curl ffmpeg git git-lfs \
      libdbus-1-3 libegl1 libgl1 libglib2.0-0 libsm6 libvulkan1 \
      libx11-6 libx11-xcb1 libxext6 libxkbcommon-x11-0 libxrender1 \
      ninja-build patchelf pkg-config python3.10 python3.10-dev python3-pip \
      unzip vulkan-tools wget \
    && rm -rf /var/lib/apt/lists/*

COPY docker/requirements-robotwin.lock.txt /tmp/requirements-robotwin.lock.txt

RUN python3.10 -m pip install --upgrade \
      pip==24.3.1 setuptools==69.5.1 wheel==0.44.0 \
    && python3.10 -m pip install \
      torch==2.4.1 torchvision==0.19.1 \
      --index-url https://download.pytorch.org/whl/cu121 \
    && python3.10 -m pip install -r /tmp/requirements-robotwin.lock.txt

ARG ROBOTWIN_GIT_URL=https://github.com/RoboTwin-Platform/RoboTwin.git
ARG XPOLICYLAB_GIT_URL=https://github.com/XPolicyLab/XPolicyLab.git
RUN git init /opt/robotwin \
    && git -C /opt/robotwin remote add origin "${ROBOTWIN_GIT_URL}" \
    && git -C /opt/robotwin fetch --depth 1 origin "${ROBOTWIN_COMMIT}" \
    && git -C /opt/robotwin checkout --detach FETCH_HEAD \
    && test "$(git -C /opt/robotwin rev-parse HEAD)" = "${ROBOTWIN_COMMIT}" \
    && rm -rf /opt/robotwin/XPolicyLab \
    && git init /opt/robotwin/XPolicyLab \
    && git -C /opt/robotwin/XPolicyLab remote add origin "${XPOLICYLAB_GIT_URL}" \
    && git -C /opt/robotwin/XPolicyLab fetch --depth 1 origin "${XPOLICYLAB_COMMIT}" \
    && git -C /opt/robotwin/XPolicyLab checkout --detach FETCH_HEAD \
    && test "$(git -C /opt/robotwin/XPolicyLab rev-parse HEAD)" = "${XPOLICYLAB_COMMIT}" \
    && python3.10 -m pip install --no-deps -e /opt/robotwin/XPolicyLab

RUN python3.10 - <<'PY'
from pathlib import Path
import mplib
import sapien

urdf_loader = Path(sapien.__file__).resolve().parent / "wrapper" / "urdf_loader.py"
text = urdf_loader.read_text(encoding="utf-8")
text = text.replace('with open(urdf_file, "r") as f:', 'with open(urdf_file, "r", encoding="utf-8") as f:')
text = text.replace('srdf_file = urdf_file[:-4] + "srdf"', 'srdf_file = urdf_file[:-4] + ".srdf"')
text = text.replace('with open(srdf_file, "r") as f:', 'with open(srdf_file, "r", encoding="utf-8") as f:')
urdf_loader.write_text(text, encoding="utf-8")

planner = Path(mplib.__file__).resolve().parent / "planner.py"
text = planner.read_text(encoding="utf-8")
old = "if np.linalg.norm(delta_twist) < 1e-4 or collide or not within_joint_limit:"
new = "if np.linalg.norm(delta_twist) < 1e-4 or not within_joint_limit:"
if old not in text and new not in text:
    raise RuntimeError("mplib compatibility patch location was not found")
planner.write_text(text.replace(old, new), encoding="utf-8")
PY

ARG CUROBO_GIT_URL=https://github.com/NVlabs/curobo.git
RUN git init /opt/curobo \
    && git -C /opt/curobo remote add origin "${CUROBO_GIT_URL}" \
    && git -C /opt/curobo fetch --depth 1 origin "${CUROBO_COMMIT}" \
    && git -C /opt/curobo checkout --detach FETCH_HEAD \
    && test "$(git -C /opt/curobo rev-parse HEAD)" = "${CUROBO_COMMIT}" \
    && python3.10 -m pip install --no-deps --no-build-isolation -e /opt/curobo

ARG PYTORCH3D_GIT_URL=https://github.com/facebookresearch/pytorch3d.git
RUN git init /opt/pytorch3d \
    && git -C /opt/pytorch3d remote add origin "${PYTORCH3D_GIT_URL}" \
    && git -C /opt/pytorch3d fetch --depth 1 origin "${PYTORCH3D_COMMIT}" \
    && git -C /opt/pytorch3d checkout --detach FETCH_HEAD \
    && test "$(git -C /opt/pytorch3d rev-parse HEAD)" = "${PYTORCH3D_COMMIT}" \
    && python3.10 -m pip install --no-deps --no-build-isolation -e /opt/pytorch3d

RUN printf '%s\n' \
      "ROBOTWIN_COMMIT=${ROBOTWIN_COMMIT}" \
      "XPOLICYLAB_COMMIT=${XPOLICYLAB_COMMIT}" \
      "CUROBO_COMMIT=${CUROBO_COMMIT}" \
      "PYTORCH3D_COMMIT=${PYTORCH3D_COMMIT}" \
      > /opt/hkc-robotwin-versions.txt \
    && rm -rf /opt/robotwin/.git /opt/robotwin/XPolicyLab/.git \
              /opt/curobo/.git /opt/pytorch3d/.git /root/.cache/pip \
    && groupadd --gid "${APP_GID}" hkc \
    && useradd --uid "${APP_UID}" --gid "${APP_GID}" --create-home --shell /bin/bash hkc \
    && mkdir -p /runtime /workspace \
    && chown -R hkc:hkc /opt/robotwin /opt/curobo /opt/pytorch3d /runtime /workspace

USER hkc
WORKDIR /opt/robotwin

RUN python3.10 - <<'PY'
import gymnasium
import h5py
import mplib
import numpy
import sapien
import torch
import torchvision
import transforms3d
import trimesh
from curobo.types.base import TensorDeviceType

print("RoboTwin Python dependencies imported successfully")
PY

RUN python3.10 -m pip check

CMD ["/bin/bash"]
