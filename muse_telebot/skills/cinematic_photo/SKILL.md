# Cinematic Photo — Bộ 6 ảnh điện ảnh của một nhân vật

## Purpose

Biến một yêu cầu ngắn thành **bộ 6 ảnh điện ảnh** của một nhân vật: **1 địa điểm + 1 bộ trang phục**, 6 góc/dáng khác nhau, kèm **link sản phẩm Shopee** của bộ đồ. Người dùng chỉ cần nói nhân vật; mùa, địa điểm, trang phục không nói thì tự chọn.

## Người dùng và xưng hô

- Skill dùng chung cho mọi profile Muse. Gọi và xưng hô với người dùng theo cách cuộc trò chuyện (hoặc memory của profile) đã dùng; chưa có thì gọi bằng tên và xưng "mình". Không mặc định một tên cụ thể.
- Luôn giao kết quả theo mục **Giao kết quả** bên dưới.

## Input Contract

- **Nhân vật (bắt buộc):** tên nhân vật có face ref. Không đoán. Không có face ref → xem Phase 0.
- **Mùa:** không nói → theo thời tiết thực tế hiện tại ở nơi người dùng sống (không rõ thì Hà Nội; VD tháng 10 = thu se lạnh).
- **Địa điểm:** không nói → địa điểm chụp ảnh đang hot nhất theo mùa (ưu tiên nơi có hoa/cảnh theo mùa).
- **Trang phục:** không nói → theo xu hướng mùa mới nhất, hợp thời tiết và vibe nhân vật.

Không hỏi lại chi tiết nhỏ: tự quyết và ghi giả định ở đầu tin giao.

## Workflow

### Phase 0 — Khóa mặt nhân vật

1. Tìm face ref, theo thứ tự: `~/workspace/characters/<nhân-vật>/reference/face_front.png` → `~/workspace/<nhân-vật>/reference/face_front.png` → `find ~/workspace -path "*reference*" -iname "face_front*"` rồi chọn file thuộc đúng nhân vật (VD trên profile gốc: Ngọc Anh ở `~/workspace/tiktok_dress/reference/`).
2. Không tìm thấy → xin người dùng **1 ảnh chính diện rõ mặt** (hoặc mô tả để gen một gương mặt mới, gửi kèm nút chọn duyệt). Lưu vào `~/workspace/characters/<nhân-vật>/reference/face_front.png` để lần sau dùng lại. Chỉ dùng ảnh người thật khi người dùng xác nhận đó là ảnh của họ hoặc họ có quyền dùng.
3. Ghi đặc điểm nhận diện (VD Thái Linh: mắt phượng, nốt ruồi dưới mắt trái) vào `~/workspace/characters/<nhân-vật>/reference/notes.md` để QA.

### Phase 1 — Nghiên cứu

1. **Địa điểm hot:** `browser.search` "địa điểm chụp ảnh hot + mùa + năm"; chọn 1 nơi giới trẻ đang check-in nhiều nhất.
2. **Trang phục:** `browser.search` xu hướng mùa hiện tại; chốt 1 outfit cụ thể (item + màu + cách phối), hợp thời tiết (VD Hà Nội se lạnh: trench coat, cardigan len, boot cổ ống).
3. **Link Shopee thật** cho từng món chính: sản phẩm tương đương, rating ≥4.8★. Ghi giá + rating + link. Không verify được (Shopee chặn bot) → ghi rõ "chưa verify", không bịa số liệu.

### Phase 2 — Sản xuất 6 ảnh

1. Mọi ảnh gen từ face ref của nhân vật, truyền làm identity reference + label đúng chuẩn `media.generate_image`.
2. **6 ảnh = 6 góc/dáng khác nhau**, cùng 1 địa điểm + 1 outfit: cận mặt, 3/4, toàn thân, đang đi, ngồi, ngược sáng/profile. Prompt tiếng Anh, ngôn ngữ máy quay ("shot on 35mm at f/2.8, shallow depth of field, film grain"); cấm "8K", "hyperrealistic".
3. **Gu mặc định (người dùng nói khác thì theo người dùng):** nghệ thuật hơn đẹp thường — silhouette ngược sáng, phản chiếu mặt nước, sương chiều, khăn/tóc bay trong gió. Tối đa **1/6 tấm nhìn thẳng camera**; còn lại profile, ngắm xa, quay lưng, hoa/khăn che một phần mặt. Tay tự nhiên (cầm túi, đút túi, chạm hoa), không cận tay, tay xa mặt.
4. **Giới hạn tool:** tối đa 4 ảnh/round → 2 round (4 + 2), round 2 chạy luôn trong turn nếu còn quota.
5. **QA từng ảnh:** so với `face_front.png` và `notes.md`. Mặt drift → gen lại tối đa 1 lần; vẫn lệch → đổi ảnh đó sang góc giấu mặt. `integrity_check_failed` → KHÔNG retry, đổi hướng sáng tạo thật sự.
6. Lưu vào `<thư mục làm việc>/cinematic_<nhân-vật>_<mùa>/cinematic-<n>-<mô-tả>.jpg` (xem **Nhiều người dùng trên một profile**).

### Phase 3 — Giao hàng

- Mở đầu: mùa, địa điểm (vì sao hot), outfit (vì sao hợp trend), giả định đã tự chọn.
- 6 ảnh đính kèm ngay trong tin trả lời, mỗi ảnh 1 dòng: góc/dáng + địa điểm + tên outfit.
- Cuối tin: danh sách link Shopee (giá, rating, hoặc "chưa verify").
- Không gửi tin chỉ có chữ khi đã hẹn giao ảnh.

## Giao kết quả

- Trả lời ngay trong chat và đính kèm ảnh trong tin.
- Ảnh giao ở dạng JPG/PNG, mỗi ảnh ≤10 MB.
- Cần người dùng chọn (nhân vật, địa điểm, duyệt gương mặt mới) → kết thúc tin bằng 1 dòng `[[nút: Lựa chọn 1 | Lựa chọn 2]]`.
- Người dùng có thể bị giới hạn số ảnh mỗi ngày: chỉ đính kèm 6 ảnh final, không đính kèm ảnh nháp/ảnh gen lại.

## Nhiều người dùng trên một profile

- Main chat của chủ profile: thư mục làm việc là `~/workspace/`.
- Side chat của người dùng khác (tin đầu side chat ghi "hãy gọi tôi là ..."): dùng `~/workspace/users/<tên-người-dùng>/`, không đọc, dùng hay nhắc tới file, nhân vật, memory của người khác. Nhân vật của chủ profile chỉ dùng khi người dùng đó tự gửi face ref.

## Operating Rules

1. **Nguyên tắc số 1:** mặt nhân vật không drift — QA từng ảnh trước khi giao.
2. 1 bộ ảnh = 1 địa điểm + 1 outfit, không đổi giữa chừng.
3. Tốc độ: chạy ngay trong turn, báo tiến độ gọn.
4. Link Shopee: chỉ ghi số liệu đã verify.
5. Xong bộ ảnh: ghi 2–3 dòng (địa điểm, outfit, ảnh nào phải gen lại) — main chat ghi vào `~/memory/YYYY-MM-DD.md`; side chat người dùng khác ghi vào `notes.md` trong thư mục dự án.

## Output Contract

- 6 file ảnh `cinematic-<n>-<mô-tả>.jpg` trong thư mục dự án.
- Tin giao: tóm tắt + 6 ảnh đính kèm + link Shopee (giá, rating hoặc "chưa verify").
- Ghi chú nghiên cứu 3–5 dòng theo Operating Rule 5.
