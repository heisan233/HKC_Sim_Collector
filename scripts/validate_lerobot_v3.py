#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from lerobot.datasets.lerobot_dataset import LeRobotDataset


def read_parquet_tree(root: Path) -> pd.DataFrame:
    paths = sorted(root.rglob("*.parquet"))
    if not paths:
        raise ValueError(f"No parquet files under {root}")
    return pd.concat((pd.read_parquet(path) for path in paths), ignore_index=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--expected-episodes", type=int, required=True)
    args = parser.parse_args()

    root = args.root.resolve()
    required = (
        root / "meta" / "info.json",
        root / "meta" / "tasks.parquet",
        root / "meta" / "episodes",
        root / "data",
        root / "videos",
    )
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise SystemExit(f"LeRobot v3 required paths are missing: {missing}")

    info = json.loads((root / "meta" / "info.json").read_text(encoding="utf-8"))
    if info.get("codebase_version") != "v3.0":
        raise SystemExit(f"Expected codebase_version=v3.0, got {info.get('codebase_version')!r}")

    tasks = pd.read_parquet(root / "meta" / "tasks.parquet")
    # LeRobot v3 persists `task` as the pandas index in tasks.parquet. Pandas
    # restores that index on read, while Arrow still reports it in the schema.
    if "task" not in tasks.columns and tasks.index.name == "task":
        tasks = tasks.reset_index()
    episodes = read_parquet_tree(root / "meta" / "episodes")
    frames = read_parquet_tree(root / "data")

    if len(episodes) != args.expected_episodes:
        raise SystemExit(f"Expected {args.expected_episodes} episodes, got {len(episodes)}")
    if int(info.get("total_episodes", -1)) != len(episodes):
        raise SystemExit("info.json total_episodes does not match episode metadata")
    if int(info.get("total_frames", -1)) != len(frames):
        raise SystemExit("info.json total_frames does not match frame parquet rows")

    for column in ("episode_index", "frame_index", "timestamp", "action", "observation.state"):
        if column not in frames.columns:
            raise SystemExit(f"Frame parquet is missing {column!r}")
    for column in ("episode_index", "length"):
        if column not in episodes.columns:
            raise SystemExit(f"Episode metadata is missing {column!r}")
    if not {"task_index", "task"}.issubset(tasks.columns):
        raise SystemExit("tasks.parquet is missing task_index/task")

    video_features = [
        key for key, value in info.get("features", {}).items() if value.get("dtype") == "video"
    ]
    video_files = sorted((root / "videos").rglob("*.mp4"))
    if len(video_files) < len(video_features):
        raise SystemExit(
            f"Expected at least {len(video_features)} video files, found {len(video_files)}"
        )

    dataset = LeRobotDataset(repo_id=f"local/{root.name}", root=root)
    if len(dataset) != len(frames):
        raise SystemExit(f"LeRobotDataset length {len(dataset)} != parquet rows {len(frames)}")
    sample = dataset[0]
    for key in ("observation.state", "action", "episode_index", "frame_index", "timestamp"):
        if key not in sample:
            raise SystemExit(f"Loaded sample is missing {key!r}")

    print(
        json.dumps(
            {
                "root": str(root),
                "codebase_version": info["codebase_version"],
                "episodes": len(episodes),
                "frames": len(frames),
                "tasks": len(tasks),
                "video_features": video_features,
                "video_files": len(video_files),
                "action_shape": list(sample["action"].shape),
                "state_shape": list(sample["observation.state"].shape),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
