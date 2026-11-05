# Muse2Tele len Render — checklist (chua deploy)

Bo file nay + `Dockerfile`, `start.sh`, `run_bot_linux.py`, `.dockerignore`
copy vao **thu muc goc cua repo Muse2Tele** (cung cap voi `requirements.txt`),
roi moi tao service tren Render. Em chua deploy that vi con thieu:
tai khoan Render, authkey Tailscale, token Telegram, login Muse/proxy —
tat ca deu la secret, anh tu nhap tren cong cua no, khong gui qua chat.

## 1. Vi sao khong dung nguyen mau anh gui

| Mau goc | Thuc te repo (da kiem tra code, commit b719a2f) |
|---|---|
| `python main.py` | Khong co `main.py` o root. Bot la `muse_telebot/muse_telebot.py`, chay kem FoxProfile |
| Chi chay 1 tien trinh | Can 2 tien trinh: FoxProfile API `127.0.0.1:8000` + bot. Bot khong co FoxProfile la bao loi |
| `src/main.py` cua FoxProfile | Do la ban GUI desktop (flet). Tren container phai dung che do server: `python -m src.server --host 127.0.0.1 --port 8000`, headless `virtual` |
| `muse_telebot.py` chay thang tren Linux | `main()` goi `ctypes.windll` + `CreateMutexW` (Windows-only) nen chet ngay tren Linux. `run_bot_linux.py` stub phan nay, khong sua code goc |
| `.env.example` dung duoc tren Linux | Trong do la duong dan Windows (`..\\Videos\\...`). Tren Linux no thanh 1 ten file co dau `\`, khong phai thu muc. Phai override bang duong dan Linux o muc 3 |
| Web Service | Sai loai service. Bot polling + FoxProfile chi loopback, khong co HTTP public. Phai la **Background Worker**, khong can `$PORT`, khong can healthCheckPath |

## 2. Tailscale (lam truoc, tren may cua anh)

- Admin console → Settings → Keys → Generate auth key: tick **Reusable** + **Ephemeral**.
  - Reusable: Render restart moi lan deu dang ky lai duoc. Single-use la lan 2 se loi.
  - Ephemeral: node tu xoa khoi tailnet khi container dung.
  - Dat expiry ngan, xong viec thi revoke/rotate. Key nay = quyen join tailnet, khong commit vao repo.
- Bat Tailscale SSH va kiem tra ACL: tai khoan cua anh phai duoc phep SSH toi node moi.
  Neu ACL chan thi `tailscale up --ssh` van thanh cong nhung `ssh` se bi tu choi.
- May cua anh phai dang o cung tailnet voi key nay thi moi `ssh` duoc.

## 3. Render — tao Background Worker + disk

- Loai service: **Background Worker** (khong phai Web Service, khong phai Private Service).
- Runtime: Docker, build tu repo (da co Dockerfile o root).
- Disk: bat buoc neu muon giu login Muse + map topic. Mount tai `/var/data`
  (neu mount cho khac thi set them `DATA_ROOT=<duong mount do>`).
  Free tier khong co disk + RAM 512MB khong du cho Camoufox moi profile —
  filesystem mac dinh cua Render mat het khi restart/redeploy, tuc la mat
  login Muse, `profiles.json`, map admin/nhom/topic.
- Env vars — chi nhap tren Render, khong ghi vao repo:

| Key | Gia tri |
|---|---|
| `TAILSCALE_AUTHKEY` | Key o muc 2 |
| `TELEGRAM_BOT_TOKEN` | Token tu @BotFather |
| `FOXPROFILE_API_TOKEN` | Chuoi ngau nhien **>= 24 ky tu** |
| `FOXPROFILE_URL` | `http://127.0.0.1:8000` |
| `FOXPROFILE_UPLOAD_DIRS` | `/var/data/uploads` |
| `MUSE_UPLOAD_DIR` | `/var/data/uploads/muse_telebot` |
| `DATA_ROOT` | `/var/data` (neu mount khac thi doi theo) |

Khong tao file `.env` trong repo de deploy. `.env` da co trong `.gitignore`
va `.dockerignore` cua bo nay.

## 4. Kiem tra sau deploy (theo thu tu log)

1. `tailscale status` trong container len, hostname `render-muse2tele` xuat hien.
2. `GET http://127.0.0.1:8000/api/v1/health` tra ve OK.
3. Log bot: `Bot @<ten_bot> da chay.` — neu thay `409 Conflict` la bot cu
   tren Windows van dang chay cung token, tat bot cu truoc.
4. Tu may cua anh (cung tailnet):
   `ssh root@render-muse2tele` (hoac `tailscale ssh root@render-muse2tele`).

## 5. Buoc chua tu dong duoc: dua profile Muse len Render

Login Muse khong nam trong repo — no nam trong `foxprofile/data` tren may
Windows cua anh (da bi `.gitignore` loai). Len Render phai lam 1 trong 2 cach:

- **A. Export/import:** tren FoxProfile Windows export tung profile ra ZIP
  (kem browser data), copy ZIP vao disk Render, goi API import tu trong
  container qua SSH. ZIP nay chua cookie/login — coi nhu secret.
- **B. Tao moi + dang nhap lai:** tao profile moi tren Render, gan proxy
  nuoc ngoai truoc khi mo, roi dang nhap muse.ai lai.

Sau do, mo profile len, cho bot tu tao topic, roi moi lam tiep tren Telegram:
`/start` (nguoi dau tien = chu bot) → tao nhom co Topics → `/setup`.

## 6. Rui ro can biet truoc

- Moi profile **phai gan proxy nuoc ngoai** truoc khi mo. README cua repo
  canh bao IP Viet Nam co the bi Muse chan/khoa tai khoan; IP egress cua
  Render khong thay the duoc proxy cua tung profile.
- Bot tu bam Allow, tu doc/ghi chat Muse qua trinh duyet — day la automation
  ngoai luong chinh thuc cua muse.ai, co rui ro khoa tai khoan. Chi dung
  tai khoan anh chap nhan rui ro nay.
- Panel FoxProfile chi chay loopback trong container. Background Worker
  khong co URL public — dung SSH de quan tri, dung mo panel ra Internet
  neu chua hieu ro token + ACL.
