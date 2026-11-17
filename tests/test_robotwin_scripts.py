from pathlib import Path


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


def test_converter_rejects_overwrite_and_publishes_atomically() -> None:
    script = (PROJECT_ROOT / "scripts" / "convert_in_container.sh").read_text(encoding="utf-8")
    assert '[[ ! -e "${FINAL}" ]]' in script
    assert '[[ ! -e "${WORK}" ]]' in script
    assert 'mv "${DATASET_ROOT}" "${FINAL}"' in script


def test_validator_accepts_lerobot_task_index_storage() -> None:
    validator = (PROJECT_ROOT / "scripts" / "validate_lerobot_v3.py").read_text(encoding="utf-8")
    assert 'tasks.index.name == "task"' in validator
    assert "tasks = tasks.reset_index()" in validator
