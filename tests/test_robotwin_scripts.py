import os
from pathlib import Path
import subprocess


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_robotwin_operational_scripts_exist() -> None:
    expected = {
        "build_robotwin.sh",
        "check_robotwin.sh",
        "download_assets.sh",
        "download_assets.py",
        "build_converter.sh",
        "collect.sh",
        "collect_in_container.sh",
        "collect_windows.sh",
        "collect_windows_in_container.sh",
        "collect_and_convert.sh",
        "convert_to_lerobot.sh",
        "convert_in_container.sh",
        "validate_lerobot_v3.py",
    }
    scripts = {path.name for path in (PROJECT_ROOT / "scripts").iterdir()}
    assert expected.issubset(scripts)


def test_collection_rejects_overwrite() -> None:
    script = (PROJECT_ROOT / "scripts" / "collect_in_container.sh").read_text(encoding="utf-8")
    assert '[[ ! -e "${WORK}" ]]' in script
    assert '[[ ! -e "${FINAL}" ]]' in script
    assert 'mv "${WORK}" "${FINAL}"' in script


def test_window_collection_is_explicit_and_keeps_normal_default() -> None:
    normal = (PROJECT_ROOT / "scripts" / "collect_in_container.sh").read_text(encoding="utf-8")
    window = (PROJECT_ROOT / "scripts" / "collect_windows.sh").read_text(encoding="utf-8")
    patcher = (PROJECT_ROOT / "scripts" / "collect_windows_in_container.sh").read_text(encoding="utf-8")
    assert 'os.environ.get("HKC_RENDER_FREQ", "0")' in normal
    assert "-e HKC_RENDER_FREQ=1" in window
    assert 'args["render_freq"] = 0' in patcher
    assert 'TASK_ENV.viewer.close()' in patcher


def test_collection_entrypoints_accept_any_positive_episode_count() -> None:
    for name in ("collect.sh", "collect_windows.sh", "collect_and_convert.sh"):
        script = (PROJECT_ROOT / "scripts" / name).read_text(encoding="utf-8")
        assert "episodes 1..3" not in script
        assert "^[1-9][0-9]*$" in script
        assert "Episodes must be a positive integer" in script


def test_vulkaninfo_failure_is_warning_before_required_sapien_check() -> None:
    script = (PROJECT_ROOT / "scripts" / "check_robotwin.sh").read_text(encoding="utf-8")
    assert "VULKAN_STATUS" in script
    assert "generic vulkaninfo check failed" in script
    assert "continuing with the required SAPIEN render check" in script
    assert 'print("SAPIEN renderer: OK")' in script


def test_robotwin_dockerfile_uses_locked_commits() -> None:
    dockerfile = (PROJECT_ROOT / "docker" / "Dockerfile").read_text(encoding="utf-8")
    lock = (PROJECT_ROOT / "docker" / "versions.lock.json").read_text(encoding="utf-8")
    for commit in (
        "ea8b21121ebb3cd201ff5b3fe361944ac94eda3f",
        "fa431ecd893ee706883e64fe5fe1464ec8cd928d",
        "d64c4b005459db10c5dd867d8b30a87d5bda9bdb",
        "75ebeeaea0908c5527e7b1e305fbc7681382db47",
    ):
        assert commit in dockerfile
        assert commit in lock


def test_converter_uses_locked_sources_and_preserves_third_view() -> None:
    dockerfile = (PROJECT_ROOT / "docker" / "Dockerfile.lerobot").read_text(encoding="utf-8")
    assert "dc0cee9c75e3cc684e4756013e214888176f2c15" in dockerfile
    assert "fa431ecd893ee706883e64fe5fe1464ec8cd928d" in dockerfile
    assert '"cam_third_view"' in dockerfile
    assert "uv sync --frozen" in dockerfile
    assert '"h5py==3.11.0"' in dockerfile
    assert "portable H.264 encoder" in dockerfile
    assert "offline non-streaming encoding" in dockerfile
    assert "non-streaming encoder guard" in dockerfile
    assert '"    streaming_encoding: bool = False\\n"' in dockerfile


def test_converter_rejects_overwrite_and_publishes_atomically() -> None:
    script = (PROJECT_ROOT / "scripts" / "convert_in_container.sh").read_text(encoding="utf-8")
    assert '[[ ! -e "${FINAL}" ]]' in script
    assert '[[ ! -e "${WORK}" ]]' in script
    assert 'mv "${DATASET_ROOT}" "${FINAL}"' in script


def test_validator_accepts_lerobot_task_index_storage() -> None:
    validator = (PROJECT_ROOT / "scripts" / "validate_lerobot_v3.py").read_text(encoding="utf-8")
    assert 'tasks.index.name == "task"' in validator
    assert "tasks = tasks.reset_index()" in validator


