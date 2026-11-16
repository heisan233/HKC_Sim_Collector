from pathlib import Path


def test_required_project_directories_exist() -> None:
    project_root = Path(__file__).resolve().parents[1]
    required = {
        "configs",
        "docker",
        "scripts",
        "src",
        "tests",
        "docs",
        "manifests",
    }

    assert required.issubset({path.name for path in project_root.iterdir() if path.is_dir()})


def test_runtime_data_is_ignored() -> None:
    project_root = Path(__file__).resolve().parents[1]
    gitignore = (project_root / ".gitignore").read_text(encoding="utf-8")

    assert "runtime/" in gitignore
    assert "*.hdf5" in gitignore
    assert "*.safetensors" in gitignore

