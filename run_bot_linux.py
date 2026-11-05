# -*- coding: utf-8 -*-
"""Shim chay bot Muse2Tele tren Linux/container, khong sua code goc.

Van de goc: muse_telebot.py -> main() goi thang:
  ctypes.windll.kernel32.SetConsoleTitleW(...)
  ctypes.WinDLL("kernel32") + CreateMutexW
  ctypes.get_last_error()
Tren Linux, ctypes khong co windll/WinDLL/get_last_error nen bot chet ngay
khi khoi dong, du token va FoxProfile deu dung.

Shim nay stub cac API Windows-only truoc khi import bot, roi:
  - fail nhanh neu thieu TELEGRAM_BOT_TOKEN (tranh roi vao console_guide
    cua ban Windows: mo notepad.exe + input() — se treo tren Render),
  - chuyen file state sang disk (BOT_STATE_FILE) de khoi mat map
    admin/nhom/topic khi Render restart. Luu y: save_state() cua bot dung
    os.replace() nen khong dung symlink cho state — patch truc tiep bien
    STATE_FILE cua module moi co tac dung.
"""
import ctypes
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "muse_telebot"))

if sys.platform != "win32":
    class _Kernel32:
        def SetConsoleTitleW(self, *args, **kwargs):
            return 0

        def CreateMutexW(self, *args, **kwargs):
            return 1  # != 0: khong phai instance thu 2

    class _Windll:
        kernel32 = _Kernel32()

    ctypes.windll = _Windll()  # type: ignore[attr-defined]
    ctypes.WinDLL = lambda *args, **kwargs: _Kernel32()  # type: ignore[attr-defined]
    if not hasattr(ctypes, "get_last_error"):
        ctypes.get_last_error = lambda: 0  # type: ignore[attr-defined]

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
if not TOKEN:
    raise SystemExit("Thieu TELEGRAM_BOT_TOKEN — set tren Render, khong ghi vao repo.")

import muse_telebot  # noqa: E402

state_file = os.environ.get("BOT_STATE_FILE", "").strip()
if state_file:
    state_path = Path(state_file)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    muse_telebot.STATE_FILE = state_path

if __name__ == "__main__":
    muse_telebot.main()
