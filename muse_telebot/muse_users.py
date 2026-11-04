# -*- coding: utf-8 -*-
"""
Nguoi dung bot muse (muse_users.db, SQLite): goi Free, quota trong ngay, danh sach de quang ba.

Free: moi nguoi 1 side chat rieng trong pool FREE_PROFILES (moi profile toi da FREE_PER_PROFILE side chat), dung
FREE_DAYS ngay; het han thi bot xoa side chat, tra suat ve pool, nguoi do phai cho FREE_COOLDOWN_DAYS ngay moi dang ky
lai. Moi ngay (gio Viet Nam) toi da FREE_DAILY anh/video Muse gui ve.
Suat dang giu = free_profile khac NULL (dang tao side chat, dang dung, hoac het han nhung chua xoa xong side chat).

VIP: moi nguoi 1 profile rieng (profile FoxProfile ten la email @sanhdieu247.xyz), khong gioi han quota. Het han thi bot
reset Muse cua profile (xoa het du lieu) roi tra profile ve pool; gia han sau do la nhan profile moi.
Che do "direct": chat rieng voi bot vao main chat; "group": nhom Telegram co topic cua ho, General = main chat, moi
topic 1 side chat (tao khi co tin dau tien trong topic). Mua: chuyen khoan theo bang gia VIP_PRICES toi VIP_BANK, admin duyet.
"""

import sqlite3
import threading
import time
from datetime import datetime, timedelta, timezone

from muse_sync import HERE, FoxProfileBrowser

DB_FILE = HERE / "muse_users.db"
FREE_ENABLED = False  # tam dung goi Free: an khoi menu, khong nhan dang ky, nguoi dang dung bi ket thuc (xoa side chat)
FREE_PROFILES = ["Muse2", "Muse3", "Muse4"]
FREE_PER_PROFILE = 10
FREE_DAYS = 3
FREE_COOLDOWN_DAYS = 3
FREE_DAILY = {"video": 10, "image": 50}
VIP_PROFILE_SUFFIX = "@sanhdieu247.xyz"  # profile VIP = moi profile FoxProfile co ten la email duoi nay
VIP_PROFILES_TTL = 60  # giay: doc lai danh sach profile tu FoxProfile
VIP_PRICES = {1: 10000, 3: 25000, 7: 50000, 30: 200000}  # so ngay -> gia (dong)
VIP_BANK = {"bank": "VIB", "account": "240628888"}
DAY = 86400
VN = timezone(timedelta(hours=7))

