# SEF-2026C-A1: BizBoard prototype

Prototype web app cho Assignment 1 (SRS & UML). Dùng để kiểm chứng yêu cầu và lấy ảnh minh họa cho SRS, không phải sản phẩm thật. Dữ liệu mẫu GreenLeaf Coffee nằm trong `data/` (xem `data/README.md`).

## Cài đặt (Windows)

Cần Python 3.11 trở lên.

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
```

Nếu Windows chặn file `_pydantic_core.pyd` ("An Application Control policy has blocked this file"), giữ đúng phiên bản pydantic trong `requirements.txt`. Dùng `python -m pip`, không gọi `pip.exe` trực tiếp.

## Chạy

```bash
.venv/Scripts/python -m uvicorn app.main:app --port 8000
```

Mở http://localhost:8000 và chọn một tài khoản mẫu. Lần chạy đầu tạo `bizboard.db` từ CSV; xóa file này (và thư mục `reports/`) để làm lại từ đầu. "Hôm nay" cố định là 8 Nov 2026.

Bản demo có sẵn báo cáo, ghi chú, cảnh báo, chia sẻ (dùng để chụp ảnh SRS), chạy trên cổng 8001 với DB riêng `demo.db`:

```bash
.venv/Scripts/python scripts/run_demo.py
```

## Kiểm thử

```bash
.venv/Scripts/python -m pytest
```

Test đối chiếu với các con số trong `data/README.md` và từng ngày trong `kpi_daily_answer_key.csv`.

## Tài liệu

- `docs/NFR_review.md`: rà soát NFR-01 đến NFR-14, bằng chứng và phần còn thiếu.
- `docs/SRS_notes.md`: các quyết định đã chốt khi làm prototype, cần đưa vào SRS.
- `docs/screenshots/`: 19 ảnh màn hình (18 ảnh ở 360px, 1 ảnh desktop 1280px).

| Ảnh | Nội dung |
| --- | --- |
| 01 | Đăng nhập bằng tài khoản mẫu (Nam đã bị deactivate) |
| 02, 19 | Dashboard của Hoa trên điện thoại và desktop |
| 03, 04 | Danh mục widget, theo nhóm và khi tìm kiếm |
| 05 | Trend Total Revenue với bộ lọc Region: North |
| 06 | Drill-down ngày 3 Nov: 16 đơn, 15 completed, $662.50 |
| 07 | Thông báo no-data nêu rõ kỳ và bộ lọc, có nút đổi kỳ và xóa lọc |
| 08 | So sánh 1 đến 7 Nov với 15 đến 21 Sep |
| 09 | Tạo báo cáo, danh sách báo cáo, báo cáo định kỳ |
| 10 | Chủ báo cáo: chia sẻ, thu hồi, ghi chú |
| 11, 12 | Người nhận qua nhóm viết được ghi chú; người nhận cá nhân chỉ đọc |
| 13 | Thông báo trong app (cảnh báo R01, R02, chia sẻ) và rule cảnh báo |
| 14 | Hồ sơ của Bao (không có email, chỉ nhận in-app) |
| 15 | Group Owner quản lý Sales Team |
| 16 | Thông báo No access |
| 17, 18 | Trang Admin: tài khoản, nhóm, ghi chú, activity log, lịch sử upload, công cụ demo |
