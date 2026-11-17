#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Usage: convert_to_lerobot.sh --source RAW_DATASET [--output LEROBOT_DATASET]

Converts one completed RoboTwin/XPolicyLab HDF5 dataset under runtime/raw/
into a validated LeRobot v3 dataset under runtime/lerobot/.
EOF
}

SOURCE=""
OUTPUT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --source) SOURCE="${2:?missing source dataset name}"; shift 2 ;;
    --output) OUTPUT="${2:?missing output dataset name}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ -n "${SOURCE}" ]] || { usage >&2; exit 2; }
OUTPUT="${OUTPUT:-${SOURCE}-lerobot-v3}"

for value in "${SOURCE}" "${OUTPUT}"; do
  [[ "${value}" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$ ]] || {
    echo "Invalid dataset name: ${value}" >&2
    exit 2
  }
done

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_ROOT}"
RUNTIME_ROOT="${HKC_SIM_RUNTIME_ROOT:-./runtime}"
mkdir -p "${RUNTIME_ROOT}"/{assets,staging,raw,lerobot,cache,logs,manifests}

[[ -d "${RUNTIME_ROOT}/raw/${SOURCE}" ]] || { echo "Source dataset does not exist: ${RUNTIME_ROOT}/raw/${SOURCE}" >&2; exit 1; }
[[ ! -e "${RUNTIME_ROOT}/lerobot/${OUTPUT}" ]] || { echo "Output dataset already exists: ${RUNTIME_ROOT}/lerobot/${OUTPUT}" >&2; exit 1; }
[[ ! -e "${RUNTIME_ROOT}/staging/${OUTPUT}.convert.work" ]] || { echo "Conversion staging already exists: ${RUNTIME_ROOT}/staging/${OUTPUT}.convert.work" >&2; exit 1; }

docker compose run --rm \
  -e HKC_SOURCE_DATASET="${SOURCE}" \
  -e HKC_OUTPUT_DATASET="${OUTPUT}" \
  converter bash /workspace/scripts/convert_in_container.sh

echo "Conversion completed: ${RUNTIME_ROOT}/lerobot/${OUTPUT}"
