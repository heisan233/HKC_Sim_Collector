import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = PROJECT_ROOT / "docker" / "versions.lock.json"


def load_lock() -> dict:
    return json.loads(LOCK_PATH.read_text(encoding="utf-8"))


def test_required_components_are_pinned() -> None:
    lock = load_lock()
    simulator = lock["simulator"]
    converter = lock["converter"]

    assert len(simulator["robotwin"]["commit"]) == 40
    assert len(simulator["xpolicylab"]["commit"]) == 40
    assert len(simulator["curobo"]["commit"]) == 40
    assert len(simulator["pytorch3d"]["commit"]) == 40
    assert len(converter["lerobot"]["commit"]) == 40
    assert converter["lerobot"]["package_version"] == "0.6.2"


def test_base_images_use_immutable_digests() -> None:
    lock = load_lock()

    assert "@sha256:" in lock["simulator"]["base_image"]
    assert "@sha256:" in lock["converter"]["base_image"]


def test_no_floating_source_references() -> None:
    lock_text = LOCK_PATH.read_text(encoding="utf-8").lower()

    assert '"tag": "main"' not in lock_text
    assert '"tag": "latest"' not in lock_text
    assert ':latest' not in lock_text


def test_split_environments_are_explicit() -> None:
    lock = load_lock()

    assert lock["design"] == "split_simulator_and_converter_images"
    assert lock["simulator"]["python"] == "3.10"
    assert lock["converter"]["python"] == "3.12"


def test_local_end_to_end_validation_is_recorded() -> None:
    lock = load_lock()

    assert lock["status"] == "local_end_to_end_validated"
    assert lock["converter"]["h5py"] == "3.11.0"
    assert lock["converter"]["video_encoder"]["codec"] == "h264"
    assert lock["local_validation"]["output_format"] == "LeRobot v3.0"
    assert lock["local_validation"]["video_features"] == 4
