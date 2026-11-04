# Cài skill lên profile Muse

Gói `dist/muse_skills.zip` chứa các skill, mỗi skill một thư mục `SKILL.md` + `skill.yaml`:

| Thư mục | Skill |
|---|---|
| `cinematic_photo/` | Cinematic Photo — bộ 6 ảnh điện ảnh + link Shopee |
| `mv_maker/` | MV Maker — MV điện ảnh từ bài hát |

Bản gốc trước khi sửa nằm trong `_original/`. Tạo lại zip bằng tay: `python build_zip.py` (bot tự tạo lại trước mỗi lần cài).

## Cài bằng bot

- **Tự động:** profile VIP hết hạn → bot Reset Muse → cài lại skill ngay, báo kết quả cho admin.
- **Bằng tay:** admin gõ `/skills <profile>` hoặc `/skills all` (mọi profile trong `muse_sync.json` + mọi profile VIP); `/skills stop` để dừng.

Bot gửi zip kèm tin bên dưới vào **main chat** của profile, tự bấm Allow nếu Muse xin quyền và chờ Muse trả lời. Trong lúc cài, bot tạm giữ không chuyển tin của main chat đó về Telegram; tin Muse trả lời việc cài không gửi cho người dùng VIP hay topic nhóm đã map. File zip tạm trên máy bị xoá ngay sau khi upload.

Tin cài đặt (bot đọc nguyên khối `text` đầu tiên dưới đây, sửa ở đây là bot dùng bản mới):

```text
Cập nhật skill dùng chung: cài các skill trong file muse_skills.zip đính kèm:
1. Giải nén vào ~/workspace/custom-skills/ → mỗi thư mục cấp 1 trong zip là 1 skill.
2. Nếu đã có thư mục cùng tên: sao lưu thư mục cũ vào ~/workspace/backups/<tên>_<ngày>/ trước khi ghi đè.
3. Nếu đã có skill khác làm cùng việc (MV, ảnh cinematic) dưới tên khác: không xoá, vẫn cài, và nêu tên skill đó trong câu trả lời.
4. Kiểm tra mỗi skill có SKILL.md và skill.yaml hợp lệ.
Không chạy thử skill, không gen ảnh/video. Trả lời ngắn, mỗi skill 1 dòng: tên — đã cài / lỗi gì.
```

## Lưu ý

- Profile chưa đăng nhập muse.ai (hiện là Muse6) thì cài lỗi; bot báo lỗi cho admin.
- Free pool (Muse2–4): mọi side chat của người dùng Free dùng chung skill của profile; skill đã tự tách thư mục làm việc theo người dùng (`~/workspace/users/<tên>/`).
