# -*- coding: utf-8 -*-
"""
Thao tac voi muse.ai qua FoxProfile: gui tin (text + anh/video/file) vao main chat cua 1 profile, doc tin tra loi +
anh/video/file cua Muse (de bot chuyen ve Telegram), kiem tra profile da dang nhap Muse chua, kiem tra IP cua profile.

Go ngam: chat duoc mo tren tab co dung URL cua no qua tham so "tab" cua FoxProfile -- khong chuyen tab, khong keo
cua so len. Loi thi refresh trang va thu lai toi SEND_ATTEMPTS lan.
"""

import base64
import json
import logging
import os
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "foxprofile"))
from foxprofile_client import FoxError, FoxProfileBrowser, same_url  # noqa: E402

MUSE_URL = "https://muse.ai/"
# O chat cua Muse; nhan theo ngon ngu giao dien (tieng Anh / tieng Viet), du phong: textarea dau tien cua composer.
MUSE_INPUT = ('textarea[aria-label="Message"], textarea[aria-label="Nhắn tin"], '
              'textarea[data-hatch-composer-prehydration-input]')
MUSE_FILE_INPUT = "input[type='file']"
SEND_ATTEMPTS = 3  # lan dau dung trang dang mo; cac lan sau refresh trang roi thu lai
UPLOAD_MAX_WAIT_SECONDS = 30
SEND_CONFIRM_POLLS = 20  # x 0.5s: cho tin vua gui hien trong chat
RESTART_GAP_SECONDS = 300  # trinh duyet treo: khoi dong lai profile toi da 1 lan moi ngan nay giay
# Muse dang lam viec: nut Stop cua o chat hien ra (luc ranh no van nam trong DOM nhung trong khoi inert/aria-hidden),
# hoac cau tra loi dang duoc viet ra. Kiem tra tren muse.ai ngay 2026-10-28.
BUSY_JS = """() => [...document.querySelectorAll('[data-testid="hatch-composer-stop-button"]')]
  .some(b => !b.closest('[inert],[aria-hidden="true"]'))
  || !!document.querySelector('[data-hatch-markdown-streaming="true"]')"""
