#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Usage: collect.sh --dataset NAME [--task TASK] [--episodes POSITIVE_INTEGER]
                  [--embodiment NAME] [--gpu INDEX]

Defaults:
  task:        beat_block_hammer
  episodes:    1
  embodiment:  aloha-agilex
  gpu:         0
EOF
}

DATASET=""
TASK="beat_block_hammer"
EPISODES="1"
EMBODIMENT="aloha-agilex"
GPU="0"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dataset) DATASET="${2:?missing dataset name}"; shift 2 ;;
    --task) TASK="${2:?missing task name}"; shift 2 ;;
    --episodes) EPISODES="${2:?missing episode count}"; shift 2 ;;
    --embodiment) EMBODIMENT="${2:?missing embodiment}"; shift 2 ;;
    --gpu) GPU="${2:?missing GPU index}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ -n "${DATASET}" ]] || { usage >&2; exit 2; }
[[ "${DATASET}" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$ ]] || { echo "Invalid dataset name" >&2; exit 2; }
[[ "${TASK}" =~ ^[a-z0-9_]+$ ]] || { echo "Invalid task name" >&2; exit 2; }
[[ "${EPISODES}" =~ ^[1-9][0-9]*$ ]] || { echo "Episodes must be a positive integer" >&2; exit 2; }
[[ "${GPU}" =~ ^[0-9]+$ ]] || { echo "Invalid GPU index" >&2; exit 2; }

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_ROOT}"
RUNTIME_ROOT="${HKC_SIM_RUNTIME_ROOT:-./runtime}"
mkdir -p "${RUNTIME_ROOT}"/{assets,staging,raw,lerobot,cache,logs,manifests}

[[ ! -e "${RUNTIME_ROOT}/raw/${DATASET}" ]] || { echo "Dataset already exists: ${RUNTIME_ROOT}/raw/${DATASET}" >&2; exit 1; }
[[ ! -e "${RUNTIME_ROOT}/staging/${DATASET}.work" ]] || { echo "Staging run already exists: ${RUNTIME_ROOT}/staging/${DATASET}.work" >&2; exit 1; }

docker compose run --rm \
  -e HKC_DATASET_NAME="${DATASET}" \
  -e HKC_TASK_NAME="${TASK}" \
  -e HKC_EPISODE_COUNT="${EPISODES}" \
  -e HKC_EMBODIMENT="${EMBODIMENT}" \
  -e CUDA_VISIBLE_DEVICES="${GPU}" \
  robotwin bash /workspace/scripts/collect_in_container.sh

echo "Collection completed: ${RUNTIME_ROOT}/raw/${DATASET}"
