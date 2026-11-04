# Muse2tele

Bot Telegram `muse_telebot` cùng FoxProfile, gom thành một thư mục riêng.

## Cấu trúc

```
Muse2tele\
  .env                     cấu hình cục bộ; không chia sẻ hoặc commit
  muse_telebot\            mã nguồn bot và skills
  foxprofile\
    foxprofile_client.py   client REST mà bot dùng
    repo\                  ứng dụng FoxProfile (có chức năng Clone)
    data\                  dữ liệu chạy FoxProfile cục bộ; không chia sẻ hoặc commit
  Videos\downloads\        thư mục tạm cho file upload
  setup.bat                cài 1 lần: .venv, thư viện, trình duyệt Camoufox
  start_all.bat            mở FoxProfile, chờ API sẵn sàng, rồi mở bot
  start_foxprofile.bat     chỉ mở FoxProfile (app desktop + API cổng 8010)
  start_bot.bat            chỉ mở bot
  clone_profile.bat/.py    clone profile từ dòng lệnh
```

Proxy, cấu hình các profile hiện có, dữ liệu trình duyệt (cookie/đăng nhập), database, trạng thái bot, log và thư mục tải xuống là dữ liệu cục bộ, không được đưa lên GitHub. `.gitignore` loại toàn bộ `foxprofile\data\`, các file `profiles.json`/`settings.json`, `.env` và dữ liệu runtime khỏi Git.

## Chạy

1. `setup.bat` (1 lần). Nếu đã có Python cài sẵn các thư viện thì bỏ qua được bước này. `_python.bat` sẽ dùng `.venv` nếu có, không thì dùng `%LOCALAPPDATA%\Python\bin\python3.exe`, cuối cùng mới tới `python` trong PATH.
2. `start_all.bat`.

**Không chạy đồng thời nhiều bản bot dùng chung `TELEGRAM_BOT_TOKEN`.** Telegram có thể báo lỗi 409 vì các bot giành update của nhau.

Thiết lập token và các giá trị cấu hình trong `.env` cục bộ trước khi chạy.

## Clone profile

Profile mới lấy proxy, hệ điều hành, timezone, locale và engine của profile nguồn. Có hai tuỳ chọn:

- **Chép dữ liệu trình duyệt** (cookie, đăng nhập, tab). Mặc định bật. Bỏ qua file khoá và cache.
- **Tạo fingerprint mới**. Mặc định bật. Trang web sẽ thấy profile mới là một máy khác.

Clone được cả khi profile nguồn đang chạy; file nào trình duyệt đang khoá thì bị bỏ qua. Nếu muốn dữ liệu chép đầy đủ nhất, hãy dừng profile nguồn trước.

Có 4 cách dùng:

- App desktop / web panel (`http://127.0.0.1:8010`): bấm nút Clone (biểu tượng 2 tờ giấy) trên dòng của profile.
- Dòng lệnh: `clone_profile.bat Muse2 Muse7`, thêm `--no-data` để chỉ chép cấu hình, `--same-fingerprint` để giữ fingerprint cũ.
- REST: `POST /api/v1/profiles/{name}/clone` với body `{"name": "...", "include_data": true, "new_fingerprint": true}`.
- MCP: tool `clone_profile`.

Khi clone kèm dữ liệu, profile mới có thể được đăng nhập vào cùng tài khoản với profile nguồn. Chỉ sử dụng profile và dữ liệu mà bạn có quyền truy cập; giữ dữ liệu xác thực ở máy cục bộ.

Chi tiết về bot: `muse_telebot\README.md`. Chi tiết về FoxProfile: `foxprofile\repo\README.vi.md`.