# Cac tin trong chat (40 tin cuoi): id, role; tin cua Muse kem text (da xong hay dang viet) va anh/video/file dinh kem
# (data-testid hatch-chat-attachment-presentation-<loai>, src thuong la blob:). Kiem tra 2026-10-28.
# Anh/video chi nap khi khung cua no nam trong vung nhin thay: cuon khung dau tien chua nap vao giua man hinh.
MESSAGES_JS = r"""() => {
 // markdown Muse da render (streamdown) -> HTML Telegram (b, i, s, code, pre, a, blockquote); danh sach -> "•" / "1."
 const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
 const tg = (node, depth) => {
   if (node.nodeType === 3) return esc(node.nodeValue);
   if (node.nodeType !== 1) return '';
   const tag = node.tagName.toLowerCase(), sd = node.getAttribute('data-streamdown') || '';
   if (tag === 'svg' || tag === 'button' || node.hasAttribute('data-copy-exclude')) return '';
   const inner = () => [...node.childNodes].map(c => tg(c, depth)).join('');
   if (tag === 'br') return '\n';
   if (tag === 'pre' || sd === 'code-block') {
     const code = node.querySelector('pre code, pre') || node;
     return '<pre>' + esc((code.innerText || '').replace(/\n+$/, '')) + '</pre>\n\n';
   }
   if (tag === 'code' || sd === 'inline-code') return '<code>' + esc(node.innerText || '') + '</code>';
   if (tag === 'strong' || tag === 'b' || sd === 'strong') return '<b>' + inner() + '</b>';
   if (tag === 'em' || tag === 'i' || sd === 'emphasis') return '<i>' + inner() + '</i>';
   if (tag === 'del' || tag === 's') return '<s>' + inner() + '</s>';
   if (tag === 'a') {
     const href = node.getAttribute('href') || '';
     return /^https?:/.test(href) ? '<a href="' + esc(href).replace(/"/g, '&quot;') + '">' + inner() + '</a>' : inner();
   }
   if (/^h[1-6]$/.test(tag)) return '<b>' + inner().trim() + '</b>\n\n';
   if (tag === 'p') return inner().trim() + '\n\n';
   if (tag === 'blockquote') return '<blockquote>' + inner().trim() + '</blockquote>\n\n';
   if (tag === 'hr') return '\n';
   if (tag === 'ul' || tag === 'ol') {
     const start = parseInt(node.getAttribute('start') || '1', 10);
     const lines = [...node.children].filter(c => c.tagName === 'LI').map((li, i) =>
       '   '.repeat(depth) + (tag === 'ol' ? (start + i) + '. ' : '• ') +
       [...li.childNodes].map(c => tg(c, depth + 1)).join('').replace(/\n{2,}/g, '\n').trim());
     return depth ? '\n' + lines.join('\n') : lines.join('\n') + '\n\n';
   }
   if (tag === 'table') {
     return [...node.querySelectorAll('tr')].map(tr =>
       [...tr.children].map(td => tg(td, depth).trim()).join(' | ')).join('\n') + '\n\n';
   }
   return inner();
 };
 const items = [...document.querySelectorAll('[data-message-item]')].slice(-40);
 // 1 khung dinh kem co the la luoi nhieu anh/video (VD 7 video 1 tin): moi o la 1 nut co aria-label chua video/img.
 // Khung 1 file: chinh khung. Kiem tra 2026-10-28.
 const tiles = p => {
   const t = [...p.querySelectorAll('[title],[aria-label]')].filter(e => e.querySelector('video, img'));
   const outer = t.filter(e => !t.some(o => o !== e && o.contains(e)));
   return outer.length > 1 ? outer : [p];
 };
 const presentations = item => [...item.querySelectorAll('[data-testid^="hatch-chat-attachment-presentation-"]')];
 const kindOf = p => p.getAttribute('data-testid').replace('hatch-chat-attachment-presentation-', '');
 // Video dang nap (resolutionStatus "loading") chi co anh poster + spinner aria-label "Loading", chua co <video>:
 // khong lay poster lam video. Kiem tra 2026-10-29.
 // Khung file (VD .md Muse tao trong sandbox) chi co <img> la icon loai file: khong phai anh. Kiem tra 2026-10-30.
 const mediaOf = (p, t) => t.querySelector('video') || (['video', 'file'].includes(kindOf(p)) ? null : t.querySelector('img'));
 // Audio: player rieng (nut Play + thanh keo), khong co <audio src> / link tai trong trang, khong bao gio "nap xong":
 // khong cho. File: lay noi dung bang fetch_file. Kiem tra 2026-10-30.
 // File da mat tren muse: khung chi con "Video not found. It may be unavailable or removed.", khong bao gio nap.
 const gone = t => /not found/i.test(t.getAttribute('title') || t.getAttribute('aria-label') || t.innerText);
 // Props React cua khung dinh kem (Camoufox: qua wrappedJSObject): {kind, displayText, data: {file: {path, label, mime}}}
 const presOf = p => { try { const w = p.wrappedJSObject || p;
     return w[Object.keys(w).find(k => k.startsWith('__reactFiber'))].return.memoizedProps.presentation || {};
   } catch (e) { return {}; } };
 const waiting = items.flatMap(i => presentations(i).filter(p => !['audio', 'file'].includes(kindOf(p))).flatMap(p =>
   tiles(p).filter(t => !mediaOf(p, t) && !t.querySelector('a[href]') && !gone(t))))[0];
 // Khong co gi cho nap: ve cuoi chat. Tin ngoai vung nhin bi ao hoa (rong), tin moi phai nam trong vung nhin.
 if (waiting) waiting.scrollIntoView({block: 'center'});
 else if (items.length) items[items.length - 1].scrollIntoView({block: 'end'});
 return items.map(item => {
  const role = item.getAttribute('data-message-role');
  const out = {id: item.getAttribute('data-message-id'), role};
  if (role !== 'assistant') {  // tin nguoi dung: chu de biet 1 lan gui truoc (tuong loi) thuc ra da toi muse
    out.text = item.innerText.trim().slice(0, 2000);
    return out;
  }
  const body = item.querySelector('[data-hatch-assistant-message-body]');
  // Tin dang viet / vua viet: [data-hatch-markdown-streaming]; tai lai trang thi tin cu hien bang
  // [data-hatch-plain-text] (van co the la markdown da render). Kiem tra 2026-10-30.
  const live = body && body.querySelector('[data-hatch-markdown-streaming]');
  const md = live || (body && body.querySelector('[data-hatch-plain-text]'));
  out.text = md ? md.innerText.trim() : '';
  out.html = md ? tg(md, 0).replace(/\n{3,}/g, '\n\n').trim() : '';
  // The link rieng (VD link tai file Muse vua upload): khung widget chi co <a href> + tieu de, khong co than markdown
  // hay khung dinh kem. Kiem tra 2026-10-29.
  // Link kho cong khai cua Muse (https://muse.ai/files/.../ten.mp4) tai thang duoc, khong can dang nhap: gui kem file.
  // Kiem tra 2026-11-04.
  const linked = [];
  for (const a of item.querySelectorAll('[data-pel-impression="chat_widget_impression"] a[href]')) {
    if (!/^https?:/.test(a.href) || a.closest('[data-testid^="hatch-chat-attachment-presentation-"]')) continue;
    const name = (a.querySelector('p[title]') || a).getAttribute('title') || a.innerText.split('\n')[0] || a.href;
    out.text = (out.text ? out.text + '\n' : '') + name + ': ' + a.href;
    out.html = (out.html ? out.html + '\n\n' : '') + '🔗 <a href="' + esc(a.href).replace(/"/g, '&quot;') + '">'
      + esc(name.trim()) + '</a>';
    const file = /^https:\/\/muse\.ai\/files\//.test(a.href) ? decodeURIComponent(new URL(a.href).pathname.split('/').pop()) : '';
    const ext = file.split('.').pop().toLowerCase();
    const kind = ['mp4', 'mov', 'webm', 'm4v'].includes(ext) ? 'video'
      : ['png', 'jpg', 'jpeg', 'webp', 'gif'].includes(ext) ? 'image' : ['mp3', 'wav', 'm4a', 'ogg'].includes(ext) ? 'audio' : '';
    if (kind) linked.push({kind, src: a.href, title: name.trim(), name: file});
  }
  out.streaming = !!(md && md.getAttribute('data-hatch-markdown-streaming') === 'true')
    || item.querySelector('[aria-busy="true"]') !== null;
  // Muse hoi lua chon bang khung nut rieng duoi chu (khong co dong [[nút: ...]]): lay nhan cac nut; nut "More options"
  // la dropdown (aria-haspopup). Da chon tren web (data-selected) thi thoi. Kiem tra 2026-10-29.
  const opts = body ? [...body.querySelectorAll('[data-copy-exclude] button:not([aria-haspopup])')] : [];
  out.choices = opts.some(b => b.getAttribute('data-selected') === 'true') ? []
    : opts.map(b => b.innerText.trim()).filter(Boolean);
  // Ten audio khong hien tren trang: lay displayText trong props React cua khung (Camoufox: qua wrappedJSObject), du
  // phong dong doc cho trinh doc man hinh "Assistant message: <ten>" (chi co khi tin chua render).
  const said = p => presOf(p).displayText
    || ((item.querySelector('[data-message-accessibility-surrogate]') || {}).textContent || '')
      .replace(/^Assistant message:\s*/, '').trim();
  // File: link goc (data.file.variants.original, *.metaaivm.com) la may sandbox cua Muse, ngu la het phan giai ten
  // mien -> khong tai duoc. name/mime de fetch_file mo khung xem file cua Muse lay noi dung. Kiem tra 2026-10-30.
  const fileOf = p => { const f = (presOf(p).data || {}).file || {}, t = p.querySelector('[title]');
    return {kind: f.missing ? 'missing' : 'file', src: '', title: f.label || (t ? t.getAttribute('title') : ''),
            name: (f.path || '').split('/').pop(), mime: f.mime || ''}; };
  // Khung "not found" nhung props van ghi missing: false (VD data.videos[i]): file con, may sandbox dang ngu / khoi dong
  // lai nen chua nap duoc -> lost: false, bot cho + tai lai trang. Kiem tra 2026-11-04.
  const entries = p => Object.values(presOf(p).data || {}).find(Array.isArray) || [];
  out.media = presentations(item).flatMap(p => kindOf(p) === 'file' ? [fileOf(p)] : tiles(p).map((t, i) => {
    const m = mediaOf(p, t), a = t.querySelector('a[href]');
    const b = t.matches('[title],[aria-label]') ? t : t.querySelector('[title],[aria-label]');
    const missing = !m && gone(t), e = entries(p)[i] || {};
    return {kind: missing ? 'missing' : kindOf(p), lost: missing && e.missing !== false,
            src: m ? (m.currentSrc || m.src || '') : (a ? a.href : ''),
            title: kindOf(p) === 'audio' ? (said(p) || '')
              : missing ? (e.label || (e.path || '').split('/').pop() || presOf(p).displayText || '')  // title khung: "Video not found..."
              : b ? (b.getAttribute('title') || b.getAttribute('aria-label') || '') : ''};
  })).concat(linked);
  return out;
 });
}"""
# Tai 1 URL (ke ca blob:) ngay trong trang. Camoufox chan doc ArrayBuffer cua trang ("Permission denied"), nen doc qua
# FileReader thanh data URL.
FETCH_JS = """async () => { const r = await fetch(%s); const b = await r.blob();
  return await new Promise((ok, err) => { const f = new FileReader(); f.onload = () => ok(String(f.result));
    f.onerror = () => err(String(f.error)); f.readAsDataURL(b); }); }"""
