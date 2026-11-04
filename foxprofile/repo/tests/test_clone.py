import json

import pytest


@pytest.fixture()
def pm(tmp_path, monkeypatch):
    """A ProfileManager whose DATA_DIR and PROFILES_FILE live in tmp_path."""
    data_dir = str(tmp_path / "camoufox_data")
    profiles_file = str(tmp_path / "profiles.json")
    import src.services.profile.manager as mgr_mod

    monkeypatch.setattr(mgr_mod, "DATA_DIR", data_dir)
    monkeypatch.setattr(mgr_mod, "PROFILES_FILE", profiles_file)
    return mgr_mod.ProfileManager()


def _source(pm, tmp_path):
    pm.add_profile("src", "user:pass@192.0.2.10:8080", "macos", "Asia/Ho_Chi_Minh", "vi-VN")
    d = tmp_path / "camoufox_data" / "src"
    (d / "fingerprint.json").write_text("{}")
    (d / "cookies.sqlite").write_text("cookies")
    (d / "parent.lock").write_text("")
    (d / "cache2").mkdir()
    (d / "cache2" / "entry").write_text("x")
    return d


def test_clone_copies_settings_and_data(pm, tmp_path):
    _source(pm, tmp_path)
    ok, name = pm.clone_profile("src", "dst", include_data=True, new_fingerprint=False)
    assert ok and name == "dst"
    p = pm.profiles["dst"]
    assert (p.proxy, p.os_type, p.timezone, p.locale) == (
        "user:pass@192.0.2.10:8080",
        "macos",
        "Asia/Ho_Chi_Minh",
        "vi-VN",
    )
    d = tmp_path / "camoufox_data" / "dst"
    assert (d / "cookies.sqlite").read_text() == "cookies"
    assert (d / "fingerprint.json").exists()
    assert not (d / "parent.lock").exists() and not (d / "cache2").exists()
    assert "dst" in json.loads((tmp_path / "profiles.json").read_text())


def test_clone_new_fingerprint_and_no_data(pm, tmp_path):
    _source(pm, tmp_path)
    assert pm.clone_profile("src", "fresh", include_data=False)[0]
    assert pm.clone_profile("src", "newfp", include_data=True, new_fingerprint=True)[0]
    assert list((tmp_path / "camoufox_data" / "fresh").iterdir()) == []
    newfp = tmp_path / "camoufox_data" / "newfp"
    assert (newfp / "cookies.sqlite").exists() and not (newfp / "fingerprint.json").exists()


@pytest.mark.parametrize(("source", "target"), [("missing", "x"), ("src", "SRC"), ("src", "..")])
def test_clone_refused(pm, tmp_path, source, target):
    _source(pm, tmp_path)
    ok, _ = pm.clone_profile(source, target)
    assert not ok
    assert set(pm.profiles) == {"src"}
    assert not any(p.name.endswith(".clone-tmp") for p in (tmp_path / "camoufox_data").iterdir())


def test_clone_route(pm, tmp_path):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from src.api.dependencies import get_browser_launcher, get_event_bus, get_profile_manager
    from src.api.routes.profiles import router
    from src.core.events import EventBus

    class _Launcher:
        def is_running(self, _name):
            return False

    _source(pm, tmp_path)
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_profile_manager] = lambda: pm
    app.dependency_overrides[get_browser_launcher] = lambda: _Launcher()
    app.dependency_overrides[get_event_bus] = EventBus
    client = TestClient(app)

    r = client.post("/profiles/src/clone", json={"name": "api-copy"})
    assert r.status_code == 201 and r.json()["os_type"] == "macos"
    assert client.post("/profiles/src/clone", json={"name": "api-copy"}).status_code == 409
    assert client.post("/profiles/nope/clone", json={"name": "z"}).status_code == 404
    assert client.post("/profiles/src/clone", json={"name": "a/b"}).status_code == 400
