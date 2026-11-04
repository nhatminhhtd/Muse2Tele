# -*- coding: utf-8 -*-
"""
Cai cac skill trong skills\\ len 1 profile Muse: dong goi skills\\dist\\muse_skills.zip (skills\\build_zip.py), gui
zip kem tin cai dat (khoi ```text dau tien trong skills\\INSTALL.md) vao MAIN CHAT cua profile, tu bam Allow neu Muse
xin quyen, cho Muse tra loi. Bot goi sau khi reset Muse cua profile VIP va qua /skills; trong luc cai bot giu khong
chuyen tin main chat ve Telegram, xong thi danh dau cac tin tra loi viec cai la da chuyen (khong gui cho ai).
"""

import logging
import re
import runpy
import shutil
import time

import muse_auto
import muse_sync
from muse_sync import HERE

SKILLS_DIR = HERE / "skills"
INSTALL_DOC = SKILLS_DIR / "INSTALL.md"
POLL_SECONDS = 3
IDLE_POLLS = 3  # Muse ranh + da co tra loi ngan nay vong lien tiep thi coi la cai xong
TIMEOUT_SECONDS = 15 * 60
# Nut Stop cua o chat (dang hien, khong nam trong khoi an): /skills stop thi dung luot cai cua Muse
CLICK_STOP_JS = """() => { const b = [...document.querySelectorAll('[data-testid="hatch-composer-stop-button"]')]
  .find(b => !b.closest('[inert],[aria-hidden="true"]')); if (!b) return false; b.click(); return true; }"""

logger = logging.getLogger("muse.skills")


def build():
    """Tao lai zip tu cac thu muc skill. Tra ve (duong dan zip, ten cac skill)."""
    return runpy.run_path(str(SKILLS_DIR / "build_zip.py"))["build"]()


def install_prompt():
    found = re.search(r"```text\n(.+?)\n```", INSTALL_DOC.read_text(encoding="utf-8"), re.DOTALL)
    if not found:
        raise RuntimeError(f"{INSTALL_DOC} khong co khoi ```text chua tin cai dat")
    return found.group(1).strip()


def install_replies(msgs, before):
    """Cac tin cua Muse tra loi tin cai dat: sau tin user moi dau tien (tin cai dat), truoc tin user ke tiep. Tin chua
    co id (dang hien len) bo qua, vong sau doc lai."""
    replies, started = [], False
    for m in msgs:
        if not m.get("id") or m["id"] in before:
            continue
        if m["role"] == "user":
            if started:
                break
            started = True
        elif started and m["role"] == "assistant":
            replies.append(m)
    return replies


def install(profile, upload_dir, cancel=None):
    """Cai skill len main chat cua profile. upload_dir phai nam trong FOXPROFILE_UPLOAD_DIRS (zip tam chep vao day, xoa
    ngay sau khi upload). cancel (threading.Event): dat thi bam Stop luot cua Muse va thoi cho.
    Tra ve (ok, tra loi cua Muse / ly do loi, id cac tin Muse tra loi viec cai)."""
    package, names = build()
    safe = re.sub(r"[^\w.-]", "_", profile)
    folder = upload_dir / f"skills_{safe}_{int(time.time())}"
    folder.mkdir(parents=True, exist_ok=True)
    chat = {"profile": profile, "url": muse_sync.MUSE_URL, "tg": "", "key": profile}
    before = set()
    try:
        shutil.copy2(package, folder / package.name)
        ok, result = muse_sync.send(chat, install_prompt(), [str(folder / package.name)], seen=before)
    finally:
        shutil.rmtree(folder, ignore_errors=True)
    if not ok:
        return False, result, []
    logger.info(f"{profile}: gui {', '.join(names)} vao main chat, cho Muse cai")
    fox = muse_sync.chat_browser(chat)
    reply, ids, idle, deadline = "", [], 0, time.time() + TIMEOUT_SECONDS
    while time.time() < deadline:
        time.sleep(POLL_SECONDS)
        try:
            if cancel and cancel.is_set():
                fox.evaluate(CLICK_STOP_JS)
                time.sleep(2)
                ids = [m["id"] for m in install_replies(muse_sync.messages(fox), before)]
                return False, "Da dung theo lenh (da bam Stop luot cai cua Muse)", ids
            fox.evaluate(muse_auto.CLICK_ALLOW_JS)  # tin cai dat la cua bot: tu duyet cac yeu cau cua no
            busy = muse_sync.is_busy(fox)
            replies = install_replies(muse_sync.messages(fox), before)
        except Exception as e:
            logger.warning(f"{profile}: doc main chat luc cai skill loi {type(e).__name__}: {e}")
            continue
        ids = [m["id"] for m in replies]
        done = [m for m in replies if m.get("text") and not m.get("streaming")]
        idle = idle + 1 if done and not busy else 0
        if idle >= IDLE_POLLS:
            reply = done[-1]["text"]
            break
    if not reply:
        return False, f"Muse chua tra loi sau {TIMEOUT_SECONDS // 60} phut", ids
    return True, reply, ids