# Mo khung xem file cua Muse (bam the file trong tin, panel hatch-file-editor) va doc noi dung goc (markdown chua render)
# trong props React "content" cua trinh soan thao, roi dong panel. Panel khong co noi dung chu (VD PDF): null.
# The file chi render khi nam trong vung nhin. Kiem tra 2026-10-30.
FILE_JS = """async () => { const id = %s, name = %s, sleep = ms => new Promise(r => setTimeout(r, ms));
  let card;
  for (let i = 0; i < 20 && !card; i++) {
    const e = [...document.querySelectorAll('[data-message-item]')].find(e => e.getAttribute('data-message-id') === id);
    if (!e) throw new Error('khong thay tin ' + id);
    e.scrollIntoView({block: 'center'}); await sleep(500);
    card = e.querySelector('[data-testid^="hatch-chat-file-card-"]'); }
  if (!card) throw new Error('the file khong hien');
  card.click();
  const contentOf = ed => { const w = ed.wrappedJSObject || ed;
    const stack = [w[Object.keys(w).find(k => k.startsWith('__reactFiber'))].child];
    for (let n = 0; stack.length && n < 2000; n++) { const f = stack.pop(); if (!f) continue;
      const c = f.memoizedProps && f.memoizedProps.content; if (typeof c === 'string') return c;
      stack.push(f.sibling, f.child); }
    return null; };
  let text = null;
  try {
    for (let i = 0; i < 20 && text === null; i++) { await sleep(500);
      const ed = document.querySelector('[data-testid="hatch-file-editor"]');
      const fn = document.querySelector('[data-testid="hatch-file-editor-file-name"]');
      if (ed && fn && (!name || fn.getAttribute('title') === name)) text = contentOf(ed); }
  } finally {
    const x = document.querySelector('[data-testid="hatch-file-editor-close"]'); if (x) x.click(); }
  return text; }"""

