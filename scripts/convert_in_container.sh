#!/usr/bin/env bash
set -Eeuo pipefail

: "${HKC_SOURCE_DATASET:?missing HKC_SOURCE_DATASET}"
: "${HKC_OUTPUT_DATASET:?missing HKC_OUTPUT_DATASET}"

SOURCE="/runtime/raw/${HKC_SOURCE_DATASET}"
FINAL="/runtime/lerobot/${HKC_OUTPUT_DATASET}"
WORK="/runtime/staging/${HKC_OUTPUT_DATASET}.convert.work"
PAYLOAD="${SOURCE}/payload"

[[ -d "${SOURCE}" ]] || { echo "Source dataset does not exist: ${SOURCE}" >&2; exit 1; }
[[ -f "${SOURCE}/manifest.json" ]] || { echo "Source manifest is missing: ${SOURCE}/manifest.json" >&2; exit 1; }
[[ -d "${PAYLOAD}" ]] || { echo "Source payload is missing: ${PAYLOAD}" >&2; exit 1; }
[[ ! -e "${FINAL}" ]] || { echo "Output dataset already exists: ${FINAL}" >&2; exit 1; }
[[ ! -e "${WORK}" ]] || { echo "Conversion staging already exists: ${WORK}" >&2; exit 1; }

mkdir -p "${WORK}/hf/local" /runtime/manifests

mapfile -t DATA_DIRS < <(find "${PAYLOAD}" -mindepth 4 -maxdepth 4 -type d -name data -print | sort)
if [[ "${#DATA_DIRS[@]}" -ne 1 ]]; then
  echo "Expected exactly one task/embodiment data directory, found ${#DATA_DIRS[@]}" >&2
  printf '  %s\n' "${DATA_DIRS[@]:-}"
  exit 1
fi

DATA_DIR="${DATA_DIRS[0]}"
ENV_DIR="$(dirname "${DATA_DIR}")"
TASK_DIR="$(dirname "${ENV_DIR}")"
BENCH_DIR="$(dirname "${TASK_DIR}")"
ENV_CFG_TYPE="$(basename "${ENV_DIR}")"
TASK_NAME="$(basename "${TASK_DIR}")"
BENCH_NAME="$(basename "${BENCH_DIR}")"
PATTERN="${BENCH_NAME}.${TASK_NAME}.${ENV_CFG_TYPE}"

EXPECTED_EPISODES="$(python - "${SOURCE}/manifest.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    print(int(json.load(handle)["episodes"]))
PY
)"

ln -s "${PAYLOAD}" /opt/robotwin/data
export HF_LEROBOT_HOME="${WORK}/hf"

python /opt/robotwin/XPolicyLab/scripts/transform_lerobot_v30_format.py \
  "${PATTERN}" \
  --repo_id "local/${HKC_OUTPUT_DATASET}" \
  --data_type RoboDojo \
  --data_version v1.0 \
  --max_episode "${EXPECTED_EPISODES}"

DATASET_ROOT="${WORK}/hf/local/${HKC_OUTPUT_DATASET}"
EXPECTED_ROBOT_TYPE="$(python /workspace/scripts/apply_lerobot_metadata.py \
  --source-manifest "${SOURCE}/manifest.json" \
  --info "${DATASET_ROOT}/meta/info.json" \
  --payload-embodiment "${ENV_CFG_TYPE}")"
python /workspace/scripts/validate_lerobot_v3.py \
  --root "${DATASET_ROOT}" \
  --expected-episodes "${EXPECTED_EPISODES}" \
  --expected-robot-type "${EXPECTED_ROBOT_TYPE}"

python - "${SOURCE}/manifest.json" "${DATASET_ROOT}/meta/hkc_conversion.json" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

source = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
record = {
    "source": source,
    "output_format": "LeRobot v3.0",
    "robot_type": source["embodiment"],
    "lerobot_commit": "dc0cee9c75e3cc684e4756013e214888176f2c15",
    "xpolicylab_commit": "fa431ecd893ee706883e64fe5fe1464ec8cd928d",
    "converted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
}
Path(sys.argv[2]).write_text(
    json.dumps(record, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
PY

cp "${DATASET_ROOT}/meta/hkc_conversion.json" "/runtime/manifests/${HKC_OUTPUT_DATASET}.json"
mv "${DATASET_ROOT}" "${FINAL}"
rmdir "${WORK}/hf/local" "${WORK}/hf" "${WORK}"
