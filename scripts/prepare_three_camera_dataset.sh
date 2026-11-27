#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Usage: prepare_three_camera_dataset.sh --source LEROBOT_DATASET [--output NAME]

Creates a separate LeRobot v3 dataset under runtime/update_data/ with:
  observation.images.image  <- observation.images.cam_high
  observation.images.image2 <- observation.images.cam_left_wrist
  observation.images.image3 <- observation.images.cam_right_wrist

The optional observation.images.cam_third_view stream is omitted. The source
dataset under runtime/lerobot/ is never modified.
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
OUTPUT="${OUTPUT:-${SOURCE}-three-camera}"

for value in "${SOURCE}" "${OUTPUT}"; do
  [[ "${value}" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$ ]] || {
    echo "Invalid dataset name: ${value}" >&2
    exit 2
  }
done

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_ROOT}"

ENV_FILE="${HKC_SIM_ENV_FILE:-${PROJECT_ROOT}/.env}"
if [[ -f "${ENV_FILE}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
elif [[ -n "${HKC_SIM_ENV_FILE:-}" ]]; then
  echo "Environment file does not exist: ${ENV_FILE}" >&2
  exit 1
fi

RUNTIME_ROOT="${HKC_SIM_RUNTIME_ROOT:-./runtime}"
mkdir -p "${RUNTIME_ROOT}/update_data"

[[ -d "${RUNTIME_ROOT}/lerobot/${SOURCE}" ]] || {
  echo "Source dataset does not exist: ${RUNTIME_ROOT}/lerobot/${SOURCE}" >&2
  exit 1
}
[[ ! -e "${RUNTIME_ROOT}/update_data/${OUTPUT}" ]] || {
  echo "Output dataset already exists: ${RUNTIME_ROOT}/update_data/${OUTPUT}" >&2
  exit 1
}

docker compose run --rm converter python \
  /workspace/scripts/prepare_three_camera_dataset.py \
  --source "/runtime/lerobot/${SOURCE}" \
  --output "/runtime/update_data/${OUTPUT}"

EXPECTED_EPISODES="$(python3 - "${RUNTIME_ROOT}/update_data/${OUTPUT}/meta/info.json" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as handle:
    print(int(json.load(handle)["total_episodes"]))
PY
)"
EXPECTED_ROBOT_TYPE="$(python3 - "${RUNTIME_ROOT}/update_data/${OUTPUT}/meta/info.json" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as handle:
    print(json.load(handle).get("robot_type", ""))
PY
)"

VALIDATION_ARGS=(
  --root "/runtime/update_data/${OUTPUT}"
  --expected-episodes "${EXPECTED_EPISODES}"
)
if [[ -n "${EXPECTED_ROBOT_TYPE}" ]]; then
  VALIDATION_ARGS+=(--expected-robot-type "${EXPECTED_ROBOT_TYPE}")
fi
docker compose run --rm converter python \
  /workspace/scripts/validate_lerobot_v3.py "${VALIDATION_ARGS[@]}"

echo "Three-camera conversion completed: ${RUNTIME_ROOT}/update_data/${OUTPUT}"
