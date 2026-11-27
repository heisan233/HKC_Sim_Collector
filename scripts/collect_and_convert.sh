#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Usage: collect_and_convert.sh --dataset NAME [--output NAME]
                              [--task TASK] [--episodes POSITIVE_INTEGER]
                              [--embodiment NAME] [--gpu INDEX]
                              [--show-window]

Collects one RoboTwin dataset and, only after collection succeeds, converts it
to a validated LeRobot v3 dataset.

Defaults:
  output:       <dataset>-lerobot-v3
  task:         beat_block_hammer
  episodes:     1
  embodiment:   aloha-agilex
  gpu:          0
EOF
}

DATASET=""
OUTPUT=""
TASK="beat_block_hammer"
EPISODES="1"
EMBODIMENT="aloha-agilex"
GPU="0"
SHOW_WINDOW="false"
LOADED_ENV_FILE=""

load_project_env() {
  local env_file="${HKC_SIM_ENV_FILE:-${PROJECT_ROOT}/.env}"
  local line=""
  local name=""
  local allexport_was_set="false"
  local -A preserved=()

  if [[ ! -e "${env_file}" ]]; then
    if [[ -n "${HKC_SIM_ENV_FILE:-}" ]]; then
      echo "Environment file does not exist: ${env_file}" >&2
      return 1
    fi
    return 0
  fi
  [[ -f "${env_file}" ]] || {
    echo "Environment file is not a regular file: ${env_file}" >&2
    return 1
  }

  # Explicitly exported variables take precedence over values in .env.
  while IFS= read -r line || [[ -n "${line}" ]]; do
    if [[ "${line}" =~ ^[[:space:]]*(export[[:space:]]+)?([A-Za-z_][A-Za-z0-9_]*)= ]]; then
      name="${BASH_REMATCH[2]}"
      if [[ -v "${name}" ]]; then
        preserved["${name}"]="${!name}"
      fi
    fi
  done < "${env_file}"

  [[ "$-" == *a* ]] && allexport_was_set="true"
  set -a
  # shellcheck disable=SC1090
  source "${env_file}"
  [[ "${allexport_was_set}" == "true" ]] || set +a

  for name in "${!preserved[@]}"; do
    printf -v "${name}" '%s' "${preserved[${name}]}"
    export "${name}"
  done
  LOADED_ENV_FILE="${env_file}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dataset) DATASET="${2:?missing dataset name}"; shift 2 ;;
    --output) OUTPUT="${2:?missing output dataset name}"; shift 2 ;;
    --task) TASK="${2:?missing task name}"; shift 2 ;;
    --episodes) EPISODES="${2:?missing episode count}"; shift 2 ;;
    --embodiment) EMBODIMENT="${2:?missing embodiment}"; shift 2 ;;
    --gpu) GPU="${2:?missing GPU index}"; shift 2 ;;
    --show-window) SHOW_WINDOW="true"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ -n "${DATASET}" ]] || { usage >&2; exit 2; }
OUTPUT="${OUTPUT:-${DATASET}-lerobot-v3}"

for value in "${DATASET}" "${OUTPUT}"; do
  [[ "${value}" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$ ]] || {
    echo "Invalid dataset name: ${value}" >&2
    exit 2
  }
done
[[ "${TASK}" =~ ^[a-z0-9_]+$ ]] || { echo "Invalid task name: ${TASK}" >&2; exit 2; }
[[ "${EPISODES}" =~ ^[1-9][0-9]*$ ]] || { echo "Episodes must be a positive integer" >&2; exit 2; }
[[ "${GPU}" =~ ^[0-9]+$ ]] || { echo "Invalid GPU index: ${GPU}" >&2; exit 2; }

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_ROOT}"
load_project_env

RUNTIME_ROOT="${HKC_SIM_RUNTIME_ROOT:-./runtime}"
COLLECT_SCRIPT="${HKC_PIPELINE_COLLECT_SCRIPT:-${PROJECT_ROOT}/scripts/collect.sh}"
WINDOW_SCRIPT="${HKC_PIPELINE_WINDOW_SCRIPT:-${PROJECT_ROOT}/scripts/collect_windows.sh}"
CONVERT_SCRIPT="${HKC_PIPELINE_CONVERT_SCRIPT:-${PROJECT_ROOT}/scripts/convert_to_lerobot.sh}"

mkdir -p "${RUNTIME_ROOT}"/{assets,staging,raw,lerobot,cache,logs,manifests}

RAW_PATH="${RUNTIME_ROOT}/raw/${DATASET}"
COLLECT_WORK="${RUNTIME_ROOT}/staging/${DATASET}.work"
OUTPUT_PATH="${RUNTIME_ROOT}/lerobot/${OUTPUT}"
CONVERT_WORK="${RUNTIME_ROOT}/staging/${OUTPUT}.convert.work"
LOG_FILE="${RUNTIME_ROOT}/logs/${DATASET}-pipeline.log"