logger = logging.getLogger("muse.sync")
lock = threading.Lock()  # 1 trinh duyet / 1 o chat: gui tung tin mot (muse_auto cung dung)


def fox_profiles():
    """Ten cac profile dang co trong FoxProfile."""
    listed = FoxProfileBrowser("", log=logger.debug)._call("GET", "/profiles", timeout=15).json()["profiles"]
    return [p["name"] for p in listed]


def open_chat(fox, url, refresh=False):
    """Tro fox vao tab cua chat (mo cua so moi neu chua co) ma khong dong vao tab/cua so dang dung."""
    fox.ensure()
    if not fox.supports_tab():  # ban cu bo qua "tab" -> se chiem tab hien hanh: dung han con hon
        raise FoxError(0, "FoxProfile chua ho tro tham so 'tab' -- khoi dong lai FoxProfile va profile nay")
    fox.open_tab(url)
    if refresh:
        fox.navigate(url)
    if not fox.wait_visible(MUSE_INPUT, 30):
        raise FoxError(0, f"khong thay o chat tren {url} (can dang nhap lai?)")
    return fox


def chat_browser(chat):
    """FoxProfileBrowser tro vao tab cua chat (tab da mo luc gui tin), chi de doc trang thai."""
    fox = FoxProfileBrowser(chat["profile"], log=logger.info)
    fox.profile_exists()
    fox.tab = chat["url"]
    return fox


