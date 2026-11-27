#!/usr/bin/env python3
"""Apply validated RoboTwin source metadata to a staged LeRobot v3 dataset."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def read_object(path: Path, label: str) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Cannot read {label} {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit(f"{label} must contain a JSON object: {path}")
    return value


def normalized_embodiment(value: str) -> str:
    return value.strip().casefold().replace("-", "_")


def manifest_robot_type(manifest: dict) -> str:
    value = manifest.get("embodiment")
    if not isinstance(value, str) or not value.strip():
        raise SystemExit("Source manifest is missing a non-empty embodiment")
    robot_type = value.strip()
    if len(robot_type) > 100:
        raise SystemExit("Source manifest embodiment exceeds 100 characters")
    if any(ord(character) < 32 for character in robot_type):
        raise SystemExit("Source manifest embodiment contains control characters")
    return robot_type


def apply_metadata(
    source_manifest: Path,
    info_path: Path,
    payload_embodiment: str,
) -> str:
    manifest = read_object(source_manifest, "source manifest")
    info = read_object(info_path, "LeRobot info.json")
    robot_type = manifest_robot_type(manifest)

    if normalized_embodiment(robot_type) != normalized_embodiment(payload_embodiment):
        raise SystemExit(
            "Source manifest embodiment does not match the payload directory: "
            f"{robot_type!r} != {payload_embodiment!r}"
        )

    info["robot_type"] = robot_type
    temporary = info_path.with_name(f"{info_path.name}.tmp")
    temporary.write_text(
        json.dumps(info, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(info_path)
    return robot_type


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--info", type=Path, required=True)
    parser.add_argument("--payload-embodiment", required=True)
    args = parser.parse_args()

    robot_type = apply_metadata(
        args.source_manifest,
        args.info,
        args.payload_embodiment,
    )
    print(robot_type)


if __name__ == "__main__":
    main()
