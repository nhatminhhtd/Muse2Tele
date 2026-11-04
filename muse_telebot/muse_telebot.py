# -*- coding: utf-8 -*-
"""
Bot Telegram cho muse.ai (@muse_tbot): nguoi dung nhan tin tren Telegram thay vi vao web muse.ai.
  - Telegram -> muse: tin nhan / anh / video / gif / file / audio duoc go vao main chat hoac side chat muse.ai cua
    profile FoxProfile tuong ung (muse_sync.py), nguyen van (khong them the). Chat muse moi mo dau bang INTRO.
  - muse -> Telegram: bot doc tra loi cua Muse tren trang (chu + anh/video/file dinh kem) va gui ve dung chat Telegram
    (relay). Chat muse da map trong muse_sync.json con duoc theo doi lien tuc (watch): moi tin moi cua Muse, ke ca tin
    khong phai tra loi tin Telegram (go tren web, viec Muse tu chay ve sau), deu ve chat/topic da map. Muse chi tra loi
    trong chat, khong tu gui Telegram (skill telegram_sender da bo). Dong "[[nút: A | B]]" cuoi tin cua Muse thanh nut
    bam; bam nut thi lua chon duoc gui lai vao chat muse.
Bot nay la noi DUY NHAT poll update cua @muse_tbot (Muse khong goi get-updates: 409, tranh nhau update).

Nguoi dung:
  - Admin (chat id trong MUSE_BOT_ALLOWED_CHAT_IDS): dung main chat / side chat trong muse_sync.json (/to de chon,
    /<profile> <noi dung>), nhom/topic (map bang /to trong nhom/topic), /stats, /broadcast, /approve*.
    Moi profile FoxProfile ten Muse* chua map duoc tu tao topic cung ten trong nhom admin ("admin_group" trong
    muse_sync.json) va map main chat vao do (admin_topics_loop).
  - Free (muse_users.py, dang tam dung: FREE_ENABLED = False): /start -> dang ky -> bot tao 1 side chat rieng trong pool Muse2-4 (profile it nguoi nhat;
    tao loi thi thu profile khac), bao Muse ten nguoi dung. Het han thi bot xoa side chat, tra suat ve pool. Quota
    anh/video moi ngay tinh tren anh/video bot chuyen ve.
  - VIP (muse_users.py): mua qua /start (QR chuyen khoan, admin duyet) hoac admin /vip <id> <ngay>; moi nguoi 1
    profile rieng. Chat rieng -> main chat; nhom gan bang /vipgroup: General -> main chat, moi topic -> 1 side chat.
  - Moi nguoi dung: /hoi <cau hoi> -> chuyen cho admin; admin reply tin do -> tra loi ve nguoi dung (nguoi dung
    reply tin tra loi la hoi tiep, khong vao Muse).
    Het han: reset Muse cua profile roi cai lai skill (muse_skills.py, /skills).
  - Tin Free / VIP gui vao Muse duoc log (muse_users.db, /log); video Muse gui cho ho duoc chuyen them cho admin.
File tai tu Telegram chi nam tam trong MUSE_UPLOAD_DIR, xoa ngay sau khi upload vao muse; anh/video Muse gui ve chi
nam trong RAM, khong ghi ra dia.
Album (nhieu anh/video gui 1 lan) duoc gom thanh 1 tin tren muse. Bot API chi tai duoc file <= 20MB.
Trang thai: 👀 da nhan, 👍 da gui vao muse, 👎 loi; trong luc Muse lam viec: "<bot> dang nhap..."; Muse xong: 👌.

.env (thu muc nay hoac ..\\.env):
    TELEGRAM_BOT_TOKEN=<token bot rieng tu BotFather>
    MUSE_BOT_ALLOWED_CHAT_IDS=<chat id admin, cach nhau dau phay>   # mac dinh = TELEGRAM_ALLOWED_CHAT_IDS
    MUSE_UPLOAD_DIR=<thu muc tam>   # phai nam trong FOXPROFILE_UPLOAD_DIRS cua FoxProfile

    python muse_telebot.py
"""

import ctypes
import html
import io
import json
import logging
import mimetypes
import os
import queue
import re
import shutil
import threading
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from types import SimpleNamespace

import requests
import telebot
from dotenv import load_dotenv
from telebot import types
from telebot.apihelper import ApiTelegramException

import muse_auto
import muse_skills
import muse_sync
import muse_users
import vietqr
from muse_sync import HERE

TITLE = "Muse2tele_Bot"  # tieu de console; khac ban linkgold de apps_monitor o C khong nham cua so
load_dotenv(HERE / ".env")
load_dotenv(HERE.parent / ".env")

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
ALLOWED_CHAT_IDS = {int(x) for x in (os.environ.get("MUSE_BOT_ALLOWED_CHAT_IDS")
                                     or os.environ.get("TELEGRAM_ALLOWED_CHAT_IDS", "")).replace(" ", "").split(",") if x}
# Thu muc tam chua file tai tu Telegram truoc khi upload: phai nam trong FOXPROFILE_UPLOAD_DIRS (foxprofile\repo\.env)
UPLOAD_DIR = Path(os.environ.get("MUSE_UPLOAD_DIR", str(HERE.parent / "Videos" / "downloads" / "muse_telebot")))
# {"targets": {"<chat id>": "<key chat muse dang chon>"}, "delivered": {"<key chat muse>": [id tin Muse da chuyen]},
#  "watched": [key chat muse watch dang theo doi]}
STATE_FILE = HERE / "muse_telebot_state.json"
TG_DOWNLOAD_LIMIT = 20 * 1024 * 1024  # getFile cua Bot API
TG_UPLOAD_LIMIT = 50 * 1024 * 1024  # gui file qua Bot API
MEDIA_UPLOAD_TIMEOUT = 300  # giay cho 1 lan tai anh/video/file len Telegram
MEDIA_UPLOAD_ATTEMPTS = 2
ALBUM_WAIT_SECONDS = 2  # cho cac phan con lai cua album (cung media_group_id) toi
REPLY_QUOTE_MAX = 150
CONTENT_TYPES = ["text", "photo", "video", "animation", "document", "audio", "voice", "video_note"]
RELAY_INTERVAL = 1.5  # giay giua 2 lan doc trang muse
RELAY_IDLE_POLLS = 3  # bao nhieu lan lien tiep Muse ranh + khong con tin cho chuyen thi coi la xong luot
RELAY_START_GRACE = 30  # khong thay muse ban lan nao sau ngan nay giay (tra loi qua nhanh) -> coi la xong
RELAY_MAX_SECONDS = 2 * 3600
RELAY_MAX_ERRORS = 15
WATCH_INTERVAL = 5  # giay giua 2 vong doc cac chat muse da map (watch)
WATCH_RETRY_SECONDS = 60  # chat loi (profile dang mo, chua dang nhap...) thi ngan nay giay sau moi doc lai
DELIVERED_KEEP = 200  # moi chat muse nho id ngan nay tin Muse da chuyen gan nhat
MEDIA_RELOAD_SECONDS = 20  # anh/video cua Muse chua nap sau ngan nay giay thi tai lai trang
MEDIA_RELOAD_GAP = 90  # toi da 1 lan tai lai trang moi ngan nay giay
MEDIA_MISSING_WAIT = 240  # khung "Video not found" (file con tren Muse) cho ngan nay giay (~2 lan tai lai) roi moi bao
EXPIRY_CHECK_SECONDS = 300
ADMIN_PROFILE_PREFIX = "Muse"  # profile FoxProfile ten bat dau bang chu nay: tu tao topic + map trong nhom admin
ADMIN_TOPICS_CHECK_SECONDS = 300
STALL_RETRY_SECONDS = 60  # muse loi (trinh duyet treo...): ngan nay giay gui lai cac tin dang xep hang 1 lan
STALL_GIVE_UP_SECONDS = 30 * 60  # muse loi lau hon: bao nguoi dung nhan lai sau, bo hang
WATCH_HANG_SECONDS = 180  # watch doc 1 profile timeout lien tuc lau hon: trinh duyet treo, khoi dong lai
MUSE_DOWN_TEXT = ("⏳ Muse đang gặp lỗi, bạn chờ chút nhé. Bot sẽ tự gửi lại tin này cho Muse khi Muse hoạt động "
                  "trở lại.")
CHOSEN_DATA = "muse_bridge_chosen"  # nut "✅ <lua chon>" thay ban phim sau khi bam; "to:", "free:", "bc:" la cua bot
BUTTONS_RE = re.compile(r"\[\[\s*(?:nút|nut|buttons?)\s*:\s*(.+?)\s*\]\]", re.IGNORECASE | re.DOTALL)
KIND_LABEL = {"image": "ảnh", "video": "video"}
INTRO = "Ở cửa sổ chat này, hãy gọi tôi là \"{name}\""  # tin dau tien cua moi chat muse moi
VIP_MODES = {"direct": "Chat trực tiếp", "group": "Group topic"}

LOG_FILE = HERE / "muse_telebot.log"
_root = logging.getLogger("muse")  # muse.sync, muse.auto ghi chung file nay
_root.setLevel(logging.INFO)
for _handler in (RotatingFileHandler(LOG_FILE, maxBytes=2 * 1024 * 1024, backupCount=2, encoding="utf-8"),
                 logging.StreamHandler()):
    _handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    _root.addHandler(_handler)
logger = logging.getLogger("muse.telebot")

# threaded=False: handler chay tuan tu tren thread polling, chi xep viec vao hang doi -> giu dung thu tu tin
bot = telebot.TeleBot(TOKEN, parse_mode=None, threaded=False) if TOKEN else None
# viec cho worker: {"kind": "msg" | "tap" | "signup", "m": tin Telegram, "chat": chat muse, "text": ...}
jobs = queue.Queue()
# key chat muse -> {"targets": [tin Telegram], "seen": id tin muse da co/da chuyen, "since", "user",
#                   "waiting": {id tin: luc thay anh/video chua nap}, "reloaded": luc tai lai trang gan nhat}
relays = {}
relay_lock = threading.Lock()
state_lock = threading.Lock()  # STATE_FILE: polling (/to), relay va watch cung ghi
skills_cancel = threading.Event()  # /skills stop: dung cac lan cai skill dang chay
skill_holds = set()  # key main chat dang cai skill: relay / watch tam chua chuyen tin cua chat do ve Telegram
# key chat muse dang loi -> {"batches": [cac tin chua gui duoc, theo thu tu], "since": luc bat dau loi}. Tin moi vao
# chat do xep sau, worker gui lai theo thu tu (STALL_RETRY_SECONDS).
stalled = {}
stalled_lock = threading.Lock()
broadcasts = {}  # id tin xac nhan quang ba -> {"text": ...} hoac {"from_chat": .., "message_id": ..}


# ---------- chon chat muse ----------

def authorized(chat_id):
    return chat_id in ALLOWED_CHAT_IDS


def load_state():
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_state(state):
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=1, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, STATE_FILE)


def selected_chat(chat_id):
    """Chat muse dang chon cho chat rieng chat_id (/to); chua chon / chat da xoa khoi config -> chat dau tien."""
    chats = muse_sync.muse_chats()
    key = load_state().get("targets", {}).get(str(chat_id))
    return next((c for c in chats if c["key"] == key), chats[0] if chats else None)


def update_state(change):
    """Doc STATE_FILE, goi change(state) roi ghi lai. Tra ve ket qua cua change."""
    with state_lock:
        state = load_state()
        result = change(state)
        save_state(state)
        return result


def select_chat(chat_id, key):
    update_state(lambda state: state.setdefault("targets", {}).__setitem__(str(chat_id), key))


def topic_of(m):
    """Topic id cua tin trong nhom co topic; None voi chat thuong (ke ca reply thread cua nhom thuong)."""
    return m.message_thread_id if getattr(m, "is_topic_message", False) else None


def free_chat(u):
    """Chat muse (side chat Free) cua nguoi dung u (ban ghi muse_users)."""
    return {"profile": u["free_profile"], "url": muse_sync.THREAD_URL + u["free_thread"], "tg": "",
            "key": f"{u['free_profile']}/{u['free_thread']}", "user": u["id"]}


