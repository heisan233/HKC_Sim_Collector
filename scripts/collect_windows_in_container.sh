#!/usr/bin/env bash
set -Eeuo pipefail

# RoboTwin 2.0 deliberately disables its Viewer before the final replay that
# writes HDF5. This container is disposable, so patch only this container's
# pinned upstream copy and keep the normal image and collect.sh unchanged.
python3.10 - <<'PY'
from pathlib import Path

path = Path("/opt/robotwin/scripts/collect_data.py")
text = path.read_text(encoding="utf-8")

disable_viewer = '        args["render_freq"] = 0\n'
keep_viewer = '        args["render_freq"] = int(args.get("render_freq", 1))\n'
if text.count(disable_viewer) != 1:
    raise SystemExit("Pinned RoboTwin viewer patch location was not found exactly once")
text = text.replace(disable_viewer, keep_viewer, 1)

close_env = (
    '            TASK_ENV.close_env(clear_cache=((episode_idx + 1) % clear_cache_freq == 0))\n'
    '            TASK_ENV.merge_pkl_to_hdf5_video(\n'
)
close_viewer = (
    '            TASK_ENV.close_env(clear_cache=((episode_idx + 1) % clear_cache_freq == 0))\n'
    '            if args["render_freq"]:\n'
    '                TASK_ENV.viewer.close()\n'
    '            TASK_ENV.merge_pkl_to_hdf5_video(\n'
)
if text.count(close_env) != 1:
    raise SystemExit("Pinned RoboTwin viewer cleanup patch location was not found exactly once")
path.write_text(text.replace(close_env, close_viewer, 1), encoding="utf-8")
PY

export HKC_RENDER_FREQ="${HKC_RENDER_FREQ:-1}"
exec bash /workspace/scripts/collect_in_container.sh
