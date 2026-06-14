from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml


DEFAULT_SETTINGS_PATH = Path("config/settings.yaml")


def get_project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _resolve_path(root: Path, value: str) -> str:
    path = Path(value)
    if path.is_absolute():
        return str(path)
    return str((root / path).resolve())


def load_settings(path: str | Path | None = None) -> dict[str, Any]:
    root = get_project_root()
    settings_path = Path(path) if path is not None else root / DEFAULT_SETTINGS_PATH
    with settings_path.open("r", encoding="utf-8") as f:
        settings = yaml.safe_load(f) or {}

    result = deepcopy(settings)
    paths = result.setdefault("paths", {})
    for key in ("db", "export_dir", "catalyst_pool"):
        if key in paths:
            paths[key] = _resolve_path(root, str(paths[key]))
    return result