def vip_chat(u, topic=None):
    """Chat muse cua nguoi dung VIP u: main chat, hoac side chat cua topic (url None: chua tao, process() tao)."""
    profile = u["vip_profile"]
    if not topic:
        return {"profile": profile, "url": muse_sync.MUSE_URL, "tg": "", "key": profile, "vip": u["id"]}
    thread = muse_users.vip_topic(u["id"], topic)
    return {"profile": profile, "url": muse_sync.THREAD_URL + thread if thread else None, "tg": "",
            "key": f"{profile}/{thread}" if thread else f"{profile}/topic{topic}", "vip": u["id"], "topic": topic}


def target_for(m, user=None):
    """Chat muse nhan tin m: topic/kenh/nhom da map trong muse_sync.json, nhom cua nguoi dung VIP, chat rieng cua VIP
    (main chat), chat dang chon cua admin, hoac side chat Free (chat rieng). Nhom/topic chua map: theo chat dang chon
    cua admin gui tin / bam nut (user)."""
    by_tg = muse_sync.chats_by_tg()
    topic = topic_of(m)
    chat = (topic and by_tg.get(f"{m.chat.id}/{topic}")) or by_tg.get(str(m.chat.id))
    if chat:
        return chat
    if m.chat.type in ("group", "supergroup"):
        u = muse_users.vip_by_group(m.chat.id)
        if muse_users.vip_active(u):
            return vip_chat(u, topic)
    if m.chat.type == "private":
        u = muse_users.get(m.chat.id)
        if muse_users.vip_active(u):  # VIP truoc ca admin: admin mua VIP de thu thi cung vao profile VIP
            return vip_chat(u)
    if authorized(m.chat.id):
        return selected_chat(m.chat.id)
    user = user or m.from_user
    if m.chat.type != "channel" and user and authorized(user.id):
        return selected_chat(user.id)
    if m.chat.type == "private" and muse_users.free_active(u):
        return free_chat(u)
    return None


def topic_name(m):
    """Ten topic Telegram cua tin m (tin trong topic reply tin tao topic), '' neu khong biet."""
    created = getattr(getattr(m, "reply_to_message", None), "forum_topic_created", None)
    return getattr(created, "name", "") or ""


def profile_commands():
    """lenh Telegram -> profile: /muse -> Muse, /muse2 -> Muse2 (ten profile trong muse_sync.json)."""
    return {re.sub(r"\W", "_", p.lower()): p for p in muse_sync.profiles()}


def command_of(m):
    return (m.text or "").partition(" ")[0].lstrip("/").split("@")[0].lower()


# ---------- Telegram -> muse ----------

def react(m, emoji):
    if m.from_user and m.from_user.is_bot:  # tin cua bot (nut bam, xac nhan dang ky): khong tha reaction
        return False
    try:
        bot.set_message_reaction(m.chat.id, m.message_id, [types.ReactionTypeEmoji(emoji)])
        return True
    except Exception as e:  # kenh tat reaction, bot khong du quyen...
        logger.debug(f"Khong dat duoc reaction {emoji}: {e}")
        return False


def notify(text, skip=None):
    """Bao cho admin."""
    for chat_id in ALLOWED_CHAT_IDS - {skip}:
        try:
            bot.send_message(chat_id, text[:4000])
        except Exception:
            logger.exception("Khong gui duoc thong bao")


def message_file(m):
    """(file Telegram, ten file) cua tin m; (None, '') neu tin khong co file."""
    kind = m.content_type
    if kind == "photo":
        return m.photo[-1], f"photo_{m.message_id}.jpg"
    obj = getattr(m, kind, None) if kind in CONTENT_TYPES[1:] else None
    if obj is None:
        return None, ""
    default_ext = {"video": ".mp4", "animation": ".mp4", "voice": ".ogg", "video_note": ".mp4", "audio": ".mp3"}
    name = getattr(obj, "file_name", None) or f"{kind}_{m.message_id}{default_ext.get(kind, '')}"
    return obj, re.sub(r'[\\/:*?"<>|]', "_", name)


def download(m, folder):
    """Tai file cua tin m vao folder (trong UPLOAD_DIR). Tra ve duong dan, '' neu tin khong co file."""
    obj, name = message_file(m)
    if obj is None:
        return ""
    size = getattr(obj, "file_size", 0) or 0
    if size > TG_DOWNLOAD_LIMIT:
        raise RuntimeError(f"{name} ({size / 1048576:.1f} MB) vuot gioi han tai 20MB cua Bot API")
    info = bot.get_file(obj.file_id)
    if "." not in name:
        name += Path(info.file_path).suffix
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_bytes(bot.download_file(info.file_path))
    return str(path)


def with_reply_context(m, text):
    """Tin la reply 1 tin khac (ke ca tin Muse do bot chuyen ve) -> them doan trich tin goc vao dau de muse biet dang
    tra loi tin nao."""
    ref = getattr(m, "reply_to_message", None)
    if not ref or (topic_of(m) and ref.message_id == m.message_thread_id):  # tin trong topic "reply" tin mo topic
        return text
    quoted = " ".join((ref.text or ref.caption or "").split())
    if not quoted:
        quoted = {"photo": "[ảnh]", "video": "[video]", "animation": "[gif]"}.get(ref.content_type, "[tệp]")
    if len(quoted) > REPLY_QUOTE_MAX:
        quoted = quoted[:REPLY_QUOTE_MAX].rstrip() + "..."
    return f'(Trả lời tin: "{quoted}") {text}'.strip()


def quota_note(uid):
    """Nhac Muse khi nguoi dung Free da het 1 loai quota hom nay; None neu het ca anh lan video (khong nhan tin nua)."""
    left = muse_users.quota_left(uid)
    if not any(left.values()):
        return None
    gone = [f"{KIND_LABEL[k]} ({muse_users.FREE_DAILY[k]}/{muse_users.FREE_DAILY[k]})" for k, n in left.items() if not n]
    return f"(Hôm nay tôi đã hết lượt {', '.join(gone)}, đừng tạo thêm.)" if gone else ""


def quota_exhausted_text():
    d = muse_users.FREE_DAILY
    return f"⚠️ Hôm nay bạn đã dùng hết {d['video']} video và {d['image']} ảnh của gói Free. Mai quay lại nhé!"


def process(batch, retry=False):
    """Gui 1 tin (hoac 1 album, hoac 1 lan bam nut) vao muse, bao ket qua roi chuyen tra loi cua Muse ve Telegram.
    Muse loi: xep tin vao hang cho cua chat (stalled), bao nguoi dung cho. retry: lan gui lai tu hang cho.
    Tra ve False neu tin con nam trong hang cho (muse loi), True neu da xong (gui duoc, hoac loi khac da bao)."""
    first, chat, tap = batch[0]["m"], batch[0]["chat"], batch[0]["kind"] == "tap"
    if not retry:
        with stalled_lock:
            s = stalled.get(chat["key"])
            if s:  # chat dang loi: xep sau cac tin truoc, giu dung thu tu
                s["batches"].append(batch)
        if s:
            hold_notice(batch)
            return False
    text = "\n".join(j["text"] for j in batch if j["text"])
    if not tap:
        text = with_reply_context(first, text)
    prompt, owner = text, chat.get("user") or chat.get("vip")
    uid = chat.get("user")
    if uid:
        note = quota_note(uid)
        if note is None:
            bot.reply_to(first, quota_exhausted_text())
            return True
        text = f"{text}\n{note}".strip() if note else text
    folder = UPLOAD_DIR / f"{first.chat.id}_{first.message_id}"
    files, errors, seen, muse_down = [], [], set(), False
    try:
        for j in batch:
            if tap:  # tin cua Muse co nut bam: khong gui lai file cua no
                break
            try:
                path = download(j["m"], folder)
                if path:
                    files.append(path)
            except Exception as e:
                errors.append(f"{j['m'].content_type}: {e}")
        if files or text.strip():
            base = batch[0].setdefault("base", set())  # giu qua cac lan gui lai: khong tao tin trung
            if chat.get("topic") and not chat["url"]:  # topic moi trong nhom VIP: tao side chat
                ok, result, chat = open_topic(chat, first, text, files, seen, base)
            else:
                ok, result = muse_sync.send(chat, text, files, seen=seen, base=base)
            muse_down = not ok and not errors  # loi tai file tu Telegram: gui lai cung vay, bao ngay
        else:
            ok, result = False, f"{chat['key']}: khong co gi de gui"
        if errors:
            ok, result = False, f"{result}\nKhong tai duoc: " + "; ".join(errors)
    finally:
        shutil.rmtree(folder, ignore_errors=True)
    logger.info(f"Chat {first.chat.id} msg {first.message_id} -> {chat['key']}: {result}")
    if owner:
        try:
            muse_users.log_prompt(owner, chat["key"], batch[0]["kind"], prompt,
                                  [Path(f).name for f in files] + [f"[loi] {e}" for e in errors], ok)
        except Exception:
            logger.exception("Khong ghi duoc log prompt")
    if muse_down:  # loi phia muse: khong bao 👎, xep hang gui lai
        if not retry:
            stall(batch, result)
        return False
    if not tap:
        for j in batch:
            react(j["m"], "👍" if ok else "👎")
    if ok:
        if retry and first.chat.type != "channel":
            try:
                bot.reply_to(first, "✅ Muse đã hoạt động lại, tin này đã được gửi cho Muse.")
            except Exception:
                logger.exception("Khong bao duoc da gui lai")
        if first.chat.type != "channel":
            relay(chat, first, seen)
        return True
    kinds = ", ".join(dict.fromkeys(j["m"].content_type for j in batch))
    if first.chat.type != "channel":
        bot.reply_to(first, f"⚠️ {result}" if authorized(first.chat.id) else "⚠️ Chưa gửi được cho Muse, bạn thử lại nhé.")
    notify(f"⚠️ Tin tu {first.chat.title or first.chat.id} ({kinds}) chua gui duoc vao muse {chat['key']}:\n"
           f"{text[:200]}\n{result}", skip=first.chat.id)
    return True


def hold_notice(batch, result=""):
    """Bao nguoi dung muse dang loi, tin da xep hang (admin: kem chi tiet loi)."""
    first = batch[0]["m"]
    if first.chat.type == "channel":
        return
    try:
        detail = f"\n{result}" if result and authorized(first.chat.id) else ""
        bot.reply_to(first, MUSE_DOWN_TEXT + detail)
    except Exception:
        logger.exception("Khong bao duoc muse dang loi")


def stall(batch, result):
    """Gui vao muse loi (da refresh, khoi dong lai trinh duyet): dua tin vao hang cho cua chat, hen gui lai."""
    key = batch[0]["chat"]["key"]
    with stalled_lock:
        new = key not in stalled
        s = stalled.setdefault(key, {"batches": [], "since": time.time()})
        s["batches"].insert(0, batch)
    hold_notice(batch, result)
    if new:
        first = batch[0]["m"]
        notify(f"⚠️ Muse {key} loi, tin tu {first.chat.title or first.chat.id} dang xep hang gui lai "
               f"{STALL_RETRY_SECONDS}s/lan:\n{result}", skip=first.chat.id)
        schedule_stalled(key)


def schedule_stalled(key):
    t = threading.Timer(STALL_RETRY_SECONDS, lambda: jobs.put({"kind": "stalled", "key": key}))
    t.daemon = True
    t.start()


def run_stalled(key):
    """Worker: gui lai theo thu tu cac tin dang xep hang cua chat key; van loi thi hen lan sau, qua lau thi bo."""
    while True:
        with stalled_lock:
            s = stalled.get(key)
            if not s or not s["batches"]:
                stalled.pop(key, None)
                return
            batch = s["batches"][0]
        if process(batch, retry=True):
            with stalled_lock:
                s["batches"].pop(0)
            continue
        if time.time() - s["since"] < STALL_GIVE_UP_SECONDS:
            schedule_stalled(key)
            return
        with stalled_lock:
            batches = stalled.pop(key, {"batches": []})["batches"]
        for b in batches:
            try:
                if b[0]["m"].chat.type != "channel":
                    bot.reply_to(b[0]["m"], "❌ Muse vẫn đang lỗi, tin này chưa gửi được. Bạn nhắn lại sau ít phút nhé.")
                if b[0]["kind"] != "tap":
                    for j in b:
                        react(j["m"], "👎")
            except Exception:
                logger.exception("Khong bao duoc bo tin")
        notify(f"❌ Muse {key} loi qua {STALL_GIVE_UP_SECONDS // 60} phut, bo {len(batches)} tin dang xep hang.")
        return


