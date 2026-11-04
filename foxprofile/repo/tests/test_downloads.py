import asyncio
import json

import pytest

from src.core import settings
from src.services.browser import downloads


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "SETTINGS_FILE", str(tmp_path / "settings.json"))
    monkeypatch.setattr(settings, "DOWNLOAD_DIR", "")
    return tmp_path


def test_default_folder_until_one_is_chosen(cfg):
    assert settings.custom_download_dir() is None
    assert settings.download_dir() == settings.default_download_dir()


def test_env_default_is_used(cfg, monkeypatch):
    monkeypatch.setattr(settings, "DOWNLOAD_DIR", str(cfg / "env"))
    assert settings.download_dir() == cfg / "env"


def test_chosen_folder_wins_and_is_created(cfg):
    target = cfg / "videos" / "muse"
    assert settings.set_download_dir(str(target)) == target
    assert target.is_dir()
    assert settings.download_dir() == target
    assert json.loads((cfg / "settings.json").read_text())["download_dir"] == str(target)


def test_empty_value_restores_default(cfg):
    settings.set_download_dir(str(cfg / "x"))
    settings.set_download_dir("  ")
    assert settings.custom_download_dir() is None


def test_relative_and_unwritable_paths_are_rejected(cfg):
    with pytest.raises(settings.SettingsError):
        settings.set_download_dir("downloads")
    blocker = cfg / "file.txt"
    blocker.write_text("x")
    with pytest.raises(settings.SettingsError):
        settings.set_download_dir(str(blocker / "sub"))
    assert settings.custom_download_dir() is None


def test_unique_path_numbers_existing_files(tmp_path):
    (tmp_path / "a.mp4").write_bytes(b"1")
    assert downloads.unique_path(tmp_path, "a.mp4").name == "a (1).mp4"
    (tmp_path / "a (1).mp4").write_bytes(b"1")
    assert downloads.unique_path(tmp_path, "a.mp4").name == "a (2).mp4"


def test_safe_name_strips_path_and_bad_characters():
    assert downloads.safe_name("../../etc/pa:ss?.mp4") == "pa_ss_.mp4"
    assert downloads.safe_name("") == "download"


class _Download:
    suggested_filename = "clip.mp4"

    async def save_as(self, path):
        with open(path, "wb") as f:
            f.write(b"video")


def test_save_writes_into_the_chosen_folder(cfg):
    settings.set_download_dir(str(cfg / "out"))
    dest = asyncio.run(downloads.save(_Download()))
    assert dest == cfg / "out" / "clip.mp4"
    assert dest.read_bytes() == b"video"


def test_save_failure_is_reported_not_raised(cfg):
    class Broken(_Download):
        async def save_as(self, path):
            raise OSError("disk full")

    settings.set_download_dir(str(cfg / "out"))
    assert asyncio.run(downloads.save(Broken())) is None


def test_settings_route_round_trip(cfg):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from src.api.routes.settings import router

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    assert client.get("/settings").json()["custom"] is False
    target = str(cfg / "web")
    res = client.put("/settings", json={"download_dir": target})
    assert res.status_code == 200
    assert res.json()["download_dir"] == target
    assert res.json()["custom"] is True
    assert client.put("/settings", json={"download_dir": "relative"}).status_code == 400
    assert client.put("/settings", json={"download_dir": ""}).json()["custom"] is False
