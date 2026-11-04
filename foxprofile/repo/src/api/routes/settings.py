from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ...core import settings
from ..schemas.settings import SettingsResponse, SettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


def _current() -> SettingsResponse:
    return SettingsResponse(
        download_dir=str(settings.download_dir()),
        default_download_dir=str(settings.default_download_dir()),
        custom=settings.custom_download_dir() is not None,
    )


@router.get("", response_model=SettingsResponse)
def get_settings() -> SettingsResponse:
    return _current()


@router.put("", response_model=SettingsResponse)
def update_settings(body: SettingsUpdate) -> SettingsResponse:
    """Choose where browsers save downloaded files (empty = default). Applies at once, also to running profiles."""
    try:
        settings.set_download_dir(body.download_dir)
    except settings.SettingsError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return _current()