def open_topic(chat, m, text, files, seen, base=None):
    """Tin dau tien trong 1 topic cua nhom VIP: tao side chat bang INTRO + chinh tin do.
    Tra ve (ok, thong bao, chat muse cua topic)."""
    u = muse_users.get(chat["vip"])
    if muse_users.vip_topic(u["id"], chat["topic"]):  # tin truoc trong cung topic vua tao side chat
        chat = vip_chat(u, chat["topic"])
        ok, result = muse_sync.send(chat, text, files, seen=seen, base=base)
        return ok, result, chat
    name = topic_name(m) or f"#{chat['topic']}"
    first = f"{INTRO.format(name=u['name'])}\n{text}".strip()
    try:
        thread = muse_sync.new_side_chat(chat["profile"], first, files)
    except Exception as e:
        return False, f"{chat['key']}: tao side chat loi {type(e).__name__}: {e}", chat
    muse_users.set_vip_topic(u["id"], chat["topic"], thread)
    seen.clear()
    logger.info(f"VIP {u['id']}: topic {chat['topic']} ({name}) -> side chat {thread}")
    return True, f"Da tao side chat {thread} cho topic {name}.", vip_chat(u, chat["topic"])


def vip_intro(m, u):
    """Profile VIP vua giao cho u: gioi thieu nguoi dung voi Muse o main chat, chuyen loi chao ve tin m."""
    chat = vip_chat(u)
    intro = INTRO.format(name=u["name"])
    seen = set()
    ok, result = muse_sync.send(chat, intro, seen=seen)
    logger.info(f"VIP intro {u['id']} -> {chat['key']}: {result}")
    if ok:
        relay(chat, m, seen)
    else:
        notify(f"⚠️ Gioi thieu VIP {u['name']} ({u['id']}) vao {chat['key']} loi: {result}")


def signup(m, user):
    """Tao side chat Free cho user (da giu suat bang muse_users.reserve_free); m = tin xac nhan cua bot."""
    u = muse_users.get(user.id)
    name = muse_users.display_name(user)
    intro = INTRO.format(name=name)
    failed = {}  # profile tao side chat loi (chua dang nhap, dang tat...) -> loi; giu suat o profile khac trong pool
    while True:
        try:
            tid = muse_sync.new_side_chat(u["free_profile"], intro)
            break
        except Exception as e:
            logger.exception(f"Tao side chat Free cho {user.id} o {u['free_profile']} loi")
            failed[u["free_profile"]] = f"{type(e).__name__}: {e}"
            muse_users.cancel_reservation(user.id)
            if not muse_users.reserve_free(user.id, exclude=failed):
                bot.edit_message_text("⚠️ Chưa tạo được chat riêng với Muse, bạn thử lại sau ít phút nhé (/start).",
                                      m.chat.id, m.message_id)
                notify(f"⚠️ Tao side chat Free cho {name} ({user.id}) loi:\n"
                       + "\n".join(f"{p}: {e}" for p, e in failed.items()))
                return
            u = muse_users.get(user.id)
    if failed:
        notify(f"⚠️ Tao side chat Free cho {name} ({user.id}) loi, da chuyen sang {u['free_profile']}:\n"
               + "\n".join(f"{p}: {e}" for p, e in failed.items()))
    u = muse_users.activate_free(user.id, tid)
    logger.info(f"Free: {name} ({user.id}) -> {u['free_profile']}/{tid}")
    bot.edit_message_text(f"✅ <b>Đã kích hoạt gói Free!</b>\nHết hạn: <b>{muse_users.fmt_time(u['free_end'])}</b>\n\n"
                          f"Muse đang chào bạn. Từ giờ cứ nhắn tin, gửi ảnh hay file vào đây để làm việc với Muse.",
                          m.chat.id, m.message_id, parse_mode="HTML")
    notify(f"🆕 Free: {name} ({user.id}) -> {u['free_profile']}, con {muse_users.slots_left()} suat")
    relay(free_chat(u), m, set())


def worker():
    """Xu ly hang doi theo dung thu tu; gom cac phan cua 1 album thanh 1 tin."""
    pending = None
    while True:
        job, pending = pending or jobs.get(), None
        batch = [job]
        group = job["m"].media_group_id if job["kind"] == "msg" else None
        while group:
            try:
                nxt = jobs.get(timeout=ALBUM_WAIT_SECONDS)
            except queue.Empty:
                break
            if nxt["kind"] == "msg" and nxt["m"].media_group_id == group and nxt["m"].chat.id == job["m"].chat.id:
                batch.append(nxt)
            else:
                pending = nxt
                break
        try:
            if job["kind"] == "stalled":  # hen gui lai cac tin xep hang khi muse loi
                run_stalled(job["key"])
            elif job["kind"] == "signup":
                signup(job["m"], job["user"])
            elif job["kind"] == "vip_intro":
                vip_intro(job["m"], job["u"])
            else:
                process(batch)
        except Exception as e:
            logger.exception("Loi xu ly tin")
            if job["kind"] == "stalled":
                schedule_stalled(job["key"])
                continue
            notify(f"⚠️ Loi xu ly tin {job['m'].message_id} tu {job['m'].chat.id}: {type(e).__name__}: {e}")


def enqueue(m, chat, text, kind="msg"):
    jobs.put({"kind": kind, "m": m, "chat": chat, "text": text})
    if kind == "msg":
        react(m, "👀")


def choose(c):
    """Bam nut cua Muse: khoa ban phim (chi con nut bao lua chon) va gui lua chon vao chat muse."""
    m = c.message
    chat = target_for(m, c.from_user)
    if chat is None:
        bot.answer_callback_query(c.id, "Chat này không còn kết nối với Muse.")
        return
    if chat.get("user") and quota_note(chat["user"]) is None:
        bot.answer_callback_query(c.id, quota_exhausted_text(), show_alert=True)
        return
    rows = m.reply_markup.keyboard if m.reply_markup else []
    label = next((b.text for row in rows for b in row if b.callback_data == c.data), c.data)
    bot.answer_callback_query(c.id, f"Đã gửi cho Muse: {label}")
    try:
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton(f"✅ {label}", callback_data=CHOSEN_DATA))
        bot.edit_message_reply_markup(m.chat.id, m.message_id, reply_markup=kb)
    except Exception:
        logger.exception("Khong khoa duoc ban phim")
    question = " ".join((m.text or m.caption or "").split())
    if len(question) > REPLY_QUOTE_MAX * 2:
        question = question[:REPLY_QUOTE_MAX * 2].rstrip() + "..."
    enqueue(m, chat, f'Tôi chọn "{label}" (trả lời tin: "{question}")', kind="tap")


# ---------- muse -> Telegram (relay) ----------

def relay(chat, m, seen):
    """Chuyen tra loi cua Muse trong chat muse ve chat Telegram cua tin m, giu "dang nhap..." cho toi khi Muse xong
    luot. seen = id cac tin da co truoc khi gui. Moi chat muse 1 luong; tin moi vao chat dang duoc theo doi thi nhap
    vao luong do (tra loi gui ve tin moi nhat)."""
    with relay_lock:
        r = relays.get(chat["key"])
        if r:
            r["targets"].append(m)
            r["since"] = time.time()
            return
        relays[chat["key"]] = r = {"targets": [m], "seen": set(seen), "since": time.time(), "user": chat.get("user"),
                                   "owner": chat.get("user") or chat.get("vip"), "waiting": {}, "reloaded": 0}
    threading.Thread(target=relay_loop, args=(chat, r), daemon=True).start()


def plain(html_text):
    return html.unescape(re.sub(r"<[^>]+>", "", html_text))


def html_chunks(text):
    """Chia HTML thanh cac phan <= 4000 ky tu theo doan (khong cat giua the). Doan qua dai: chuyen chu thuong."""
    chunks, cur = [], ""
    for block in text.split("\n\n"):
        if len(block) > 4000:
            if cur:
                chunks.append(cur)
                cur = ""
            raw = plain(block)
            chunks += [html.escape(raw[i:i + 3500]) for i in range(0, len(raw), 3500)]
        elif cur and len(cur) + 2 + len(block) > 4000:
            chunks.append(cur)
            cur = block
        else:
            cur = f"{cur}\n\n{block}" if cur else block
    return chunks + ([cur] if cur else [])


def send_text(target, text, kb=None, parse_mode="HTML"):
    """Gui tin (mac dinh HTML Telegram) ve chat cua target; Telegram tu choi HTML thi gui lai chu thuong."""
    chunks = html_chunks(text) if parse_mode == "HTML" else [text[i:i + 4000] for i in range(0, len(text), 4000)]
    for i, chunk in enumerate(chunks):
        args = dict(message_thread_id=topic_of(target), reply_markup=kb if i == len(chunks) - 1 else None,
                    link_preview_options=types.LinkPreviewOptions(is_disabled=True))
        try:
            bot.send_message(target.chat.id, chunk, parse_mode=parse_mode, **args)
        except ApiTelegramException as e:
            if parse_mode != "HTML" or e.error_code != 400:
                raise
            logger.info(f"Telegram tu choi HTML ({e}), gui chu thuong")
            bot.send_message(target.chat.id, plain(chunk), **args)


def send_media(target, kind, data, name, caption):
    """Gui anh/video/file (bytes trong RAM) ve chat cua target. Tra ve tin da gui, None neu file qua lon."""
    chat_id, topic = target.chat.id, topic_of(target)
    if len(data) > TG_UPLOAD_LIMIT:
        bot.send_message(chat_id, f"⚠️ {caption or name}: file {len(data) / 1048576:.0f} MB vượt giới hạn 50 MB của "
                                  f"Telegram, bot không gửi được.", message_thread_id=topic)
        return None

    def upload(send, **kw):
        # timeout mac dinh cua telebot (15s) khong du tai video vai chuc MB len; dut ket noi luc dang tai len
        # (ConnectionError) thi Telegram chua nhan file -> gui lai. Het gio doc tra loi thi khong gui lai (co the da toi).
        for attempt in range(MEDIA_UPLOAD_ATTEMPTS):
            try:
                return send(chat_id, types.InputFile(io.BytesIO(data), file_name=name), caption=caption,
                            message_thread_id=topic, timeout=MEDIA_UPLOAD_TIMEOUT, **kw)
            except requests.exceptions.ConnectionError as e:
                if attempt == MEDIA_UPLOAD_ATTEMPTS - 1:
                    raise
                logger.warning(f"Tai {name} len Telegram loi ({e}), thu lai")
    if kind == "video":
        return upload(bot.send_video, supports_streaming=True)
    if kind == "image":
        try:
            return upload(bot.send_photo)
        except ApiTelegramException as e:  # dinh dang Telegram khong nhan lam anh: gui dang file
            logger.info(f"send_photo {name}: {e}; gui dang file")
    return upload(bot.send_document)


def forward_to_admin(sent, owner, key, target):
    """Video Muse vua gui cho nguoi dung Free / VIP owner: chep them cho admin, kem ten nguoi dung va tin ho da gui."""
    if owner in ALLOWED_CHAT_IDS:  # admin tu dung (VIP thu): khong chuyen lai cho chinh minh
        return
    u = muse_users.get(owner) or {}
    asked = " ".join((getattr(target, "text", None) or getattr(target, "caption", None) or "").split())
    caption = (f"🎬 Video gửi cho {u.get('name') or owner}{' @' + u['username'] if u.get('username') else ''} "
               f"({owner}) · {'VIP' if muse_users.vip_active(u) else 'Free'} · {key}"
               + (f"\n💬 {asked[:700]}" if asked else ""))
    for chat_id in ALLOWED_CHAT_IDS:
        try:
            bot.copy_message(chat_id, sent.chat.id, sent.message_id, caption=caption[:1024])
        except Exception as e:
            logger.warning(f"Khong chuyen duoc video cua {owner} cho admin {chat_id}: {e}")


