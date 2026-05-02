"""Path helpers for GUI resources."""

from pathlib import Path


GUI_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = GUI_DIR.parent
ASSETS_DIR = PROJECT_ROOT / "assets"


def project_path(*parts: str) -> Path:
    return PROJECT_ROOT.joinpath(*parts)


def asset_path(*parts: str) -> Path:
    return ASSETS_DIR.joinpath(*parts)


def resolve_project_relative(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return PROJECT_ROOT / candidate
