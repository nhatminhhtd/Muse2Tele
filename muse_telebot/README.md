# muse_telebot

Bot Telegram `@muse_tbot` giúp người dùng làm việc với Muse (muse.ai) ngay trên Telegram, không cần vào web.

## Cách hoạt động

- **Telegram → Muse:** bot gõ tin nhắn, ảnh, video, GIF, file, audio, voice vào main chat hoặc side chat muse.ai của profile FoxProfile tương ứng. Tin được gửi nguyên văn, không thêm thẻ; mọi chữ bot gửi vào Muse (trích dẫn khi trả lời tin, bấm nút, nhắc hết lượt Free, tin cài skill, nội dung skill) không nhắc tới bot hay Telegram. Chat Muse mới (side chat Free, main chat VIP, side chat topic VIP) mở đầu bằng đúng 1 câu: `Ở cửa sổ chat này, hãy gọi tôi là "<tên>"` (topic VIP: câu này + tin đầu tiên của topic).
- **Muse → Telegram:** bot đọc câu trả lời của Muse ngay trên trang, gồm chữ và ảnh/video/file đính kèm, rồi gửi về đúng chat Telegram. Định dạng của Muse (đậm, nghiêng, `code`, khối code, link, tiêu đề, danh sách, bảng) được chuyển sang HTML của Telegram. Nếu Telegram từ chối HTML, bot gửi lại dạng chữ thường. Muse chỉ trả lời trong chat, không tự gửi Telegram; skill `telegram_sender` đã bỏ. Câu trả lời ngắn đến sau khoảng 5 giây; trước đây, khi Muse tự gửi qua skill, mất khoảng 17 giây.
- **Chat đã map luôn được theo dõi:** cứ 5 giây bot đọc mọi chat muse đã map trong `muse_sync.json`. Mọi tin mới của Muse ở đó đều về đúng chat/topic đã map, kể cả tin không trả lời tin Telegram nào: khi bạn gõ trên web, hoặc khi việc Muse tự chạy (batch, cron) xong về sau. Câu trả lời cho tin gửi từ chỗ khác (ví dụ chat riêng với bot) vẫn về chỗ đã gửi. Mỗi tin chỉ được chuyển một lần. Profile đang tắt thì bỏ qua và không tự mở; khi profile mở lại, bot gửi bù các tin còn thiếu. Chat vừa map thì các tin đã có không bị gửi lại. Side chat đã map được giữ tab mở để bot đọc được.
- **Nút bấm:** Muse kết thúc tin bằng dòng `[[nút: A | B]]` thì bot biến dòng đó thành nút bấm. Bấm nút thì bàn phím đổi thành "✅ <lựa chọn>", và lựa chọn được gửi lại vào chat Muse.
- **Trạng thái:** khi Muse đang làm, Telegram hiện "MuseAI đang nhập...". Bot nhận biết Muse đang làm khi nút Stop của ô chat trên muse.ai hiện ra. Khi Muse xong, bot đặt reaction 👌.
- **Ảnh/video kẹt tải:** nếu ảnh hoặc video của Muse kẹt ở khung "đang tải" quá 20 giây, bot tải lại trang chat.
- **Poll update:** chỉ bot này được poll update. Muse không gọi `get-updates`, nếu gọi sẽ bị lỗi 409 và giành mất tin của bot.

## Người dùng