def send_reply(fox, msg, target, r, key, warned):
    """Gui 1 tin cua Muse (chu + nut bam + anh/video/file) ve chat Telegram cua target. r: luong relay/watch cua
    chat muse key (r["user"]: nguoi dung Free tinh quota, r["owner"]: nguoi dung Free / VIP de chuyen video cho admin)."""
    uid = r["user"]
    text, kb = msg.get("html") or html.escape(msg["text"]), None
    found = BUTTONS_RE.search(msg["text"])  # nhan nut lay tu chu thuong, xoa dong nut khoi ban HTML
    labels = msg.get("choices") or []  # khung nut chon cua chinh Muse (muse_sync.MESSAGES_JS)
    if found:
        labels = [x.strip() for x in found.group(1).split("|") if x.strip()]
        text = BUTTONS_RE.sub("", text).strip()
    if labels:
        text = text or "👇 Bạn chọn:"
        kb = types.InlineKeyboardMarkup()
        for i, label in enumerate(labels[:12]):
            kb.add(types.InlineKeyboardButton(label[:60], callback_data=f"mb:{i}"))
    if text:
        send_text(target, text, kb)
    for a in msg["media"]:
        kind = a["kind"] if a["kind"] in KIND_LABEL else "file"
        if uid and kind in KIND_LABEL and not muse_users.quota_left(uid)[kind]:
            if kind not in warned:
                warned.add(kind)
                send_text(target, f"⚠️ Hôm nay bạn đã dùng hết <b>{muse_users.FREE_DAILY[kind]} {KIND_LABEL[kind]}</b> "
                                  f"của gói Free, bot không gửi thêm {KIND_LABEL[kind]}. Nâng cấp VIP để không giới "
                                  f"hạn (/start).")
            continue
        title = re.sub(r"^Open (?:generated|animated) (?:image|video)\s*", "", a["title"]).strip()
        base = re.sub(r'[\\/:*?"<>|\s]+', "_", title)[:60] or f"muse_{kind}"
        if not a["src"] and a["kind"] != "file":  # VD audio: Muse chi co player rieng, trang khong co file / link tai duoc
            logger.info(f"{key}: khong tai duoc {a['kind']} {title!r} (lost={a.get('lost')})")
            if a["kind"] == "missing":  # khung "Video not found": file mat tren muse / sandbox cua Muse khong tra file
                why = ("Muse không còn file này (máy sandbox của Muse đã khởi động lại / xoá file)" if a.get("lost")
                       else f"Muse không nạp được file sau {MEDIA_MISSING_WAIT // 60} phút")
                send_text(target, f"📎 <b>{html.escape(title or base)}</b>: {why}. Nhắn Muse gửi lại hoặc tạo "
                                  f"link tải công khai.")
                continue
            send_text(target, f"{'🎵' if a['kind'] == 'audio' else '📎'} <b>{html.escape(title or base)}</b> "
                              f"({html.escape(a['kind'])}): bot không tải được file này, mở Muse để nghe / xem.")
            continue
        try:  # 1 file loi: bao rieng file do, gui tiep cac file con lai cua tin
            if a["kind"] == "file":  # file Muse tao trong sandbox (VD .md): doc qua khung xem file cua Muse
                text = muse_sync.fetch_file(fox, msg["id"], a.get("name") or "")
                if text is None:
                    raise ValueError("khung xem file cua Muse khong co noi dung chu")
                data, mime = text.encode("utf-8"), a.get("mime") or "text/plain"
            else:
                data, mime = muse_sync.fetch_media(fox, a["src"])
            if kind == "video" and not mime.startswith("video/"):  # lay nham poster: khong gui anh thanh video hong
                raise ValueError(f"tai ve {mime or 'rong'} ({len(data)} byte), khong phai video")
            name = re.sub(r'[\\/:*?"<>|\s]+', "_", a.get("name") or "") or base + (mimetypes.guess_extension(mime) or "")
            sent = send_media(target, kind, data, name, title[:1000] or None)
            del data  # anh/video chi nam trong RAM, khong ghi ra may
        except Exception as e:
            logger.exception(f"Khong chuyen duoc {kind} {title or a['src']} ve Telegram")
            try:
                send_text(target, f"⚠️ Không gửi được {KIND_LABEL.get(kind, 'file')} "
                                  f"<b>{html.escape(title or base)}</b>: {html.escape(type(e).__name__)}")
            except Exception:
                logger.exception("Khong bao duoc loi gui file")
            continue
        if uid:
            muse_users.add_usage(uid, kind)
        if sent and kind == "video" and r.get("owner"):
            forward_to_admin(sent, r["owner"], key, target)


def deliver_new(fox, chat, r, target, busy, warned):
    """Gui ve Telegram cac tin moi cua Muse da viet xong, theo thu tu. Tra ve True neu con tin dang viet / dang tai."""
    if chat["key"] in skill_holds:  # dang cai skill: cho xong, tin tra loi viec cai se duoc danh dau da chuyen
        return True
    for msg in muse_sync.messages(fox):
        if msg["role"] != "assistant" or msg["id"] in r["seen"]:
            continue
        if msg["streaming"]:
            return True
        loading = any(not a["src"] and a["kind"] in KIND_LABEL for a in msg["media"])
        # khung "not found" nhung Muse van giu file (may sandbox dang ngu): cho toi MEDIA_MISSING_WAIT roi moi bao mat
        unfound = any(a["kind"] == "missing" and not a.get("lost") for a in msg["media"])
        waited = time.time() - r["waiting"].setdefault(msg["id"], time.time()) if loading or unfound else 0
        if loading or unfound and waited < MEDIA_MISSING_WAIT:  # anh/video chua nap: ket lau thi tai lai trang
            if waited > MEDIA_RELOAD_SECONDS and time.time() - r["reloaded"] > MEDIA_RELOAD_GAP:
                logger.info(f"{chat['key']}: anh/video chua nap sau {waited:.0f}s, tai lai trang")
                r["reloaded"] = time.time()
                muse_sync.reload_chat(fox, chat["url"])
            return True
        if not msg["text"] and not msg["media"] and not msg.get("choices"):
            if busy:  # khung tin rong: Muse sap viet
                return True
            r["seen"].add(msg["id"])
            continue
        r["seen"].add(msg["id"])  # danh dau truoc khi gui: loi gui Telegram khong lam gui lap
        if not claim(chat["key"], msg["id"]):  # relay / watch da chuyen tin nay roi
            continue
        try:
            send_reply(fox, msg, target, r, chat["key"], warned)
        except Exception:
            logger.exception(f"Khong chuyen duoc tin {msg['id']} ve Telegram")
    return False


