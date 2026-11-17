#!/usr/bin/env bash
set -Eeuo pipefail

: "${HKC_DATASET_NAME:?missing HKC_DATASET_NAME}"
: "${HKC_TASK_NAME:?missing HKC_TASK_NAME}"
: "${HKC_EPISODE_COUNT:?missing HKC_EPISODE_COUNT}"
: "${HKC_EMBODIMENT:?missing HKC_EMBODIMENT}"

WORK="/runtime/staging/${HKC_DATASET_NAME}.work"
FINAL="/runtime/raw/${HKC_DATASET_NAME}"
CONFIG_NAME="hkc_${HKC_DATASET_NAME//[^A-Za-z0-9_]/_}"
CONFIG_PATH="/opt/robotwin/env_cfg/task_config/${CONFIG_NAME}.yml"
export CONFIG_PATH

[[ ! -e "${WORK}" ]] || { echo "Staging run already exists: ${WORK}" >&2; exit 1; }
[[ ! -e "${FINAL}" ]] || { echo "Dataset already exists: ${FINAL}" >&2; exit 1; }
[[ -d /opt/robotwin/assets/embodiments ]] || { echo "RoboTwin embodiments are missing; run download_assets.sh" >&2; exit 1; }
[[ -d /opt/robotwin/assets/objects ]] || { echo "RoboTwin objects are missing; run download_assets.sh" >&2; exit 1; }

mkdir -p "${WORK}/payload"
cleanup_config() { rm -f "${CONFIG_PATH}"; }
trap cleanup_config EXIT

python3.10 - <<'PY'
import os
from pathlib import Path
import yaml

source = Path("/opt/robotwin/env_cfg/task_config/demo_clean.yml")
target = Path(os.environ["CONFIG_PATH"])
config = yaml.safe_load(source.read_text(encoding="utf-8"))
config["episode_num"] = int(os.environ["HKC_EPISODE_COUNT"])
config["embodiment"] = [os.environ["HKC_EMBODIMENT"]]
config["save_path"] = f"/runtime/staging/{os.environ['HKC_DATASET_NAME']}.work/payload"
config["render_freq"] = int(os.environ.get("HKC_RENDER_FREQ", "0"))
config["use_seed"] = False
config["collect_data"] = True
config["eval_video_log"] = False
config["language_num"] = 10
target.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
PY

cd /opt/robotwin
timeout --signal=TERM "${HKC_COLLECT_TIMEOUT_SECONDS:-3600}" \
  python3.10 scripts/collect_data.py "${HKC_TASK_NAME}" "${CONFIG_NAME}" \
  2>&1 | tee "/runtime/logs/${HKC_DATASET_NAME}.log"

python3.10 - <<'PY'
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import h5py

work = Path(f"/runtime/staging/{os.environ['HKC_DATASET_NAME']}.work")
episodes = sorted(work.rglob("episode_*.hdf5"))
expected = int(os.environ["HKC_EPISODE_COUNT"])
if len(episodes) != expected:
    raise SystemExit(f"Expected {expected} HDF5 episodes, found {len(episodes)}")

for path in episodes:
    with h5py.File(path, "r") as handle:
        required = {"state", "action", "vision", "data_format_version"}
        missing = sorted(required.difference(handle.keys()))
        if missing:
            raise SystemExit(f"{path.name} is missing HDF5 keys: {missing}")
        if not list(handle["vision"].keys()):
            raise SystemExit(f"{path.name} contains no camera data")

manifest = {
    "dataset_name": os.environ["HKC_DATASET_NAME"],
    "task": os.environ["HKC_TASK_NAME"],
    "embodiment": os.environ["HKC_EMBODIMENT"],
    "episodes": expected,
    "format": "XPolicyLab HDF5",
    "robotwin_commit": "ea8b21121ebb3cd201ff5b3fe361944ac94eda3f",
    "xpolicylab_commit": "fa431ecd893ee706883e64fe5fe1464ec8cd928d",
    "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "files": [str(path.relative_to(work)) for path in episodes],
}
(work / "manifest.json").write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
print(json.dumps(manifest, ensure_ascii=False, indent=2))
PY

mv "${WORK}" "${FINAL}"
