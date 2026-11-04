import os
import subprocess
import sys
import time

import psutil
import pytest

from src.services.browser import orphans


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        (["camoufox.exe", "-no-remote", "-profile", "{dir}", "-juggler-pipe"], True),
        (["chrome.exe", "--user-data-dir={dir}", "--no-first-run"], True),
        (["camoufox.exe", "-profile", "{dir}2"], False),
        (["camoufox.exe", "{dir}"], False),
        (["camoufox.exe", "-profile"], False),
    ],
)
def test_uses_data_dir(tmp_path, args, expected):
    data_dir = str(tmp_path / "camoufox_data" / "p")
    args = [a.format(dir=data_dir) for a in args]
    assert orphans._uses_data_dir(args, orphans._norm(data_dir)) is expected


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        (["python.exe", "C:\\fox\\src\\services\\browser\\runner.py", "Muse", "None"], True),
        (["python.exe", "/fox/src/services/browser/runner.py", "muse", "None"], True),
        (["python.exe", "-m", "chrome_engine.runner", "Muse", "None"], True),
        (["python.exe", "runner.py", "Muse2", "None"], False),
        (["python.exe", "playwright_upload_runner.py", "Muse"], False),
        (["python.exe", "chrome_engine.runner", "Muse"], False),
        (["python.exe", "runner.py"], False),
    ],
)
def test_is_runner_for(args, expected):
    assert orphans._is_runner_for(args, "Muse") is expected


def _sleeper(*extra):
    return subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)", *extra])


def test_kill_orphans_kills_only_the_profiles_processes(tmp_path):
    data_dir = str(tmp_path / "camoufox_data" / "p")
    holder = _sleeper("-profile", data_dir)
    other = _sleeper("-profile", data_dir + "2")
    try:
        assert orphans.kill_orphans("p", data_dir) >= 1
        assert holder.wait(5) is not None
        assert other.poll() is None
    finally:
        for proc in (holder, other):
            proc.kill()
            proc.wait(5)


def test_kill_orphans_also_kills_children(tmp_path):
    data_dir = str(tmp_path / "camoufox_data" / "p")
    code = (
        "import subprocess, sys, time;"
        "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)']);"
        "time.sleep(60)"
    )
    parent = subprocess.Popen([sys.executable, "-c", code, "-profile", data_dir])
    try:
        ps = psutil.Process(parent.pid)
        deadline = time.monotonic() + 10
        while not ps.children() and time.monotonic() < deadline:
            time.sleep(0.1)
        children = ps.children()
        assert children
        assert orphans.kill_orphans("p", data_dir) >= 2
        gone, alive = psutil.wait_procs(children, timeout=5)
        assert not alive
    finally:
        parent.kill()
        parent.wait(5)


def test_kill_orphans_ignores_runners_from_another_folder(tmp_path, monkeypatch):
    runner = tmp_path / "runner.py"
    runner.write_text("import time; time.sleep(60)")
    proc = subprocess.Popen([sys.executable, str(runner), "p"], cwd=tmp_path)
    try:
        other = tmp_path / "other"
        other.mkdir()
        monkeypatch.chdir(other)
        assert orphans.kill_orphans("p", str(other / "camoufox_data" / "p")) == 0
        monkeypatch.chdir(tmp_path)
        assert orphans.kill_orphans("p", str(tmp_path / "camoufox_data" / "p")) >= 1
        assert proc.wait(5) is not None
    finally:
        proc.kill()
        proc.wait(5)


def test_nothing_to_kill(tmp_path):
    assert orphans.kill_orphans("p", os.path.join(tmp_path, "camoufox_data", "p")) == 0
