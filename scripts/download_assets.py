#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from huggingface_hub import hf_hub_download


REPO_ID = "TianxingChen/RoboTwin2.0"
REVISION = "3dc3b798668feb99ac61cc9086d84cbcc3d79186"
MINIMAL_FILES = ("embodiments.zip", "objects.zip")
FULL_FILES = ("background_texture.zip", *MINIMAL_FILES)


def safe_extract(archive: Path, destination: Path) -> None:
    root = destination.resolve()
    with zipfile.ZipFile(archive) as handle:
        for member in handle.infolist():
            target = (destination / member.filename).resolve()
            if not target.is_relative_to(root):
                raise ValueError(f"Unsafe archive path: {member.filename}")
        handle.extractall(destination)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", type=Path, default=Path("/runtime/assets"))
    parser.add_argument("--include-backgrounds", action="store_true")
    args = parser.parse_args()

    destination = args.destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    files = FULL_FILES if args.include_backgrounds else MINIMAL_FILES
    marker = destination / ".hkc-assets.json"

    completed: set[str] = set()
    if marker.is_file():
        state = json.loads(marker.read_text(encoding="utf-8"))
        if state.get("revision") != REVISION:
            raise SystemExit("Existing assets use a different upstream revision")
        completed = set(state.get("archives", []))

    free = shutil.disk_usage(destination).free
    if free < 20 * 1024**3:
        raise SystemExit("At least 20 GiB of free space is required for minimal assets")

    for filename in files:
        if filename in completed:
            print(f"[skip] {filename}")
            continue
        print(f"[download] {filename}", flush=True)
        downloaded = Path(
            hf_hub_download(
                repo_id=REPO_ID,
                filename=filename,
                repo_type="dataset",
                revision=REVISION,
                local_dir=destination,
                local_dir_use_symlinks=False,
                resume_download=True,
            )
        )
        print(f"[extract] {filename}", flush=True)
        safe_extract(downloaded, destination)
        downloaded.unlink()
        completed.add(filename)
        marker.write_text(
            json.dumps(
                {
                    "repo_id": REPO_ID,
                    "revision": REVISION,
                    "archives": sorted(completed),
                    "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    print("RoboTwin assets are ready")


if __name__ == "__main__":
    main()
