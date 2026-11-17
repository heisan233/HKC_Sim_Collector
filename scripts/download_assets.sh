#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_ROOT}"

RUNTIME_ROOT="${HKC_SIM_RUNTIME_ROOT:-./runtime}"
mkdir -p "${RUNTIME_ROOT}"/{assets,staging,raw,lerobot,cache,logs,manifests}

ARGS=(--destination /runtime/assets)
if [[ "${1:-}" == "--include-backgrounds" ]]; then
  ARGS+=(--include-backgrounds)
elif [[ $# -gt 0 ]]; then
  echo "Usage: $0 [--include-backgrounds]" >&2
  exit 2
fi

docker compose run --rm robotwin python3.10 /workspace/scripts/download_assets.py "${ARGS[@]}"
docker compose run --rm robotwin bash -lc 'cd /opt/robotwin && python3.10 scripts/update_embodiment_config_path.py'