def relay_loop(chat, r):
    start, since, busy_seen, idle, errors = time.time(), None, False, 0, 0
    fox, error, warned = None, "", set()
    while True:
        time.sleep(RELAY_INTERVAL)
        now = time.time()
        with relay_lock:
            if r["since"] != since:  # co tin moi: Muse lai bat dau 1 luot moi
                since, busy_seen, idle = r["since"], False, 0
            target = r["targets"][-1]
        try:
            fox = fox or muse_sync.chat_browser(chat)
            busy = muse_sync.is_busy(fox)
            pending = deliver_new(fox, chat, r, target, busy, warned)
            errors = 0
        except Exception as e:
            busy, pending, errors, error = None, True, errors + 1, f"{type(e).__name__}: {e}"
            logger.warning(f"Relay {chat['key']}: {error}")
        if busy:
            busy_seen, idle = True, 0
        elif busy is False and not pending:
            idle += 1
        done = idle >= RELAY_IDLE_POLLS and (busy_seen or now - since >= RELAY_START_GRACE)
        if done or errors >= RELAY_MAX_ERRORS or now - start >= RELAY_MAX_SECONDS:
            with relay_lock:
                if r["since"] != since:  # tin moi vua toi: theo doi tiep
                    continue
                relays.pop(chat["key"], None)
                targets = list(r["targets"])
            break
        try:  # "dang nhap..." tu tat sau ~5s nen gui lai moi vong
            bot.send_chat_action(target.chat.id, "typing", message_thread_id=topic_of(target))
        except Exception as e:
            logger.debug(f"send_chat_action: {e}")
    minutes = int((time.time() - start) // 60)
    logger.info(f"{chat['key']}: Muse {'xong' if done else 'chua xong'} sau {time.time() - start:.0f}s "
                f"({len(targets)} tin)")
    for m in targets:
        try:
            if done:
                react(m, "👌")
            else:  # het gio / loi doc trang: bao 1 lan, ngung chuyen tiep
                why = "không đọc được trả lời của Muse" if errors else "Muse vẫn đang làm"
                bot.reply_to(m, f"⏳ {why} sau {minutes} phút, bot ngừng chờ. Nhắn tiếp để tiếp tục nhé.")
                if errors:
                    notify(f"⚠️ Relay {chat['key']} loi: {error}")
        except Exception:
            logger.exception("Khong bao duoc trang thai")
    if chat["url"] != muse_sync.MUSE_URL and not chat["tg"]:  # side chat xong viec: dong tab (da map: watch can)
        with relay_lock:
            busy_again = chat["key"] in relays
        if not busy_again:
            try:
                muse_sync.close_tab(chat["profile"], chat["url"])
            except Exception as e:
                logger.debug(f"Dong tab {chat['url']}: {e}")


def claim(key, mid):
    """Ghi nhan tin mid cua Muse trong chat muse key da chuyen ve Telegram. False neu da chuyen roi: relay va watch
    dung chung, tin chi di 1 lan."""
    def add(state):
        ids = state.setdefault("delivered", {}).setdefault(key, [])
        if mid in ids:
            return False
        ids.append(mid)
        del ids[:-DELIVERED_KEEP]
        return True
    return update_state(add)


# ---------- muse -> Telegram (watch: chat da map) ----------

def tg_target(tg):
    """Gia tri map "<chat id>" / "<chat id>/<topic id>" -> target cho send_text / send_media (nhu 1 tin Telegram)."""
    chat_id, _, topic = tg.partition("/")
    return SimpleNamespace(chat=SimpleNamespace(id=int(chat_id)), message_thread_id=int(topic) if topic else None,
                           is_topic_message=bool(topic))


def watch_chat(chat, r, tabs):
    """1 vong watch cho 1 chat muse da map. tabs: profile -> URL cac tab dang mo (None: profile chua mo), hoi
    FoxProfile 1 lan moi vong."""
    profile = chat["profile"]
    fox = muse_sync.FoxProfileBrowser(profile, log=logger.info)
    if profile not in tabs:
        tabs[profile] = [t["url"] for t in fox.tabs()] if fox.is_running() else None
    if tabs[profile] is None:  # profile chua mo: khong tu mo; mo lai thi vong sau gui bu
        return
    if not any(muse_sync.same_url(u, chat["url"]) for u in tabs[profile]):
        with muse_sync.lock:
            fox.open_tab(chat["url"])  # tab chat da dong (side chat): mo lai va giu mo de doc tin moi
        tabs[profile].append(chat["url"])
    fox.tab = chat["url"]
    if chat["key"] not in load_state().get("watched", []):  # chat moi map: tin dang co coi nhu da chuyen
        ids = [m["id"] for m in muse_sync.messages(fox) if m["role"] == "assistant"]

        def start(state):
            known = state.setdefault("delivered", {}).setdefault(chat["key"], [])
            known += [i for i in ids if i not in known]
            del known[:-DELIVERED_KEEP]
            state.setdefault("watched", []).append(chat["key"])
        update_state(start)
        r["seen"].update(ids)
        logger.info(f"Watch {chat['key']} -> Telegram {chat['tg']}")
        return
    deliver_new(fox, chat, r, tg_target(chat["tg"]), muse_sync.is_busy(fox), set())


def watch_loop():
    """Moi WATCH_INTERVAL giay chuyen ve chat/topic Telegram da map cac tin moi cua Muse trong cac chat muse da map.
    Chat dang co relay (vua nhan tin Telegram) thi de relay chuyen."""
    runs = {}  # key chat muse -> r cua deliver_new
    errors = {}  # key chat muse -> loi gan nhat (chi ghi log khi loi doi)
    hung = {}  # profile -> luc bat dau doc timeout lien tuc (trinh duyet treo)
    while True:
        time.sleep(WATCH_INTERVAL)
        try:
            chats = [c for c in muse_sync.muse_chats() if c["tg"]]
            keys = {c["key"] for c in chats}
            if any(k not in keys for k in load_state().get("watched", [])):  # bo map: map lai thi khong gui tin cu
                update_state(lambda state: state.__setitem__("watched", [k for k in state["watched"] if k in keys]))
        except Exception:
            logger.exception("Watch: khong doc duoc muse_sync.json")
            continue
        tabs = {}
        for chat in chats:
            with relay_lock:
                if chat["key"] in relays:
                    continue
            r = runs.setdefault(chat["key"], {"seen": set(), "user": None, "waiting": {}, "reloaded": 0, "retry": 0})
            if time.time() < r["retry"]:
                continue
            try:
                watch_chat(chat, r, tabs)
                errors.pop(chat["key"], None)
                hung.pop(chat["profile"], None)
            except Exception as e:
                r["retry"] = time.time() + WATCH_RETRY_SECONDS
                error = f"{type(e).__name__}: {e}"
                if errors.get(chat["key"]) != error:
                    logger.warning(f"Watch {chat['key']}: {error}")
                errors[chat["key"]] = error
                if is_hang(e):
                    since = hung.setdefault(chat["profile"], time.time())
                    if time.time() - since >= WATCH_HANG_SECONDS and muse_sync.can_restart(chat["profile"]):
                        hung.pop(chat["profile"], None)
                        recover(chat["profile"], error)


def is_hang(e):
    """Loi kieu trinh duyet / FoxProfile treo: het gio doc, trinh duyet khong tra loi. (Khong tinh: FoxProfile tat,
    chua dang nhap -- khoi dong lai trinh duyet khong chua duoc.)"""
    text = str(e).lower()
    return isinstance(e, muse_sync.FoxError) and (e.status == 504 or "timeout" in text or "timed out" in text)


def recover(profile, why):
    """Khoi dong lai trinh duyet treo cua profile (watch thay doc timeout lien tuc)."""
    try:
        with muse_sync.lock:
            muse_sync.restart_profile(profile, why)
        notify(f"🔄 Trinh duyet {profile} treo (doc trang timeout > {WATCH_HANG_SECONDS // 60} phut), da khoi dong lai.")
    except Exception as e:
        logger.exception(f"Khong khoi dong lai duoc {profile}")
        notify(f"⚠️ Trinh duyet {profile} treo, khoi dong lai loi: {type(e).__name__}: {e}")


# ---------- Free ----------

def money(amount):
    return f"{amount:,}".replace(",", ".") + "đ"


def start_text(user):
    """Menu nguoi dung (HTML): goi dang dung, Free, VIP + nut."""
    u = muse_users.touch(user)
    d = muse_users.FREE_DAILY
    lines = [f"👋 <b>Xin chào {html.escape(muse_users.display_name(user))}!</b>",
             "Bot giúp bạn làm việc với <b>Muse AI</b> ngay trên Telegram: trò chuyện, tạo ảnh, video và nhiều việc "
             "khác.", ""]
    kb = types.InlineKeyboardMarkup()
    vip, free = muse_users.vip_active(u), muse_users.free_active(u)
    free_slots = f"<b>{muse_users.slots_left()}/{len(muse_users.FREE_PROFILES) * muse_users.FREE_PER_PROFILE}</b>"
    vip_left, vip_total = muse_users.vip_slots()
    vip_slots = f"<b>{vip_left}/{vip_total}</b>"

    lines.append("💎 <b>Gói VIP</b> · " + ("đang dùng" if vip else "từ " + money(min(muse_users.VIP_PRICES.values()))
                                           + "/ngày, 30 ngày chỉ " + money(muse_users.VIP_PRICES[30])))
    lines += ["• Tài khoản Muse <b>riêng</b> cho bạn: phản hồi nhanh, nhớ được nhiều thông tin và lịch sử làm việc",
              "• Không giới hạn ảnh/video, chat trực tiếp hoặc theo từng topic trong nhóm"]
    if vip:
        lines += [f"• Hết hạn: <b>{muse_users.fmt_time(u['vip_until'])}</b>",
                  f"• Chế độ: <b>{VIP_MODES.get(u['vip_mode'], 'chưa chọn')}</b>"]
        kb.row(types.InlineKeyboardButton("💎 Gia hạn VIP", callback_data="vip:buy"),
               types.InlineKeyboardButton("🔁 Đổi chế độ", callback_data="vip:modes"))
    else:
        lines.append(f"• Còn {vip_slots} suất")
        if muse_users.vip_profile_for(user.id):
            kb.add(types.InlineKeyboardButton("💎 Mua VIP", callback_data="vip:buy"))
        else:
            lines.append("<i>VIP tạm hết chỗ, bạn quay lại sau nhé.</i>")

    if muse_users.FREE_ENABLED:  # Free tam dung: an han muc Free
        lines += ["", "🎁 <b>Gói Free</b> · " + ("đang dùng" if free else "miễn phí"),
                  "• Dùng <b>chung</b> tài khoản Muse với người khác: nhớ ít ngữ cảnh hơn, phản hồi chậm hơn một chút",
                  f"• Dùng {muse_users.FREE_DAYS} ngày, mỗi ngày {d['video']} video + {d['image']} ảnh"]
        if free:
            used = muse_users.usage(user.id)
            lines += [f"• Hết hạn: <b>{muse_users.fmt_time(u['free_end'])}</b>",
                      f"• Hôm nay: <b>{used['video']}/{d['video']}</b> video · <b>{used['image']}/{d['image']}</b> ảnh"]
        else:
            lines.append(f"• Còn {free_slots} suất")
            reason = None if vip else muse_users.free_block_reason(u)
            if reason:
                lines.append(f"<i>{html.escape(reason)}</i>")
            elif not vip:
                kb.add(types.InlineKeyboardButton("🎁 Dùng thử Free", callback_data="free:ask"))
    if vip or free:
        lines += ["", "💬 Cứ nhắn tin hoặc gửi ảnh, file vào đây để làm việc với Muse."]
    lines += ["", "❓ Cần hỗ trợ? Gõ <code>/hoi câu hỏi của bạn</code> để hỏi admin."]
    return "\n".join(lines), kb


def mode_keyboard():
    kb = types.InlineKeyboardMarkup()
    kb.row(*[types.InlineKeyboardButton(("💬 " if mode == "direct" else "👥 ") + label,
                                        callback_data=f"vip:mode:{mode}") for mode, label in VIP_MODES.items()])
    return kb


MODES_TEXT = ("🔁 <b>Chọn cách dùng VIP</b>\n"
              "• 💬 <b>Chat trực tiếp</b>: nhắn ngay trong chat này\n"
              "• 👥 <b>Group topic</b>: mỗi topic trong nhóm của bạn là 1 chat riêng với Muse")
GROUP_HELP = ("👥 <b>Chế độ Group topic</b>\n\n"
              "1. Tạo nhóm Telegram, bật <b>Chủ đề (Topics)</b> trong cài đặt nhóm\n"
              "2. Thêm @{bot} vào nhóm và cấp quyền admin\n"
              "3. Gõ /vipgroup trong nhóm\n\n"
              "• <b>General</b>: chat chính với Muse\n"
              "• <b>Mỗi topic</b>: 1 chat riêng với Muse, tạo khi bạn nhắn tin đầu tiên trong topic\n"
              "• Chat riêng với bot vẫn vào chat chính")


def vip_callback(c, args):
    m, user = c.message, c.from_user
    u = muse_users.touch(user)
    action = args[0] if args else ""
    if action == "buy":
        if not muse_users.vip_profile_for(user.id):
            bot.answer_callback_query(c.id, "VIP tạm hết chỗ, bạn quay lại sau nhé.", show_alert=True)
            return
        kb = types.InlineKeyboardMarkup()
        buttons = [types.InlineKeyboardButton(f"{d} ngày · {money(price)}", callback_data=f"vip:days:{d}")
                   for d, price in muse_users.VIP_PRICES.items()]
        for i in range(0, len(buttons), 2):
            kb.row(*buttons[i:i + 2])
        bot.answer_callback_query(c.id)
        bot.send_message(m.chat.id, "💎 <b>Chọn thời gian VIP</b>\n"
                                    "Tài khoản Muse riêng cho bạn: phản hồi nhanh, nhớ được nhiều thông tin, không giới "
                                    "hạn ảnh/video.",
                         parse_mode="HTML", reply_markup=kb)
    elif action == "days":
        days = int(args[1])
        if days not in muse_users.VIP_PRICES:  # nut cu tu bang gia truoc
            bot.answer_callback_query(c.id, "Gói này không còn, bạn chọn lại nhé (/start).", show_alert=True)
            return
        pid = muse_users.new_payment(user.id, days)
        amount, info, bank = muse_users.VIP_PRICES[days], f"MUSE{pid}", muse_users.VIP_BANK
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("✅ Tôi đã chuyển khoản", callback_data=f"vip:paid:{pid}"))
        caption = (f"💎 <b>VIP {days} ngày</b> · <b>{money(amount)}</b>\n\n"
                   f"🏦 Ngân hàng: <b>{bank['bank']}</b>\n"
                   f"💳 Số tài khoản: <code>{bank['account']}</code>\n"
                   f"📝 Nội dung: <code>{info}</code>\n\n"
                   f"Quét mã QR hoặc chuyển khoản theo thông tin trên, xong bấm <b>Tôi đã chuyển khoản</b> để admin "
                   f"duyệt.")
        bot.answer_callback_query(c.id)
        try:
            qr = vietqr.png(bank["bank"], bank["account"], amount, info)
            bot.send_photo(m.chat.id, types.InputFile(io.BytesIO(qr), file_name=f"{info}.png"), caption=caption,
                           parse_mode="HTML", reply_markup=kb)
        except Exception as e:  # khong tao / gui duoc anh QR: gui chu
            logger.warning(f"Gui QR loi: {e}")
            bot.send_message(m.chat.id, caption, parse_mode="HTML", reply_markup=kb)
        bot.edit_message_reply_markup(m.chat.id, m.message_id, reply_markup=None)
    elif action == "paid":
        pid = int(args[1])
        pay = muse_users.payment(pid)
        if not pay or pay["user_id"] != user.id or not muse_users.set_payment_status(pid, "claimed", ("new",)):
            bot.answer_callback_query(c.id, "Yêu cầu này đã được gửi rồi.")
            return
        bot.answer_callback_query(c.id, "Đã gửi yêu cầu duyệt cho admin.")
        bot.edit_message_reply_markup(m.chat.id, m.message_id, reply_markup=None)
        bot.send_message(m.chat.id, "⏳ <b>Đã gửi yêu cầu duyệt</b>\nAdmin sẽ kiểm tra chuyển khoản và kích hoạt VIP cho "
                                    "bạn sớm nhất.", parse_mode="HTML")
        kb = types.InlineKeyboardMarkup()
        kb.row(types.InlineKeyboardButton(f"✅ Duyệt {pay['days']} ngày", callback_data=f"vipok:{pid}"),
               types.InlineKeyboardButton("❌ Từ chối", callback_data=f"vipno:{pid}"))
        text = (f"💎 Yêu cầu VIP #{pid}\n"
                f"• Người dùng: {u['name']}{' @' + u['username'] if u['username'] else ''} ({user.id})\n"
                f"• Gói: {pay['days']} ngày = {money(pay['amount'])}\n"
                f"• Nội dung chuyển khoản: MUSE{pid}")
        for admin in ALLOWED_CHAT_IDS:
            bot.send_message(admin, text, reply_markup=kb)
    elif action == "modes":
        bot.answer_callback_query(c.id)
        bot.send_message(m.chat.id, MODES_TEXT, parse_mode="HTML", reply_markup=mode_keyboard())
    elif action == "mode" and muse_users.vip_active(u):
        mode = args[1]
        muse_users.set_vip_mode(user.id, mode)
        bot.answer_callback_query(c.id, f"Đã chọn {VIP_MODES[mode]}")
        bot.edit_message_reply_markup(m.chat.id, m.message_id, reply_markup=None)
        if mode == "group":
            bot.send_message(m.chat.id, GROUP_HELP.format(bot=bot.get_me().username), parse_mode="HTML")
        else:
            bot.send_message(m.chat.id, "💬 <b>Chế độ Chat trực tiếp</b>\nCứ nhắn tin, gửi ảnh hay file vào đây để làm "
                                        "việc với Muse riêng của bạn.", parse_mode="HTML")
    else:
        bot.answer_callback_query(c.id, "VIP của bạn chưa kích hoạt hoặc đã hết hạn.")


