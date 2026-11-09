# Rà soát NFR-01 đến NFR-14 trên prototype

Đo ngày 10 Nov 2026 trên máy Windows, dữ liệu mẫu GreenLeaf Coffee (12,876 đơn, 45,959 phiên). Toàn bộ test: `.venv/Scripts/python -m pytest` (188 test đạt).

| NFR | Yêu cầu | Prototype làm gì | Bằng chứng | Kết quả |
| --- | --- | --- | --- | --- |
| NFR-01 | 95% lượt xem dashboard hiện nội dung chính dưới 3 giây | Mọi KPI tính bằng SQL có chỉ mục theo ngày | `test_nfr01_dashboard_within_3_seconds`: 20 lượt, đủ 13 widget, 4 kỳ. Đo tay: Last 30 days khoảng 0.07 giây phía server | Đạt (đo trên máy cục bộ, chưa đo qua mạng di động) |
| NFR-02 | PDF dưới 10 giây cho tối đa 30 ngày | ReportLab, tạo xong mới thêm vào danh sách | `test_nfr02_pdf_within_10_seconds`: 8 KPI, Last 30 days, khoảng 0.05 giây | Đạt |
| NFR-03 | Refresh mỗi 5 phút hoặc ngay khi upload | APScheduler chạy `refresh` mỗi 5 phút; upload hợp lệ gọi `refresh` ngay | `test_nfr03_refresh_every_5_minutes_and_on_upload`, `test_upload_08_changes_dashboard_right_away` | Đạt |
| NFR-04 | Email cảnh báo trong 1 phút sau refresh | Hộp thư giả, job gửi mỗi 10 giây | `test_email_sent_within_one_minute` | Đạt (email giả) |
| NFR-05 | Từ chối và báo "no access" khi thiếu quyền | Một hàm `auth.require()` cho mọi kiểm tra quyền, luôn trả 403 cùng một thông báo | Các test 403 trong `test_dashboard.py`, `test_reports_alerts.py`, `test_groups_notes_admin.py`; ảnh `16_no_access.jpg` | Đạt |
| NFR-06 | Phải đăng nhập; hết phiên sau 30 phút không hoạt động | Cookie phiên, `last_seen` cập nhật mỗi lần gọi API | `test_nfr06_every_data_endpoint_needs_sign_in` (63 endpoint), `test_session_ends_after_30_minutes_idle` | Đạt |
| NFR-07 | Dùng HTTPS | Không làm: prototype chạy trên `localhost` qua HTTP | Chỉ nêu trong SRS | Ngoài phạm vi prototype |
| NFR-08 | Mật khẩu lưu dạng salted hash | Không có mật khẩu: đăng nhập bằng cách chọn tài khoản mẫu | Chỉ nêu trong SRS | Ngoài phạm vi prototype |
| NFR-09 | 99.5% sẵn sàng mỗi tháng | Chạy một máy, không có giám sát | Chỉ nêu trong SRS | Ngoài phạm vi prototype |
| NFR-10 | Email lỗi: thử lại 3 lần cách 1 phút, luôn giữ alert trong app | Lần đầu + 3 lần thử lại; hết lượt thì đánh dấu "email not delivered" và ghi activity log | `test_email_retries_three_times_then_not_delivered`, `test_retry_stops_when_mail_recovers`; Admin bật "Simulate mail server failure" để demo | Đạt |
| NFR-11 | Không mất lựa chọn dashboard, báo cáo, rule, nhóm, ghi chú sau khi khởi động lại | Mọi thứ lưu trong SQLite theo tài khoản | `test_nfr11_saved_items_survive_restart`, `test_choices_survive_sign_out_and_restart` | Đạt |
| NFR-12 | Chạy trên 2 phiên bản mới nhất của Chrome, Safari, Edge; từ 360px đến desktop | HTML, CSS, JS thuần, mobile first | Đã kiểm tra bằng trình duyệt nhân Chromium ở 360px và 1280px: không trang nào tràn ngang. Ảnh `02` đến `18` ở 360px, `19` ở 1280px | Đạt một phần: chưa thử Safari và Edge thật |
| NFR-13 | Người mới thêm được widget trong 1 phút không cần hướng dẫn | Nút "Widgets" ở đầu dashboard, danh mục có tìm kiếm và ô tick | Cần thử với ít nhất 5 người dùng mới | Chưa đo |
| NFR-14 | Mọi điều khiển trên mobile tối thiểu 44 x 44 px | CSS chung: nút, ô chọn, ô nhập, link điều hướng `min-height: 44px` | `test_nfr14_css_sets_44px_minimum`. Đo bằng script trên 17 màn hình ở 360px với 4 vai trò: không có điều khiển nào dưới 44px | Đạt |

## Thêm trong bước 6

- API trả header `Cache-Control: no-store`: khi hai người đổi tài khoản trên cùng một trình duyệt, người sau không thấy dữ liệu đã lưu đệm của người trước (`test_api_responses_are_not_cached`). Lỗi này lộ ra khi chụp ảnh màn hình.
- Sửa giao diện: nút trong danh sách xuống dòng thay vì ép chữ ở 360px; tên file dài không tràn khung; thẻ số trên desktop không bị kéo cao theo biểu đồ; ẩn gợi ý "Tap a point" khi biểu đồ không có dữ liệu.

## Việc còn lại nếu cần

- NFR-12: mở app trên Safari (iPhone) và Edge thật, chụp thêm ảnh.
- NFR-13: nhờ 5 người chưa dùng app thử thêm một widget, bấm giờ.
- NFR-01: đo lại qua mạng di động thật (ví dụ chạy app trong mạng LAN và mở bằng điện thoại).