def is_busy(fox):
    """Muse dang lam viec trong chat cua fox (chat_browser)?"""
    return bool(fox.evaluate(BUSY_JS))


def messages(fox):
    """Cac tin cuoi trong chat cua fox (xem MESSAGES_JS)."""
    return fox.evaluate(MESSAGES_JS) or []


def reload_chat(fox, url):
    """Tai lai trang chat: anh/video Muse vua tao doi khi ket o khung "dang tai" hang phut, tai lai trang la nap ngay."""
    with lock:  # khong tai lai giua luc dang go tin vao o chat
        fox.navigate(url)
        fox.wait_visible(MUSE_INPUT, 30)


def fetch_media(fox, src):
    """Tai anh/video/file Muse dinh kem (src thuong la blob:) ngay trong trang. Tra ve (bytes, mime)."""
    head, _, data = fox.evaluate(FETCH_JS % json.dumps(src)).partition(",")
    return base64.b64decode(data), head.removeprefix("data:").split(";")[0]


def fetch_file(fox, message_id, name):
    """Noi dung chu cua file Muse dinh kem (VD .md) trong tin message_id, qua khung xem file cua Muse (xem FILE_JS).
    None neu khung xem khong co noi dung chu."""
    with lock:  # bam / dong panel: khong chen vao luc dang go tin
        return fox.evaluate(FILE_JS % (json.dumps(message_id), json.dumps(name)))


_restarted = {}  # profile -> luc khoi dong lai gan nhat


def can_restart(profile):
    return time.time() - _restarted.get(profile, 0) >= RESTART_GAP_SECONDS


def restart_profile(profile, why=""):
    """Trinh duyet cua profile treo (FoxProfile timeout, trang xoa o chat ma khong gui): dong, mo lai va mo lai cac
    tab muse.ai dang co (side chat cua nguoi dung khac). Goi khi dang giu lock."""
    _restarted[profile] = time.time()
    logger.warning(f"Khoi dong lai trinh duyet {profile}: {why}")
    fox = FoxProfileBrowser(profile, log=logger.info)
    fox.profile_exists()
    try:
        urls = [t["url"] for t in fox.tabs() if "muse.ai" in t["url"]]
    except Exception:  # treo han: khong doc duoc tab, chi mo lai chat chinh
        urls = []
    fox.stop()
    fox.launch()
    for url in dict.fromkeys(urls or [MUSE_URL]):
        try:
            fox.open_tab(url)
        except Exception as e:
            logger.warning(f"{profile}: khong mo lai duoc tab {url}: {e}")


def upload_files(fox, files):
    for f in files:  # tung file mot: input file cua muse co the khong cho chon nhieu file 1 lan
        fox.upload([f], input_selector=MUSE_FILE_INPUT, timeout=30000)
        time.sleep(min(UPLOAD_MAX_WAIT_SECONDS, 3 + os.path.getsize(f) / 1048576))  # cho muse upload file xong


def _flat(s):
    return " ".join((s or "").split())


def try_send(chat, text, files, refresh, seen=None, base=None):
    """Mot lan thu gui text + files (duong dan, phai nam trong FOXPROFILE_UPLOAD_DIRS) vao chat. (da_gui, thong_bao).
    seen (set): dien id cac tin dang co truoc khi gui, de biet tin nao cua Muse la tra loi moi.
    base (set): id cac tin co truoc lan thu dau (lan dau: rong, ham tu dien). Lan thu sau gap tin nguoi dung moi cung
    noi dung thi lan truoc thuc ra da gui: khong gui lai (tranh tin trung)."""
    profile, key = chat["profile"], chat["key"]
    fox = FoxProfileBrowser(profile, log=logger.info)
    if not fox.profile_exists():
        return False, f"Profile '{profile}' chua co trong FoxProfile."
    open_chat(fox, chat["url"], refresh)
    current = messages(fox)
    before = {m["id"] for m in current}
    if base is not None:
        if not base:
            base.update(before)
        elif text and any(m["role"] == "user" and m["id"] not in base and _flat(text)[:60] in _flat(m.get("text"))
                          for m in current):
            if seen is not None:
                seen.clear()
                seen.update(base)
            return True, f"Da gui vao {key} (lan thu truoc da toi muse)."
    if seen is not None:
        seen.clear()
        seen.update(before)
    upload_files(fox, files)
    if text:
        fox.type_into(MUSE_INPUT, text)  # fill(): xuong dong trong text khong bi coi la Enter
    else:
        fox.click(MUSE_INPUT)
    fox.press("Enter", MUSE_INPUT)
    if not text:  # chi co file: o chat von rong nen khong co dau hieu xoa de kiem tra
        time.sleep(2)
        return True, f"Da gui vao {key}."
    # O chat duoc xoa chua du: trang treo (2026-10-29 23:58) van xoa o chat ma tin khong len muse. Phai thay tin
    # nguoi dung moi trong chat.
    cleared = False
    for _ in range(SEND_CONFIRM_POLLS):
        time.sleep(0.5)
        cleared = cleared or not fox.evaluate(f"() => document.querySelector('{MUSE_INPUT}').value")
        if cleared and any(m["role"] == "user" and m["id"] not in before for m in messages(fox)):
            return True, f"Da gui vao {key}."
    if cleared:
        return False, f"{key}: o chat da xoa nhung tin khong hien trong chat, chua gui duoc."
    return False, f"{key}: da go text nhung o chat chua duoc xoa, co the chua gui duoc."