def test_validator_requires_every_video_feature_to_match_parquet_frames() -> None:
    validator = (PROJECT_ROOT / "scripts" / "validate_lerobot_v3.py").read_text(encoding="utf-8")
    assert "def read_video_frame_count" in validator
    assert "video_frame_counts" in validator
    assert "encoded frames" in validator
    assert "frame parquet rows" in validator


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def test_pipeline_runs_collection_before_conversion(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    calls = tmp_path / "calls.txt"
    collector = tmp_path / "collect.sh"
    window = tmp_path / "window.sh"
    converter = tmp_path / "convert.sh"

    _write_executable(
        collector,
        """#!/usr/bin/env bash
set -eu
dataset=""
while [ "$#" -gt 0 ]; do
  case "$1" in --dataset) dataset="$2"; shift 2;; *) shift;; esac
done
echo collect >> "$HKC_TEST_CALLS"
mkdir -p "$HKC_SIM_RUNTIME_ROOT/raw/$dataset"
printf '{}\n' > "$HKC_SIM_RUNTIME_ROOT/raw/$dataset/manifest.json"
""",
    )
    _write_executable(window, "#!/usr/bin/env bash\nexit 99\n")
    _write_executable(
        converter,
        """#!/usr/bin/env bash
set -eu
output=""
while [ "$#" -gt 0 ]; do
  case "$1" in --output) output="$2"; shift 2;; *) shift;; esac
done
echo convert >> "$HKC_TEST_CALLS"
mkdir -p "$HKC_SIM_RUNTIME_ROOT/lerobot/$output/meta"
printf '{}\n' > "$HKC_SIM_RUNTIME_ROOT/lerobot/$output/meta/info.json"
""",
    )

    env = os.environ | {
        "HKC_SIM_RUNTIME_ROOT": str(runtime),
        "HKC_PIPELINE_COLLECT_SCRIPT": str(collector),
        "HKC_PIPELINE_WINDOW_SCRIPT": str(window),
        "HKC_PIPELINE_CONVERT_SCRIPT": str(converter),
        "HKC_TEST_CALLS": str(calls),
    }
    result = subprocess.run(
        [
            str(PROJECT_ROOT / "scripts" / "collect_and_convert.sh"),
            "--dataset",
            "pipeline-test",
        ],
        cwd=PROJECT_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert calls.read_text(encoding="utf-8").splitlines() == ["collect", "convert"]
    assert (runtime / "raw/pipeline-test/manifest.json").is_file()
    assert (runtime / "lerobot/pipeline-test-lerobot-v3/meta/info.json").is_file()
    assert (runtime / "logs/pipeline-test-pipeline.log").is_file()


def test_pipeline_forwards_episode_count_above_three(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    captured = tmp_path / "episodes.txt"
    collector = tmp_path / "collect.sh"
    window = tmp_path / "window.sh"
    converter = tmp_path / "convert.sh"

    _write_executable(
        collector,
        """#!/usr/bin/env bash
set -eu
dataset=""
episodes=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --dataset) dataset="$2"; shift 2;;
    --episodes) episodes="$2"; shift 2;;
    *) shift;;
  esac
done
printf '%s\n' "$episodes" > "$HKC_TEST_EPISODES"
mkdir -p "$HKC_SIM_RUNTIME_ROOT/raw/$dataset"
printf '{}\n' > "$HKC_SIM_RUNTIME_ROOT/raw/$dataset/manifest.json"
""",
    )
    _write_executable(window, "#!/usr/bin/env bash\nexit 99\n")
    _write_executable(
        converter,
        """#!/usr/bin/env bash
set -eu
output=""
while [ "$#" -gt 0 ]; do
  case "$1" in --output) output="$2"; shift 2;; *) shift;; esac
done
mkdir -p "$HKC_SIM_RUNTIME_ROOT/lerobot/$output/meta"
printf '{}\n' > "$HKC_SIM_RUNTIME_ROOT/lerobot/$output/meta/info.json"
""",
    )

    env = os.environ | {
        "HKC_SIM_RUNTIME_ROOT": str(runtime),
        "HKC_PIPELINE_COLLECT_SCRIPT": str(collector),
        "HKC_PIPELINE_WINDOW_SCRIPT": str(window),
        "HKC_PIPELINE_CONVERT_SCRIPT": str(converter),
        "HKC_TEST_EPISODES": str(captured),
    }
    result = subprocess.run(
        [
            str(PROJECT_ROOT / "scripts" / "collect_and_convert.sh"),
            "--dataset",
            "five-episodes",
            "--episodes",
            "5",
        ],
        cwd=PROJECT_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert captured.read_text(encoding="utf-8").strip() == "5"


def test_pipeline_loads_env_file_without_overriding_explicit_environment(
    tmp_path: Path,
) -> None:
    runtime_from_file = tmp_path / "runtime-from-file"
    runtime_override = tmp_path / "runtime-override"
    calls = tmp_path / "calls.txt"
    collector = tmp_path / "collect.sh"
    window = tmp_path / "window.sh"
    converter = tmp_path / "convert.sh"
    env_file = tmp_path / "collector.env"

    _write_executable(
        collector,
        """#!/usr/bin/env bash
set -eu
dataset=""
while [ "$#" -gt 0 ]; do
  case "$1" in --dataset) dataset="$2"; shift 2;; *) shift;; esac
done
echo collect >> "$HKC_TEST_CALLS"
mkdir -p "$HKC_SIM_RUNTIME_ROOT/raw/$dataset"
printf '{}\n' > "$HKC_SIM_RUNTIME_ROOT/raw/$dataset/manifest.json"
""",
    )
    _write_executable(window, "#!/usr/bin/env bash\nexit 99\n")
    _write_executable(
        converter,
        """#!/usr/bin/env bash
set -eu
output=""
while [ "$#" -gt 0 ]; do
  case "$1" in --output) output="$2"; shift 2;; *) shift;; esac
done
echo convert >> "$HKC_TEST_CALLS"
mkdir -p "$HKC_SIM_RUNTIME_ROOT/lerobot/$output/meta"
printf '{}\n' > "$HKC_SIM_RUNTIME_ROOT/lerobot/$output/meta/info.json"
""",
    )
    env_file.write_text(
        "\n".join(
            (
                f"HKC_SIM_RUNTIME_ROOT={runtime_from_file}",
                f"HKC_PIPELINE_COLLECT_SCRIPT={collector}",
                f"HKC_PIPELINE_WINDOW_SCRIPT={window}",
                f"HKC_PIPELINE_CONVERT_SCRIPT={converter}",
                f"HKC_TEST_CALLS={calls}",
            )
        )
        + "\n",
        encoding="utf-8",
    )

    env = os.environ | {
        "HKC_SIM_ENV_FILE": str(env_file),
        "HKC_SIM_RUNTIME_ROOT": str(runtime_override),
    }
    result = subprocess.run(
        [
            str(PROJECT_ROOT / "scripts" / "collect_and_convert.sh"),
            "--dataset",
            "env-file-test",
        ],
        cwd=PROJECT_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert calls.read_text(encoding="utf-8").splitlines() == ["collect", "convert"]
    assert (runtime_override / "raw/env-file-test/manifest.json").is_file()
    assert (runtime_override / "lerobot/env-file-test-lerobot-v3/meta/info.json").is_file()
    assert not runtime_from_file.exists()
    assert f"Environment: {env_file}" in result.stdout


def test_pipeline_preserves_raw_dataset_when_conversion_fails(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    collector = tmp_path / "collect.sh"
    window = tmp_path / "window.sh"
    converter = tmp_path / "convert.sh"

    _write_executable(
        collector,
        """#!/usr/bin/env bash
set -eu
dataset=""
while [ "$#" -gt 0 ]; do
  case "$1" in --dataset) dataset="$2"; shift 2;; *) shift;; esac
done
mkdir -p "$HKC_SIM_RUNTIME_ROOT/raw/$dataset"
printf '{}\n' > "$HKC_SIM_RUNTIME_ROOT/raw/$dataset/manifest.json"
""",
    )
    _write_executable(window, "#!/usr/bin/env bash\nexit 99\n")
    _write_executable(converter, "#!/usr/bin/env bash\nexit 42\n")

    env = os.environ | {
        "HKC_SIM_RUNTIME_ROOT": str(runtime),
        "HKC_PIPELINE_COLLECT_SCRIPT": str(collector),
        "HKC_PIPELINE_WINDOW_SCRIPT": str(window),
        "HKC_PIPELINE_CONVERT_SCRIPT": str(converter),
    }
    result = subprocess.run(
        [
            str(PROJECT_ROOT / "scripts" / "collect_and_convert.sh"),
            "--dataset",
            "conversion-fails",
        ],
        cwd=PROJECT_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 42
    assert (runtime / "raw/conversion-fails/manifest.json").is_file()
    assert not (runtime / "lerobot/conversion-fails-lerobot-v3").exists()
    assert "completed raw HDF5 dataset has been preserved" in result.stdout


def test_pipeline_rejects_existing_raw_dataset_before_collection(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    (runtime / "raw/already-there").mkdir(parents=True)
    no_op = tmp_path / "no-op.sh"
    _write_executable(no_op, "#!/usr/bin/env bash\nexit 88\n")

    env = os.environ | {
        "HKC_SIM_RUNTIME_ROOT": str(runtime),
        "HKC_PIPELINE_COLLECT_SCRIPT": str(no_op),
        "HKC_PIPELINE_WINDOW_SCRIPT": str(no_op),
        "HKC_PIPELINE_CONVERT_SCRIPT": str(no_op),
    }
    result = subprocess.run(
        [
            str(PROJECT_ROOT / "scripts" / "collect_and_convert.sh"),
            "--dataset",
            "already-there",
        ],
        cwd=PROJECT_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Raw dataset already exists" in result.stderr
