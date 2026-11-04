# MV Maker — Sản xuất MV điện ảnh tự động

## Purpose

Biến một bài hát + vài dòng mô tả thành MV điện ảnh hoàn chỉnh, **tự chạy từng batch, không đợi người dùng nói "tiếp"**. Skill lo toàn bộ: xử lý nhạc, phân tích lời, kịch bản shot, sản xuất clip, QA, ghép final, giao hàng.

## Người dùng và xưng hô

- Skill dùng chung cho mọi profile Muse. Gọi và xưng hô với người dùng theo cách cuộc trò chuyện (hoặc memory của profile) đã dùng; chưa có thì gọi bằng tên và xưng "mình". Không mặc định một tên cụ thể.
- Luôn giao kết quả theo mục **Giao kết quả**.

## Input Contract

- **Bài hát:** file audio hoặc link (YouTube/TikTok...). Link → tải về, trích audio gốc.
- **Mô tả:** nhân vật chính (face ref nào), phong cách quay, ý tưởng/cảm xúc chủ đạo, yêu cầu đặc biệt (nhân vật phụ, có cảnh hát hay không).
- **Face ref:** tìm theo thứ tự `~/workspace/characters/<nhân-vật>/reference/face_front.png` → `~/workspace/<nhân-vật>/reference/face_front.png` → `find ~/workspace -path "*reference*" -iname "face_front*"`. Không có → xin người dùng 1 ảnh chính diện rõ mặt (chỉ dùng ảnh người thật khi họ xác nhận là ảnh của mình hoặc có quyền dùng), lưu vào `~/workspace/characters/<nhân-vật>/reference/face_front.png`. MV không có nhân vật có mặt → bỏ qua.

Không hỏi lại chi tiết nhỏ: tự quyết theo continuity, ghi giả định ngắn vào kịch bản.

## Workflow

### Phase 1 — Xử lý nhạc (làm trước, làm kỹ)

1. Trích audio **nguyên bài, liên tục từ đầu đến cuối**. TUYỆT ĐỐI không cắt/ghép đoạn giữa bài (nối nhiều khúc gây vấp nhạc, cắt ngang câu/nhịp).
2. Kiểm tra phần đuôi: không lẫn outro/nội dung lạ sau bài hát; có thì cắt ở điểm bài hát kết thúc thật.
3. Fade-out nhẹ 2–3 s cuối. Đo mức âm đầu/giữa/cuối để xác nhận nhạc đầy đủ.
4. Ghi duration chính xác — đây là khung thời lượng; mọi section hình cộng lại phải đúng bằng số này.

### Phase 2 — Phân tích bài hát → Beat sheet

1. Nghe/transcribe toàn bài, chia theo **cấu trúc thật của lời** (mở đầu, các khổ, điệp khúc, cầu nối, kết), mỗi section có timestamp bắt đầu–kết thúc.
2. Mỗi section ghi: câu hát đang diễn ra, cảm xúc, và **thứ tự cảm xúc đúng lời** (VD tình đầu vui trước buồn sau — hình không được đảo).
3. Beat sheet = bảng: timestamp | lời/cảm xúc | shot | thời lượng thật | transition.
4. Sai số timestamp ±3 s chấp nhận ở bản nháp; trước khi ghép final phải rà lại bằng cách nghe + xem từng section.

### Phase 3 — Kịch bản shooting

1. Mỗi section chia thành shot **10 giây** (khớp khả năng gen clip). Section lẻ giây → shot cuối trim lúc ghép.
2. Đánh dấu từng shot: `mới không mặt` / `mới có mặt` / `tái dùng clip cũ` (ghi rõ file).
3. Nguyên tắc hình:
   - Em bé/trẻ nhỏ: quay tay, chân, lưng, silhouette — không cận mặt.
   - Không cận mặt nhân vật lúc "hát" (không lip-sync khớp tiếng Việt); cảnh hát nếu có thì ngắn, mic che miệng.
   - Ưu tiên chuyển động máy, phố phường, cảnh tĩnh; hạn chế hành động phức tạp.
   - Nhân vật phụ (nếu có yêu cầu): gom vào 1 cảnh, không làm loãng mạch chính.
4. Transition giữa section: fade in/out ~1 s hoặc xfade 0.8 s theo nhịp (kiểu "hiện/ẩn").
5. Báo người dùng ước tính trước khi sản xuất: số section, tổng số clip mới, số batch, thời gian dự kiến.

### Phase 4 — Sản xuất tự động theo batch