_lock = threading.Lock()
_db = sqlite3.connect(DB_FILE, check_same_thread=False, isolation_level=None)
_db.row_factory = sqlite3.Row
_db.executescript("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,           -- Telegram user id (= chat id chat rieng)
    name TEXT, username TEXT,
    first_seen REAL, last_seen REAL,
    blocked INTEGER DEFAULT 0,        -- da chan bot: bo qua khi quang ba
    free_profile TEXT,                -- profile dang giu suat Free (NULL = khong giu)
    free_thread TEXT,                 -- id side chat Free (NULL khi dang tao)
    free_start REAL, free_end REAL,
    free_cooldown_until REAL          -- dang ky Free lai duoc tu luc nay
);
CREATE TABLE IF NOT EXISTS usage (
    user_id INTEGER, day TEXT, image INTEGER DEFAULT 0, video INTEGER DEFAULT 0,
    PRIMARY KEY (user_id, day)
);
CREATE TABLE IF NOT EXISTS vip_topics (      -- che do group: topic Telegram -> side chat trong profile VIP
    user_id INTEGER, topic_id INTEGER, thread TEXT, PRIMARY KEY (user_id, topic_id)
);
CREATE TABLE IF NOT EXISTS payments (        -- yeu cau mua / gia han VIP
    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, days INTEGER, amount INTEGER,
    created REAL, status TEXT               -- new: da gui QR, claimed: bao da chuyen, approved, rejected
);
CREATE TABLE IF NOT EXISTS prompts (         -- log tin nguoi dung Free / VIP gui vao Muse
    id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, user_id INTEGER, chat TEXT, kind TEXT,  -- kind: msg / tap
    text TEXT, files TEXT, ok INTEGER
);
CREATE INDEX IF NOT EXISTS prompts_user ON prompts (user_id, ts);
""")
for _col in ("vip_profile TEXT", "vip_until REAL", "vip_mode TEXT", "vip_group INTEGER",
             "vip_expiry_noted INTEGER DEFAULT 0"):  # bang users cu: them cot VIP
    try:
        _db.execute(f"ALTER TABLE users ADD COLUMN {_col}")
    except sqlite3.OperationalError:  # cot da co
        pass


def _q(sql, *args):
    with _lock:
        return [dict(r) for r in _db.execute(sql, args).fetchall()]


def today():
    return datetime.now(VN).strftime("%Y-%m-%d")


def fmt_time(ts):
    return datetime.fromtimestamp(ts, VN).strftime("%H:%M %d/%m/%Y")


def display_name(user):
    """Ten de Muse goi: ho ten Telegram, khong co thi @username."""
    name = " ".join(x for x in (user.first_name, user.last_name) if x).strip()
    return name or (f"@{user.username}" if user.username else str(user.id))


def touch(user):
    """Luu / cap nhat nguoi dung Telegram (telebot User). Tra ve ban ghi."""
    now = time.time()
    with _lock:
        _db.execute("""INSERT INTO users (id, name, username, first_seen, last_seen) VALUES (?, ?, ?, ?, ?)
                       ON CONFLICT(id) DO UPDATE SET name = excluded.name, username = excluded.username,
                       last_seen = excluded.last_seen, blocked = 0""",
                    (user.id, display_name(user), user.username or "", now, now))
    return get(user.id)


def get(uid):
    rows = _q("SELECT * FROM users WHERE id = ?", uid)
    return rows[0] if rows else None


def set_blocked(uid):
    _q("UPDATE users SET blocked = 1 WHERE id = ?", uid)


# ---------- Free ----------

def free_active(u, now=None):
    return bool(u and u["free_thread"] and (u["free_end"] or 0) > (now or time.time()))


def slots_used():
    """{profile: so suat dang giu}."""
    used = {p: 0 for p in FREE_PROFILES}
    for r in _q("SELECT free_profile, COUNT(*) AS n FROM users WHERE free_profile IS NOT NULL GROUP BY free_profile"):
        used[r["free_profile"]] = r["n"]
    return used


def slots_left():
    return sum(max(0, FREE_PER_PROFILE - n) for p, n in slots_used().items() if p in FREE_PROFILES)


def free_block_reason(u):
    """Ly do chua dang ky Free duoc (None = duoc)."""
    now = time.time()
    if not FREE_ENABLED:
        return "Gói Free đang tạm dừng."
    if u["free_profile"]:
        return "Bạn đang dùng gói Free rồi." if free_active(u, now) else "Gói Free của bạn đang được xử lý, thử lại sau ít phút."
    if (u["free_cooldown_until"] or 0) > now:
        return f"Bạn vừa dùng hết gói Free, có thể đăng ký lại từ {fmt_time(u['free_cooldown_until'])}."
    if slots_left() <= 0:
        return "Hiện đã hết suất Free, bạn quay lại sau nhé."
    return None


def reserve_free(uid, exclude=()):
    """Giu 1 suat o profile it nguoi Free nhat (bang nhau thi profile hom nay it anh/video nhat), bo qua cac profile
    trong exclude (vua tao side chat loi). Tra ve profile, None neu het suat / khong du dieu kien."""
    with _lock:
        u = _db.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
        if not FREE_ENABLED or not u or u["free_profile"] or (u["free_cooldown_until"] or 0) > time.time():
            return None
        used, load = {p: 0 for p in FREE_PROFILES}, {p: 0 for p in FREE_PROFILES}
        for r in _db.execute("SELECT free_profile, COUNT(*) FROM users WHERE free_profile IS NOT NULL "
                             "GROUP BY free_profile"):
            used[r[0]] = r[1]
        for r in _db.execute("SELECT s.free_profile, SUM(u.image + u.video) FROM usage u JOIN users s "
                             "ON s.id = u.user_id WHERE u.day = ? AND s.free_profile IS NOT NULL "
                             "GROUP BY s.free_profile", (today(),)):
            load[r[0]] = r[1] or 0
        profile = min((p for p in FREE_PROFILES if used[p] < FREE_PER_PROFILE and p not in exclude),
                      key=lambda p: (used[p], load[p]), default=None)
        if profile:
            _db.execute("UPDATE users SET free_profile = ?, free_thread = NULL WHERE id = ?", (profile, uid))
        return profile


def activate_free(uid, thread):
    now = time.time()
    _q("UPDATE users SET free_thread = ?, free_start = ?, free_end = ? WHERE id = ?",
       thread, now, now + FREE_DAYS * DAY, uid)
    return get(uid)


def cancel_reservation(uid):
    _q("UPDATE users SET free_profile = NULL, free_thread = NULL WHERE id = ? AND free_thread IS NULL", uid)


def cancel_pending():
    """Tra cac suat dang giu do dang ky do dang (bot tat giua chung)."""
    _q("UPDATE users SET free_profile = NULL WHERE free_profile IS NOT NULL AND free_thread IS NULL")


def expired_free():
    """Nguoi dung Free da het han, hoac da len VIP (chat rieng vao profile VIP, side chat Free bo khong), side chat chua
    xoa. Free tam dung (FREE_ENABLED = False): moi nguoi dung Free."""
    now = time.time()
    if not FREE_ENABLED:
        return _q("SELECT * FROM users WHERE free_thread IS NOT NULL")
    return _q("SELECT * FROM users WHERE free_thread IS NOT NULL AND (free_end <= ? OR "
              "(vip_profile IS NOT NULL AND vip_until > ?))", now, now)


def release_free(uid):
    """Tra suat ve pool (side chat da xoa) va bat dau thoi gian cho dang ky lai."""
    _q("""UPDATE users SET free_profile = NULL, free_thread = NULL, free_cooldown_until = ? WHERE id = ?""",
       time.time() + FREE_COOLDOWN_DAYS * DAY, uid)


# ---------- VIP ----------

_vip_profiles = {"at": 0, "names": []}


def vip_profiles():
    """Profile VIP: moi profile FoxProfile ten ket thuc bang VIP_PROFILE_SUFFIX (doc lai sau VIP_PROFILES_TTL giay;
    FoxProfile loi thi dung danh sach cu)."""
    if time.time() - _vip_profiles["at"] > VIP_PROFILES_TTL:
        try:
            listed = FoxProfileBrowser("", log=lambda *a: None)._call("GET", "/profiles", timeout=15).json()["profiles"]
            _vip_profiles["names"] = sorted(p["name"] for p in listed
                                            if p["name"].lower().endswith(VIP_PROFILE_SUFFIX))
            _vip_profiles["at"] = time.time()
        except Exception:
            pass
    return list(_vip_profiles["names"])


def vip_active(u, now=None):
    return bool(u and u["vip_profile"] and (u["vip_until"] or 0) > (now or time.time()))


def vip_slots():
    """(so profile VIP con trong, tong so profile VIP)."""
    profiles = vip_profiles()
    taken = {r["vip_profile"] for r in _q("SELECT vip_profile FROM users WHERE vip_profile IS NOT NULL")}
    return sum(1 for p in profiles if p not in taken), len(profiles)


def vip_profile_for(uid):
    """Profile VIP cua uid (da giu) hoac profile VIP con trong; None neu het."""
    u = get(uid)
    if u and u["vip_profile"]:
        return u["vip_profile"]
    taken = {r["vip_profile"] for r in _q("SELECT vip_profile FROM users WHERE vip_profile IS NOT NULL")}
    return next((p for p in vip_profiles() if p not in taken), None)


def grant_vip(uid, days):
    """Cong days ngay VIP (giu profile cu hoac nhan profile con trong). Tra ve (ban ghi, profile moi nhan hay khong);
    (None, False) neu het profile VIP."""
    available = vip_profiles()  # goi FoxProfile ngoai khoa database
    with _lock:
        u = _db.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
        if not u:
            return None, False
        profile, new = u["vip_profile"], False
        if not profile:
            taken = {r[0] for r in _db.execute("SELECT vip_profile FROM users WHERE vip_profile IS NOT NULL")}
            profile = next((p for p in available if p not in taken), None)
            if not profile:
                return None, False
            new = True
        until = max(time.time(), u["vip_until"] or 0) + days * DAY
        _db.execute("UPDATE users SET vip_profile = ?, vip_until = ?, vip_expiry_noted = 0 WHERE id = ?",
                    (profile, until, uid))
    return get(uid), new


def end_vip(uid):
    """Ket thuc VIP ngay; vong kiem tra het han se reset Muse va tra profile."""
    _q("UPDATE users SET vip_until = ? WHERE id = ?", time.time(), uid)


def set_vip_mode(uid, mode):
    _q("UPDATE users SET vip_mode = ? WHERE id = ?", mode, uid)


def set_vip_group(uid, chat_id):
    _q("UPDATE users SET vip_group = NULL WHERE vip_group = ?", chat_id)  # 1 nhom chi gan 1 nguoi
    _q("UPDATE users SET vip_group = ?, vip_mode = 'group' WHERE id = ?", chat_id, uid)


def vip_by_group(chat_id):
    rows = _q("SELECT * FROM users WHERE vip_group = ?", chat_id)
    return rows[0] if rows else None


def vip_topic(uid, topic_id):
    rows = _q("SELECT thread FROM vip_topics WHERE user_id = ? AND topic_id = ?", uid, topic_id)
    return rows[0]["thread"] if rows else None


def set_vip_topic(uid, topic_id, thread):
    _q("INSERT OR REPLACE INTO vip_topics (user_id, topic_id, thread) VALUES (?, ?, ?)", uid, topic_id, thread)


def vip_expired():
    """VIP da het han ma van giu profile (chua reset Muse, chua tra profile)."""
    return _q("SELECT * FROM users WHERE vip_profile IS NOT NULL AND vip_until <= ?", time.time())


def release_vip(uid):
    """Tra profile VIP ve pool sau khi da reset Muse; side chat cua cac topic da mat theo nen xoa map topic."""
    _q("UPDATE users SET vip_profile = NULL WHERE id = ?", uid)
    _q("DELETE FROM vip_topics WHERE user_id = ?", uid)


def new_payment(uid, days):
    with _lock:
        cur = _db.execute("INSERT INTO payments (user_id, days, amount, created, status) VALUES (?, ?, ?, ?, 'new')",
                          (uid, days, VIP_PRICES[days], time.time()))
        return cur.lastrowid


def payment(pid):
    rows = _q("SELECT * FROM payments WHERE id = ?", pid)
    return rows[0] if rows else None


def set_payment_status(pid, status, only_from=None):
    """Doi trang thai; only_from: chi doi khi trang thai hien tai nam trong do (tranh duyet 2 lan). True neu doi."""
    with _lock:
        if only_from:
            marks = ",".join("?" * len(only_from))
            cur = _db.execute(f"UPDATE payments SET status = ? WHERE id = ? AND status IN ({marks})",
                              (status, pid, *only_from))
        else:
            cur = _db.execute("UPDATE payments SET status = ? WHERE id = ?", (status, pid))
        return cur.rowcount > 0


def vip_users():
    return _q("SELECT * FROM users WHERE vip_profile IS NOT NULL ORDER BY vip_until DESC")


# ---------- quota ----------

def usage(uid, day=None):
    rows = _q("SELECT image, video FROM usage WHERE user_id = ? AND day = ?", uid, day or today())
    return rows[0] if rows else {"image": 0, "video": 0}


def add_usage(uid, kind):
    if kind not in FREE_DAILY:
        return
    _q(f"""INSERT INTO usage (user_id, day, {kind}) VALUES (?, ?, 1)
           ON CONFLICT(user_id, day) DO UPDATE SET {kind} = {kind} + 1""", uid, today())


def quota_left(uid):
    used = usage(uid)
    return {k: max(0, limit - used[k]) for k, limit in FREE_DAILY.items()}


# ---------- log prompt ----------

def log_prompt(uid, chat, kind, text, files, ok):
    _q("INSERT INTO prompts (ts, user_id, chat, kind, text, files, ok) VALUES (?, ?, ?, ?, ?, ?, ?)",
       time.time(), uid, chat, kind, text, ", ".join(files), int(ok))


def recent_prompts(uid=None, limit=20):
    """Cac tin moi nhat (cu truoc moi sau), cua uid hoac cua moi nguoi."""
    where, args = ("WHERE p.user_id = ?", (uid,)) if uid else ("", ())
    rows = _q(f"SELECT p.*, s.name FROM prompts p LEFT JOIN users s ON s.id = p.user_id {where} "
              f"ORDER BY p.id DESC LIMIT ?", *args, limit)
    return rows[::-1]


# ---------- thong ke / quang ba ----------

def broadcast_ids():
    return [r["id"] for r in _q("SELECT id FROM users WHERE blocked = 0")]


def stats():
    now, day = time.time(), today()
    users = _q("SELECT * FROM users")
    used_today = _q("SELECT u.user_id, u.image, u.video, s.name FROM usage u LEFT JOIN users s ON s.id = u.user_id "
                    "WHERE u.day = ? ORDER BY u.video DESC, u.image DESC", day)
    return {
        "users": len(users),
        "active_7d": sum(1 for u in users if (u["last_seen"] or 0) > now - 7 * DAY),
        "blocked": sum(1 for u in users if u["blocked"]),
        "free_active": [u for u in users if free_active(u, now)],
        "cooldown": sum(1 for u in users if (u["free_cooldown_until"] or 0) > now and not u["free_profile"]),
        "slots": slots_used(),
        "slots_left": slots_left(),
        "today": used_today,
        "vip": [u for u in users if u["vip_profile"]],
        "payments": _q("SELECT status, COUNT(*) AS n, SUM(amount) AS total FROM payments GROUP BY status"),
    }