def approve_vip(c, pid, ok):
    """Admin duyet / tu choi yeu cau VIP pid."""
    m = c.message
    pay = muse_users.payment(pid)
    if not pay or not muse_users.set_payment_status(pid, "approved" if ok else "rejected", ("new", "claimed")):
        bot.answer_callback_query(c.id, "Yêu cầu đã được xử lý rồi.")
        return
    if not ok:
        bot.answer_callback_query(c.id, "Đã từ chối.")
        bot.edit_message_text(m.text + "\n❌ Đã từ chối", m.chat.id, m.message_id)
        bot.send_message(pay["user_id"], f"❌ <b>Yêu cầu VIP #{pid} chưa được duyệt</b>\nCó gì thắc mắc bạn nhắn admin "
                                         f"nhé.", parse_mode="HTML")
        return
    u = grant(pay["user_id"], pay["days"])
    if not u:
        muse_users.set_payment_status(pid, "claimed")
        bot.answer_callback_query(c.id, "Hết profile VIP để giao!", show_alert=True)
        return
    bot.answer_callback_query(c.id, "Đã duyệt.")
    bot.edit_message_text(m.text + f"\n✅ Đã duyệt, VIP đến {muse_users.fmt_time(u['vip_until'])}", m.chat.id,
                          m.message_id)


def grant(uid, days):
    """Cong VIP va bao nguoi dung; profile moi giao thi gioi thieu voi Muse. Tra ve ban ghi, None neu het profile."""
    u, new = muse_users.grant_vip(uid, days)
    if not u:
        return None
    logger.info(f"VIP {u['name']} ({uid}) +{days} ngay -> {u['vip_profile']} den {muse_users.fmt_time(u['vip_until'])}")
    try:
        text = f"💎 <b>VIP đã kích hoạt!</b>\nHết hạn: <b>{muse_users.fmt_time(u['vip_until'])}</b>"
        if not u["vip_mode"]:
            text += "\n\n" + MODES_TEXT
        msg = bot.send_message(uid, text, parse_mode="HTML",
                               reply_markup=mode_keyboard() if not u["vip_mode"] else None)
        if new:
            jobs.put({"kind": "vip_intro", "m": msg, "u": u, "chat": None, "text": ""})
    except Exception as e:
        logger.warning(f"Bao VIP cho {uid} loi: {e}")
    return u


def free_callback(c, action):
    m, user = c.message, c.from_user
    u = muse_users.touch(user)
    if action == "ask":
        reason = muse_users.free_block_reason(u)
        if reason:
            bot.answer_callback_query(c.id, reason, show_alert=True)
            return
        d = muse_users.FREE_DAILY
        kb = types.InlineKeyboardMarkup()
        kb.row(types.InlineKeyboardButton("✅ Xác nhận", callback_data="free:ok"),
               types.InlineKeyboardButton("Huỷ", callback_data="free:no"))
        bot.answer_callback_query(c.id)
        bot.edit_message_text(
            f"🎁 <b>Xác nhận dùng gói Free?</b>\n\n"
            f"• Dùng <b>{muse_users.FREE_DAYS} ngày</b>, mỗi ngày <b>{d['video']} video</b> + "
            f"<b>{d['image']} ảnh</b>\n"
            f"• Muse có 1 chat riêng cho bạn và sẽ gọi bạn là <b>{html.escape(muse_users.display_name(user))}</b>\n"
            f"• Dùng <b>chung</b> tài khoản Muse với người khác: nhớ ít ngữ cảnh hơn, phản hồi chậm hơn VIP một chút\n"
            f"• Hết hạn thì chat riêng bị xoá, <b>{muse_users.FREE_COOLDOWN_DAYS} ngày</b> sau mới đăng ký lại được",
            m.chat.id, m.message_id, parse_mode="HTML", reply_markup=kb)
    elif action == "no":
        bot.answer_callback_query(c.id, "Đã huỷ.")
        text, kb = start_text(user)
        bot.edit_message_text(text, m.chat.id, m.message_id, parse_mode="HTML", reply_markup=kb)
    elif action == "ok":
        reason = muse_users.free_block_reason(u)
        profile = None if reason else muse_users.reserve_free(user.id)
        if not profile:
            bot.answer_callback_query(c.id, reason or "Hiện đã hết suất Free.", show_alert=True)
            return
        bot.answer_callback_query(c.id, "Đang tạo chat riêng...")
        bot.edit_message_text("⏳ Đang tạo chat riêng với Muse cho bạn...", m.chat.id, m.message_id)
        jobs.put({"kind": "signup", "m": m, "user": user, "chat": None, "text": ""})


def expiry_loop():
    """Free het han: xoa side chat, tra suat ve pool. VIP het han: reset Muse cua profile, tra profile ve pool.
    Bao nguoi dung. Loi thi thu lai o vong sau."""
    while True:
        for u in muse_users.expired_free():
            try:
                muse_sync.delete_side_chat(u["free_profile"], u["free_thread"])
            except Exception as e:
                logger.warning(f"Xoa side chat Free {u['free_profile']}/{u['free_thread']} ({u['id']}): {e}")
                continue
            muse_users.release_free(u["id"])
            u = muse_users.get(u["id"])
            if muse_users.vip_active(u):  # len VIP: tra suat Free, khong bao "het han"
                logger.info(f"Free -> VIP: {u['name']} ({u['id']}), da xoa side chat Free, tra suat ve pool")
                continue
            logger.info(f"Free het han: {u['name']} ({u['id']}), da xoa side chat")
            text = (f"⏰ <b>Gói Free đã hết hạn</b>\nChat riêng với Muse đã được xoá. Bạn có thể đăng ký lại từ "
                    f"<b>{muse_users.fmt_time(u['free_cooldown_until'])}</b>, hoặc nâng cấp VIP để dùng tiếp ngay (/start)."
                    if muse_users.FREE_ENABLED else
                    "⏸ <b>Gói Free đã tạm dừng</b>\nChat riêng với Muse đã được xoá. Nâng cấp VIP để dùng tiếp (/start).")
            try:
                bot.send_message(u["id"], text, parse_mode="HTML")
            except Exception as e:
                logger.info(f"Khong bao duoc het han cho {u['id']}: {e}")
        for u in muse_users.vip_expired():  # VIP het han: reset Muse cua profile roi tra profile ve pool
            try:
                muse_sync.reset_muse(u["vip_profile"])
            except Exception as e:
                logger.warning(f"Reset Muse {u['vip_profile']} (VIP {u['id']} het han): {e}")
                continue
            install_skills([u["vip_profile"]])  # cai vao main chat truoc khi tra profile: VIP moi chua kip vao
            muse_users.release_vip(u["id"])
            logger.info(f"VIP het han: {u['name']} ({u['id']}), da reset Muse {u['vip_profile']} va cai lai skill")
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("💎 Gia hạn VIP", callback_data="vip:buy"))
            try:
                bot.send_message(u["id"], "⏰ <b>VIP đã hết hạn</b>\nMuse riêng của bạn đã được xoá dữ liệu. Gia hạn để "
                                          "dùng tiếp với một Muse mới.", parse_mode="HTML", reply_markup=kb)
            except Exception as e:
                logger.info(f"Khong bao duoc het han VIP cho {u['id']}: {e}")
        time.sleep(EXPIRY_CHECK_SECONDS)


def sync_admin_topics():
    """Profile FoxProfile ten Muse* chua map: tao topic cung ten trong nhom admin ("admin_group" trong muse_sync.json)
    va map main chat cua profile vao topic do."""
    cfg = muse_sync.load_config()
    group = str(cfg.get("admin_group") or "").strip()
    if not group:
        return
    mapped = {p for p, tg in (cfg.get("channels") or {}).items() if str(tg or "").strip()}
    for profile in muse_sync.fox_profiles():
        if not profile.startswith(ADMIN_PROFILE_PREFIX) or profile in mapped:
            continue
        topic = bot.create_forum_topic(int(group), profile).message_thread_id
        muse_sync.map_tg(profile, f"{group}/{topic}")
        logger.info(f"Profile {profile} -> topic {group}/{topic} trong nhom admin")
        notify(f"🆕 Profile {profile}: da tao topic {profile} trong nhom admin va map vao main chat.")


def admin_topics_loop():
    while True:
        try:
            sync_admin_topics()
        except Exception as e:  # FoxProfile tat, bot thieu quyen quan ly topic...: thu lai vong sau
            logger.warning(f"Tu map profile Muse* vao topic admin loi: {type(e).__name__}: {e}")
        time.sleep(ADMIN_TOPICS_CHECK_SECONDS)


def install_skills(profiles, report_chat=None):
    """Cai lai skill (skills\\) vao main chat cua tung profile, lan luot; bao ket qua cho report_chat (mac dinh: moi
    admin). Trong luc cai giu khong chuyen tin main chat (VIP, topic da map); tin Muse tra loi viec cai khong gui ai."""
    skills_cancel.clear()  # /skills stop cu (ke ca khi luc do khong co gi dang cai) khong chan lan cai nay
    for i, profile in enumerate(profiles):
        if skills_cancel.is_set():
            text = f"⏹ Da dung cai skill, bo qua: {', '.join(profiles[i:])}"
            bot.send_message(report_chat, text) if report_chat else notify(text)
            return
        skill_holds.add(profile)
        try:
            ok, result, ids = muse_skills.install(profile, UPLOAD_DIR, skills_cancel)
            for mid in ids:
                claim(profile, mid)
        except Exception as e:
            logger.exception(f"Cai skill {profile} loi")
            ok, result = False, f"{type(e).__name__}: {e}"
        finally:
            skill_holds.discard(profile)
        logger.info(f"Cai skill {profile}: {'xong' if ok else 'loi'} {result[:300]}")
        text = f"{'🧩' if ok else '⚠️'} Cai skill {profile}: {'xong' if ok else 'loi'}\n{result[:3500]}"
        if report_chat:
            bot.send_message(report_chat, text)
        else:
            notify(text)


def clean_upload_dir():
    """Xoa file tam con sot trong UPLOAD_DIR (bot tat giua luc upload): thu muc <chat id>_<msg id> va skills_*."""
    for p in UPLOAD_DIR.iterdir():
        if p.is_dir() and re.fullmatch(r"-?\d+_\d+|skills_.+", p.name):
            shutil.rmtree(p, ignore_errors=True)
            logger.info(f"Xoa file tam con sot: {p}")


# ---------- admin ----------