def send(chat, text="", files=(), seen=None, base=None):
    """Gui text (+ files) vao chat muse; loi thi refresh trang va thu lai, van loi thi khoi dong lai trinh duyet cua
    profile (treo) va thu them 1 lan. Tra ve (ok, thong_bao). seen, base: xem try_send (base: giu qua cac lan goi
    send cho cung 1 tin de lan gui lai sau khong tao tin trung)."""
    text, files, msg = (text or "").strip(), list(files), ""
    if not text and not files:
        return False, "Tin rong, khong co gi de gui."
    base = set() if base is None else base
    with lock:
        for attempt in range(SEND_ATTEMPTS + 1):
            if attempt == SEND_ATTEMPTS:  # het refresh: trinh duyet treo -> khoi dong lai roi thu lan cuoi
                if not can_restart(chat["profile"]):
                    break
                try:
                    restart_profile(chat["profile"], msg)
                except Exception as e:
                    msg = f"{chat['key']}: khoi dong lai trinh duyet loi {type(e).__name__}: {e}"
                    break
            try:
                ok, msg = try_send(chat, text, files, refresh=0 < attempt < SEND_ATTEMPTS, seen=seen, base=base)
            except Exception as e:  # FoxError, mang...
                ok, msg = False, f"{chat['key']}: loi {type(e).__name__}: {e}"
            if ok:
                return True, (msg if attempt == 0 else f"{msg} (sau {attempt} lan refresh)" if attempt < SEND_ATTEMPTS
                              else f"{msg} (sau khi khoi dong lai trinh duyet)")
            logger.warning(f"send {chat['key']} lan {attempt + 1}/{SEND_ATTEMPTS + 1}: {msg}")
            time.sleep(2)
    return False, f"{msg} Da refresh va thu lai van loi."


def muse_ready(profile):
    """Profile dang mo va da dang nhap Muse (o chat cua main chat hien ra)? Khong tu mo profile dang tat.
    Profile chua co tab muse.ai thi mo 1 tab (trang chuyen sang trang dang nhap thi tab do tu dong)."""
    fox = FoxProfileBrowser(profile, log=logger.debug)
    if not fox.profile_exists() or not fox.is_running():
        return False
    with lock:
        try:
            fox.open_tab(MUSE_URL)
        except FoxError as e:
            if e.status == 404:  # bi chuyen sang trang dang nhap: chua dang nhap
                return False
            raise
        return fox.visible(MUSE_INPUT, 3000)


VN_NAMES = {"vn", "vietnam", "viet nam"}


def ip_check(profile):
    """IP ma profile dung de vao Muse (qua proxy cua profile, khong co proxy thi la IP may nay):
    (ip, quoc gia, co phai Viet Nam). FoxProfile hoi Cloudflare / ipinfo / ip-api (~10s)."""
    fox = FoxProfileBrowser(profile, log=logger.debug)
    r = fox._call("GET", f"/profiles/{profile}/ip-check", timeout=60).json()
    countries = [r.get("country")] + [s.get("country") for s in r.get("sources") or []]
    countries = [c for c in countries if c]
    is_vn = any(c.strip().casefold() in VN_NAMES for c in countries)
    return r.get("exit_ip") or "?", (countries[0] if countries else "?"), is_vn