| Loại | Dùng chat nào | Ghi chú |
|---|---|---|
| Admin (`MUSE_BOT_ALLOWED_CHAT_IDS`) | Main chat và side chat trong `muse_sync.json` (Muse, Muse2–4), chọn bằng `/to`. Nhóm/topic map bằng `/to` gõ ngay trong nhóm/topic. | `/stats`, `/broadcast`, `/approve*`, `/<profile> <nội dung>` |
| Free | Mỗi người 1 side chat riêng trong pool Muse2, Muse3, Muse4, tối đa 10 side chat mỗi profile (30 suất). Người mới vào profile đang ít người Free nhất; bằng nhau thì vào profile hôm nay ít ảnh/video nhất. Tạo side chat lỗi (profile tắt, chưa đăng nhập) thì bot tự thử profile khác trong pool. | `/start` xem số suất còn lại và đăng ký. Dùng 3 ngày, mỗi ngày tối đa 10 video và 50 ảnh do bot chuyển về. Hết hạn thì bot xoá side chat và trả suất về pool; 3 ngày sau mới đăng ký lại được. |
| VIP | Mỗi người 1 profile riêng, không giới hạn ảnh/video. Profile VIP là mọi profile FoxProfile có tên là email `@sanhdieu247.xyz`; bot đọc lại danh sách mỗi phút, nên thêm profile mới trong FoxProfile là có thêm chỗ VIP. | Mua trong `/start`: chọn số ngày, nhận mã QR VietQR chuyển khoản tới VIB 240628888 theo bảng giá `VIP_PRICES` trong `muse_users.py` (1 ngày 10k, 3 ngày 25k, 7 ngày 50k, 30 ngày 200k) (nội dung `MUSE<số yêu cầu>`), bấm "Tôi đã chuyển khoản", rồi admin bấm duyệt. Admin cũng cấp thẳng được bằng `/vip <user id> <số ngày>`. Chế độ **Chat trực tiếp**: chat riêng với bot vào main chat. Chế độ **Group topic**: gõ `/vipgroup` trong nhóm đã bật Topics; General vào main chat, mỗi topic là 1 side chat, tạo khi có tin đầu tiên trong topic. Hết hạn (kể cả khi admin `/vip <id> 0`) thì bot vào Settings → Data controls → **Reset Muse**, gõ tên agent để xác nhận và xoá hết dữ liệu Muse của profile, rồi trả profile về pool và **cài lại skill** trong `skills\` (báo kết quả cho admin). Gia hạn sau đó sẽ nhận một Muse mới. |

Người có VIP còn hạn thì chat riêng luôn vào profile VIP, kể cả admin. Admin dùng `/me` để xem menu như người dùng thường và thử mua VIP.

Khi đăng ký Free, bot tạo side chat bằng tin đầu tiên báo cho Muse tên người dùng và các quy tắc của side chat (`FREE_INTRO` trong `muse_telebot.py`). Dữ liệu người dùng và quota nằm trong `muse_users.db`.

Chiều muse → Telegram cũ (`muse_sync.py` bản cũ) đã bỏ. Toàn bộ phần muse trong `..\telegram_control_bot.py` cũng đã bỏ (lệnh `/muse`, `/muse2`, `/approve*` và chuyển bài từ kênh).

## File

| File | Vai trò |
|---|---|
| `muse_telebot.py` | Bot, chạy chính (`python muse_telebot.py`). Tiêu đề console: `Python_Muse_Telebot`. |
| `muse_sync.py` | Thao tác với muse.ai qua FoxProfile: gõ text và upload file vào chat (lỗi thì refresh trang, thử lại 3 lần), đọc câu trả lời và media của Muse, tạo và xoá side chat. Đọc `muse_sync.json`. |
| `muse_users.py` | Người dùng, gói Free, VIP, thanh toán, quota trong ngày, thống kê (`muse_users.db`, SQLite). |
| `vietqr.py` | Tạo mã QR chuyển khoản VietQR (chuẩn EMVCo/NAPAS) ngay trên máy. Cần `pip install qrcode pypng`. |
| `muse_auto.py` | Tự bấm Allow trên muse.ai, chạy thành thread trong bot. |
| `muse_skills.py` | Cài skill trong `skills\` lên 1 profile: gửi `muse_skills.zip` kèm tin cài đặt vào main chat, tự bấm Allow, chờ Muse trả lời. |
| `skills\` | Skill dùng chung cho mọi profile Muse (`cinematic_photo`, `mv_maker`). Xem `skills\INSTALL.md`. |
| `muse_sync.json` | Map chat muse ↔ chat Telegram. Bot đọc lại mỗi lần dùng nên sửa file không cần restart. |
| `muse_autoapprove.json` | Trạng thái bật/tắt auto Allow. |
| `muse_telebot_state.json` | Chat muse mà mỗi chat riêng đang chọn (`/to`), id các tin Muse đã chuyển về Telegram (để không gửi lặp) và các chat đang theo dõi. Bot tự tạo. |
| `setup_task.ps1` | Chuyển app `Python_Muse_Sync` cũ sang app này. Chỉ chạy 1 lần. |
| `_legacy\` | Các file cũ từ `foxprofile\`, do `setup_task.ps1` chuyển vào. |

`foxprofile_client.py` vẫn được dùng chung từ `..\foxprofile\`.

## Cấu hình

`.env` (đặt trong thư mục này hoặc `..\.env`):

```
TELEGRAM_BOT_TOKEN=<token bot mới tạo bằng BotFather>
MUSE_BOT_ALLOWED_CHAT_IDS=1302966409        # tùy chọn, mặc định = TELEGRAM_ALLOWED_CHAT_IDS
MUSE_UPLOAD_DIR=...                          # tùy chọn, mặc định ..\Videos\downloads\muse_telebot
```

`MUSE_UPLOAD_DIR` phải nằm trong `FOXPROFILE_UPLOAD_DIRS` (`..\foxprofile\repo\.env`, hiện là `..\Videos\downloads`).

`muse_sync.json`:

```json
{
  "channels": {"Muse": "-1003773996087", "Muse2": "-1003939191673"},
  "threads":  {"Muse2": {"<thread id hoặc URL https://muse.ai/thread/...>": "-100..."}}
}
```

- Giá trị là chat id của kênh hoặc nhóm Telegram. Mọi bài đăng trong đó đều được chuyển vào chat muse tương ứng.
- Để `""` thì chat muse đó chỉ nhận tin gửi qua chat riêng với bot.
- Nhóm có topic: dùng giá trị `"<chat id>/<topic id>"` để map riêng từng topic, mỗi side chat một topic. Gửi `/id` trong topic để bot trả về hai số này. Cách dễ hơn là gõ `/to` ngay trong topic: bot tự ghi map vào file. Muốn map vào side chat thì gõ `/to <profile> <link side chat>`.
- Nhóm hoặc topic chưa map: tin do người được phép gửi sẽ vào chat muse mà người đó đang chọn bằng `/to` ở chat riêng (hiện là Muse3).

## Dùng

- **Kênh hoặc nhóm đã map:** đăng bài là bot tự chuyển. Với kênh, bot phải là admin. Với nhóm, cần tắt privacy mode (BotFather → `/setprivacy` → Disable).
- **Người dùng thường:** `/start` để xem gói đang dùng hoặc đăng ký Free. Sau đó nhắn gì cho bot cũng được chuyển vào side chat riêng của họ.
- **Admin:** `/stats` xem thống kê người dùng. `/broadcast <nội dung>`, hoặc reply một tin chữ/ảnh/video bằng `/broadcast`, để quảng bá tới mọi người dùng (bot hỏi xác nhận trước khi gửi).
  - `/log [user id] [số tin]`: xem các tin người dùng Free/VIP đã gửi vào Muse (lưu trong bảng `prompts` của `muse_users.db`, cả lựa chọn bấm nút và tên file đính kèm).
  - Video Muse gửi cho người dùng Free/VIP được bot chép thêm cho admin, kèm tên người dùng, gói, chat muse và tin họ vừa gửi.
  - `/skills <profile>` hoặc `/skills all`: cài lại skill qua main chat của profile (all = mọi profile trong `muse_sync.json` và mọi profile VIP). `/skills stop` dừng: bot bấm Stop lượt cài của Muse ở profile đang cài, các profile sau bị bỏ qua. Trong lúc cài, bot tạm giữ không chuyển tin main chat của profile đó về Telegram; tin Muse trả lời việc cài không gửi cho ai.
- **Chat riêng của admin** (các chat id được phép):
  - Gửi gì bot cũng chuyển vào chat muse đang chọn.
  - `/to` chọn chat muse.
  - `/muse2` (không kèm nội dung) chọn main chat của Muse2.
  - `/muse2 nội dung` gửi thẳng nội dung vào main chat của Muse2.
- `/approve_on`, `/approve_off`, `/approve`: bật, tắt, xem auto Allow.
- **File trên máy:** file người dùng gửi lên chỉ nằm tạm trong `MUSE_UPLOAD_DIR` và bị xoá ngay sau khi upload vào muse; file tạm còn sót do bot tắt giữa chừng được xoá khi bot khởi động. Ảnh/video Muse gửi về chỉ nằm trong RAM, không ghi ra đĩa.
- **Trạng thái trên tin:** 👀 đã nhận, 👍 đã vào muse, 👎 lỗi. Khi lỗi, bot báo thêm cho các chat được phép.
- Nhiều ảnh/video gửi cùng lúc (album) được gom thành một tin trên muse.
- Tin reply một tin khác thì phần trích dẫn tin gốc được thêm vào đầu.
- Bot API chỉ tải được file ≤ 20MB.
- Bot không bỏ qua các tin đến lúc nó đang tắt: khi chạy lại sẽ chuyển tiếp những tin đó.

## Chuyển từ hệ thống cũ (1 lần)

1. Tạo bot mới bằng BotFather, thêm `TELEGRAM_BOT_TOKEN` vào `..\.env`.
2. Thêm bot mới làm admin của 2 kênh Muse/Muse2. Có thể gỡ bot cũ khỏi kênh vì nó không còn xử lý kênh nữa.
3. Chạy `powershell -ExecutionPolicy Bypass -File setup_task.ps1`. Nếu báo lỗi quyền thì chạy bằng PowerShell Administrator. Script sẽ:
   - tạo task `Python_Muse_Telebot` (event 8898) và xóa task `Python_Muse_Sync`;
   - tắt `muse_sync.py` và control bot cũ;
   - chuyển file cũ vào `_legacy\`;
   - restart `Python_Monitor_Apps`. Monitor sẽ tự bật lại control bot và bot này.