def stats_text():
    s = muse_users.stats()
    total = len(muse_users.FREE_PROFILES) * muse_users.FREE_PER_PROFILE
    lines = ["📊 Thống kê",
             f"Người dùng: {s['users']} (hoạt động 7 ngày: {s['active_7d']}, đã chặn bot: {s['blocked']})",
             f"Free đang dùng: {len(s['free_active'])}, còn {s['slots_left']}/{total} suất",
             "  " + ", ".join(f"{p}: {n}/{muse_users.FREE_PER_PROFILE}" for p, n in s["slots"].items()),
             f"Đang chờ đăng ký lại: {s['cooldown']}",
             f"Hôm nay: {sum(r['video'] for r in s['today'])} video, {sum(r['image'] for r in s['today'])} ảnh"]
    lines += [f"  {r['name'] or r['user_id']}: {r['video']} video, {r['image']} ảnh" for r in s["today"][:5]]
    if s["free_active"]:
        lines.append("Free:")
        lines += [f"  {u['name']}{' @' + u['username'] if u['username'] else ''} ({u['id']}) {u['free_profile']}, "
                  f"hết hạn {muse_users.fmt_time(u['free_end'])}" for u in s["free_active"][:30]]
    lines.append(f"VIP ({len(s['vip'])}/{len(muse_users.vip_profiles())} profile đã giao):")
    lines += [f"  {u['name']} ({u['id']}) {u['vip_profile']}, {VIP_MODES.get(u['vip_mode'], 'chưa chọn chế độ')}, "
              f"{'đến' if muse_users.vip_active(u) else 'hết hạn'} {muse_users.fmt_time(u['vip_until'])}"
              for u in s["vip"]] or ["  (chưa có)"]
    if s["payments"]:
        lines.append("Thanh toán VIP: " + ", ".join(f"{p['status']} {p['n']} ({(p['total'] or 0):,}đ)"
                                                     for p in s["payments"]))
    return "\n".join(lines)


def run_broadcast(source, report_chat):
    ok = blocked = failed = 0
    for uid in muse_users.broadcast_ids():
        try:
            if "text" in source:
                bot.send_message(uid, source["text"])
            else:
                bot.copy_message(uid, source["from_chat"], source["message_id"])
            ok += 1
        except ApiTelegramException as e:
            if e.error_code == 403:
                muse_users.set_blocked(uid)
                blocked += 1
            else:
                failed += 1
                logger.warning(f"Quang ba toi {uid}: {e}")
        except Exception as e:
            failed += 1
            logger.warning(f"Quang ba toi {uid}: {e}")
        time.sleep(0.05)  # Bot API ~30 tin/giay
    logger.info(f"Quang ba: {ok} ok, {blocked} chan, {failed} loi")
    bot.send_message(report_chat, f"📣 Quảng bá xong: {ok} người nhận, {blocked} đã chặn bot, {failed} lỗi.")


# ---------- hoi admin ----------
# Cau hoi chuyen cho admin mang user id o dong dau: admin reply tin do la tra loi duoc, khong can luu trang thai
# (bot restart van reply duoc). Tin tra loi bat dau bang ANSWER_HEAD: nguoi dung reply tin do la hoi tiep.

ASK_RE = re.compile(r"❓ Câu hỏi từ .*\((\d+)\)")
ANSWER_HEAD = "💬 Admin trả lời"


def replied_text(m):
    r = m.reply_to_message
    return (r.text or r.caption or "") if r and r.from_user and r.from_user.is_bot else ""


def is_admin_answer(m):
    """Admin reply tin cau hoi cua nguoi dung."""
    return sender_authorized(m) and not (m.text or "").startswith("/") and bool(ASK_RE.match(replied_text(m)))


def is_follow_up(m):
    """Nguoi dung reply tin tra loi cua admin: hoi tiep (khong chuyen vao Muse)."""
    return not sender_authorized(m) and m.chat.type == "private" and replied_text(m).startswith(ANSWER_HEAD)


def ask_admin(m, question):
    """Chuyen cau hoi cua nguoi dung cho admin (tin co anh / file: chep ca file, cau hoi vao caption)."""
    u = muse_users.touch(m.from_user)
    plan = "VIP" if muse_users.vip_active(u) else "Free" if muse_users.free_active(u) else "chưa có gói"
    head = f"❓ Câu hỏi từ {u['name']}{' @' + u['username'] if u['username'] else ''} ({u['id']}) · {plan}"
    sent = 0
    for chat_id in ALLOWED_CHAT_IDS:
        try:
            if m.content_type == "text":
                bot.send_message(chat_id, f"{head}\n\n{question[:3500]}\n\n↩️ Reply tin này để trả lời.")
            else:
                bot.copy_message(chat_id, m.chat.id, m.message_id,
                                 caption=f"{head}\n\n{question[:800]}\n\n↩️ Reply tin này để trả lời.")
            sent += 1
        except Exception:
            logger.exception(f"Khong chuyen duoc cau hoi cua {u['id']} cho admin {chat_id}")
    logger.info(f"Cau hoi tu {u['id']} -> {sent} admin")
    bot.reply_to(m, "✅ Đã gửi câu hỏi cho admin. Câu trả lời sẽ được gửi vào đây." if sent
                 else "⚠️ Chưa gửi được câu hỏi cho admin, bạn thử lại sau nhé.")


def answer_user(m):
    """Chuyen tin admin reply (chu / anh / video / file) ve nguoi dung hoi."""
    uid = int(ASK_RE.match(replied_text(m)).group(1))
    u = muse_users.get(uid) or {"name": str(uid)}
    head = f"<b>{ANSWER_HEAD}:</b>\n\n"
    hint = "\n\n<i>↩️ Reply tin này hoặc gõ /hoi để hỏi tiếp.</i>"
    try:
        if m.content_type == "text":
            bot.send_message(uid, head + html.escape(m.text) + hint, parse_mode="HTML")
        else:  # anh / video / file: giu nguyen file, chen tieu de vao caption
            bot.copy_message(uid, m.chat.id, m.message_id, caption=head + html.escape(m.caption or "")[:800] + hint,
                             parse_mode="HTML")
    except ApiTelegramException as e:
        if e.error_code == 403:
            muse_users.set_blocked(uid)
        bot.reply_to(m, f"⚠️ Không gửi được cho {u['name']} ({uid}): {e.description}")
        return
    bot.reply_to(m, f"✅ Đã trả lời {u['name']} ({uid}).")


# ---------- bot ----------

def menu_text():
    lines = ["Gui tin/anh/video/file vao day -> bot chuyen vao chat muse dang chon, tra loi cua Muse duoc chuyen ve.",
             "/to - chon chat muse nhan tin (gui trong nhom/topic: map nhom/topic do vao chat muse)",
             "/<profile> <noi dung> - gui thang vao main chat cua profile (" +
             ", ".join(f"/{c}" for c in profile_commands()) + ")",
             "/stats - thong ke nguoi dung",
             "/log [user id] [so tin] - xem tin nguoi dung Free / VIP da gui vao Muse",
             "/skills <profile> | all - cai lai skill (thu muc skills) len profile; /skills stop - dung",
             "/vip <user id> <so ngay> - cap / gia han VIP (0 = ket thuc); /vip - danh sach VIP",
             "/me - xem menu nguoi dung (Free / mua VIP) nhu nguoi dung thuong",
             "/broadcast <noi dung> (hoac reply 1 tin bang /broadcast) - quang ba toi moi nguoi dung",
             "Nguoi dung /hoi <cau hoi> -> bot gui tin '❓ Câu hỏi từ ...' cho admin: reply tin do de tra loi",
             "/approve_on, /approve_off, /approve - bat/tat/xem tu dong bam Allow tren muse.ai",
             "/id - xem chat id (va topic id) cua chat nay", "",
             "Kenh/nhom map trong muse_sync.json:"]
    lines += [f"  {c['tg']} -> {c['key']}" for c in muse_sync.muse_chats() if c["tg"]] or ["  (chua co)"]
    return "\n".join(lines)


def set_command_descriptions():
    admin = [("to", "Chon chat muse nhan tin"), ("stats", "Thong ke nguoi dung"),
             ("log", "Xem tin nguoi dung da gui"), ("skills", "Cai lai skill len profile"),
             ("vip", "Cap / xem VIP"), ("me", "Menu nguoi dung (Free / VIP)"),
             ("broadcast", "Quang ba toi moi nguoi dung"), ("approve_on", "Bat tu dong bam Allow tren muse.ai"),
             ("approve_off", "Tat tu dong bam Allow tren muse.ai"), ("approve", "Xem trang thai auto Allow"),
             ("id", "Xem chat id / topic id"), ("help", "Huong dan")]
    admin += [(c, f"Gui vao main chat muse.ai ({p})") for c, p in profile_commands().items()]
    try:
        bot.set_my_commands([types.BotCommand("start", "Bắt đầu / xem gói đang dùng"),
                             types.BotCommand("hoi", "Hỏi admin"),
                             types.BotCommand("vipgroup", "VIP: gắn nhóm này với Muse của bạn")])
        for chat_id in ALLOWED_CHAT_IDS:
            bot.set_my_commands([types.BotCommand(c, d) for c, d in admin],
                                scope=types.BotCommandScopeChat(chat_id))
    except Exception:
        logger.exception("Khong set duoc command description")


def sender_authorized(m):
    """Chat duoc phep, hoac (trong nhom/topic) nguoi gui la chat rieng duoc phep."""
    return authorized(m.chat.id) or bool(m.from_user and authorized(m.from_user.id))


def tg_key(m):
    """Gia tri map chat Telegram cua tin m trong muse_sync.json: "<chat id>" hoac "<chat id>/<topic id>"."""
    topic = topic_of(m)
    return f"{m.chat.id}/{topic}" if topic else str(m.chat.id)


def guard(handler):
    """Lenh chi danh cho admin."""
    def wrapper(m):
        if not sender_authorized(m):
            logger.warning(f"Tu choi lenh {command_of(m)} tu {m.chat.id}")
            return
        try:
            handler(m)
        except Exception as e:
            logger.exception("Loi xu ly lenh")
            bot.reply_to(m, f"Loi: {e}")
    return wrapper