[[ ! -e "${RAW_PATH}" ]] || { echo "Raw dataset already exists: ${RAW_PATH}" >&2; exit 1; }
[[ ! -e "${COLLECT_WORK}" ]] || { echo "Collection staging already exists: ${COLLECT_WORK}" >&2; exit 1; }
[[ ! -e "${OUTPUT_PATH}" ]] || { echo "LeRobot output already exists: ${OUTPUT_PATH}" >&2; exit 1; }
[[ ! -e "${CONVERT_WORK}" ]] || { echo "Conversion staging already exists: ${CONVERT_WORK}" >&2; exit 1; }

for script in "${COLLECT_SCRIPT}" "${WINDOW_SCRIPT}" "${CONVERT_SCRIPT}"; do
  [[ -x "${script}" ]] || { echo "Required script is not executable: ${script}" >&2; exit 1; }
done

export HKC_SIM_RUNTIME_ROOT="${RUNTIME_ROOT}"
exec > >(tee -a "${LOG_FILE}") 2>&1

PIPELINE_STAGE="preflight"

pipeline_failed() {
  local status="$?"
  trap - ERR
  echo
  echo "Pipeline failed during ${PIPELINE_STAGE} (exit ${status})."
  if [[ -d "${RAW_PATH}" && ! -d "${OUTPUT_PATH}" ]]; then
    echo "The completed raw HDF5 dataset has been preserved: ${RAW_PATH}"
    echo "After fixing the problem, convert it separately with:"
    echo "  ./scripts/convert_to_lerobot.sh --source ${DATASET} --output ${OUTPUT}"
  elif [[ -e "${COLLECT_WORK}" ]]; then
    echo "Collection staging was kept for diagnosis: ${COLLECT_WORK}"
  fi
  echo "Combined log: ${LOG_FILE}"
  exit "${status}"
}

pipeline_interrupted() {
  local signal="$1"
  trap - ERR INT TERM
  echo
  echo "Pipeline interrupted by ${signal} during ${PIPELINE_STAGE}."
  [[ -e "${COLLECT_WORK}" ]] && echo "Collection staging: ${COLLECT_WORK}"
  [[ -e "${CONVERT_WORK}" ]] && echo "Conversion staging: ${CONVERT_WORK}"
  [[ -d "${RAW_PATH}" ]] && echo "Completed raw dataset preserved: ${RAW_PATH}"
  echo "Combined log: ${LOG_FILE}"
  exit 130
}

trap pipeline_failed ERR
trap 'pipeline_interrupted INT' INT
trap 'pipeline_interrupted TERM' TERM

echo "=== HKC simulation collection and conversion ==="
echo "Dataset:     ${DATASET}"
echo "Output:      ${OUTPUT}"
echo "Task:        ${TASK}"
echo "Episodes:    ${EPISODES}"
echo "Embodiment:  ${EMBODIMENT}"
echo "GPU:         ${GPU}"
echo "Window:      ${SHOW_WINDOW}"
echo "Environment: ${LOADED_ENV_FILE:-not loaded}"
echo "Log:         ${LOG_FILE}"

COLLECT_ARGS=(
  --dataset "${DATASET}"
  --task "${TASK}"
  --episodes "${EPISODES}"
  --embodiment "${EMBODIMENT}"
  --gpu "${GPU}"
)

PIPELINE_STAGE="collection"
echo
echo "=== Stage 1/2: RoboTwin collection ==="
if [[ "${SHOW_WINDOW}" == "true" ]]; then
  "${WINDOW_SCRIPT}" "${COLLECT_ARGS[@]}"
else
  "${COLLECT_SCRIPT}" "${COLLECT_ARGS[@]}"
fi

[[ -f "${RAW_PATH}/manifest.json" ]] || {
  echo "Collection returned successfully but manifest is missing: ${RAW_PATH}/manifest.json" >&2
  false
}

PIPELINE_STAGE="conversion"
echo
echo "=== Stage 2/2: LeRobot v3 conversion and validation ==="
"${CONVERT_SCRIPT}" --source "${DATASET}" --output "${OUTPUT}"

[[ -f "${OUTPUT_PATH}/meta/info.json" ]] || {
  echo "Conversion returned successfully but info.json is missing: ${OUTPUT_PATH}/meta/info.json" >&2
  false
}

PIPELINE_STAGE="complete"
trap - ERR INT TERM

echo
echo "=== Pipeline completed ==="
echo "Raw HDF5:    ${RAW_PATH}"
echo "LeRobot v3:  ${OUTPUT_PATH}"
echo "Manifest:    ${RUNTIME_ROOT}/manifests/${OUTPUT}.json"
echo "Combined log: ${LOG_FILE}"
