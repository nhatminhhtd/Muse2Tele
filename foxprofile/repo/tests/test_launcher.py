import os
import threading

import pytest

from src.models.profile import Profile
from src.services.browser import launcher as launcher_mod
from src.services.browser.launcher import BrowserLauncher, ProfileBusyError
from src.ui.actions.browser import launch_or_stop
from src.ui.state import AppState


class FakeProc:
    def poll(self):
        return None


@pytest.fixture
def bl(monkeypatch):
    spawned = []

    def spawn(profile):
        spawned.append(profile.name)
        return FakeProc()

    monkeypatch.setattr(launcher_mod, "spawn_browser", spawn)
    monkeypatch.setattr(launcher_mod, "wait_for_exit", lambda *a: None)
    monkeypatch.setattr(launcher_mod.orphans, "kill_orphans", lambda *a, **k: 0)
    b = BrowserLauncher()
    monkeypatch.setattr(b, "_monitor_process", lambda *a: None)
    b.spawned = spawned
    yield b
    # Fake processes must not reach terminate() at interpreter exit.
    b._active_sessions.clear()


def test_second_launch_returns_false_without_callbacks(bl):
    calls = []
    assert bl.start_thread(Profile(name="p"), lambda m: None) is True
    started = bl.start_thread(
        Profile(name="p"),
        lambda m: None,
        on_start=lambda: calls.append("start"),
        on_stop=lambda: calls.append("stop"),
    )
    assert started is False
    assert calls == []
    assert bl.spawned == ["p"]


def test_concurrent_launches_spawn_one_browser(bl, monkeypatch):
    entered, release = threading.Event(), threading.Event()

    def slow_spawn(profile):
        entered.set()
        release.wait(5)
        bl.spawned.append(profile.name)
        return FakeProc()

    monkeypatch.setattr(launcher_mod, "spawn_browser", slow_spawn)
    first = threading.Thread(target=bl.start_thread, args=(Profile(name="p"), lambda m: None))
    first.start()
    assert entered.wait(5)
    try:
        with pytest.raises(ProfileBusyError):
            bl.start_thread(Profile(name="p"), lambda m: None)
    finally:
        release.set()
        first.join(5)
    assert bl.spawned == ["p"]
    assert bl.is_running("p")


def test_failed_spawn_releases_the_profile(bl, monkeypatch):
    def broken(profile):
        raise OSError("no runner")

    monkeypatch.setattr(launcher_mod, "spawn_browser", broken)
    stopped = []
    assert bl.start_thread(Profile(name="p"), lambda m: None, on_stop=lambda: stopped.append(1))
    assert stopped == [1]
    with bl.exclusive("p"):
        pass


class _Profiles:
    def __init__(self, *names):
        self.profiles = {n: Profile(name=n) for n in names}


def test_ui_click_does_not_stay_loading_when_launched_elsewhere(bl, monkeypatch):
    state = AppState()
    # The API launched the profile between the UI's is_running check and its
    # start_thread call.
    monkeypatch.setattr(bl, "is_running", lambda name: False)
    bl.start_thread(Profile(name="p"), lambda m: None)

    launch_or_stop("p", _Profiles("p"), bl, state, lambda m: None)

    assert not state.is_loading("p")
    assert "p" not in state.failed
    assert bl.spawned == ["p"]


def test_a_raising_callback_does_not_leave_the_profile_busy(bl):
    def boom():
        raise RuntimeError("UI gone")

    with pytest.raises(RuntimeError):
        bl.start_thread(Profile(name="p"), lambda m: None, on_start=boom)
    with bl.exclusive("p"):
        pass
    assert bl.spawned == []


def test_an_old_session_ending_keeps_the_newer_launch(bl, monkeypatch):
    exits = []
    monkeypatch.setattr(
        launcher_mod, "wait_for_exit", lambda proc, name, notify: exits.append(notify)
    )
    bl.start_thread(Profile(name="p"), lambda m: None)
    # The first browser is gone but its exit callback has not run yet.
    bl._active_sessions.clear()
    bl._stop_notifiers.clear()
    bl.start_thread(Profile(name="p"), lambda m: None)

    exits[0]()

    assert bl.is_running("p")
    assert bl.spawned == ["p", "p"]


