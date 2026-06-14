from pathlib import Path

from src.config import get_project_root, load_settings


def test_get_project_root_points_at_repo_root():
    root = get_project_root()
    assert root.name == "wstatus"
    assert (root / "docs" / "superpowers").exists()


def test_load_settings_reads_thresholds_and_resolves_paths():
    settings = load_settings()
    assert settings["params"]["mode_a"]["prior_high_window"] == 60
    assert settings["params"]["mode_b"]["crash_window_days"] == 5
    assert Path(settings["paths"]["db"]).is_absolute()
    assert Path(settings["paths"]["export_dir"]).is_absolute()
