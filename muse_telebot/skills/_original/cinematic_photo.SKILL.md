# Cinematic Photo — Chụp ảnh điện ảnh tự động

## Purpose

Biến một yêu cầu ngắn của Linh thành **bộ 6 ảnh điện ảnh** của một nhân vật: **1 địa điểm + 1 bộ trang phục duy nhất**, 6 góc/dáng khác nhau, kèm **link sản phẩm Shopee** của bộ đồ. Cô chỉ gửi: nhân vật (+ mùa/địa điểm/trang phục nếu muốn). Không nói gì → tự chọn mùa, địa điểm hot nhất, trang phục hợp trend.

## Input Contract (nhận từ Linh)

- **Nhân vật:** tên (Ngọc Anh, Thái Linh, Minh Châu, Khánh Vy, An Nhiên, mẹ Hằng). Bắt buộc — không đoán.
- **Mùa:** xuân/hạ/thu/đông. Không nói → tự chọn theo thời tiết thực tế hiện tại (VD: tháng 10 Hà Nội = thu se lạnh).
- **Địa điểm:** Không nói → tự tìm địa điểm đang hot nhất (browser.search "địa điểm chụp ảnh hot + mùa + năm"), ưu tiên nơi có hoa/cảnh theo mùa.
- **Trang phục:** Không nói → tự chọn theo xu hướng Thu-Đông/Xuân-Hè mới nhất (browser.search), hợp thời tiết, hợp vibe nhân vật.

Không hỏi lại chi tiết nhỏ — tự quyết và ghi giả định vào đầu bài giao.

## Workflow

### Phase 1 — Nghiên cứu (làm trước mỗi bộ ảnh)

1. Tìm **địa điểm hot**: browser.search theo mùa + năm, chọn 1 nơi đang được giới trẻ check-in nhiều nhất (có hoa/cảnh đặc trưng càng tốt).
2. Tìm **xu hướng trang phục**: browser.search xu hướng mùa hiện tại, chọn 1 outfit cụ thể (tên item + màu sắc + cách phối), hợp thời tiết (VD: se lạnh Hà Nội → khoác cổ ống, trench coat, cardigan len).
3. Tìm **link Shopee thật** của outfit: sản phẩm tương đương, rating ≥4.8★, có trang bán được. Ghi rõ giá + rating + link. Nếu không verify được (Shopee chặn bot) → nói rõ "chưa verify", không bịa số liệu.

### Phase 2 — Sản xuất 6 ảnh

1. **Khóa mặt:** mọi ảnh đều gen từ face ref của nhân vật (`~/workspace/<nhân vật>/reference/face_front.png`, Ngọc Anh ở `~/workspace/tiktok_dress/reference/`), truyền làm identity reference + label đúng chuẩn media.generate_image.
2. **6 ảnh = 6 góc/dáng khác nhau**, cùng 1 địa điểm + 1 outfit: cận mặt, 3/4, toàn thân, đang đi, ngồi, ngược sáng/profile... Prompt tiếng Anh, ngôn ngữ máy quay ("shot on 35mm at f/2.8, shallow depth of field, film grain"), cấm "8K/hyperrealistic".
2b. **Gu nghệ thuật Linh đã chốt (16/10):** ưu tiên hướng nghệ thuật như bộ Hồ Tây — silhouette ngược sáng, phản chiếu mặt hồ, sương chiều, khăn/tóc bay trong gió. Tối đa **1 tấm nhìn thẳng camera** trong 6 tấm; còn lại: profile, ngắm xa, quay lưng, hoa/khăn che mặt một phần. Tay để tự nhiên (cầm túi, đút túi, chạm hoa), KHÔNG cận tay, tay xa mặt.
3. **Giới hạn tool:** tối đa 4 ảnh/round → chia 2 round (4 + 2). Round 2 tiếp nối ngay trong turn nếu còn quota, hoặc hẹn cron/subagent chạy tiếp.
4. **QA từng ảnh:** xem bằng mắt, so với face_front.png — mặt drift (đặc biệt với Thái Linh: mắt phượng, nốt ruồi dưới mắt trái) → gen lại tối đa 1 lần. Vẫn lệch → chuyển ảnh đó sang góc giấu mặt. `integrity_check_failed` → KHÔNG retry, đổi hướng sáng tạo thật sự.
5. Lưu vào `~/workspace/cinematic_<nhânvật>_<mùa>/` (VD: `~/workspace/ngoc_anh_cinematic/`).

### Phase 3 — Giao hàng

Mỗi ảnh 1 dòng riêng (giọng em–cô), đính kèm ảnh, ghi: **địa điểm + tên outfit + link Shopee (giá, rating)**. Mở đầu tóm tắt: mùa, địa điểm hot (vì sao hot), outfit (vì sao hợp trend). Không gửi text-only khi hẹn giao ảnh.

## Operating Rules

1. **Nguyên tắc số 1:** mặt nhân vật tuyệt đối không drift — QA từng ảnh trước khi giao.
2. 1 bộ ảnh = 1 địa điểm + 1 outfit duy nhất, không đổi giữa chừng.
2b. Gu mặc định: nghệ thuật > đẹp thường — ít nhất 5/6 tấm không nhìn thẳng camera, tay tự nhiên không cận (xem 2b ở Phase 2).
3. Tốc độ: Linh cần nhanh — ưu tiên chạy ngay trong turn, báo tiến độ gọn.
4. Ghi 2–3 dòng vào `~/memory/YYYY-MM-DD.md` sau mỗi bộ ảnh xong.
5. Link Shopee: chỉ ghi số liệu đã verify; chưa verify thì nói rõ.

## Output Contract

- 6 file ảnh trong `~/workspace/cinematic_<nhânvật>_<mùa>/` (đặt tên `cinematic-<n>-<mô-tả>.webp`).
- Tin nhắn giao: 6 ảnh đính kèm + địa điểm + outfit + link Shopee (giá, rating).
- Ghi chú nghiên cứu (địa điểm hot, trend đồ) 3–5 dòng trong memory ngày.