def test_api_launch_answers_409_when_the_browser_appeared_meanwhile(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from src.api.app import create_app
    from src.core.container import Container

    monkeypatch.chdir(tmp_path)
    container = Container()
    client = TestClient(create_app(container), base_url="http://127.0.0.1")
    assert client.post("/api/v1/profiles", json={"name": "p"}).status_code in (200, 201)
    monkeypatch.setattr(container.browser_launcher, "is_running", lambda name: False)
    monkeypatch.setattr(container.browser_launcher, "start_thread", lambda *a, **k: False)

    r = client.post("/api/v1/browser/p/launch")

    assert r.status_code == 409
    assert r.json()["detail"] == "Browser already running"


def _fail_launch(bl, monkeypatch):
    """Launch, then have the browser exit before it was ready."""
    exits = []
    monkeypatch.setattr(
        launcher_mod, "wait_for_exit", lambda proc, name, notify: exits.append(notify)
    )
    bl.start_thread(Profile(name="p"), lambda m: None)
    exits[-1]()


def test_repeated_failed_launches_start_a_backoff(bl, monkeypatch):
    monkeypatch.setattr(launcher_mod, "LAUNCH_FAILURE_LIMIT", 3)
    monkeypatch.setattr(launcher_mod, "LAUNCH_BACKOFF", 300)
    _fail_launch(bl, monkeypatch)
    _fail_launch(bl, monkeypatch)
    assert bl.launch_backoff("p") == 0
    _fail_launch(bl, monkeypatch)
    assert 290 < bl.launch_backoff("p") <= 300
    assert bl.launch_backoff("other") == 0


def test_failures_outside_the_window_do_not_count(bl, monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr(launcher_mod.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(launcher_mod, "LAUNCH_FAILURE_LIMIT", 2)
    monkeypatch.setattr(launcher_mod, "LAUNCH_FAILURE_WINDOW", 120)
    _fail_launch(bl, monkeypatch)
    clock[0] += 121
    _fail_launch(bl, monkeypatch)
    assert bl.launch_backoff("p") == 0


def test_a_successful_launch_clears_failures_and_backoff(bl, monkeypatch):
    monkeypatch.setattr(launcher_mod, "LAUNCH_FAILURE_LIMIT", 2)
    _fail_launch(bl, monkeypatch)
    _fail_launch(bl, monkeypatch)
    assert bl.launch_backoff("p") > 0
    bl._note_launch("p", ok=True)
    assert bl.launch_backoff("p") == 0
    _fail_launch(bl, monkeypatch)
    assert bl.launch_backoff("p") == 0


def test_stopping_a_starting_browser_is_not_a_failure(bl, monkeypatch):
    monkeypatch.setattr(launcher_mod, "LAUNCH_FAILURE_LIMIT", 1)
    monkeypatch.setattr(launcher_mod, "terminate", lambda *a, **k: None)
    exits = []
    monkeypatch.setattr(
        launcher_mod, "wait_for_exit", lambda proc, name, notify: exits.append(notify)
    )
    bl.start_thread(Profile(name="p"), lambda m: None)
    bl.stop_profile("p")
    exits[-1]()
    assert bl.launch_backoff("p") == 0


def test_backoff_can_be_turned_off(bl, monkeypatch):
    monkeypatch.setattr(launcher_mod, "LAUNCH_FAILURE_LIMIT", 0)
    for _ in range(5):
        _fail_launch(bl, monkeypatch)
    assert bl.launch_backoff("p") == 0


def test_leftover_browsers_are_killed_before_spawning(bl, monkeypatch):
    order = []
    spawn = launcher_mod.spawn_browser

    def kill(name, data_dir):
        order.append(("kill", name, data_dir))
        return 2

    def spawn_after(profile):
        order.append(("spawn", profile.name))
        return spawn(profile)

    monkeypatch.setattr(launcher_mod.orphans, "kill_orphans", kill)
    monkeypatch.setattr(launcher_mod, "spawn_browser", spawn_after)
    logs = []
    bl.start_thread(Profile(name="p"), logs.append)
    assert order == [("kill", "p", os.path.join(launcher_mod.DATA_DIR, "p")), ("spawn", "p")]
    assert any("2" in m and "p" in m for m in logs)


def test_a_broken_orphan_scan_does_not_block_the_launch(bl, monkeypatch):
    def broken(*a, **k):
        raise RuntimeError("no access")

    monkeypatch.setattr(launcher_mod.orphans, "kill_orphans", broken)
    assert bl.start_thread(Profile(name="p"), lambda m: None)
    assert bl.spawned == ["p"]


def test_api_launch_answers_429_during_backoff(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from src.api.app import create_app
    from src.core.container import Container

    monkeypatch.chdir(tmp_path)
    container = Container()
    client = TestClient(create_app(container), base_url="http://127.0.0.1")
    assert client.post("/api/v1/profiles", json={"name": "p"}).status_code in (200, 201)
    monkeypatch.setattr(container.browser_launcher, "launch_backoff", lambda name: 41.2)
    monkeypatch.setattr(
        container.browser_launcher, "start_thread", lambda *a, **k: pytest.fail("launched")
    )

    r = client.post("/api/v1/browser/p/launch")

    assert r.status_code == 429
    assert r.headers["Retry-After"] == "42"
    assert "42s" in r.json()["detail"]
