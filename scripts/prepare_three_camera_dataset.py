#!/usr/bin/env python3
"""Create a three-camera LeRobot v3 derivative for VLA training.

The source dataset is never modified.  The new dataset keeps the high and two
wrist cameras, renames them to the model-facing image/image2/image3 slots, and
omits the optional third-person camera.
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pyarrow.parquet as pq


CAMERA_MAP = {
    "observation.images.cam_high": "observation.images.image",
    "observation.images.cam_left_wrist": "observation.images.image2",
    "observation.images.cam_right_wrist": "observation.images.image3",
}
DROPPED_CAMERAS = ("observation.images.cam_third_view",)


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read JSON {path}: {exc}") from exc


def write_json(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def replace_feature_keys(values: dict, *, label: str) -> dict:
    missing = [key for key in (*CAMERA_MAP, *DROPPED_CAMERAS) if key not in values]
    if missing:
        raise ValueError(f"{label} is missing required camera keys: {missing}")
    conflicts = [key for key in CAMERA_MAP.values() if key in values]
    if conflicts:
        raise ValueError(f"{label} already contains output camera keys: {conflicts}")

    converted = {}
    for key, value in values.items():
        if key in DROPPED_CAMERAS:
            continue
        converted[CAMERA_MAP.get(key, key)] = value
    return converted


def converted_column_name(name: str) -> str | None:
    for dropped in DROPPED_CAMERAS:
        for prefix in (f"videos/{dropped}/", f"stats/{dropped}/"):
            if name.startswith(prefix):
                return None
    for source, target in CAMERA_MAP.items():
        for group in ("videos", "stats"):
            prefix = f"{group}/{source}/"
            if name.startswith(prefix):
                return f"{group}/{target}/{name[len(prefix):]}"
    return name


def rewrite_episode_parquet(root: Path) -> None:
    paths = sorted((root / "meta" / "episodes").rglob("*.parquet"))
    if not paths:
        raise ValueError("No episode metadata Parquet files were found")

    for path in paths:
        table = pq.read_table(path)
        kept_indices: list[int] = []
        names: list[str] = []
        for index, name in enumerate(table.column_names):
            converted = converted_column_name(name)
            if converted is None:
                continue
            kept_indices.append(index)
            names.append(converted)
        if len(names) != len(set(names)):
            raise ValueError(f"Camera column conversion creates duplicates in {path}")
        converted_table = table.select(kept_indices).rename_columns(names)
        temporary = path.with_suffix(".parquet.tmp")
        pq.write_table(converted_table, temporary, compression="zstd")
        temporary.replace(path)


def rewrite_video_directories(root: Path) -> None:
    videos = root / "videos"
    for source, target in CAMERA_MAP.items():
        source_path = videos / source
        target_path = videos / target
        if not source_path.is_dir():
            raise ValueError(f"Missing source video directory: {source_path}")
        if target_path.exists():
            raise ValueError(f"Output video directory already exists: {target_path}")
        source_path.rename(target_path)
    for dropped in DROPPED_CAMERAS:
        dropped_path = videos / dropped
        if not dropped_path.is_dir():
            raise ValueError(f"Missing camera selected for removal: {dropped_path}")
        shutil.rmtree(dropped_path)


def record_conversion(root: Path, source: Path) -> None:
    record_path = root / "meta" / "hkc_conversion.json"
    record = load_json(record_path) if record_path.is_file() else {}
    record["camera_slot_conversion"] = {
        "source_dataset": source.name,
        "source_camera_count": 4,
        "output_camera_count": 3,
        "mapping": CAMERA_MAP,
        "dropped": list(DROPPED_CAMERAS),
        "converted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    write_json(record_path, record)


def validate_result(root: Path) -> None:
    info = load_json(root / "meta" / "info.json")
    video_features = {
        key
        for key, value in info.get("features", {}).items()
        if value.get("dtype") == "video"
    }
    expected = set(CAMERA_MAP.values())
    if video_features != expected:
        raise ValueError(
            f"Expected exactly three converted video features {sorted(expected)}, "
            f"got {sorted(video_features)}"
        )
    video_directories = {
        path.name for path in (root / "videos").iterdir() if path.is_dir()
    }
    if video_directories != expected:
        raise ValueError(
            f"Expected exactly three converted video directories {sorted(expected)}, "
            f"got {sorted(video_directories)}"
        )


def convert(source: Path, output: Path) -> None:
    source = source.resolve()
    output = output.resolve()
    if not source.is_dir():
        raise ValueError(f"Source dataset does not exist: {source}")
    if source == output:
        raise ValueError("Source and output datasets must be different")
    if output.exists():
        raise ValueError(f"Output dataset already exists: {output}")

    required = (
        source / "meta" / "info.json",
        source / "meta" / "stats.json",
        source / "meta" / "episodes",
        source / "data",
        source / "videos",
    )
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise ValueError(f"Source is not a complete LeRobot v3 dataset: {missing}")

    output.parent.mkdir(parents=True, exist_ok=True)
    work = output.with_name(f".{output.name}.three-camera.work")
    if work.exists():
        raise ValueError(f"Staging path already exists: {work}")

    try:
        shutil.copytree(
            source,
            work,
            ignore=shutil.ignore_patterns(".hkc-uploaded.json", "*.hkc-uploaded.json"),
        )
        info_path = work / "meta" / "info.json"
        info = load_json(info_path)
        info["features"] = replace_feature_keys(
            info.get("features", {}), label="meta/info.json features"
        )
        write_json(info_path, info)

        stats_path = work / "meta" / "stats.json"
        stats = replace_feature_keys(load_json(stats_path), label="meta/stats.json")
        write_json(stats_path, stats)

        rewrite_episode_parquet(work)
        rewrite_video_directories(work)
        record_conversion(work, source)
        validate_result(work)
        work.rename(output)
    except Exception:
        shutil.rmtree(work, ignore_errors=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert a four-camera LeRobot v3 dataset to image/image2/image3."
    )
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        convert(args.source, args.output)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    print(f"Three-camera dataset created: {args.output}")


if __name__ == "__main__":
    main()
