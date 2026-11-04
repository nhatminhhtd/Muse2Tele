# MV Maker — Sản xuất MV điện ảnh tự động

## Purpose

Biến một bài hát + mô tả ngắn của Linh thành MV điện ảnh hoàn chỉnh, chạy **tự động từng batch không cần cô phải nói "tiếp"**. Cô chỉ gửi: bài hát (file/link) + vài dòng mô tả (nhân vật, phong cách, ý tưởng). Skill lo toàn bộ: xử lý nhạc, phân tích lời, kịch bản shot, sản xuất clip, QA, ghép final, giao hàng.

## Input Contract (nhận từ Linh)

- **Bài hát:** file audio hoặc link (YouTube/TikTok...). Nếu là link, tải về và trích audio gốc.
- **Mô tả:** nhân vật chính (dùng face ref nào), phong cách quay, ý tưởng/cảm xúc chủ đạo, yêu cầu đặc biệt (VD: nhân vật phụ xuất hiện mấy lần, có cảnh hát hay không).

Không hỏi lại chi tiết nhỏ — tự quyết theo continuity và ghi giả định ngắn vào kịch bản.

## Workflow

### Phase 1 — Xử lý nhạc (làm trước, làm kỹ)

1. Trích audio **nguyên bài, liên tục từ đầu đến cuối**. TUYỆT ĐỐI không cắt/ghép các đoạn giữa bài (bài học xương máu: nối 3 khúc gây vấp nhạc, cắt ngang câu/nhịp).
2. Kiểm tra phần đuôi: đảm bảo không lẫn outro/nội dung lạ sau bài hát. Nếu có, cắt sạch ở điểm bài hát kết thúc thật.
3. Fade-out nhẹ 2–3s cuối. Đo mức âm đầu/giữa/cuối xác nhận nhạc đầy đủ.
4. Ghi duration chính xác — đây là "khung xương" thời lượng, mọi section hình phải cộng đúng bằng số này.

### Phase 2 — Phân tích bài hát → Beat sheet

1. Nghe/transcribe toàn bài, chia theo **cấu trúc thật của lời** (mở đầu, các khổ, điệp khúc, cầu nối, kết), mỗi section có timestamp bắt đầu–kết thúc.
2. Mỗi section ghi: nội dung câu hát đang diễn ra, cảm xúc (vui/buồn/hy vọng...), và **thứ tự cảm xúc phải đúng lời** (VD: tình đầu vui trước buồn sau — hình không được đảo).
3. Beat sheet = bảng: timestamp | lời/cảm xúc | shot tương ứng | thời lượng thật | kiểu transition (fade/xfade theo nhịp).
4. Sai số timestamp chấp nhận ±3s ở bản nháp, nhưng trước khi ghép final phải rà lại bằng cách nghe + xem thử từng section.

### Phase 3 — Kịch bản shooting

1. Mỗi section chia thành các shot **10 giây** (khớp khả năng gen clip). Section lẻ giây thì shot cuối trim bớt lúc ghép.
2. Đánh dấu từng shot: `mới không mặt` / `mới có mặt` / `tái dùng clip cũ` (ghi rõ file).
3. Nguyên tắc hình ảnh:
   - Em bé/trẻ nhỏ: quay tay, chân, lưng, silhouette — không cần cận mặt.
   - Không quay cận mặt nhân vật lúc "hát" (không lip-sync khớp tiếng Việt); cảnh hát nếu có thì ngắn, dùng mic che miệng.
   - Ưu tiên chuyển động máy, phố phường, cảnh tĩnh; hạn chế hành động phức tạp.
   - Nhân vật phụ (nếu cô yêu cầu): gom vào 1 cảnh duy nhất, không làm loãng mạch chính.
4. Transition giữa section: fade in/out ~1s (hoặc xfade 0.8s theo nhịp) — Linh đã duyệt kiểu "hiện/ẩn".

### Phase 4 — Sản xuất tự động theo batch

1. **Tự động chạy batch, không hỏi "tiếp".** Mỗi run (kể cả cron): tối đa **6 video** + **4 ảnh** thành công. Hết quota thì hẹn runonce cron chạy tiếp, dồn việc không hỏi user.
2. **Frame-first cho mọi shot có mặt:** gen ảnh start-frame từ face ref (ép mặt vào đúng bối cảnh, đúng phục trang) → QA mặt khớp ref → mới image-to-video từ ảnh đó. Prompt ảnh/video viết bằng ngôn ngữ máy quay ("shot on 35mm at f/2.8, natural depth of field"), cấm từ "8K/hyperrealistic".
3. Shot không mặt: gen video trực tiếp từ text prompt.
4. **QA sau mỗi batch:** strip frame giữa các clip — kiểm tra mặt/trang phục/vật/bối cảnh/cảm xúc có đúng câu hát đang diễn ra không. Sai → gen lại 1 lần. `integrity_check_failed` → KHÔNG thử lại dưới mọi hình thức, đổi hướng sáng tạo thật sự (giấu mặt, đổi góc, tập trung vật/bối cảnh) và ghi chú.
5. Khóa liên tục: phục trang + vật quan trọng + bối cảnh giữ nguyên xuyên suốt các shot (dùng frame master làm ref khi cần).

### Phase 5 — Ghép final

1. Mỗi section: nối các clip → scale 1280×720 → trim đúng thời lượng beat sheet → fade in/out (trừ đầu/cuối MV).
2. Nối 12 section → mux với **audio gốc Phase 1**, LUÔN dùng `-map 0:v -map 1:a` (bài học: không `-map` là ffmpeg lấy nhầm track ồn của clip AI, mất tiếng).
3. Verify: duration = duration nhạc, đủ 2 stream video+audio, đo mức âm giữa bài (~-10dB) và cuối bài (fade-out), xem strip 6 frame rải đều timeline.

### Phase 6 — Giao hàng

Gửi user tin nhắn ngắn (giọng em–cô) **kèm file MV đính kèm**, tóm tắt: thời lượng, số đoạn, điểm đặc biệt (VD: cảnh gia đình cuối). Không gửi tin nhắn chỉ có chữ khi hẹn giao video.

## Operating Rules

1. **Nguyên tắc số 1:** hình phải chân thực, nhân vật tuyệt đối không drift giữa các shot.
2. Nhạc là thánh: không cắt/ghép/sửa nhạc dưới mọi hình thức. Chỉ cắt hình cho khớp nhạc.
3. Hình phải đúng lời đang hát tại đúng timestamp — kiểm tra bằng cách nghe + xem, không đoán.
4. Tốc độ: Linh cần nhanh — khi cô giục, ưu tiên chạy batch ngay trong turn hiện tại, kéo lịch cron sớm lại, báo tiến độ gọn ("32/34 clip, đang ghép").
5. Lưu kịch bản + tiến độ vào `~/workspace/mv_<ten>/shooting_script.md`; cập nhật sau mỗi batch để cron sau tiếp nối được.
6. Ghi 2–3 dòng vào `~/memory/YYYY-MM-DD.md` sau mỗi cột mốc (xong batch, xong final).
7. Bản quyền: nếu dùng bản thu có bản quyền, không tuyên bố đã được cấp quyền thương mại.

## Output Contract

- `~/workspace/mv_<ten>/nhatky_MV_FINAL.mp4` (tên theo dự án): duration = duration nhạc, 1280×720, H.264/AAC, faststart.
- `shooting_script.md`: beat sheet + shot list + tiến độ batch.
- Clip nguồn trong `clips/` (tái dùng) và `v2clips/` (mới), frame khóa mặt trong `v2frames/`.