1. **Tự chạy batch, không hỏi "tiếp".** Mỗi run (kể cả cron): tối đa **6 video** + **4 ảnh** thành công. Hết quota → hẹn runonce cron chạy tiếp, không hỏi người dùng (ngoại lệ duy nhất: xác nhận trước khi bắt đầu ở side chat của người dùng khác, xem **Giao kết quả**).
2. **Frame-first cho shot có mặt:** gen ảnh start-frame từ face ref (đúng bối cảnh, đúng phục trang) → QA mặt khớp ref → image-to-video từ ảnh đó. Prompt viết bằng ngôn ngữ máy quay ("shot on 35mm at f/2.8, natural depth of field"); cấm "8K", "hyperrealistic".
3. Shot không mặt: gen video thẳng từ text prompt.
4. **QA sau mỗi batch:** xem strip frame các clip — mặt, trang phục, vật, bối cảnh, cảm xúc có đúng câu hát tại timestamp đó không. Sai → gen lại 1 lần. `integrity_check_failed` → KHÔNG thử lại dưới mọi hình thức; đổi hướng sáng tạo thật sự (giấu mặt, đổi góc, tập trung vật/bối cảnh) và ghi chú.
5. Khóa liên tục: phục trang, vật quan trọng, bối cảnh giữ nguyên xuyên suốt (dùng frame master làm ref khi cần).
6. Cập nhật `shooting_script.md` (tiến độ từng shot) sau mỗi batch để cron sau tiếp nối được.

### Phase 5 — Ghép final

1. Mỗi section: nối clip → scale 1280×720 → trim đúng thời lượng beat sheet → fade in/out (trừ đầu/cuối MV).
2. Nối **tất cả** section theo beat sheet → mux với **audio gốc Phase 1**, LUÔN dùng `-map 0:v -map 1:a` (không `-map` thì ffmpeg lấy nhầm track ồn của clip AI, mất tiếng nhạc).
3. Encode H.264/AAC, `-movflags +faststart`.
4. Verify: duration = duration nhạc, đủ 2 stream video + audio, mức âm giữa bài (~-10 dB) và cuối bài (fade-out), strip 6 frame rải đều timeline.

### Phase 6 — Giao hàng

Tin ngắn **kèm file MV đính kèm**: thời lượng, số đoạn, điểm đặc biệt, giả định đã tự chọn. Không gửi tin chỉ có chữ khi đã hẹn giao video.

## Giao kết quả

- Trả lời ngay trong chat, đính kèm file trong tin.
- File đính kèm tối đa 50 MB. File final > 48 MB → làm thêm bản `<ten>_MV_small.mp4` (giữ 1280×720, hạ bitrate: video kbps ≈ 393000 / duration giây − 128) và đính kèm bản đó; nói rõ bản gốc vẫn nằm trong thư mục dự án.
- Chỉ đính kèm MV final (và 1 ảnh strip nếu cần duyệt). Không đính kèm clip nháp: người dùng có thể bị giới hạn số video/ảnh mỗi ngày.
- Side chat của người dùng khác (có thể là gói Free, giới hạn video/ảnh mỗi ngày): báo trước ước tính ở Phase 3 và chờ người dùng xác nhận bằng `[[nút: Làm luôn | Rút gọn MV | Huỷ]]` trước khi chạy batch.
- Việc chạy bằng cron: báo người dùng thời gian dự kiến xong; khi họ nhắn lại, đính kèm lại MV final (hoặc báo tiến độ "32/34 clip, đang ghép") trong câu trả lời mới.
- Cần người dùng chọn → kết thúc tin bằng 1 dòng `[[nút: Lựa chọn 1 | Lựa chọn 2]]`.

## Nhiều người dùng trên một profile

- Main chat của chủ profile: thư mục làm việc là `~/workspace/`.
- Side chat của người dùng khác (tin đầu side chat ghi "hãy gọi tôi là ..."): dùng `~/workspace/users/<tên-người-dùng>/`; không đọc, dùng hay nhắc tới file, clip, nhân vật, memory của người khác.

## Operating Rules

1. **Nguyên tắc số 1:** hình chân thực, nhân vật không drift giữa các shot.
2. Nhạc là thánh: không cắt/ghép/sửa nhạc dưới mọi hình thức (ngoài cắt đuôi lạ + fade-out ở Phase 1). Chỉ cắt hình cho khớp nhạc.
3. Hình đúng lời đang hát tại đúng timestamp — kiểm tra bằng nghe + xem, không đoán.
4. Tốc độ: khi người dùng giục, chạy batch ngay trong turn, kéo lịch cron sớm lại, báo tiến độ gọn ("32/34 clip, đang ghép").
5. Ghi 2–3 dòng sau mỗi cột mốc (xong batch, xong final): main chat → `~/memory/YYYY-MM-DD.md`; side chat người dùng khác → `shooting_script.md` của dự án.
6. Bản quyền: dùng bản thu có bản quyền thì không tuyên bố đã được cấp quyền thương mại.

## Output Contract

Trong `<thư mục làm việc>/mv_<ten>/`:

- `<ten>_MV_FINAL.mp4`: duration = duration nhạc, 1280×720, H.264/AAC, faststart (+ `<ten>_MV_tg.mp4` nếu bản final > 48 MB).
- `shooting_script.md`: beat sheet + shot list + tiến độ batch.
- Clip tái dùng trong `clips/`, clip mới trong `v2clips/`, frame khóa mặt trong `v2frames/`.
