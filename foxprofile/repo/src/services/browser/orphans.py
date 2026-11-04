"""Find and kill browsers left behind by an earlier FoxProfile process.

When FoxProfile dies without stopping its browsers (killed, crashed), their
runner and browser processes keep running and keep the profile's data dir
locked. A new launch of that profile then fails at once, because the browser
refuses a data dir another instance holds. Before launching, the launcher
kills whatever still uses the profile's data dir.
"""

from __future__ import annotations

import contextlib
import os

import psutil

from ...core.logging import get_logger

logger = get_logger("browser.orphans")


def _norm(path: str) -> str:
    return os.path.normcase(os.path.abspath(path.strip('"')))


def _uses_data_dir(args: list[str], data_dir: str) -> bool:
    """Camoufox gets `-profile <dir>`, Chromium `--user-data-dir=<dir>`."""
    for i, arg in enumerate(args):
        if arg.startswith("--user-data-dir="):
            arg = arg.split("=", 1)[1]
        elif not (i > 0 and args[i - 1] == "-profile"):
            continue
        if _norm(arg) == data_dir:
            return True
    return False


def _is_runner_for(args: list[str], profile_name: str) -> bool:
    """`python .../runner.py <name> ...` or `python -m chrome_engine.runner <name> ...`."""
    for i, arg in enumerate(args[:-1]):
        camoufox = os.path.basename(arg).casefold() == "runner.py"
        chrome = arg == "chrome_engine.runner" and i > 0 and args[i - 1] == "-m"
        if camoufox or chrome:
            return args[i + 1].casefold() == profile_name.casefold()
    return False


def find_orphans(profile_name: str, data_dir: str) -> list[psutil.Process]:
    """Processes outside this one that run `profile_name` or use its data dir.

    Runners only count when started from this working directory, since that
    is what their relative data dir resolves against.
    """
    data_dir = _norm(data_dir)
    cwd = _norm(os.getcwd())
    me = os.getpid()
    found = []
    for proc in psutil.process_iter(["pid", "cmdline"]):
        try:
            args = proc.info["cmdline"] or []
            if proc.pid == me or not args:
                continue
            if _uses_data_dir(args, data_dir) or (
                _is_runner_for(args, profile_name) and _norm(proc.cwd()) == cwd
            ):
                found.append(proc)
        except psutil.Error:
            continue
    return found


def kill_orphans(profile_name: str, data_dir: str, timeout: float = 5) -> int:
    """Kill the orphans of a profile and their children; returns how many died."""
    victims: dict[int, psutil.Process] = {}
    for proc in find_orphans(profile_name, data_dir):
        victims[proc.pid] = proc
        with contextlib.suppress(psutil.Error):
            for child in proc.children(recursive=True):
                victims[child.pid] = child
    if not victims:
        return 0
    for proc in victims.values():
        with contextlib.suppress(psutil.Error):
            proc.kill()
    # The data dir stays locked until the browser has actually exited.
    psutil.wait_procs(list(victims.values()), timeout=timeout)
    logger.warning(
        "Killed %d leftover process(es) of profile %s: %s",
        len(victims),
        profile_name,
        sorted(victims),
    )
    return len(victims)
