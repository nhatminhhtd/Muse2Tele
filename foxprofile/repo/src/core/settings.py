"""Settings the user changes at run time from the web panel, kept in settings.json.

Browsers run as separate processes and the folder is read each time a file is
saved, so a change applies to profiles that are already running.
"""

from __future__ import annotations

import json
import os
import pathlib
import tempfile

from .config import DOWNLOAD_DIR, SETTINGS_FILE
from .logging import get_logger

logger = get_logger("settings")

MAX_PATH_LENGTH = 400


class SettingsError(ValueError):
    """The requested value cannot be used."""


def default_download_dir() -> pathlib.Path:
    if DOWNLOAD_DIR.strip():
        return pathlib.Path(DOWNLOAD_DIR.strip()).expanduser()
    return pathlib.Path.home() / "Downloads" / "FoxProfile"


def _load() -> dict:
    path = pathlib.Path(SETTINGS_FILE)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        logger.warning("Ignoring unreadable %s: %s", path, e)
        return {}
    return data if isinstance(data, dict) else {}


def _save(data: dict) -> None:
    path = pathlib.Path(SETTINGS_FILE)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def custom_download_dir() -> str | None:
    value = _load().get("download_dir")
    return value.strip() if isinstance(value, str) and value.strip() else None


def download_dir() -> pathlib.Path:
    """The folder downloads are saved to right now."""
    custom = custom_download_dir()
    return pathlib.Path(custom).expanduser() if custom else default_download_dir()


def set_download_dir(value: str | None) -> pathlib.Path:
    """Choose the download folder; an empty value restores the default.

    The folder is created and checked for write access, so a typo is reported
    here instead of surfacing later as downloads that silently go missing.
    """
    value = (value or "").strip()
    data = _load()
    if not value:
        data.pop("download_dir", None)
        _save(data)
        return download_dir()
    if len(value) > MAX_PATH_LENGTH or "\x00" in value:
        raise SettingsError("Invalid folder path")
    path = pathlib.Path(value).expanduser()
    if not path.is_absolute():
        raise SettingsError(
            "Enter a full folder path, e.g. C:/Users/me/Downloads or /home/me/Downloads"
        )
    try:
        path.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryFile(dir=path):
            pass
    except OSError as e:
        raise SettingsError(f"Cannot write to this folder: {e.strerror or e}") from e
    data["download_dir"] = str(path)
    _save(data)
    return path
