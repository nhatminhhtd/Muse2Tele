"""Keep the files a browser downloads.

Playwright parks every download in a temporary folder and deletes it when the
browser closes, so a download that looks finished in the page vanishes unless
it is saved explicitly. This copies each one into the download folder chosen
in the web panel.
"""

from __future__ import annotations

import asyncio
import os
import pathlib
import re
import sys

from ...core import settings

_INVALID = re.compile(r'[<>:"/\|?*\x00-\x1f]')


def _say(message: str) -> None:
    try:
        print(message, flush=True)
    except UnicodeEncodeError:
        sys.stdout.buffer.write((message + "\n").encode("utf-8", errors="replace"))
        sys.stdout.flush()


def safe_name(name: str) -> str:
    name = _INVALID.sub("_", os.path.basename(name or "")).strip(" .")
    return name[:180] or "download"


def unique_path(folder: pathlib.Path, name: str) -> pathlib.Path:
    """`name` inside `folder`, numbered ("a (1).mp4") when it already exists."""
    stem, suffix = os.path.splitext(safe_name(name))
    candidate = folder / f"{stem}{suffix}"
    n = 1
    while candidate.exists():
        candidate = folder / f"{stem} ({n}){suffix}"
        n += 1
    return candidate


async def save(download: object) -> pathlib.Path | None:
    _say(f"Download started: {download.suggested_filename} <- {download.url[:150]}")
    try:
        folder = settings.download_dir()
        folder.mkdir(parents=True, exist_ok=True)
        dest = unique_path(folder, download.suggested_filename)
        await download.save_as(str(dest))
        failure = await download.failure()
        if failure:
            raise OSError(f"download failed: {failure}")
    except Exception as e:  # a failed save must never take the browser down
        _say(
            f"Warning: could not save download: {type(e).__name__}: {' '.join(str(e).split())[:200]}"
        )
        return None
    _say(f"Saved download: {dest}")
    return dest


def install(context: object) -> None:
    """Save the downloads of every tab, including tabs opened later."""
    tasks: set[asyncio.Task] = set()

    def on_download(download: object) -> None:
        task = asyncio.ensure_future(save(download))
        tasks.add(task)
        task.add_done_callback(tasks.discard)

    def watch(page: object) -> None:
        page.on("download", on_download)

    for page in context.pages:
        watch(page)
    context.on("page", watch)
