#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_ROOT}"

mkdir -p "${HKC_SIM_RUNTIME_ROOT:-./runtime}"/{assets,staging,raw,lerobot,cache,logs,manifests}

echo "Building the pinned RoboTwin collection image..."
docker compose --progress=plain build robotwin