def register_handlers():
    @bot.message_handler(commands=["id"])
    def _id(m):  # khong can quyen: de lay chat id / topic id map vao muse_sync.json
        topic = topic_of(m)
        bot.reply_to(m, f"chat_id={m.chat.id}" + (f" topic_id={topic}" if topic else ""))

    @bot.message_handler(commands=["me"])
    def _me(m):  # menu nguoi dung (Free / VIP), ca admin cung xem duoc de thu mua VIP
        if m.chat.type == "private" and m.from_user:
            text, kb = start_text(m.from_user)
            bot.send_message(m.chat.id, text, parse_mode="HTML", reply_markup=kb)

    @bot.message_handler(commands=["vipgroup"])
    def _vipgroup(m):
        u = muse_users.get(m.from_user.id) if m.from_user else None
        if m.chat.type not in ("group", "supergroup"):
            bot.reply_to(m, "Gõ /vipgroup trong nhóm Telegram (đã bật Chủ đề) mà bạn muốn dùng với Muse.")
        elif not muse_users.vip_active(u):
            bot.reply_to(m, "Chỉ người dùng VIP mới gắn được nhóm. Mua VIP: nhắn /start cho bot.")
        else:
            muse_users.set_vip_group(u["id"], m.chat.id)
            note = "" if getattr(m.chat, "is_forum", False) else "\n⚠️ Nhóm chưa bật Chủ đề (Topics): bật lên để mỗi topic là 1 chat riêng."
            bot.reply_to(m, "✅ <b>Đã gắn nhóm với Muse VIP của bạn</b>\n• <b>General</b>: chat chính với Muse\n"
                            "• <b>Mỗi topic</b>: 1 chat riêng với Muse, tạo khi có tin đầu tiên trong topic"
                            + html.escape(note), parse_mode="HTML")

    @bot.message_handler(commands=["hoi"])
    def _hoi(m):  # nguoi dung hoi admin
        question = m.text.partition(" ")[2].strip()
        if sender_authorized(m):
            bot.reply_to(m, "Admin: reply tin ❓ Câu hỏi từ ... de tra loi nguoi dung.")
        elif not m.from_user:
            return
        elif not question:
            bot.reply_to(m, "✍️ Gõ câu hỏi ngay sau lệnh, ví dụ:\n/hoi Làm sao để gia hạn VIP?")
        else:
            ask_admin(m, question)

    @bot.message_handler(commands=["vip"])
    @guard
    def _vip(m):
        args = m.text.split()[1:]
        if len(args) == 2 and args[0].lstrip("-").isdigit() and args[1].isdigit():
            uid, days = int(args[0]), int(args[1])
            if not muse_users.get(uid):
                bot.reply_to(m, f"Chua co nguoi dung {uid} (ho phai /start bot truoc).")
            elif days == 0:
                muse_users.end_vip(uid)
                bot.reply_to(m, f"Da ket thuc VIP cua {uid}: trong vai phut bot se reset Muse va tra profile ve pool.")
            else:
                u = grant(uid, days)
                bot.reply_to(m, f"VIP {u['name']} den {muse_users.fmt_time(u['vip_until'])} ({u['vip_profile']})"
                             if u else "Het profile VIP de giao.")
            return
        lines = ["Dung: /vip <user id> <so ngay> (0 = ket thuc VIP)", ""]
        lines += [f"{u['name']} ({u['id']}) {u['vip_profile']}, {VIP_MODES.get(u['vip_mode'], 'chua chon che do')}, "
                  f"{'den' if muse_users.vip_active(u) else 'het han'} {muse_users.fmt_time(u['vip_until'])}"
                  for u in muse_users.vip_users()] or ["Chua co VIP."]
        bot.reply_to(m, "\n".join(lines))

    @bot.message_handler(commands=["start", "help"])
    def _start(m):
        if sender_authorized(m):
            set_command_descriptions()
            cur = selected_chat(m.chat.id)
            bot.send_message(m.chat.id, menu_text() + f"\n\nDang chon: {cur['key'] if cur else '(chua co chat nao)'}")
        elif m.chat.type == "private" and m.from_user:
            text, kb = start_text(m.from_user)
            bot.send_message(m.chat.id, text, parse_mode="HTML", reply_markup=kb)

    @bot.message_handler(commands=["stats"])
    @guard
    def _stats(m):
        bot.reply_to(m, stats_text())

    @bot.message_handler(commands=["skills"])
    @guard
    def _skills(m):
        arg = m.text.partition(" ")[2].strip()
        if arg.lower() == "stop":
            skills_cancel.set()
            bot.reply_to(m, "Dang dung cai skill: bam Stop luot cai cua Muse o profile dang cai, cac profile sau bi bo qua.")
            return
        existing = set(muse_sync.fox_profiles())  # muse_sync.json co the con ten profile da xoa khoi FoxProfile
        known = [p for p in dict.fromkeys(muse_sync.profiles() + muse_users.vip_profiles()) if p in existing]
        profiles = known if arg.lower() == "all" else [p for p in known if p.casefold() == arg.casefold()]
        if not profiles:
            bot.reply_to(m, "Dung: /skills <profile> | all | stop\nProfile: " + ", ".join(known))
            return
        bot.reply_to(m, f"Dang cai skill len {', '.join(profiles)} (moi profile vai phut, xong se bao)...")
        threading.Thread(target=install_skills, args=(profiles, m.chat.id), daemon=True).start()

    @bot.message_handler(commands=["log"])
    @guard
    def _log(m):
        args = m.text.split()[1:]
        uid = int(args[0]) if args and args[0].lstrip("-").isdigit() else None
        limit = int(args[1]) if len(args) > 1 and args[1].isdigit() else 20
        rows = muse_users.recent_prompts(uid, min(limit, 100))
        lines = [f"{muse_users.fmt_time(r['ts'])} {r['name'] or r['user_id']} ({r['user_id']}) {r['chat']}"
                 f"{'' if r['ok'] else ' [loi]'}{' [nut]' if r['kind'] == 'tap' else ''}: {r['text'] or ''}"
                 f"{' + ' + r['files'] if r['files'] else ''}" for r in rows]
        text = "\n\n".join(lines) or "Chua co log."
        for i in range(0, len(text), 4000):
            bot.send_message(m.chat.id, text[i:i + 4000])

    @bot.message_handler(commands=["broadcast"])
    @guard
    def _broadcast(m):
        text = m.text.partition(" ")[2].strip()
        if m.reply_to_message:
            source = {"from_chat": m.chat.id, "message_id": m.reply_to_message.message_id}
        elif text:
            source = {"text": text}
        else:
            bot.reply_to(m, "Dung: /broadcast <noi dung>, hoac reply 1 tin (chu/anh/video) bang /broadcast")
            return
        kb = types.InlineKeyboardMarkup()
        kb.row(types.InlineKeyboardButton("📣 Gửi", callback_data="bc:ok"),
               types.InlineKeyboardButton("Huỷ", callback_data="bc:no"))
        confirm = bot.reply_to(m, f"Gửi tin này tới {len(muse_users.broadcast_ids())} người dùng?", reply_markup=kb)
        broadcasts[confirm.message_id] = source

    @bot.message_handler(commands=["to"])
    @guard
    def _to(m):
        """Chat rieng: chon chat muse nhan tin. Nhom/topic: map nhom/topic nay vao 1 chat muse trong muse_sync.json;
        /to <profile> <id hoac link side chat> them side chat moi va map luon."""
        private = m.chat.type == "private"
        args = m.text.split()[1:]
        if not private and len(args) == 2:
            profile = next((p for p in muse_sync.profiles() if p.casefold() == args[0].casefold()), None)
            tid = muse_sync.thread_id(args[1])
            if not profile or not tid:
                bot.reply_to(m, f"Dung: /to <profile> <link side chat>, profile: {', '.join(muse_sync.profiles())}")
                return
            muse_sync.map_tg(f"{profile}/{tid}", tg_key(m))
            bot.reply_to(m, f"Tin o day se vao side chat {profile}/{tid}.")
            return
        cur = selected_chat(m.chat.id) if private else muse_sync.chats_by_tg().get(tg_key(m))
        kb = types.InlineKeyboardMarkup()
        for c in muse_sync.muse_chats():
            mark = "✅ " if cur and c["key"] == cur["key"] else ""
            kb.add(types.InlineKeyboardButton(mark + c["key"], callback_data=f"to:{c['key']}"[:64]))
        hint = "" if private else "\n(Side chat moi: /to <profile> <link side chat>)"
        bot.reply_to(m, ("Chon chat muse nhan tin:" if kb.keyboard else "Chua co chat nao trong muse_sync.json") + hint,
                     reply_markup=kb)

    @bot.message_handler(commands=["approve_on", "approve_off", "approve"])
    @guard
    def _approve(m):
        command = command_of(m)
        if command != "approve":
            muse_auto.set_enabled(command == "approve_on")
        state = "BAT" if muse_auto.enabled() else "TAT"
        bot.send_message(m.chat.id, f"Auto Allow tren muse.ai: {state} (/approve_on, /approve_off)")

    @bot.message_handler(func=lambda m: (m.text or "").startswith("/") and command_of(m) in profile_commands())
    @guard
    def _profile(m):
        profile = profile_commands()[command_of(m)]
        chat = next((c for c in muse_sync.muse_chats() if c["profile"] == profile and c["url"] == muse_sync.MUSE_URL),
                    {"profile": profile, "url": muse_sync.MUSE_URL, "tg": "", "key": profile})
        text = m.text.partition(" ")[2].strip()
        if not text:
            select_chat(m.chat.id, chat["key"])
            bot.reply_to(m, f"Da chon {chat['key']}: tin tiep theo se vao main chat cua {profile}.")
            return
        enqueue(m, chat, text)

    @bot.message_handler(content_types=CONTENT_TYPES, func=is_admin_answer)
    def _answer(m):
        try:
            answer_user(m)
        except Exception as e:
            logger.exception("Loi tra loi nguoi dung")
            bot.reply_to(m, f"Loi: {e}")

    @bot.message_handler(content_types=CONTENT_TYPES, func=is_follow_up)
    def _follow_up(m):
        ask_admin(m, (m.text or m.caption or "").strip())

    @bot.message_handler(content_types=CONTENT_TYPES)
    @bot.channel_post_handler(content_types=CONTENT_TYPES)
    def _forward(m):
        if m.chat.type == "private" and m.from_user and not authorized(m.chat.id):
            muse_users.touch(m.from_user)
        chat = target_for(m)
        if chat is None:
            if m.chat.type == "private":
                text, kb = start_text(m.from_user)
                bot.reply_to(m, "ℹ️ <i>Bạn chưa có gói nào để làm việc với Muse.</i>\n\n" + text, parse_mode="HTML",
                             reply_markup=kb)
            elif m.chat.type != "channel" and sender_authorized(m):
                logger.info(f"Bo qua tin {m.message_id}: {tg_key(m)} chua map vao chat muse nao")
                bot.reply_to(m, f"Nhom/topic nay ({tg_key(m)}) chua map vao chat muse nao. Gui /to de chon.")
            return
        if chat.get("user") and quota_note(chat["user"]) is None:
            bot.reply_to(m, quota_exhausted_text())
            return
        enqueue(m, chat, (m.text or m.caption or "").strip())

    @bot.callback_query_handler(func=lambda c: True)
    def _callback(c):
        m = c.message
        admin = authorized(m.chat.id) or authorized(c.from_user.id)
        kind, _, value = c.data.partition(":")
        if kind == "free" and m.chat.type == "private":
            free_callback(c, value)
        elif kind == "vip" and m.chat.type == "private":
            vip_callback(c, value.split(":"))
        elif kind in ("vipok", "vipno") and admin:
            approve_vip(c, int(value), kind == "vipok")
        elif kind == "bc" and admin:
            source = broadcasts.pop(m.message_id, None)
            if value != "ok" or not source:
                bot.answer_callback_query(c.id, "Đã huỷ." if value != "ok" else "Tin xác nhận đã cũ.")
                bot.edit_message_reply_markup(m.chat.id, m.message_id, reply_markup=None)
                return
            bot.answer_callback_query(c.id, "Đang gửi...")
            bot.edit_message_text("📣 Đang quảng bá...", m.chat.id, m.message_id)
            threading.Thread(target=run_broadcast, args=(source, m.chat.id), daemon=True).start()
        elif kind == "to" and admin:
            if m.chat.type == "private":
                select_chat(m.chat.id, value)
            else:  # nhom/topic: ghi map vao muse_sync.json
                muse_sync.map_tg(value, tg_key(m))
            bot.answer_callback_query(c.id, f"Da chon {value}")
            bot.edit_message_text(f"Tin tiep theo se vao: {value}", m.chat.id, m.message_id)
        elif c.data == CHOSEN_DATA:
            bot.answer_callback_query(c.id, "Đã chọn rồi.")
        elif admin or m.chat.type == "private" or muse_users.vip_by_group(m.chat.id):  # nut cua Muse
            choose(c)
        else:
            bot.answer_callback_query(c.id, "Không có quyền.")


def main():
    ctypes.windll.kernel32.SetConsoleTitleW(TITLE)
    # 1 tien trinh moi luc: 2 ban cung polling 1 token se bi Telegram tu choi (409). Mutex tu nha khi tien trinh chet.
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    main.mutex = kernel32.CreateMutexW(None, False, "Local\\" + TITLE)
    if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
        raise SystemExit("muse_telebot dang chay o tien trinh khac -- thoat")
    if not TOKEN:
        raise SystemExit("Thieu TELEGRAM_BOT_TOKEN trong .env (tao bot rieng bang BotFather)")
    if not ALLOWED_CHAT_IDS:
        logger.warning("MUSE_BOT_ALLOWED_CHAT_IDS dang trong: khong co admin.")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    clean_upload_dir()
    muse_users.cancel_pending()  # dang ky dang do luc bot tat: tra suat
    register_handlers()
    set_command_descriptions()
    threading.Thread(target=worker, daemon=True).start()
    threading.Thread(target=expiry_loop, daemon=True).start()
    threading.Thread(target=admin_topics_loop, daemon=True).start()
    threading.Thread(target=watch_loop, daemon=True).start()
    threading.Thread(target=muse_auto.loop, args=(lambda p, ctx: notify(f"✅ Auto Allow ({p}): {ctx[:300]}"),),
                     daemon=True).start()
    logger.info("Muse telebot started.")
    # khong skip_pending: tin dang trong kenh luc bot tat van duoc chuyen vao muse khi bot chay lai
    bot.infinity_polling(timeout=30, long_polling_timeout=30)


if __name__ == "__main__":
    main()
